import { useEffect, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import Timeline, { TimelineEvent } from "../components/Timeline";

type Obligation = { obligation_id?: string; due_date?: string; description?: string; status?: string };
type Matter = {
  id: string;
  case_no?: string;
  court?: string;
  parties?: { plaintiff?: string; defendant?: string };
  next_hearing_date?: string;
  obligations?: Obligation[];
  risk_flags?: string[];
  timeline?: TimelineEvent[];
  provenance_verified: false;
};

const authHeaders = () => {
  const token = window.localStorage.getItem("nyaya_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

function matterIdFromPath() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  return parts[1] ?? "";
}

export default function MatterDetail() {
  const matterId = matterIdFromPath();
  const [matter, setMatter] = useState<Matter | null>(null);
  const [error, setError] = useState("");

  async function loadMatter() {
    try {
      const res = await fetch(`/api/matters/${matterId}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`Matter load failed: ${res.status}`);
      setMatter((await res.json()) as Matter);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load matter");
    }
  }

  useEffect(() => {
    loadMatter();
  }, [matterId]);

  async function updateStatus(obligation: Obligation, status: string) {
    if (!obligation.obligation_id) return;
    await fetch(`/api/obligations/${matterId}/${obligation.obligation_id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status }),
    });
    await loadMatter();
  }

  if (error) return <main className="mx-auto max-w-4xl px-4 py-8 text-red-700">{error}</main>;
  if (!matter) return <main className="mx-auto max-w-4xl px-4 py-8 text-slate-600">Loading matter...</main>;

  return (
    <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[1fr_380px]">
      <section className="space-y-6">
        <a className="text-sm font-medium text-blue-700" href="/matters">
          Back to matters
        </a>
        <div className="rounded border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          NOT VERIFIED - Human review required before legal reliance.
        </div>
        <section className="rounded border border-slate-200 bg-white p-5">
          <h1 className="text-2xl font-semibold text-slate-950">{matter.case_no ?? matter.id}</h1>
          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase text-slate-500">Court</dt>
              <dd className="mt-1 text-sm text-slate-900">{matter.court ?? "Not captured"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-slate-500">Next hearing</dt>
              <dd className="mt-1 text-sm text-slate-900">{matter.next_hearing_date ?? "Not captured"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-slate-500">Plaintiff</dt>
              <dd className="mt-1 text-sm text-slate-900">{matter.parties?.plaintiff ?? "Not captured"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-slate-500">Defendant</dt>
              <dd className="mt-1 text-sm text-slate-900">{matter.parties?.defendant ?? "Not captured"}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h2 className="mb-3 text-base font-semibold text-slate-950">Timeline</h2>
          <Timeline events={matter.timeline ?? []} />
        </section>

        <section className="rounded border border-slate-200 bg-white p-5">
          <h2 className="text-base font-semibold text-slate-950">Obligations</h2>
          <ul className="mt-4 space-y-3">
            {(matter.obligations ?? []).map((obligation, index) => (
              <li key={`${obligation.due_date}-${index}`} className="flex flex-col gap-3 rounded border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{obligation.due_date ?? "No date"}</p>
                  <p className="text-sm text-slate-600">{obligation.description ?? "No description"}</p>
                </div>
                <select
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                  value={obligation.status ?? "pending"}
                  onChange={(event) => updateStatus(obligation, event.target.value)}
                  aria-label="Update obligation status"
                >
                  <option value="pending">Pending</option>
                  <option value="done">Done</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </li>
            ))}
          </ul>
        </section>
      </section>
      <aside className="space-y-4">
        <a className="block rounded bg-blue-700 px-4 py-3 text-center text-sm font-semibold text-white" href="/api/calendar/ics">
          Download calendar ICS
        </a>
        <ChatPanel matter_id={matter.id} />
      </aside>
    </main>
  );
}
