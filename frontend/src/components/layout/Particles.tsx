'use client';

import { useState, useEffect } from 'react';

// ─── Floating Particles Background ─────────────────────────
export default function Particles() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  // Deterministic pseudo-random based on index
  const seed = (i: number) => ((i * 7 + 13) % 100) / 100;
  const particles = Array.from({ length: 12 }, (_, i) => ({
    id: i,
    size: 80 + seed(i) * 300,
    x: seed(i + 3) * 100,
    delay: seed(i + 5) * 20,
    duration: 18 + seed(i + 7) * 20,
    opacity: 0.015 + seed(i + 9) * 0.025,
  }));

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {particles.map((p) => (
        <div
          key={p.id}
          className="particle absolute rounded-full"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
            bottom: `-${p.size}px`,
            background: `radial-gradient(circle, rgba(99,102,241,${p.opacity * 3}) 0%, rgba(139,92,246,${p.opacity}) 60%, transparent 100%)`,
            '--delay': `${p.delay}s`,
            '--duration': `${p.duration}s`,
          } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
