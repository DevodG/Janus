"""
High-Fidelity MMSA Dissonance Engine.

Orchestration layer for tri-modal (Audio + Text + Video) deception detection.
Now wired to DissonanceEngine for real wav2vec2 / DistilBERT features.

Env vars consumed by this layer:
  USE_DIMENSIONAL_AUDIO_MODEL=true   → audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim
  USE_EMOTION2VEC=true               → emotion2vec/emotion2vec_plus_large (requires funasr)

Env vars forwarded to DissonanceEngine (set them in the same .env):
  AUDIO_TEMPERATURE=1.5              → softmax temperature for audio emotion calibration
  DISSONANCE_WEIGHTS=0.5,0.3,0.2    → w1·audio_text + w2·prosody + w3·text_conf
"""

import os
import logging
import time
import json
from typing import Dict, List, Any, Optional
import numpy as np
from pathlib import Path

# Guardian Integrated services
from .guardian_sensory import guardian_sensory
from .scam_graph import scam_graph
# Core dissonance engine — real models, VAD space, prosody, persistence
from .dissonance_engine import dissonance_engine, _probs_to_vad

# Heavyweight optional imports — deferred
torch       = None
mp          = None
tasks       = None
vision      = None
cv2         = None
yt_dlp      = None
static_ffmpeg = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Upgrade 1: audeering dimensional model
# ---------------------------------------------------------------------------
_USE_DIMENSIONAL = os.getenv("USE_DIMENSIONAL_AUDIO_MODEL", "false").lower() == "true"
_USE_EMOTION2VEC = os.getenv("USE_EMOTION2VEC", "false").lower() == "true"

DIMENSIONAL_MODEL_NAME = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"


class _DimensionalAudioModel:
    """
    Wraps the audeering regression model that directly outputs
    [arousal, dominance, valence] floats — no VAD lookup needed.
    """

    def __init__(self):
        self._loaded = False
        self.processor = None
        self.model     = None

    def load(self) -> bool:
        global torch
        try:
            import torch as _torch
            torch = _torch
            import torch.nn as nn
            from transformers import Wav2Vec2Processor
            from transformers.models.wav2vec2.modeling_wav2vec2 import (
                Wav2Vec2Model,
                Wav2Vec2PreTrainedModel,
            )

            class RegressionHead(nn.Module):
                def __init__(self, config):
                    super().__init__()
                    self.dense    = nn.Linear(config.hidden_size, config.hidden_size)
                    self.dropout  = nn.Dropout(config.final_dropout)
                    self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

                def forward(self, features, **kwargs):
                    x = self.dropout(features)
                    x = self.dense(x)
                    x = _torch.tanh(x)
                    x = self.dropout(x)
                    return self.out_proj(x)

            class EmotionModel(Wav2Vec2PreTrainedModel):
                def __init__(self, config):
                    super().__init__(config)
                    self.wav2vec2   = Wav2Vec2Model(config)
                    self.classifier = RegressionHead(config)
                    self.init_weights()

                def forward(self, input_values):
                    hidden = self.wav2vec2(input_values)[0]
                    hidden = _torch.mean(hidden, dim=1)
                    return self.classifier(hidden)

            logger.info("[MMSA] Loading audeering dimensional audio model …")
            self.processor = Wav2Vec2Processor.from_pretrained(DIMENSIONAL_MODEL_NAME)
            self.model     = EmotionModel.from_pretrained(DIMENSIONAL_MODEL_NAME)
            self.model.eval()
            self._loaded = True
            logger.info("[MMSA] Dimensional model ready (outputs arousal/dominance/valence).")
            return True
        except Exception as e:
            logger.warning("[MMSA] Dimensional model unavailable: %s", e)
            return False

    def predict_vad(self, audio_path: str) -> np.ndarray:
        """
        Returns np.ndarray [valence, arousal, dominance] ∈ [0, 1].
        audeering model outputs [arousal, dominance, valence] — reordered here
        to match the [val, aro, dom] convention used everywhere else.
        """
        import librosa
        y, _ = librosa.load(audio_path, sr=16000)
        inputs = self.processor(y, sampling_rate=16000, return_tensors="pt", padding=True)
        with torch.no_grad():
            out = self.model(inputs.input_values)
        vad = torch.sigmoid(out).squeeze().numpy()  # [arousal, dominance, valence]
        # Reorder to [valence, arousal, dominance] for consistency with EMOTION_TO_VAD
        return np.array([vad[2], vad[0], vad[1]])


