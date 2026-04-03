'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { FlaskConical, Target, ListOrdered, Share2, Hexagon, ChevronLeft, Network, ShieldAlert } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { SimulationRecord } from '@/lib/types';

// ─── Shared UI Components ──────────────────────────────────────
function Typewriter({ text, speed = 8 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed('');
    if (!text) return;
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
        <span className="inline-block w-1.5 h-4 bg-amber-400 ml-1 animate-pulse" />
      )}
    </span>
  );
}

export default function SimulationDetailPage() {
  const params = useParams();
  const simulationId = params.id as string;
  const [sim, setSim] = useState<SimulationRecord | null>(null);
  const [loading, setLoading] = useState(true);

  // Poll for status if not complete
  useEffect(() => {
    async function loadData() {
      try {
        const data = await apiClient.getSimulation(simulationId);
        setSim(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
    const interval = setInterval(() => {
      if (sim && ['completed', 'failed'].includes(sim.status)) {
        clearInterval(interval);
      } else {
        loadData();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [simulationId, sim?.status]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center pb-20">
        <div className="relative w-24 h-24 flex items-center justify-center">
          <div className="absolute inset-0 border-2 border-amber-500/20 rounded-full" />
          <div className="absolute inset-0 border-2 border-t-amber-400 rounded-full animate-spin" />
          <Hexagon className="text-amber-500/50" size={32} />
        </div>
      </div>
    );
  }

  if (!sim) {
    return (
      <div className="flex h-screen flex-col items-center justify-center">
        <ShieldAlert size={32} className="text-red-500/50 mb-4" />
        <p className="text-sm font-mono text-gray-500">Simulation parameters not found or purged.</p>
        <Link href="/simulation" className="mt-4 px-4 py-2 border border-red-500/20 hover:bg-red-500/10 rounded-full text-xs font-mono text-red-400 transition-colors uppercase">Return to Lab</Link>
      </div>
    );
  }

  const isRunning = !['completed', 'failed'].includes(sim.status);

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-8">
      {/* Back nav & Header */}
      <div className="flex items-center justify-between mb-8">
        <Link href="/simulation" className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/5 hover:border-amber-500/30 hover:text-amber-300 text-gray-400 transition-colors text-xs font-mono uppercase tracking-widest group">
          <ChevronLeft size={14} className="group-hover:-translate-x-1 transition-transform" /> Lab Overview
        </Link>

        {/* Live Status indicator */}
        <div className="flex items-center gap-3 glass px-4 py-2 rounded-full border-white/5">
          <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-amber-400 animate-pulse' : sim.status === 'completed' ? 'bg-emerald-400' : 'bg-red-500'}`} />
          <span className="text-[10px] font-mono text-gray-300 uppercase tracking-widest">{sim.status}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        
        {/* Left Column: Mission Parameters */}
        <div className="xl:col-span-4 flex flex-col gap-6">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="glass rounded-3xl p-8 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-6 opacity-5">
              <Network size={120} />
            </div>
            
            <div className="flex items-center justify-between mb-8 relative z-10">
              <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-widest">
                <FlaskConical size={14} /> Vector Simulation
              </div>
              <span className="text-[10px] font-mono text-gray-600">ID: {sim.simulation_id.slice(0, 8)}</span>
            </div>

            <h2 className="text-xl font-light text-gray-100 leading-relaxed relative z-10 mb-8">
              {sim.title}
            </h2>

            <div className="space-y-6 relative z-10">
              <div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 border-b border-white/5 pb-2">
                  <ListOrdered size={12} /> Initial Seed Data
                </div>
                <p className="text-xs font-mono text-gray-400 leading-relaxed whitespace-pre-wrap pl-1">{sim.remote_payload?.seed_text || 'No seed text provided.'}</p>
              </div>

              <div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 border-b border-white/5 pb-2">
                  <Target size={12} /> Prediction Target
                </div>
                <p className="text-sm font-mono text-amber-300 leading-relaxed pl-1">{sim.prediction_goal}</p>
              </div>
            </div>

            {sim.case_id && (
               <div className="mt-8 pt-6 border-t border-white/5">
                 <Link href={`/cases/${sim.case_id}`} className="block w-full text-center py-2.5 rounded-xl border border-indigo-500/20 hover:bg-indigo-500/10 text-xs font-mono text-indigo-300 transition-colors uppercase tracking-widest">
                   Link: Originating Case
                 </Link>
               </div>
            )}
          </motion.div>
        </div>

        {/* Right Column: Active Simulation Render / Report */}
        <div className="xl:col-span-8 flex flex-col">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="h-full glass rounded-3xl p-8 border border-amber-500/10 outline outline-1 outline-amber-500/5 relative overflow-hidden flex flex-col">
            
            {isRunning ? (
              <div className="flex-1 flex flex-col items-center justify-center min-h-[400px]">
                {/* Simulated active node graph animation */}
                <div className="relative w-64 h-64 mb-8">
                  <div className="absolute inset-0 bg-amber-500/5 blur-3xl rounded-full" />
                  <div className="absolute inset-0 border border-amber-500/20 rounded-full animate-[spin_10s_linear_infinite]" />
                  <div className="absolute inset-4 border border-amber-500/10 rounded-full animate-[spin_7s_linear_infinite_reverse]" />
                  <div className="absolute inset-8 border border-dashed border-amber-500/30 rounded-full animate-[spin_20s_linear_infinite]" />
                  <Hexagon size={48} className="absolute inset-0 m-auto text-amber-400 animate-pulse" />
                  
                  {/* Orbiting nodes */}
                  <div className="absolute top-0 inset-x-0 mx-auto w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.8)]" />
                  <div className="absolute bottom-8 left-8 w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_8px_rgba(251,191,36,0.6)]" />
                  <div className="absolute top-1/2 right-4 w-2 h-2 rounded-full bg-orange-400 shadow-[0_0_10px_rgba(251,146,60,0.8)]" />
                </div>
                
                <h3 className="text-sm font-mono text-amber-400 uppercase tracking-widest mb-3">Monte Carlo Engine Running</h3>
                <div className="space-y-2 text-center text-[10px] font-mono text-gray-500 uppercase tracking-widest w-full max-w-sm">
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 0 }}>→ Evolving graph vectors based on seed data</motion.p>
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 0.6 }}>→ Establishing domain connections...</motion.p>
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 1.2 }}>→ Cross-referencing external data nodes...</motion.p>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-amber-500/10 blur-[60px] rounded-full pointer-events-none" />
                
                <div className="flex items-center gap-3 mb-8 border-b border-white/5 pb-4 relative z-10">
                  <div className={`p-2 rounded-lg ${sim.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                    <Share2 size={16} />
                  </div>
                  <div>
                    <h3 className="text-xs font-mono text-gray-300 uppercase tracking-widest">MiroFish Analysis Engine</h3>
                    <p className={`text-[10px] font-mono uppercase tracking-widest ${sim.status === 'completed' ? 'text-emerald-500/70' : 'text-red-500/70'}`}>
                      {sim.status === 'completed' ? 'Resolution Complete' : 'Simulation Terminated'}
                    </p>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto pr-2 relative z-10">
                  <div className="prose prose-invert max-w-none text-sm leading-relaxed font-mono">
                    {sim.status === 'completed' ? (
                      <div className="text-amber-100/90 whitespace-pre-wrap">
                        <Typewriter text={sim.report || 'No report generated.'} speed={2} />
                      </div>
                    ) : (
                      <div className="text-red-400/90 whitespace-pre-wrap">
                         {sim.report || 'Critical structural failure during scenario mapping. Check system logs.'}
                      </div>
                    )}
                  </div>
                </div>

                {/* Simulated actions */}
                {sim.status === 'completed' && (
                   <div className="mt-8 pt-4 border-t border-white/5 flex items-center justify-end gap-3 relative z-10">
                     <button className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-full text-[10px] font-mono text-gray-400 uppercase tracking-widest transition-colors">
                       Export Graph Data
                     </button>
                     <button className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 rounded-full text-[10px] font-mono text-amber-300 uppercase tracking-widest transition-colors">
                       Run Counter-factual
                     </button>
                   </div>
                )}
              </div>
            )}
            
          </motion.div>
        </div>

      </div>
    </div>
  );
}
