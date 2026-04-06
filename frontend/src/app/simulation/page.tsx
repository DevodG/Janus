'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Target, ListOrdered, Share2, RefreshCw } from 'lucide-react';
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

  const [form, setForm] = useState({ title: '', seedText: '', predictionGoal: '' });

  const loadSimulations = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await apiClient.getSimulations();
      const summaries: SimulationSummary[] = (Array.isArray(data) ? data : []).map((sim: any) => ({
        simulation_id: sim.simulation_id,
        user_input: sim.user_input || sim.title || '',
        status: sim.status,
        scenarios: sim.scenarios || 0,
        elapsed_seconds: sim.elapsed_seconds || 0,
        created_at: sim.created_at || 0,
      }));
      setSimulations(summaries);
    } catch { setSimulations([]); }
    finally { setRefreshing(false); }
  }, []);

  useEffect(() => { loadSimulations(); }, [loadSimulations]);

  const handleSubmit = async () => {
    if (!form.title || !form.seedText || !form.predictionGoal) {
      setError('All simulation parameters are required.');
      return;
    }
    setLoading(true); setError(null);
    try {
      const userInput = `${form.title}. ${form.seedText}. Goal: ${form.predictionGoal}`;
      const result = await apiClient.runNativeSimulation(userInput, {
        title: form.title, seed_text: form.seedText, prediction_goal: form.predictionGoal,
      });
      if (result.simulation_id) {
        router.push(`/simulation/${result.simulation_id}`);
      } else {
        setError('Simulation completed but no ID returned.');
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run simulation.');
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/15 flex items-center justify-center">
              <Zap size={16} className="text-amber-400" />
              {loading && <div className="absolute inset-0 rounded-xl border-2 border-amber-400/40 border-t-transparent animate-spin" />}
            </div>
            <div>
              <h1 className="text-lg font-light text-gray-100">Simulation Lab</h1>
              <p className="text-[11px] text-gray-600">Scenario modeling and prediction engine</p>
            </div>
          </div>
          <button onClick={loadSimulations} disabled={refreshing} className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-[11px] text-gray-500 hover:text-gray-300 transition-all disabled:opacity-40">
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Form */}
          <div className="lg:col-span-7">
            <div className="card p-6 space-y-5">
              <h2 className="text-[11px] text-amber-400 uppercase tracking-wider flex items-center gap-2">
                <Zap size={12} /> New Simulation
              </h2>

              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/15 text-[12px] text-red-400">{error}</div>
              )}

              <div className="space-y-1.5">
                <label className="text-[10px] text-gray-500 uppercase tracking-wider">Scenario Title</label>
                <div className="relative">
                  <Target size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600" />
                  <input
                    value={form.title}
                    onChange={e => setForm({ ...form, title: e.target.value })}
                    disabled={loading}
                    placeholder="e.g. US Debt Default Simulation"
                    className="w-full py-2.5 pl-9 pr-4 text-[13px] text-gray-200 rounded-xl border border-white/[0.06] focus:border-amber-500/30 focus:outline-none transition-colors placeholder:text-gray-700"
                    style={{ background: 'rgba(0,0,0,0.3)' }}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-gray-500 uppercase tracking-wider">Initial Context</label>
                <div className="relative">
                  <ListOrdered size={14} className="absolute left-3 top-3 text-gray-600" />
                  <textarea
                    value={form.seedText}
                    onChange={e => setForm({ ...form, seedText: e.target.value })}
                    disabled={loading}
                    placeholder="Background facts, market state, constraints..."
                    rows={3}
                    className="w-full py-2.5 pl-9 pr-4 text-[13px] text-gray-200 rounded-xl border border-white/[0.06] focus:border-amber-500/30 focus:outline-none transition-colors placeholder:text-gray-700 resize-none"
                    style={{ background: 'rgba(0,0,0,0.3)' }}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-gray-500 uppercase tracking-wider">Prediction Goal</label>
                <div className="relative">
                  <Share2 size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600" />
                  <input
                    value={form.predictionGoal}
                    onChange={e => setForm({ ...form, predictionGoal: e.target.value })}
                    disabled={loading}
                    placeholder="e.g. Impact on 10-year treasury yields?"
                    className="w-full py-2.5 pl-9 pr-4 text-[13px] text-gray-200 rounded-xl border border-white/[0.06] focus:border-amber-500/30 focus:outline-none transition-colors placeholder:text-gray-700"
                    style={{ background: 'rgba(0,0,0,0.3)' }}
                  />
                </div>
              </div>

              <button
                onClick={handleSubmit}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 disabled:opacity-40 transition-all text-[12px] text-amber-300"
              >
                <Zap size={14} className={loading ? 'animate-pulse' : ''} />
                {loading ? 'Running Simulation...' : 'Launch Simulation'}
              </button>
            </div>
          </div>

          {/* Recent simulations */}
          <div className="lg:col-span-5 space-y-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Recent Executions</span>
              <span className="text-[10px] text-gray-600">{simulations.length} total</span>
            </div>

            {simulations.length === 0 ? (
              <div className="card text-center py-12">
                <Zap size={24} className="text-gray-700 mx-auto mb-3" />
                <p className="text-[12px] text-gray-600">No simulations yet.</p>
              </div>
            ) : (
              simulations.map((sim, i) => (
                <motion.div
                  key={sim.simulation_id}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => router.push(`/simulation/${sim.simulation_id}`)}
                  className="card hover:border-amber-500/20 cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${sim.status === 'completed' ? 'bg-emerald-400' : sim.status === 'failed' ? 'bg-red-400' : 'bg-amber-400 animate-pulse'}`} />
                      <span className="text-[10px] text-gray-500 uppercase tracking-wider">{sim.status}</span>
                    </div>
                    <span className="text-[10px] text-gray-600">{sim.simulation_id.slice(0, 8)}</span>
                  </div>
                  <h4 className="text-[13px] text-gray-300 group-hover:text-amber-300 transition-colors line-clamp-1 mb-1">
                    {sim.user_input}
                  </h4>
                  <div className="flex items-center gap-3 text-[10px] text-gray-600">
                    <span>{sim.scenarios} scenarios</span>
                    <span>·</span>
                    <span>{sim.elapsed_seconds}s</span>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
