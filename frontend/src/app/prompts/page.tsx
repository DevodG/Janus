'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Terminal, FileCode2, Brain, Zap, Search, Shield, Hexagon, Info } from 'lucide-react';

const PROMPTS = [
  {
    name: 'switchboard',
    label: 'Switchboard',
    icon: Search,
    description: 'Routes queries to the right agent pipeline. Classifies domain, complexity, and required tools.',
    color: 'text-indigo-400',
  },
  {
    name: 'research',
    label: 'Research',
    icon: FileCode2,
    description: 'Gathers and analyzes information from web search, news, knowledge base, and API discovery.',
    color: 'text-violet-400',
  },
  {
    name: 'synthesizer',
    label: 'Synthesizer',
    icon: Brain,
    description: 'Produces the final answer by combining research, planning, and simulation outputs.',
    color: 'text-emerald-400',
  },
  {
    name: 'verifier',
    label: 'Verifier',
    icon: Shield,
    description: 'Quality gate — checks analysis for logical soundness, evidence alignment, and completeness.',
    color: 'text-amber-400',
  },
];

export default function PromptsPage() {
  const [selectedPrompt, setSelectedPrompt] = useState<typeof PROMPTS[0] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setSelectedPrompt(PROMPTS[0]);
      setLoading(false);
    }, 500);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center pb-20">
        <div className="flex flex-col items-center gap-4">
          <Terminal size={32} className="text-indigo-500/50" />
          <div className="flex gap-1.5 mt-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-500" style={{ animation: `pulse 1.5s infinite ${i * 0.2}s` }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col p-6 max-h-screen max-w-[1600px] mx-auto relative overflow-hidden">
      
      {/* Background flare */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-500/5 blur-[100px] rounded-[100%] pointer-events-none" />

      <header className="flex items-center justify-between shrink-0 mb-6 relative z-10 px-2 lg:px-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-2xl glass flex items-center justify-center border border-indigo-500/20">
            <Terminal size={18} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-light tracking-[0.15em] text-gradient-subtle uppercase">
              Agent Protocols
            </h1>
            <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-1">
              Cognitive instruction sets for the Janus agent pipeline
            </p>
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 flex gap-6 px-2 lg:px-6 relative z-10">
        
        {/* Left Sidebar: Prompt selector */}
        <div className="w-72 shrink-0 flex flex-col gap-4">
          <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
            <FileCode2 size={12} /> Agent Instructions
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-2 pr-2">
            {PROMPTS.map((p) => {
              const isActive = selectedPrompt?.name === p.name;
              const Icon = p.icon;
              return (
                <button
                  key={p.name}
                  onClick={() => setSelectedPrompt(p)}
                  className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border block group ${
                    isActive 
                      ? 'glass border-indigo-500/40 bg-indigo-500/5' 
                      : 'border-white/[0.03] hover:border-white/10 hover:bg-white/[0.02]'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Icon size={16} className={isActive ? p.color : 'text-gray-600'} />
                    <span className={`text-sm font-mono tracking-wider ${isActive ? 'text-indigo-300' : 'text-gray-400 group-hover:text-gray-300'}`}>
                      {p.label}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-gray-600 line-clamp-2">
                    {p.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Area: Prompt detail */}
        <div className="flex-1 flex flex-col glass rounded-3xl border border-white/[0.05] overflow-hidden group">
          {/* Header */}
          <div className="h-14 border-b border-white/[0.05] flex items-center justify-between px-6 bg-black/20">
            <div className="flex items-center gap-3 text-xs font-mono text-gray-400">
              {selectedPrompt && <selectedPrompt.icon size={14} className={selectedPrompt.color} />}
              <span>Viewing: <span className="text-indigo-300">{selectedPrompt?.label || 'Nothing Selected'}</span></span>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 relative bg-[#0a0a0f]/80 p-8 overflow-y-auto">
            {selectedPrompt ? (
              <div className="max-w-2xl">
                <div className="flex items-center gap-3 mb-6">
                  <selectedPrompt.icon size={24} className={selectedPrompt.color} />
                  <h2 className="text-xl font-light text-gray-100">{selectedPrompt.label}</h2>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed mb-8">{selectedPrompt.description}</p>
                
                <div className="glass rounded-xl p-6 border border-white/[0.04]">
                  <div className="flex items-center gap-2 mb-4 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                    <Info size={12} /> Protocol Details
                  </div>
                  <div className="space-y-3 text-xs font-mono">
                    <div className="flex justify-between border-b border-white/5 pb-2">
                      <span className="text-gray-500">Agent Name</span>
                      <span className="text-gray-300">{selectedPrompt.name}</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                      <span className="text-gray-500">Pipeline Position</span>
                      <span className="text-gray-300">
                        {selectedPrompt.name === 'switchboard' ? '1st (entry point)' :
                         selectedPrompt.name === 'research' ? '2nd (data gathering)' :
                         selectedPrompt.name === 'synthesizer' ? '3rd (final output)' :
                         'Quality gate (optional)'}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                      <span className="text-gray-500">Model Calls</span>
                      <span className="text-gray-300">1 per execution</span>
                    </div>
                    <div className="flex justify-between pb-2">
                      <span className="text-gray-500">Editable</span>
                      <span className="text-gray-300">Via backend prompt store</span>
                    </div>
                  </div>
                </div>

                <div className="mt-6 p-4 rounded-xl bg-amber-500/5 border border-amber-500/10">
                  <p className="text-xs font-mono text-amber-400/70">
                    Prompt files are stored on the cloud backend. To edit prompts, modify the files in <code className="text-amber-300">backend/app/prompts/</code> and redeploy.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Terminal size={32} className="text-gray-700 mb-4" />
                <p className="text-sm font-mono text-gray-500">Select an agent protocol to view details.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
