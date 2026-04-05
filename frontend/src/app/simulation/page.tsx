'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, Target, ListOrdered, Share2, Play, Hexagon, Zap, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface SimulationSummary {
  simulation_id: string;
  user_input: string;
  status: string;
  scenarios: number;
  elapsed_seconds: number;
  created_at: number;
}

export default function SimulationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulations, setSimulations] = useState<SimulationSummary[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const [form, setForm] = useState({
    title: '',
    seedText: '',
    predictionGoal: ''
  });

  const loadSimulations = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await apiClient.getSimulations();
      // Map SimulationRecord to SimulationSummary
      const summaries: SimulationSummary[] = (Array.isArray(data) ? data : []).map((sim: any) => ({
        simulation_id: sim.simulation_id,
        user_input: sim.user_input || sim.title || '',
        status: sim.status,
        scenarios: sim.scenarios || 0,
        elapsed_seconds: sim.elapsed_seconds || 0,
        created_at: sim.created_at || 0,
      }));
      setSimulations(summaries);
    } catch {
      setSimulations([]);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSimulations();
  }, [loadSimulations]);

  const handleSubmit = async () => {
    if (!form.title || !form.seedText || !form.predictionGoal) {
      setError('All simulation parameters are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Run native simulation directly
      const userInput = `${form.title}. ${form.seedText}. Goal: ${form.predictionGoal}`;
      const result = await apiClient.runNativeSimulation(userInput, {
        title: form.title,
        seed_text: form.seedText,
        prediction_goal: form.predictionGoal,
      });

      // Navigate to simulation detail
      if (result.simulation_id) {
        router.push(`/simulation/${result.simulation_id}`);
      } else {
        setError('Simulation completed but no ID was returned.');
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize simulation core.');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-12">
      <header className="mb-12">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 mb-4">
            <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20">
              <FlaskConical size={20} className="text-amber-400" />
              {loading && <div className="absolute inset-0 rounded-2xl border-2 border-amber-400/50 border-t-transparent animate-spin" />}
            </div>
            <div>
              <h1 className="text-3xl font-light tracking-[0.15em] text-gradient-subtle uppercase">
                Simulation Lab
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-[10px] font-mono text-amber-400/70 uppercase tracking-widest">
                  Native Simulation Engine Online
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={loadSimulations}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl glass border border-white/5 hover:border-amber-500/20 text-xs font-mono text-gray-400 hover:text-amber-300 transition-all disabled:opacity-40"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* CREATE SIMULATION FORM */}
        <div className="lg:col-span-7">
          <div className="glass rounded-3xl p-8 relative overflow-hidden group">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-amber-500/5 blur-3xl rounded-full pointer-events-none" />
            
            <h2 className="text-sm font-mono text-gray-400 uppercase tracking-widest mb-8 flex items-center gap-2">
              <Hexagon size={14} className="text-amber-400/50" />
              Initialize New Scenario
            </h2>

            {error && (
              <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400">
                {error}
              </div>
            )}

            <div className="space-y-6">
              
              <div className="space-y-2">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Scenario Title</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Target size={14} className="text-amber-500/50" />
                  </div>
                  <input
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    disabled={loading}
                    placeholder="e.g. US Debt Default Simulation"
                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm text-gray-200 font-mono focus:border-amber-500/50 focus:outline-none transition-colors placeholder:text-gray-700"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Initial Context (Seed)</label>
                <div className="relative">
                  <div className="absolute top-3.5 left-0 pl-4 pointer-events-none">
                    <ListOrdered size={14} className="text-amber-500/50" />
                  </div>
                  <textarea
                    value={form.seedText}
                    onChange={(e) => setForm({ ...form, seedText: e.target.value })}
                    disabled={loading}
                    placeholder="Provide the background facts, current market state, and constraints..."
                    rows={4}
                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm text-gray-200 font-mono focus:border-amber-500/50 focus:outline-none transition-colors placeholder:text-gray-700 resize-none"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Prediction Goal</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Share2 size={14} className="text-amber-500/50" />
                  </div>
                  <input
                    value={form.predictionGoal}
                    onChange={(e) => setForm({ ...form, predictionGoal: e.target.value })}
                    disabled={loading}
                    placeholder="e.g. What is the impact on 10-year treasury yields?"
                    className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-sm text-gray-200 font-mono focus:border-amber-500/50 focus:outline-none transition-colors placeholder:text-gray-700"
                  />
                </div>
              </div>

              <div className="pt-4">
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="w-full group relative flex items-center justify-center gap-2 py-4 rounded-xl bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 disabled:bg-gray-900 disabled:border-gray-800 transition-all duration-300"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-amber-500/0 via-amber-500/10 to-amber-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-md" />
                  <Zap size={16} className={loading ? 'text-gray-600' : 'text-amber-400 group-hover:scale-110 transition-transform'} />
                  <span className={`text-xs font-mono uppercase tracking-widest ${loading ? 'text-gray-500' : 'text-amber-300'}`}>
                    {loading ? 'Running Simulation...' : 'Launch Simulation'}
                  </span>
                </button>
              </div>

            </div>
          </div>
        </div>

        {/* ACTIVE SIMULATIONS LIST */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between mb-2">
             <h3 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Recent Executions</h3>
             <span className="text-[10px] font-mono text-gray-600">{simulations.length} total</span>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-3 pr-2" style={{ maxHeight: '600px' }}>
            <AnimatePresence>
              {simulations.length === 0 ? (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-8 border border-white/5 border-dashed rounded-2xl flex flex-col items-center justify-center text-center">
                  <Hexagon size={24} className="text-gray-800 mb-3" />
                  <p className="text-xs font-mono text-gray-600 uppercase tracking-widest">No active simulations.</p>
                </motion.div>
              ) : (
                simulations.map((sim, i) => (
                  <motion.div
                    key={sim.simulation_id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => router.push(`/simulation/${sim.simulation_id}`)}
                    className="glass p-5 rounded-2xl border border-white/[0.04] hover:border-amber-500/30 hover:bg-white/[0.04] cursor-pointer transition-all duration-300 group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full ${sim.status === 'completed' ? 'bg-emerald-400' : sim.status === 'failed' ? 'bg-red-400' : 'bg-amber-400 animate-pulse'}`} />
                        <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                          {sim.status}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-gray-600 uppercase">
                        {sim.simulation_id.slice(0, 8)}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-gray-200 group-hover:text-amber-300 transition-colors line-clamp-1 mb-1">
                      {sim.user_input}
                    </h4>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-gray-600">
                      <span>{sim.scenarios} scenarios</span>
                      <span>·</span>
                      <span>{sim.elapsed_seconds}s</span>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
