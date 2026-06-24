"use client";

import { Fragment, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { fetchAlerts, updateAlert, type AlertResponse, type AlertFilters } from "@/lib/api";
import { AiTriagePanel } from "@/components/ai-triage-panel";
import { AlertSummaryBar } from "@/components/alert-summary-bar";
import { Badge, severityTone, statusTone } from "@/components/ui/badge";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [filters, setFilters] = useState<AlertFilters>({ limit: 100 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triageId, setTriageId] = useState<number | null>(null);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAlerts(filters);
      setAlerts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleStatusUpdate = async (id: number, newStatus: string) => {
    try {
      const updated = await updateAlert(id, { status: newStatus });
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch (err) {
      alert("Failed to update status: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleAssign = async (id: number, assignee: string | null) => {
    try {
      const updated = await updateAlert(id, { assignee });
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch (err) {
      alert("Failed to assign alert: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const updateFilter = (key: keyof AlertFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === "ALL" ? undefined : value,
    }));
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-8">
      {/* Header */}
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Link href="/" className="hover:text-slate-200">Home</Link>
          <span>/</span>
          <span className="text-slate-200">Alerts</span>
        </div>
        <h1 className="h-display text-3xl font-semibold tracking-tight text-white mt-1">SIEM Alerts</h1>
        <p className="text-slate-400">Manage, inspect, and transition security detection alerts.</p>
      </header>

      {/* Navigation Tabs */}
      <div className="flex gap-4 border-b border-slate-800 pb-3">
        <Link href="/alerts" className="text-sm font-semibold border-b-2 border-accent pb-3 text-accent-soft px-1">
          Alerts List
        </Link>
        <Link href="/incidents" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Incidents Board
        </Link>
        <Link href="/explore" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Explore Logs
        </Link>
        <Link href="/channels" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Alerting Settings
        </Link>
      </div>

      {/* Filter controls */}
      <section className="flex flex-wrap items-center gap-3 bg-slate-900/40 p-4 rounded-xl border border-slate-800">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</label>
          <select
            className="rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
            onChange={(e) => updateFilter("status", e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Severity</label>
          <select
            className="rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
            onChange={(e) => updateFilter("severity", e.target.value)}
          >
            <option value="ALL">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>

        <button
          onClick={loadAlerts}
          className="ml-auto mt-auto self-end btn-primary"
        >
          Refresh
        </button>
      </section>

      {/* At-a-glance summary derived from loaded alerts */}
      {!loading && !error && <AlertSummaryBar alerts={alerts} />}

      {/* Content Table / Loading / Error */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          {error}
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16 rounded-xl border border-dashed border-slate-800 bg-slate-900/10">
          <p className="text-slate-400 text-sm">No alerts match the active filters.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/10">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Time</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Rule / Severity</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Entities</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">MITRE ATT&CK</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs">Status / Owner</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-xs text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {alerts.map((alert) => (
                <Fragment key={alert.id}>
                <tr className="hover:bg-slate-900/25 transition">
                  {/* Time */}
                  <td className="whitespace-nowrap px-4 py-4 text-slate-400 font-mono text-xs">
                    {new Date(alert.timestamp).toLocaleString()}
                  </td>

                  {/* Rule & Severity */}
                  <td className="px-4 py-4">
                    <div className="font-semibold text-slate-200">{alert.rule_name}</div>
                    <div className="mt-1 flex items-center gap-1.5">
                      <Badge tone={severityTone(alert.severity)}>
                        {alert.severity.toUpperCase()}
                      </Badge>
                      <span className="text-slate-500 text-2xs font-mono">ID: {alert.rule_id.split("-")[0]}</span>
                    </div>
                  </td>

                  {/* Entities */}
                  <td className="px-4 py-4">
                    {alert.entities.length > 0 ? (
                      <div className="flex flex-wrap gap-1 max-w-[220px]">
                        {alert.entities.map((ent, idx) => (
                          <span
                            key={idx}
                            className="inline-block rounded bg-slate-800 px-1.5 py-0.5 text-2xs text-slate-300 font-mono border border-slate-700/50"
                            title={`${ent.type}: ${ent.value}`}
                          >
                            <span className="text-slate-500">{ent.type.substring(0, 3)}:</span>
                            {ent.value}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>

                  {/* MITRE ATT&CK Mapping */}
                  <td className="px-4 py-4">
                    {alert.mitre_mapping.length > 0 ? (
                      <div className="flex flex-wrap gap-1 max-w-[200px]">
                        {alert.mitre_mapping.map((mitre, idx) => (
                          <span
                            key={idx}
                            className="inline-flex rounded bg-red-950/40 border border-red-900/30 px-1.5 py-0.5 text-2xs text-red-300 font-medium"
                            title={mitre.tactic}
                          >
                            {mitre.technique_id}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>

                  {/* Status & Assignee */}
                  <td className="px-4 py-4">
                    <Badge tone={statusTone(alert.status)} size="xs" pill>
                      {alert.status}
                    </Badge>
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <span className="text-slate-400 text-xs">Assignee:</span>
                      <select
                        className="rounded border border-slate-800 bg-slate-950 px-1.5 py-0.5 text-xs focus:border-accent focus:outline-none"
                        value={alert.assignee ?? "UNASSIGNED"}
                        onChange={(e) => handleAssign(alert.id, e.target.value === "UNASSIGNED" ? null : e.target.value)}
                      >
                        <option value="UNASSIGNED">Unassigned</option>
                        <option value="Alice">Alice</option>
                        <option value="Bob">Bob</option>
                        <option value="Charlie">Charlie</option>
                      </select>
                    </div>
                  </td>

                  {/* Action controls */}
                  <td className="whitespace-nowrap px-4 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setTriageId((id) => (id === alert.id ? null : alert.id))}
                        className="rounded bg-violet-600/10 border border-violet-500/20 px-2 py-1 text-xs font-semibold text-violet-300 hover:bg-violet-600/20 transition"
                      >
                        {triageId === alert.id ? "Hide AI" : "AI triage"}
                      </button>
                      {alert.status === "open" && (
                        <button
                          onClick={() => handleStatusUpdate(alert.id, "acknowledged")}
                          className="rounded bg-sky-600/10 border border-sky-500/20 px-2 py-1 text-xs font-semibold text-sky-400 hover:bg-sky-600/20 active:bg-sky-600/30 transition"
                        >
                          Acknowledge
                        </button>
                      )}
                      {(alert.status === "open" || alert.status === "acknowledged") && (
                        <button
                          onClick={() => handleStatusUpdate(alert.id, "resolved")}
                          className="rounded bg-emerald-600/10 border border-emerald-500/20 px-2 py-1 text-xs font-semibold text-emerald-400 hover:bg-emerald-600/20 active:bg-emerald-600/30 transition"
                        >
                          Resolve
                        </button>
                      )}
                      {alert.incident_id ? (
                        <Link
                          href={`/incidents?id=${alert.incident_id}`}
                          className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                        >
                          View Incident #{alert.incident_id}
                        </Link>
                      ) : (
                        <span className="text-2xs text-slate-600 italic">No incident correlated</span>
                      )}
                    </div>
                  </td>
                </tr>
                {triageId === alert.id && (
                  <tr>
                    <td colSpan={6} className="bg-slate-950/50 px-4 py-3">
                      <AiTriagePanel alertId={alert.id} />
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
