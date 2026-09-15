// Minimal service worker: no offline caching of API data in the POC,
// just enough to satisfy PWA installability.
self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => self.clients.claim());
self.addEventListener("fetch", () => {}); // pass-through
