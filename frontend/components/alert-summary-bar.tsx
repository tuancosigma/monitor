import type { AlertResponse } from "@/lib/api";

// At-a-glance counts derived from the currently loaded alerts (no extra fetch).
const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;

const SEVERITY_TONE: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-yellow-400",
  low: "text-blue-400",
  info: "text-slate-400",
};

function countBy<T extends string>(items: { [k: string]: unknown }[], key: string): Record<T, number> {
  const out = {} as Record<T, number>;
  for (const item of items) {
    const v = String(item[key] ?? "").toLowerCase() as T;
    out[v] = (out[v] ?? 0) + 1;
  }
  return out;
}

export function AlertSummaryBar({ alerts }: { alerts: AlertResponse[] }) {
  if (alerts.length === 0) return null;
  const bySeverity = countBy(alerts as unknown as Record<string, unknown>[], "severity");
  const openCount = alerts.filter((a) => a.status === "open").length;

  return (
    <section className="flex flex-wrap items-center gap-3">
      <div className="card px-4 py-2">
        <span className="text-xs text-slate-400">Total</span>
        <span className="ml-2 font-bold text-slate-100">{alerts.length}</span>
      </div>
      <div className="card px-4 py-2">
        <span className="text-xs text-slate-400">Open</span>
        <span className={`ml-2 font-bold ${openCount > 0 ? "text-red-400" : "text-emerald-400"}`}>
          {openCount}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3 card px-4 py-2">
        {SEVERITY_ORDER.map((sev) => (
          <span key={sev} className="text-xs">
            <span className="text-slate-400">{sev}</span>
            <span className={`ml-1.5 font-bold ${SEVERITY_TONE[sev]}`}>{bySeverity[sev] ?? 0}</span>
          </span>
        ))}
      </div>
    </section>
  );
}
