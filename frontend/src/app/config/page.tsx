'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Settings, Activity, Brain, Zap, Shield, RefreshCw, Server, Globe, HardDrive, Cpu } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api';

export default function ConfigPage() {
  const [daemonStatus, setDaemonStatus] = useState<any>(null);
  const [curiosity, setCuriosity] = useState<any>(null);
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const baseUrl = getApiBaseUrl();
    try {
      const [healthRes, statusRes, curiosityRes, memoryRes] = await Promise.all([
        fetch(`${baseUrl}/health`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/daemon/status`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/daemon/curiosity`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/memory/stats`).then(r => r.ok ? r.json() : null),
      ]);
      if (healthRes) setHealth(healthRes);
      if (statusRes) setDaemonStatus(statusRes);
      if (curiosityRes) setCuriosity(curiosityRes);
      if (memoryRes) setMemoryStats(memoryRes);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw size={20} className="text-gray-500 animate-spin" />
          <p className="text-[12px] text-gray-500">Running diagnostics...</p>
        </div>
      </div>
    );
  }

  const overallOk = health?.status === 'ok' && daemonStatus?.running;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
              <Settings size={16} className="text-gray-400" />
            </div>
            <div>
              <h1 className="text-lg font-light text-gray-100">System Config</h1>
              <p className="text-[11px] text-gray-600">Backend health, daemon telemetry, and intelligence metrics</p>
            </div>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border ${overallOk ? 'border-emerald-500/15 bg-emerald-500/5' : 'border-red-500/15 bg-red-500/5'}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${overallOk ? 'bg-emerald-400' : 'bg-red-500'}`} />
            <span className={`text-[10px] uppercase tracking-wider ${overallOk ? 'text-emerald-400' : 'text-red-400'}`}>
              {overallOk ? 'Nominal' : 'Degraded'}
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Core system */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 opacity-[0.03]"><Cpu size={80} /></div>
              <div className="flex items-center gap-2 text-[11px] text-indigo-400 uppercase tracking-wider mb-5 relative z-10">
                <Activity size={13} /> Core Subsystems
              </div>
              <div className="space-y-3 relative z-10 text-[12px]">
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">Backend Version</span>
                  <span className="text-gray-300">v{health?.version || 'Unknown'}</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">Daemon Status</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded ${daemonStatus?.running ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'} uppercase tracking-wider`}>
                    {daemonStatus?.running ? 'Active' : 'Offline'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Daemon Cycles</span>
                  <span className="text-gray-300">{daemonStatus?.cycle_count || 0}</span>
                </div>
              </div>
            </motion.div>

            {/* Intelligence Engine */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="card p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 opacity-[0.03]"><Server size={80} /></div>
              <div className="flex items-center gap-2 text-[11px] text-violet-400 uppercase tracking-wider mb-5 relative z-10">
                <Brain size={13} /> Intelligence Engine
              </div>
              <div className="space-y-3 relative z-10 text-[12px]">
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">Circadian Phase</span>
                  <span className="text-gray-300 capitalize">{daemonStatus?.circadian?.current_phase || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">Phase Priority</span>
                  <span className="text-gray-300 capitalize">{daemonStatus?.circadian?.priority || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Active Tasks</span>
                  <span className="text-gray-300">{daemonStatus?.circadian?.current_tasks?.length || 0}</span>
                </div>
              </div>
            </motion.div>

            {/* Data Sources */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 opacity-[0.03]"><Globe size={80} /></div>
              <div className="flex items-center gap-2 text-[11px] text-emerald-400 uppercase tracking-wider mb-5 relative z-10">
                <Globe size={13} /> Data Sources
              </div>
              <div className="space-y-3 relative z-10 text-[12px]">
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">Market Watcher</span>
                  <span className="text-gray-300">{daemonStatus?.watchlist?.length || 0} tickers</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/[0.03] pb-2">
                  <span className="text-gray-500">News Pulse</span>
                  <span className="text-gray-300">{daemonStatus?.topics?.length || 0} topics</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Signals Collected</span>
                  <span className="text-gray-300">{daemonStatus?.signal_queue?.total_signals || daemonStatus?.signals || 0}</span>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Big stats bar */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="card p-8 flex flex-col md:flex-row items-center justify-around relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/[0.03] via-transparent to-violet-500/[0.03]" />
            {[
              { icon: HardDrive, value: memoryStats?.total_cases || 0, label: 'Cases Stored', color: 'text-indigo-400' },
              { icon: Brain, value: curiosity?.total_discoveries || 0, label: 'Discoveries', color: 'text-violet-400' },
              { icon: Zap, value: curiosity?.total_interests || 0, label: 'Topics', color: 'text-amber-400' },
              { icon: Shield, value: daemonStatus?.cycle_count || 0, label: 'Daemon Cycles', color: 'text-emerald-400' },
            ].map((stat, i) => (
              <div key={stat.label} className="flex flex-col items-center gap-2 relative z-10 py-2">
                <stat.icon size={20} className={stat.color + ' mb-1'} />
                <span className="text-2xl font-light text-gray-100">{stat.value}</span>
                <span className="text-[10px] text-gray-600 uppercase tracking-wider">{stat.label}</span>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
