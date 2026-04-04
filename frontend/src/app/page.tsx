'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Zap, Sparkles, Activity, Search, TrendingUp, TrendingDown,
  Minus, AlertTriangle, Shield, CheckCircle, Globe, BarChart3,
  RefreshCw, ExternalLink, Eye, Scan, ChevronRight
} from 'lucide-react';
import { apiClient, financeClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';

// ─── Types ───────────────────────────────────────────────────
interface TextAnalysis {
  tickers: string[];
  entities: { text: string; type: string; confidence: number }[];
  stance: { stance: string; confidence: number; sentiment_score: number; bullish_count: number; bearish_count: number };
  scam_detection: { scam_score: number; risk_level: string; match_count: number };
  rumor_detection: { rumor_score: number; assessment: string; rumor_count: number; verification_count: number };
  event_impact: { impact_level: string; volatility_level: string; confidence: number; event_count: number };
  source_assessment: { average_score: number; trusted_count: number; assessment: string } | null;
}

interface TickerIntel {
  symbol: string;
  company_name: string;
  quote: Record<string, string>;
  overview: { sector?: string; industry?: string; market_cap?: string; pe_ratio?: string; '52_week_high'?: string; '52_week_low'?: string; analyst_target?: string; description?: string };
  news: { title: string; source: string; url: string; published_at: string; description: string }[];
  stance: { stance: string; confidence: number; sentiment_score: number };
  event_impact: { impact_level: string; volatility_level: string; event_count: number };
  ai_signal: { signal: string; conviction: number; reasoning: string; risk: string; timeframe: string };
}

interface AnalyzedArticle {
  title: string; source: string; url: string; published_at: string; description: string;
  stance: string; sentiment_score: number; scam_score: number; rumor_score: number; source_credibility: number;
}

// ─── Janus Orb ───────────────────────────────────────────────
function JanusOrb({ size = 40, thinking = false }: { size?: number; thinking?: boolean }) {
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <motion.div className="absolute inset-0 rounded-full"
        style={{ background: 'radial-gradient(circle at 30% 30%, #818cf8, #4f46e5 50%, #312e81 100%)', boxShadow: thinking ? '0 0 30px rgba(99,102,241,0.6), 0 0 60px rgba(99,102,241,0.3)' : '0 0 15px rgba(99,102,241,0.3)' }}
        animate={thinking ? { scale: [1, 1.1, 1] } : {}} transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }} />
      {thinking && <>
        <div className="janus-ring-1 absolute inset-[-6px] rounded-full border border-indigo-400/30" style={{ borderTopColor: 'transparent', borderBottomColor: 'transparent' }} />
        <div className="janus-ring-2 absolute inset-[-12px] rounded-full border border-violet-400/20" style={{ borderLeftColor: 'transparent', borderRightColor: 'transparent' }} />
        <div className="janus-ring-3 absolute inset-[-18px] rounded-full border border-indigo-300/10" style={{ borderTopColor: 'transparent', borderRightColor: 'transparent' }} />
      </>}
    </div>
  );
}

