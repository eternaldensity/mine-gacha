/* Offline cache for the Chaos Gacha web apps. App shell + data bundle;
 * player saves live in localStorage and need no network at all.
 *
 * Strategy: the app shell (html/css/js/icons) is cache-first, but generated
 * data bundles are network-first — they change on every export, and a
 * cache-first data file silently pins returning players to an old dataset
 * until the cache name is bumped. Bump CACHE when shell files change. */
const CACHE = "chaos-gacha-web-v14";
const ASSETS = [
  "./",
  "index.html",
  "tree.html",
  "gacha.html",
  "curse.html",
  "entries.html",
  "docs.html",
  "manifest.webmanifest",
  "favicon.svg",
  "css/app.css",
  "data/entries.js",
  "data/tags.js",
  "data/curses.js",
  "js/rng.js",
  "js/generator.js",
  "js/engine.js",
  "js/gacha.js",
  "js/tree-app.js",
  "js/share.js",
  "js/paste.js",
  "js/gacha-app.js",
  "js/curse-app.js",
  "js/docs.js",
  "js/entries-app.js",
  "casino.html",
  "js/casino/config.js",
  "js/casino/dom.js",
  "js/casino/legacy.js",
  "js/casino/state.js",
  "js/casino/hud.js",
  "js/casino/stats.js",
  "js/casino/slots.js",
  "js/casino/effects.js",
  "js/casino/prizes.js",
  "js/casino/pulls.js",
  "js/casino/combat.js",
  "js/casino/audio.js",
  "js/casino/draft.js",
  "js/casino/curses.js",
  "js/casino/death.js",
  "js/casino/sprites.js",
  "js/casino/update.js",
  "js/casino/render.js",
  "js/casino/main.js",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
  "social/social.png",
  "social/social-tree.png",
  "social/social-gacha.png"
];

// Generated bundles: entries/tags/curses plus anything under data/.
const DATA_RE = /\/data\//;

self.addEventListener("install", (ev) => {
  ev.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (ev) => {
  if (ev.request.method !== "GET") return;
  if (DATA_RE.test(new URL(ev.request.url).pathname)) {
    // Network first so a fresh export is picked up on the next reload, with
    // the cached copy as the offline fallback.
    ev.respondWith(
      fetch(ev.request).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(ev.request, copy)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match(ev.request, { ignoreSearch: true }))
    );
    return;
  }
  ev.respondWith(
    caches.match(ev.request, { ignoreSearch: true }).then((hit) => hit || fetch(ev.request))
  );
});
