import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import DiffView from "../components/DiffView";
import RedlineView from "../components/RedlineView";
import ReExtractDiff from "../components/ReExtractDiff";
import RiskBadge, { Risk } from "../components/RiskBadge";
import RiskScoreGauge from "../components/RiskScoreGauge";
import Timeline, { TimelineEvent } from "../components/Timeline";
import { apiFetch } from "../utils/api";
import { getMatterFromIDB, queueOfflineRequest, saveMatterToIDB } from "../pwa/db";

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
type RiskScan = { risks?: Risk[]; combined_risks?: Risk[]; risk_score?: number; risk_score_combined?: number; risk_tier?: string; provenance_verified: false };
type Diff = { added?: string[]; removed?: string[]; changed?: { old: string; new: string; similarity: number }[] };

export default function MatterDetail() {
  const { matter_id = "" } = useParams();
  const [matter, setMatter] = useState<Matter | null>(null);
  const [matters, setMatters] = useState<Matter[]>([]);
  const [tab, setTab] = useState("Overview");
  const [riskScan, setRiskScan] = useState<RiskScan | null>(null);
  const [compareTarget, setCompareTarget] = useState("");
  const [diff, setDiff] = useState<Diff | null>(null);
  const [redlines, setRedlines] = useState<{ redlines: [] } | null>(null);
  const [reextract, setReextract] = useState(null);
  const [error, setError] = useState("");

  async function loadMatter() {
    try {
      const [current, all] = await Promise.all([apiFetch<Matter>(`/api/matters/${matter_id}`), apiFetch<Matter[]>("/api/matters")]);
      setMatter(current);
      await saveMatterToIDB(current);
      setMatters(all.filter((item) => item.id !== matter_id));
    } catch (err) {
      const cached = await getMatterFromIDB(matter_id);
      if (cached) {
        setMatter(cached as Matter);
      } else {
        setError(err instanceof Error ? err.message : "Unable to load matter");
      }
    }
  }

  useEffect(() => {
    loadMatter();
  }, [matter_id]);

  async function updateStatus(obligation: Obligation, status: string) {
    if (!obligation.obligation_id) return;
    if (!navigator.onLine) {
      await queueOfflineRequest({ url: `/api/obligations/${matter_id}/${obligation.obligation_id}/status`, method: "POST", body: { status } });
      setMatter((current) => current ? { ...current, obligations: current.obligations?.map((item) => item.obligation_id === obligation.obligation_id ? { ...item, status } : item) } : current);
      return;
    }
    await apiFetch(`/api/obligations/${matter_id}/${obligation.obligation_id}/status`, { method: "POST", body: JSON.stringify({ status }) });
    await loadMatter();
  }

  async function scanRisks() {
    setRiskScan(await apiFetch<RiskScan>(`/api/intelligence/matter/${matter_id}/analyze`, { method: "POST", body: JSON.stringify({ use_llm: true }) }));
  }

  async function compare() {
    if (!compareTarget) return;
    setDiff(await apiFetch<Diff>("/api/matters/compare", { method: "POST", body: JSON.stringify({ matter_id_a: matter_id, matter_id_b: compareTarget }) }));
  }

  if (error) return <main className="mx-auto max-w-4xl px-4 py-8 text-red-700">{error}</main>;
  if (!matter) return <main className="mx-auto max-w-4xl px-4 py-8 text-slate-600">Loading matter...</main>;

  async function generateRedlines() {
    setRedlines(await apiFetch<{ redlines: [] }>(`/api/intelligence/matter/${matter_id}/redline`, { method: "POST" }));
  }

  async function runReextract() {
    setReextract(await apiFetch(`/api/intelligence/matter/${matter_id}/reextract`, { method: "POST", body: JSON.stringify({ use_llm: false }) }));
  }

  const tabs = ["Overview", "Timeline", "Obligations", "Risks", "Compare", "Redline", "Re-extract", "Chat"];
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <a className="text-sm font-medium text-blue-700" href="/matters">Back to matters</a>
      <section className="mt-4 rounded border border-slate-200 bg-white p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950">{matter.case_no ?? matter.id}</h1>
            <p className="mt-1 text-sm text-slate-600">{matter.court ?? "Court not captured"}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/api/calendar/ics">Download ICS</a>
            <a className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white" href={`/api/matters/${matter.id}`}>Download extracted.json</a>
          </div>
        </div>
        <div className="mt-4 rounded border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          NOT VERIFIED - provenance_verified:false - Human review required
        </div>
      </section>

      <div className="mt-5 flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button key={item} onClick={() => setTab(item)} className={`rounded px-3 py-2 text-sm font-semibold ${tab === item ? "bg-blue-700 text-white" : "bg-white text-slate-700"}`}>{item}</button>
        ))}
      </div>

      <section className="mt-5">
        {tab === "Overview" ? (
          <div className="rounded border border-slate-200 bg-white p-5">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Plaintiff</dt><dd className="mt-1 text-sm text-slate-900">{matter.parties?.plaintiff ?? "Not captured"}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Defendant</dt><dd className="mt-1 text-sm text-slate-900">{matter.parties?.defendant ?? "Not captured"}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Next hearing</dt><dd className="mt-1 text-sm text-slate-900">{matter.next_hearing_date ?? "Not captured"}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-slate-500">Risk flags</dt><dd className="mt-1 text-sm text-slate-900">{matter.risk_flags?.join(", ") || "None"}</dd></div>
            </dl>
          </div>
        ) : null}
        {tab === "Timeline" ? <Timeline events={matter.timeline ?? []} /> : null}
        {tab === "Obligations" ? (
          <ul className="space-y-3">
            {(matter.obligations ?? []).map((obligation, index) => (
              <li key={`${obligation.due_date}-${index}`} className="flex flex-col gap-3 rounded border border-slate-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
                <div><p className="text-sm font-semibold text-slate-900">{obligation.due_date ?? "No date"}</p><p className="text-sm text-slate-600">{obligation.description ?? "No description"}</p></div>
                <select className="rounded border border-slate-300 px-3 py-2 text-sm" value={obligation.status ?? "pending"} onChange={(event) => updateStatus(obligation, event.target.value)} aria-label="Update obligation status">
                  <option value="pending">Pending</option><option value="done">Done</option><option value="dismissed">Dismissed</option>
                </select>
              </li>
            ))}
          </ul>
        ) : null}
        {tab === "Risks" ? (
          <div className="rounded border border-slate-200 bg-white p-5">
            <button onClick={scanRisks} className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white">Run risk scan</button>
            {riskScan ? <div className="mt-4"><RiskScoreGauge score={riskScan.risk_score_combined ?? riskScan.risk_score ?? 0} /></div> : null}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">{(riskScan?.combined_risks ?? riskScan?.risks ?? []).map((risk, index) => <RiskBadge key={`${risk.type}-${index}`} risk={risk} />)}</div>
          </div>
        ) : null}
        {tab === "Compare" ? (
          <div className="rounded border border-slate-200 bg-white p-5">
            <div className="flex gap-2">
              <select className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 text-sm" value={compareTarget} onChange={(event) => setCompareTarget(event.target.value)}>
                <option value="">Select matter</option>
                {matters.map((item) => <option key={item.id} value={item.id}>{item.case_no ?? item.id}</option>)}
              </select>
              <button onClick={compare} className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Compare</button>
            </div>
            <div className="mt-4"><DiffView diff={diff} /></div>
          </div>
        ) : null}
        {tab === "Redline" ? (
          <div className="rounded border border-slate-200 bg-white p-5">
            <button onClick={generateRedlines} className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white">Generate redlines</button>
            <div className="mt-4"><RedlineView redlines={redlines?.redlines ?? []} /></div>
          </div>
        ) : null}
        {tab === "Re-extract" ? (
          <div className="rounded border border-slate-200 bg-white p-5">
            <button onClick={runReextract} className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Run v2 extraction</button>
            <div className="mt-4"><ReExtractDiff result={reextract} /></div>
          </div>
        ) : null}
        {tab === "Chat" ? <ChatPanel matter_id={matter.id} /> : null}
      </section>
    </main>
  );
}
