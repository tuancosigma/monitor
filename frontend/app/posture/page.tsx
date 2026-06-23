"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchPosture, runPosture, type PostureRun } from "@/lib/api";

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

export default function PosturePage() {
  const [runs, setRuns] = useState<PostureRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRuns(await fetchPosture());
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const scan = async (tool: string) => {
    setBusy(true);
    setError(null);
    try {
      await runPosture(tool);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "scan failed");
    } finally {
      setBusy(false);
    }
  };

  const latest = runs[0];

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Security Posture</h1>
          <p className="text-slate-400">CIS-style score from Trivy / Lynis, with drift</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => void scan("trivy")}
            disabled={busy}
            className="rounded bg-sky-600 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
          >
            Run Trivy
          </button>
          <button
            onClick={() => void scan("lynis")}
            disabled={busy}
            className="rounded bg-slate-700 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
          >
            Run Lynis
          </button>
        </div>
      </header>

      {error && <p className="text-sm text-amber-400">{error}</p>}

      {latest && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400 uppercase">Latest ({latest.tool})</p>
          <div className="mt-2 flex items-baseline gap-4">
            <span className={`text-5xl font-bold ${scoreColor(latest.score)}`}>
              {latest.score}
            </span>
            <span className="text-slate-400">/ 100</span>
            <span className={latest.drift >= 0 ? "text-emerald-400" : "text-red-400"}>
              {latest.drift >= 0 ? "▲" : "▼"} {Math.abs(latest.drift)} drift
            </span>
            <span className="text-slate-500">{latest.total_findings} findings</span>
          </div>
        </section>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Tool</th>
              <th className="px-3 py-2">Score</th>
              <th className="px-3 py-2">Drift</th>
              <th className="px-3 py-2">Findings</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-400">{new Date(r.ts).toLocaleString()}</td>
                <td className="px-3 py-2">{r.tool}</td>
                <td className={`px-3 py-2 font-mono ${scoreColor(r.score)}`}>{r.score}</td>
                <td className="px-3 py-2">{r.drift}</td>
                <td className="px-3 py-2">{r.total_findings}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-center text-slate-500">
                  No posture runs yet. Trivy/Lynis run inside the Linux container.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
