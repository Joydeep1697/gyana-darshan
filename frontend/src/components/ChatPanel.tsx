import { FormEvent, useEffect, useState } from "react";

type Citation = { matter_id: string; case_no?: string; field: string };
type ChatEntry = { query: string; response?: ChatResponse; created_at?: string };
type ChatResponse = {
  answer: string;
  citations: Citation[];
  provenance_verified: false;
  retrieved_count: number;
  llm_placeholder: boolean;
};

const authHeaders = () => {
  const token = window.localStorage.getItem("nyaya_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function ChatPanel({ matter_id }: { matter_id?: string }) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<ChatResponse | null>(null);
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!matter_id) return;
    fetch(`/api/chat/history/${matter_id}`, { headers: authHeaders() })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Unable to load chat history"))))
      .then((data) => setHistory(data.history ?? []))
      .catch(() => setHistory([]));
  }, [matter_id]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError("");
    try {
      const path = matter_id ? `/api/chat/matter/${matter_id}` : "/api/chat";
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ query: trimmed, matter_id }),
      });
      if (!res.ok) throw new Error(`Chat failed with ${res.status}`);
      const data = (await res.json()) as ChatResponse;
      setAnswer(data);
      setHistory((current) => [{ query: trimmed, response: data }, ...current]);
      setQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Vault chat</h2>
          <p className="mt-1 text-sm text-slate-600">Answers are grounded only in extracted matter facts.</p>
        </div>
        <span className="rounded bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">NOT VERIFIED</span>
      </div>

      <form onSubmit={submit} className="mt-4 flex gap-2">
        <input
          className="min-w-0 flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask about hearings, obligations, parties..."
          aria-label="Ask vault chat"
        />
        <button className="rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={loading}>
          {loading ? "Asking" : "Ask"}
        </button>
      </form>

      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      {answer ? (
        <article className="mt-4 rounded border border-slate-200 bg-slate-50 p-4">
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{answer.answer}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {answer.citations.map((citation) => (
              <span key={`${citation.matter_id}-${citation.field}`} className="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800">
                {citation.case_no ?? citation.matter_id} · {citation.field}
              </span>
            ))}
          </div>
        </article>
      ) : null}

      {history.length ? (
        <div className="mt-5">
          <h3 className="text-sm font-semibold text-slate-800">History</h3>
          <ul className="mt-2 space-y-2">
            {history.slice(0, 5).map((item, index) => (
              <li key={`${item.created_at ?? index}-${item.query}`} className="text-sm text-slate-600">
                {item.query}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
