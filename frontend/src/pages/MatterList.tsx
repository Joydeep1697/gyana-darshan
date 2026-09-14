import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";

type Matter = {
  id: string;
  matter_id?: string;
  case_no?: string;
  parties?: { plaintiff?: string; defendant?: string };
  next_hearing_date?: string;
  risk_flags?: string[];
};

export default function MatterList() {
  const { user } = useAuth();
  const [matters, setMatters] = useState<Matter[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  async function loadMatters() {
    try {
      const data = await apiFetch<Matter[]>("/api/matters");
      setMatters(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load matters");
    }
  }

  async function search() {
    const data = await apiFetch<{ results: Matter[] }>(`/api/search?q=${encodeURIComponent(query)}`);
    setMatters((data.results ?? []).map((item) => ({ ...item, id: item.id ?? item.matter_id ?? "" })));
  }

  useEffect(() => {
    loadMatters();
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">Matter cockpit</h1>
          <p className="mt-1 text-sm text-slate-600">Tenant: {user?.tenant_id ?? "unknown"}</p>
        </div>
        <a className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/api/calendar/ics">Download ICS</a>
      </div>
      <div className="mb-4 flex gap-2">
        <input className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 text-sm" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search case number, parties, court..." />
        <button className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white" onClick={search}>Search</button>
      </div>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}
      <div className="overflow-hidden rounded border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr><th className="px-4 py-3">Case</th><th className="px-4 py-3">Plaintiff</th><th className="px-4 py-3">Next hearing</th><th className="px-4 py-3">Risk</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {matters.map((matter) => (
                <tr key={matter.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-blue-700"><a href={`/matters/${matter.id}`}>{matter.case_no ?? matter.id}</a></td>
                  <td className="px-4 py-3 text-slate-700">{matter.parties?.plaintiff ?? "Not captured"}</td>
                  <td className="px-4 py-3 text-slate-700">{matter.next_hearing_date ?? "Not captured"}</td>
                  <td className="px-4 py-3"><span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{matter.risk_flags?.length ? matter.risk_flags.join(", ") : "Unscanned"}</span></td>
                </tr>
              ))}
              {!matters.length ? <tr><td colSpan={4} className="px-4 py-10 text-center text-slate-500">No matters indexed yet.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
