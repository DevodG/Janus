'use client';

import { useEffect, useState } from 'react';
import { Terminal, FileCode2, Brain, Search, Shield, Info, RefreshCw } from 'lucide-react';

const PROMPTS = [
  { name: 'switchboard', label: 'Switchboard', icon: Search, description: 'Routes queries to the right agent pipeline. Classifies domain, complexity, and required tools.', color: 'text-indigo-400' },
  { name: 'research', label: 'Research', icon: FileCode2, description: 'Gathers and analyzes information from web search, news, knowledge base, and API discovery.', color: 'text-violet-400' },
  { name: 'synthesizer', label: 'Synthesizer', icon: Brain, description: 'Produces the final answer by combining research, planning, and simulation outputs.', color: 'text-emerald-400' },
  { name: 'verifier', label: 'Verifier', icon: Shield, description: 'Quality gate — checks analysis for logical soundness, evidence alignment, and completeness.', color: 'text-amber-400' },
];

export default function PromptsPage() {
  const [selectedPrompt, setSelectedPrompt] = useState<typeof PROMPTS[0] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => { setSelectedPrompt(PROMPTS[0]); setLoading(false); }, 300);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw size={20} className="text-indigo-400 animate-spin" />
          <p className="text-[12px] text-gray-500">Loading protocols...</p>
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
            <Terminal size={16} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-light text-gray-100">Prompt Lab</h1>
            <p className="text-[11px] text-gray-600">Agent protocol instruction sets for the Janus pipeline</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left: Protocol selector */}
        <div className="w-64 shrink-0 border-r border-white/[0.04] p-4 overflow-y-auto space-y-2">
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-3 px-1">Agent Protocols</div>
          {PROMPTS.map(p => {
            const isActive = selectedPrompt?.name === p.name;
            const Icon = p.icon;
            return (
              <button
                key={p.name}
                onClick={() => setSelectedPrompt(p)}
                className={`w-full text-left p-3 rounded-xl transition-all border group ${
                  isActive
                    ? 'bg-white/[0.05] border-indigo-500/20'
                    : 'border-transparent hover:bg-white/[0.03] hover:border-white/[0.04]'
                }`}
              >
                <div className="flex items-center gap-2.5 mb-1">
                  <Icon size={14} className={isActive ? p.color : 'text-gray-600'} />
                  <span className={`text-[12px] ${isActive ? 'text-gray-200' : 'text-gray-500 group-hover:text-gray-300'}`}>
                    {p.label}
                  </span>
                </div>
                <p className="text-[10px] text-gray-600 line-clamp-2 pl-[22px]">{p.description}</p>
              </button>
            );
          })}
        </div>

        {/* Right: Detail view */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedPrompt ? (
            <div className="max-w-2xl">
              <div className="flex items-center gap-3 mb-5">
                <selectedPrompt.icon size={22} className={selectedPrompt.color} />
                <h2 className="text-xl font-light text-gray-100">{selectedPrompt.label}</h2>
              </div>
              <p className="text-[13px] text-gray-400 leading-relaxed mb-6">{selectedPrompt.description}</p>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase tracking-wider mb-3">
                  <Info size={11} /> Protocol Details
                </div>
                {[
                  ['Agent Name', selectedPrompt.name],
                  ['Pipeline Position', selectedPrompt.name === 'switchboard' ? '1st (entry)' : selectedPrompt.name === 'research' ? '2nd (data)' : selectedPrompt.name === 'synthesizer' ? '3rd (output)' : 'Quality gate'],
                  ['Model Calls', '1 per execution'],
                  ['Editable', 'Via backend prompt store'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between text-[12px] border-b border-white/[0.03] pb-2">
                    <span className="text-gray-500">{k}</span>
                    <span className="text-gray-300">{v}</span>
                  </div>
                ))}
              </div>

              <div className="mt-5 p-4 rounded-xl bg-amber-500/5 border border-amber-500/10">
                <p className="text-[11px] text-amber-400/70">
                  Prompt files are stored on the backend. Edit files in <code className="text-amber-300">backend/app/prompts/</code> and redeploy.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <Terminal size={28} className="text-gray-700 mb-3" />
              <p className="text-[13px] text-gray-500">Select a protocol to view.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
