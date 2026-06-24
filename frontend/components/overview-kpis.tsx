"use client";

import { useEffect, useState } from "react";
import {
  fetchAlerts,
  fetchConnectors,
  fetchIncidents,
  fetchPosture,
} from "@/lib/api";
import { StatCard, StatCardSkeleton, type StatTone } from "@/components/ui/stat-card";

interface Kpi {
  label: string;
  value: string;
  sub: string;
  href: string;
  tone: StatTone;
}

const CAP = 100;
const cap = (n: number) => (n >= CAP ? `${CAP}+` : String(n));

function scoreTone(score: number): StatTone {
  if (score >= 80) return "ok";
  if (score >= 60) return "warn";
  return "bad";
}

async function loadKpis(): Promise<Kpi[]> {
  const [alerts, incidents, posture, connectors] = await Promise.all([
    fetchAlerts({ status: "open", limit: CAP }).catch(() => []),
    fetchIncidents({ limit: CAP }).catch(() => []),
    fetchPosture().catch(() => []),
    fetchConnectors().catch(() => []),
  ]);

  const activeIncidents = incidents.filter(
    (i) => i.status === "open" || i.status === "investigating",
  ).length;
  const latestPosture = posture[0];
  const activeConnectors = connectors.filter((c) => c.is_active).length;
  const erroredConnectors = connectors.filter((c) => c.status === "error").length;

  return [
    {
      label: "Open Alerts",
      value: cap(alerts.length),
      sub: alerts.length === 0 ? "all clear" : "needs triage",
      href: "/alerts",
      tone: alerts.length === 0 ? "ok" : "warn",
    },
    {
      label: "Active Incidents",
      value: cap(activeIncidents),
      sub: "open / investigating",
      href: "/incidents",
      tone: activeIncidents === 0 ? "ok" : "bad",
    },
    {
      label: "Posture Score",
      value: latestPosture ? `${Math.round(latestPosture.score)}` : "—",
      sub: latestPosture ? `${latestPosture.tool} · ${latestPosture.total_findings} findings` : "no scan yet",
      href: "/posture",
      tone: latestPosture ? scoreTone(latestPosture.score) : "neutral",
    },
    {
      label: "Connectors",
      value: `${activeConnectors}/${connectors.length}`,
      sub: erroredConnectors > 0 ? `${erroredConnectors} errored` : "active / total",
      href: "/connectors",
      tone: erroredConnectors > 0 ? "bad" : "neutral",
    },
  ];
}

export function OverviewKpis() {
  const [kpis, setKpis] = useState<Kpi[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    loadKpis()
      .then((k) => active && setKpis(k))
      .catch((e) => active && setError(e instanceof Error ? e.message : "load failed"));
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-red-400">Could not load overview: {error}</p>;
  }

  return (
    <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {(kpis ?? Array.from({ length: 4 }, () => null)).map((kpi, i) =>
        kpi ? (
          <StatCard
            key={kpi.label}
            label={kpi.label}
            value={kpi.value}
            sub={kpi.sub}
            tone={kpi.tone}
            href={kpi.href}
          />
        ) : (
          <StatCardSkeleton key={i} />
        ),
      )}
    </section>
  );
}
