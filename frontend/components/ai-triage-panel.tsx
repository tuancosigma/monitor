"use client";

import { useState } from "react";
import { triageAlert, type AlertTriage } from "@/lib/api";

const SEV_COLOR: Record<string, string> = {
  info: "text-slate-400",
  low: "text-sky-400",
  medium: "text-amber-400",
  high: "text-orange-400",
  critical: "text-red-400",
};

// "AI triage" action for a single alert. Calls the gateway-backed endpoint;
// shows "analyzing…" while the background routing/cache resolves.
export function AiTriagePanel({ alertId }: { alertId: number }) {
  const [triage, setTriage] = useState<AlertTriage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setTriage(await triageAlert(alertId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "triage failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">AI Triage</h3>
        <button
          onClick={run}
          disabled={loading}
          className="rounded bg-violet-600 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Analyzing…" : "AI triage"}
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}

      {triage && (
        <div className="mt-3 space-y-2 text-sm">
          <p>{triage.summary}</p>
          <p>
            Severity:{" "}
            <span className={SEV_COLOR[triage.severity_assessment] ?? ""}>
              {triage.severity_assessment}
            </span>{" "}
            · FP likelihood: {(triage.false_positive_likelihood * 100).toFixed(0)}% · confidence:{" "}
            {(triage.confidence * 100).toFixed(0)}%
          </p>
          {triage.likely_root_cause && (
            <p className="text-slate-400">Root cause: {triage.likely_root_cause}</p>
          )}
          {triage.remediation_steps.length > 0 && (
            <div>
              <p className="font-medium">Remediation</p>
              <ol className="list-decimal pl-5 text-slate-300">
                {triage.remediation_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
          {triage.recommended_actions && triage.recommended_actions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {triage.recommended_actions.map((a) => (
                <span key={a} className="rounded bg-slate-800 px-2 py-0.5 text-xs">
                  {a}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
