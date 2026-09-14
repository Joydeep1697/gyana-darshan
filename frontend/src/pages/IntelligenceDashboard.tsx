import { useEffect, useState } from "react";
import { apiFetch } from "../utils/api";

type Trend = { date: string; avg_score: number; high_count: number };

export default function IntelligenceDashboard() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [summary, setSummary] = useState<{ total_matters: number; high_risk_count: number; medium_risk_count: number } | null>(null);

  useEffect(() => {
    apiFetch<{ trends: Trend[] }>("/api/intelligence/trends?days=30").then((data) => setTrends(data.trends ?? []));
    apiFetch<{ total_matters: number; high_risk_count: number; medium_risk_count: number }>("/api/risks/summary").then(setSummary);
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold text-slate-950">Intelligence dashboard</h1>
      <p className="mt-1 text-sm text-slate-600">AI-generated analysis requires lawyer review. provenance_verified:false</p>
      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded border border-slate-200 bg-white p-4"><p className="text-xs uppercase text-slate-500">Matters</p><p className="mt-2 text-2xl font-bold">{summary?.total_matters ?? 0}</p></div>
        <div className="rounded border border-red-200 bg-red-50 p-4"><p className="text-xs uppercase text-red-700">High risk</p><p className="mt-2 text-2xl font-bold">{summary?.high_risk_count ?? 0}</p></div>
        <div className="rounded border border-amber-200 bg-amber-50 p-4"><p className="text-xs uppercase text-amber-700">Medium risk</p><p className="mt-2 text-2xl font-bold">{summary?.medium_risk_count ?? 0}</p></div>
      </section>
      <section className="mt-6 rounded border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold">Risk trends</h2>
        <div className="mt-4 flex h-32 items-end gap-2">
          {trends.map((trend) => <div key={trend.date} title={trend.date} className="w-8 rounded-t bg-blue-600" style={{ height: `${Math.max(4, trend.avg_score)}%` }} />)}
        </div>
      </section>
    </main>
  );
}
