'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, Activity, AlertTriangle, CheckCircle, Clock,
  Zap, RefreshCw, ChevronRight, Eye, Bot,
  TrendingUp, TrendingDown, Minus, X, Check, Cpu,
  AlertCircle, Info, BarChart3, Layers, GitBranch, Brain
} from 'lucide-react';
import { apiClient } from '@/lib/api';

/* ═══════════════════════════════════════════════════════════
   SENTINEL — Signal Validation & Risk Layer
   ═══════════════════════════════════════════════════════════ */

interface SentinelStatus {
  sentinel_enabled: boolean;
  current_health: boolean;
  last_cycle_at: string | null;
  sentinel_running: boolean;
}

interface Alert {
  alert_id: string;
  layer: number;
  component: string;
  issue_type: string;
  severity: string;
  raw_evidence: string;
  timestamp: string;
}

interface CapabilitySnapshot {
  snapshot_id: string;
  timestamp: string;
  agi_progression_index: number;
  scores: Record<string, number>;
  delta_from_last: Record<string, number>;
}

interface CrossCaseInsights {
  effective_sources: Record<string, number>;
  avg_response_times: Record<string, number>;
  complexity_distribution: Record<string, number>;
  total_cases_analyzed: number;
}

interface IntelligenceReport {
  total_cases: number;
  system_personality: Record<string, number>;
  domain_expertise: Record<string, any>;
  cross_case_insights: CrossCaseInsights;
}

interface CacheStats {
  total_entries: number;
  generic_entries: number;
  specific_entries: number;
  hybrid_entries: number;
  expired_entries: number;
  total_hits: number;
  cache_size_mb: number;
  avg_hits_per_entry: number;
}

// ─── Janus Orb ──────────────────────────────────────────────
function JanusOrb({ size = 40, thinking = false }: { size?: number; thinking?: boolean }) {
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'radial-gradient(circle at 30% 30%, #818cf8, #4f46e5 50%, #312e81 100%)',
          boxShadow: thinking
            ? '0 0 30px rgba(99,102,241,0.6), 0 0 60px rgba(99,102,241,0.3)'
            : '0 0 15px rgba(99,102,241,0.3)',
        }}
        animate={thinking ? { scale: [1, 1.1, 1] } : {}}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
      />
      {thinking && (
        <>
          <div className="janus-ring-1 absolute inset-[-6px] rounded-full border border-indigo-400/30" style={{ borderTopColor: 'transparent', borderBottomColor: 'transparent' }} />
          <div className="janus-ring-2 absolute inset-[-12px] rounded-full border border-violet-400/20" style={{ borderLeftColor: 'transparent', borderRightColor: 'transparent' }} />
          <div className="janus-ring-3 absolute inset-[-18px] rounded-full border border-indigo-300/10" style={{ borderTopColor: 'transparent', borderRightColor: 'transparent' }} />
        </>
      )}
    </div>
  );
}

// ─── Capability Ring ─────────────────────────────────────────
function CapabilityRing({ value, running, label }: { value: number; running: boolean; label: string }) {
  const size = 120;
  const r = 48;
  const circ = 2 * Math.PI * r;
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? '#22c55e' : value >= 0.4 ? '#6366f1' : '#f59e0b';

  return (
    <div className="relative flex flex-col items-center" style={{ width: size }}>
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <div className="absolute inset-0 rounded-full blur-xl opacity-10" style={{ background: color }} />
        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="4" />
          <motion.circle
            cx="60" cy="60" r={r} fill="none"
            stroke={color}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ * (1 - value) }}
            transition={{ duration: 2, ease: 'easeOut' }}
          />
        </svg>
        <div className="relative z-10 flex flex-col items-center">
          {running ? (
            <JanusOrb size={20} thinking />
          ) : (
            <motion.span
              key={pct}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-xl font-light text-white"
            >
              {pct}
            </motion.span>
          )}
        </div>
      </div>
      <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mt-1 text-center">
        {label}
      </span>
    </div>
  );
}

