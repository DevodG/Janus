'use client';

import { useCallback, useEffect, useState } from 'react';
import { Brain, RefreshCw, Send, ShieldCheck, Database, Gauge, History } from 'lucide-react';

const V2 = process.env.NEXT_PUBLIC_JANUS_V2_URL || 'http://localhost:7860';

type Trace = {
  answer: string; confidence: number; method: string; attempts: number;
  plan?: string[]; progress_ledger?: string[];
};

export default function JanusV2Page() {
  const [question, setQuestion] = useState('');
  const [trace, setTrace] = useState<Trace | null>(null);
  const [scores, setScores] = useState<Record<string, { SCORE: number; passed: number; n: number }>>({});
  const [memory, setMemory] = useState<{ facts?: unknown[]; skills?: unknown[] }>({});
  const [correct, setCorrect] = useState('');
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    try {
      const [e, m] = await Promise.all([
        fetch(`${V2}/eval`).then((r) => r.json()),
        fetch(`${V2}/memory`).then((r) => r.json()),
      ]);
      setScores(e); setMemory(m); setOffline(false);
    } catch { setOffline(true); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function ask() {
    if (!question.trim()) return;
    setBusy(true);
    try {
      const t = await fetch(`${V2}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }).then((r) => r.json());
      setTrace(t); setOffline(false);
    } catch { setOffline(true); }
    setBusy(false);
  }

  async function submitCorrection() {
    if (!trace || !correct.trim()) return;
    await fetch(`${V2}/corrections`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, wrong: trace.answer, correct }),
    }).catch(() => setOffline(true));
    setCorrect('');
    load();
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Brain className="text-indigo-400" />
        <div>
          <h1 className="text-lg font-semibold">Janus V2 Kernel</h1>
          <p className="text-xs text-gray-500">General kernel · orchestrator-workers · evaluator gate · single-writer memory</p>
        </div>
        {offline && <span className="ml-auto rounded bg-amber-900/40 px-2 py-1 text-[11px] text-amber-300">API offline — start: uvicorn janus_v2.api:app --port 7860</span>}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Object.entries(scores).map(([k, v]) => (
          <div key={k} className="rounded-lg border border-white/10 p-3">
            <div className="flex items-center gap-1 text-[11px] uppercase text-gray-500"><Gauge size={12} /> {k.replace('eval_', '')}</div>
            <div className="mt-1 text-xl font-semibold">{(v.SCORE * 100).toFixed(0)}%</div>
            <div className="text-[11px] text-gray-500">{v.passed}/{v.n} first-attempt</div>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-white/10 p-4">
        <div className="flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()}
            placeholder="Ask anything — math, finance, science, code…"
            className="flex-1 rounded bg-white/5 px-3 py-2 text-sm outline-none" />
          <button onClick={ask} disabled={busy} className="flex items-center gap-1 rounded bg-indigo-600 px-3 py-2 text-sm disabled:opacity-50">
            {busy ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />} Ask
          </button>
        </div>
        {trace && (
          <div className="mt-4 space-y-2 text-sm">
            <p className="whitespace-pre-wrap">{trace.answer}</p>
            <p className="flex items-center gap-2 text-[11px] text-gray-500">
              <ShieldCheck size={12} /> method {trace.method} · confidence {trace.confidence.toFixed(2)} · attempts {trace.attempts}
            </p>
            {trace.plan && <p className="text-[11px] text-gray-600">plan: {trace.plan.join(' → ')}</p>}
            <div className="flex gap-2 pt-1">
              <input value={correct} onChange={(e) => setCorrect(e.target.value)}
                placeholder="Correct this answer (stored verbatim, retrieved first)"
                className="flex-1 rounded bg-white/5 px-3 py-1.5 text-xs outline-none" />
              <button onClick={submitCorrection} className="rounded bg-emerald-700 px-3 py-1.5 text-xs">Submit correction</button>
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-white/10 p-4">
          <div className="mb-2 flex items-center gap-1 text-xs uppercase text-gray-500"><Database size={12} /> Memory (single writer)</div>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-[11px] text-gray-400">
            {JSON.stringify({ facts: memory.facts ?? [], skills: memory.skills ?? [] }, null, 1)}
          </pre>
        </div>
        <div className="rounded-lg border border-white/10 p-4">
          <div className="mb-2 flex items-center gap-1 text-xs uppercase text-gray-500"><History size={12} /> Progress ledger</div>
          <ul className="space-y-1 text-[11px] text-gray-400">
            {(trace?.progress_ledger ?? ['Ask a question to see the ledger']).map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
}
