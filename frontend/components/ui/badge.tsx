import { type ReactNode } from "react";

// Centralized badge tones so severity/status colors stay consistent everywhere.
type Tone =
  | "neutral"
  | "accent"
  | "ok"
  | "warn"
  | "danger"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "info";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  accent: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  ok: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  warn: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  danger: "bg-red-500/10 text-red-400 border-red-500/20",
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  info: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

// Map an arbitrary severity string to a tone (falls back to neutral).
const SEVERITIES: readonly string[] = ["critical", "high", "medium", "low", "info"];
export function severityTone(severity: string): Tone {
  const s = severity.toLowerCase();
  return SEVERITIES.includes(s) ? (s as Tone) : "neutral";
}

// Map an alert/incident status string to a tone.
export function statusTone(status: string): Tone {
  switch (status.toLowerCase()) {
    case "open":
      return "danger";
    case "acknowledged":
    case "investigating":
      return "accent";
    case "resolved":
    case "closed":
      return "ok";
    default:
      return "neutral";
  }
}

export function Badge({
  tone = "neutral",
  size = "2xs",
  pill = false,
  children,
  className = "",
}: {
  tone?: Tone;
  size?: "2xs" | "xs";
  pill?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const sizeClass = size === "xs" ? "px-2 py-0.5 text-xs" : "px-1.5 py-0.5 text-2xs";
  const shape = pill ? "rounded-full" : "rounded";
  return (
    <span
      className={`inline-block border font-semibold ${shape} ${sizeClass} ${TONE_CLASS[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
