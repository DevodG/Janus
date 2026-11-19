'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Brain, Send, RefreshCw, Gauge, Database, Radio, Search, Zap,
  ShieldCheck, GitBranch, Activity, BookOpen, ChevronDown, ChevronUp,
} from 'lucide-react';

const V2 = process.env.NEXT_PUBLIC_JANUS_V2_URL || 'http://localhost:7860';

type Trace = {
  answer: string; confidence: number; method: string; attempts: number;
  plan?: string[]; progress_ledger?: string[]; branches?: unknown[];
  provenance?: { stages?: string[] };
};
type Scores = Record<string, { SCORE: number; passed: number; n: number }>;

const panel = 'rounded-2xl border border-white/8 bg-white/[0.03] backdrop-blur-md';
const label = 'text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400';

function Section({ icon: Icon, title, children, defaultOpen = true }: {
  icon: React.ElementType; title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`${panel} overflow-hidden`}>
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2.5 px-5 py-3.5 text-left transition hover:bg-white/[0.03]">
        <Icon size={15} className="text-indigo-300" />
        <span className="text-sm font-semibold text-slate-100">{title}</span>
        <span className="ml-auto text-slate-500">{open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</span>
      </button>
      {open && <div className="border-t border-white/6 px-5 py-4">{children}</div>}
    </section>
  );
}

