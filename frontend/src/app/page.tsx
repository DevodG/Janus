'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Zap, Sparkles, Activity, Search, TrendingUp, TrendingDown,
  Minus, AlertTriangle, Shield, CheckCircle, Globe, BarChart3,
  RefreshCw, ExternalLink, Eye, Scan, ChevronRight, X, Play,
  Clock, Target, AlertCircle, Layers, Brain, Cpu, ArrowRight,
  FileText, MessageSquare, ChevronDown, Terminal, Radio, GitBranch,
  Bell, Moon, Sun, Sunrise, Sunset, Activity as PulseIcon, Database, Network,
  ChevronUp, Star, Hash, Eye as EyeIcon, Info, Plus
} from 'lucide-react';
import { apiClient, financeClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, CandlestickData, HistogramData } from 'lightweight-charts';
import JanusOrb from '@/components/ui/JanusOrb';
import Typewriter from '@/components/ui/Typewriter';
import ConfidenceRing from '@/components/ui/ConfidenceRing';
import { StanceChip, SignalBadge, SeverityBadge } from '@/components/ui/Badges';

// ─── Types ───────────────────────────────────────────────────
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
  signal_queue: {
    total_signals: number;
    severity_counts: Record<string, number>;
    type_counts: Record<string, number>;
  };
}

interface Alert {
  type: string;
  title: string;
  description: string;
  source: string;
  severity: string;
  sentiment: string;
  timestamp: string;
  url?: string;
}

interface MemoryStats {
  queries: number;
  entities: number;
  insights: number;
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
        <h1 className="text-7xl font-extralight tracking-[0.3em] mb-4 bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-400 bg-clip-text text-transparent">JANUS</h1>
        <motion.div initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: '100%' }} transition={{ delay: 1.5, duration: 2 }}
          className="h-px bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent mb-6" />
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 0.5 }} transition={{ delay: 2, duration: 1.5 }}
          className="font-mono text-xs tracking-[0.4em] text-gray-400 uppercase">living intelligence system</motion.p>
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

// ─── Thinking ────────────────────────────────────────────────
const STAGES = ['Routing to switchboard...', 'Research agent scanning sources...', 'Cross-referencing databases...', 'Synthesizer composing analysis...'];
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

// ─── Research Result Panel ────────────────────────────────────
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
      {result.outputs && result.outputs.filter((o: any) => o.confidence > 0).length > 0 && (
        <div className="flex items-center gap-5">
          {result.outputs.filter((o: any) => o.confidence > 0).map((o: any, idx: number) => (
            <ConfidenceRing key={`${o.agent || 'output'}-${idx}`} value={o.confidence} label={o.agent || `Agent ${idx + 1}`} />
          ))}
        </div>
      )}
      {result.route && (
        <div className="flex gap-2 flex-wrap">
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{result.route.domain_pack}</span>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-white/5 text-gray-400 border border-white/10">{result.route.execution_mode}</span>
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-white/5 text-gray-400 border border-white/10">{result.route.complexity}</span>
        </div>
      )}
      {result.final_answer && (
        <div className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap font-mono">
          <Typewriter text={result.final_answer} speed={6} />
        </div>
      )}
    </motion.div>
  );
}

