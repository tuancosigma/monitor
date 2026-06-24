import type { WidgetSeriesPoint } from "@/lib/api";
import { EmptyChart } from "./timeseries-chart";

// 24-cell hour-of-day intensity strip. Opacity scales with event volume.
export function HeatmapStrip({ series }: { series: WidgetSeriesPoint[] }) {
  if (series.length === 0) {
    return <EmptyChart />;
  }
  const max = Math.max(...series.map((p) => p.value), 1);

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-12 gap-1">
        {series.map((p) => {
          const intensity = p.value / max;
          return (
            <div
              key={p.label}
              title={`${p.label}:00 — ${p.value} events`}
              className="flex h-8 items-center justify-center rounded text-[10px] text-slate-300"
              style={{ backgroundColor: `rgb(245 158 11 / ${0.08 + intensity * 0.82})` }}
            >
              {p.label}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-slate-500">
        events by hour of day · peak <span className="font-mono text-slate-300">{max}</span>
      </p>
    </div>
  );
}
