'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Globe, BarChart3, Layers, Activity as PulseIcon,
  Zap, Hexagon, Shield, Terminal, Settings,
  ChevronLeft, ChevronRight, Menu, X
} from 'lucide-react';

const navItems = [
  { id: '/', label: 'Command', icon: Sparkles, section: 'Main' },
  { id: '/intel', label: 'Intel Stream', icon: Globe, section: 'Main' },
  { id: '/markets', label: 'Markets', icon: BarChart3, section: 'Main' },
  { id: '/workspace', label: 'Workspace', icon: Layers, section: 'Main' },
  { id: '/pulse', label: 'Pulse', icon: PulseIcon, section: 'Main' },
  { id: '/cases', label: 'Cases', icon: Hexagon, section: 'System' },
  { id: '/simulation', label: 'Simulations', icon: Zap, section: 'System' },
  { id: '/sentinel', label: 'Sentinel', icon: Shield, section: 'System' },
  { id: '/prompts', label: 'Prompt Lab', icon: Terminal, section: 'System' },
  { id: '/config', label: 'Config', icon: Settings, section: 'System' },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [daemonStatus, setDaemonStatus] = useState<any>(null);

  const fetchStatus = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const r = await fetch(`${baseUrl}/daemon/status`);
      if (r.ok) setDaemonStatus(await r.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchStatus();
    const iv = setInterval(fetchStatus, 60000);
    return () => clearInterval(iv);
  }, [fetchStatus]);

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname?.startsWith(path);
  };

  const sections = ['Main', 'System'];

  return (
    <div className="h-screen bg-gray-950 text-gray-100 flex overflow-hidden">
      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 64 : 240 }}
        className={`hidden lg:flex flex-col bg-gray-900/80 border-r border-white/5 relative z-30 shrink-0`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-4 border-b border-white/5">
          {!collapsed && (
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm font-light tracking-[0.2em] bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              JANUS
            </motion.span>
          )}
          <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors">
            {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
          {sections.map(section => (
            <div key={section}>
              {!collapsed && (
                <div className="px-3 py-2 text-[9px] font-mono text-gray-600 uppercase tracking-widest">
                  {section}
                </div>
              )}
              {navItems.filter(item => item.section === section).map(item => {
                const active = isActive(item.id);
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => router.push(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 text-sm ${
                      active
                        ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/5 border border-transparent'
                    } ${collapsed ? 'justify-center' : ''}`}
                    title={collapsed ? item.label : undefined}
                  >
                    <Icon size={16} className="shrink-0" />
                    {!collapsed && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-mono text-[11px] uppercase tracking-wider truncate">
                        {item.label}
                      </motion.span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Status */}
        {!collapsed && (
          <div className="px-4 py-3 border-t border-white/5">
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${daemonStatus?.running ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                {daemonStatus?.running ? 'Living' : 'Offline'}
              </span>
            </div>
            {daemonStatus?.circadian && (
              <div className="text-[9px] font-mono text-gray-700 mt-1 capitalize">
                {daemonStatus.circadian.current_phase} phase
              </div>
            )}
          </div>
        )}
      </motion.aside>

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-gray-900/90 backdrop-blur-sm border-b border-white/5 flex items-center justify-between px-4 z-30">
        <button onClick={() => setMobileOpen(true)} className="p-2 rounded-lg hover:bg-white/5 text-gray-400">
          <Menu size={18} />
        </button>
        <span className="text-sm font-light tracking-[0.2em] bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">JANUS</span>
        <div className="w-8" />
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 left-0 bottom-0 w-72 bg-gray-900 border-r border-white/5 z-50 lg:hidden"
          >
            <div className="flex items-center justify-between h-14 px-4 border-b border-white/5">
              <span className="text-sm font-light tracking-[0.2em] bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">JANUS</span>
              <button onClick={() => setMobileOpen(false)} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500">
                <X size={16} />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
              {sections.map(section => (
                <div key={section}>
                  <div className="px-3 py-2 text-[9px] font-mono text-gray-600 uppercase tracking-widest">{section}</div>
                  {navItems.filter(item => item.section === section).map(item => {
                    const active = isActive(item.id);
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => { router.push(item.id); setMobileOpen(false); }}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm ${
                          active ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5 border border-transparent'
                        }`}
                      >
                        <Icon size={16} className="shrink-0" />
                        <span className="font-mono text-[11px] uppercase tracking-wider">{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              ))}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-hidden pt-14 lg:pt-0">
        {children}
      </main>
    </div>
  );
}