// ─── Art Piece ───────────────────────────────────────────────
function ArtPiece({ onUnlock }: { onUnlock: () => void }) {
  const [show, setShow] = useState(false);
  useEffect(() => { const t = setTimeout(() => setShow(true), 2000); return () => clearTimeout(t); }, []);
  return (
    <motion.div key="art" exit={{ opacity: 0, scale: 1.05, filter: 'blur(30px)' }} transition={{ duration: 1.5 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gray-950 overflow-hidden">
      <motion.div className="absolute w-[500px] h-[500px] rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, rgba(139,92,246,0.06) 40%, transparent 70%)' }}
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }} transition={{ duration: 6, repeat: Infinity }} />
      <motion.div initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }} className="relative z-10 mb-10">
        <JanusOrb size={64} thinking />
      </motion.div>
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 1.5 }} className="relative z-10 text-center">
        <h1 className="text-7xl font-extralight tracking-[0.3em] mb-4 text-gradient">JANUS</h1>
        <motion.div initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: '100%' }} transition={{ delay: 1.5, duration: 2 }}
          className="h-px bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent mb-6" />
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 0.5 }} transition={{ delay: 2, duration: 1.5 }}
          className="font-mono text-xs tracking-[0.4em] text-gray-400 uppercase">cognitive intelligence interface</motion.p>
      </motion.div>
      <AnimatePresence>
        {show && (
          <motion.button initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.8 }} onClick={onUnlock} className="relative z-10 mt-16 group">
            <div className="relative px-10 py-3.5 rounded-full border border-white/10 bg-white/[0.03] backdrop-blur-sm overflow-hidden transition-all duration-500 group-hover:border-indigo-500/30 group-hover:bg-white/[0.06]">
              <span className="relative z-10 text-xs tracking-[0.3em] uppercase text-gray-300 group-hover:text-white transition-colors">Initialize System</span>
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-600/10 to-violet-600/10 translate-y-full group-hover:translate-y-0 transition-transform duration-700" />
            </div>
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Typewriter ──────────────────────────────────────────────
function Typewriter({ text, speed = 10 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);
  useEffect(() => {
    idx.current = 0; setDisplayed('');
    const iv = setInterval(() => {
      if (idx.current < text.length) { setDisplayed(p => p + text[idx.current]); idx.current++; } else clearInterval(iv);
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed]);
  return <span>{displayed}{displayed.length < text.length && <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 animate-pulse" />}</span>;
}

// ─── Thinking ────────────────────────────────────────────────
const STAGES = ['Routing to switchboard...', 'Research agent scanning sources...', 'Cross-referencing databases...', 'Planner formulating strategy...', 'Verifier stress-testing claims...', 'Synthesizer composing analysis...'];
function ThinkingDisplay({ stage }: { stage: string }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-16 gap-6">
      <JanusOrb size={56} thinking />
      <div className="text-center mt-4">
        <motion.p key={stage} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-sm font-mono text-indigo-300">{stage}</motion.p>
        <div className="flex items-center justify-center gap-1.5 mt-3">
          {[0,1,2,3,4].map(i => <motion.div key={i} className="w-1 h-1 rounded-full bg-indigo-400" animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.2, 0.8] }} transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.15 }} />)}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Confidence Ring ─────────────────────────────────────────
function ConfidenceRing({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100);
  const circ = 2 * Math.PI * 18;
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-12 h-12">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="2" />
          <motion.circle cx="20" cy="20" r="18" fill="none" stroke={value >= 0.7 ? '#22c55e' : value >= 0.5 ? '#eab308' : '#ef4444'} strokeWidth="2" strokeLinecap="round" strokeDasharray={circ} initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: circ * (1 - value) }} transition={{ duration: 1.5, ease: 'easeOut' }} />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-mono text-gray-300">{pct}</span>
      </div>
      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

// ─── Stance Chip ─────────────────────────────────────────────
function StanceChip({ stance, score }: { stance: string; score: number }) {
  if (stance === 'bullish') return <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full"><TrendingUp size={9} />Bull {Math.round(score * 100)}%</span>;
  if (stance === 'bearish') return <span className="flex items-center gap-1 text-[10px] font-mono text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full"><TrendingDown size={9} />Bear {Math.round((1 - score) * 100)}%</span>;
  return <span className="flex items-center gap-1 text-[10px] font-mono text-gray-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full"><Minus size={9} />Neutral</span>;
}

// ─── Score Bar ────────────────────────────────────────────────

