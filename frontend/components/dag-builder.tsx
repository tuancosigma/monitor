"use client";

import { useState } from "react";
import { createPlaybook, type Playbook } from "@/lib/api";

const TEMPLATE = JSON.stringify(
  {
    name: "critical-alert-response",
    trigger_type: "alert",
    trigger_filter: { severity: "critical" },
    nodes: [
      { id: "triage", action: "ai_triage", params: {} },
      { id: "notify", action: "notify", params: {} },
    ],
    edges: [["triage", "notify"]],
    auto_approve: false,
    is_active: true,
  },
  null,
  2,
);

// JSON-based playbook authoring: a DAG of {nodes, edges}. The backend validates the
// DAG (acyclic, known actions) on submit. Visual canvas can replace this later.
export function DagBuilder({ onCreated }: { onCreated: (p: Playbook) => void }) {
  const [text, setText] = useState(TEMPLATE);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = JSON.parse(text) as Omit<Playbook, "id">;
      onCreated(await createPlaybook(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="font-semibold">New playbook (JSON DAG)</h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        className="filter-input w-full font-mono text-xs"
        spellCheck={false}
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button
        onClick={submit}
        disabled={busy}
        className="rounded bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {busy ? "Creating…" : "Create playbook"}
      </button>
    </div>
  );
}
