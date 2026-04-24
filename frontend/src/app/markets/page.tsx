'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, BarChart3, TrendingUp, TrendingDown, Minus,
  AlertTriangle, Sparkles, Zap, RefreshCw, Scan, ExternalLink
} from 'lucide-react';
import { financeClient, apiClient } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, CandlestickData, HistogramData } from 'lightweight-charts';

// ─── Chips ─────────────────────────────────────────────────
function StanceChip({ stance, score }: { stance: string; score: number }) {
  if (stance === 'bullish') return <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full"><TrendingUp size={9} />Bull {Math.round(score * 100)}%</span>;
  if (stance === 'bearish') return <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full"><TrendingDown size={9} />Bear {Math.round((1 - score) * 100)}%</span>;
  return <span className="flex items-center gap-1 text-[10px] text-gray-500 bg-white/[0.04] border border-white/[0.06] px-2 py-0.5 rounded-full"><Minus size={9} />Neutral</span>;
}

function SignalBadge({ signal, conviction }: { signal: string; conviction: number }) {
  const map: Record<string, string> = { BUY: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', SELL: 'bg-red-500/15 text-red-300 border-red-500/30', HOLD: 'bg-amber-500/15 text-amber-300 border-amber-500/30', WATCH: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30' };
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-xl border ${map[signal] || map.WATCH}`}>
      <span className="text-[12px] font-semibold">{signal}</span>
      <span className="text-[10px] opacity-70">{Math.round(conviction * 100)}%</span>
    </div>
  );
}

// ─── Chart ─────────────────────────────────────────────────
function CandlestickChart({ symbol, companyName, price, change, changePct, isPositive }: { symbol: string; companyName: string; price?: string; change?: string; changePct?: string; isPositive?: boolean }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null);
  const volumeSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null);
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '3M' | '1Y'>('1M');

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
      data.push({ time: date.toISOString().split('T')[0], open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2) });
      currentPrice = close;
    }
    return data;
  }, []);

  const generateVolumeData = useCallback((candleData: CandlestickData[]): HistogramData[] => {
    return candleData.map(c => ({ time: c.time, value: Math.floor(Math.random() * 10000000) + 1000000, color: c.close >= c.open ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)' }));
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#6b7280', fontSize: 11 },
      grid: { vertLines: { color: 'rgba(255,255,255,0.02)' }, horzLines: { color: 'rgba(255,255,255,0.02)' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.04)', scaleMargins: { top: 0.1, bottom: 0.25 } },
      timeScale: { borderColor: 'rgba(255,255,255,0.04)', timeVisible: false },
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
    const candles = generateChartData(basePrice, timeframe);
    const volumes = generateVolumeData(candles);
    seriesRef.current.setData(candles); volumeSeriesRef.current.setData(volumes);
    if (chartRef.current) chartRef.current.timeScale().fitContent();
  }, [price, timeframe, generateChartData, generateVolumeData]);

  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.04]">
        <div>
          <div className="flex items-center gap-2"><span className="text-lg font-light text-white">{symbol}</span><span className="text-[13px] text-gray-500">{companyName}</span></div>
          {price && (
            <div className="flex items-center gap-3 mt-1">
              <span className="text-2xl font-light text-white">{parseFloat(price).toFixed(2)}</span>
              {change && changePct && <span className={`text-[13px] ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>{isPositive ? '+' : ''}{parseFloat(change).toFixed(2)} ({changePct})</span>}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">{(['1D','1W','1M','3M','1Y'] as const).map(tf => (
          <button key={tf} onClick={() => setTimeframe(tf)} className={`px-3 py-1 rounded-lg text-[11px] transition-all ${timeframe === tf ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20' : 'text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]'}`}>{tf}</button>
        ))}</div>
      </div>
      <div className="h-72"><div ref={chartContainerRef} className="w-full h-full" /></div>
    </div>
  );
}

// ─── Research Panel ────────────────────────────────────────
const STAGES = ['Routing to switchboard...', 'Scanning sources...', 'Cross-referencing...', 'Synthesizing...'];

