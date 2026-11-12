/* Service worker Mon Kiosque : coquille de l'appli en cache, jamais l'API. */
const CACHE = "mon-kiosque-v1";
const COQUILLE = ["/app", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(COQUILLE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/console")) return; // données : toujours le réseau
  // Réseau d'abord, cache en secours (appli ouverte sans connexion).
  e.respondWith(
    fetch(e.request)
      .then((r) => {
        if (r.ok) { const copie = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copie)); }
        return r;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("/app")))
  );
});
