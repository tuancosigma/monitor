"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchWidgetData,
  type DashboardWidget,
  type EcsEvent,
  type WidgetData,
} from "@/lib/api";
import { LogTable } from "@/components/log-table";
import { TimeseriesChart } from "./timeseries-chart";
import { BarList } from "./bar-list";
import { HeatmapStrip } from "./heatmap-strip";

function renderBody(data: WidgetData) {
  switch (data.type) {
    case "timeseries":
      return <TimeseriesChart series={data.series ?? []} />;
    case "top_n":
      return <BarList series={data.series ?? []} />;
    case "heatmap":
      return <HeatmapStrip series={data.series ?? []} />;
    case "log_table":
      return <LogTable events={(data.events ?? []) as EcsEvent[]} />;
    default:
      return <p className="text-sm text-slate-500">Unknown widget type: {data.type}</p>;
  }
}

export function WidgetCard({
  widget,
  minutes,
  onRemove,
}: {
  widget: DashboardWidget;
  minutes: number;
  onRemove: (id: string) => void;
}) {
  const [data, setData] = useState<WidgetData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchWidgetData(widget.type, widget.query, minutes));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    } finally {
      setLoading(false);
    }
  }, [widget.type, widget.query, minutes]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="card card-interactive p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{widget.title}</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void load()}
            className="text-xs text-slate-400 hover:text-slate-200"
            title="Refresh"
          >
            ↻
          </button>
          <button
            onClick={() => onRemove(widget.id)}
            className="text-xs text-red-400 hover:text-red-300"
          >
            remove
          </button>
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {widget.type} · <span className="font-mono">{widget.query}</span>
      </p>
      <div className="mt-3">
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!loading && !error && data && renderBody(data)}
      </div>
    </div>
  );
}
