// App shell cache; card data and prices always come from the network.
const CACHE = "binderscan-v9";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.includes("/data/") || u.hostname.endsWith("scryfall.com") || u.hostname.endsWith("anthropic.com")) return;
  if (u.origin === location.origin) {
    // bypass the browser's HTTP cache so a new version shows up on the next open
    e.respondWith(fetch(e.request, { cache: "no-store" }).then(r => { const c = r.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
  } else if (u.hostname === "cdn.jsdelivr.net" || u.hostname.endsWith("gstatic.com") || u.hostname === "fonts.googleapis.com" || u.hostname.endsWith("tessdata.projectnaptha.com")) {
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); return r; })));
  }
});
