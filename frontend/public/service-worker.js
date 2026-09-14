const STATIC_CACHE = "gyana-static-v1";
const API_CACHE = "gyana-api-v1";
const QUEUE_KEY = "gyana-offline-queue";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(["/", "/offline.html", "/manifest.json"])));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

async function queueRequest(request) {
  const body = await request.clone().text();
  const queue = JSON.parse((await idbGet(QUEUE_KEY)) || "[]");
  queue.push({ url: request.url, method: request.method, headers: [...request.headers.entries()], body, timestamp: Date.now() });
  await idbSet(QUEUE_KEY, JSON.stringify(queue));
}

function idbStore() {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open("gyana-vault-sw", 1);
    open.onupgradeneeded = () => open.result.createObjectStore("kv");
    open.onsuccess = () => resolve(open.result);
    open.onerror = () => reject(open.error);
  });
}

async function idbGet(key) {
  const db = await idbStore();
  return new Promise((resolve) => {
    const tx = db.transaction("kv", "readonly");
    const req = tx.objectStore("kv").get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(null);
  });
}

async function idbSet(key, value) {
  const db = await idbStore();
  return new Promise((resolve) => {
    const tx = db.transaction("kv", "readwrite");
    tx.objectStore("kv").put(value, key);
    tx.oncomplete = () => resolve();
  });
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method === "POST" && (url.pathname.startsWith("/api/obligations/") || url.pathname.startsWith("/api/chat"))) {
    event.respondWith(fetch(event.request.clone()).catch(async () => {
      await queueRequest(event.request);
      return new Response(JSON.stringify({ queued: true, offline: true, provenance_verified: false }), { headers: { "Content-Type": "application/json" } });
    }));
    return;
  }
  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(caches.open(STATIC_CACHE).then((cache) => cache.match(event.request).then((hit) => hit || fetch(event.request).then((res) => { cache.put(event.request, res.clone()); return res; }))));
    return;
  }
  if (url.pathname.startsWith("/api/matters") || url.pathname.startsWith("/api/obligations")) {
    event.respondWith(fetch(event.request).then((res) => { caches.open(API_CACHE).then((cache) => cache.put(event.request, res.clone())); return res; }).catch(() => caches.match(event.request)));
    return;
  }
  if (url.pathname.startsWith("/api/calendar")) {
    event.respondWith(caches.match(event.request).then((hit) => hit || fetch(event.request)));
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then((hit) => hit || caches.match("/offline.html"))));
});

self.addEventListener("sync", (event) => {
  if (event.tag === "gyana-offline-sync") event.waitUntil(idbSet(QUEUE_KEY, "[]"));
});
