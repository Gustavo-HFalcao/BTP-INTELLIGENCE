// Bomtempo Dashboard — Service Worker (Level 1 PWA: installability + asset cache)
const CACHE_NAME = 'bomtempo-v1';

const PRECACHE = [
  '/',
  '/manifest.json',
];

// Install: pre-cache shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first (app requires real-time server state via WebSocket)
self.addEventListener('fetch', (event) => {
  // Skip non-GET and cross-origin requests
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;

  // Skip WebSocket upgrade requests
  if (event.request.headers.get('upgrade') === 'websocket') return;

  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
