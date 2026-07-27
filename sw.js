// Caches only the app shell so the portal opens instantly and still shows its
// interface with no connection. Stats are never cached — they must always be
// live, so every API call goes straight to the network.
const SHELL = "shell-v7";
const FILES = ["./", "index.html", "manifest.webmanifest",
               "icon-192.png", "icon-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // never cache data: YouTube API, our probe function, Google sign-in
  if (url.origin !== location.origin || url.pathname.includes("/api/")) return;

  // network-first for the shell so a new deploy is picked up straight away
  e.respondWith(
    fetch(e.request)
      .then(r => {
        const copy = r.clone();
        caches.open(SHELL).then(c => c.put(e.request, copy)).catch(() => {});
        return r;
      })
      .catch(() => caches.match(e.request).then(m => m || caches.match("./")))
  );
});
