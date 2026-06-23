"use client";

import { useState } from "react";
import { createConnector, type Connector } from "@/lib/api";

const TYPE_HINTS: Record<string, string> = {
  wazuh: '{"base_url":"https://wazuh:55000","username":"sentinel","password":"${WAZUH_KEY}"}',
  prometheus: '{"base_url":"http://prometheus:9090","queries":["up","node_load1"]}',
  webhook: '{"token":"${WEBHOOK_TOKEN}","mapping":{"@timestamp":"ts","message":"msg"}}',
};

// Create a connector. Config is entered as JSON; secrets should be ${ENV} references.
export function ConnectorForm({ onCreated }: { onCreated: (c: Connector) => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("wazuh");
  const [configText, setConfigText] = useState(TYPE_HINTS.wazuh ?? "{}");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const config = JSON.parse(configText) as Record<string, unknown>;
      const created = await createConnector({ name, type, config, is_active: true });
      onCreated(created);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="font-semibold">Add connector</h3>
      <div className="flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="name"
          className="filter-input flex-1"
        />
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setConfigText(TYPE_HINTS[e.target.value] ?? "{}");
          }}
          className="filter-input"
        >
          <option value="wazuh">wazuh</option>
          <option value="prometheus">prometheus</option>
          <option value="webhook">webhook</option>
        </select>
      </div>
      <textarea
        value={configText}
        onChange={(e) => setConfigText(e.target.value)}
        rows={3}
        className="filter-input w-full font-mono text-xs"
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button
        onClick={submit}
        disabled={busy || name.trim() === ""}
        className="rounded bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {busy ? "Creating…" : "Create"}
      </button>
    </div>
  );
}
