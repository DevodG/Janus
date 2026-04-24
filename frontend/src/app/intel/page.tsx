'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Globe, Search, RefreshCw, ExternalLink, Sparkles,
  TrendingUp, TrendingDown, Minus, Zap
} from 'lucide-react';
import { apiClient, financeClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';

// ─── Sub-components ────────────────────────────────────────
function StanceChip({ stance, score }: { stance: string; score: number }) {
  if (stance === 'bullish') return <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full"><TrendingUp size={9} />Bullish {Math.round(score * 100)}%</span>;
  if (stance === 'bearish') return <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full"><TrendingDown size={9} />Bearish {Math.round((1 - score) * 100)}%</span>;
  return <span className="flex items-center gap-1 text-[10px] text-gray-500 bg-white/[0.04] border border-white/[0.06] px-2 py-0.5 rounded-full"><Minus size={9} />Neutral</span>;
}

function ArticleCard({ article, index, onResearch }: { article: any; index: number; onResearch: (q: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="card hover:border-white/[0.12] group"
    >
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <StanceChip stance={article.stance} score={article.sentiment_score} />
        {article.source && <span className="text-[10px] text-gray-600">{article.source}</span>}
        {article.published_at && <span className="text-[10px] text-gray-700">{new Date(article.published_at).toLocaleDateString()}</span>}
      </div>
      <h3 className="text-[14px] text-gray-200 leading-snug mb-2 group-hover:text-white transition-colors">{article.title}</h3>
      {article.description && <p className="text-[12px] text-gray-500 leading-relaxed line-clamp-2">{article.description}</p>}
      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/[0.04]">
        <button
          onClick={() => onResearch(article.title + (article.description ? '. ' + article.description : ''))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/15 text-[11px] text-indigo-400 transition-all"
        >
          <Sparkles size={11} /> Deep Research
        </button>
        {article.url && (
          <a href={article.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[11px] text-gray-600 hover:text-gray-400 transition-colors">
            <ExternalLink size={10} /> Source
          </a>
        )}
      </div>
    </motion.div>
  );
}

const STAGES = ['Routing to switchboard...', 'Research agent scanning...', 'Cross-referencing sources...', 'Synthesizing analysis...'];

export default function IntelPage() {
  const [headlines, setHeadlines] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [researchResult, setResearchResult] = useState<CaseRecord | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchStage, setResearchStage] = useState(0);
  const [researchQuery, setResearchQuery] = useState('');
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    financeClient.getHeadlines().then(data => setHeadlines(data)).catch(() => {});
  }, []);

  const searchNews = async () => {
    if (!query.trim()) return;
    setLoading(true); setSearched(true); setResearchResult(null);
    try {
      const data = await financeClient.analyzeNews(query, 10);
      setHeadlines(data.articles || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  const runResearch = async (articleText: string) => {
    setResearchLoading(true); setResearchResult(null); setResearchQuery(articleText.slice(0, 80));
    setResearchStage(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => setResearchStage(p => (p + 1) % STAGES.length), 3000);
    try {
      const res = await apiClient.run(articleText);
      setResearchResult(res);
    } catch { /* silent */ }
    finally {
      setResearchLoading(false);
      if (stageTimer.current) clearInterval(stageTimer.current);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <Globe size={16} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-light text-gray-100">Intel Stream</h1>
            <p className="text-[11px] text-gray-600">Search and analyze news with Janus deep research</p>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="flex-1 flex items-center gap-3 px-4 py-2.5 rounded-xl border border-white/[0.06] focus-within:border-indigo-500/30 transition-colors" style={{ background: 'var(--janus-surface)' }}>
            <Search size={14} className="text-gray-600 shrink-0" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && searchNews()}
              placeholder="Search news — company, topic, event..."
              className="flex-1 bg-transparent text-[13px] text-gray-200 placeholder-gray-600 focus:outline-none"
            />
          </div>
          <button onClick={searchNews} disabled={loading} className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-indigo-500/20 text-[12px] text-gray-400 hover:text-indigo-300 transition-all disabled:opacity-40" style={{ background: 'var(--janus-surface)' }}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : 'Search'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex gap-0 overflow-hidden">
        {/* Articles */}
        <div className={`flex-1 overflow-y-auto p-4 space-y-3 transition-all duration-300 ${researchResult || researchLoading ? 'max-w-[50%]' : ''}`}>
          <div className="text-[11px] text-gray-600 mb-2">
            {searched ? `Results for "${query}"` : 'Top Business Headlines'} — click Deep Research on any article
          </div>
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <RefreshCw size={20} className="text-indigo-400 animate-spin" />
              <p className="text-[12px] text-gray-500">Fetching articles...</p>
            </div>
          )}
          {!loading && headlines.map((a, i) => (
            <ArticleCard key={`${a.title}-${i}`} article={a} index={i} onResearch={runResearch} />
          ))}
          {!loading && headlines.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Globe size={24} className="text-gray-700 mb-3" />
              <p className="text-[13px] text-gray-500">No articles found.</p>
            </div>
          )}
        </div>

        {/* Research panel */}
        <AnimatePresence>
          {(researchResult || researchLoading) && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 border-l border-white/[0.04] p-4 overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="text-[11px] text-gray-500 truncate">Research: {researchQuery}...</div>
                <button
                  onClick={() => { setResearchResult(null); setResearchLoading(false); }}
                  className="text-[11px] text-gray-600 hover:text-gray-400 transition-colors"
                >✕ Close</button>
              </div>

              {researchLoading ? (
                <div className="card flex items-center gap-3 p-5">
                  <div className="w-6 h-6 rounded-full border border-indigo-500/30 border-t-indigo-400 animate-spin" />
                  <p className="text-[12px] text-indigo-400">{STAGES[researchStage]}</p>
                </div>
              ) : researchResult ? (
                <div className="card p-5 space-y-4">
                  <div className="flex items-center gap-2 text-[10px] text-indigo-400 uppercase tracking-wider">
                    <Zap size={11} /> Research Complete
                  </div>
                  {researchResult.route && (
                    <div className="flex gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded-full text-[10px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/15">{researchResult.route.domain_pack}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] text-gray-500 bg-white/[0.04] border border-white/[0.06]">{researchResult.route.execution_mode}</span>
                    </div>
                  )}
                  {researchResult.final_answer && (
                    <div className="text-[13px] text-gray-300 leading-relaxed whitespace-pre-wrap">{researchResult.final_answer}</div>
                  )}
                </div>
              ) : null}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
