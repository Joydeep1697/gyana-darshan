import { useEffect, useState } from "react";
import { pendingQueue, syncOfflineQueue } from "./db";

export function useOffline() {
  const [isOnline, setOnline] = useState(navigator.onLine);
  const [lastSynced, setLastSynced] = useState("");
  const [pendingQueueCount, setPendingQueueCount] = useState(0);
  const [syncing, setSyncing] = useState(false);

  async function refresh() {
    setPendingQueueCount((await pendingQueue()).length);
  }

  async function syncNow() {
    setSyncing(true);
    try {
      await syncOfflineQueue();
      setLastSynced(new Date().toISOString());
      await refresh();
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    refresh();
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return { isOnline, isOffline: !isOnline, lastSynced, syncNow, pendingQueueCount, syncing };
}
