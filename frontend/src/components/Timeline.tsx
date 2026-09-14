export type TimelineEvent = {
  date: string;
  type?: string;
  event_type?: string;
  title: string;
  description?: string;
  provenance_verified?: boolean;
};

function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date));

  if (!sorted.length) {
    return <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">No dated events extracted yet.</p>;
  }

  return (
    <ol className="space-y-3">
      {sorted.map((event, index) => {
        const kind = event.type ?? event.event_type ?? "obligation";
        const dotClass = kind === "hearing" ? "bg-blue-600" : "bg-amber-500";
        return (
          <li key={`${event.date}-${event.title}-${index}`} className="flex gap-3 rounded border border-slate-200 bg-white p-4">
            <span aria-hidden="true" className={`mt-1 h-3 w-3 shrink-0 rounded-full ${dotClass}`} />
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatDate(event.date)}</p>
              <h3 className="mt-1 text-sm font-semibold text-slate-950">{event.title}</h3>
              {event.description ? <p className="mt-1 text-sm text-slate-600">{event.description}</p> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