// ═══════════════════════════════════════════════════════════
export default function MarketsPage() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ symbol: string; name: string; region?: string }[]>([]);
  const [intel, setIntel] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [news, setNews] = useState<any[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [activeSymbol, setActiveSymbol] = useState('');
  const [error, setError] = useState<string | null>(null);
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
      try { setSearchResults(await financeClient.searchTicker(val)); } catch { setSearchResults([]); }
    }, 400);
  };

  const loadTicker = useCallback(async (symbol: string) => {
    setLoading(true); setIntel(null); setNews([]); setActiveSymbol(symbol); setSearchResults([]); setError(null); setResearchResult(null);
    try {
      const data = await financeClient.getTickerIntelligence(symbol);
      setIntel(data); setNewsLoading(true);
      try { const nd = await financeClient.analyzeNews(data.company_name || symbol, 8); setNews(nd.articles || []); } catch { /* silent */ } finally { setNewsLoading(false); }
    } catch { setError(`Could not load intelligence for ${symbol}. Ensure ALPHAVANTAGE_API_KEY is set.`); }
    finally { setLoading(false); }
  }, []);

  const runDeepResearch = async () => {
    if (!intel) return;
    const q = `Analyze ${intel.company_name} (${intel.symbol}) stock. ${intel.overview?.description || ''}`.slice(0, 500);
    setResearchLoading(true); setResearchResult(null); setResearchStage(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => setResearchStage(p => (p + 1) % STAGES.length), 3000);
    try { const res = await apiClient.run(q); setResearchResult(res); } catch { /* silent */ }
    finally { setResearchLoading(false); if (stageTimer.current) clearInterval(stageTimer.current); }
  };

  const price = intel?.quote?.['05. price'];
  const change = intel?.quote?.['09. change'];
  const changePct = intel?.quote?.['10. change percent'];
  const isPositive = change && parseFloat(change) >= 0;

  const quickTickers = [
    { s: 'RELIANCE.BSE', l: 'Reliance' },
    { s: 'TCS.BSE', l: 'TCS' },
    { s: 'AAPL', l: 'Apple' },
    { s: 'TSLA', l: 'Tesla' },
    { s: 'MSFT', l: 'Microsoft' },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 pt-6 pb-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <BarChart3 size={16} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-light text-gray-100">Markets</h1>
            <p className="text-[11px] text-gray-600">Ticker intelligence powered by Alpha Vantage + Janus AI</p>
          </div>
        </div>
        <div className="relative">
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-white/[0.06] focus-within:border-indigo-500/30 transition-colors" style={{ background: 'var(--janus-surface)' }}>
            <Search size={14} className="text-gray-600 shrink-0" />
            <input
              value={query}
              onChange={e => handleQueryChange(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setSearchResults([]); loadTicker(query.toUpperCase()); } }}
              placeholder="Search — RELIANCE, TCS, AAPL, TSLA..."
              className="flex-1 bg-transparent text-[13px] text-gray-200 placeholder-gray-600 focus:outline-none"
            />
            {query && (
              <button onClick={() => { setSearchResults([]); loadTicker(query.toUpperCase()); }} className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] transition-colors">
                Analyze
              </button>
            )}
          </div>
          {/* Autocomplete */}
          <AnimatePresence>
            {searchResults.length > 0 && (
              <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute top-full left-0 right-0 mt-1 rounded-xl border border-white/[0.08] overflow-hidden z-20" style={{ background: 'var(--janus-surface)' }}>
                {searchResults.slice(0, 6).map(r => (
                  <button key={r.symbol} onClick={() => { setQuery(r.symbol); loadTicker(r.symbol); }}
                    className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.04] transition-colors text-left">
                    <span className="text-[13px] text-indigo-300">{r.symbol}</span>
                    <div className="flex items-center gap-3">
                      {r.region && <span className="text-[10px] text-gray-600 bg-white/[0.04] px-1.5 py-0.5 rounded">{r.region}</span>}
                      <span className="text-[12px] text-gray-500 truncate max-w-[200px]">{r.name}</span>
                    </div>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <RefreshCw size={20} className="text-indigo-400 animate-spin" />
            <p className="text-[12px] text-indigo-400">Fetching intelligence for {activeSymbol}...</p>
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <AlertTriangle size={24} className="text-amber-500/50" />
            <p className="text-[13px] text-amber-400 max-w-md text-center">{error}</p>
          </div>
        )}

        {!loading && !intel && !error && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <BarChart3 size={28} className="text-gray-700" />
            <p className="text-[13px] text-gray-500">Search any stock — Indian or global</p>
            <div className="flex gap-2 mt-3 flex-wrap justify-center">
              {quickTickers.map(({ s, l }) => (
                <button key={s} onClick={() => { setQuery(s); loadTicker(s); }} className="px-3 py-1.5 rounded-full border border-white/[0.06] hover:border-indigo-500/20 text-[12px] text-gray-500 hover:text-indigo-300 transition-all">{l}</button>
              ))}
            </div>
          </div>
        )}

        {!loading && intel && (
          <>
            <CandlestickChart symbol={intel.symbol} companyName={intel.company_name} price={price} change={change} changePct={changePct} isPositive={!!isPositive} />

            {/* Overview card */}
            <div className="card p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xl font-light text-white">{intel.symbol}</span>
                    <span className="text-[13px] text-gray-500">{intel.company_name}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {intel.overview?.sector && <span className="text-[10px] text-gray-500 bg-white/[0.04] px-2 py-0.5 rounded">{intel.overview.sector}</span>}
                    {intel.overview?.industry && <span className="text-[10px] text-gray-500 bg-white/[0.04] px-2 py-0.5 rounded">{intel.overview.industry}</span>}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  {intel.ai_signal && <SignalBadge signal={intel.ai_signal.signal} conviction={intel.ai_signal.conviction} />}
                  {intel.stance && <StanceChip stance={intel.stance.stance} score={intel.stance.sentiment_score} />}
                </div>
              </div>

              {intel.ai_signal?.reasoning && (
                <div className="mt-4 pt-4 border-t border-white/[0.04]">
                  <div className="flex items-center gap-2 mb-1.5 text-[10px] text-indigo-400 uppercase tracking-wider"><Zap size={10} /> AI Signal</div>
                  <p className="text-[12px] text-gray-400 leading-relaxed">{intel.ai_signal.reasoning}</p>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-white/[0.04]">
                <button onClick={runDeepResearch} disabled={researchLoading} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/15 text-[12px] text-indigo-400 transition-all disabled:opacity-40">
                  <Sparkles size={12} className={researchLoading ? 'animate-pulse' : ''} />
                  {researchLoading ? 'Running research...' : 'Deep Research — Full Pipeline'}
                </button>
              </div>
            </div>

            {/* Research result */}
            {(researchResult || researchLoading) && (
              <div className="card p-5">
                {researchLoading ? (
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full border border-indigo-500/30 border-t-indigo-400 animate-spin" />
                    <p className="text-[12px] text-indigo-400">{STAGES[researchStage]}</p>
                  </div>
                ) : researchResult ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-[10px] text-indigo-400 uppercase tracking-wider"><Zap size={11} /> Research Complete</div>
                    {researchResult.final_answer && (
                      <div className="text-[13px] text-gray-300 leading-relaxed whitespace-pre-wrap">{researchResult.final_answer}</div>
                    )}
                  </div>
                ) : null}
              </div>
            )}

            {/* Fundamentals + Events grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="card p-4 space-y-2">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-3">Fundamentals</div>
                {(() => {
                  const rows: [string, string | undefined][] = [
                    ['P/E Ratio', intel.overview?.pe_ratio],
                    ['Market Cap', intel.overview?.market_cap ? (Number(intel.overview.market_cap) > 1e9 ? `$${(Number(intel.overview.market_cap) / 1e9).toFixed(1)}B` : Number(intel.overview.market_cap) > 1e6 ? `$${(Number(intel.overview.market_cap) / 1e6).toFixed(0)}M` : intel.overview.market_cap) : undefined],
                    ['52W High', intel.overview?.['52_week_high']],
                    ['52W Low', intel.overview?.['52_week_low']],
                    ['Analyst Target', intel.overview?.analyst_target],
                    ['Volume', intel.quote?.['06. volume'] ? Number(intel.quote['06. volume']).toLocaleString() : undefined],
                    ['Previous Close', intel.quote?.['08. previous close']],
                    ['Day High', intel.quote?.['03. high']],
                    ['Day Low', intel.quote?.['04. low']],
                    ['Open', intel.quote?.['02. open']],
                  ];
                  const validRows = rows.filter(([, v]) => v && v !== 'None' && v !== '-' && v !== 'N/A' && v !== '0' && v !== 'undefined');
                  return validRows.length > 0 ? (
                    validRows.map(([k, v]) => (
                      <div key={k} className="flex justify-between text-[12px] border-b border-white/[0.03] pb-1.5">
                        <span className="text-gray-500">{k}</span><span className="text-gray-300">{v}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-[12px] text-gray-600">No fundamental data available.</p>
                      <p className="text-[10px] text-gray-700 mt-1">Ticker may not be covered by Alpha Vantage.</p>
                    </div>
                  );
                })()}
              </div>
              <div className="card p-4 space-y-3">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-3">Event Intelligence</div>
                {intel.event_impact && intel.event_impact.event_count > 0 ? (
                  <>
                    <div className="text-[12px]"><span className="text-gray-500">Impact: </span><span className={intel.event_impact.impact_level === 'high' || intel.event_impact.impact_level === 'very_high' ? 'text-amber-400' : 'text-gray-300'}>{intel.event_impact.impact_level}</span></div>
                    <div className="text-[12px]"><span className="text-gray-500">Volatility: </span><span className={intel.event_impact.volatility_level === 'high' || intel.event_impact.volatility_level === 'very_high' ? 'text-red-400' : 'text-gray-300'}>{intel.event_impact.volatility_level}</span></div>
                    <div className="text-[12px]"><span className="text-gray-500">Events: </span><span className="text-gray-300">{intel.event_impact.event_count} detected</span></div>
                    {intel.event_impact.detected_events && intel.event_impact.detected_events.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/[0.04]">
                        {intel.event_impact.detected_events.map((ev: any, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded text-[9px] text-amber-300 bg-amber-500/10 border border-amber-500/15 uppercase tracking-wider">
                            {ev.event_type?.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div className="text-[12px]"><span className="text-gray-500">Impact: </span><span className="text-emerald-400">Low</span></div>
                    <div className="text-[12px]"><span className="text-gray-500">Volatility: </span><span className="text-emerald-400">Low</span></div>
                    <div className="text-[12px]"><span className="text-gray-500">Events: </span><span className="text-gray-300">None detected</span></div>
                    <p className="text-[10px] text-gray-700 mt-2 pt-2 border-t border-white/[0.04]">
                      No significant market events detected in recent news for this ticker. This usually indicates stable conditions.
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* News */}
            {(news.length > 0 || newsLoading) && (
              <div>
                <div className="flex items-center gap-2 text-[11px] text-gray-500 uppercase tracking-wider mb-3">
                  <Scan size={11} className="text-indigo-400" /> News
                  {newsLoading && <RefreshCw size={10} className="animate-spin text-indigo-400" />}
                </div>
                <div className="space-y-3">
                  {news.map((a: any, i: number) => (
                    <div key={`${a.title}-${i}`} className="card p-3 hover:border-white/[0.12]">
                      <p className="text-[13px] text-gray-300 leading-snug mb-1">{a.title}</p>
                      {a.description && <p className="text-[11px] text-gray-600 line-clamp-1">{a.description}</p>}
                      <div className="flex items-center gap-3 mt-2">
                        {a.source && <span className="text-[10px] text-gray-600">{a.source}</span>}
                        {a.url && <a href={a.url} target="_blank" rel="noreferrer" className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"><ExternalLink size={8} /> Read</a>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
