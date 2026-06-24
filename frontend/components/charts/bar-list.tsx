import type { WidgetSeriesPoint } from "@/lib/api";
import { EmptyChart } from "./timeseries-chart";

// Horizontal top-N bars. Bar width is proportional to the largest value.
export function BarList({ series }: { series: WidgetSeriesPoint[] }) {
  if (series.length === 0) {
    return <EmptyChart />;
  }
  const max = Math.max(...series.map((p) => p.value), 1);

  return (
    <ul className="flex flex-col gap-1.5">
      {series.map((p) => (
        <li key={p.label} className="flex items-center gap-2 text-xs">
          <span className="w-32 truncate text-slate-400" title={p.label}>
            {p.label || "—"}
          </span>
          <div className="relative h-4 flex-1 overflow-hidden rounded bg-slate-950/80">
            <div
              className="h-full rounded bg-gradient-to-r from-accent to-accent-soft"
              style={{ width: `${(p.value / max) * 100}%` }}
            />
          </div>
          <span className="w-12 text-right font-mono text-slate-300">{p.value}</span>
        </li>
      ))}
    </ul>
  );
}
