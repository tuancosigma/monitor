"use client";

import { useState } from "react";
import { generateSql, runApprovedSql, type SqlRunResult } from "@/lib/api";

// Natural-language -> SQL with a mandatory user-approval gate before execution.
// The AI only generates the SELECT; nothing runs until the user clicks "Run".
export function NlQueryBox() {
  const [question, setQuestion] = useState("");
  const [sql, setSql] = useState<string | null>(null);
  const [result, setResult] = useState<SqlRunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    setSql(null);
    try {
      const res = await generateSql(question);
      setSql(res.sql);
    } catch (err) {
      setError(err instanceof Error ? err.message : "generation failed");
    } finally {
      setBusy(false);
    }
  };

  const run = async () => {
    if (!sql) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await runApprovedSql(sql));
    } catch (err) {
      setError(err instanceof Error ? err.message : "query failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask in natural language, e.g. failed SSH logins in the last hour"
          className="filter-input flex-1"
        />
        <button
          onClick={ask}
          disabled={busy || question.trim() === ""}
          className="rounded bg-violet-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {busy ? "…" : "Ask AI"}
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}

      {sql && (
        <div className="mt-3 space-y-2">
          <p className="text-xs uppercase text-slate-500">Generated SQL — review before running</p>
          <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-sm text-emerald-300">
            {sql}
          </pre>
          <button
            onClick={run}
            disabled={busy}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Running…" : "Approve & run (read-only)"}
          </button>
        </div>
      )}

      {result && (
        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                {result.columns.map((c) => (
                  <th key={c} className="px-2 py-1">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, i) => (
                <tr key={i} className="border-t border-slate-800">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1">
                      {String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