// ─── News Article Card ─────────────────
function ArticleCard({ article, index, onResearch }: {
  article: { title: string; source: string; url: string; published_at: string; description: string; stance: string; sentiment_score: number };
  index: number; onResearch: (query: string) => void;
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

// ─── Alert Card ──────────────────────────────────────────────
function AlertCard({ alert, index }: { alert: Alert; index: number }) {
  return (
    <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05 }}
      className="glass rounded-xl border border-white/[0.04] hover:border-white/10 transition-colors p-3">
      <div className="flex items-start gap-3">
        <div className="mt-1">
          {alert.severity === 'high' || alert.severity === 'critical' ? (
            <AlertTriangle size={14} className="text-red-400" />
          ) : (
            <Info size={14} className="text-amber-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <SeverityBadge severity={alert.severity} />
            <span className="text-[9px] font-mono text-gray-600">{alert.type}</span>
            {alert.source && <span className="text-[9px] font-mono text-gray-700">{alert.source}</span>}
          </div>
          <p className="text-xs text-gray-300 leading-snug">{alert.title}</p>
          {alert.description && <p className="text-[10px] text-gray-600 mt-1 line-clamp-1">{alert.description}</p>}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[9px] font-mono text-gray-700">{new Date(alert.timestamp).toLocaleString()}</span>
            {alert.url && (
              <a href={alert.url} target="_blank" rel="noreferrer" className="text-[9px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5">
                <ExternalLink size={8} /> Read
              </a>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── System Status Bar ───────────────────────────────────────
function StatusBar({ daemonStatus, memoryStats, alertCount }: { daemonStatus: DaemonStatus | null; memoryStats: MemoryStats | null; alertCount: number }) {
  const phaseIcons: Record<string, React.ReactNode> = {
    morning: <Sunrise size={12} className="text-amber-400" />,
    daytime: <Sun size={12} className="text-indigo-400" />,
    evening: <Sunset size={12} className="text-violet-400" />,
    night: <Moon size={12} className="text-indigo-300" />,
  };

  return (
    <div className="flex items-center gap-4 text-[10px] font-mono text-gray-500">
      {daemonStatus?.circadian && (
        <div className="flex items-center gap-1.5">
          {phaseIcons[daemonStatus.circadian.current_phase]}
          <span className="text-gray-400">{daemonStatus.circadian.phase_name}</span>
        </div>
      )}
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-emerald-400/70">Daemon Active</span>
      </div>
      {memoryStats && (
        <div className="flex items-center gap-1.5">
          <Database size={10} className="text-gray-600" />
          <span>{memoryStats.queries} queries, {memoryStats.entities} entities</span>
        </div>
      )}
      {daemonStatus && (
        <div className="flex items-center gap-1.5">
          <Radio size={10} className="text-gray-600" />
          <span>{daemonStatus.signal_queue?.total_signals || daemonStatus.signals || 0} signals</span>
        </div>
      )}
      {alertCount > 0 && (
        <div className="flex items-center gap-1.5">
          <Bell size={10} className="text-amber-400" />
          <span className="text-amber-400">{alertCount} alerts</span>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
//  TAB COMPONENTS
// ═══════════════════════════════════════════════════════════

// ─── Command Tab ─────────────────────────────────────────────
function CommandTab() {
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

  return (
    <div className="h-full flex flex-col">
      <div className="relative group shrink-0">
        <div className="absolute -inset-px rounded-2xl bg-gradient-to-r from-indigo-500/20 via-transparent to-violet-500/20 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
        <div className="relative flex items-center gap-3 px-5 py-4 rounded-2xl glass border border-white/[0.06] group-focus-within:border-indigo-500/20 transition-colors">
          <Sparkles size={16} className="text-indigo-400/50 shrink-0" />
          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAnalyze(input)} disabled={isAnalyzing}
            placeholder="Ask Janus anything — analysis, research, market intelligence..."
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
              {result.outputs && result.outputs.filter((o: any) => o.confidence > 0).length > 0 && (
                <div className="flex items-center gap-6 py-3">
                  {result.outputs.filter((o: any) => o.confidence > 0).map((o: any, idx: number) => (
                    <ConfidenceRing key={`${o.agent || 'output'}-${idx}`} value={o.confidence} label={o.agent || `Agent ${idx + 1}`} />
                  ))}
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
              <p className="mt-2 text-xs text-gray-700 max-w-md">Multi-agent pipeline: switchboard → research → synthesizer.</p>
              <div className="flex flex-wrap justify-center gap-2 mt-8 max-w-lg">
                {['Analyze RBI rate hike impact on Indian markets', 'What happens to $NVDA if AI spending slows?', 'Compare Reliance vs TCS as long-term investments'].map(q => (
                  <button key={q} onClick={() => { setInput(q); handleAnalyze(q); }} className="px-3 py-1.5 rounded-full text-xs font-mono text-gray-500 border border-white/5 hover:border-indigo-500/20 hover:text-indigo-300 transition-all text-left">{q}</button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ─── Intel Stream Tab ─────────────────────────────────────────
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
          {searched ? `"${query}"` : 'Top Business Headlines'} — click Deep Research on any article
        </div>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <JanusOrb size={36} thinking />
              <p className="text-xs font-mono text-indigo-400 animate-pulse">Fetching articles...</p>
            </div>
          )}
          {!loading && headlines.map((a, i) => (
            <ArticleCard key={`${a.title}-${i}`} article={a} index={i} onResearch={runResearch} />
          ))}
          {!loading && headlines.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Globe size={28} className="text-gray-700 mb-3" />
              <p className="text-sm font-mono text-gray-500">No articles found.</p>
            </div>
          )}
        </div>
      </div>
      <AnimatePresence>
        {(researchResult || researchLoading) && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
            className="flex-1 flex flex-col gap-3 overflow-hidden">
            <div className="flex items-center justify-between shrink-0">
              <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider truncate max-w-[80%]">
                Research: {researchQuery}...
              </div>
              <button onClick={() => { setResearchResult(null); setResearchLoading(false); }}
                className="text-[10px] font-mono text-gray-600 hover:text-gray-400 transition-colors">✕ Close</button>
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

// ─── Candlestick Chart Component ─────────────────────────────
function CandlestickChart({ symbol, companyName, price, change, changePct, isPositive }: {
  symbol: string; companyName: string; price?: string; change?: string; changePct?: string; isPositive?: boolean;
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null);
  const volumeSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null);
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '3M' | '1Y'>('1M');
  const [loading, setLoading] = useState(false);

  const generateChartData = useCallback((basePrice: number, tf: string): CandlestickData[] => {
    const data: CandlestickData[] = [];
    let currentPrice = basePrice;
    const volatility = basePrice * 0.02;
    const now = new Date();
    let days = tf === '1D' ? 1 : tf === '1W' ? 7 : tf === '1M' ? 30 : tf === '3M' ? 90 : 365;
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - days);

    for (let i = 0; i < days; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      if (date.getDay() === 0 || date.getDay() === 6) continue;
      const dayVol = volatility * (0.5 + Math.random());
      const open = currentPrice;
      const high = open + Math.random() * dayVol;
      const low = open - Math.random() * dayVol;
      const close = open + (Math.random() - 0.48) * dayVol;
      data.push({ time: date.toISOString().split('T')[0], open: parseFloat(open.toFixed(2)), high: parseFloat(high.toFixed(2)), low: parseFloat(low.toFixed(2)), close: parseFloat(close.toFixed(2)) });
      currentPrice = close;
    }
    return data;
  }, []);

  const generateVolumeData = useCallback((candleData: CandlestickData[]): HistogramData[] => {
    return candleData.map(candle => ({
      time: candle.time, value: Math.floor(Math.random() * 10000000) + 1000000,
      color: candle.close >= candle.open ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
    }));
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#9ca3af', fontSize: 11 },
      grid: { vertLines: { color: 'rgba(255, 255, 255, 0.03)' }, horzLines: { color: 'rgba(255, 255, 255, 0.03)' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.05)', scaleMargins: { top: 0.1, bottom: 0.25 } },
      timeScale: { borderColor: 'rgba(255, 255, 255, 0.05)', timeVisible: false },
      handleScroll: true, handleScale: true,
    });
    const candleSeries = chart.addSeries(CandlestickSeries, { upColor: '#22c55e', downColor: '#ef4444', borderUpColor: '#22c55e', borderDownColor: '#ef4444', wickUpColor: '#22c55e', wickDownColor: '#ef4444' });
    const volumeSeries = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume' });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chartRef.current = chart; seriesRef.current = candleSeries; volumeSeriesRef.current = volumeSeries;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; volumeSeriesRef.current = null; };
  }, []);

  useEffect(() => {
    if (!price || !seriesRef.current || !volumeSeriesRef.current) return;
    const basePrice = parseFloat(price);
    if (isNaN(basePrice)) return;
    setLoading(true);
    const candles = generateChartData(basePrice, timeframe);
    const volumes = generateVolumeData(candles);
    seriesRef.current.setData(candles); volumeSeriesRef.current.setData(volumes);
    if (chartRef.current) chartRef.current.timeScale().fitContent();
    setLoading(false);
  }, [price, timeframe, generateChartData, generateVolumeData]);

  return (
    <div className="glass rounded-2xl border border-white/[0.06] overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-light text-white">{symbol}</span>
            <span className="text-sm text-gray-500">{companyName}</span>
          </div>
          {price && (
            <div className="flex items-center gap-3 mt-1">
              <span className="text-2xl font-light text-white">{parseFloat(price).toFixed(2)}</span>
              {change && changePct && (
                <span className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                  {isPositive ? '+' : ''}{parseFloat(change).toFixed(2)} ({changePct})
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {(['1D', '1W', '1M', '3M', '1Y'] as const).map(tf => (
            <button key={tf} onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${timeframe === tf ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/30' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'}`}>{tf}</button>
          ))}
        </div>
      </div>
      <div className="relative h-80">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950/50 z-10">
            <div className="flex flex-col items-center gap-3">
              <JanusOrb size={32} thinking />
              <p className="text-xs font-mono text-indigo-400 animate-pulse">Loading chart...</p>
            </div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
      <div className="flex items-center gap-4 px-5 py-2 border-t border-white/5 text-[10px] font-mono text-gray-600">
        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-sm bg-emerald-500/50" />Bullish</div>
        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-sm bg-red-500/50" />Bearish</div>
        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-sm bg-indigo-500/30" />Volume</div>
      </div>
    </div>
  );
}

// ─── Markets Tab ──────────────────────────────────────────────
function MarketsTab() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ symbol: string; name: string; region?: string }[]>([]);
  const [intel, setIntel] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [newsLoading, setNewsLoading] = useState(false);
  const [news, setNews] = useState<any[]>([]);
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
          <CandlestickChart symbol={intel.symbol} companyName={intel.company_name} price={price} change={change} changePct={changePct} isPositive={!!isPositive} />
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-2xl font-light text-white">{intel.symbol}</span>
                  <span className="text-sm text-gray-500">{intel.company_name}</span>
                </div>
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
            <div className="mt-4 pt-4 border-t border-white/5">
              <button onClick={runDeepResearch} disabled={researchLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-xs font-mono text-indigo-300 transition-colors disabled:opacity-40">
                <Sparkles size={12} className={researchLoading ? 'animate-pulse' : ''} />
                {researchLoading ? 'Running research...' : 'Deep Research — Run Full Agent Pipeline'}
              </button>
            </div>
          </div>
          <ResearchPanel result={researchResult} loading={researchLoading} stage={STAGES[researchStage]} />
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
          <div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">
              <Scan size={11} className="text-indigo-400" />
              News {newsLoading && <RefreshCw size={10} className="animate-spin text-indigo-400" />}
            </div>
            {newsLoading && <div className="text-xs font-mono text-gray-600 animate-pulse">Fetching articles...</div>}
            <div className="space-y-2">
              {news.map((a: any, i: number) => <ArticleCard key={`${a.title}-${i}`} article={{ ...a, stance: 'neutral', sentiment_score: 0.5 }} index={i} onResearch={runDeepResearch} />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Pulse Tab ───────────────────────────────────────────────
function PulseTab({ daemonStatus, alerts, memoryStats }: { daemonStatus: DaemonStatus | null; alerts: Alert[]; memoryStats: MemoryStats | null }) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1000);
  };

  const phaseIcons: Record<string, React.ReactNode> = {
    morning: <Sunrise size={16} className="text-amber-400" />,
    daytime: <Sun size={16} className="text-indigo-400" />,
    evening: <Sunset size={16} className="text-violet-400" />,
    night: <Moon size={16} className="text-indigo-300" />,
  };

  return (
    <div className="h-full flex gap-5 overflow-hidden">
      <div className="flex flex-col gap-4 overflow-y-auto pr-1" style={{ width: '40%' }}>
        {daemonStatus?.circadian && (
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-center gap-3 mb-4">
              {phaseIcons[daemonStatus.circadian.current_phase]}
              <div>
                <h3 className="text-sm font-mono text-gray-200">{daemonStatus.circadian.phase_name}</h3>
                <p className="text-[10px] font-mono text-gray-500">{daemonStatus.circadian.phase_description}</p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-gray-500">Priority</span>
                <span className="text-gray-300 capitalize">{daemonStatus.circadian.priority}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-gray-500">Active Tasks</span>
                <span className="text-gray-300">{daemonStatus.circadian.current_tasks.length}</span>
              </div>
            </div>
          </div>
        )}

        {daemonStatus && (
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-indigo-400 uppercase tracking-wider">
              <Radio size={12} /> Signal Queue
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center">
                <div className="text-xl font-light text-white">{daemonStatus.signal_queue?.total_signals || daemonStatus.signals || 0}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Total Signals</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-light text-red-400">{daemonStatus.signal_queue?.severity_counts?.high || 0}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">High Severity</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-light text-amber-400">{daemonStatus.signal_queue?.severity_counts?.medium || 0}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Medium</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-light text-gray-400">{daemonStatus.signal_queue?.severity_counts?.low || 0}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Low</div>
              </div>
            </div>
          </div>
        )}

        {memoryStats && (
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-violet-400 uppercase tracking-wider">
              <Database size={12} /> Memory Graph
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <div className="text-xl font-light text-white">{memoryStats.queries}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Queries</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-light text-indigo-400">{memoryStats.entities}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Entities</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-light text-violet-400">{memoryStats.insights}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase">Insights</div>
              </div>
            </div>
          </div>
        )}

        {daemonStatus && (
          <div className="glass rounded-2xl p-5 border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-emerald-400 uppercase tracking-wider">
              <Activity size={12} /> Daemon Status
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span className="text-emerald-400">Running</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Cycles</span>
                <span className="text-gray-300">{daemonStatus.cycle_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Last Run</span>
                <span className="text-gray-300">{daemonStatus.last_run ? new Date(daemonStatus.last_run).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 overflow-hidden flex-1">
        <div className="flex items-center justify-between shrink-0">
          <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
            Live Alert Feed — {alerts.length} alerts
          </div>
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg glass border border-white/5 hover:border-indigo-500/20 text-[10px] font-mono text-gray-400 hover:text-indigo-300 transition-all disabled:opacity-40">
            <RefreshCw size={10} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {alerts.length > 0 ? (
            alerts.map((alert, i) => <AlertCard key={`${alert.title}-${i}`} alert={alert} index={i} />)
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <CheckCircle size={28} className="text-emerald-500/30 mb-3" />
              <p className="text-sm font-mono text-gray-500">No alerts.</p>
              <p className="text-xs font-mono text-gray-700 mt-1">All systems operating normally.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Workspace Tab ─────────────────────────────────────────────
function WorkspaceTab() {
  const [curiosity, setCuriosity] = useState<any>(null);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [activeWf, setActiveWf] = useState<any>(null);
  const [wfLoading, setWfLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const [curRes, wfRes, sessRes] = await Promise.all([
        fetch(`${baseUrl}/daemon/curiosity`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/workflows?limit=10`).then(r => r.ok ? r.json() : []),
        fetch(`${baseUrl}/sessions?limit=10`).then(r => r.ok ? r.json() : []),
      ]);
      if (curRes) setCuriosity(curRes);
      if (wfRes) setWorkflows(Array.isArray(wfRes) ? wfRes : []);
      if (sessRes) setSessions(Array.isArray(sessRes) ? sessRes : []);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const triggerCuriosity = async () => {
    setTriggering(true);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/daemon/curiosity/now`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setCuriosity(prev => prev ? { ...prev, discoveries: [...(prev.discoveries || []), ...(data.discoveries || [])], total_discoveries: (prev.total_discoveries || 0) + (data.discoveries || []).length } : data);
      }
    } catch { /* silent */ } finally { setTriggering(false); }
  };

  const runWorkflow = async (wf: any) => {
    setActiveWf(wf);
    setWfLoading(true);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/workflows/${wf.id}/run`, { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        setActiveWf(updated);
        setWorkflows(prev => prev.map(w => w.id === wf.id ? updated : w));
      }
    } catch { /* silent */ } finally { setWfLoading(false); }
  };

  const createResearchWf = async () => {
    const query = prompt('Enter research query:');
    if (!query) return;
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/workflows/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (res.ok) {
        const wf = await res.json();
        setWorkflows(prev => [wf, ...prev]);
      }
    } catch { /* silent */ }
  };

  const statusColors: Record<string, string> = {
    pending: 'text-gray-400',
    running: 'text-indigo-400',
    completed: 'text-emerald-400',
    failed: 'text-red-400',
    cancelled: 'text-gray-500',
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <JanusOrb size={48} thinking />
      <p className="text-xs font-mono text-indigo-400 animate-pulse">Loading workspace...</p>
    </div>
  );

  return (
    <div className="h-full flex gap-5 overflow-hidden">
      {/* Left: Discoveries + Sessions */}
      <div className="flex flex-col gap-4 overflow-y-auto pr-1" style={{ width: '45%' }}>
        {/* Curiosity Discoveries */}
        <div className="glass rounded-2xl p-5 border border-white/[0.06]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-xs font-mono text-violet-400 uppercase tracking-wider">
              <Brain size={12} /> Discoveries ({curiosity?.total_discoveries || 0})
            </div>
            <button onClick={triggerCuriosity} disabled={triggering}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600/40 border border-violet-500/30 text-[10px] font-mono text-violet-300 transition-all disabled:opacity-40">
              <Sparkles size={10} className={triggering ? 'animate-pulse' : ''} />
              {triggering ? 'Exploring...' : 'Explore'}
            </button>
          </div>
          <div className="space-y-3">
            {(curiosity?.discoveries || []).slice(-5).reverse().map((d: any, i: number) => (
              <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                className="glass rounded-xl p-3 border border-white/[0.04]">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[9px] font-mono text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded">{d.topic}</span>
                  <span className="text-[9px] font-mono text-gray-600">{new Date(d.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-xs text-gray-300 leading-relaxed">{d.insight}</p>
              </motion.div>
            ))}
            {(!curiosity?.discoveries || curiosity.discoveries.length === 0) && (
              <p className="text-xs font-mono text-gray-600 text-center py-4">No discoveries yet. Click "Explore" to start.</p>
            )}
          </div>
        </div>

        {/* Sessions */}
        <div className="glass rounded-2xl p-5 border border-white/[0.06]">
          <div className="flex items-center gap-2 mb-4 text-xs font-mono text-indigo-400 uppercase tracking-wider">
            <MessageSquare size={12} /> Sessions ({sessions.length})
          </div>
          <div className="space-y-2">
            {sessions.slice(0, 5).map((s: any, i: number) => (
              <div key={s.id} className="flex items-center justify-between text-xs font-mono py-2 px-3 glass rounded-lg border border-white/[0.04]">
                <span className="text-gray-400 truncate">{s.id}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-gray-600">{s.message_count || 0} msgs</span>
                  <span className="text-gray-700">{new Date(s.updated_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
            {sessions.length === 0 && <p className="text-xs font-mono text-gray-600 text-center py-4">No sessions yet. Start a conversation.</p>}
          </div>
        </div>
      </div>

      {/* Right: Workflows */}
      <div className="flex flex-col gap-3 overflow-hidden flex-1">
        <div className="flex items-center justify-between shrink-0">
          <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
            Workflows ({workflows.length})
          </div>
          <div className="flex gap-2">
            <button onClick={createResearchWf}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-[10px] font-mono text-indigo-300 transition-all">
              <Plus size={10} /> Research
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {workflows.map((wf: any, i: number) => (
            <motion.div key={wf.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
              className="glass rounded-xl border border-white/[0.04] hover:border-white/10 transition-colors p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${statusColors[wf.status] || 'text-gray-400'} bg-white/5`}>{wf.status}</span>
                    <span className="text-[9px] font-mono text-gray-600">{wf.type}</span>
                  </div>
                  <p className="text-xs text-gray-300">{wf.query || wf.scenario || 'Untitled'}</p>
                </div>
                {wf.status === 'pending' && (
                  <button onClick={() => runWorkflow(wf)} disabled={wfLoading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 border border-emerald-500/30 text-[10px] font-mono text-emerald-300 transition-all disabled:opacity-40">
                    <Play size={10} /> Run
                  </button>
                )}
              </div>
              {/* Steps */}
              <div className="space-y-1.5">
                {wf.steps?.map((step: any, si: number) => (
                  <div key={step.id} className="flex items-center gap-2 text-[10px] font-mono">
                    <div className={`w-2 h-2 rounded-full ${step.status === 'completed' ? 'bg-emerald-400' : step.status === 'running' ? 'bg-indigo-400 animate-pulse' : step.status === 'failed' ? 'bg-red-400' : 'bg-gray-600'}`} />
                    <span className={step.status === 'completed' ? 'text-emerald-400' : step.status === 'running' ? 'text-indigo-400' : 'text-gray-500'}>{step.name}</span>
                  </div>
                ))}
              </div>
              {wf.metadata && (
                <div className="flex items-center gap-3 mt-3 pt-2 border-t border-white/5 text-[9px] font-mono text-gray-600">
                  <span>{wf.metadata.completed_steps}/{wf.metadata.total_steps} steps</span>
                  {wf.metadata.failed_steps > 0 && <span className="text-red-400">{wf.metadata.failed_steps} failed</span>}
                </div>
              )}
            </motion.div>
          ))}
          {workflows.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <GitBranch size={28} className="text-gray-700 mb-3" />
              <p className="text-sm font-mono text-gray-500">No workflows yet.</p>
              <p className="text-xs font-mono text-gray-700 mt-1">Create a research or simulation workflow.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
//  MAIN APP
// ═══════════════════════════════════════════════════════════
export default function JanusApp() {
  const [systemState, setSystemState] = useState<'art' | 'dashboard'>('art');
  const [activeTab, setActiveTab] = useState<'command' | 'intel' | 'markets' | 'pulse'>('command');
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);

  const fetchSystemData = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const [statusRes, alertsRes, memoryRes] = await Promise.all([
        fetch(`${baseUrl}/daemon/status`).then(r => r.ok ? r.json() : null),
        fetch(`${baseUrl}/daemon/alerts?limit=20`).then(r => r.ok ? r.json() : []),
        fetch(`${baseUrl}/memory/stats`).then(r => r.ok ? r.json() : null),
      ]);
      if (statusRes) setDaemonStatus(statusRes);
      if (alertsRes) setAlerts(Array.isArray(alertsRes) ? alertsRes : []);
      if (memoryRes) setMemoryStats(memoryRes);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchSystemData();
    const interval = setInterval(fetchSystemData, 60000);
    return () => clearInterval(interval);
  }, [fetchSystemData]);

  const tabs = [
    { id: 'command' as const, label: 'Command', icon: Sparkles },
    { id: 'intel' as const, label: 'Intel Stream', icon: Globe },
    { id: 'markets' as const, label: 'Markets', icon: BarChart3 },
    { id: 'workspace' as const, label: 'Workspace', icon: Layers },
    { id: 'pulse' as const, label: 'Pulse', icon: PulseIcon },
  ];

  const alertCount = alerts.filter(a => a.severity === 'high' || a.severity === 'critical').length;

  return (
    <div className="relative min-h-screen bg-transparent text-gray-100 overflow-hidden">
      <AnimatePresence>
        {systemState === 'art' && <ArtPiece onUnlock={() => setSystemState('dashboard')} />}
      </AnimatePresence>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: systemState === 'dashboard' ? 1 : 0 }} transition={{ duration: 1.2, delay: 0.5 }}
        className={`relative z-10 flex flex-col h-screen max-w-[1480px] mx-auto px-6 py-5 ${systemState === 'art' ? 'pointer-events-none' : ''}`}>

        {/* Header */}
        <header className="flex items-center justify-between mb-5 shrink-0">
          <div className="flex items-center gap-4">
            <JanusOrb size={32} thinking={activeTab === 'command'} phase={daemonStatus?.circadian?.current_phase || 'daytime'} />
            <div>
              <h1 className="text-lg font-light tracking-[0.15em] bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-400 bg-clip-text text-transparent">JANUS</h1>
              <StatusBar daemonStatus={daemonStatus} memoryStats={memoryStats} alertCount={alertCount} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${daemonStatus?.running ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'}`} />
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
              {daemonStatus?.running ? 'Living' : 'Offline'}
            </span>
          </div>
        </header>

        {/* Navigation */}
        <nav className="flex gap-1 mb-5 shrink-0">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 text-sm ${activeTab === tab.id ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>
              {activeTab === tab.id && <motion.div layoutId="tabIndicator" className="absolute inset-0 glass rounded-xl" transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }} />}
              <tab.icon size={15} className="relative z-10" />
              <span className="relative z-10 font-mono text-xs uppercase tracking-wider">{tab.label}</span>
              {tab.id === 'pulse' && alertCount > 0 && (
                <span className="relative z-10 px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-300 text-[9px] font-mono">{alertCount}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main className="flex-1 min-h-0 overflow-hidden">
          <AnimatePresence mode="wait">
            {activeTab === 'command' && (
              <motion.div key="command" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full">
                <CommandTab />
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
            {activeTab === 'workspace' && (
              <motion.div key="workspace" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full">
                <WorkspaceTab />
              </motion.div>
            )}
            {activeTab === 'pulse' && (
              <motion.div key="pulse" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }} className="h-full">
                <PulseTab daemonStatus={daemonStatus} alerts={alerts} memoryStats={memoryStats} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </motion.div>
    </div>
  );
}
