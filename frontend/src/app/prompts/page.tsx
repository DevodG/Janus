'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Save, FileCode2, History, RotateCcw, AlertTriangle, Hexagon } from 'lucide-react';
import { apiClient } from '@/lib/api';
import type { PromptInfo } from '@/lib/types';

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptInfo | null>(null);
  const [editorContent, setEditorContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const data = await apiClient.getPrompts();
      setPrompts(data);
      if (data.length > 0 && !selectedPrompt) {
        handleSelect(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (prompt: PromptInfo) => {
    setSelectedPrompt(prompt);
    setEditorContent(prompt.content);
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    setSaving(true);
    try {
      await apiClient.updatePrompt(selectedPrompt.name, editorContent);
      await loadPrompts();
      // Brief success animation state could go here
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = selectedPrompt?.content !== editorContent;

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
              Prompt Engineering Lab
            </h1>
            <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-1">
              Direct access to agent cognitive parameters
            </p>
          </div>
        </div>
      </header>

      {error && (
        <div className="mb-4 mx-2 lg:mx-6 p-4 glass border-red-500/30 bg-red-500/10 rounded-xl flex flex-col">
          <div className="flex items-center gap-2 text-xs font-mono text-red-400 uppercase tracking-widest">
            <AlertTriangle size={14} /> System Error
          </div>
          <p className="mt-2 text-sm text-gray-300">{error}</p>
        </div>
      )}

      <div className="flex-1 min-h-0 flex gap-6 px-2 lg:px-6 relative z-10">
        
        {/* Left Sidebar: Prompt selector */}
        <div className="w-72 shrink-0 flex flex-col gap-4">
          <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
            <FileCode2 size={12} /> Target Instructions
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-2 pr-2">
            {prompts.map((p) => {
              const isActive = selectedPrompt?.name === p.name;
              return (
                <button
                  key={p.name}
                  onClick={() => handleSelect(p)}
                  className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border block group ${
                    isActive 
                      ? 'glass border-indigo-500/40 bg-indigo-500/5' 
                      : 'border-white/[0.03] hover:border-white/10 hover:bg-white/[0.02]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-sm font-mono tracking-wider ${isActive ? 'text-indigo-300' : 'text-gray-400 group-hover:text-gray-300'}`}>
                      {p.name.replace('.txt', '')}
                    </span>
                    <Hexagon size={12} className={isActive ? 'text-indigo-500/80' : 'text-gray-700'} />
                  </div>
                  <div className="text-[10px] font-mono text-gray-600 line-clamp-1">
                    {p.content.slice(0, 40)}...
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Area: IDE */}
        <div className="flex-1 flex flex-col glass rounded-3xl border border-white/[0.05] overflow-hidden group">
          {/* Editor Header */}
          <div className="h-14 border-b border-white/[0.05] flex items-center justify-between px-6 bg-black/20">
            <div className="flex items-center gap-3 text-xs font-mono text-gray-400">
              <History size={14} />
              <span>Editing: <span className="text-indigo-300">{selectedPrompt?.name || 'Nothing Selected'}</span></span>
              {hasChanges && <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse ml-2" title="Unsaved changes" />}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setEditorContent(selectedPrompt?.content || '')}
                disabled={!hasChanges || saving}
                className="px-4 py-1.5 flex flex-row items-center gap-2 rounded-lg text-xs font-mono text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-colors disabled:opacity-30 disabled:pointer-events-none"
              >
                <RotateCcw size={12} /> Revert
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || saving}
                className="px-4 py-1.5 flex flex-row items-center gap-2 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-mono transition-colors disabled:opacity-30 disabled:pointer-events-none relative overflow-hidden"
              >
                <Save size={12} />
                <span>{saving ? 'Syncing...' : 'Save Array'}</span>
                {saving && (
                   <div className="absolute inset-0 bg-white/20 animate-pulse" />
                )}
              </button>
            </div>
          </div>

          {/* Editor Body */}
          <div className="flex-1 relative bg-[#0a0a0f]/80">
            {/* Line numbers mock (optional visual flair) */}
            <div className="absolute left-0 top-0 bottom-0 w-12 border-r border-white-[0.02] bg-black/20 flex flex-col items-end py-6 pr-3 font-mono text-[10px] text-gray-700 pointer-events-none select-none">
              {Array.from({ length: 50 }).map((_, i) => (
                <div key={i} className="leading-6">{i + 1}</div>
              ))}
            </div>

            <textarea
              className="w-full h-full bg-transparent text-gray-300 font-mono text-[13px] leading-6 resize-none focus:outline-none p-6 pl-16 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-white/10"
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              disabled={!selectedPrompt || saving}
              spellCheck={false}
              placeholder="Select a prompt to begin editing cognitive constraints..."
            />
          </div>
        </div>

      </div>
    </div>
  );
}
