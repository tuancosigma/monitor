"use client";

import { useState } from "react";
import type { AlertResponse } from "@/lib/api";

function severityBadgeColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "high":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "medium":
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "low":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

function severityDotColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500 ring-red-500/20";
    case "high":
      return "bg-orange-500 ring-orange-500/20";
    case "medium":
      return "bg-yellow-500 ring-yellow-500/20";
    case "low":
      return "bg-blue-500 ring-blue-500/20";
    default:
      return "bg-slate-500 ring-slate-500/20";
  }
}

export function IncidentTimeline({ alerts }: { alerts: AlertResponse[] }) {
  const [expandedAlert, setExpandedAlert] = useState<number | null>(null);

  if (alerts.length === 0) {
    return <p className="text-sm text-slate-500">No alerts associated with this incident.</p>;
  }

  return (
    <div className="flow-root">
      <ul role="list" className="-mb-8">
        {alerts.map((alert, alertIdx) => {
          const isExpanded = expandedAlert === alert.id;
          const formattedTime = new Date(alert.timestamp).toLocaleString();

          return (
            <li key={alert.id}>
              <div className="relative pb-8">
                {/* Timeline connector line */}
                {alertIdx !== alerts.length - 1 ? (
                  <span
                    className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-slate-800"
                    aria-hidden="true"
                  />
                ) : null}

                <div className="relative flex space-x-3">
                  {/* Timeline dot */}
                  <div>
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-full ring-8 ${severityDotColor(
                        alert.severity,
                      )}`}
                    >
                      <span className="h-2 w-2 rounded-full bg-slate-950" />
                    </span>
                  </div>

                  {/* Alert Content Card */}
                  <div className="flex-1 min-w-0 bg-slate-900/50 rounded-lg border border-slate-800 p-4 hover:border-slate-700 transition duration-150">
                    <div className="flex items-center justify-between">
                      <h4 className="text-md font-semibold text-slate-100">{alert.rule_name}</h4>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${severityBadgeColor(
                            alert.severity,
                          )}`}
                        >
                          {alert.severity}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">{formattedTime}</span>
                      </div>
                    </div>

                    {/* MITRE Mapping Tags */}
                    {alert.mitre_mapping.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {alert.mitre_mapping.map((m, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded bg-red-950/40 border border-red-900/30 px-2 py-0.5 text-xs font-medium text-red-300"
                            title={m.tactic}
                          >
                            <span className="font-bold">{m.technique_id}</span>
                            <span>({m.technique_name})</span>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Entities Details */}
                    {alert.entities.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        <span className="text-slate-400">Entities:</span>
                        {alert.entities.map((e, idx) => (
                          <span
                            key={idx}
                            className="inline-block rounded bg-slate-800 px-2 py-0.5 text-slate-300 border border-slate-700/50 font-mono"
                          >
                            <span className="text-slate-500 mr-1">{e.type}:</span>
                            {e.value}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Expand/Collapse samples button */}
                    <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3">
                      <span className="text-xs text-slate-400">
                        {alert.sample_events.length}{" "}
                        {alert.sample_events.length === 1 ? "forensic event" : "forensic events"}
                      </span>
                      <button
                        onClick={() => setExpandedAlert(isExpanded ? null : alert.id)}
                        className="text-xs font-semibold text-sky-400 hover:text-sky-300 focus:outline-none"
                      >
                        {isExpanded ? "Hide Forensic Data" : "Inspect Forensic Data"}
                      </button>
                    </div>

                    {/* Expandable samples block */}
                    {isExpanded && (
                      <div className="mt-3 overflow-x-auto rounded border border-slate-800 bg-slate-950 p-3 text-xs font-mono text-slate-300 max-h-96">
                        <pre className="whitespace-pre-wrap">
                          {JSON.stringify(alert.sample_events, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
