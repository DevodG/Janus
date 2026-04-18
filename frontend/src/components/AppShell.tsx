'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, Globe, BarChart3, Layers, Activity,
  Zap, Shield, Terminal, Settings, Plus,
  ChevronLeft, ChevronRight, Menu, X, Brain
} from 'lucide-react';

const navSections = [
  {
    label: 'Main',
    items: [
      { path: '/', label: 'Chat', icon: MessageSquare },
      { path: '/intel', label: 'Intel', icon: Globe },
      { path: '/markets', label: 'Markets', icon: BarChart3 },
      { path: '/workspace', label: 'Workspace', icon: Brain },
      { path: '/pulse', label: 'Pulse', icon: Activity },
    ],
  },
  {
    label: 'System',
    items: [
      { path: '/cases', label: 'Cases', icon: Layers },
      { path: '/simulation', label: 'Simulation', icon: Zap },
      { path: '/sentinel', label: 'Sentinel', icon: Shield },
      { path: '/prompts', label: 'Prompts', icon: Terminal },
      { path: '/config', label: 'Config', icon: Settings },
    ],
  },
];

function JanusOrbSmall({ pulse = false }: { pulse?: boolean }) {
  return (
    <div className="relative w-8 h-8 shrink-0">
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'radial-gradient(circle at 35% 35%, #818cf8, #4f46e5 60%, #1e1b4b 100%)',
          boxShadow: '0 0 12px rgba(99,102,241,0.3)',
        }}
      />
      {pulse && (
        <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-indigo-400" />
      )}
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [daemonStatus, setDaemonStatus] = useState<any>(null);

  const fetchStatus = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7860';
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

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname?.startsWith(path);
  };

  const NavContent = ({ isMobile = false }: { isMobile?: boolean }) => (
    <>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-white/[0.04] shrink-0">
        <JanusOrbSmall pulse={daemonStatus?.running} />
        {(!collapsed || isMobile) && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-[13px] font-light tracking-[0.2em] text-gradient"
          >
            JANUS
          </motion.span>
        )}
      </div>

      {/* New Chat button */}
      <div className="px-3 pt-3 pb-1 shrink-0">
        <button
          onClick={() => router.push('/')}
          className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.03] transition-all text-sm text-gray-400 hover:text-gray-200 ${collapsed && !isMobile ? 'justify-center' : ''}`}
        >
          <Plus size={16} className="shrink-0" />
          {(!collapsed || isMobile) && <span className="text-[12px]">New conversation</span>}
        </button>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto py-2 px-2">
        {navSections.map(section => (
          <div key={section.label} className="mb-1">
            {(!collapsed || isMobile) && (
              <div className="px-2 pt-4 pb-1.5 text-[10px] font-medium text-gray-600 uppercase tracking-[0.15em]">
                {section.label}
              </div>
            )}
            {collapsed && !isMobile && <div className="h-3" />}
            <div className="space-y-0.5">
              {section.items.map(item => {
                const active = isActive(item.path);
                const Icon = item.icon;
                return (
                  <button
                    key={item.path}
                    onClick={() => router.push(item.path)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-200 group ${
                      active
                        ? 'bg-white/[0.06] text-gray-100'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
                    } ${collapsed && !isMobile ? 'justify-center px-2' : ''}`}
                    title={collapsed && !isMobile ? item.label : undefined}
                  >
                    <Icon size={16} className={`shrink-0 ${active ? 'text-indigo-400' : 'group-hover:text-gray-400'}`} />
                    {(!collapsed || isMobile) && (
                      <span className="text-[12px] truncate">{item.label}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Status footer */}
      {(!collapsed || isMobile) && (
        <div className="px-4 py-3 border-t border-white/[0.04] shrink-0">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${daemonStatus?.running ? 'bg-emerald-400' : 'bg-gray-600'}`} />
            <span className="text-[10px] text-gray-600">
              {daemonStatus?.running ? 'System active' : 'Offline'}
            </span>
          </div>
          {daemonStatus?.circadian && (
            <div className="text-[10px] text-gray-700 mt-0.5 capitalize ml-3.5">
              {daemonStatus.circadian.current_phase} phase
            </div>
          )}
        </div>
      )}
    </>
  );

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: 'var(--janus-bg)' }}>
      {/* Desktop Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 68 : 260 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="hidden lg:flex flex-col border-r border-white/[0.04] relative shrink-0"
        style={{ background: 'rgba(10, 10, 15, 0.8)' }}
      >
        <NavContent />
        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute top-3 -right-3 w-6 h-6 rounded-full border border-white/[0.08] bg-[#111118] flex items-center justify-center text-gray-600 hover:text-gray-400 hover:border-white/[0.15] transition-all z-10"
        >
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </motion.aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-12 border-b border-white/[0.04] flex items-center justify-between px-4 z-30" style={{ background: 'rgba(10, 10, 15, 0.95)', backdropFilter: 'blur(12px)' }}>
        <button onClick={() => setMobileOpen(true)} className="p-1.5 rounded-lg hover:bg-white/[0.05] text-gray-400">
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <JanusOrbSmall />
          <span className="text-[12px] tracking-[0.2em] text-gradient">JANUS</span>
        </div>
        <div className="w-8" />
      </div>

      {/* Mobile Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed top-0 left-0 bottom-0 w-72 z-50 lg:hidden flex flex-col border-r border-white/[0.04]"
            style={{ background: 'var(--janus-bg)' }}
          >
            <div className="absolute top-3 right-3">
              <button onClick={() => setMobileOpen(false)} className="p-1 rounded-lg hover:bg-white/[0.05] text-gray-500">
                <X size={16} />
              </button>
            </div>
            <NavContent isMobile />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 overflow-hidden pt-12 lg:pt-0">
        {children}
      </main>
    </div>
  );
}
