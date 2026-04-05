'use client';

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function StanceChip({ stance, score }: { stance: string; score: number }) {
  if (stance === 'bullish')
    return <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full"><TrendingUp size={9} />Bull {Math.round(score * 100)}%</span>;
  if (stance === 'bearish')
    return <span className="flex items-center gap-1 text-[10px] font-mono text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full"><TrendingDown size={9} />Bear {Math.round((1 - score) * 100)}%</span>;
  return <span className="flex items-center gap-1 text-[10px] font-mono text-gray-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full"><Minus size={9} />Neutral</span>;
}

export function SignalBadge({ signal, conviction }: { signal: string; conviction: number }) {
  const map: Record<string, string> = {
    BUY: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    SELL: 'bg-red-500/20 text-red-300 border-red-500/40',
    HOLD: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    WATCH: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
  };
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border ${map[signal] || map.WATCH}`}>
      <span className="text-sm font-mono font-bold">{signal}</span>
      <span className="text-[10px] font-mono opacity-70">{Math.round(conviction * 100)}% conviction</span>
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-300 border-red-500/30',
    high: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    medium: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  return <span className={`px-2 py-0.5 rounded border text-[9px] font-mono uppercase tracking-wider ${map[severity] || map.low}`}>{severity}</span>;
}
