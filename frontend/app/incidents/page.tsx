"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  fetchIncidents,
  fetchIncidentDetail,
  updateIncident,
  type IncidentResponse,
  type IncidentDetailResponse,
  type IncidentFilters,
} from "@/lib/api";
import { IncidentTimeline } from "@/components/incident-timeline";

function severityBadge(severity: string) {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    case "high":
      return "bg-orange-500/10 text-orange-400 border-orange-500/20";
    case "medium":
      return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
    case "low":
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    default:
      return "bg-slate-500/10 text-slate-400 border-slate-500/20";
  }
}

function statusBadge(status: string) {
  switch (status.toLowerCase()) {
    case "open":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "investigating":
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "resolved":
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    case "closed":
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<IncidentDetailResponse | null>(null);
  const [filters, setFilters] = useState<IncidentFilters>({ limit: 100 });

  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch incidents list
  const loadIncidents = useCallback(async () => {
    setListLoading(true);
    setError(null);
    try {
      const data = await fetchIncidents(filters);
      setIncidents(data);
      
      // If there's a selected ID but it's not in the list, or we just want to default to the first
      if (data.length > 0 && selectedId === null) {
        // Read URL query param first
        const params = new URLSearchParams(window.location.search);
        const urlId = params.get("id");
        if (urlId) {
          setSelectedId(Number(urlId));
        } else {
          setSelectedId(data[0]?.id ?? null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load incidents");
    } finally {
      setListLoading(false);
    }
  }, [filters, selectedId]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  // 2. Read query string changes
  useEffect(() => {
    const handleUrlCheck = () => {
      const params = new URLSearchParams(window.location.search);
      const urlId = params.get("id");
      if (urlId) {
        setSelectedId(Number(urlId));
      }
    };
    window.addEventListener("popstate", handleUrlCheck);
    return () => window.removeEventListener("popstate", handleUrlCheck);
  }, []);

  // 3. Fetch selected incident detail
  useEffect(() => {
    if (selectedId === null) {
      setDetail(null);
      return;
    }

    const loadDetail = async () => {
      setDetailLoading(true);
      try {
        const data = await fetchIncidentDetail(selectedId);
        setDetail(data);
      } catch (err) {
        console.error("Failed to load incident detail", err);
      } finally {
        setDetailLoading(false);
      }
    };

    loadDetail();
  }, [selectedId]);

  // 4. Update incident status
  const handleStatusUpdate = async (id: number, status: string) => {
    try {
      const updated = await updateIncident(id, { status });
      setIncidents((prev) => prev.map((inc) => (inc.id === id ? updated : inc)));
      if (detail && detail.id === id) {
        setDetail((prev) => prev ? { ...prev, status: updated.status } : null);
      }
    } catch (err) {
      alert("Failed to update status: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  // 5. Update incident assignee
  const handleAssignUpdate = async (id: number, assignee: string | null) => {
    try {
      const updated = await updateIncident(id, { assignee });
      setIncidents((prev) => prev.map((inc) => (inc.id === id ? updated : inc)));
      if (detail && detail.id === id) {
        setDetail((prev) => prev ? { ...prev, assignee: updated.assignee } : null);
      }
    } catch (err) {
      alert("Failed to update assignee: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const updateFilter = (key: keyof IncidentFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === "ALL" ? undefined : value,
    }));
    setSelectedId(null);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-8">
      {/* Header */}
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Link href="/" className="hover:text-slate-200">Home</Link>
          <span>/</span>
          <span className="text-slate-200">Incidents</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mt-1">Incidents Board</h1>
        <p className="text-slate-400">Investigate correlated security incidents and manage timeline actions.</p>
      </header>

      {/* Navigation Tabs */}
      <div className="flex gap-4 border-b border-slate-800 pb-3">
        <Link href="/alerts" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Alerts List
        </Link>
        <Link href="/incidents" className="text-sm font-semibold border-b-2 border-sky-500 pb-3 text-sky-400 px-1">
          Incidents Board
        </Link>
        <Link href="/explore" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Explore Logs
        </Link>
        <Link href="/channels" className="text-sm font-semibold text-slate-400 hover:text-slate-200 pb-3 px-1">
          Alerting Settings
        </Link>
      </div>

      {/* Split Pane Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Incidents List */}
        <section className="lg:col-span-4 flex flex-col gap-4">
          <div className="flex items-center justify-between bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <select
              className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs focus:border-sky-500 focus:outline-none"
              onChange={(e) => updateFilter("status", e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>

            <button
              onClick={loadIncidents}
              className="rounded bg-slate-800 border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
            >
              Refresh
            </button>
          </div>

          {listLoading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sky-500" />
            </div>
          ) : incidents.length === 0 ? (
            <div className="text-center py-10 border border-dashed border-slate-800 rounded-lg">
              <p className="text-sm text-slate-500">No incidents match filters.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2 max-h-[600px] overflow-y-auto pr-1">
              {incidents.map((inc) => {
                const isSelected = inc.id === selectedId;
                const dateStr = new Date(inc.last_seen).toLocaleTimeString();

                return (
                  <button
                    key={inc.id}
                    onClick={() => {
                      setSelectedId(inc.id);
                      // Update URL parameter without full page reload
                      window.history.pushState(null, "", `/incidents?id=${inc.id}`);
                    }}
                    className={`text-left p-4 rounded-xl border transition ${
                      isSelected
                        ? "bg-slate-900 border-sky-500/80 shadow-md ring-1 ring-sky-500/30"
                        : "bg-slate-900/30 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <span className="text-xs font-mono text-slate-500 font-bold">INC-{inc.id}</span>
                      <span className={`inline-block rounded border px-1.5 py-0.2 text-3xs font-semibold ${severityBadge(inc.severity)}`}>
                        {inc.severity.toUpperCase()}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-slate-100 mt-1 line-clamp-1">{inc.title}</h3>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">{inc.description}</p>

                    <div className="mt-3 flex justify-between items-center text-3xs text-slate-500 border-t border-slate-800/40 pt-2">
                      <span>Seen: {dateStr}</span>
                      <span className={`rounded-full px-2 py-0.1 border ${statusBadge(inc.status)}`}>
                        {inc.status}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        {/* Right Column: Incident Workbench */}
        <section className="lg:col-span-8 bg-slate-900/20 border border-slate-800 rounded-2xl p-6 min-h-[500px]">
          {detailLoading ? (
            <div className="flex justify-center items-center py-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
            </div>
          ) : !detail ? (
            <div className="flex flex-col items-center justify-center py-40 text-center text-slate-500">
              <svg className="h-10 w-10 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <h3 className="text-md font-semibold text-slate-400 mt-2">No Incident Selected</h3>
              <p className="text-xs text-slate-600 mt-1">Select an incident from the list to view its workbench.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {/* Workbench Header */}
              <div className="flex flex-col gap-3 border-b border-slate-800 pb-5">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-xs font-mono text-sky-400 font-bold bg-sky-950/40 px-2 py-0.5 rounded border border-sky-900/30">
                    INC-{detail.id}
                  </span>
                  
                  {/* Status & Assignee transition */}
                  <div className="flex items-center gap-3">
                    {/* Status Dropdown */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-2xs text-slate-500 uppercase font-semibold">Status:</span>
                      <select
                        value={detail.status}
                        onChange={(e) => handleStatusUpdate(detail.id, e.target.value)}
                        className="rounded border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs focus:border-sky-500 focus:outline-none"
                      >
                        <option value="open">Open</option>
                        <option value="investigating">Investigating</option>
                        <option value="resolved">Resolved</option>
                        <option value="closed">Closed</option>
                      </select>
                    </div>

                    {/* Assignee Dropdown */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-2xs text-slate-500 uppercase font-semibold">Owner:</span>
                      <select
                        value={detail.assignee ?? "UNASSIGNED"}
                        onChange={(e) => handleAssignUpdate(detail.id, e.target.value === "UNASSIGNED" ? null : e.target.value)}
                        className="rounded border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs focus:border-sky-500 focus:outline-none"
                      >
                        <option value="UNASSIGNED">Unassigned</option>
                        <option value="Alice">Alice</option>
                        <option value="Bob">Bob</option>
                        <option value="Charlie">Charlie</option>
                      </select>
                    </div>
                  </div>
                </div>

                <h2 className="text-xl font-bold text-white mt-1">{detail.title}</h2>
                <p className="text-slate-300 text-sm">{detail.description}</p>
              </div>

              {/* Grid: Incident Metadata */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-900/20 p-4 rounded-xl border border-slate-800/60">
                <div className="flex flex-col gap-1 text-xs">
                  <span className="text-slate-500 font-semibold uppercase tracking-wider text-3xs">Severity Rating</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={`inline-block rounded border px-2 py-0.5 font-semibold text-2xs ${severityBadge(detail.severity)}`}>
                      {detail.severity.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="flex flex-col gap-1 text-xs">
                  <span className="text-slate-500 font-semibold uppercase tracking-wider text-3xs">Sliding Time Window</span>
                  <div className="text-slate-300 mt-1 flex flex-col gap-0.5 font-mono text-2xs">
                    <span>First Seen: {new Date(detail.first_seen).toLocaleString()}</span>
                    <span>Last Seen: {new Date(detail.last_seen).toLocaleString()}</span>
                  </div>
                </div>

                {/* Consolidated Entities */}
                <div className="md:col-span-2 flex flex-col gap-1 text-xs border-t border-slate-800/40 pt-3">
                  <span className="text-slate-500 font-semibold uppercase tracking-wider text-3xs">Correlated Target Entities</span>
                  {detail.entities.length > 0 ? (
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {detail.entities.map((e, idx) => (
                        <span
                          key={idx}
                          className="inline-block rounded bg-slate-850 px-2 py-0.5 text-xs text-slate-200 border border-slate-700 font-mono"
                        >
                          <span className="text-slate-500 mr-1">{e.type}:</span>
                          {e.value}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-600 mt-1 text-xs italic">No entities extracted.</span>
                  )}
                </div>
              </div>

              {/* Section: Timeline & Associated Alerts */}
              <div className="flex flex-col gap-4 mt-2">
                <h3 className="text-md font-bold text-white border-b border-slate-800 pb-2">
                  Correlated Alerts Timeline
                </h3>
                <IncidentTimeline alerts={detail.alerts} />
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
