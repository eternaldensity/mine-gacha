"use strict";
// Behaviour test for web/sw.js: generated data bundles (data/*.js) must be
// network-first so a fresh export shows up on reload, the app shell stays
// cache-first, and an offline visit still works from cache.
//
//   node tools/sw_behavior_test.cjs
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const REPO = path.resolve(__dirname, "..");
const SRC = fs.readFileSync(path.join(REPO, "web", "sw.js"), "utf8");

let failures = 0;
function ok(name, cond, extra) {
  if (cond) console.log(`ok ${name}`);
  else { failures++; console.log(`FAIL ${name}${extra ? ": " + extra : ""}`); }
}

function loadWorker({ cached = {}, offlineUrls = [] } = {}) {
  const cache = new Map(Object.entries(cached));
  const puts = [];
  const fetched = [];
  const handlers = {};
  const store = {
    addAll: async (urls) => { for (const u of urls) cache.set(u, `precached:${u}`); },
    put: async (req, res) => { puts.push(String(req.url)); cache.set(String(req.url), await res.text()); },
    match: async (req) => {
      const key = String(req.url);
      if (!cache.has(key)) return undefined;
      const body = cache.get(key);
      return { ok: true, text: async () => body, clone() { return this; } };
    },
  };
  const sandbox = {
    console, URL, Promise,
    caches: {
      open: async () => store,
      match: (req) => store.match(req),
      keys: async () => ["chaos-gacha-web-v8"],
      delete: async () => true,
    },
    clients: { claim: async () => {} },
    self: { addEventListener: (n, fn) => { handlers[n] = fn; }, skipWaiting: async () => {} },
    fetch: (req) => {
      const url = String(req.url || req);
      fetched.push(url);
      if (offlineUrls.includes(url)) return Promise.reject(new Error("offline"));
      return Promise.resolve({
        ok: true, text: async () => "fresh",
        clone() { return { text: async () => "fresh" }; },
      });
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox);
  return { handlers, cache, puts, fetched };
}

function request(handlers, url) {
  let captured = null;
  handlers.fetch({ request: { method: "GET", url }, respondWith: (p) => { captured = p; } });
  return captured;
}

(async () => {
  // install precaches the shell + data, including the tags bundle
  const w1 = loadWorker();
  const waits = [];
  w1.handlers.install({ waitUntil: (p) => waits.push(p) });
  await Promise.all(waits);
  ok("install precaches data/tags.js", w1.cache.has("data/tags.js"));
  ok("install precaches data/entries.js", w1.cache.has("data/entries.js"));

  // data bundle, online: network wins and the cache is refreshed
  const w2 = loadWorker({ cached: { "http://x/data/entries.js": "stale" } });
  const res2 = await request(w2.handlers, "http://x/data/entries.js");
  const body2 = res2 ? await res2.text() : null;
  ok("data bundle is served from the network", body2 === "fresh", String(body2));
  ok("data bundle cache is refreshed", w2.puts.includes("http://x/data/entries.js"),
    w2.puts.join(","));

  // data bundle, offline: cached copy still answers
  const w3 = loadWorker({
    cached: { "http://x/data/tags.js": "cached-tags" },
    offlineUrls: ["http://x/data/tags.js"],
  });
  const res3 = await request(w3.handlers, "http://x/data/tags.js");
  const body3 = res3 ? await res3.text() : null;
  ok("offline data falls back to cache", body3 === "cached-tags", String(body3));
  ok("no cache write when the network fails", w3.puts.length === 0, w3.puts.join(","));

  // app shell: cache-first, no network traffic on a hit
  const w4 = loadWorker({ cached: { "http://x/js/tree-app.js": "shell-js" } });
  const res4 = await request(w4.handlers, "http://x/js/tree-app.js");
  const body4 = res4 ? await res4.text() : null;
  ok("shell served from cache without a fetch",
    body4 === "shell-js" && w4.fetched.length === 0,
    `${body4}/${w4.fetched.join(",")}`);

  // shell miss falls through to the network
  const w5 = loadWorker();
  const res5 = await request(w5.handlers, "http://x/js/engine.js");
  const body5 = res5 ? await res5.text() : null;
  ok("shell miss goes to the network", body5 === "fresh" && w5.fetched.length === 1,
    `${body5}/${w5.fetched.join(",")}`);

  console.log(failures ? `${failures} FAILURES` : "ALL PASS");
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log("FAIL harness:", e && e.stack || e); process.exit(1); });
