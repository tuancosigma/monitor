"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deletePlaybook,
  dryRunPlaybook,
  fetchPlaybooks,
  runPlaybook,
  type Playbook,
  type PlaybookRun,
} from "@/lib/api";
import { DagBuilder } from "@/components/dag-builder";

const RUN_COLOR: Record<string, string> = {
  success: "text-emerald-400",
  dry_run: "text-sky-400",
  blocked: "text-amber-400",
  failed: "text-red-400",
};

export default function PlaybooksPage() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [lastRun, setLastRun] = useState<PlaybookRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setPlaybooks(await fetchPlaybooks());
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (fn: () => Promise<PlaybookRun | void>) => {
    setError(null);
    try {
      const result = await fn();
      if (result) setLastRun(result);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "action failed");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-8">
      <header>
        <h1 className="text-2xl font-bold">Playbooks</h1>
        <p className="text-slate-400">Automate response: trigger → action DAGs (SOAR)</p>
      </header>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <DagBuilder onCreated={() => void load()} />

      <div className="space-y-3">
        {playbooks.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-4"
          >
            <div>
              <p className="font-medium">
                {p.name}{" "}
                <span className="text-xs text-slate-500">
                  ({p.trigger_type}, {p.nodes.length} nodes{p.auto_approve ? ", auto-approve" : ""})
                </span>
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => void act(() => dryRunPlaybook(p.id))}
                className="rounded bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
              >
                Dry-run
              </button>
              <button
                onClick={() => void act(() => runPlaybook(p.id, true))}
                className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium"
              >
                Run
              </button>
              <button
                onClick={() => void act(() => deletePlaybook(p.id))}
                className="rounded bg-red-600/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-600/20"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
        {playbooks.length === 0 && (
          <p className="text-center text-slate-500">No playbooks yet.</p>
        )}
      </div>

      {lastRun && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <p className="font-medium">
            Last run #{lastRun.id} —{" "}
            <span className={RUN_COLOR[lastRun.status] ?? ""}>{lastRun.status}</span>
            {lastRun.dry_run ? " (dry-run)" : ""}
          </p>
          <pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-300">
            {JSON.stringify(lastRun.node_results, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
