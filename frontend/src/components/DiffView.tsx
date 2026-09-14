type Diff = { added?: string[]; removed?: string[]; changed?: { old: string; new: string; similarity: number }[] };

export default function DiffView({ diff }: { diff: Diff | null }) {
  if (!diff) return <p className="text-sm text-slate-500">Run a comparison to see changes.</p>;
  return (
    <div className="space-y-3">
      {(diff.added ?? []).map((item) => (
        <div key={`a-${item}`} className="added rounded bg-green-100 p-3 text-sm text-green-900">+ {item}</div>
      ))}
      {(diff.removed ?? []).map((item) => (
        <div key={`r-${item}`} className="removed rounded bg-red-100 p-3 text-sm text-red-900">- {item}</div>
      ))}
      {(diff.changed ?? []).map((item, index) => (
        <div key={`${item.old}-${index}`} className="rounded bg-yellow-100 p-3 text-sm text-yellow-950">
          <p>Old: {item.old}</p>
          <p className="mt-1">New: {item.new}</p>
          <p className="mt-1 text-xs">Similarity: {item.similarity}</p>
        </div>
      ))}
    </div>
  );
}