_dimensional_model = _DimensionalAudioModel() if _USE_DIMENSIONAL else None


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class MMSADissonanceEngine:
    """
    Tri-modal deception detection: Text × Audio × Video.
    Real features via DissonanceEngine (wav2vec2 + DistilBERT + prosody).
    """

    def __init__(self):
        self.model_name = "self_mm"
        self._vision_loaded = False
        self.landmarker = None
        self.dissonance_threshold = 0.4

        self.memory_path = os.path.join(
            os.path.dirname(__file__), "..", "cache", "emotional_baselines.json"
        )
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)

        self.guardian    = guardian_sensory
        self.scam_memory = scam_graph

        self.action_guidance = {
            "BLOCK":    "Immediate Risk: Block sender and do not respond. Save screenshot as evidence.",
            "WARN":     "Suspicious Journey: Pattern matches known scam scripts. Verify via official app.",
            "RESTRICT": "Potential Fraud: Dissonance and metadata conflicts. Do not share OTP.",
        }

        # Load optional dimensional model at startup
        if _USE_DIMENSIONAL and _dimensional_model:
            _dimensional_model.load()

    # ------------------------------------------------------------------
    # MediaPipe face landmarker (lazy)
    # ------------------------------------------------------------------
    def _lazy_load_vision(self) -> bool:
        global mp, tasks, vision, cv2, yt_dlp, static_ffmpeg
        if self._vision_loaded:
            return True
        try:
            import mediapipe as _mp
            from mediapipe.tasks import python as _tasks
            from mediapipe.tasks.python import vision as _vision
            import cv2 as _cv2
            import yt_dlp as _yt_dlp
            import static_ffmpeg as _sffmpeg
            from static_ffmpeg import run as _ffmpeg_run

            mp = _mp; tasks = _tasks; vision = _vision; cv2 = _cv2
            yt_dlp = _yt_dlp; static_ffmpeg = _ffmpeg_run

            model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
            if os.path.exists(model_path):
                base_opts = tasks.BaseOptions(model_asset_path=model_path)
                opts      = vision.FaceLandmarkerOptions(
                    base_options=base_opts,
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                    num_faces=1,
                )
                self.landmarker = vision.FaceLandmarker.create_from_options(opts)

            self._vision_loaded = True
            logger.info("[MMSA] Vision / MediaPipe sensors active.")
            return True
        except ImportError as e:
            logger.warning("[MMSA] Vision deps missing (%s); video analysis disabled.", e)
            return False
        except Exception as e:
            logger.error("[MMSA] Vision init failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Public: analyze file triplet
    # ------------------------------------------------------------------
    def analyze(
        self,
        audio_path: str,
        transcript: str,
        video_path: Optional[str] = None,
        video_id:   Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full tri-modal deception analysis.
        Real audio/text features from DissonanceEngine; MediaPipe for video.
        """
        start = time.time()

        # ── Guardian context ──────────────────────────────────────────
        intent_signals = self.guardian._detect_signals(transcript)
        entities       = self.guardian._extract_entities(transcript)
        journey_report = self.scam_memory.get_journey_score(entities)
        self.scam_memory.add_event("call_transcript", entities, intent_signals)

        # ── 1. Core cross-modal dissonance (REAL features) ────────────
        try:
            dissonance_result = dissonance_engine.analyze(
                audio_path, transcript, video_id=video_id
            )
        except Exception as e:
            # Dissonance engine models not loaded yet (cold start / no GPU)
            logger.warning("[MMSA] DissonanceEngine unavailable: %s — falling back.", e)
            dissonance_result = {
                "dissonance_score":       0.0,
                "audio_text_divergence":  0.0,
                "conflict_detected":      False,
                "likely_sarcasm":         False,
                "audio_dominant_emotion": "unknown",
                "text_dominant_emotion":  "unknown",
                "audio_vad":              [0.5, 0.5, 0.5],
                "text_vad":               [0.5, 0.5, 0.5],
                "prosody":                {},
                "fusion_contributions":   {},
                "dominant_modality":      "unavailable",
                "error":                  str(e),
            }

        final_score       = dissonance_result.get("dissonance_score", 0.0)
        audio_text_div    = dissonance_result.get("audio_text_divergence", 0.0)
        conflicts: Dict[str, float] = {"text_audio": round(audio_text_div, 4)}

        # ── 2. Optional dimensional audio override ────────────────────
        audio_vad = np.array(dissonance_result.get("audio_vad", [0.5, 0.5, 0.5]))
        text_vad  = np.array(dissonance_result.get("text_vad",  [0.5, 0.5, 0.5]))

        if _USE_DIMENSIONAL and _dimensional_model and _dimensional_model._loaded:
            try:
                dim_vad   = _dimensional_model.predict_vad(audio_path)
                import scipy.spatial.distance as _dist
                dim_div   = float(_dist.cosine(dim_vad, text_vad))
                if dim_div > audio_text_div:
                    final_score = max(final_score, dim_div)
                    conflicts["dimensional_audio_text"] = round(dim_div, 4)
                    logger.info("[MMSA] Dimensional model raised score to %.4f", final_score)
            except Exception as e:
                logger.warning("[MMSA] Dimensional model inference failed: %s", e)

        # ── 3. Video sentiment (MediaPipe face blendshapes) ───────────
        visual_sentiment = None
        if video_path and self._lazy_load_vision():
            try:
                visual_sentiment = self._extract_visual_sentiment(video_path)
                import scipy.spatial.distance as _dist
                vis_vad  = np.array([visual_sentiment, 0.5, 0.5])  # simplified
                div_tv   = float(_dist.cosine(text_vad,  vis_vad))
                div_av   = float(_dist.cosine(audio_vad, vis_vad))
                conflicts["text_visual"]  = round(div_tv, 4)
                conflicts["audio_visual"] = round(div_av, 4)
                final_score = max(final_score, div_tv, div_av)
            except Exception as e:
                logger.warning("[MMSA] Visual sentiment failed: %s", e)

        # ── 4. Deception meta-analysis ────────────────────────────────
        audio_score = dissonance_result.get("audio_vad", [0.5, 0.5, 0.5])[0]  # valence
        text_score  = dissonance_result.get("text_vad",  [0.5, 0.5, 0.5])[0]
        deception   = self._detect_deception(text_score, audio_score, visual_sentiment)

        # ── 5. Confidence assessment ──────────────────────────────────
        confidence  = self._calculate_confidence(transcript, audio_path, video_path)
        reliability = "HIGH" if confidence > 0.8 else "MEDIUM" if confidence > 0.5 else "LOW"

        is_dissonant = final_score > self.dissonance_threshold

        # ── 6. Guardian fusion ────────────────────────────────────────
        guardian_risk = journey_report["score"]
        if deception["leakage"] or final_score > 0.6:
            guardian_risk = min(100.0, guardian_risk + 30.0)

        action_key = (
            "BLOCK"    if guardian_risk >= 70
            else "WARN"    if guardian_risk >= 40
            else "RESTRICT" if is_dissonant
            else "ALLOW"
        )

        result: Dict[str, Any] = {
            # Core scores
            "dissonance_score":          round(final_score, 4),
            "audio_text_divergence":     round(audio_text_div, 4),
            "is_dissonant":              is_dissonant,
            "conflict_detected":         dissonance_result.get("conflict_detected", False),
            "likely_sarcasm":            dissonance_result.get("likely_sarcasm", False),
            # Confidence
            "confidence_score":          round(confidence, 2),
            "reliability_tier":          reliability,
            # Guardian
            "guardian_score":            round(guardian_risk, 2),
            "safe_action":               self.action_guidance.get(
                                             action_key, "No immediate threat detected. Stay vigilant."
                                         ),
            "scam_journey":              journey_report,
            # Deception
            "deception_probability":     deception["probability"],
            "emotional_leakage_detected": deception["leakage"],
            "analysis_tags":             deception["tags"],
            # VAD vectors
            "audio_vad":                 audio_vad.tolist(),
            "text_vad":                  text_vad.tolist(),
            # Modality breakdown
            "modality_scores": {
                "text":   round(text_score, 4),
                "audio":  round(audio_score, 4),
                "visual": round(visual_sentiment, 4) if visual_sentiment is not None else None,
            },
            "pairwise_conflicts":        conflicts,
            "dominant_modality":         dissonance_result.get("dominant_modality", "unknown"),
            "fusion_contributions":      dissonance_result.get("fusion_contributions", {}),
            # Prosody
            "prosody":                   dissonance_result.get("prosody", {}),
            # Raw emotion probs
            "audio_emotion_probs":       dissonance_result.get("audio_emotion_probs", {}),
            "text_emotion_probs":        dissonance_result.get("text_emotion_probs", {}),
            # Meta
            "framework":                 "DissonanceEngine(wav2vec2+DistilBERT+VAD) + ZeroTrust Guardian",
            "dimensional_model_used":    _USE_DIMENSIONAL and _dimensional_model and _dimensional_model._loaded,
            "duration_ms":               int((time.time() - start) * 1000),
            "source_url":                None,
        }

        self._update_cognitive_memory(result)
        logger.info(
            "[MMSA] Analysis done. score=%.4f  sarcasm=%s  deception=%.2f",
            final_score, result["likely_sarcasm"], deception["probability"],
        )
        return result

    # ------------------------------------------------------------------
    # Public: analyze URL (yt-dlp download)
    # ------------------------------------------------------------------
    def analyze_url(self, url: str, transcript: str) -> Dict[str, Any]:
        if not self._lazy_load_vision():
            # Vision optional; still run audio+text analysis if possible
            logger.warning("[MMSA] Vision unavailable; attempting audio-only URL analysis.")

        import tempfile, shutil
        from static_ffmpeg import run as ffmpeg_run

        tmp_dir         = tempfile.mkdtemp(prefix="janus_yt_")
        output_template = os.path.join(tmp_dir, "media.%(ext)s")
        ffmpeg_bin, _   = ffmpeg_run.get_or_fetch_platform_executables_else_raise()

        ydl_opts = {
            "format":              "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "outtmpl":             output_template,
            "merge_output_format": "mp4",
            "quiet":               True,
            "no_warnings":         True,
            "ffmpeg_location":     ffmpeg_bin,
        }

        try:
            logger.info("[MMSA] Ingesting URL: %s", url)
            import yt_dlp as _ytdlp
            with _ytdlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = os.listdir(tmp_dir)
            if not files:
                raise RuntimeError("Failed to download media from URL.")

            video_path = os.path.join(tmp_dir, files[0])
            audio_path = os.path.join(tmp_dir, "extracted_audio.wav")
            os.system(
                f"{ffmpeg_bin} -i {video_path} -ss 00:00:00 -t 00:01:00 "
                f"-vn -acodec pcm_s16le -ar 16000 -ac 1 {audio_path} -y"
            )

            # Derive stable video_id from URL
            import hashlib
            video_id = hashlib.md5(url.encode()).hexdigest()[:12]

            results = self.analyze(audio_path, transcript, video_path=video_path, video_id=video_id)
            results["source_url"] = url
            return results

        except Exception as e:
            logger.error("[MMSA] URL analysis failed: %s", e)
            return {"error": str(e)}
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _detect_deception(
        self, t: float, a: float, v: Optional[float]
    ) -> Dict[str, Any]:
        """Meta-analysis for deception using VAD-space emotional paradoxes."""
        prob  = 0.0
        tags  = []
        leakage = False

        # Rule 1: Sarcasm / Irony — high valence text, low valence audio
        if t > 0.6 and a < 0.35:
            prob += 0.4
            tags.append("Sarcasm/Irony Detected")

        # Rule 2: Emotional masking — positive face, negative voice
        if v is not None and v > 0.3 and a < 0.3:
            prob += 0.5
            leakage = True
            tags.append("Emotional Masking (Fake Expression)")

        # Rule 3: High-intensity paradox across all modalities
        div_ta = abs(t - a)
        div_tv = abs(t - (v or 0.5))
        if div_ta > 0.5 and div_tv > 0.5:
            prob += 0.3
            tags.append("High-Fidelity Cognitive Dissonance")

        return {
            "probability": min(1.0, round(prob, 2)),
            "leakage":     leakage,
            "tags":        tags,
        }

    def _extract_visual_sentiment(self, video_path: str) -> float:
        """Sample up to 15 frames with MediaPipe face blendshapes → mean valence proxy."""
        from mediapipe.tasks.python.vision.core.image import Image as MpImage
        cap = cv2.VideoCapture(video_path)
        sentiments = []
        frame_count = 0
        while cap.isOpened() and frame_count < 15:
            ret, frame = cap.read()
            if not ret:
                break
            mp_image = MpImage(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
            )
            result = self.landmarker.detect(mp_image)
            if result.face_blendshapes:
                sentiments.append(-0.4)  # placeholder until blendshape → valence mapping added
            frame_count += 1
        cap.release()
        return float(np.mean(sentiments)) if sentiments else 0.0

    def _calculate_confidence(
        self, transcript: str, a_path: str, v_path: Optional[str]
    ) -> float:
        score = 1.0
        words = transcript.split()
        if len(words) < 10:
            score -= 0.3
        elif len(words) < 20:
            score -= 0.1
        score -= 0.05  # baseline noise assumption
        if not v_path:
            score -= 0.1
        return max(0.0, min(1.0, score))

    def _update_cognitive_memory(self, result: Dict[str, Any]) -> None:
        try:
            memory: Dict = {}
            if os.path.exists(self.memory_path):
                with open(self.memory_path) as f:
                    memory = json.load(f)

            source = result.get("source_url") or "local_file"
            if source not in memory:
                memory[source] = []
            memory[source].append({
                "timestamp":  time.time(),
                "dissonance": result["dissonance_score"],
                "deception":  result["deception_probability"],
                "sarcasm":    result.get("likely_sarcasm", False),
                "tags":       result["analysis_tags"],
            })
            memory[source] = memory[source][-100:]

            with open(self.memory_path, "w") as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.warning("[MMSA] Memory update failed: %s", e)

    def calibrate(self) -> Dict[str, Any]:
        """Proxy calibration through DissonanceEngine."""
        dissonance_engine.refine_with_dataset()
        return {
            "status":    "calibrated",
            "threshold": dissonance_engine.dissonance_threshold,
            "timestamp": time.time(),
        }


# Singleton
mmsa_engine = MMSADissonanceEngine()
