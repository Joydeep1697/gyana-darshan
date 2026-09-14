type Redline = { risk_type?: string; original_snippet: string; redline_suggestion: string; explanation?: string; severity?: string };

export default function RedlineView({ redlines }: { redlines: Redline[] }) {
  if (!redlines.length) return <p className="text-sm text-slate-500">No redlines generated yet.</p>;
  return (
    <div className="space-y-4">
      {redlines.map((item, index) => (
        <article key={`${item.risk_type}-${index}`} className="rounded border border-slate-200 bg-white p-4">
          <p className="text-xs font-bold uppercase text-slate-500">{item.severity} - {item.risk_type}</p>
          <p className="mt-3 rounded bg-red-50 p-3 text-sm text-red-900 line-through">{item.original_snippet}</p>
          <p className="mt-2 rounded bg-green-50 p-3 text-sm text-green-900">{item.redline_suggestion}</p>
          <p className="mt-2 text-sm text-slate-600">{item.explanation}</p>
          <button className="mt-3 rounded bg-slate-900 px-3 py-2 text-xs font-semibold text-white" onClick={() => navigator.clipboard.writeText(item.redline_suggestion)}>Copy</button>
        </article>
      ))}
    </div>
  );
}
