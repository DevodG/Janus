"use client";

import { useEffect, useMemo, useState } from "react";
import axios from "axios";

type AgentOutput = {
  agent: string;
  summary: string;
  details: Record<string, unknown>;
  confidence: number;
};

type RunResponse = {
  case_id: string;
  user_input: string;
  outputs?: AgentOutput[];
  final_answer?: string;
  route?: Record<string, unknown>;
  research?: AgentOutput;
  planner?: AgentOutput;
  verifier?: AgentOutput;
  final?: AgentOutput;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [data, setData] = useState<RunResponse | null>(null);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await axios.get(`${API_BASE}/health`);
        setHealth("ok");
      } catch {
        setHealth("down");
      }
    };
    checkHealth();
  }, []);

  const normalizedOutputs = useMemo(() => {
    if (!data) return [];

    if (data.outputs?.length) return data.outputs;

    const arr: AgentOutput[] = [];
    if (data.research) arr.push(data.research);
    if (data.planner) arr.push(data.planner);
    if (data.verifier) arr.push(data.verifier);
    if (data.final) arr.push(data.final);
    return arr;
  }, [data]);

  const getAgent = (name: string) =>
    normalizedOutputs.find((item) => item.agent === name);

  const runOrg = async () => {
    if (!prompt.trim()) return;

    setLoading(true);
    setError("");
    setData(null);

    try {
      const endpoint = debugMode ? "/run/debug" : "/run";
      const res = await axios.post(`${API_BASE}${endpoint}`, {
        user_input: prompt,
      });
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-white px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">MiroOrg Basic</h1>
            <p className="mt-2 text-zinc-400">
              Your first AI organization dashboard
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm">
            <span className="mr-2 text-zinc-400">Backend:</span>
            {health === "checking" && <span className="text-yellow-300">Checking...</span>}
            {health === "ok" && <span className="text-green-400">Healthy</span>}
            {health === "down" && <span className="text-red-400">Unavailable</span>}
          </div>
        </header>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-xl">
          <label className="mb-2 block text-sm text-zinc-300">
            Give the organization a task
          </label>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask MiroOrg something..."
            className="min-h-[160px] w-full rounded-xl border border-zinc-700 bg-zinc-950 p-4 text-white outline-none"
          />

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={runOrg}
              disabled={loading}
              className="rounded-xl bg-white px-5 py-3 font-semibold text-black disabled:opacity-50"
            >
              {loading ? "Running..." : "Run Organization"}
            </button>

            <button
              onClick={() => {
                setPrompt("");
                setData(null);
                setError("");
              }}
              className="rounded-xl border border-zinc-700 px-5 py-3 text-white"
            >
              Clear
            </button>

            <label className="ml-0 flex items-center gap-2 text-sm text-zinc-300 md:ml-2">
              <input
                type="checkbox"
                checked={debugMode}
                onChange={(e) => setDebugMode(e.target.checked)}
                className="h-4 w-4"
              />
              Debug mode
            </label>
          </div>
        </section>

        {error && (
          <section className="mt-6 rounded-xl border border-red-500 bg-red-950/40 p-4 text-red-300">
            {error}
          </section>
        )}

        {data && (
          <section className="mt-8 space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <InfoCard title="Case ID" content={data.case_id} mono />
              <InfoCard title="User Input" content={data.user_input} />
            </div>

            {debugMode && data.route && (
              <InfoCard
                title="Route Decision"
                content={JSON.stringify(data.route, null, 2)}
                mono
              />
            )}

            <div className="grid gap-6 md:grid-cols-2">
              <AgentCard
                title="Research Agent"
                output={getAgent("research")}
              />
              <AgentCard
                title="Planner Agent"
                output={getAgent("planner")}
              />
              <AgentCard
                title="Verifier Agent"
                output={getAgent("verifier")}
              />
              <AgentCard
                title="Final Answer"
                output={getAgent("synthesizer") || getAgent("final")}
                fallbackText={data.final_answer}
              />
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function InfoCard({
  title,
  content,
  mono = false,
}: {
  title: string;
  content?: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 shadow-lg">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      <pre
        className={`whitespace-pre-wrap text-sm text-zinc-300 ${
          mono ? "font-mono" : "font-sans"
        }`}
      >
        {content || "No data"}
      </pre>
    </div>
  );
}

function AgentCard({
  title,
  output,
  fallbackText,
}: {
  title: string;
  output?: AgentOutput;
  fallbackText?: string;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 shadow-lg">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">{title}</h3>
        {typeof output?.confidence === "number" && (
          <span className="rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-300">
            confidence {output.confidence.toFixed(2)}
          </span>
        )}
      </div>

      <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-300">
        {output?.summary || fallbackText || "No output"}
      </pre>
    </div>
  );
}
