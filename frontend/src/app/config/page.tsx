'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Cpu, HardDrive, Network, Link as LinkIcon, Server, Shield, Activity, Database, Hexagon } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { ConfigStatusResponse, DeepHealthResponse, CaseRecord, SimulationRecord } from '@/lib/types';

export default function ConfigPage() {
  const [config, setConfig] = useState<ConfigStatusResponse | null>(null);
  const [health, setHealth] = useState<DeepHealthResponse | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [simulations, setSimulations] = useState<SimulationRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.getConfigStatus(),
      apiClient.getDeepHealth(),
      apiClient.getCases(),
      apiClient.getSimulations(),
    ])
    .then(([configData, healthData, casesData, simulationsData]) => {
      setConfig(configData);
      setHealth(healthData);
      setCases(casesData);
      setSimulations(simulationsData);
    })
    .catch(console.error)
    .finally(() => setLoading(false));
  }, []);

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

  const overallOk = health?.status === 'ok';

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
              System Configuration
            </h1>
            <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-1">
              Hardware telemetry & agent capability matrix
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
              <span className="text-gray-500">Kernel Version</span>
              <span className="text-gray-300">v{health?.version || 'Unknown'}</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">MiroFish Driver</span>
              <span className={`text-[10px] px-2 py-0.5 rounded ${config?.mirofish_enabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'} uppercase tracking-wider`}>
                 {config?.mirofish_enabled ? 'Active' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-gray-500">Local Vector Map</span>
              <span className="text-gray-300">{health?.checks?.memory_dir_writable ? 'Write OK' : 'Read Only'}</span>
            </div>
          </div>
        </motion.div>

        {/* Neural Endpoints */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-3xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5"><Server size={100} /></div>
          <div className="flex items-center gap-2 text-xs font-mono text-violet-400 uppercase tracking-wider mb-6 relative z-10">
            <Network size={14} /> Neural Endpoints
          </div>
          <div className="space-y-4 relative z-10 text-sm font-mono">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Primary Core</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-300">{health?.checks?.primary_provider || 'N/A'}</span>
                <div className={`w-1.5 h-1.5 rounded-full ${health?.checks?.primary_provider_health?.reachable ? 'bg-emerald-400' : 'bg-red-400'}`} />
              </div>
            </div>
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-gray-500">Fallback Core</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-300">{health?.checks?.fallback_provider || 'N/A'}</span>
                <div className={`w-1.5 h-1.5 rounded-full ${health?.checks?.fallback_provider_health?.reachable ? 'bg-emerald-400' : 'bg-red-400'}`} />
              </div>
            </div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-gray-500">Local Tensor (Ollama)</span>
              <span className={`text-[10px] px-2 py-0.5 rounded ${config?.ollama_enabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-800 text-gray-500'} uppercase tracking-wider`}>
                 {config?.ollama_enabled ? 'Ready' : 'Disabled'}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Data Uplinks */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass rounded-3xl p-6 relative overflow-hidden border-indigo-500/10">
          <div className="absolute top-0 right-0 p-4 opacity-5"><LinkIcon size={100} /></div>
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider mb-6 relative z-10">
            <Database size={14} /> Global Uplinks
          </div>
          <div className="space-y-4 relative z-10 text-sm font-mono">
            {[
              { name: 'Tavily Search', enabled: config?.tavily_enabled },
              { name: 'Alpha Vantage', enabled: config?.alphavantage_enabled },
              { name: 'News API', enabled: config?.newsapi_enabled },
            ].map(uplink => (
              <div key={uplink.name} className="flex items-center justify-between border-b border-white/5 last:border-0 pb-2">
                <span className="text-gray-500">{uplink.name}</span>
                 <span className={`text-[10px] px-2 py-0.5 rounded ${uplink.enabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-800 text-gray-500'} uppercase tracking-wider`}>
                   {uplink.enabled ? 'Streaming' : 'Offline'}
                 </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Memory Modules */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass rounded-3xl p-6 lg:col-span-3 flex flex-col md:flex-row items-center justify-around py-10 relative overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-[200px] bg-indigo-500/5 blur-[80px] rounded-full pointer-events-none" />
          
          <div className="flex flex-col items-center gap-2 relative z-10">
            <HardDrive size={24} className="text-indigo-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{cases.length}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Archived Traces</span>
          </div>

          <div className="h-16 w-px bg-white/10 hidden md:block" />

          <div className="flex flex-col items-center gap-2 relative z-10">
            <Hexagon size={24} className="text-amber-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">{simulations.length}</span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Simulations Executed</span>
          </div>

          <div className="h-16 w-px bg-white/10 hidden md:block" />

          <div className="flex flex-col items-center gap-2 relative z-10">
            <Shield size={24} className="text-emerald-400 mb-2" />
            <span className="text-3xl font-light text-gray-100">
               {Object.keys(health?.checks?.prompt_files || {}).length}
            </span>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Cognitive Protocols</span>
          </div>

        </motion.div>

      </div>
    </div>
  );
}
