import type { EcsEvent } from "@/lib/api";

function severityColor(sev: number | undefined): string {
  const s = sev ?? 0;
  if (s >= 80) return "text-red-400";
  if (s >= 50) return "text-amber-400";
  if (s >= 20) return "text-sky-400";
  return "text-slate-400";
}

export function LogTable({ events }: { events: EcsEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No events.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-900 text-slate-400">
          <tr>
            <th className="px-3 py-2">Time</th>
            <th className="px-3 py-2">Sev</th>
            <th className="px-3 py-2">Host</th>
            <th className="px-3 py-2">Source IP</th>
            <th className="px-3 py-2">User</th>
            <th className="px-3 py-2">Action</th>
            <th className="px-3 py-2">Message</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr key={`${e["@timestamp"]}-${i}`} className="border-t border-slate-800">
              <td className="whitespace-nowrap px-3 py-2 text-slate-400">
                {e["@timestamp"]}
              </td>
              <td className={`px-3 py-2 font-mono ${severityColor(e.event_severity)}`}>
                {e.event_severity ?? 0}
              </td>
              <td className="px-3 py-2">{e.host_name || "—"}</td>
              <td className="px-3 py-2">{e.source_ip || "—"}</td>
              <td className="px-3 py-2">{e.user_name || "—"}</td>
              <td className="px-3 py-2">{e.event_action || "—"}</td>
              <td className="max-w-md truncate px-3 py-2 text-slate-300">
                {e.message || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
