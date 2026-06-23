"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteConnector,
  fetchConnectors,
  updateConnector,
  type Connector,
} from "@/lib/api";
import { ConnectorForm } from "@/components/connector-form";

const STATUS_COLOR: Record<string, string> = {
  idle: "text-slate-400",
  running: "text-emerald-400",
  error: "text-red-400",
};

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setConnectors(await fetchConnectors());
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (c: Connector) => {
    await updateConnector(c.id, { is_active: !c.is_active });
    await load();
  };

  const remove = async (id: number) => {
    await deleteConnector(id);
    await load();
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-8">
      <header>
        <h1 className="text-2xl font-bold">Connectors</h1>
        <p className="text-slate-400">Pull from Wazuh / Prometheus, or receive webhooks</p>
      </header>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <ConnectorForm onCreated={() => void load()} />

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Last run</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map((c) => (
              <tr key={c.id} className="border-t border-slate-800">
                <td className="px-3 py-2 font-medium">{c.name}</td>
                <td className="px-3 py-2">{c.type}</td>
                <td className={`px-3 py-2 ${STATUS_COLOR[c.status] ?? ""}`}>
                  {c.status}
                  {c.last_error && (
                    <span className="ml-2 text-xs text-red-400">({c.last_error})</span>
                  )}
                </td>
                <td className="px-3 py-2 text-slate-400">
                  {c.last_run_at ? new Date(c.last_run_at).toLocaleString() : "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => void toggle(c)}
                      className="rounded bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700"
                    >
                      {c.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => void remove(c.id)}
                      className="rounded bg-red-600/10 px-2 py-1 text-xs text-red-400 hover:bg-red-600/20"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {connectors.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-center text-slate-500">
                  No connectors configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
