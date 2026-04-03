'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, FolderOpen, FlaskConical, Terminal, Settings, Shield } from 'lucide-react';
import { motion } from 'framer-motion';

const navItems = [
  { href: '/', label: 'Overview', icon: Home },
  { href: '/cases', label: 'Cases', icon: FolderOpen },
  { href: '/simulation', label: 'Simulations', icon: FlaskConical },
  { href: '/sentinel', label: 'Sentinel', icon: Shield },
  { href: '/prompts', label: 'Prompt Lab', icon: Terminal },
  { href: '/config', label: 'Config', icon: Settings },
];

export default function JanusSidebar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 h-12 z-40 flex items-center px-6 border-b border-white/[0.04] bg-gray-950/80 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex items-center gap-2.5 mr-8">
        <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.6)] animate-pulse" />
        <span className="font-light tracking-[0.25em] text-[11px] text-gradient-subtle uppercase">JANUS.OS</span>
      </div>

      {/* Nav items */}
      <div className="flex items-center gap-1 flex-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 text-[11px] font-mono uppercase tracking-wider ${
                isActive ? 'text-white' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="topNavActive"
                  className="absolute inset-0 bg-white/[0.06] rounded-lg border border-white/[0.08]"
                  transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
                />
              )}
              <item.icon size={13} className={`relative z-10 ${isActive ? 'text-indigo-400' : ''}`} aria-hidden />
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Status dot */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping opacity-40" />
        </div>
        <span className="text-[9px] font-mono text-emerald-400/60 uppercase tracking-widest">Active</span>
      </div>
    </nav>
  );
}
