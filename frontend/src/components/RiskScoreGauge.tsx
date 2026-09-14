export default function RiskScoreGauge({ score }: { score: number }) {
  const safe = Math.max(0, Math.min(100, score || 0));
  const color = safe > 60 ? "#dc2626" : safe > 30 ? "#d97706" : "#16a34a";
  return (
    <div className="flex items-center gap-4">
      <div className="grid h-24 w-24 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${safe * 3.6}deg, #e2e8f0 0deg)` }}>
        <div className="grid h-16 w-16 place-items-center rounded-full bg-white text-lg font-bold text-slate-950">{safe}</div>
      </div>
      <span className="rounded px-3 py-1 text-sm font-semibold" style={{ backgroundColor: `${color}22`, color }}>{safe > 60 ? "High" : safe > 30 ? "Medium" : "Low"} risk</span>
    </div>
  );
}
