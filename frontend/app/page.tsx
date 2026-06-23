import { fetchHealth, type HealthResponse } from "@/lib/api";

// Server component: fetches backend health on each request (Phase 0 smoke).
export const dynamic = "force-dynamic";

async function loadHealth(): Promise<HealthResponse | { error: string }> {
  try {
    return await fetchHealth();
  } catch (err) {
    return { error: err instanceof Error ? err.message : "unknown error" };
  }
}

export default async function HomePage() {
  const health = await loadHealth();
  const ok = "status" in health && health.status === "ok";

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-10">
      <header>
        <h1 className="text-3xl font-bold">Sentinel</h1>
        <p className="text-slate-400">Unified monitoring platform</p>
      </header>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-3">
          <span
            data-testid="health-badge"
            className={`inline-block h-3 w-3 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"
              }`}
          />
          <span className="font-medium">
            Backend: {"status" in health ? health.status : "unreachable"}
          </span>
        </div>

        {"dependencies" in health && (
          <ul className="mt-4 space-y-1 text-sm">
            {health.dependencies.map((d) => (
              <li key={d.name} className="flex justify-between">
                <span>{d.name}</span>
                <span className={d.healthy ? "text-emerald-400" : "text-red-400"}>
                  {d.healthy ? "healthy" : "down"} — {d.detail}
                </span>
              </li>
            ))}
          </ul>
        )}

        {"error" in health && (
          <p className="mt-4 text-sm text-red-400">{health.error}</p>
        )}
      </section>
    </main>
  );
}
