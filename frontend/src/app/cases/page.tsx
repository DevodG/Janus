'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { FolderOpen, ArrowRight, Activity, Cpu } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';
import LoadingSpinner from '@/components/common/LoadingSpinner';

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
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
          <span className="text-xs font-mono text-indigo-400 uppercase tracking-widest">Accessing Archives...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1480px] mx-auto px-10 py-12">
      <header className="mb-10 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-2xl glass flex items-center justify-center">
              <FolderOpen size={18} className="text-indigo-400" />
            </div>
            <h1 className="text-2xl font-light tracking-[0.15em] text-gradient-subtle uppercase">
              Intelligence Cases
            </h1>
          </div>
          <p className="text-sm font-mono text-gray-500 max-w-xl">
            Archived cognitive traces, agent execution logs, and final synthesis reports from prior intelligence routing scenarios.
          </p>
        </div>
        
        <div className="flex items-center gap-2 glass px-4 py-2 rounded-xl border-white/5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">
            {cases.length} records indexed
          </span>
        </div>
      </header>

      {cases.length === 0 ? (
        <div className="w-full aspect-[3/1] glass rounded-3xl flex flex-col items-center justify-center">
          <Cpu size={32} className="text-gray-700 mb-4" />
          <p className="text-sm font-mono text-gray-500">No cognitive traces recorded.</p>
          <Link href="/" className="mt-6 px-6 py-2 rounded-full border border-indigo-500/30 hover:bg-indigo-500/10 text-xs font-mono text-indigo-300 transition-colors uppercase tracking-widest">
            Initialize Scan
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {cases.map((record, i) => (
            <motion.div
              key={record.case_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.5 }}
            >
              <Link 
                href={`/cases/${record.case_id}`}
                className="group block h-full p-6 glass rounded-2xl border border-white/[0.04] hover:border-indigo-500/30 hover:bg-white/[0.04] transition-all duration-500"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-violet-400" />
                    <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                      ID: {record.case_id.slice(0, 8)}
                    </span>
                  </div>
                  {record.route?.execution_mode && (
                    <span className="px-2 py-1 rounded border border-indigo-500/20 bg-indigo-500/10 text-[9px] font-mono text-indigo-300 uppercase tracking-wider">
                      {record.route.execution_mode}
                    </span>
                  )}
                </div>

                <h3 className="text-sm font-medium text-gray-200 leading-relaxed line-clamp-2 mb-6 group-hover:text-white transition-colors">
                  {record.user_input}
                </h3>

                <div className="mt-auto">
                  <div className="flex items-center gap-2 flex-wrap mb-4">
                    {record.route?.domain_pack && record.route.domain_pack !== 'general' && (
                      <span className="px-2 py-1 rounded bg-white/5 text-[9px] font-mono text-gray-400 uppercase tracking-wider">
                        {record.route.domain_pack}
                      </span>
                    )}
                    {record.route?.task_family && (
                      <span className="px-2 py-1 rounded bg-white/5 text-[9px] font-mono text-gray-400 uppercase tracking-wider">
                        {record.route.task_family}
                      </span>
                    )}
                    {record.simulation_id && (
                      <span className="px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] font-mono text-amber-300 uppercase tracking-wider">
                        Simulation Active
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between border-t border-white/5 pt-4">
                    <span className="text-[10px] font-mono text-gray-500">
                      {record.saved_at ? new Date(record.saved_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-mono text-indigo-400 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity translate-x-2 group-hover:translate-x-0 duration-300">
                      View Trace <ArrowRight size={10} />
                    </span>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
