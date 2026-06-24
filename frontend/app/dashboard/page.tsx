"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchDashboard,
  saveDashboard,
  type DashboardWidget,
} from "@/lib/api";
import { WidgetCard } from "@/components/charts/widget-card";
import { PageHeader } from "@/components/ui/page-header";

const WIDGET_TYPES = ["timeseries", "top_n", "heatmap", "log_table"];

// Common ECS-lite fields a top_n / heatmap widget groups on.
const FIELD_OPTIONS = [
  "event_category",
  "event_action",
  "host_name",
  "source_ip",
  "user_name",
  "event_outcome",
  "network_protocol",
  "log_level",
];

const WINDOWS: { label: string; minutes: number }[] = [
  { label: "Last 1h", minutes: 60 },
  { label: "Last 6h", minutes: 360 },
  { label: "Last 24h", minutes: 1440 },
  { label: "Last 7d", minutes: 10080 },
];

export default function DashboardPage() {
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("timeseries");
  const [query, setQuery] = useState("event_category");
  const [minutes, setMinutes] = useState(1440);
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
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-8">
      <PageHeader
        title="Dashboard"
        description="Configurable widget grid over live event data"
        actions={
          <>
            <select
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value))}
              className="filter-input"
              aria-label="time window"
            >
              {WINDOWS.map((w) => (
                <option key={w.minutes} value={w.minutes}>
                  {w.label}
                </option>
              ))}
            </select>
            <button onClick={() => void save()} className="btn-primary">
              Save layout
            </button>
          </>
        }
      />

      {status && <p className="text-sm text-sky-400">{status}</p>}

      <section className="card flex flex-wrap items-end gap-2 p-4">
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
        <select value={query} onChange={(e) => setQuery(e.target.value)} className="filter-input">
          {FIELD_OPTIONS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <button onClick={addWidget} className="btn-ghost">
          Add widget
        </button>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {widgets.map((w) => (
          <WidgetCard key={w.id} widget={w} minutes={minutes} onRemove={removeWidget} />
        ))}
        {widgets.length === 0 && (
          <p className="text-slate-500">No widgets. Add one above, then Save layout.</p>
        )}
      </section>
    </main>
  );
}