// ─── Dimension Bar ───────────────────────────────────────────
function DimensionBar({ label, value, delta }: { label: string; value: number; delta: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? 'bg-emerald-500' : value >= 0.4 ? 'bg-indigo-500' : 'bg-amber-500';

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
          {label.replace(/_/g, ' ')}
        </span>
        <div className="flex items-center gap-1.5">
          {delta > 0.01 ? (
            <TrendingUp size={10} className="text-emerald-400" />
          ) : delta < -0.01 ? (
            <TrendingDown size={10} className="text-red-400" />
          ) : (
            <Minus size={10} className="text-gray-600" />
          )}
          <span className="text-xs font-mono text-gray-300">{pct}%</span>
        </div>
      </div>
      <div className="h-1 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

// ─── Severity Badge ──────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-300 border-red-500/30',
    high: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    medium: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  return (
    <span className={`px-2 py-0.5 rounded border text-[9px] font-mono uppercase tracking-wider ${map[severity] || map.low}`}>
      {severity}
    </span>
  );
}

// ─── Layer Name Map ──────────────────────────────────────────
const LAYER_NAMES: Record<number, string> = {
  1: 'Core Platform',
  2: 'Agents',
  3: 'Domain Packs',
  4: 'Simulation',
  5: 'Knowledge',
  6: 'Sentinel',
};

// ═══════════════════════════════════════════════════════════
//  MAIN PAGE
// ═══════════════════════════════════════════════════════════
export default function SentinelPage() {
  const [status, setStatus] = useState<SentinelStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [capability, setCapability] = useState<CapabilitySnapshot | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningCycle, setRunningCycle] = useState(false);
  const [activeAlert, setActiveAlert] = useState<Alert | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'intelligence'>('overview');

  const crossCaseInsights: CrossCaseInsights = intelligence?.cross_case_insights || {
    effective_sources: {},
    avg_response_times: {},
    complexity_distribution: {},
    total_cases_analyzed: 0,
  };

  const fetchData = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7860';
    try {
      const [statusRes, alertsRes, capRes, intelRes, cacheRes] = await Promise.all([
        apiClient.getSentinelStatus(),
        apiClient.getSentinelAlerts(20),
        apiClient.getSentinelCapability(),
        fetch(`${baseUrl}/intelligence/report`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/cache/stats`).then(r => r.ok ? r.json() : null),
      ]);
      if (statusRes) setStatus(statusRes);
      if (alertsRes) setAlerts(Array.isArray(alertsRes) ? alertsRes : []);
      if (capRes) setCapability(capRes);
      if (intelRes) setIntelligence(intelRes);
      if (cacheRes) setCacheStats(cacheRes);
    } catch {
      // silent — backend may be starting
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 30000);
    return () => clearInterval(t);
  }, [fetchData]);

  const runCycleNow = async () => {
    setRunningCycle(true);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7860';
    try {
      await fetch(`${baseUrl}/sentinel/run-now`, { method: 'POST' });
      await fetchData();
    } finally {
      setRunningCycle(false);
    }
  };

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-6">
          <JanusOrb size={56} thinking />
          <p className="text-xs font-mono text-indigo-400 uppercase tracking-widest animate-pulse">
            Initializing Sentinel Layer...
          </p>
        </div>
      </div>
    );
  }

  // ── Disabled ──
  if (!status?.sentinel_enabled) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <div className="glass rounded-3xl p-12 text-center max-w-md">
          <Shield size={40} className="text-gray-600 mx-auto mb-6" />
          <h2 className="text-lg font-light tracking-[0.15em] text-gradient-subtle uppercase mb-3">
            Sentinel Offline
          </h2>
          <p className="text-sm font-mono text-gray-500">
            Set <span className="text-indigo-300">SENTINEL_ENABLED=true</span> in .env to activate adaptive maintenance.
          </p>
        </div>
      </div>
    );
  }

  const isRunning = runningCycle || status?.sentinel_running;
  const recentAlerts = [...alerts].reverse().slice(0, 12);
  const domainExpertise = intelligence?.domain_expertise || {};

  return (
    <div className="h-full overflow-y-auto">
    <div className="max-w-[1400px] mx-auto px-6 py-8 relative">

      {/* ── Background flare ── */}
      <div className="fixed top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-indigo-500/5 blur-[120px] rounded-full pointer-events-none" />

      {/* ── Header ── */}
      <header className="flex items-end justify-between mb-10 relative z-10">
        <div className="flex items-center gap-5">
          <div className="relative w-14 h-14 flex items-center justify-center">
            <div className="absolute inset-0 rounded-2xl bg-indigo-500/10 border border-indigo-500/20" />
            <Shield size={22} className="text-indigo-400 relative z-10" />
            {isRunning && (
              <div className="absolute inset-0 rounded-2xl border-2 border-indigo-400/50 border-t-transparent animate-spin" />
            )}
          </div>
          <div>
            <h1 className="text-3xl font-light tracking-[0.15em] text-gradient-subtle uppercase">
              Sentinel
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-1.5 h-1.5 rounded-full ${status?.current_health ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
              <span className={`text-[10px] font-mono uppercase tracking-widest ${status?.current_health ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                {isRunning ? 'Cycle Running' : status?.current_health ? 'All Systems Nominal' : 'Issues Detected'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {status?.last_cycle_at && (
            <div className="glass px-4 py-2 rounded-xl border-white/5 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
              Last cycle: {new Date(status.last_cycle_at).toLocaleTimeString()}
            </div>
          )}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={runCycleNow}
            disabled={isRunning}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-all duration-200 text-xs font-mono uppercase tracking-wider"
          >
            <RefreshCw size={13} className={isRunning ? 'animate-spin' : ''} />
            {isRunning ? 'Running...' : 'Run Cycle'}
          </motion.button>
        </div>
      </header>

      {/* ── Tab Navigation ── */}
      <nav className="flex gap-1 mb-8 relative z-10">
        {[
          { id: 'overview' as const, label: 'Overview', icon: Shield },
          { id: 'alerts' as const, label: 'Alerts', icon: AlertTriangle },
          { id: 'intelligence' as const, label: 'Intelligence', icon: Brain },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 text-sm ${
              activeTab === tab.id ? 'text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="sentinelTabIndicator"
                className="absolute inset-0 glass rounded-xl"
                transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
              />
            )}
            <tab.icon size={15} className="relative z-10" />
            <span className="relative z-10 font-mono text-xs uppercase tracking-wider">{tab.label}</span>
            {tab.id === 'alerts' && alerts.length > 0 && (
              <span className="relative z-10 px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[9px] font-mono">
                {alerts.length}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* ── Main Content ── */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">

          {/* ── OVERVIEW TAB ── */}
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="grid grid-cols-12 gap-6"
            >
              {/* LEFT: System Health */}
              <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
                {/* System Status Card */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass rounded-3xl p-8 relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 p-6 opacity-[0.03]">
                    <Cpu size={140} />
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 uppercase tracking-wider mb-6 relative z-10">
                    <Activity size={14} /> System Health
                  </div>

                  <div className="flex items-center gap-6 relative z-10">
                    <CapabilityRing value={capability?.agi_progression_index ?? 0} running={isRunning} label="Health" />
                    <div className="flex-1">
                      <div className="text-2xl font-light text-white mb-1">
                        {Math.round((capability?.agi_progression_index ?? 0) * 100)}
                        <span className="text-sm text-gray-500 ml-1">/ 100</span>
                      </div>
                      <p className="text-xs font-mono text-gray-500 leading-relaxed">
                        Composite health metric across system dimensions
                      </p>
                    </div>
                  </div>

                  {/* Stat row */}
                  <div className="grid grid-cols-2 gap-3 mt-8 pt-6 border-t border-white/5 relative z-10">
                    {[
                      { label: 'Total Cases', value: intelligence?.total_cases ?? 0, color: 'text-indigo-400' },
                      { label: 'Cache Hits', value: cacheStats?.total_hits ?? 0, color: 'text-emerald-400' },
                      { label: 'Cache Entries', value: cacheStats?.total_entries ?? 0, color: 'text-violet-400' },
                      { label: 'Domains', value: Object.keys(domainExpertise).length, color: 'text-amber-400' },
                    ].map((s) => (
                      <div key={s.label} className="text-center">
                        <div className={`text-xl font-light ${s.color}`}>{s.value}</div>
                        <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest mt-0.5">{s.label}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Capability Dimensions */}
                {capability && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass rounded-3xl p-6"
                  >
                    <div className="flex items-center gap-2 text-xs font-mono text-violet-400 uppercase tracking-wider mb-6">
                      <TrendingUp size={14} /> Dimension Scores
                    </div>
                    <div className="space-y-4">
                      {Object.entries(capability.scores).map(([key, val]) => (
                        <DimensionBar
                          key={key}
                          label={key}
                          value={val}
                          delta={capability.delta_from_last?.[key] ?? 0}
                        />
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* RIGHT: Intelligence + Cache */}
              <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                {/* Domain Expertise */}
                {Object.keys(domainExpertise).length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass rounded-3xl p-6"
                  >
                    <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider mb-6">
                      <Brain size={14} /> Domain Expertise
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(domainExpertise).map(([domain, data]: [string, any]) => (
                        <motion.div
                          key={domain}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="glass rounded-xl p-4 border border-white/[0.06]"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-sm font-mono text-gray-200 capitalize">{domain}</h4>
                            <span className="text-[10px] font-mono text-gray-500">{data.case_count} cases</span>
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs font-mono">
                              <span className="text-gray-500">Success Rate</span>
                              <span className="text-gray-300">{Math.round(data.success_rate * 100)}%</span>
                            </div>
                            <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                              <motion.div
                                className="h-full rounded-full bg-emerald-500"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.round(data.success_rate * 100)}%` }}
                                transition={{ duration: 1.5, ease: 'easeOut' }}
                              />
                            </div>
                            {data.key_entities && data.key_entities.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {data.key_entities.slice(0, 5).map((entity: string, i: number) => (
                                  <span key={`${domain}-entity-${i}`} className="text-[9px] font-mono text-gray-500 bg-white/5 px-1.5 py-0.5 rounded">
                                    {entity}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Cache Stats */}
                {cacheStats && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass rounded-3xl p-6"
                  >
                    <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-wider mb-6">
                      <Layers size={14} /> Cache Performance
                    </div>
                    <div className="grid grid-cols-4 gap-4">
                      {[
                        { label: 'Total Entries', value: cacheStats.total_entries, color: 'text-indigo-400' },
                        { label: 'Total Hits', value: cacheStats.total_hits, color: 'text-emerald-400' },
                        { label: 'Hit Rate', value: cacheStats.total_entries > 0 ? `${Math.round((cacheStats.total_hits / (cacheStats.total_entries + cacheStats.total_hits)) * 100)}%` : '0%', color: 'text-violet-400' },
                        { label: 'Cache Size', value: `${cacheStats.cache_size_mb.toFixed(2)} MB`, color: 'text-amber-400' },
                      ].map((s) => (
                        <div key={s.label} className="text-center">
                          <div className={`text-xl font-light ${s.color}`}>{s.value}</div>
                          <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest mt-0.5">{s.label}</div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Cross-Case Insights */}
                {crossCaseInsights.total_cases_analyzed > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass rounded-3xl p-6"
                  >
                    <div className="flex items-center gap-2 text-xs font-mono text-blue-400 uppercase tracking-wider mb-6">
                      <GitBranch size={14} /> Cross-Case Insights
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {crossCaseInsights.effective_sources && Object.keys(crossCaseInsights.effective_sources).length > 0 && (
                        <div>
                          <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Effective Sources</h4>
                          <div className="space-y-2">
                            {Object.entries(crossCaseInsights.effective_sources)
                              .sort(([, a], [, b]) => (b as number) - (a as number))
                              .slice(0, 5)
                              .map(([source, score]) => (
                                <div key={source} className="flex items-center justify-between text-xs font-mono">
                                  <span className="text-gray-400 truncate mr-2">{source}</span>
                                  <span className="text-emerald-400">{Math.round((score as number) * 100)}%</span>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                      {crossCaseInsights.avg_response_times && Object.keys(crossCaseInsights.avg_response_times).length > 0 && (
                        <div>
                          <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Avg Response Times</h4>
                          <div className="space-y-2">
                            {Object.entries(crossCaseInsights.avg_response_times).map(([domain, time]) => (
                              <div key={domain} className="flex items-center justify-between text-xs font-mono">
                                <span className="text-gray-400 capitalize">{domain}</span>
                                <span className="text-gray-300">{time}s</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Recent Alerts Preview */}
                {recentAlerts.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass rounded-3xl p-6"
                  >
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-wider">
                        <Eye size={14} className="text-indigo-400" />
                        <span>Recent Alerts</span>
                        <span className="ml-1 px-2 py-0.5 rounded-full bg-white/5 text-gray-500 text-[9px]">
                          {recentAlerts.length}
                        </span>
                      </div>
                      <button
                        onClick={() => setActiveTab('alerts')}
                        className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        View All →
                      </button>
                    </div>
                    <div className="space-y-3">
                      {recentAlerts.slice(0, 3).map((alert, i) => (
                        <motion.div
                          key={alert.alert_id}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.04 }}
                          className="rounded-xl p-3 bg-white/[0.02] border border-white/[0.04]"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <SeverityBadge severity={alert.severity} />
                            <span className="text-xs font-mono text-gray-300">
                              {LAYER_NAMES[alert.layer] || `Layer ${alert.layer}`}
                            </span>
                            <span className="text-[10px] font-mono text-gray-600">·</span>
                            <span className="text-[10px] font-mono text-gray-500">{alert.component}</span>
                          </div>
                          <p className="text-xs font-mono text-gray-400 line-clamp-1">{alert.raw_evidence}</p>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}

          {/* ── ALERTS TAB ── */}
          {activeTab === 'alerts' && (
            <motion.div
              key="alerts"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="glass rounded-3xl p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-wider">
                  <AlertTriangle size={14} className="text-amber-400" />
                  <span>All Alerts</span>
                  {recentAlerts.length > 0 && (
                    <span className="ml-1 px-2 py-0.5 rounded-full bg-white/5 text-gray-500 text-[9px]">
                      {recentAlerts.length}
                    </span>
                  )}
                </div>
              </div>

              {recentAlerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <CheckCircle size={32} className="text-emerald-500/30 mb-4" />
                  <p className="text-sm font-mono text-gray-500">No alerts detected.</p>
                  <p className="text-xs font-mono text-gray-700 mt-1">All systems operating within normal parameters.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentAlerts.map((alert, i) => (
                    <motion.div
                      key={alert.alert_id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                      onClick={() => setActiveAlert(activeAlert?.alert_id === alert.alert_id ? null : alert)}
                      className={`rounded-2xl p-4 cursor-pointer transition-all duration-300 border ${
                        activeAlert?.alert_id === alert.alert_id
                          ? 'bg-white/[0.05] border-indigo-500/30'
                          : 'bg-white/[0.02] border-white/[0.04] hover:border-white/10 hover:bg-white/[0.03]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <SeverityBadge severity={alert.severity} />
                            <span className="text-xs font-mono text-gray-300">
                              {LAYER_NAMES[alert.layer] || `Layer ${alert.layer}`}
                            </span>
                            <span className="text-[10px] font-mono text-gray-600">·</span>
                            <span className="text-[10px] font-mono text-gray-500">{alert.component}</span>
                          </div>
                          <p className="text-xs font-mono text-gray-400 line-clamp-1">{alert.raw_evidence}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-[9px] font-mono text-gray-600">
                            {new Date(alert.timestamp).toLocaleTimeString()}
                          </div>
                          <div className="text-[9px] font-mono text-gray-700">
                            {new Date(alert.timestamp).toLocaleDateString()}
                          </div>
                        </div>
                      </div>

                      <AnimatePresence>
                        {activeAlert?.alert_id === alert.alert_id && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-3 pt-3 border-t border-white/5">
                              <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                                <Bot size={10} /> Evidence
                              </div>
                              <p className="text-xs font-mono text-gray-400 leading-relaxed">
                                {alert.raw_evidence}
                              </p>
                              <div className="flex items-center gap-3 mt-3 text-[9px] font-mono text-gray-600 uppercase tracking-wider">
                                <span>Type: {alert.issue_type}</span>
                                <span>·</span>
                                <span>Layer {alert.layer}</span>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* ── INTELLIGENCE TAB ── */}
          {activeTab === 'intelligence' && (
            <motion.div
              key="intelligence"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* System Personality */}
              {intelligence?.system_personality && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass rounded-3xl p-6"
                >
                  <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 uppercase tracking-wider mb-6">
                    <Brain size={14} /> System Personality
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(intelligence.system_personality).map(([key, val]) => (
                      <div key={key} className="text-center">
                        <div className="text-lg font-light text-white">{typeof val === 'number' ? Math.round(val * 100) : val}</div>
                        <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest mt-0.5">{key.replace(/_/g, ' ')}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Domain Expertise Detail */}
              {Object.keys(domainExpertise).length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="glass rounded-3xl p-6"
                >
                  <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-wider mb-6">
                    <Layers size={14} /> Domain Expertise Detail
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {Object.entries(domainExpertise).map(([domain, data]: [string, any]) => (
                      <div key={domain} className="glass rounded-xl p-5 border border-white/[0.06]">
                        <div className="flex items-center justify-between mb-4">
                          <h4 className="text-sm font-mono text-gray-200 capitalize">{domain}</h4>
                          <span className="text-[10px] font-mono text-gray-500">{data.case_count} cases</span>
                        </div>
                        <div className="space-y-3">
                          <div>
                            <div className="flex justify-between text-xs font-mono mb-1">
                              <span className="text-gray-500">Success Rate</span>
                              <span className="text-gray-300">{Math.round(data.success_rate * 100)}%</span>
                            </div>
                            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                              <motion.div
                                className="h-full rounded-full bg-emerald-500"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.round(data.success_rate * 100)}%` }}
                                transition={{ duration: 1.5, ease: 'easeOut' }}
                              />
                            </div>
                          </div>
                          {data.trusted_sources && data.trusted_sources.length > 0 && (
                            <div>
                              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-2">Trusted Sources</div>
                              <div className="space-y-1">
                                {data.trusted_sources.slice(0, 3).map((s: any, i: number) => (
                                  <div key={`${domain}-source-${i}`} className="flex justify-between text-xs font-mono">
                                    <span className="text-gray-400 truncate mr-2">{s.source}</span>
                                    <span className="text-emerald-400">{Math.round(s.trust * 100)}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {data.key_entities && data.key_entities.length > 0 && (
                            <div>
                              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-2">Key Entities</div>
                              <div className="flex flex-wrap gap-1">
                                {data.key_entities.slice(0, 8).map((entity: string, i: number) => (
                                  <span key={`${domain}-entity-${i}`} className="text-[9px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
                                    {entity}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Cross-Case Insights Detail */}
              {crossCaseInsights.total_cases_analyzed > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="glass rounded-3xl p-6"
                >
                  <div className="flex items-center gap-2 text-xs font-mono text-blue-400 uppercase tracking-wider mb-6">
                    <GitBranch size={14} /> Cross-Case Pattern Analysis
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {crossCaseInsights.effective_sources && Object.keys(crossCaseInsights.effective_sources).length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Source Effectiveness</h4>
                        <div className="space-y-2">
                          {Object.entries(crossCaseInsights.effective_sources)
                            .sort(([, a], [, b]) => (b as number) - (a as number))
                            .map(([source, score]) => (
                              <div key={source} className="flex items-center justify-between text-xs font-mono">
                                <span className="text-gray-400 truncate mr-2">{source}</span>
                                <span className="text-emerald-400">{Math.round((score as number) * 100)}%</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                    {crossCaseInsights.avg_response_times && Object.keys(crossCaseInsights.avg_response_times).length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Response Times by Domain</h4>
                        <div className="space-y-2">
                          {Object.entries(crossCaseInsights.avg_response_times).map(([domain, time]) => (
                            <div key={domain} className="flex items-center justify-between text-xs font-mono">
                              <span className="text-gray-400 capitalize">{domain}</span>
                              <span className="text-gray-300">{time}s</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {crossCaseInsights.complexity_distribution && Object.keys(crossCaseInsights.complexity_distribution).length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Complexity Distribution</h4>
                        <div className="space-y-2">
                          {Object.entries(crossCaseInsights.complexity_distribution).map(([complexity, count]) => (
                            <div key={complexity} className="flex items-center justify-between text-xs font-mono">
                              <span className="text-gray-400 capitalize">{complexity}</span>
                              <span className="text-gray-300">{count as number} cases</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
    </div>
  );
}
