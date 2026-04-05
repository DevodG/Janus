'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Activity, Radio, Database, Brain, Zap, Clock, Shield, Server, Globe, Hexagon, HardDrive, Cpu, Network, Link as LinkIcon, Settings } from 'lucide-react';

export default function ConfigPage() {
  const [daemonStatus, setDaemonStatus] = useState<any>(null);
  const [curiosity, setCuriosity] = useState<any>(null);
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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
    } catch (console.error) {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center pb-20">
        <div className="flex flex-col items-center gap-4">
          <Settings size={32} className="text-gray-500/50 animate-[spin_4s_linear_infinite]" />
          <p className="text-xs font-mono text-gray-500 uppercase tracking-widest animate-pulse">Running System Diagnostics...</p>
        </div>
      </div>
    );
  }

  const overallOk = health?.status === 'ok' && daemonStatus?.running;

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-12">
      <header className="mb-12 flex items-end justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl glass flex items-center justify-center border border-white/5 relative overflow-hidden">
             <div className="absolute inset-0 bg-gray-500/10" />
             <Settings size={20} className="text-gray-400 relative z-10" />
          </div>
          <div>
            <h1 className="text-3xl font-light tracking-[0.15em] text-gradient-subtle uppercase">
              System Status
            </h1>
            <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-1">
              Cloud backend health, daemon telemetry, and intelligence metrics
            </p>
          </div>
        </div>

        <div className={`flex items-center gap-3 px-4 py-2 rounded-xl glass border ${overallOk ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
          <div className={`w-2 h-2 rounded-full ${overallOk ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
          <span className={`text-[10px] font-mono uppercase tracking-widest ${overallOk ? 'text-emerald-300' : 'text-red-300'}`}>
            System {overallOk ? 'Nominal' : 'Degraded'}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Core System Status */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }} className="glass rounded-3xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5"><Cpu size={100} /></div>
          <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 uppercase tracking-wider mb-6 relative z-10">
            <Activity size={14} /> Core Subsystems
          </div>
          <div className="space-y-4 relative z-10 text-sm font-mono">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Backend Version</span>
              <span className="text-gray-300">v{health?.version || 'Unknown'}</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Daemon Status</span>
              <span className={`text-[10px] px-2 py-0.5 rounded ${daemonStatus?.running ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'} uppercase tracking-wider`}>
                 {daemonStatus?.running ? 'Active' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-gray-500">Daemon Cycles</span>
              <span className="text-gray-300">{daemonStatus?.cycle_count || 0}</span>
            </div>
          </div>
        </motion.div>

        {/* Neural Endpoints */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-3xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5"><Server size={100} /></div>
          <div className="flex items-center gap-2 text-xs font-mono text-violet-400 uppercase tracking-wider mb-6 relative z-10">
            <Network size={14} /> Intelligence Engine
          </div>
          <div className="space-y-4 relative z-10 text-sm font-mono">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Circadian Phase</span>
              <span className="text-gray-300 capitalize">{daemonStatus?.circadian?.current_phase || 'N/A'}</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Phase Priority</span>
              <span className="text-gray-300 capitalize">{daemonStatus?.circadian?.priority || 'N/A'}</span>
            </div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-gray-500">Active Tasks</span>
              <span className="text-gray-300">{daemonStatus?.circadian?.current_tasks?.length || 0}</span>
            </div>
          </div>
        </motion.div>

        {/* Data Uplinks */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass rounded-3xl p-6 relative overflow-hidden border-indigo-500/10">
          <div className="absolute top-0 right-0 p-4 opacity-5"><LinkIcon size={100} /></div>
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider mb-6 relative z-10">
            <Globe size={14} /> Data Sources
          </div>
          <div className="space-y-4 relative z-10 text-sm font-mono">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Market Watcher</span>
              <span className="text-gray-300">{daemonStatus?.watchlist?.length || 0} tickers</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">News Pulse</span>
              <span className="text-gray-300">{daemonStatus?.topics?.length || 0} topics</span>
            </div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-gray-500">Signals Collected</span>
              <span className="text-gray-300">{daemonStatus?.signal_queue?.total_signals || daemonStatus?.signals || 0}</span>
            </div>
          </div>
        </motion.div>

        {/* Memory Modules */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass rounded-3xl p-6 lg:col-span-3 flex flex-col md:flex-row items-center justify-around py-10 relative overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-[200px] bg-indigo-500/5 blur-[80px] rounded-full pointer-events-none" />
          
          <div className="flex flex-col items-center gap-2 relative z-10">
            <HardDrive size={24} className="text-indigo-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{memoryStats?.total_cases || 0}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Cases Stored</span>
          </div>

          <div className="h-16 w-px bg-white/10 hidden md:block" />

          <div className="flex flex-col items-center gap-2 relative z-10">
            <Brain size={24} className="text-violet-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{curiosity?.total_discoveries || 0}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Curiosity Discoveries</span>
          </div>

          <div className="h-16 w-px bg-white/10 hidden md:block" />

          <div className="flex flex-col items-center gap-2 relative z-10">
            <Zap size={24} className="text-amber-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{curiosity?.total_interests || 0}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Topics of Interest</span>
          </div>

          <div className="h-16 w-px bg-white/10 hidden md:block" />

          <div className="flex flex-col items-center gap-2 relative z-10">
            <Shield size={24} className="text-emerald-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{daemonStatus?.cycle_count || 0}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Daemon Cycles</span>
          </div>

        </motion.div>

      </div>
    </div>
  );
}
