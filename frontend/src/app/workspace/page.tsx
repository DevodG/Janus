'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Brain, Sparkles, RefreshCw, Lightbulb } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api';

export default function WorkspacePage() {
  const [curiosity, setCuriosity] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchData = useCallback(async () => {
    const baseUrl = getApiBaseUrl();
    try {
      const res = await fetch(`${baseUrl}/daemon/curiosity`);
      if (res.ok) setCuriosity(await res.json());
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const triggerCuriosity = async () => {
    setTriggering(true);
    const baseUrl = getApiBaseUrl();
    try {
      const res = await fetch(`${baseUrl}/daemon/curiosity/now`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setCuriosity((prev: any) => prev
          ? { ...prev, discoveries: [...(prev.discoveries || []), ...(data.discoveries || [])], total_discoveries: (prev.total_discoveries || 0) + (data.discoveries || []).length }
          : data
        );
      }
    } catch { /* silent */ }
    finally { setTriggering(false); }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
              <Brain size={16} className="text-violet-400" />
            </div>
            <div>
              <h1 className="text-lg font-light text-gray-100">Workspace</h1>
              <p className="text-[11px] text-gray-600">Janus curiosity engine — autonomous discovery</p>
            </div>
          </div>
          <button
            onClick={triggerCuriosity}
            disabled={triggering}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/15 text-[12px] text-violet-400 transition-all disabled:opacity-40"
          >
            <Sparkles size={12} className={triggering ? 'animate-pulse' : ''} />
            {triggering ? 'Exploring...' : 'Explore'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <RefreshCw size={20} className="text-violet-400 animate-spin" />
            <p className="text-[12px] text-gray-500">Loading workspace...</p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="card p-5 text-center">
                <div className="text-2xl font-light text-white">{curiosity?.total_discoveries || 0}</div>
                <div className="text-[10px] text-gray-600 uppercase tracking-wider mt-1">Discoveries</div>
              </div>
              <div className="card p-5 text-center">
                <div className="text-2xl font-light text-violet-400">{curiosity?.total_interests || 0}</div>
                <div className="text-[10px] text-gray-600 uppercase tracking-wider mt-1">Topics of Interest</div>
              </div>
            </div>

            {/* Discoveries list */}
            <div className="card p-5">
              <div className="flex items-center gap-2 text-[11px] text-violet-400 uppercase tracking-wider mb-5">
                <Lightbulb size={13} /> Recent Discoveries
              </div>
              <div className="space-y-3">
                {(curiosity?.discoveries || []).slice(-10).reverse().map((d: any, i: number) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="p-3 rounded-xl border border-white/[0.04] hover:border-white/[0.08] transition-colors"
                    style={{ background: 'rgba(255,255,255,0.015)' }}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full">{d.topic}</span>
                      <span className="text-[10px] text-gray-700">{new Date(d.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-[13px] text-gray-300 leading-relaxed">{d.insight}</p>
                  </motion.div>
                ))}
                {(!curiosity?.discoveries || curiosity.discoveries.length === 0) && (
                  <div className="text-center py-12">
                    <Brain size={28} className="text-gray-700 mx-auto mb-3" />
                    <p className="text-[13px] text-gray-500">No discoveries yet.</p>
                    <p className="text-[11px] text-gray-700 mt-1">Click &quot;Explore&quot; to trigger the curiosity engine.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Interests */}
            {curiosity?.interests && Object.keys(curiosity.interests).length > 0 && (
              <div className="card p-5">
                <div className="text-[11px] text-gray-500 uppercase tracking-wider mb-4">Topics of Interest</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(curiosity.interests).map(([topic, score]: [string, any]) => (
                    <span key={topic} className="px-3 py-1.5 rounded-full text-[11px] text-gray-400 border border-white/[0.06] bg-white/[0.02]">
                      {topic} <span className="text-gray-600 ml-1">{typeof score === 'number' ? Math.round(score * 100) + '%' : ''}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
