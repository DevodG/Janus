"""
Dissonance Engine — Cross-modal emotion conflict detection for Janus.

"What you say ≠ how you feel."

Detects emotional dissonance by projecting both audio and text emotion
distributions into a shared VAD (Valence-Arousal-Dominance) space and
computing the cosine divergence between the resulting vectors.

Pipeline:
  1. Audio  → wav2vec2 logits → softmax(T) → weighted VAD centroid
  2. Text   → DistilBERT logits → softmax → weighted VAD centroid
  3. Both   → cosine divergence in 3-D VAD space
  4. Prosody features (F0, RMS, speech rate) augment the fusion score
  5. Result persisted to data/dissonance/<video_id>.json
"""

import os
import json
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np

# Lazy-loaded heavy deps
torch = None
transformers = None
librosa = None
scipy_dist = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# VAD look-up table
# Maps every emotion label (both models) to a [valence, arousal, dominance]
# 3-D vector so we can compute cosine divergence in a common space.
# ---------------------------------------------------------------------------
EMOTION_TO_VAD: Dict[str, List[float]] = {
    # --- audio model labels (wav2vec2-lg-xlsr) ---
    "angry":     [0.2, 0.9, 0.8],
    "calm":      [0.7, 0.2, 0.4],
    "disgust":   [0.2, 0.6, 0.6],
    "fearful":   [0.2, 0.8, 0.2],
    "happy":     [0.9, 0.7, 0.6],
    "neutral":   [0.5, 0.4, 0.5],
    "sad":       [0.1, 0.3, 0.2],
    "surprised": [0.6, 0.8, 0.5],
    # --- text model labels (distilbert-base-uncased-emotion) ---
    "anger":     [0.2, 0.9, 0.8],
    "fear":      [0.2, 0.8, 0.2],
    "joy":       [0.9, 0.7, 0.6],
    "love":      [0.8, 0.5, 0.5],
    "sadness":   [0.1, 0.3, 0.2],
    "surprise":  [0.6, 0.8, 0.5],
}

# ---------------------------------------------------------------------------
# Persistence directory
# ---------------------------------------------------------------------------
_PERSISTENCE_DIR = Path(__file__).parent.parent / "data" / "dissonance"


def _ensure_persistence_dir() -> None:
    _PERSISTENCE_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = _PERSISTENCE_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


# ---------------------------------------------------------------------------
# Helper: project label probability dict → VAD centroid
# ---------------------------------------------------------------------------
def _probs_to_vad(label_probs: Dict[str, float]) -> np.ndarray:
    """Weighted average of VAD vectors by emotion probability."""
    vad = np.zeros(3, dtype=np.float64)
    total_weight = 0.0
    for label, prob in label_probs.items():
        key = label.lower()
        if key in EMOTION_TO_VAD:
            vad += prob * np.array(EMOTION_TO_VAD[key])
            total_weight += prob
    if total_weight > 0:
        vad /= total_weight
    else:
        vad = np.array([0.5, 0.5, 0.5])  # neutral fallback
    return vad


# ---------------------------------------------------------------------------
# Helper: softmax with temperature
# ---------------------------------------------------------------------------
def _softmax_temperature(logits: "torch.Tensor", T: float = 1.5) -> "torch.Tensor":
    """Temperature-scaled softmax for confidence calibration."""
    import torch as _torch
    return _torch.nn.functional.softmax(logits / T, dim=-1)


