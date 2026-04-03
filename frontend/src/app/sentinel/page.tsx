'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, Activity, AlertTriangle, CheckCircle, Clock,
  Zap, RefreshCw, ChevronRight, Hexagon, Eye, Bot,
  TrendingUp, TrendingDown, Minus, X, Check, Cpu
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════
   SENTINEL — Adaptive Maintenance Layer
   ═══════════════════════════════════════════════════════════ */

interface SentinelStatus {
  sentinel_enabled: boolean;
  current_health: boolean;
  last_cycle_at: string | null;
  sentinel_running: boolean;
  agi_progression_index: number;
  alerts_this_week: number;
  patches_applied_this_week: number;
  pending_review_count: number;
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

interface PendingPatch {
  patch_id: string;
  timestamp: string;
  diagnosis: {
    root_cause: string;
    fix_type: string;
    proposed_fix: string;
    confidence: number;
    reasoning: string;
  };
  component: string;
}

interface CapabilitySnapshot {
  snapshot_id: string;
  timestamp: string;
  agi_progression_index: number;
  scores: Record<string, number>;
  delta_from_last: Record<string, number>;
}

// ─── Janus Orb (reused from main page pattern) ──────────────
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

// ─── AGI Progression Ring ────────────────────────────────────
function AgiRing({ value, running }: { value: number; running: boolean }) {
  const size = 160;
  const r = 68;
  const circ = 2 * Math.PI * r;
  const pct = Math.round(value * 100);

  const color = value >= 0.7 ? '#22c55e' : value >= 0.4 ? '#6366f1' : '#f59e0b';

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Glow */}
      <div className="absolute inset-0 rounded-full blur-2xl opacity-20" style={{ background: color }} />
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 160 160">
        <circle cx="80" cy="80" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="6" />
        <motion.circle
          cx="80" cy="80" r={r} fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ * (1 - value) }}
          transition={{ duration: 2, ease: 'easeOut' }}
        />
      </svg>
      <div className="relative z-10 flex flex-col items-center">
        {running ? (
          <JanusOrb size={28} thinking />
        ) : (
          <motion.span
            key={pct}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-3xl font-light text-white"
          >
            {pct}
          </motion.span>
        )}
        <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mt-1">
          {running ? 'scanning' : '%'}
        </span>
      </div>
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
  const [pendingPatches, setPendingPatches] = useState<PendingPatch[]>([]);
  const [capability, setCapability] = useState<CapabilitySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningCycle, setRunningCycle] = useState(false);
  const [activeAlert, setActiveAlert] = useState<Alert | null>(null);
  const [activePatch, setActivePatch] = useState<PendingPatch | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, alertsRes, patchesRes, capRes] = await Promise.all([
        fetch('http://localhost:8000/sentinel/status'),
        fetch('http://localhost:8000/sentinel/alerts?limit=20'),
        fetch('http://localhost:8000/sentinel/patches/pending'),
        fetch('http://localhost:8000/sentinel/capability/current'),
      ]);
      if (statusRes.ok) setStatus(await statusRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (patchesRes.ok) setPendingPatches(await patchesRes.json());
      if (capRes.ok) setCapability(await capRes.json());
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
    try {
      await fetch('http://localhost:8000/sentinel/run-now', { method: 'POST' });
      await fetchData();
    } finally {
      setRunningCycle(false);
    }
  };

  const approvePatch = async (patchId: string) => {
    await fetch(`http://localhost:8000/sentinel/patches/${patchId}/approve`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    setActivePatch(null);
    await fetchData();
  };

  const rejectPatch = async (patchId: string) => {
    await fetch(`http://localhost:8000/sentinel/patches/${patchId}/reject`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    setActivePatch(null);
    await fetchData();
  };

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center pb-20">
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
      <div className="flex h-screen flex-col items-center justify-center pb-20">
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

  const agiIndex = status?.agi_progression_index ?? 0;
  const isRunning = runningCycle || status?.sentinel_running;
  const recentAlerts = [...alerts].reverse().slice(0, 12);

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-10 relative">

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

      {/* ── Main Grid ── */}
      <div className="grid grid-cols-12 gap-6 relative z-10">

        {/* ── LEFT COLUMN: AGI Ring + Capability Dimensions ── */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">

          {/* AGI Progression Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-3xl p-8 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-6 opacity-[0.03]">
              <Cpu size={140} />
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 uppercase tracking-wider mb-6 relative z-10">
              <Activity size={14} /> Capability Index
            </div>

            <div className="flex items-center gap-8 relative z-10">
              <AgiRing value={agiIndex} running={isRunning} />
              <div className="flex-1">
                <div className="text-2xl font-light text-white mb-1">
                  {Math.round(agiIndex * 100)}
                  <span className="text-sm text-gray-500 ml-1">/ 100</span>
                </div>
                <p className="text-xs font-mono text-gray-500 leading-relaxed">
                  Composite health metric across 6 system dimensions
                </p>
                <p className="text-[9px] font-mono text-gray-700 mt-2 leading-relaxed">
                  Vanity metric — not a measure of AGI
                </p>
              </div>
            </div>

            {/* Stat row */}
            <div className="grid grid-cols-3 gap-3 mt-8 pt-6 border-t border-white/5 relative z-10">
              {[
                { label: 'Alerts', value: status?.alerts_this_week ?? 0, color: 'text-amber-400' },
                { label: 'Patches', value: status?.patches_applied_this_week ?? 0, color: 'text-emerald-400' },
                { label: 'Pending', value: status?.pending_review_count ?? 0, color: 'text-violet-400' },
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

        {/* ── RIGHT COLUMN: Alerts + Patches ── */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">

          {/* Pending Patches */}
          <AnimatePresence>
            {pendingPatches.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="glass rounded-3xl p-6 border border-amber-500/20 outline outline-1 outline-amber-500/10"
              >
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-wider">
                    <Zap size={14} />
                    <span>Patches Awaiting Review</span>
                    <span className="ml-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[9px]">
                      {pendingPatches.length}
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  {pendingPatches.map((patch, i) => (
                    <motion.div
                      key={patch.patch_id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => setActivePatch(activePatch?.patch_id === patch.patch_id ? null : patch)}
                      className={`rounded-2xl p-5 cursor-pointer transition-all duration-300 border ${
                        activePatch?.patch_id === patch.patch_id
                          ? 'bg-amber-500/10 border-amber-500/30'
                          : 'bg-white/[0.02] border-white/[0.04] hover:border-amber-500/20 hover:bg-white/[0.04]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-0.5 rounded border border-amber-500/30 bg-amber-500/10 text-[9px] font-mono text-amber-300 uppercase tracking-wider">
                              {patch.diagnosis.fix_type}
                            </span>
                            <span className="text-xs font-mono text-gray-400">{patch.component}</span>
                          </div>
                          <p className="text-sm text-gray-200 leading-relaxed mb-1">{patch.diagnosis.root_cause}</p>
                          <p className="text-xs font-mono text-gray-500 line-clamp-1">{patch.diagnosis.proposed_fix}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] font-mono text-gray-600">
                            {Math.round(patch.diagnosis.confidence * 100)}% conf
                          </span>
                          <ChevronRight size={14} className={`text-gray-600 transition-transform ${activePatch?.patch_id === patch.patch_id ? 'rotate-90' : ''}`} />
                        </div>
                      </div>

                      {/* Expanded detail */}
                      <AnimatePresence>
                        {activePatch?.patch_id === patch.patch_id && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-4 pt-4 border-t border-white/5">
                              <p className="text-xs font-mono text-gray-400 leading-relaxed mb-4">
                                {patch.diagnosis.reasoning}
                              </p>
                              <div className="flex gap-3">
                                <button
                                  onClick={(e) => { e.stopPropagation(); approvePatch(patch.patch_id); }}
                                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 text-xs font-mono uppercase tracking-wider transition-colors"
                                >
                                  <Check size={12} /> Approve
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); rejectPatch(patch.patch_id); }}
                                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-mono uppercase tracking-wider transition-colors"
                                >
                                  <X size={12} /> Reject
                                </button>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Recent Alerts */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="glass rounded-3xl p-6 flex-1"
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-wider">
                <Eye size={14} className="text-indigo-400" />
                <span>Recent Alerts</span>
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

        </div>
      </div>
    </div>
  );
}
