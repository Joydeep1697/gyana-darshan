// IndexedDB wrapper for cached matter vault state and offline write queue.
export type OfflineMatter = { id: string; matter_id?: string; case_no?: string; tenant_id?: string; extracted?: unknown; timeline?: unknown[]; last_synced?: string };

const DB_NAME = "gyana-vault";
const DB_VERSION = 1;
const STORES = ["matters", "obligations", "chat_history", "offline_queue", "notifications"];

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      for (const store of STORES) if (!db.objectStoreNames.contains(store)) db.createObjectStore(store, { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function put(store: string, value: Record<string, unknown>) {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function get<T>(store: string, id: string): Promise<T | null> {
  const db = await openDB();
  return new Promise((resolve) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).get(id);
    req.onsuccess = () => resolve((req.result as T) ?? null);
    req.onerror = () => resolve(null);
  });
}

async function all<T>(store: string): Promise<T[]> {
  const db = await openDB();
  return new Promise((resolve) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve((req.result as T[]) ?? []);
    req.onerror = () => resolve([]);
  });
}

export const saveMatterToIDB = (matter: OfflineMatter) => put("matters", { ...matter, id: matter.id ?? matter.matter_id, last_synced: new Date().toISOString() });
export const getMatterFromIDB = (matter_id: string) => get<OfflineMatter>("matters", matter_id);
export const getAllMattersFromIDB = () => all<OfflineMatter>("matters");
export const queueOfflineRequest = (req: { url: string; method: string; body?: unknown }) => put("offline_queue", { id: crypto.randomUUID(), ...req, timestamp: new Date().toISOString() });
export const pendingQueue = () => all("offline_queue");
export async function syncOfflineQueue() {
  const queued = await pendingQueue();
  for (const item of queued as Array<{ url: string; method: string; body?: unknown }>) {
    await fetch(item.url, { method: item.method, headers: { "Content-Type": "application/json" }, body: item.body ? JSON.stringify(item.body) : undefined });
  }
  return queued.length;
}
