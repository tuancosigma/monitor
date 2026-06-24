import Link from "next/link";

export type StatTone = "ok" | "warn" | "bad" | "neutral";

const VALUE_TONE: Record<StatTone, string> = {
  ok: "text-emerald-400",
  warn: "text-amber-400",
  bad: "text-red-400",
  neutral: "text-accent-soft",
};

// Tone-colored accent wash in the top-right of the tile (subtle, no neon).
const GLOW_TONE: Record<StatTone, string> = {
  ok: "bg-emerald-500/10",
  warn: "bg-amber-500/10",
  bad: "bg-red-500/10",
  neutral: "bg-accent/10",
};

// A single KPI tile: label, large value, sub-line. Becomes a link when `href`
// is set (hover lift), otherwise a static card.
export function StatCard({
  label,
  value,
  sub,
  tone = "neutral",
  href,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: StatTone;
  href?: string;
}) {
  const body = (
    <>
      <div
        className={`pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full blur-2xl ${GLOW_TONE[tone]}`}
        aria-hidden
      />
      <p className="eyebrow">{label}</p>
      <p className={`tabular mt-2.5 text-4xl font-semibold tracking-tight ${VALUE_TONE[tone]}`}>
        {value}
      </p>
      {sub && <p className="mt-1.5 text-xs text-slate-500">{sub}</p>}
    </>
  );

  if (href) {
    return (
      <Link href={href} className="card card-interactive relative overflow-hidden p-5">
        {body}
      </Link>
    );
  }
  return <div className="card relative overflow-hidden p-5">{body}</div>;
}

// Loading placeholder matching StatCard dimensions.
export function StatCardSkeleton() {
  return <div className="h-28 animate-pulse rounded-card border border-slate-800/80 bg-slate-900/60" />;
}
