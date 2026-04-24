'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, Zap, MessageSquare, Link as LinkIcon, 
  FileText, Upload, Brain, Activity, AlertTriangle,
  ChevronRight, RefreshCw, Eye, Bot, Layers
} from 'lucide-react';
import { apiClient, getApiBaseUrl } from '@/lib/api';

/* ═══════════════════════════════════════════════════════════
   SAFETY GATEWAY — Forensic Evidence & MMSA Intake
   ═══════════════════════════════════════════════════════════ */

interface AnalysisResult {
  id: string;
  type: 'text' | 'link' | 'file';
  input: string;
  is_scam: boolean;
  risk_score: number;
  reason: string;
  safe_action: string;
  details: any;
  timestamp: string;
}

export default function SafetyGateway() {
  const [activeTab, setActiveTab] = useState<'text' | 'link' | 'file'>('text');
  const [inputText, setInputText] = useState('');
  const [inputUrl, setInputUrl] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalysisResult[]>([]);

  const handleAnalyzeText = async () => {
    if (!inputText.trim()) return;
    setIsAnalyzing(true);
    try {
      // We use the general analyze endpoint but force a high-diligence report
      const res = await apiClient.run(inputText, { mode: 'forensic', source: 'manual_intake' });
      
      const newResult: AnalysisResult = {
        id: `res-${Date.now()}`,
        type: 'text',
        input: inputText,
        is_scam: (res.final?.confidence ?? 0) > 0.6,
        risk_score: res.final?.confidence ?? 0,
        reason: res.final_answer || 'Analysis complete.',
        safe_action: res.guardian?.safe_action || 'Double-check before proceeding.',
        details: res,
        timestamp: new Date().toISOString()
      };
      setResults([newResult, ...results]);
      setInputText('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyzeUrl = async () => {
    if (!inputUrl.trim()) return;
    setIsAnalyzing(true);
    const baseUrl = getApiBaseUrl();
    try {
      const res = await fetch(`${baseUrl}/guardian/analyze/url?url=${encodeURIComponent(inputUrl)}`, {
        method: 'POST'
      }).then(r => r.json());
      
      const newResult: AnalysisResult = {
        id: `res-${Date.now()}`,
        type: 'link',
        input: inputUrl,
        is_scam: res.risk_score > 0.6,
        risk_score: res.risk_score,
        reason: res.reason,
        safe_action: res.safe_action,
        details: res.details,
        timestamp: new Date().toISOString()
      };
      setResults([newResult, ...results]);
      setInputUrl('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsAnalyzing(true);
    setUploadProgress(10);
    const baseUrl = getApiBaseUrl();
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadProgress(40);
      const res = await fetch(`${baseUrl}/guardian/analyze/file`, {
        method: 'POST',
        body: formData
      }).then(r => r.json());
      
      setUploadProgress(100);
      const newResult: AnalysisResult = {
        id: `res-${Date.now()}`,
        type: 'file',
        input: file.name,
        is_scam: res.risk_score > 0.6,
        risk_score: res.risk_score,
        reason: res.reason,
        safe_action: res.safe_action,
        details: res.details,
        timestamp: new Date().toISOString()
      };
      setResults([newResult, ...results]);
    } catch (err) {
      console.error(err);
    } finally {
      setTimeout(() => {
        setIsAnalyzing(false);
        setUploadProgress(0);
      }, 500);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-[#0a0a0f]">
      <div className="max-w-[1400px] mx-auto px-6 py-8 relative">
        
        {/* ── Background decoration ── */}
        <div className="fixed top-0 left-1/2 -translate-x-1/2 w-full h-[500px] bg-gradient-to-b from-indigo-500/5 to-transparent pointer-events-none" />
        <div className="fixed bottom-0 left-0 w-full h-[1px] bg-indigo-500/10" />

        <header className="flex items-center justify-between mb-10 relative z-10">
          <div className="flex items-center gap-5">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.1)]">
              <Zap size={24} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-3xl font-light tracking-[0.2em] text-gradient uppercase">Safety Gateway</h1>
              <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-1">Multi-agent Forensic & Dissonance Engine</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <Activity size={14} className="text-indigo-400 animate-pulse" />
            <span className="text-[10px] font-mono text-indigo-400/80 uppercase tracking-widest">Active Guard</span>
          </div>
        </header>

        <div className="grid grid-cols-12 gap-8 relative z-10">
          {/* LEFT: Intake Terminal */}
          <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
            <section className="glass rounded-3xl p-8 border-white/[0.04]">
              <h2 className="text-xs font-mono text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                <Shield size={14} className="text-indigo-400" /> Forensic Evidence Intake
              </h2>

              <nav className="flex gap-1 mb-8 bg-black/40 p-1 rounded-2xl">
                {[
                  { id: 'text', label: 'SMS / Chat', icon: MessageSquare },
                  { id: 'link', label: 'URL / YT', icon: LinkIcon },
                  { id: 'file', label: 'File / Pic', icon: FileText },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl transition-all duration-300 text-[10px] uppercase font-mono tracking-widest ${
                      activeTab === tab.id ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'text-gray-500 hover:bg-white/[0.05]'
                    }`}
                  >
                    <tab.icon size={13} />
                    {tab.label}
                  </button>
                ))}
              </nav>

              <div className="space-y-6">
                {activeTab === 'text' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                    <textarea 
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      placeholder="Paste suspicious SMS, email, or chat text here..."
                      className="w-full h-40 bg-black/40 border border-white/[0.08] rounded-2xl p-5 text-[13px] text-gray-200 placeholder-gray-700 focus:outline-none focus:border-indigo-500/30 transition-all resize-none"
                    />
                    <button 
                      onClick={handleAnalyzeText}
                      disabled={isAnalyzing || !inputText.trim()}
                      className="w-full py-4 rounded-2xl bg-indigo-600/90 hover:bg-indigo-500 text-white font-mono text-xs uppercase tracking-widest transition-all shadow-[0_4px_20px_rgba(79,70,229,0.2)] disabled:opacity-50"
                    >
                      {isAnalyzing ? <RefreshCw size={14} className="animate-spin mx-auto" /> : 'Execute Text Forensics'}
                    </button>
                  </motion.div>
                )}

                {activeTab === 'link' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                    <div className="relative">
                      <LinkIcon size={16} className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600" />
                      <input 
                        type="url"
                        value={inputUrl}
                        onChange={(e) => setInputUrl(e.target.value)}
                        placeholder="Paste URL or YouTube link..."
                        className="w-full h-14 bg-black/40 border border-white/[0.08] rounded-2xl pl-12 pr-5 text-[13px] text-gray-200 placeholder-gray-700 focus:outline-none focus:border-indigo-500/30 transition-all"
                      />
                    </div>
                    <button 
                      onClick={handleAnalyzeUrl}
                      disabled={isAnalyzing || !inputUrl.trim()}
                      className="w-full py-4 rounded-2xl bg-indigo-600/90 hover:bg-indigo-500 text-white font-mono text-xs uppercase tracking-widest transition-all shadow-[0_4px_20px_rgba(79,70,229,0.2)] disabled:opacity-50"
                    >
                      {isAnalyzing ? <RefreshCw size={14} className="animate-spin mx-auto" /> : 'Probe Link Dissonance'}
                    </button>
                    <p className="text-[10px] font-mono text-gray-600 text-center uppercase tracking-widest px-4">
                      Janus will scan headers, domain age, and audio-visual dissonance patterns.
                    </p>
                  </motion.div>
                )}

                {activeTab === 'file' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 text-center">
                    <label className="block w-full border-2 border-dashed border-white/5 hover:border-indigo-500/20 hover:bg-indigo-500/[0.02] rounded-3xl p-12 transition-all cursor-pointer group">
                      <input type="file" onChange={handleFileUpload} className="hidden" accept="image/*,application/pdf" />
                      <div className="w-16 h-16 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                        <Upload size={24} className="text-gray-500 group-hover:text-indigo-400" />
                      </div>
                      <p className="text-xs font-mono text-gray-400 uppercase tracking-widest">Select Evidence File</p>
                      <p className="text-[9px] font-mono text-gray-600 mt-2">Screenshots, PDF Documents (Scanned/Native)</p>
                    </label>
                    {isAnalyzing && uploadProgress > 0 && (
                      <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                        <motion.div className="h-full bg-indigo-500" initial={{ width: 0 }} animate={{ width: `${uploadProgress}%` }} />
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </section>

            <section className="glass rounded-3xl p-6 border-white/[0.04]">
              <div className="flex items-center gap-3 mb-4">
                <Brain size={18} className="text-violet-400" />
                <h3 className="text-xs font-mono text-gray-300 uppercase tracking-widest">Active Intelligence</h3>
              </div>
              <p className="text-xs font-mono text-gray-500 leading-relaxed">
                Evidence submitted through the Safety Gateway is link-processed through the **ZeroTrust Scam Journey Graph**. If matched against historical dissonance patterns, the signal is squashed and reported globally.
              </p>
            </section>
          </div>

          {/* RIGHT: Analysis Logs */}
          <div className="col-span-12 lg:col-span-7 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <Layers size={14} className="text-indigo-400" /> Live Analysis Report
              </h2>
              <span className="text-[9px] font-mono text-gray-600 uppercase tracking-widest">{results.length} Artifacts processed</span>
            </div>

            <div className="space-y-4">
              <AnimatePresence>
                {results.length === 0 ? (
                  <motion.div 
                    initial={{ opacity: 0 }} 
                    animate={{ opacity: 1 }} 
                    className="flex flex-col items-center justify-center py-20 text-center glass rounded-3xl"
                  >
                    <Eye size={30} className="text-white/10 mb-4" />
                    <p className="text-[10px] font-mono text-gray-700 uppercase tracking-widest">Awaiting Evidence Ingestion...</p>
                  </motion.div>
                ) : (
                  results.map((res, i) => (
                    <motion.div
                      key={res.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className={`glass rounded-3xl p-6 border ${res.is_scam ? 'border-red-500/20 bg-red-500/5' : 'border-emerald-500/10 bg-emerald-500/[0.02]'}`}
                    >
                      <div className="flex items-start justify-between gap-4 mb-4">
                        <div className="flex items-start gap-4">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-sm ${res.is_scam ? 'bg-red-500/10 border-red-500/30' : 'bg-emerald-500/10 border-emerald-500/30'}`}>
                            {res.is_scam ? <AlertTriangle size={18} className="text-red-400" /> : <Shield size={18} className="text-emerald-400" />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded border ${res.is_scam ? 'text-red-400 border-red-500/30' : 'text-emerald-300 border-emerald-500/30'}`}>
                                {res.is_scam ? 'SCAM DETECTED' : 'SAFE / CLEAN'}
                              </span>
                              <span className="text-[10px] font-mono text-gray-600">{new Date(res.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <h4 className="text-sm font-mono text-gray-200 mt-2 truncate max-w-[400px]">{res.input}</h4>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-xl font-light ${res.is_scam ? 'text-red-400' : 'text-emerald-400'}`}>
                            {Math.round(res.risk_score * 100)}%
                          </div>
                          <div className="text-[8px] font-mono text-gray-600 uppercase tracking-widest">Risk Index</div>
                        </div>
                      </div>

                      <div className="bg-black/20 rounded-2xl p-5 border border-white/5 space-y-3">
                        <div className="flex items-center gap-2 text-[10px] font-mono text-indigo-400/70 uppercase tracking-widest">
                          <Bot size={11} /> Expert Reasoning
                        </div>
                        <p className="text-xs font-mono text-gray-400 leading-relaxed whitespace-pre-wrap">{res.reason}</p>
                      </div>

                      <div className="mt-4 flex items-center justify-between gap-4">
                         <div className="flex-1 flex items-center gap-3 px-4 py-2 bg-white/[0.03] rounded-xl border border-white/[0.05]">
                           <span className="text-[10px] font-mono text-gray-500 uppercase">Safest Action:</span>
                           <span className={`text-[10px] font-mono uppercase tracking-wider ${res.is_scam ? 'text-amber-400' : 'text-emerald-400'}`}>{res.safe_action}</span>
                         </div>
                         <button className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-gray-500 hover:text-gray-300 text-[10px] font-mono uppercase transition-all">
                           Details
                         </button>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
