"use client";

import { useCallback, useMemo, useState } from "react";
import { fetchEvents, type EcsEvent, type EventFilters } from "@/lib/api";
import { useSse } from "@/lib/use-sse";
import { LogTable } from "@/components/log-table";
import { NlQueryBox } from "@/components/nl-query-box";
import { PageHeader } from "@/components/ui/page-header";

export default function ExplorePage() {
  const [filters, setFilters] = useState<EventFilters>({ limit: 100 });
  const [queried, setQueried] = useState<EcsEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [liveTail, setLiveTail] = useState(false);

  const liveEvents = useSse(liveTail);

  const runQuery = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEvents(filters);
      setQueried(res.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : "query failed");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const shown = useMemo(
    () => (liveTail ? liveEvents : queried),
    [liveTail, liveEvents, queried],
  );

  const update = (key: keyof EventFilters) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setFilters((prev) => ({ ...prev, [key]: value === "" ? undefined : value }));
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-8">
      <PageHeader
        title="Explore"
        description="Search and live-tail ingested events"
        actions={
          <button
            onClick={() => setLiveTail((v) => !v)}
            className={`rounded px-4 py-2 text-sm font-medium ${
              liveTail ? "bg-emerald-600" : "bg-slate-700"
            }`}
          >
            {liveTail ? "● Live" : "Live tail"}
          </button>
        }
      />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <input className="filter-input" placeholder="host.name" onChange={update("host_name")} />
        <input className="filter-input" placeholder="source.ip" onChange={update("source_ip")} />
        <input className="filter-input" placeholder="user.name" onChange={update("user_name")} />
        <input className="filter-input" placeholder="category" onChange={update("event_category")} />
        <input className="filter-input" placeholder="message contains" onChange={update("message")} />
        <button
          onClick={runQuery}
          disabled={loading || liveTail}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </section>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <NlQueryBox />

      <LogTable events={shown} />
    </main>
  );
}
