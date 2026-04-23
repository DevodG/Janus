'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Link, Image as ImageIcon, Search, AlertTriangle, CheckCircle, XCircle, Info, Hash, ExternalLink, Brain } from 'lucide-react';
import { apiClient, guardianClient } from '@/lib/api';
import type { ScamGuardianResponse } from '@/lib/types';

export default function ScamGuardian() {
  const [activeTab, setActiveTab] = useState<'text' | 'url' | 'image'>('text');
  const [inputValue, setInputValue] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ScamGuardianResponse | null>(null);
  const [history, setHistory] = useState<ScamGuardianResponse[]>([]);

  // Load history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await guardianClient.getHistory();
      setHistory(res);
    } catch (err) {
      console.error('History fetch failed', err);
    }
  };

  const handleAnalyze = async () => {
    if (!inputValue.trim() && activeTab !== 'image') return;
    setIsAnalyzing(true);
    try {
      const payload: any = { source: 'guardian-ui' };
      if (activeTab === 'text') payload.text = inputValue;
      if (activeTab === 'url') payload.url = inputValue;
      
      const res = await apiClient.analyze(payload);
      setResult(res as unknown as ScamGuardianResponse);
      fetchHistory(); // Refresh history
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (score >= 30) return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
    return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'BLOCK': return <XCircle className="text-red-500" />;
      case 'WARN': return <AlertTriangle className="text-amber-500" />;
      default: return <CheckCircle className="text-emerald-500" />;
    }
  };

  return (
    <div className="flex h-full overflow-hidden bg-black/40">
      {/* Main Analysis Area */}
      <div className="flex-1 overflow-y-auto px-4 py-8 border-r border-white/[0.04]">
        <div className="max-w-[800px] mx-auto space-y-8 pb-12">
          {/* Header */}
          <div className="text-center space-y-4">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="inline-flex p-3 rounded-2xl bg-indigo-500/10 border border-indigo-500/20"
            >
              <ShieldAlert className="text-indigo-400 w-8 h-8" />
            </motion.div>
            <h1 className="text-3xl font-bold text-white tracking-tight uppercase tracking-tighter">Guardian Sensory</h1>
            <p className="text-gray-400 max-w-lg mx-auto text-sm">
              Deep forensic analysis across text, images, and domains. Janus ZeroTrust Mesh provides real-time threat neutralization.
            </p>
          </div>

          {/* Intake Area */}
          <div className="bg-[#181818] border border-white/[0.06] rounded-3xl overflow-hidden shadow-2xl">
            <div className="flex border-b border-white/[0.06]">
              {[
                { id: 'text', label: 'Detection', icon: <Search size={16} /> },
                { id: 'url', label: 'Link Intelligence', icon: <Link size={16} /> },
                { id: 'image', label: 'OCR Vision', icon: <ImageIcon size={16} /> },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex-1 flex items-center justify-center gap-2 py-4 text-[11px] font-black uppercase tracking-widest transition-all ${
                    activeTab === tab.id ? 'text-indigo-400 bg-white/[0.04]' : 'text-gray-600 hover:text-gray-400 hover:bg-white/[0.01]'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="p-6 space-y-6">
              {activeTab === 'text' && (
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Analyze a suspicious SMS, Email, or Chat message..."
                  className="w-full h-32 bg-black/30 border border-white/[0.06] rounded-2xl p-4 text-gray-200 placeholder-gray-700 focus:outline-none focus:border-indigo-500/50 transition-colors resize-none text-sm leading-relaxed"
                />
              )}
              {activeTab === 'url' && (
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="https://claim-reward-fast.top/login"
                  className="w-full bg-black/30 border border-white/[0.06] rounded-2xl p-4 text-gray-200 placeholder-gray-700 focus:outline-none focus:border-indigo-500/50 transition-colors text-sm"
                />
              )}
              {activeTab === 'image' && (
                <div className="h-32 border-2 border-dashed border-white/[0.06] rounded-2xl flex flex-col items-center justify-center text-gray-700 group hover:border-indigo-500/30 transition-all cursor-pointer">
                   <ImageIcon size={24} className="mb-2 group-hover:text-indigo-500 transition-colors" />
                   <span className="text-[10px] uppercase tracking-widest font-black">Upload Forensic Screenshot</span>
                   <span className="text-[9px] mt-1 opacity-40">MMSA Emotional Dissonance engine will process.</span>
                </div>
              )}

              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing || (!inputValue.trim() && activeTab !== 'image')}
                className="w-full py-4 rounded-2xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <motion.div 
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full"
                    />
                    Synchronizing Cognition...
                  </>
                ) : (
                  <>
                    <Search size={18} />
                    Run Security Sweep
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Area */}
          <AnimatePresence mode="wait">
            {result && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6"
              >
                <div className={`p-6 rounded-3xl border-2 flex items-center justify-between ${getRiskColor(result.risk_score)}`}>
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-white/10 rounded-2xl shrink-0">
                      {getDecisionIcon(result.decision)}
                    </div>
                    <div>
                      <div className="text-[10px] font-black uppercase tracking-wider opacity-60">Janus Decision Engine</div>
                      <div className="text-2xl font-black italic tracking-tighter">{result.decision}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-black uppercase tracking-wider opacity-60">Risk Intelligence Index</div>
                    <div className="text-4xl font-black tracking-tighter">{result.risk_score}<span className="text-sm opacity-50 ml-1">%</span></div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Reasons */}
                  <div className="bg-[#181818] border border-white/[0.06] rounded-3xl p-6">
                    <h3 className="text-[10px] font-black text-gray-500 flex items-center gap-2 uppercase tracking-widest mb-4">
                       <Info size={14} className="text-indigo-400" /> Evidence Reconstruction
                    </h3>
                    <ul className="space-y-3">
                      {result.reasons.map((reason, i) => (
                        <li key={i} className="flex items-start gap-3 text-xs text-gray-300 leading-relaxed italic">
                          <span className="mt-1.5 w-1 h-1 rounded-full bg-indigo-500 shrink-0" />
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Entities */}
                  <div className="bg-[#181818] border border-white/[0.06] rounded-3xl p-6">
                    <h3 className="text-[10px] font-black text-gray-500 flex items-center gap-2 uppercase tracking-widest mb-4">
                       <Hash size={14} className="text-indigo-400" /> Malicious Signatures
                    </h3>
                    <div className="flex flex-wrap gap-2">
                       {result.entities.phones.map(p => (
                         <span key={p} className="px-2 py-1 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-mono">{p}</span>
                       ))}
                       {result.entities.upi_ids.map(u => (
                         <span key={u} className="px-2 py-1 rounded bg-fuchsia-500/10 border border-fuchsia-500/20 text-fuchsia-400 text-[10px] font-mono uppercase">{u}</span>
                       ))}
                       {result.entities.domains.map(d => (
                         <span key={d} className="px-2 py-1 rounded bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[10px] font-mono">{d}</span>
                       ))}
                       {Object.keys(result.entities).every(k => (result.entities as any)[k].length === 0) && (
                         <p className="text-[10px] text-gray-700 italic">No malicious entities extracted.</p>
                       )}
                    </div>
                  </div>
                </div>

                {/* Similarity Matches */}
                {result.similarity?.matches && result.similarity.matches.length > 0 && (
                  <div className="bg-[#181818] border border-white/[0.06] rounded-3xl p-6">
                    <h3 className="text-[10px] font-black text-gray-500 flex items-center gap-2 uppercase tracking-widest mb-6">
                       <ExternalLink size={14} className="text-indigo-400" /> Relational Journey Memory
                    </h3>
                    <div className="space-y-3">
                      {result.similarity.matches.map((match, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl hover:bg-white/[0.04] transition-all cursor-pointer group">
                           <div className="flex-1 min-w-0 pr-4">
                             <p className="text-xs text-gray-300 truncate font-medium group-hover:text-indigo-300">"{match.text}"</p>
                             <p className="text-[9px] text-gray-600 mt-1 font-mono">Trace: {match.event_id.slice(0, 8)}</p>
                           </div>
                           <div className="bg-indigo-500/10 px-2 py-0.5 rounded text-indigo-400 text-[10px] font-black">
                             {match.similarity}% Similarity
                           </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* History Sidebar */}
      <div className="hidden lg:flex w-72 shrink-0 flex-col bg-[#0d0d0d]/80 backdrop-blur-xl">
        <div className="p-6 border-b border-white/[0.04]">
          <h2 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
            <Brain size={14} className="text-indigo-400" /> Global Threat Feed
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {history.length > 0 ? (
            history.map((item, i) => (
              <div 
                key={i} 
                className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] hover:border-white/10 transition-all cursor-pointer group"
                onClick={() => setResult(item)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[9px] font-black px-1.5 py-0.5 rounded ${getRiskColor(item.risk_score)}`}>
                    {item.risk_score}%
                  </span>
                  <span className="text-[9px] text-gray-600 font-mono italic">
                    {item.decision}
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 line-clamp-2 leading-relaxed bg-black/20 p-2 rounded-lg group-hover:text-gray-200 transition-colors">
                  {item.text}
                </p>
              </div>
            ))
          ) : (
             <div className="h-full flex flex-col items-center justify-center opacity-30">
               <ShieldAlert size={32} className="mb-2" />
               <p className="text-[10px] uppercase font-black tracking-widest">No Threat History</p>
             </div>
          )}
        </div>
        <div className="p-4 border-t border-white/[0.04] text-center">
           <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Relational Mesh Active</p>
        </div>
      </div>
    </div>
  );
}
