import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ChatPanel from "./components/ChatPanel";
import OfflineBanner from "./components/OfflineBanner";
import Login from "./pages/Login";
import IntelligenceDashboard from "./pages/IntelligenceDashboard";
import MatterDetail from "./pages/MatterDetail";
import MatterList from "./pages/MatterList";
import Offline from "./pages/Offline";
import { setupPushNotifications } from "./pwa/push";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user } = useAuth();
  const token = window.localStorage.getItem("nyaya_token");
  if (!user && !token) return <Navigate to="/login" replace />;
  return children;
}

function Shell() {
  const { user, logout } = useAuth();
  return (
    <div>
      <OfflineBanner />
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <a className="text-sm font-bold text-slate-950" href="/">Gyana Darshan</a>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-600">
            <a className="hover:text-blue-700" href="/matters">Matters</a>
            <a className="hover:text-blue-700" href="/intelligence">Intelligence</a>
            <a className="hover:text-blue-700" href="/api/calendar/ics">Calendar</a>
            {user ? <span className="text-xs text-slate-500">{user.tenant_id} - {user.role}</span> : null}
            {user ? <button onClick={logout} className="text-slate-600 hover:text-blue-700">Logout</button> : null}
          </div>
        </nav>
      </header>
      <Routes>
        <Route path="/matters" element={<ProtectedRoute><MatterList /></ProtectedRoute>} />
        <Route path="/matters/:matter_id" element={<ProtectedRoute><MatterDetail /></ProtectedRoute>} />
        <Route path="/intelligence" element={<ProtectedRoute><IntelligenceDashboard /></ProtectedRoute>} />
        <Route path="/offline" element={<ProtectedRoute><Offline /></ProtectedRoute>} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[1fr_380px]">
                <section className="rounded border border-slate-200 bg-white p-6">
                  <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Gyana Darshan</p>
                  <h1 className="mt-2 text-3xl font-semibold text-slate-950">Matter cockpit</h1>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                    Review extracted hearings, obligations, risks, and vault chat with explicit provenance warnings.
                  </p>
                  <a className="mt-5 inline-flex rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white" href="/matters">Open matters</a>
                </section>
                <ChatPanel />
              </main>
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

export default function App() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").then(() => setupPushNotifications()).catch(() => undefined);
    }
  }, []);
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<Shell />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
