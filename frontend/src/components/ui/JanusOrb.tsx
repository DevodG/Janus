'use client';

import { motion } from 'framer-motion';

interface JanusOrbProps {
  size?: number;
  thinking?: boolean;
  phase?: string;
}

const phaseColors: Record<string, { from: string; to: string; shadow: string }> = {
  morning: { from: '#fbbf24', to: '#f59e0b', shadow: 'rgba(251,191,36,0.4)' },
  daytime: { from: '#818cf8', to: '#4f46e5', shadow: 'rgba(99,102,241,0.4)' },
  evening: { from: '#a78bfa', to: '#7c3aed', shadow: 'rgba(167,139,250,0.4)' },
  night: { from: '#6366f1', to: '#312e81', shadow: 'rgba(99,102,241,0.3)' },
};

export default function JanusOrb({ size = 32, thinking = false, phase = 'daytime' }: JanusOrbProps) {
  const colors = phaseColors[phase] || phaseColors.daytime;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle at 30% 30%, ${colors.from}, ${colors.to} 50%, #0f172a 100%)`,
          boxShadow: thinking
            ? `0 0 30px ${colors.shadow}, 0 0 60px ${colors.shadow}`
            : `0 0 15px ${colors.shadow}`,
        }}
        animate={thinking ? { scale: [1, 1.12, 1] } : { scale: [1, 1.03, 1] }}
        transition={{ duration: thinking ? 1.2 : 4, repeat: Infinity, ease: 'easeInOut' }}
      />
      {thinking && (
        <>
          <div className="absolute inset-[-6px] rounded-full border border-indigo-400/30"
            style={{ borderTopColor: 'transparent', borderBottomColor: 'transparent', animation: 'spin 2s linear infinite' }} />
          <div className="absolute inset-[-12px] rounded-full border border-violet-400/20"
            style={{ borderLeftColor: 'transparent', borderRightColor: 'transparent', animation: 'spin 3s linear infinite reverse' }} />
          <div className="absolute inset-[-18px] rounded-full border border-indigo-300/10"
            style={{ borderTopColor: 'transparent', borderRightColor: 'transparent', animation: 'spin 4s linear infinite' }} />
        </>
      )}
    </div>
  );
}
