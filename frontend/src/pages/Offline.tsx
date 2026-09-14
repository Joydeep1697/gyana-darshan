import { useEffect, useState } from "react";
import { getAllMattersFromIDB, pendingQueue } from "../pwa/db";
import { useOffline } from "../pwa/useOffline";

export default function Offline() {
  const { lastSynced, syncNow } = useOffline();
  const [matterCount, setMatterCount] = useState(0);
  const [queueCount, setQueueCount] = useState(0);
  useEffect(() => {
    getAllMattersFromIDB().then((items) => setMatterCount(items.length));
    pendingQueue().then((items) => setQueueCount(items.length));
  }, []);
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-semibold text-slate-950">Offline vault</h1>
      <p className="mt-2 text-sm text-slate-600">Cached matters: {matterCount}</p>
      <p className="mt-1 text-sm text-slate-600">Pending queue: {queueCount}</p>
      <p className="mt-1 text-sm text-slate-600">Last synced: {lastSynced || "Not synced this session"}</p>
      <button onClick={syncNow} className="mt-5 rounded bg-blue-700 px-4 py-2 text-sm font-semibold text-white">Sync now</button>
    </main>
  );
}
