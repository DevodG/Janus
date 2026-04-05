'use client';

import { motion } from 'framer-motion';

export default function ConfidenceRing({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100);
  const circ = 2 * Math.PI * 18;
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-10 h-10">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="2" />
          <motion.circle
            cx="20" cy="20" r="18" fill="none"
            stroke={value >= 0.7 ? '#22c55e' : value >= 0.5 ? '#eab308' : '#ef4444'}
            strokeWidth="2" strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ * (1 - value) }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-mono text-gray-300">{pct}</span>
      </div>
      <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}