// ─── Signal Badge ─────────────────────────────────────────────
function SignalBadge({ signal, conviction }: { signal: string; conviction: number }) {
  const map: Record<string, string> = { BUY: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40', SELL: 'bg-red-500/20 text-red-300 border-red-500/40', HOLD: 'bg-amber-500/20 text-amber-300 border-amber-500/40', WATCH: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' };
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border ${map[signal] || map.WATCH}`}>
      <span className="text-sm font-mono font-bold">{signal}</span>
      <span className="text-[10px] font-mono opacity-70">{Math.round(conviction * 100)}% conviction</span>
    </div>
  );
}

// ─── Research Result Panel ────────────────────────────────────
// Shows the full 5-agent pipeline output inline
function ResearchPanel({ result, loading, stage }: { result: CaseRecord | null; loading: boolean; stage: string }) {
  if (loading) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass rounded-2xl p-6 border border-indigo-500/20 space-y-4">
      <div className="flex items-center gap-3">
        <JanusOrb size={28} thinking />
        <div>
          <p className="text-xs font-mono text-indigo-300">{stage}</p>
          <div className="flex gap-1 mt-1.5">
            {[0,1,2,3,4].map(i => <motion.div key={i} className="w-1 h-1 rounded-full bg-indigo-400" animate={{ opacity: [0.2,1,0.2] }} transition={{ duration: 1.2, repeat: Infinity, delay: i*0.15 }} />)}
          </div>
        </div>
      </div>
    </motion.div>
  );
  if (!result) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-2xl p-5 border border-indigo-500/20 space-y-4">
      <div className="flex items-center gap-2 text-[10px] font-mono text-indigo-400 uppercase tracking-wider">
        <Zap size={12} /> JANUS Research Complete
      </div>
      {/* Agent confidence rings */}
      {result.outputs && result.outputs.filter(o => o.confidence > 0).length > 0 && (
        <div className="flex items-center gap-5">
          {result.outputs.filter(o => o.confidence > 0).map(o => <ConfidenceRing key={o.agent} value={o.confidence} label={o.agent} />)}
        </div>
      )}
      {/* Route */}
      {result.route && (
        <div className="flex gap-2 flex-wrap">
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{result.route.domain_pack}</span>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-white/5 text-gray-400 border border-white/10">{result.route.execution_mode}</span>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-white/5 text-gray-400 border border-white/10">{result.route.complexity}</span>
        </div>
      )}
      {/* Final synthesis */}
      {result.final_answer && (
        <div className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap font-mono">
          <Typewriter text={result.final_answer} speed={6} />
        </div>
      )}
    </motion.div>
  );
}

// ─── News Article Card (clean — no scam/rumor scores) ─────────
function ArticleCard({ article, index, onResearch }: {
  article: { title: string; source: string; url: string; published_at: string; description: string; stance: string; sentiment_score: number };
  index: number;
  onResearch: (query: string) => void;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}
      className="glass rounded-xl border border-white/[0.04] hover:border-white/10 transition-colors p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <StanceChip stance={article.stance} score={article.sentiment_score} />
            {article.source && <span className="text-[9px] font-mono text-gray-600">{article.source}</span>}
            {article.published_at && <span className="text-[9px] font-mono text-gray-700">{new Date(article.published_at).toLocaleDateString()}</span>}
          </div>
          <p className="text-sm text-gray-200 leading-snug mb-2">{article.title}</p>
          {article.description && <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{article.description}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/5">
        <button onClick={() => onResearch(article.title + (article.description ? '. ' + article.description : ''))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-[10px] font-mono text-indigo-300 transition-colors uppercase tracking-wider">
          <Sparkles size={10} /> Deep Research
        </button>
        {article.url && (
          <a href={article.url} target="_blank" rel="noreferrer"
            className="flex items-center gap-1 text-[10px] font-mono text-gray-600 hover:text-gray-400 transition-colors">
            <ExternalLink size={10} /> Source
          </a>
        )}
      </div>
    </motion.div>
  );
}


// ─── Intel Stream Tab ─────────────────────────────────────────
// Search news → click "Deep Research" on any article → full 5-agent pipeline runs
function IntelStreamTab() {
  const [headlines, setHeadlines] = useState<{ title: string; source: string; url: string; published_at: string; description: string; stance: string; sentiment_score: number }[]>([]);
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
    } catch { /* silent */ } finally { setLoading(false); }
  };

  const runResearch = async (articleText: string) => {
    setResearchLoading(true); setResearchResult(null); setResearchQuery(articleText.slice(0, 80));
    setResearchStage(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => setResearchStage(p => (p + 1) % STAGES.length), 3000);
    try {
      const res = await apiClient.analyze({ user_input: articleText });
      setResearchResult(res);
    } catch { /* silent */ } finally {
      setResearchLoading(false);
      if (stageTimer.current) clearInterval(stageTimer.current);
    }
  };

  return (
    <div className="h-full flex gap-5 overflow-hidden">
      {/* Left: news feed */}
      <div className="flex flex-col gap-3 overflow-hidden" style={{ width: researchResult || researchLoading ? '45%' : '100%', transition: 'width 0.4s ease' }}>
        <div className="flex gap-2 shrink-0">
          <div className="flex-1 flex items-center gap-3 px-4 py-3 glass rounded-2xl border border-white/[0.06] focus-within:border-indigo-500/30 transition-colors">
            <Globe size={14} className="text-gray-500 shrink-0" />
            <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchNews()}
              placeholder="Search news — company, topic, event..."
              className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 font-mono focus:outline-none" />
          </div>
          <button onClick={searchNews} disabled={loading}
            className="px-4 py-2 glass rounded-2xl border border-white/[0.06] hover:border-indigo-500/30 text-xs font-mono text-gray-400 hover:text-indigo-300 transition-all disabled:opacity-40">
            {loading ? <RefreshCw size={13} className="animate-spin" /> : 'Search'}
          </button>
        </div>

        <div className="text-[10px] font-mono text-gray-600 uppercase tracking-wider shrink-0">
          {searched ? `"${query}"` : 'Top Business Headlines'} — click Deep Research on any article to run full agent analysis
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <JanusOrb size={36} thinking />
              <p className="text-xs font-mono text-indigo-400 animate-pulse">Fetching articles...</p>
            </div>
          )}
          {!loading && headlines.map((a, i) => (
            <ArticleCard key={i} article={a} index={i} onResearch={runResearch} />
          ))}
          {!loading && headlines.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Globe size={28} className="text-gray-700 mb-3" />
              <p className="text-sm font-mono text-gray-500">No articles found.</p>
            </div>
          )}
        </div>
      </div>

      {/* Right: research output */}
      <AnimatePresence>
        {(researchResult || researchLoading) && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
            className="flex-1 flex flex-col gap-3 overflow-hidden">
            <div className="flex items-center justify-between shrink-0">
              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider truncate max-w-[80%]">
                Research: {researchQuery}...
              </div>
              <button onClick={() => { setResearchResult(null); setResearchLoading(false); }}
                className="text-[10px] font-mono text-gray-600 hover:text-gray-400 transition-colors">
                ✕ Close
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <ResearchPanel result={researchResult} loading={researchLoading} stage={STAGES[researchStage]} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Markets Tab ──────────────────────────────────────────────
function MarketsTab() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ symbol: string; name: string; region?: string }[]>([]);
  const [intel, setIntel] = useState<TickerIntel | null>(null);
  const [loading, setLoading] = useState(false);
  const [newsLoading, setNewsLoading] = useState(false);
  const [news, setNews] = useState<{ title: string; source: string; url: string; published_at: string; description: string; stance: string; sentiment_score: number }[]>([]);
  const [activeSymbol, setActiveSymbol] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [researchResult, setResearchResult] = useState<CaseRecord | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchStage, setResearchStage] = useState(0);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleQueryChange = (val: string) => {
    setQuery(val);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!val.trim()) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try { setSearchResults(await financeClient.searchTicker(val)); }
      catch { setSearchResults([]); }
    }, 400);
  };



  const loadTicker = useCallback(async (symbol: string, region = '') => {
    setLoading(true); setIntel(null); setNews([]); setActiveSymbol(symbol);
    setSearchResults([]); setError(null); setResearchResult(null);
    try {
      const data = await financeClient.getTickerIntelligence(symbol);
      setIntel(data);
      setNewsLoading(true);
      try {
        const nd = await financeClient.analyzeNews(data.company_name || symbol, 8);
        setNews(nd.articles || []);
      } catch { /* silent */ } finally { setNewsLoading(false); }
    } catch {
      setError(`Could not load intelligence for ${symbol}. Ensure ALPHAVANTAGE_API_KEY is set in backend/.env`);
    } finally { setLoading(false); }
  }, []);

  const runDeepResearch = async () => {
    if (!intel) return;
    const q = `Analyze ${intel.company_name} (${intel.symbol}) stock. ${intel.overview.description || ''}`.slice(0, 500);
    setResearchLoading(true); setResearchResult(null); setResearchStage(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => setResearchStage(p => (p + 1) % STAGES.length), 3000);
    try {
      const res = await apiClient.analyze({ user_input: q });
      setResearchResult(res);
    } catch { /* silent */ } finally {
      setResearchLoading(false);
      if (stageTimer.current) clearInterval(stageTimer.current);
    }
  };

  const price = intel?.quote?.['05. price'];
  const change = intel?.quote?.['09. change'];
  const changePct = intel?.quote?.['10. change percent'];
  const isPositive = change && parseFloat(change) >= 0;


  return (
    <div className="h-full flex flex-col gap-4 overflow-hidden">
      {/* Search */}
      <div className="relative shrink-0">
        <div className="flex items-center gap-3 px-4 py-3 glass rounded-2xl border border-white/[0.06] focus-within:border-indigo-500/30 transition-colors">
          <Search size={15} className="text-gray-500 shrink-0" />
          <input value={query} onChange={e => handleQueryChange(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setSearchResults([]); loadTicker(query.toUpperCase(), selectedRegion); } }}
            placeholder="Search — RELIANCE, TCS, NIFTY, AAPL, Tesla..."
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 font-mono focus:outline-none" />
          {query && (
            <button onClick={() => { setSearchResults([]); loadTicker(query.toUpperCase(), selectedRegion); }}
              className="px-3 py-1 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-mono transition-colors">
              Analyze
            </button>
          )}
        </div>
        <AnimatePresence>
          {searchResults.length > 0 && (
            <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="absolute top-full left-0 right-0 mt-1 glass rounded-xl border border-white/10 overflow-hidden z-20">
              {searchResults.slice(0, 6).map(r => (
                <button key={r.symbol} onClick={() => { setQuery(r.symbol); setSelectedRegion(r.region || ''); loadTicker(r.symbol, r.region || ''); }}
                  className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.04] transition-colors text-left">
                  <span className="text-sm font-mono text-indigo-300">{r.symbol}</span>
                  <div className="flex items-center gap-3 ml-4 min-w-0">
                    {r.region && <span className="text-[9px] font-mono text-gray-600 bg-white/5 px-1.5 py-0.5 rounded shrink-0">{r.region}</span>}
                    <span className="text-xs text-gray-500 truncate">{r.name}</span>
                  </div>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <JanusOrb size={48} thinking />
          <p className="text-xs font-mono text-indigo-400 uppercase tracking-widest animate-pulse">Fetching intelligence for {activeSymbol}...</p>
        </div>
      )}

      {!loading && error && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
          <AlertTriangle size={28} className="text-amber-500/50" />
          <p className="text-sm font-mono text-amber-400 max-w-md">{error}</p>
        </div>
      )}

      {!loading && !intel && !error && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
          <BarChart3 size={32} className="text-gray-700" />
          <p className="text-sm font-mono text-gray-500">Search any stock — Indian (RELIANCE, TCS, INFY) or global (AAPL, TSLA)</p>
          <div className="flex gap-2 mt-2 flex-wrap justify-center">
            {[{s:'RELIANCE.BSE',l:'Reliance',r:'India'},{s:'TCS.BSE',l:'TCS',r:'India'},{s:'INFY.BSE',l:'Infosys',r:'India'},{s:'AAPL',l:'Apple',r:''},{s:'TSLA',l:'Tesla',r:''}].map(({s,l,r}) => (
              <button key={s} onClick={() => { setQuery(s); setSelectedRegion(r); loadTicker(s, r); }}
                className="px-3 py-1 rounded-full border border-white/10 hover:border-indigo-500/30 text-xs font-mono text-gray-500 hover:text-indigo-300 transition-all">{l}</button>
            ))}
          </div>
        </div>
      )}

      {!loading && intel && (
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {/* Header */}
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-2xl font-light text-white">{intel.symbol}</span>
                  <span className="text-sm text-gray-500">{intel.company_name}</span>
                </div>
                {price ? (
                  <div className="flex items-center gap-3">
                    <span className="text-3xl font-light text-white">{parseFloat(price).toFixed(2)}</span>
                    {change && changePct && (
                      <span className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isPositive ? '+' : ''}{parseFloat(change).toFixed(2)} ({changePct})
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="text-xs font-mono text-gray-600 mt-1">Live quote unavailable — add ALPHAVANTAGE_API_KEY to .env</p>
                )}
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  {intel.overview.sector && <span className="text-[10px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded">{intel.overview.sector}</span>}
                  {intel.overview.industry && <span className="text-[10px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded">{intel.overview.industry}</span>}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                {intel.ai_signal && <SignalBadge signal={intel.ai_signal.signal} conviction={intel.ai_signal.conviction} />}
                <StanceChip stance={intel.stance.stance} score={intel.stance.sentiment_score} />
              </div>
            </div>
            {/* AI signal reasoning */}
            {intel.ai_signal?.reasoning && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <div className="flex items-center gap-2 mb-1.5 text-[10px] font-mono text-indigo-400 uppercase tracking-wider"><Zap size={10} /> AI Signal</div>
                <p className="text-xs text-gray-300 font-mono leading-relaxed">{intel.ai_signal.reasoning}</p>
                <div className="flex gap-4 mt-2">
                  <span className="text-[9px] font-mono text-gray-600 uppercase">Risk: <span className={intel.ai_signal.risk === 'HIGH' ? 'text-red-400' : intel.ai_signal.risk === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'}>{intel.ai_signal.risk}</span></span>
                  <span className="text-[9px] font-mono text-gray-600 uppercase">Timeframe: <span className="text-gray-400">{intel.ai_signal.timeframe}</span></span>
                </div>
              </div>
            )}
            {/* Deep Research button */}
            <div className="mt-4 pt-4 border-t border-white/5">
              <button onClick={runDeepResearch} disabled={researchLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-xs font-mono text-indigo-300 transition-colors disabled:opacity-40">
                <Sparkles size={12} className={researchLoading ? 'animate-pulse' : ''} />
                {researchLoading ? 'Running 5-agent research...' : 'Deep Research — Run Full Agent Pipeline'}
              </button>
            </div>
          </div>

          {/* Research output */}
          <ResearchPanel result={researchResult} loading={researchLoading} stage={STAGES[researchStage]} />

          {/* Fundamentals + Events */}
          <div className="grid grid-cols-2 gap-4">
            <div className="glass rounded-xl p-4 border border-white/[0.04] space-y-2">
              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Fundamentals</div>
              {([['P/E Ratio', intel.overview.pe_ratio], ['52W High', intel.overview['52_week_high']], ['52W Low', intel.overview['52_week_low']], ['Analyst Target', intel.overview.analyst_target]] as [string, string | undefined][])
                .filter(([, v]) => v && v !== 'None' && v !== '-' && v !== 'N/A')
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs font-mono border-b border-white/5 pb-1.5">
                    <span className="text-gray-500">{k}</span><span className="text-gray-300">{v}</span>
                  </div>
                ))}
              {!intel.overview.pe_ratio && <p className="text-[10px] font-mono text-gray-700">Requires Alpha Vantage key</p>}
            </div>
            <div className="glass rounded-xl p-4 border border-white/[0.04] space-y-3">
              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Event Intelligence</div>
              <div className="text-xs font-mono"><span className="text-gray-500">Impact: </span><span className={intel.event_impact.impact_level === 'high' || intel.event_impact.impact_level === 'very_high' ? 'text-amber-400' : 'text-gray-300'}>{intel.event_impact.impact_level || 'unknown'}</span></div>
              <div className="text-xs font-mono"><span className="text-gray-500">Volatility: </span><span className="text-gray-300">{intel.event_impact.volatility_level || 'unknown'}</span></div>
              <div className="text-xs font-mono"><span className="text-gray-500">Events: </span><span className="text-gray-300">{intel.event_impact.event_count || 0} detected</span></div>
            </div>
          </div>

          {/* News */}
          <div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">
              <Scan size={11} className="text-indigo-400" />
              News {newsLoading && <RefreshCw size={10} className="animate-spin text-indigo-400" />}
              <span className="text-gray-700">— click Deep Research on any article</span>
            </div>
            {newsLoading && <div className="text-xs font-mono text-gray-600 animate-pulse">Fetching articles...</div>}
            <div className="space-y-2">
              {news.map((a, i) => <ArticleCard key={i} article={a} index={i} onResearch={runDeepResearch} />)}
              {!newsLoading && news.length === 0 && intel.news.map((a, i) => (
                <ArticleCard key={i} article={{ ...a, stance: 'neutral', sentiment_score: 0.5 }} index={i} onResearch={(q) => runDeepResearch()} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
//  MAIN APP
// ═══════════════════════════════════════════════════════════
export default function JanusApp() {
  const [systemState, setSystemState] = useState<'art' | 'dashboard'>('art');
  const [activeTab, setActiveTab] = useState<'command' | 'intel' | 'markets'>('command');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [thinkingStage, setThinkingStage] = useState(0);
  const [result, setResult] = useState<CaseRecord | null>(null);
  const [input, setInput] = useState('');
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isAnalyzing) return;
    const iv = setInterval(() => setThinkingStage(p => (p + 1) % STAGES.length), 3000);
    return () => clearInterval(iv);
  }, [isAnalyzing]);

  const handleAnalyze = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setIsAnalyzing(true); setResult(null); setThinkingStage(0);
    try {
      const res = await apiClient.analyze({ user_input: q });
      setResult(res);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
    } catch { /* silent */ } finally { setIsAnalyzing(false); }
  }, []);

  const tabs = [
    { id: 'command' as const, label: 'Command', icon: Sparkles },
    { id: 'intel' as const, label: 'Intel Stream', icon: Globe },
    { id: 'markets' as const, label: 'Markets', icon: BarChart3 },
  ];

  return (
    <div className="relative min-h-screen bg-transparent text-gray-100 overflow-hidden">
      <AnimatePresence>
        {systemState === 'art' && <ArtPiece onUnlock={() => setSystemState('dashboard')} />}
      </AnimatePresence>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: systemState === 'dashboard' ? 1 : 0 }} transition={{ duration: 1.2, delay: 0.5 }}
        className={`relative z-10 flex flex-col h-screen max-w-[1480px] mx-auto px-6 py-5 ${systemState === 'art' ? 'pointer-events-none' : ''}`}>

        <header className="flex items-center justify-between mb-5 shrink-0">
          <div className="flex items-center gap-4">
            <JanusOrb size={32} thinking={isAnalyzing} />
            <div>
              <h1 className="text-lg font-light tracking-[0.15em] text-gradient-subtle">JANUS</h1>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-mono text-emerald-400/70 uppercase tracking-widest">{isAnalyzing ? 'Processing' : 'System Active'}</span>
              </div>
            </div>
          </div>
        </header>

        <nav className="flex gap-1 mb-5 shrink-0">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 text-sm ${activeTab === tab.id ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>
              {activeTab === tab.id && <motion.div layoutId="tabIndicator" className="absolute inset-0 glass rounded-xl" transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }} />}
              <tab.icon size={15} className="relative z-10" />
              <span className="relative z-10 font-mono text-xs uppercase tracking-wider">{tab.label}</span>
            </button>
          ))}
        </nav>

        <main className="flex-1 min-h-0 overflow-hidden">
          <AnimatePresence mode="wait">

            {activeTab === 'command' && (
              <motion.div key="command" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full flex flex-col">
                <div className="relative group shrink-0">
                  <div className="absolute -inset-px rounded-2xl bg-gradient-to-r from-indigo-500/20 via-transparent to-violet-500/20 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
                  <div className="relative flex items-center gap-3 px-5 py-4 rounded-2xl glass border border-white/[0.06] group-focus-within:border-indigo-500/20 transition-colors">
                    <Sparkles size={16} className="text-indigo-400/50 shrink-0" />
                    <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAnalyze(input)} disabled={isAnalyzing}
                      placeholder="Ask Janus — financial analysis, market intelligence, research any topic..."
                      className="flex-1 bg-transparent text-gray-100 placeholder-gray-600 text-sm focus:outline-none disabled:opacity-40 font-mono" />
                    <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => handleAnalyze(input)} disabled={isAnalyzing || !input.trim()}
                      className="p-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-all duration-200">
                      <Send size={14} />
                    </motion.button>
                  </div>
                </div>

                <div className="flex-1 mt-5 overflow-y-auto rounded-2xl">
                  <AnimatePresence mode="wait">
                    {isAnalyzing ? (
                      <ThinkingDisplay stage={STAGES[thinkingStage]} />
                    ) : result ? (
                      <motion.div key="result" ref={resultRef} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 pb-8">
                        {result.route && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{result.route.domain_pack}</span>
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider bg-white/5 text-gray-400 border border-white/10">{result.route.execution_mode}</span>
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider bg-white/5 text-gray-400 border border-white/10">{result.route.complexity}</span>
                          </div>
                        )}
                        {result.outputs && result.outputs.filter(o => o.confidence > 0).length > 0 && (
                          <div className="flex items-center gap-6 py-3">
                            {result.outputs.filter(o => o.confidence > 0).map(o => <ConfidenceRing key={o.agent} value={o.confidence} label={o.agent} />)}
                          </div>
                        )}
                        {result.final_answer && (
                          <div className="glass rounded-2xl p-6">
                            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-indigo-400/70 uppercase tracking-wider"><Zap size={12} /><span>Synthesis Complete</span></div>
                            <div className="prose prose-invert max-w-none text-sm leading-relaxed text-gray-200 whitespace-pre-wrap">
                              <Typewriter text={result.final_answer} speed={8} />
                            </div>
                          </div>
                        )}
                      </motion.div>
                    ) : (
                      <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full flex flex-col items-center justify-center text-center py-20">
                        <JanusOrb size={48} />
                        <p className="mt-6 text-sm text-gray-500 font-mono">Awaiting directive...</p>
                        <p className="mt-2 text-xs text-gray-700 max-w-md">5-agent pipeline: research → planner → verifier → synthesizer. Use Intel Stream or Markets to run research on news and stocks.</p>
                        <div className="flex flex-wrap justify-center gap-2 mt-8 max-w-lg">
                          {['Analyze RBI rate hike impact on Indian markets', 'What happens to $NVDA if AI spending slows?', 'Compare Reliance vs TCS as long-term investments'].map(q => (
                            <button key={q} onClick={() => { setInput(q); handleAnalyze(q); }} className="px-3 py-1.5 rounded-full text-xs font-mono text-gray-500 border border-white/5 hover:border-indigo-500/20 hover:text-indigo-300 transition-all text-left">{q}</button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}

            {activeTab === 'intel' && (
              <motion.div key="intel" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full">
                <IntelStreamTab />
              </motion.div>
            )}

            {activeTab === 'markets' && (
              <motion.div key="markets" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full">
                <MarketsTab />
              </motion.div>
            )}

          </AnimatePresence>
        </main>
      </motion.div>
    </div>
  );
}
