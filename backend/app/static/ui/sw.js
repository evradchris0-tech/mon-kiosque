/* Service worker de la nouvelle interface : coquille /ui/ en cache, réseau d'abord, jamais l'API ni la console. */
const VERSION = "mk-ui-v1";
const COQUILLE = [
  "/ui/", "/ui/manifest.webmanifest", "/ui/css/app.css",
  "/ui/js/core.js", "/ui/js/shell.js", "/ui/js/main.js",
  "/ui/img/logo.svg", "/ui/icons/app-192.png", "/ui/icons/app-512.png",
];

self.addEventListener("install", (e) => {
  // Chaque fichier est ajouté séparément : un fichier absent n'empêche pas l'installation.
  e.waitUntil(
    caches.open(VERSION)
      .then((c) => Promise.all(COQUILLE.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((cles) => Promise.all(cles.filter((k) => k.startsWith("mk-ui-") && k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (!url.pathname.startsWith("/ui/")) return; // /api, /console, /app : jamais interceptés
  e.respondWith(
    fetch(e.request)
      .then((r) => {
        if (r.ok && !url.search.includes("mock=1")) {
          const copie = r.clone();
          caches.open(VERSION).then((c) => c.put(e.request, copie));
        }
        return r;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: e.request.mode === "navigate" }).then((r) => r || (e.request.mode === "navigate" ? caches.match("/ui/") : undefined)))
  );
});
