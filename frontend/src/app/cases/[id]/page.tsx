'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Target, Zap, Activity, ChevronLeft, Hexagon, FileText, Bot, Clock } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';

// ─── Shared UI Components ──────────────────────────────────────
function Typewriter({ text, speed = 10 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed('');
    const interval = setInterval(() => {
      if (idx.current < text.length) {
        setDisplayed((prev) => prev + text[idx.current]);
        idx.current++;
      } else {
        clearInterval(interval);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 animate-pulse" />
      )}
    </span>
  );
}

function ConfidenceRing({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 18;
  const stroke = circumference * (1 - value);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-12 h-12">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="2" />
          <motion.circle
            cx="20" cy="20" r="18" fill="none"
            stroke={value >= 0.7 ? '#22c55e' : value >= 0.5 ? '#eab308' : '#ef4444'}
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: stroke }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-mono text-gray-300">{pct}</span>
      </div>
      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

// ─── Main View ───────────────────────────────────────────────
export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.getCase(caseId)
      .then(setRecord)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center pb-20">
        <div className="flex flex-col items-center gap-6">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 border-2 border-indigo-500/20 rounded-full" />
            <div className="absolute inset-0 border-2 border-t-indigo-400 rounded-full animate-spin" />
            <div className="absolute inset-2 border-2 border-violet-500/20 rounded-full" />
            <div className="absolute inset-2 border-2 border-l-violet-400 rounded-full animate-spin direction-reverse" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
            <Hexagon className="absolute inset-0 m-auto text-indigo-500/50" size={16} />
          </div>
          <p className="text-xs font-mono text-indigo-400 uppercase tracking-widest animate-pulse">Decrypting Trace...</p>
        </div>
      </div>
    );
  }

  if (!record) {
    return (
      <div className="flex h-screen flex-col items-center justify-center">
        <Shield size={32} className="text-red-500/50 mb-4" />
        <p className="text-sm font-mono text-gray-500">Record not found or access denied.</p>
        <Link href="/cases" className="mt-4 px-4 py-2 border border-red-500/20 hover:bg-red-500/10 rounded-full text-xs font-mono text-red-400 transition-colors uppercase">Return to Archives</Link>
      </div>
    );
  }

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-8">
      {/* Back nav & Header */}
      <Link href="/cases" className="inline-flex items-center gap-2 mb-8 px-4 py-2 rounded-full border border-white/5 hover:border-indigo-500/30 hover:text-indigo-300 text-gray-400 transition-colors text-xs font-mono uppercase tracking-widest group">
        <ChevronLeft size={14} className="group-hover:-translate-x-1 transition-transform" /> Archives
      </Link>

      <div className="grid grid-cols-12 gap-6">
        
        {/* Left Column: Input & Metadata */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
          
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="glass rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <FileText size={100} />
            </div>
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-indigo-400 uppercase tracking-wider relative z-10">
              <Target size={14} /> Mission Directive
            </div>
            <h2 className="text-lg font-light text-gray-100 leading-relaxed relative z-10">
              "{record.user_input}"
            </h2>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5 text-xs font-mono text-violet-400 uppercase tracking-wider">
              <Activity size={14} /> Cognitive Trace Data
            </div>

            <div className="space-y-4 text-sm font-mono">
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-500">Record ID</span>
                <span className="text-gray-300">{record.case_id.split('-')[0]}</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-500">Timestamp</span>
                <span className="text-gray-300">{record.saved_at ? new Date(record.saved_at).toLocaleString() : 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-500">Routing Mode</span>
                <span className="text-indigo-300">{record.route?.execution_mode || 'STANDARD'}</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-500">Domain Pack</span>
                <span className="text-gray-300">{record.route?.domain_pack || 'General'}</span>
              </div>
              <div className="flex justify-between items-center pb-1">
                <span className="text-gray-500">Task Complexity</span>
                <span className="text-gray-300">{record.route?.complexity || 'Unknown'}</span>
              </div>
            </div>

            {record.simulation_id && (
              <div className="mt-6 pt-6 border-t border-white/5">
                <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-center">
                  <p className="text-xs font-mono text-amber-500/80 uppercase tracking-widest mb-3">Simulation Data Attached</p>
                  <Link href={`/simulation/${record.simulation_id}`} className="inline-block px-4 py-1.5 rounded-full bg-amber-500/10 hover:bg-amber-500/20 text-xs font-mono text-amber-300 transition-colors uppercase tracking-widest">
                    View Vector Sim
                  </Link>
                </div>
              </div>
            )}
          </motion.div>

          {/* Confidence Summary */}
          {record.outputs && record.outputs.length > 0 && (
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="glass rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-6 text-xs font-mono text-emerald-400 uppercase tracking-wider">
                <Shield size={14} /> Agent Calibration
              </div>
              <div className="flex items-center justify-around">
                {record.outputs.filter(o => o.confidence > 0).map((o, idx) => (
                  <ConfidenceRing key={`${o.agent || 'agent'}-${idx}`} value={o.confidence} label={o.agent || `Agent ${idx + 1}`} />
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Right Column: Final Answer & Agent Outputs */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
          
          {/* Final Synthesis */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-2xl p-8 border border-indigo-500/20 outline outline-1 outline-indigo-500/10 shadow-[0_0_30px_rgba(99,102,241,0.05)] relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full" />
            
            <div className="flex items-center gap-2 mb-6">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500/20">
                <Zap size={14} className="text-indigo-400" />
              </div>
              <div>
                <h3 className="text-sm font-mono text-indigo-300 uppercase tracking-widest">Synthesizer Agent</h3>
                <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Final Report</p>
              </div>
            </div>

            <div className="prose prose-invert max-w-none text-[15px] leading-relaxed text-gray-200 whitespace-pre-wrap">
              {record.final_answer ? (
                <Typewriter text={record.final_answer} speed={5} />
              ) : (
                <span className="text-gray-500 italic">No final synthesis recorded.</span>
              )}
            </div>
          </motion.div>

          {/* Individual Agent Sub-outputs */}
          {record.outputs && record.outputs.length > 0 && (
             <div className="space-y-4">
               <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest px-2 pt-4">Sub-Agent Operational Logs</h3>
               {record.outputs.map((out, i) => (
                  <motion.div
                    key={`${out.agent || 'output'}-${i}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + (i * 0.1) }}
                    className="glass rounded-xl p-5 border border-white/[0.04]"
                  >
                   <div className="flex items-start gap-4">
                     <div className="shrink-0 mt-1">
                       <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center border border-gray-700">
                         <Bot size={14} className="text-gray-400" />
                       </div>
                     </div>
                     <div className="flex-1">
                       <div className="flex items-center justify-between mb-2">
                         <h4 className="text-xs font-mono text-gray-300 uppercase tracking-widest">{out.agent}</h4>
                         <span className="text-[10px] font-mono text-emerald-400">STATUS: CPLT</span>
                       </div>
                       <p className="text-sm text-gray-400 leading-relaxed mb-4">{out.summary}</p>
                       
                       {/* Nested Details */}
                       {out.details && Object.keys(out.details).length > 0 && (
                         <div className="rounded-lg bg-black/40 border border-white/5 p-4 text-xs font-mono text-gray-500 overflow-x-auto">
                           <pre>{JSON.stringify(out.details, null, 2)}</pre>
                         </div>
                       )}
                     </div>
                   </div>
                 </motion.div>
               ))}
             </div>
          )}

        </div>

      </div>
    </div>
  );
}
