type ReExtractResult = { diff?: { added?: string[]; removed?: string[]; changed?: { old: string; new: string }[] } };

export default function ReExtractDiff({ result }: { result: ReExtractResult | null }) {
  if (!result) return <p className="text-sm text-slate-500">Run re-extraction to compare v1 and v2 obligations.</p>;
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-950">Extraction diff for human review</h3>
      <pre className="mt-3 max-h-80 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-50">{JSON.stringify(result.diff ?? result, null, 2)}</pre>
      <div className="mt-3 flex gap-2">
        <button className="rounded bg-blue-700 px-3 py-2 text-xs font-semibold text-white">Accept for review</button>
        <button className="rounded bg-slate-200 px-3 py-2 text-xs font-semibold text-slate-800">Reject</button>
      </div>
    </div>
  );
}
