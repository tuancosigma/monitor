"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchBenchmarks, runBenchmark, type BenchmarkRun } from "@/lib/api";

export default function BenchmarkPage() {
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRuns(await fetchBenchmarks());
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (scenario: string) => {
    setBusy(true);
    setError(null);
    try {
      await runBenchmark(scenario);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "benchmark failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Benchmarks</h1>
          <p className="text-slate-400">
            k6 ingest throughput (≥10k/s) &amp; query latency (p95 &lt;2s)
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => void run("ingest_throughput")}
            disabled={busy}
            className="rounded bg-sky-600 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
          >
            Run ingest
          </button>
          <button
            onClick={() => void run("query_latency")}
            disabled={busy}
            className="rounded bg-slate-700 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
          >
            Run query
          </button>
        </div>
      </header>

      {error && <p className="text-sm text-amber-400">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Scenario</th>
              <th className="px-3 py-2">Value</th>
              <th className="px-3 py-2">Target met</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-400">{new Date(r.ts).toLocaleString()}</td>
                <td className="px-3 py-2">{r.scenario}</td>
                <td className="px-3 py-2 font-mono">
                  {r.metric_value} {r.metric_unit}
                </td>
                <td className={`px-3 py-2 ${r.passed ? "text-emerald-400" : "text-red-400"}`}>
                  {r.passed ? "✓ pass" : "✗ miss"}
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-slate-500">
                  No benchmark runs yet. k6 runs against the live compose stack.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
