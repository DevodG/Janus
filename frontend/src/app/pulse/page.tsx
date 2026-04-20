'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Radio, Database, Moon, Sun, Sunrise, Sunset,
  AlertTriangle, CheckCircle, ExternalLink, Info, RefreshCw
} from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api';

interface DaemonStatus {
  running: boolean;
  cycle_count: number;
  last_run: string;
  circadian: {
    current_phase: string;
    phase_name: string;
    phase_description: string;
    priority: string;
    current_tasks: string[];
  };
  signal_queue?: {
    total_signals: number;
    severity_counts: Record<string, number>;
  };
  signals?: number;
}

interface Alert {
  type: string;
  title: string;
  description: string;
  source: string;
  severity: string;
  timestamp: string;
  url?: string;
}

interface MemoryStats {
  queries: number;
  entities: number;
  insights: number;
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-500/15 text-red-300 border-red-500/25',
    high: 'bg-orange-500/15 text-orange-300 border-orange-500/25',
    medium: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
    low: 'bg-gray-500/15 text-gray-400 border-gray-500/25',
  };
  return <span className={`px-2 py-0.5 rounded border text-[9px] uppercase tracking-wider ${map[severity] || map.low}`}>{severity}</span>;
}

export default function PulsePage() {
  const [status, setStatus] = useState<DaemonStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [memory, setMemory] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const baseUrl = getApiBaseUrl();
    try {
      const [statusRes, alertsRes, memoryRes] = await Promise.all([
        fetch(`${baseUrl}/daemon/status`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/daemon/alerts?limit=20`).then(r => r.ok ? r.json() : []),
        fetch(`${baseUrl}/memory/stats`).then(r => r.ok ? r.json() : null),
      ]);
      if (statusRes) setStatus(statusRes);
      if (alertsRes) setAlerts(Array.isArray(alertsRes) ? alertsRes : []);
      if (memoryRes) setMemory(memoryRes);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const phaseIcons: Record<string, React.ReactNode> = {
    morning: <Sunrise size={16} className="text-amber-400" />,
    daytime: <Sun size={16} className="text-indigo-400" />,
    evening: <Sunset size={16} className="text-violet-400" />,
    night: <Moon size={16} className="text-indigo-300" />,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw size={20} className="text-indigo-400 animate-spin" />
          <p className="text-[12px] text-gray-500">Loading pulse data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <Activity size={16} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-lg font-light text-gray-100">Pulse</h1>
            <p className="text-[11px] text-gray-600">Daemon telemetry, signal queue, and memory graph</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto">
          {/* Top stats grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Circadian phase */}
            {status?.circadian && (
              <div className="card p-5">
                <div className="flex items-center gap-3 mb-4">
                  {phaseIcons[status.circadian.current_phase]}
                  <div>
                    <h3 className="text-[14px] text-gray-200">{status.circadian.phase_name}</h3>
                    <p className="text-[11px] text-gray-600">{status.circadian.phase_description}</p>
                  </div>
                </div>
                <div className="space-y-2 text-[12px]">
                  <div className="flex justify-between"><span className="text-gray-500">Priority</span><span className="text-gray-300 capitalize">{status.circadian.priority}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Active Tasks</span><span className="text-gray-300">{status.circadian.current_tasks.length}</span></div>
                </div>
              </div>
            )}

            {/* Signal Queue */}
            <div className="card p-5">
              <div className="flex items-center gap-2 text-[11px] text-indigo-400 uppercase tracking-wider mb-4">
                <Radio size={12} /> Signal Queue
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center">
                  <div className="text-xl font-light text-white">{status?.signal_queue?.total_signals || status?.signals || 0}</div>
                  <div className="text-[9px] text-gray-600 uppercase tracking-wider">Total</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-light text-red-400">{status?.signal_queue?.severity_counts?.high || 0}</div>
                  <div className="text-[9px] text-gray-600 uppercase tracking-wider">High</div>
                </div>
              </div>
            </div>

            {/* Memory Graph */}
            {memory && (
              <div className="card p-5">
                <div className="flex items-center gap-2 text-[11px] text-violet-400 uppercase tracking-wider mb-4">
                  <Database size={12} /> Memory Graph
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <div className="text-xl font-light text-white">{memory.queries}</div>
                    <div className="text-[9px] text-gray-600 uppercase">Queries</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-light text-indigo-400">{memory.entities}</div>
                    <div className="text-[9px] text-gray-600 uppercase">Entities</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-light text-violet-400">{memory.insights}</div>
                    <div className="text-[9px] text-gray-600 uppercase">Insights</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Daemon status bar */}
          {status && (
            <div className="card p-4 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${status.running ? 'bg-emerald-400' : 'bg-gray-600'}`} />
                  <span className="text-[12px] text-gray-300">{status.running ? 'Daemon active' : 'Daemon offline'}</span>
                </div>
                <div className="flex items-center gap-4 text-[11px] text-gray-600">
                  <span>Cycles: {status.cycle_count}</span>
                  {status.last_run && <span>Last run: {new Date(status.last_run).toLocaleTimeString()}</span>}
                </div>
              </div>
            </div>
          )}

          {/* Alerts feed */}
          <div>
            <div className="text-[11px] text-gray-500 uppercase tracking-wider mb-3">
              Alert Feed — {alerts.length} alerts
            </div>
            {alerts.length > 0 ? (
              <div className="space-y-2">
                {alerts.map((alert, i) => (
                  <motion.div
                    key={`${alert.title}-${i}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="card p-3 hover:border-white/[0.12]"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {alert.severity === 'high' || alert.severity === 'critical'
                          ? <AlertTriangle size={14} className="text-red-400" />
                          : <Info size={14} className="text-amber-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <SeverityBadge severity={alert.severity} />
                          <span className="text-[10px] text-gray-600">{alert.type}</span>
                        </div>
                        <p className="text-[12px] text-gray-300 leading-snug">{alert.title}</p>
                        {alert.description && <p className="text-[11px] text-gray-600 mt-1 line-clamp-1">{alert.description}</p>}
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-[10px] text-gray-700">{new Date(alert.timestamp).toLocaleString()}</span>
                          {alert.url && (
                            <a href={alert.url} target="_blank" rel="noreferrer" className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5">
                              <ExternalLink size={8} /> Read
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="card text-center py-12">
                <CheckCircle size={24} className="text-emerald-500/30 mx-auto mb-3" />
                <p className="text-[13px] text-gray-500">No alerts. All systems normal.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
