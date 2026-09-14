import { useOffline } from "../pwa/useOffline";

export default function OfflineBanner() {
  const { isOffline, syncing, pendingQueueCount, syncNow } = useOffline();
  if (isOffline) return <div className="bg-amber-100 px-4 py-2 text-center text-sm font-semibold text-amber-900">Offline - using cached vault. Pending actions: {pendingQueueCount}</div>;
  if (syncing) return <div className="bg-blue-100 px-4 py-2 text-center text-sm font-semibold text-blue-900">Syncing...</div>;
  return <button onClick={syncNow} className="w-full bg-green-50 px-4 py-2 text-center text-sm font-semibold text-green-800">All synced</button>;
}
