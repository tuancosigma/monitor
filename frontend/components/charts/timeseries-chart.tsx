import type { WidgetSeriesPoint } from "@/lib/api";

// Lightweight SVG area+line chart. No chart lib — KISS, zero deps.
const VIEW_W = 600;
const VIEW_H = 160;
const PAD = 4;

export function TimeseriesChart({ series }: { series: WidgetSeriesPoint[] }) {
  if (series.length === 0) {
    return <EmptyChart />;
  }

  const max = Math.max(...series.map((p) => p.value), 1);
  const stepX = series.length > 1 ? (VIEW_W - PAD * 2) / (series.length - 1) : 0;
  const y = (v: number) => VIEW_H - PAD - (v / max) * (VIEW_H - PAD * 2);
  const x = (i: number) => PAD + i * stepX;

  const line = series.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");
  const area = `${PAD},${VIEW_H - PAD} ${line} ${x(series.length - 1)},${VIEW_H - PAD}`;
  // Non-empty guaranteed by the early return above.
  const last = series[series.length - 1] as WidgetSeriesPoint;

  return (
    <div className="flex h-full flex-col">
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        preserveAspectRatio="none"
        className="h-32 w-full"
        role="img"
        aria-label="event volume over time"
      >
        <defs>
          <linearGradient id="ts-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(245 158 11)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="rgb(245 158 11)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={area} fill="url(#ts-fill)" />
        <polyline
          points={line}
          fill="none"
          stroke="rgb(245 158 11)"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <p className="mt-1 text-xs text-slate-500">
        peak <span className="font-mono text-slate-300">{max}</span> · latest{" "}
        <span className="font-mono text-slate-300">{last.value}</span> · {series.length} buckets
      </p>
    </div>
  );
}

export function EmptyChart() {
  return (
    <div className="flex h-32 items-center justify-center rounded bg-slate-950 text-sm text-slate-600">
      No data in window
    </div>
  );
}
