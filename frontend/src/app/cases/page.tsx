'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { Layers, ArrowRight, Activity, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';

export default function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCases() {
      try {
        const data = await apiClient.getCases();
        setCases(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadCases();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw size={20} className="text-indigo-400 animate-spin" />
          <span className="text-[12px] text-gray-500">Loading cases...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
              <Layers size={16} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-light text-gray-100">Cases</h1>
              <p className="text-[11px] text-gray-600">Archived intelligence traces and synthesis reports</p>
            </div>
          </div>
          <span className="text-[11px] text-gray-600">{cases.length} records</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {cases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Layers size={28} className="text-gray-700 mb-4" />
            <p className="text-[13px] text-gray-500 mb-4">No cases recorded yet.</p>
            <Link href="/" className="px-5 py-2 rounded-xl border border-indigo-500/20 hover:bg-indigo-500/10 text-[12px] text-indigo-400 transition-all">
              Start a conversation
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl mx-auto">
            {cases.map((record, i) => (
              <motion.div
                key={record.case_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Link
                  href={`/cases/${record.case_id}`}
                  className="group block h-full card hover:border-white/[0.12] transition-all"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Activity size={12} className="text-violet-400" />
                      <span className="text-[10px] text-gray-600 uppercase tracking-wider">
                        {record.case_id.slice(0, 8)}
                      </span>
                    </div>
                    {record.route?.execution_mode && (
                      <span className="px-2 py-0.5 rounded text-[9px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/15 uppercase tracking-wider">
                        {record.route.execution_mode}
                      </span>
                    )}
                  </div>

                  <h3 className="text-[13px] text-gray-300 leading-relaxed line-clamp-2 mb-4 group-hover:text-white transition-colors">
                    {record.user_input}
                  </h3>

                  <div className="flex items-center gap-2 flex-wrap mb-3">
                    {record.route?.domain_pack && record.route.domain_pack !== 'general' && (
                      <span className="px-2 py-0.5 rounded text-[9px] text-gray-400 bg-white/[0.04] uppercase tracking-wider">
                        {record.route.domain_pack}
                      </span>
                    )}
                    {record.simulation_id && (
                      <span className="px-2 py-0.5 rounded text-[9px] text-amber-300 bg-amber-500/10 border border-amber-500/15 uppercase tracking-wider">
                        Simulation
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between border-t border-white/[0.04] pt-3 mt-auto">
                    <span className="text-[10px] text-gray-600">
                      {record.saved_at ? new Date(record.saved_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      View <ArrowRight size={10} />
                    </span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
