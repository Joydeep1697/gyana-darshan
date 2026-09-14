export type Risk = { type: string; severity: string; desc: string; matched_text?: string };

export default function RiskBadge({ risk }: { risk: Risk }) {
  const high = risk.severity === "high";
  return (
    <article className={`rounded border p-3 ${high ? "border-red-200 bg-red-50 text-red-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-white/70 px-2 py-1 text-xs font-bold uppercase">{risk.severity}</span>
        <h3 className="text-sm font-semibold">{risk.type}</h3>
      </div>
      <p className="mt-2 text-sm">{risk.desc}</p>
      {risk.matched_text ? <p className="mt-2 text-xs opacity-80">{risk.matched_text}</p> : null}
    </article>
  );
}
