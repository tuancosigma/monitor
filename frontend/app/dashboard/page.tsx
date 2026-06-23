"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchDashboard,
  saveDashboard,
  type DashboardWidget,
} from "@/lib/api";

const WIDGET_TYPES = ["timeseries", "top_n", "heatmap", "log_table"];

export default function DashboardPage() {
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("timeseries");
  const [query, setQuery] = useState("event_category");
  const [status, setStatus] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const layout = await fetchDashboard();
      setWidgets(layout.widgets);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const addWidget = () => {
    if (title.trim() === "") return;
    setWidgets((prev) => [
      ...prev,
      { id: `w-${Date.now()}`, type, title, query },
    ]);
    setTitle("");
  };

  const removeWidget = (id: string) => {
    setWidgets((prev) => prev.filter((w) => w.id !== id));
  };

  const save = async () => {
    setStatus(null);
    try {
      await saveDashboard({ owner: "default", widgets });
      setStatus("Saved layout.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "save failed");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-slate-400">Configurable widget grid (saved as layout JSON)</p>
        </div>
        <button
          onClick={() => void save()}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium"
        >
          Save layout
        </button>
      </header>

      {status && <p className="text-sm text-sky-400">{status}</p>}

      <section className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Widget title"
          className="filter-input"
        />
        <select value={type} onChange={(e) => setType(e.target.value)} className="filter-input">
          {WIDGET_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="query / field"
          className="filter-input"
        />
        <button onClick={addWidget} className="rounded bg-sky-600 px-4 py-2 text-sm font-medium">
          Add widget
        </button>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {widgets.map((w) => (
          <div key={w.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{w.title}</h3>
              <button
                onClick={() => removeWidget(w.id)}
                className="text-xs text-red-400 hover:text-red-300"
              >
                remove
              </button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {w.type} · <span className="font-mono">{w.query}</span>
            </p>
            <div className="mt-3 flex h-24 items-center justify-center rounded bg-slate-950 text-slate-600">
              {w.type} preview
            </div>
          </div>
        ))}
        {widgets.length === 0 && (
          <p className="text-slate-500">No widgets. Add one above, then Save layout.</p>
        )}
      </section>
    </main>
  );
}
