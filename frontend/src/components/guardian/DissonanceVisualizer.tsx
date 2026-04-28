'use client';

import React, { useState, useRef } from 'react';
import { getApiBaseUrl } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, UploadCloud, AlertTriangle, ShieldCheck, Activity, Play, Pause, X, BarChart2 } from 'lucide-react';

interface VADSpace {
  valence: number;
  arousal: number;
  dominance: number;
}

interface AnalysisResult {
  dissonance_score: number;
  conflict_detected: boolean;
  likely_sarcasm: boolean;
  audio_dominant: string;
  text_dominant: string;
  contributions: {
    audio_text_div: number;
    prosody_boost: number;
    text_confidence_penalty: number;
  };
  audio_vad: number[];
  text_vad: number[];
  prosody: {
    pitch_mean: number;
    rms_energy: number;
    speech_rate: number;
  };
  error?: string;
}

export default function DissonanceVisualizer() {
  const [transcript, setTranscript] = useState('');
  const [audioFile, setAudioFile] = useState<File | Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioFile(audioBlob);
        setAudioUrl(URL.createObjectURL(audioBlob));
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setAudioFile(file);
      setAudioUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const resetState = () => {
    setAudioFile(null);
    setAudioUrl(null);
    setResult(null);
    setError(null);
    setTranscript('');
    setRecordingTime(0);
  };

  const analyzeDissonance = async () => {
    if (!audioFile) {
      setError('Please provide an audio recording.');
      return;
    }
    if (!transcript.trim()) {
      setError('Please provide a transcript.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    const formData = new FormData();
    // Use .webm extension for blob, or keep original file name
    formData.append('audio', audioFile, audioFile instanceof File ? audioFile.name : 'recording.webm');
    formData.append('transcript', transcript);

    try {
      const res = await fetch(`${getApiBaseUrl()}/finance/analyze/emotion-conflict`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Analysis failed');
      }

      const data: AnalysisResult = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8 pb-24">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
          <Mic className="w-6 h-6 text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-light text-white tracking-wide">MMSA Deception Radar</h1>
          <p className="text-sm text-gray-400 mt-1">Cross-Modal Emotion Conflict Engine</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input Section */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-[#111118] border border-white/[0.05] rounded-2xl p-6 shadow-2xl relative overflow-hidden">
            <h2 className="text-sm font-medium text-gray-300 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" /> Audio Intake
            </h2>
            
            {!audioFile ? (
              <div className="space-y-4">
                <div className="flex justify-center">
                  {isRecording ? (
                    <div className="flex flex-col items-center gap-4">
                      <div className="relative">
                        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center animate-pulse">
                          <button
                            onClick={stopRecording}
                            className="w-14 h-14 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white transition-all shadow-[0_0_20px_rgba(239,68,68,0.4)]"
                          >
                            <Square className="w-6 h-6 fill-current" />
                          </button>
                        </div>
                      </div>
                      <div className="text-xl font-mono text-red-400 tracking-wider">
                        {formatTime(recordingTime)}
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={startRecording}
                      className="w-20 h-20 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-full flex items-center justify-center text-indigo-400 transition-all hover:scale-105"
                    >
                      <Mic className="w-8 h-8" />
                    </button>
                  )}
                </div>
                
                {!isRecording && (
                  <div className="text-center">
                    <p className="text-xs text-gray-500 mb-3">OR</p>
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={handleFileUpload}
                      ref={fileInputRef}
                      className="hidden"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.05] rounded-lg text-sm text-gray-300 transition-all"
                    >
                      <UploadCloud className="w-4 h-4" /> Upload Audio File
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-white/[0.02] border border-white/[0.05] rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-500/20 rounded-full flex items-center justify-center">
                      <Mic className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-200">Audio Captured</p>
                      {audioUrl && <audio src={audioUrl} controls className="h-8 mt-2 w-full max-w-[200px]" />}
                    </div>
                  </div>
                  <button onClick={resetState} className="p-2 text-gray-500 hover:text-red-400 transition-colors">
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="bg-[#111118] border border-white/[0.05] rounded-2xl p-6 shadow-2xl relative overflow-hidden flex-1 flex flex-col">
            <h2 className="text-sm font-medium text-gray-300 uppercase tracking-widest mb-4">
              Transcript
            </h2>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Enter the exact spoken words to compare against the vocal tone..."
              className="w-full bg-black/40 border border-white/[0.1] rounded-xl p-4 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 resize-none flex-1 min-h-[150px]"
            />
            
            {error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2 text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <p>{error}</p>
              </div>
            )}

            <button
              onClick={analyzeDissonance}
              disabled={!audioFile || !transcript.trim() || isAnalyzing}
              className={`mt-4 w-full py-3 rounded-xl flex items-center justify-center gap-2 font-medium transition-all ${
                !audioFile || !transcript.trim() || isAnalyzing
                  ? 'bg-white/[0.05] text-gray-500 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_15px_rgba(79,70,229,0.4)]'
              }`}
            >
              {isAnalyzing ? (
                <>
                  <Activity className="w-5 h-5 animate-pulse" /> Processing Audio Tensor...
                </>
              ) : (
                'Compute Dissonance'
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        <div className="lg:col-span-7">
          <AnimatePresence mode="wait">
            {isAnalyzing ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full bg-[#111118] border border-white/[0.05] rounded-2xl flex flex-col items-center justify-center p-12 relative overflow-hidden min-h-[500px]"
              >
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(79,70,229,0.15)_0%,transparent_70%)] opacity-50 animate-pulse" />
                <div className="relative w-32 h-32 mb-8 flex items-center justify-center">
                  <div className="absolute inset-0 border-t-2 border-indigo-500 rounded-full animate-spin [animation-duration:1.5s]" />
                  <div className="absolute inset-2 border-r-2 border-purple-500 rounded-full animate-spin [animation-duration:2s] [animation-direction:reverse]" />
                  <div className="absolute inset-4 border-b-2 border-emerald-500 rounded-full animate-spin [animation-duration:3s]" />
                  <Activity className="w-8 h-8 text-indigo-400 animate-pulse" />
                </div>
                <h3 className="text-lg font-light text-gray-200 tracking-wider">Extracting wav2vec2 prosody...</h3>
                <p className="text-sm text-gray-500 mt-2">Projecting modalities into VAD space</p>
              </motion.div>
            ) : result ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Verdict Banner */}
                <div className={`p-6 rounded-2xl border flex items-center gap-4 ${
                  result.conflict_detected 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-emerald-500/10 border-emerald-500/30'
                }`}>
                  <div className={`p-3 rounded-full ${
                    result.conflict_detected ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {result.conflict_detected ? <AlertTriangle className="w-8 h-8" /> : <ShieldCheck className="w-8 h-8" />}
                  </div>
                  <div>
                    <h2 className={`text-2xl font-semibold tracking-wide ${
                      result.conflict_detected ? 'text-red-400' : 'text-emerald-400'
                    }`}>
                      {result.likely_sarcasm ? 'High Probability Sarcasm/Irony' : 
                       result.conflict_detected ? 'Emotional Dissonance Detected' : 'Signals Aligned'}
                    </h2>
                    <p className="text-gray-400 mt-1">
                      {result.conflict_detected 
                        ? 'Audio tone significantly conflicts with text transcript sentiment.' 
                        : 'Audio delivery matches the semantic meaning of the text.'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Gauge */}
                  <div className="bg-[#111118] border border-white/[0.05] rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center">
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-6 w-full text-left">Divergence Score</h3>
                    <div className="relative w-48 h-48 flex items-center justify-center">
                      <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                        <circle cx="96" cy="96" r="80" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
                        <circle 
                          cx="96" cy="96" r="80" fill="none" 
                          stroke={result.conflict_detected ? '#ef4444' : '#10b981'} 
                          strokeWidth="12" 
                          strokeDasharray="502" 
                          strokeDashoffset={502 - (502 * Math.min(result.dissonance_score, 1))} 
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <div className="text-center">
                        <span className="text-4xl font-light text-white">{(result.dissonance_score).toFixed(2)}</span>
                        <p className="text-xs text-gray-500 mt-1">Cosine Distance</p>
                      </div>
                    </div>
                  </div>

                  {/* Dominant Emotions */}
                  <div className="bg-[#111118] border border-white/[0.05] rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-4">Detected Sentiments</h3>
                    
                    <div className="space-y-6">
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span className="text-gray-300 flex items-center gap-2"><Mic className="w-4 h-4"/> Audio Tone</span>
                          <span className="text-indigo-400 font-medium uppercase">{result.audio_dominant}</span>
                        </div>
                        <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden">
                          <div className="h-full bg-indigo-500 w-full" />
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span className="text-gray-300 flex items-center gap-2"><Square className="w-4 h-4"/> Transcript Meaning</span>
                          <span className="text-purple-400 font-medium uppercase">{result.text_dominant}</span>
                        </div>
                        <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 w-full" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* VAD Space Visualization */}
                <div className="bg-[#111118] border border-white/[0.05] rounded-2xl p-6 shadow-xl">
                  <h3 className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-6">3D VAD Space Projection</h3>
                  
                  <div className="space-y-5">
                    {[
                      { label: 'Valence (Negative → Positive)', idx: 0 },
                      { label: 'Arousal (Calm → Excited)', idx: 1 },
                      { label: 'Dominance (Submissive → Dominant)', idx: 2 }
                    ].map((dim) => (
                      <div key={dim.label} className="relative">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>{dim.label.split(' ')[0]}</span>
                        </div>
                        <div className="h-6 w-full bg-white/[0.03] border border-white/[0.05] rounded-lg relative">
                          {/* Center line */}
                          <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/[0.1]" />
                          
                          {/* Audio marker */}
                          <div 
                            className="absolute top-1 bottom-1 w-3 bg-indigo-500 rounded shadow-[0_0_8px_rgba(99,102,241,0.6)] z-10 transition-all duration-1000"
                            style={{ left: `calc(${result.audio_vad[dim.idx] * 100}% - 6px)` }}
                            title={`Audio: ${result.audio_vad[dim.idx].toFixed(2)}`}
                          />
                          
                          {/* Text marker */}
                          <div 
                            className="absolute top-2 bottom-2 w-2 bg-purple-500 rounded shadow-[0_0_8px_rgba(168,85,247,0.6)] z-20 transition-all duration-1000"
                            style={{ left: `calc(${result.text_vad[dim.idx] * 100}% - 4px)` }}
                            title={`Text: ${result.text_vad[dim.idx].toFixed(2)}`}
                          />
                        </div>
                      </div>
                    ))}
                    
                    <div className="flex justify-end gap-4 mt-4 pt-4 border-t border-white/[0.05]">
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <div className="w-3 h-3 bg-indigo-500 rounded-sm" /> Audio Embedding
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <div className="w-3 h-3 bg-purple-500 rounded-sm" /> Text Embedding
                      </div>
                    </div>
                  </div>
                </div>

              </motion.div>
            ) : (
              <div className="h-full bg-[#111118]/50 border border-white/[0.02] rounded-2xl flex flex-col items-center justify-center p-12 text-center border-dashed min-h-[500px]">
                <BarChart2 className="w-16 h-16 text-gray-700 mb-4" />
                <h3 className="text-xl font-light text-gray-500">Awaiting Modalities</h3>
                <p className="text-sm text-gray-600 mt-2 max-w-sm">
                  Record or upload audio and provide a transcript to project vectors into the emotional dissonance space.
                </p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
