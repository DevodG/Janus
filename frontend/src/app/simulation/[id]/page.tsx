'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { FlaskConical, Target, ListOrdered, Share2, Hexagon, ChevronLeft, Network, ShieldAlert, BarChart3, TrendingUp, TrendingDown, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';

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

// ─── Simulation Scenario Card ─────────────────────────────────
function ScenarioCard({ scenario, index }: { scenario: any; index: number }) {
  const impactColors: Record<string, string> = {
    low: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    medium: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
    extreme: 'text-red-400 bg-red-500/10 border-red-500/20',
  };
  const impactClass = impactColors[scenario.impact] || impactColors.medium;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="glass rounded-xl p-4 border border-white/[0.06]"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-xs font-mono text-indigo-300">
            {index + 1}
          </div>
          <div>
            <h4 className="text-sm font-mono text-gray-200">{scenario.name}</h4>
            <span className="text-[10px] font-mono text-gray-500">Probability: {Math.round(scenario.probability * 100)}%</span>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono uppercase border ${impactClass}`}>
          {scenario.impact}
        </span>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed mb-3">{scenario.description}</p>
      {scenario.key_indicators && scenario.key_indicators.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {scenario.key_indicators.map((ind: string, i: number) => (
            <span key={`${scenario.name}-indicator-${i}`} className="text-[9px] font-mono text-gray-600 bg-white/5 px-1.5 py-0.5 rounded">
              {ind}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}

// ─── Perspective Card ─────────────────────────────────────────
function PerspectiveCard({ perspective, index }: { perspective: any; index: number }) {
  const colors: Record<string, string> = {
    optimist: 'text-emerald-400 border-emerald-500/20',
    pessimist: 'text-red-400 border-red-500/20',
    realist: 'text-blue-400 border-blue-500/20',
    contrarian: 'text-purple-400 border-purple-500/20',
  };
  const colorClass = colors[perspective.perspective] || colors.realist;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`glass rounded-xl p-4 border ${colorClass}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-mono uppercase tracking-wider">{perspective.perspective}</h4>
        <span className="text-[10px] font-mono text-gray-500">
          Prob: {Math.round((perspective.probability || 0.5) * 100)}%
        </span>
      </div>
      <p className="text-xs text-gray-300 mb-2">{perspective.outlook}</p>
      {perspective.key_points && perspective.key_points.length > 0 && (
        <ul className="space-y-1">
          {perspective.key_points.map((point: string, i: number) => (
            <li key={`${perspective.perspective}-point-${i}`} className="text-[10px] font-mono text-gray-500 flex items-start gap-1.5">
              <span className="text-indigo-400 mt-0.5">•</span>
              {point}
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}

export default function SimulationDetailPage() {
  const params = useParams();
  const simulationId = params.id as string;
  const [sim, setSim] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Poll for status if not complete
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        const data = await apiClient.getSimulation(simulationId);
        if (mounted) {
          setSim(data);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || 'Failed to load simulation');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
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
    
    return () => {
      mounted = false;
      clearInterval(interval);
    };
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

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center">
        <ShieldAlert size={32} className="text-red-500/50 mb-4" />
        <p className="text-sm font-mono text-red-400 mb-4">{error}</p>
        <Link href="/simulation" className="px-4 py-2 border border-red-500/20 hover:bg-red-500/10 rounded-full text-xs font-mono text-red-400 transition-colors uppercase">Return to Lab</Link>
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
  const synthesis = sim.synthesis || {};
  const decomposition = sim.decomposition || {};
  const perspectives = sim.perspectives || [];
  const scenarios = synthesis.scenarios || [];
  const userInput = sim.user_input || '';

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
          {sim.elapsed_seconds && (
            <span className="text-[10px] font-mono text-gray-600">({sim.elapsed_seconds}s)</span>
          )}
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
                <FlaskConical size={14} /> Native Simulation
              </div>
              <span className="text-[10px] font-mono text-gray-600">ID: {sim.simulation_id?.slice(0, 8)}</span>
            </div>

            <h2 className="text-xl font-light text-gray-100 leading-relaxed relative z-10 mb-8">
              {userInput}
            </h2>

            <div className="space-y-6 relative z-10">
              {/* Decomposition */}
              {decomposition.variables && decomposition.variables.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 border-b border-white/5 pb-2">
                    <ListOrdered size={12} /> Key Variables ({decomposition.variables.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {decomposition.variables.map((v: string, i: number) => (
                      <span key={`var-${i}`} className="text-[9px] font-mono text-gray-400 bg-white/5 px-2 py-0.5 rounded-full">{v}</span>
                    ))}
                  </div>
                </div>
              )}

              {decomposition.actors && decomposition.actors.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 border-b border-white/5 pb-2">
                    <Target size={12} /> Key Actors ({decomposition.actors.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {decomposition.actors.map((a: string, i: number) => (
                      <span key={`actor-${i}`} className="text-[9px] font-mono text-amber-300/70 bg-amber-500/10 px-2 py-0.5 rounded-full">{a}</span>
                    ))}
                  </div>
                </div>
              )}

              {decomposition.complexity && (
                <div className="flex items-center justify-between text-xs font-mono border-b border-white/5 pb-2">
                  <span className="text-gray-500">Complexity</span>
                  <span className="text-gray-300 capitalize">{decomposition.complexity}</span>
                </div>
              )}

              {decomposition.uncertainty_level && (
                <div className="flex items-center justify-between text-xs font-mono pb-1">
                  <span className="text-gray-500">Uncertainty</span>
                  <span className="text-gray-300 capitalize">{decomposition.uncertainty_level}</span>
                </div>
              )}
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

        {/* Right Column: Simulation Results */}
        <div className="xl:col-span-8 flex flex-col gap-6">
          
          {isRunning ? (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="h-full glass rounded-3xl p-8 border border-amber-500/10 outline outline-1 outline-amber-500/5 relative overflow-hidden flex flex-col">
              <div className="flex-1 flex flex-col items-center justify-center min-h-[400px]">
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
                
                <h3 className="text-sm font-mono text-amber-400 uppercase tracking-widest mb-3">Simulation Engine Running</h3>
                <div className="space-y-2 text-center text-[10px] font-mono text-gray-500 uppercase tracking-widest w-full max-w-sm">
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 0 }}>→ Decomposing scenario variables</motion.p>
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 0.6 }}>→ Running multi-perspective analysis...</motion.p>
                  <motion.p animate={{ opacity: [0, 1, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 1.2 }}>→ Synthesizing outcomes...</motion.p>
                </div>
              </div>
            </motion.div>
          ) : sim.status === 'completed' ? (
            <>
              {/* Scenarios */}
              {scenarios.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-2xl p-6 border border-white/[0.06]">
                  <div className="flex items-center gap-2 mb-4 text-xs font-mono text-indigo-400 uppercase tracking-wider">
                    <BarChart3 size={14} /> Scenario Analysis ({scenarios.length} scenarios)
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {scenarios.map((scenario: any, i: number) => (
                      <ScenarioCard key={`scenario-${i}`} scenario={scenario} index={i} />
                    ))}
                  </div>

                  {/* Most Likely */}
                  {synthesis.most_likely && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-emerald-400 uppercase tracking-wider">
                        <CheckCircle size={12} /> Most Likely Outcome
                      </div>
                      <p className="text-xs text-gray-300 leading-relaxed">{synthesis.most_likely}</p>
                    </div>
                  )}

                  {/* Decision Framework */}
                  {synthesis.decision_framework && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-amber-400 uppercase tracking-wider">
                        <Target size={12} /> Decision Framework
                      </div>
                      <p className="text-xs text-gray-300 leading-relaxed">{synthesis.decision_framework}</p>
                    </div>
                  )}

                  {/* Early Warning Signals */}
                  {synthesis.early_warning_signals && synthesis.early_warning_signals.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-red-400 uppercase tracking-wider">
                        <AlertCircle size={12} /> Early Warning Signals
                      </div>
                      <div className="space-y-1.5">
                        {synthesis.early_warning_signals.map((signal: string, i: number) => (
                          <div key={`signal-${i}`} className="flex items-start gap-2 text-xs text-gray-400">
                            <span className="text-red-400 mt-0.5">⚠</span>
                            {signal}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Uncertainties */}
                  {synthesis.key_uncertainties && synthesis.key_uncertainties.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                        Key Uncertainties
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {synthesis.key_uncertainties.map((unc: string, i: number) => (
                          <span key={`unc-${i}`} className="text-[9px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">{unc}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Perspectives */}
              {perspectives.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass rounded-2xl p-6 border border-white/[0.06]">
                  <div className="flex items-center gap-2 mb-4 text-xs font-mono text-violet-400 uppercase tracking-wider">
                    <Network size={14} /> Multi-Perspective Analysis ({perspectives.length} perspectives)
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {perspectives.map((p: any, i: number) => (
                      <PerspectiveCard key={`perspective-${i}`} perspective={p} index={i} />
                    ))}
                  </div>
                </motion.div>
              )}
            </>
          ) : (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="h-full glass rounded-3xl p-8 border border-red-500/10 outline outline-1 outline-red-500/5 relative overflow-hidden flex flex-col">
              <div className="flex-1 flex flex-col items-center justify-center">
                <XCircle size={48} className="text-red-500/50 mb-4" />
                <h3 className="text-sm font-mono text-red-400 uppercase tracking-widest mb-3">Simulation Failed</h3>
                <p className="text-xs text-gray-500 text-center max-w-md">
                  {synthesis.error || 'The simulation encountered an error and could not complete.'}
                </p>
              </div>
            </motion.div>
          )}
        </div>

      </div>
    </div>
  );
}