export default function JanusV2Page() {
  const [q, setQ] = useState('');
  const [trace, setTrace] = useState<Trace | null>(null);
  const [scores, setScores] = useState<Scores>({});
  const [memory, setMemory] = useState<{ facts?: unknown[]; skills?: unknown[] }>({});
  const [loopData, setLoopData] = useState<{ enabled?: string[]; recent?: unknown[] }>({});
  const [live, setLive] = useState<{ live?: Record<string, unknown> }>({});
  const [correct, setCorrect] = useState('');
  const [newFact, setNewFact] = useState({ s: '', p: '', o: '' });
  const [stream, setStream] = useState('');
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const note = useCallback((m: string) => setLog((l) => [m, ...l].slice(0, 40)), []);

  const load = useCallback(async () => {
    try {
      const [e, m, l, lv] = await Promise.all([
        fetch(`${V2}/eval`).then((r) => r.json()),
        fetch(`${V2}/memory`).then((r) => r.json()),
        fetch(`${V2}/loop/status`).then((r) => r.json()),
        fetch(`${V2}/live`).then((r) => r.json()),
      ]);
      setScores(e); setMemory(m); setLoopData(l); setLive(lv); setOffline(false);
      note('↻ refreshed all panels');
    } catch { setOffline(true); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function ask() {
    if (!q.trim() || busy) return;
    setBusy(true); setTrace(null); setStream('');
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await fetch(`${V2}/run/stream`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }), signal: ctrl.signal,
      });
      const reader = res.body?.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value);
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const d = JSON.parse(line.slice(5));
          if (d.done) note(`✓ streamed done · ${d.method} · conf ${Number(d.confidence).toFixed(2)}`);
          else setStream((s) => s + d.token);
        }
      }
      const full = await fetch(`${V2}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      }).then((r) => r.json());
      setTrace(full); setOffline(false);
    } catch { if (!ctrl.signal.aborted) setOffline(true); }
    setBusy(false);
  }

  async function submitCorrection() {
    if (!trace || !correct.trim()) return;
    await fetch(`${V2}/corrections`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, wrong: trace.answer, correct }),
    }).then(() => { setCorrect(''); note('✓ correction stored verbatim — retrieved first from now'); load(); })
      .catch(() => setOffline(true));
  }

  async function addFact() {
    if (!newFact.s || !newFact.p || !newFact.o) return;
    await fetch(`${V2}/facts`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: newFact.s, predicate: newFact.p, object: newFact.o, source: 'console' }),
    }).then(() => { setNewFact({ s: '', p: '', o: '' }); note('✓ fact stored (temporal)'); load(); })
      .catch(() => setOffline(true));
  }

  const w = live.live?.weather as { temp_c?: number; humidity?: number; wind_kmh?: number } | undefined;

  return (
    <div className="min-h-screen bg-[#06060c] text-slate-200">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_-10%,rgba(99,102,241,0.14),transparent)]" />
      <div className="relative mx-auto max-w-6xl px-5 py-8">
        {/* Header */}
        <header className="flex flex-wrap items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/30 to-violet-500/20 ring-1 ring-indigo-400/30">
            <Brain size={22} className="text-indigo-200" />
          </div>
          <div>
            <h1 className="bg-gradient-to-r from-slate-50 via-indigo-200 to-violet-300 bg-clip-text text-2xl font-bold tracking-tight text-transparent">
              Janus
            </h1>
            <p className="text-xs text-slate-500">six stages · one workspace · self-improving behind evidence</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {offline
              ? <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-300 ring-1 ring-amber-400/30">API offline — uvicorn janus_v2.api:app --port 7860</span>
              : <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300 ring-1 ring-emerald-400/30">● live</span>}
            <button onClick={load} className="rounded-lg bg-white/5 px-3 py-1.5 text-xs ring-1 ring-white/10 transition hover:bg-white/10">
              <RefreshCw size={12} className="inline" /> refresh
            </button>
          </div>
        </header>

        {/* Score cards */}
        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
          {Object.entries(scores).map(([k, v]) => (
            <div key={k} className={`${panel} p-4`}>
              <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                <Gauge size={11} />{k.replace('eval', '').replace('_', ' ') || 'frozen'}
              </div>
              <div className="mt-1.5 text-2xl font-bold text-slate-50">{(v.SCORE * 100).toFixed(0)}%</div>
              <div className="text-[11px] text-slate-500">{v.passed}/{v.n} first-attempt</div>
            </div>
          ))}
        </div>

        <div className="mt-5 space-y-4">
          {/* Ask */}
          <Section icon={Send} title="Ask — streamed, tripped-guard, verified">
            <div className="flex gap-2.5">
              <input value={q} onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && ask()}
                placeholder="Ask anything — math, finance, science, worlds, live data…"
                className="flex-1 rounded-xl bg-black/40 px-4 py-3 text-sm text-slate-100 ring-1 ring-white/10 outline-none transition focus:ring-indigo-400/50" />
              <button onClick={ask} disabled={busy}
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50">
                {busy ? <RefreshCw size={15} className="animate-spin" /> : <Send size={15} />}
                {busy ? 'thinking' : 'ask'}
              </button>
            </div>
            {stream && <p className="mt-3 whitespace-pre-wrap rounded-xl bg-black/30 p-3 text-sm text-slate-300 ring-1 ring-white/6">{stream}<span className="animate-pulse text-indigo-300">▌</span></p>}
            {trace && (
              <div className="mt-4 space-y-3">
                <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-slate-100">{trace.answer}</p>
                <p className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                  <ShieldCheck size={12} className="text-emerald-300" />
                  method <b className="text-slate-300">{trace.method}</b> · confidence {Number(trace.confidence).toFixed(2)} · attempts {trace.attempts}
                  {trace.plan && <span className="text-slate-600">{trace.plan.join(' → ')}</span>}
                </p>
                {trace.branches && trace.branches.length > 0 && (
                  <p className="text-[11px] text-slate-600">branches tried: {(trace.branches as { method?: string }[]).map((b) => b.method).filter(Boolean).join(', ')}</p>
                )}
                <div className="flex gap-2 pt-1">
                  <input value={correct} onChange={(e) => setCorrect(e.target.value)}
                    placeholder="Correct this answer — stored verbatim, retrieved first"
                    className="flex-1 rounded-lg bg-black/40 px-3 py-2 text-xs ring-1 ring-white/10 outline-none focus:ring-emerald-400/50" />
                  <button onClick={submitCorrection} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-medium transition hover:bg-emerald-600">submit correction</button>
                </div>
              </div>
            )}
          </Section>

          {/* Live sensors */}
          <Section icon={Radio} title="Live sensor grid">
            <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-5">
              <div>🌡 weather<b className="block text-base text-slate-100">{w?.temp_c ?? '—'}°C</b><span className="text-[11px] text-slate-500">hum {w?.humidity ?? '—'}% · wind {w?.wind_kmh ?? '—'}</span></div>
              <div>🌫 air<b className="block text-base text-slate-100">{String((live.live?.air_quality as { us_aqi?: number } | undefined)?.us_aqi ?? '—')}</b><span className="text-[11px] text-slate-500">US AQI</span></div>
              <div>🌍 quakes<b className="block text-base text-slate-100">{String((live.live?.earthquakes as unknown[] | undefined)?.length ?? '—')}</b><span className="text-[11px] text-slate-500">M≥4.5 / day</span></div>
              <div>🛰 ISS<b className="block text-base text-slate-100">{(live.live?.iss as { lat?: number } | undefined)?.lat?.toFixed(1) ?? '—'}</b><span className="text-[11px] text-slate-500">latitude · live</span></div>
              <div>📰 news<b className="block text-base text-slate-100">{String((live.live?.headlines as unknown[] | undefined)?.length ?? '—')}</b><span className="text-[11px] text-slate-500">BBC headlines</span></div>
            </div>
          </Section>

          {/* Memory */}
          <Section icon={Database} title="Memory — single writer">
            <div className="mb-3 grid grid-cols-3 gap-2">
              {(['s', 'p', 'o'] as const).map((k) => (
                <input key={k} value={newFact[k]} onChange={(e) => setNewFact({ ...newFact, [k]: e.target.value })}
                  placeholder={{ s: 'subject', p: 'predicate', o: 'object' }[k]}
                  className="rounded-lg bg-black/40 px-3 py-2 text-xs ring-1 ring-white/10 outline-none focus:ring-indigo-400/50" />
              ))}
            </div>
            <button onClick={addFact} className="mb-4 rounded-lg bg-white/8 px-3 py-2 text-xs ring-1 ring-white/12 transition hover:bg-white/12">store fact (temporal)</button>
            <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-xl bg-black/30 p-3 text-[11px] leading-relaxed text-slate-400 ring-1 ring-white/6">
              {JSON.stringify({ facts: memory.facts ?? [], skills: memory.skills ?? [] }, null, 1)}
            </pre>
          </Section>

          {/* Loop + activity */}
          <div className="grid gap-4 md:grid-cols-2">
            <Section icon={GitBranch} title="Self-improvement loop">
              <p className="text-xs text-slate-400">enabled: {(loopData.enabled as string[] | undefined)?.join(', ') || '—'}</p>
              <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-[11px] text-slate-500">
                {((loopData.recent as { round?: number; candidate?: string; event?: string }[] | undefined) ?? []).map((r, i) => (
                  <li key={i}>r{r.round} · {r.candidate} · <b className={r.event === 'PROMOTED' ? 'text-emerald-300' : 'text-slate-400'}>{r.event}</b></li>
                ))}
              </ul>
            </Section>
            <Section icon={Activity} title="Activity">
              <ul className="max-h-48 space-y-1 overflow-auto text-[11px] text-slate-500">
                {log.map((m, i) => <li key={i}>{m}</li>)}
                {log.length === 0 && <li>idle — ask something</li>}
              </ul>
            </Section>
          </div>

          {/* Endpoints reference */}
          <Section icon={BookOpen} title="Endpoints (all wired above)" defaultOpen={false}>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] text-slate-500 md:grid-cols-3">
              {['GET /health', 'GET /model', 'POST /run', 'POST /run/stream', 'GET /live',
                'GET /memory', 'GET /corrections', 'POST /corrections', 'POST /facts',
                'GET /eval', 'GET /loop/status'].map((e) => <span key={e} className="font-mono">{e}</span>)}
            </div>
            <p className="mt-3 text-[11px] text-slate-600">
              Tools behind them: web_search · fetch_page · market_quote · browser_roam · crawl_feed ·
              deep_search · swarm · live_sensor · social_search · social_post (world ring) · code_exec · mcp_*
            </p>
          </Section>
        </div>

        <footer className="mt-8 pb-4 flex items-center gap-2 text-[11px] text-slate-600">
          <Zap size={11} />
          <Search size={11} className="hidden" />
          Janus — every change on evidence · receipts for every tool call
        </footer>
      </div>
    </div>
  );
}
