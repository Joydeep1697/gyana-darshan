import ChatPanel from "./components/ChatPanel";
import MatterDetail from "./pages/MatterDetail";
import MatterList from "./pages/MatterList";

function route() {
  const path = window.location.pathname;
  if (path.startsWith("/matters/")) return <MatterDetail />;
  if (path === "/matters") return <MatterList />;
  return (
    <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[1fr_380px]">
      <section className="rounded border border-slate-200 bg-white p-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Gyana Darshan</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Matter cockpit</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          Review extracted hearings, obligations, and matter facts with explicit provenance warnings.
        </p>
        <a className="mt-5 inline-flex rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/matters">
          Open matters
        </a>
      </section>
      <ChatPanel />
    </main>
  );
}

export default function App() {
  return (
    <div>
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <a className="text-sm font-bold text-slate-950" href="/">
            Gyana Darshan
          </a>
          <div className="flex gap-4 text-sm font-medium text-slate-600">
            <a className="hover:text-blue-700" href="/matters">
              Matters
            </a>
            <a className="hover:text-blue-700" href="/api/calendar/ics">
              Calendar
            </a>
          </div>
        </nav>
      </header>
      {route()}
    </div>
  );
}