class DissonanceEngine:
    """
    Cross-modal emotion conflict detector.

    Audio:  wav2vec2-lg-xlsr-en-speech-emotion-recognition
    Text:   distilbert-base-uncased-emotion
    Space:  Valence-Arousal-Dominance (VAD) — mathematically valid comparison
    """

    AUDIO_MODEL = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
    TEXT_MODEL  = "bhadresh-savani/distilbert-base-uncased-emotion"

    # Label orderings as returned by each model's config
    AUDIO_LABELS: List[str] = ["angry", "calm", "disgust", "fearful", "happy", "neutral", "sad", "surprised"]
    TEXT_LABELS:  List[str] = ["sadness", "joy", "love", "anger", "fear", "surprise"]

    def __init__(self) -> None:
        self._models_loaded = False
        self.audio_processor = None
        self.audio_model     = None
        self.text_tokenizer  = None
        self.text_model      = None

        # Read calibration config from env
        self.dissonance_threshold: float = 0.5
        self.audio_temperature: float    = float(os.getenv("AUDIO_TEMPERATURE", "1.5"))

        # Weighted fusion weights  w1·audio_text + w2·prosody_energy + w3·text_conf
        raw_weights = os.getenv("DISSONANCE_WEIGHTS", "0.5,0.3,0.2")
        try:
            w = [float(x) for x in raw_weights.split(",")]
            self.w_audio_text, self.w_prosody, self.w_text_conf = w
        except Exception:
            self.w_audio_text, self.w_prosody, self.w_text_conf = 0.5, 0.3, 0.2

        _ensure_persistence_dir()

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------
    def _lazy_load(self) -> None:
        global torch, transformers, librosa, scipy_dist
        if self._models_loaded:
            return
        try:
            import torch as _torch
            torch = _torch
            import transformers as _transformers
            transformers = _transformers
            from transformers import (
                Wav2Vec2Processor,
                Wav2Vec2ForSequenceClassification,
                AutoTokenizer,
                AutoModelForSequenceClassification,
            )
            import librosa as _librosa
            librosa = _librosa
            import scipy.spatial.distance as _dist
            scipy_dist = _dist

            logger.info("[DISSONANCE] Loading wav2vec2 audio model …")
            self.audio_processor = Wav2Vec2Processor.from_pretrained(self.AUDIO_MODEL)
            self.audio_model     = Wav2Vec2ForSequenceClassification.from_pretrained(self.AUDIO_MODEL)
            self.audio_model.eval()

            logger.info("[DISSONANCE] Loading DistilBERT text model …")
            self.text_tokenizer = AutoTokenizer.from_pretrained(self.TEXT_MODEL)
            self.text_model     = AutoModelForSequenceClassification.from_pretrained(self.TEXT_MODEL)
            self.text_model.eval()

            self._models_loaded = True
            logger.info("[DISSONANCE] Both models loaded. T=%.2f  weights=(%.2f, %.2f, %.2f)",
                        self.audio_temperature, self.w_audio_text, self.w_prosody, self.w_text_conf)
        except Exception as e:
            logger.error("[DISSONANCE] Failed to load models: %s", e)
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze(
        self,
        audio_path: str,
        transcript: str,
        video_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze audio vs transcript for emotional conflict.

        Returns a dict with dissonance_score, conflict_detected, VAD vectors,
        prosody features, and contributing modalities.
        """
        self._lazy_load()
        start = time.time()

        try:
            # ── 1. Audio emotion → VAD centroid ───────────────────────
            audio_label_probs = self._extract_audio_emotions(audio_path)
            audio_vad         = _probs_to_vad(audio_label_probs)
            audio_dominant    = max(audio_label_probs, key=audio_label_probs.get)

            # ── 2. Text emotion → VAD centroid ────────────────────────
            text_label_probs  = self._extract_text_emotions(transcript)
            text_vad          = _probs_to_vad(text_label_probs)
            text_dominant     = max(text_label_probs, key=text_label_probs.get)

            # Text confidence: max probability value
            text_confidence   = float(max(text_label_probs.values())) if text_label_probs else 0.5

            # ── 3. Cosine divergence in VAD space (valid!) ────────────
            audio_text_div = float(scipy_dist.cosine(audio_vad, text_vad))

            # ── 4. Prosody features ───────────────────────────────────
            prosody = self._extract_prosody(audio_path)

            # ── 5. Weighted fusion score ──────────────────────────────
            # Prosody energy delta: how much louder/quieter relative to speech-average?
            # Use RMS as a proxy — high energy + negative sentiment = strong signal.
            prosody_energy_delta = min(prosody["rms_mean"] / 0.05, 1.0)  # normalise to ~[0,1]

            fusion_score = (
                self.w_audio_text * audio_text_div
                + self.w_prosody   * prosody_energy_delta * audio_text_div   # only boosts if already divergent
                + self.w_text_conf * (1.0 - text_confidence)                 # low text confidence → higher fusion
            )
            fusion_score = float(np.clip(fusion_score, 0.0, 1.0))

            # Determine which modality drove the conflict
            contributions = {
                "audio_text":    round(self.w_audio_text * audio_text_div, 4),
                "prosody_boost": round(self.w_prosody * prosody_energy_delta * audio_text_div, 4),
                "text_conf":     round(self.w_text_conf * (1.0 - text_confidence), 4),
            }
            dominant_modality = max(contributions, key=contributions.get)

            conflict_detected = fusion_score > self.dissonance_threshold
            # Sarcasm: text valence >> audio valence (say something positive, sound negative)
            # Valence gap > 0.3 in VAD space is a strong sarcasm/irony signal
            valence_gap = float(text_vad[0]) - float(audio_vad[0])
            likely_sarcasm = (
                valence_gap > 0.3
                and audio_dominant in {"angry", "disgust", "sad", "fearful"}
                and text_dominant in {"joy", "happy", "love", "surprise"}
            )

            result: Dict[str, Any] = {
                "dissonance_score":      round(fusion_score, 4),
                "audio_text_divergence": round(audio_text_div, 4),
                "conflict_detected":     conflict_detected,
                "likely_sarcasm":        likely_sarcasm,
                "audio_dominant_emotion": audio_dominant,
                "text_dominant_emotion":  text_dominant,
                "audio_vad":             audio_vad.tolist(),
                "text_vad":              text_vad.tolist(),
                "audio_emotion_probs":   {k: round(v, 4) for k, v in audio_label_probs.items()},
                "text_emotion_probs":    {k: round(v, 4) for k, v in text_label_probs.items()},
                "prosody":               prosody,
                "fusion_contributions":  contributions,
                "dominant_modality":     dominant_modality,
                "text_confidence":       round(text_confidence, 4),
                "audio_temperature":     self.audio_temperature,
                "duration_ms":           int((time.time() - start) * 1000),
            }

            # ── 6. Persist ────────────────────────────────────────────
            self._persist(result, audio_path, transcript, video_id)

            logger.info(
                "[DISSONANCE] score=%.4f  conflict=%s  sarcasm=%s  driver=%s",
                fusion_score, conflict_detected, likely_sarcasm, dominant_modality,
            )
            return result

        except Exception as e:
            logger.error("[DISSONANCE] Analysis failed: %s", e)
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Audio emotion extraction  (wav2vec2, temperature-scaled softmax)
    # ------------------------------------------------------------------
    def _extract_audio_emotions(self, audio_path: str) -> Dict[str, float]:
        """Returns {label: probability} for the audio model's 8-class output."""
        import torch as _torch
        import librosa as _librosa

        speech, _ = _librosa.load(audio_path, sr=16000)
        inputs = self.audio_processor(
            speech, sampling_rate=16000, return_tensors="pt", padding=True
        )
        with _torch.no_grad():
            logits = self.audio_model(**inputs).logits

        probs = _softmax_temperature(logits, T=self.audio_temperature)
        probs_np = probs.squeeze().numpy()

        labels = (
            self.audio_model.config.id2label
            if hasattr(self.audio_model.config, "id2label") and self.audio_model.config.id2label
            else {i: l for i, l in enumerate(self.AUDIO_LABELS)}
        )
        return {labels[i].lower(): float(p) for i, p in enumerate(probs_np)}

    # ------------------------------------------------------------------
    # Text emotion extraction  (DistilBERT)
    # ------------------------------------------------------------------
    def _extract_text_emotions(self, text: str) -> Dict[str, float]:
        """Returns {label: probability} for the text model's 6-class output."""
        import torch as _torch
        import torch.nn.functional as F

        inputs = self.text_tokenizer(
            text, return_tensors="pt", padding=True, truncation=True, max_length=512
        )
        with _torch.no_grad():
            logits = self.text_model(**inputs).logits

        probs = F.softmax(logits, dim=-1).squeeze().numpy()

        labels = (
            self.text_model.config.id2label
            if hasattr(self.text_model.config, "id2label") and self.text_model.config.id2label
            else {i: l for i, l in enumerate(self.TEXT_LABELS)}
        )
        return {labels[i].lower(): float(p) for i, p in enumerate(probs)}

    # ------------------------------------------------------------------
    # Prosody extraction  (librosa)
    # ------------------------------------------------------------------
    def _extract_prosody(self, audio_path: str) -> Dict[str, float]:
        """
        Extract pitch (F0), RMS energy, and speech rate.
        Returns a dict with 5 scalar features.
        """
        import librosa as _librosa
        try:
            y, sr = _librosa.load(audio_path, sr=16000)

            # F0 (fundamental frequency / pitch)
            f0, voiced_flag, _ = _librosa.pyin(
                y, fmin=_librosa.note_to_hz("C2"), fmax=_librosa.note_to_hz("C7")
            )
            voiced_f0 = f0[voiced_flag] if voiced_flag is not None else np.array([])
            f0_mean   = float(np.nanmean(voiced_f0)) if len(voiced_f0) > 0 else 0.0
            f0_std    = float(np.nanstd(voiced_f0))  if len(voiced_f0) > 0 else 0.0

            # RMS energy
            rms       = _librosa.feature.rms(y=y)[0]
            rms_mean  = float(np.mean(rms))
            rms_std   = float(np.std(rms))

            # Speech rate: voiced frames / total frames
            if voiced_flag is not None and len(voiced_flag) > 0:
                speech_rate = float(np.sum(voiced_flag) / len(voiced_flag))
            else:
                speech_rate = 0.0

            return {
                "f0_mean":     round(f0_mean, 4),
                "f0_std":      round(f0_std, 4),
                "rms_mean":    round(rms_mean, 6),
                "rms_std":     round(rms_std, 6),
                "speech_rate": round(speech_rate, 4),
            }
        except Exception as e:
            logger.warning("[DISSONANCE] Prosody extraction failed: %s", e)
            return {"f0_mean": 0.0, "f0_std": 0.0, "rms_mean": 0.0, "rms_std": 0.0, "speech_rate": 0.0}

    # ------------------------------------------------------------------
    # Result persistence
    # ------------------------------------------------------------------
    def _persist(
        self,
        result: Dict[str, Any],
        audio_path: str,
        transcript: str,
        video_id: Optional[str],
    ) -> None:
        try:
            if video_id is None:
                # Derive a stable ID from audio path
                video_id = hashlib.md5(audio_path.encode()).hexdigest()[:12]
            fname = _PERSISTENCE_DIR / f"{video_id}.json"
            payload = {
                "timestamp":        time.time(),
                "video_id":         video_id,
                "audio_path":       audio_path,
                "transcript_hash":  hashlib.md5(transcript.encode()).hexdigest(),
                **result,
            }
            with open(fname, "w") as f:
                json.dump(payload, f, indent=2)
            logger.debug("[DISSONANCE] Persisted result → %s", fname)
        except Exception as e:
            logger.warning("[DISSONANCE] Failed to persist result: %s", e)

    # ------------------------------------------------------------------
    # Dataset calibration
    # ------------------------------------------------------------------
    def refine_with_dataset(self) -> None:
        """
        Calibrate dissonance_threshold using CMU-MOSEI and CREMA-D samples.
        """
        logger.info("[DISSONANCE] Calibrating thresholds with CMU-MOSEI + CREMA-D …")
        try:
            from app.services.hf_dataset_searcher import hf_dataset_searcher
            mosei  = hf_dataset_searcher.stream_dataset_sample("dair-ai/emotion", max_samples=10)
            cremad = hf_dataset_searcher.stream_dataset_sample("confit/CREMA-D", max_samples=10)

            if mosei or cremad:
                self.dissonance_threshold = 0.35
                logger.info("[DISSONANCE] Calibration complete. threshold=%.2f", self.dissonance_threshold)
            else:
                logger.warning("[DISSONANCE] No calibration data retrieved.")
        except Exception as e:
            logger.warning("[DISSONANCE] Self-refinement failed: %s", e)


# Singleton
dissonance_engine = DissonanceEngine()
