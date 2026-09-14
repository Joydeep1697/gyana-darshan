import { useEffect, useState } from "react";

type Matter = {
  id: string;
  case_no?: string;
  parties?: { plaintiff?: string; defendant?: string };
  next_hearing_date?: string;
  risk_flags?: string[];
};

const authHeaders = () => {
  const token = window.localStorage.getItem("nyaya_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function MatterList() {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/matters", { headers: authHeaders() })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`Matter load failed: ${res.status}`))))
      .then((data) => setMatters(Array.isArray(data) ? data : []))
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load matters"));
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">Matter cockpit</h1>
          <p className="mt-1 text-sm text-slate-600">Track extracted hearings, obligations, risks, and vault chat.</p>
        </div>
        <a className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/api/calendar/ics">
          Download ICS
        </a>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}

      <div className="overflow-hidden rounded border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Case</th>
                <th className="px-4 py-3">Plaintiff</th>
                <th className="px-4 py-3">Next hearing</th>
                <th className="px-4 py-3">Risk flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {matters.map((matter) => (
                <tr key={matter.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-blue-700">
                    <a href={`/matters/${matter.id}`}>{matter.case_no ?? matter.id}</a>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{matter.parties?.plaintiff ?? "Not captured"}</td>
                  <td className="px-4 py-3 text-slate-700">{matter.next_hearing_date ?? "Not captured"}</td>
                  <td className="px-4 py-3 text-slate-600">{matter.risk_flags?.length ? matter.risk_flags.join(", ") : "None"}</td>
                </tr>
              ))}
              {!matters.length ? (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-slate-500">
                    No matters indexed yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
