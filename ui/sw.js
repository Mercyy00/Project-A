// JARVIS Autonomous Assistant PWA Service Worker
const CACHE_NAME = 'jarvis-pwa-v7';
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Pass WebSocket and API requests straight through to network
  if (event.request.url.includes('/ws') || event.request.url.includes('/api/')) {
    return;
  }
  const isNavigation = event.request.mode === 'navigate';
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    if (isNavigation) {
      try {
        const freshResponse = await fetch(event.request);
        if (freshResponse.ok) await cache.put(event.request, freshResponse.clone());
        return freshResponse;
      } catch (_) {
        return (await cache.match(event.request)) || (await cache.match('/'));
      }
    }
    const cachedResponse = await cache.match(event.request);
    if (cachedResponse) return cachedResponse;
    return fetch(event.request);
  })());
});
