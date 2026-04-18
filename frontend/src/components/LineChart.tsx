'use client';
/**
 * LineChart.tsx — Real historical price chart using lightweight-charts v5
 *
 * Fetches from /finance/historical/{symbol} (yfinance → Finnhub → FMP fallback chain)
 * Supports timeframe switching: 1W | 1M | 3M | 6M | 1Y
 * Gracefully degrades to a "no data" state if all sources fail.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface HistoricalPoint {
  date:   string;
  open:   number;
  high:   number;
  low:    number;
  close:  number;
  volume: number;
}

interface Props {
  symbol:      string;
  companyName?: string;
  isPositive?: boolean;
  height?:     number;
}

type Timeframe = '1W' | '1M' | '3M' | '6M' | '1Y';

const TIMEFRAME_DAYS: Record<Timeframe, number> = {
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:7860';

export default function LineChart({ symbol, companyName, isPositive = true, height = 280 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<unknown>(null);
  const seriesRef    = useRef<unknown>(null);

  const [allData, setAllData]       = useState<HistoricalPoint[]>([]);
  const [timeframe, setTimeframe]   = useState<Timeframe>('3M');
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange]   = useState<{ abs: number; pct: number } | null>(null);

  // ── Fetch historical data ──────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 25_000);
      const res = await fetch(
        `${API_BASE}/finance/historical/${symbol.toUpperCase()}?outputsize=full`,
        { signal: ctrl.signal }
      );
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const data: HistoricalPoint[] = json.data ?? [];
      setAllData(data);
      if (data.length > 0) {
        const last  = data[data.length - 1];
        const first = data[data.length - 2] ?? data[0];
        setCurrentPrice(last.close);
        setPriceChange({
          abs: last.close - first.close,
          pct: ((last.close - first.close) / first.close) * 100,
        });
      }
    } catch (e: unknown) {
      const msg = (e as Error).name === 'AbortError'
        ? 'Request timed out'
        : 'Failed to load chart data';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Filter by timeframe ────────────────────────────────────────────────
  const filteredData = useCallback((): HistoricalPoint[] => {
    if (!allData.length) return [];
    const days  = TIMEFRAME_DAYS[timeframe];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return allData.filter(d => d.date >= cutoffStr);
  }, [allData, timeframe]);

  // ── Build/update chart ────────────────────────────────────────────────
  useEffect(() => {
    if (loading || !containerRef.current) return;

    const data = filteredData();

    // Lazy-load lightweight-charts
    import('lightweight-charts').then(({ AreaSeries, LineSeries, LineStyle, createChart }) => {
      // Destroy previous chart
      if (chartRef.current) {
        (chartRef.current as { remove(): void }).remove();
        chartRef.current = null;
        seriesRef.current = null;
      }

      if (!containerRef.current || data.length === 0) return;

      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

      const chart = createChart(containerRef.current, {
        width:  containerRef.current.clientWidth,
        height,
        layout: {
          background: { color: 'transparent' },
          textColor:  isDark ? '#9ca3af' : '#6b7280',
          fontSize:   11,
        },
        grid: {
          vertLines:  { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          horzLines:  { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
        },
        crosshair: { mode: 1 },
        rightPriceScale: {
          borderColor:    'transparent',
          scaleMargins:   { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor:   'transparent',
          timeVisible:   true,
          secondsVisible: false,
        },
        handleScroll: true,
        handleScale:  true,
      });

      const color = isPositive ? '#10b981' : '#ef4444';

      const series = chart.addSeries(LineSeries, {
        color,
        lineWidth:     2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius:  4,
        lastValueVisible:       true,
        priceLineVisible:       true,
        priceLineStyle:         LineStyle.Dashed,
        priceLineWidth:         1,
        priceLineColor:         color,
      });

      const chartData = data.map(d => ({ time: d.date as string, value: d.close }));
      series.setData(chartData);

      // Area fill
      const areaSeries = chart.addSeries(AreaSeries, {
        topColor:    isPositive ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
        bottomColor: 'rgba(0,0,0,0)',
        lineColor:   'transparent',
        lineWidth:   1,
      });
      areaSeries.setData(chartData);

      chart.timeScale().fitContent();

      chartRef.current  = chart;
      seriesRef.current = series;

      // Resize observer
      const ro = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      if (containerRef.current) ro.observe(containerRef.current);
    }).catch(() => {
      setError('Chart library failed to load');
    });

    return () => {
      if (chartRef.current) {
        (chartRef.current as { remove(): void }).remove();
        chartRef.current  = null;
        seriesRef.current = null;
      }
    };
  }, [loading, timeframe, allData, isPositive, height, filteredData]);

  // ── Render ─────────────────────────────────────────────────────────────
  const positiveClass = isPositive ? 'text-emerald-400' : 'text-red-400';

  return (
    <div className="relative w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div>
          {currentPrice !== null && (
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-semibold tabular-nums">
                ${currentPrice.toFixed(2)}
              </span>
              {priceChange && (
                <span className={`text-sm ${positiveClass}`}>
                  {priceChange.abs >= 0 ? '+' : ''}{priceChange.abs.toFixed(2)}
                  {' '}({priceChange.pct >= 0 ? '+' : ''}{priceChange.pct.toFixed(2)}%)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Timeframe buttons */}
        <div className="flex gap-1">
          {(Object.keys(TIMEFRAME_DAYS) as Timeframe[]).map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors
                ${timeframe === tf
                  ? 'bg-white/10 text-white'
                  : 'text-gray-500 hover:text-gray-300'
                }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      <div style={{ height, position: 'relative' }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex gap-1">
              {[0,1,2].map(i => (
                <div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-white/30 animate-pulse"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-gray-500">
            <span className="text-sm">{error}</span>
            <button
              onClick={fetchData}
              className="text-xs text-blue-400 hover:text-blue-300 underline"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && allData.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
            No chart data available for {symbol}
          </div>
        )}

        <div ref={containerRef} className="w-full" style={{ height }} />
      </div>
    </div>
  );
}
