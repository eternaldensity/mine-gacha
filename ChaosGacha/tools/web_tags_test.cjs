"use strict";
// Real-interface test: boots the actual pages in jsdom and drives the tag UI
// (entries chips/search/tooltips, gacha tag filter + tagged tickets).
// Usage: node tools/web_tags_test.cjs
const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { JSDOM, VirtualConsole } = require("jsdom");

const REPO = path.resolve(__dirname, "..");
const PORT = 8151;
const BASE = `http://127.0.0.1:${PORT}/`;
let failures = 0;
function ok(name, cond, extra) {
  if (cond) console.log(`ok ${name}`);
  else { failures++; console.log(`FAIL ${name}${extra ? ": " + extra : ""}`); }
}

// The pages read localStorage, so serve them over HTTP like production
// (file:// is an opaque origin and jsdom refuses localStorage there).
function startServer() {
  const proc = spawn("python3", ["-m", "http.server", String(PORT)],
    { cwd: path.join(REPO, "web"), stdio: "ignore" });
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + 8000;
    (function ping() {
      http.get(BASE + "entries.html", res => {
        res.resume();
        resolve(proc);
      }).on("error", () => {
        if (Date.now() > deadline) reject(new Error("web server did not start"));
        else setTimeout(ping, 150);
      });
    })();
  });
}

function boot(page, seed) {
  const vc = new VirtualConsole();
  const errors = [];
  // jsdom has no canvas backend; the tree 3D view logs that on boot.
  vc.on("jsdomError", e => {
    if (!/getContext/.test(e.message)) errors.push(e.message);
  });
  vc.on("error", e => errors.push(String(e)));
  const dom = new JSDOM(fs.readFileSync(path.join(REPO, "web", page), "utf8"), {
    url: BASE + page, runScripts: "dangerously", resources: "usable",
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      if (seed) for (const [k, v] of Object.entries(seed)) w.localStorage.setItem(k, v);
      // jsdom has no canvas backend: give the 3D view a no-op 2D context so
      // an active tree can boot and draw without throwing.
      const noop = () => {};
      const ctx = new Proxy({}, {
        get: (t, k) => (k in t ? t[k] : noop),
        set: (t, k, v) => { t[k] = v; return true; },
      });
      w.HTMLCanvasElement.prototype.getContext = () => ctx;
      if (!w.Path2D) {
        w.Path2D = class { constructor() {} moveTo() {} lineTo() {} arc() {} closePath() {} };
      }
    },
  });
  return new Promise(resolve => {
    dom.window.addEventListener("load", () => resolve({ dom, errors }));
  });
}

(async () => {
  const server = await startServer();
  try {
  // ---------- entries page ----------
  {
    const { dom, errors } = await boot("entries.html");
    const w = dom.window, d = w.document;
    ok("entries: no page errors", errors.length === 0, errors[0]);
    ok("entries: data loaded", (w.CHAOS_DATA && w.CHAOS_DATA.entries || []).length > 4000);
    ok("entries: tag docs loaded", w.CHAOS_TAGS && Object.keys(w.CHAOS_TAGS).length === 5);

    const chips = [...d.querySelectorAll("#eqTags button")];
    ok("entries: chips rendered", chips.length > 20, String(chips.length));

    // pick a chip for a tag we can verify against the data
    const data = w.CHAOS_DATA.entries;
    const wantTag = "fire";
    const hold = data.filter(e => (e.tags || []).includes(wantTag)).length;
    ok("entries: fire entries exist", hold > 50, String(hold));
    const chip = chips.find(b => b.textContent.startsWith(wantTag + " "));
    ok("entries: fire chip present", !!chip);
    const before = d.getElementById("eqCount").textContent;
    chip.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const after = d.getElementById("eqCount").textContent;
    const shown = parseInt(after.split(" ")[0], 10);
    ok("entries: chip filter narrows", shown > 0 && shown < data.length, after);
    ok("entries: count mentions tag", /tags: fire/.test(after), after);
    ok("entries: before/after differ", before !== after);

    // rendered rows all carry the tag, and pills show dictionary tooltips
    const rows = [...d.querySelectorAll("#eqBody tr")].slice(0, 25);
    const nameOf = tr => tr.children[1] ? tr.children[1].textContent.trim() : "";
    const allTagged = rows.every(tr => {
      const nm = nameOf(tr).replace(/\s*📋$/, "").trim();
      const e = data.find(x => x.name === nm);
      return e && (e.tags || []).includes(wantTag);
    });
    ok("entries: every shown row carries the tag", allTagged);
    const pills = [...d.querySelectorAll("#eqBody td .pill[title]")];
    ok("entries: pills carry dictionary tooltips", pills.length > 0,
      String(pills.length));
    const titleOk = pills.slice(0, 5).every(p => p.title.length > 10);
    ok("entries: tooltip text is a real description", titleOk,
      pills[0] && pills[0].title);

    // tag search narrows the chip list
    const chipQ = d.getElementById("eqTagQ");
    chipQ.value = "anti-";
    chipQ.dispatchEvent(new w.Event("input", { bubbles: true }));
    const anti = [...d.querySelectorAll("#eqTags button")];
    ok("entries: tag search filters chips",
      anti.length > 0 && anti.every(b => b.textContent.startsWith("anti-")),
      anti.map(b => b.textContent).join(","));
    dom.window.close();
  }

  // ---------- gacha page ----------
  {
    const { dom, errors } = await boot("gacha.html");
    const w = dom.window, d = w.document;
    ok("gacha: no page errors", errors.length === 0, errors[0]);
    const opts = [...d.querySelectorAll("#fTag option")].map(o => o.value);
    ok("gacha: tag filter lists tags", opts.length > 50, String(opts.length));
    ok("gacha: filter includes official names",
      opts.includes("fire") && opts.includes("fire+") && opts.includes("anti-dragon"));

    // roll with a tag selected -> result must carry that tag (spin off so the
    // result renders immediately instead of after the wheel animation)
    d.getElementById("spinSpeed").value = "off";
    d.getElementById("spinSpeed").dispatchEvent(new w.Event("change", { bubbles: true }));
    d.getElementById("fTag").value = "holy";
    d.getElementById("rollBtn").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const body = d.getElementById("resultBody").textContent;
    ok("gacha: tagged roll produced a result", /holy/.test(body), body.slice(0, 80));
    ok("gacha: result pill shows the tag", /🏷 holy/.test(d.getElementById("resultBody").innerHTML));
    const histTags = JSON.parse(w.localStorage.getItem("chaosGacha.v1") || "{}");
    ok("gacha: history entry carries the tag",
      (histTags.history || []).some(h => (h.tags || []).includes("holy")),
      JSON.stringify((histTags.history || [])[0] || {}).slice(0, 120));

    // a ticket carrying a tag rolls only that tag
    d.getElementById("tkTier").value = "legendary";
    d.getElementById("tkTag").value = "draconic";
    d.getElementById("btnAddTicket").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    ok("gacha: ticket added with tag pill",
      /🏷 draconic/.test(d.getElementById("ticketList").innerHTML));
    const rollBtns = [...d.querySelectorAll("#ticketList button")];
    rollBtns[rollBtns.length - 1].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const ticketHtml = d.getElementById("resultBody").innerHTML;
    ok("gacha: tagged ticket rolls tagged entry", /🏷 draconic/.test(ticketHtml),
      ticketHtml.slice(0, 140));
    const hist2 = JSON.parse(w.localStorage.getItem("chaosGacha.v1") || "{}");
    ok("gacha: tagged ticket history is tagged",
      (hist2.history || []).some(h => (h.tags || []).includes("draconic")),
      JSON.stringify((hist2.history || [])[0] || {}).slice(0, 120));
    ok("gacha: ticket was spent",
      (hist2.tickets || []).length === 0, JSON.stringify(hist2.tickets));

    // a tag the chosen tier cannot reach reports a clear error (no silent roll)
    d.getElementById("tkTier").value = "trash";
    d.getElementById("tkTag").value = "draconic";
    d.getElementById("btnAddTicket").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const before3 = (JSON.parse(w.localStorage.getItem("chaosGacha.v1") || "{}").history || []).length;
    const btns3 = [...d.querySelectorAll("#ticketList button")];
    btns3[btns3.length - 1].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const after3 = (JSON.parse(w.localStorage.getItem("chaosGacha.v1") || "{}").history || []).length;
    ok("gacha: impossible tag+tier shows a toast",
      /no entries match|matches nothing/.test(d.getElementById("toast").textContent),
      d.getElementById("toast").textContent);
    ok("gacha: impossible roll adds no history", after3 === before3);

    // a tag with no entries in the chosen category reports a clear error
    d.getElementById("fTag").value = "";
    const catBtn = [...d.querySelectorAll("#catGrid button")].find(b => b.textContent === "skill");
    catBtn.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    const skillOpts = [...d.querySelectorAll("#fTag option")].map(o => o.value);
    // official tags are per category: skill's own tags appear, familiar-only
    // tags (medium-size) do not. Curated elemental themes still ride along.
    ok("gacha: filter is category-aware (skill)",
      skillOpts.includes("expertise") && !skillOpts.includes("medium-size"),
      skillOpts.slice(0, 8).join(","));
    dom.window.close();
  }

  // ---------- tree page ----------
  {
    const { dom, errors } = await boot("tree.html");
    const w = dom.window, d = w.document;
    ok("tree: no page errors", errors.length === 0, errors[0]);
    const ownOpts = [...d.querySelectorAll("#ownTag option")].map(o => o.value);
    const newOpts = [...d.querySelectorAll("#newTag option")].map(o => o.value);
    ok("tree: owned-tag filter populated", ownOpts.length > 20, String(ownOpts.length));
    ok("tree: generation tag filter populated", newOpts.length > 20, String(newOpts.length));
    ok("tree: options carry counts", /\(\d+\)/.test(d.querySelector("#newTag option:nth-child(2)").textContent));
    dom.window.close();
  }

  // ---------- tree page: data-version mismatch offers Upgrade ----------
  {
    const stale = JSON.stringify({
      trees: [{ id: "t1", name: "Stale tree", seed: 7, params: {}, limit: 60,
                filters: {}, dataVersion: "oldversion", static: false, createdAt: 1 }],
      states: { t1: { points: 0, cores: 0, inventory: [], unlocked: [0] } },
      activeId: "t1", guideSeen: true, settings: {},
    });
    const { dom, errors } = await boot("tree.html", { "chaosTree.v1": stale });
    const w = dom.window, d = w.document;
    ok("tree: no page errors on a stale tree", errors.length === 0, errors[0]);
    ok("tree: mismatch banner is shown", d.getElementById("verWarn").style.display !== "none");
    const banner = d.getElementById("btnUpgradeActive");
    ok("tree: banner offers Upgrade", !!banner);
    const rowBtn = d.querySelector('#treeList button[data-tree-id="t1"]');
    ok("tree: tree row carries an Upgrade button keyed by id", !!rowBtn);
    banner.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    await new Promise(r => setTimeout(r, 150));
    const picked = !!d.querySelector("#treeList .upPicker") ||
      [...d.querySelectorAll("#treeList b")].some(b => /upgraded/i.test(b.textContent));
    ok("tree: banner Upgrade opens the upgrade flow", picked,
      d.getElementById("treeList").textContent.slice(0, 120));
    dom.window.close();
  }

  // ---------- frozen content with no recorded version still warns ----------
  {
    // The silent case: the tree record has no dataVersion at all and its
    // snapshot was silently re-keyed to the current data. Content provenance
    // is the only thing that can flag it.
    const tree = JSON.stringify({
      trees: [{ id: "t2", name: "Unversioned tree", seed: 7, params: {}, limit: 60,
                filters: {}, static: false, createdAt: 1 }],
      states: { t2: { points: 0, cores: 0, inventory: [], unlocked: [0] } },
      activeId: "t2", guideSeen: true, settings: {},
    });
    const nodes = [{ id: 0, file: "__root__", name: "Origin", rarity: 0, pos: [0, 0, 0], r: 0 },
                   { id: 1, file: "ability", name: "HyperQbe the Streamer", rarity: 3.4,
                     source: "Q-UP", tag: "both", description: "old entry", meta: [], pos: [1, 0, 0], r: 1 }];
    const gen = JSON.stringify({ key: JSON.stringify([7, {}, {}, 60, "oldversion"]),
                                 res: { nodes, edges: [{ a: 0, b: 1, d: 1 }] } });
    const { dom, errors } = await boot("tree.html",
      { "chaosTree.v1": tree, "chaosTree.gen.v1.t2": gen });
    const w = dom.window, d = w.document;
    ok("tree: frozen tree boots", errors.length === 0, errors[0]);
    ok("tree: unversioned frozen content still warns",
      d.getElementById("verWarn").style.display !== "none",
      d.getElementById("verWarnText").textContent.slice(0, 120));
    const saved = JSON.parse(w.localStorage.getItem("chaosTree.gen.v1.t2") || "{}");
    const savedKey = JSON.parse(saved.key || "[]");
    ok("tree: frozen run kept its old entries under the current key",
      saved.res && saved.res.nodes && saved.res.nodes.some(nd => nd.name === "HyperQbe the Streamer") &&
      savedKey[4] === w.CHAOS_DATA.dataVersion,
      JSON.stringify(savedKey));
    ok("tree: row pill names the stale version",
      /data voldversion/.test(d.getElementById("treeList").textContent),
      d.getElementById("treeList").textContent.slice(0, 140));
    dom.window.close();
  }

  // ---------- static (imported) snapshot on old data warns too ----------
  {
    const tree = JSON.stringify({
      trees: [{ id: "t3", name: "Imported primary", seed: 5, params: {}, limit: null,
                filters: {}, dataVersion: "ee5d89ed5c", static: true, createdAt: 1 }],
      states: { t3: { points: 0, cores: 0, inventory: [], unlocked: [0] } },
      activeId: "t3", guideSeen: true, settings: {},
    });
    const topo = JSON.stringify({
      params: {},
      nodes: [{ id: 0, file: "__root__", name: "Origin", rarity: 0, pos: [0, 0, 0], r: 0 },
              { id: 1, file: "ability", name: "HyperQbe the Streamer", rarity: 3.4, source: "Q-UP",
                tag: "both", description: "baked entry", meta: [], pos: [1, 0, 0], r: 1 }],
      edges: [{ a: 0, b: 1, d: 1 }],
    });
    const { dom, errors } = await boot("tree.html",
      { "chaosTree.v1": tree, "chaosTree.static.v1.t3": topo });
    const w = dom.window, d = w.document;
    ok("tree: static snapshot boots", errors.length === 0, errors[0]);
    ok("tree: imported snapshot on old data warns",
      d.getElementById("verWarn").style.display !== "none",
      d.getElementById("verWarnText").textContent.slice(0, 140));
    ok("tree: warning says it is an imported snapshot",
      /imported snapshot/.test(d.getElementById("verWarnText").textContent));
    ok("tree: row pill names the exported version",
      /data vee5d89ed5c/.test(d.getElementById("treeList").textContent),
      d.getElementById("treeList").textContent.slice(0, 140));
    ok("tree: warning counts vanished entries for a versioned snapshot too",
      /1 of its entries no longer exist/.test(d.getElementById("verWarnText").textContent),
      d.getElementById("verWarnText").textContent.slice(-90));
    // an external snapshot with no recorded version stays quiet
    const anon = JSON.stringify({
      trees: [{ id: "t4", name: "External file", seed: 5, params: {}, limit: null,
                filters: {}, dataVersion: null, static: true, createdAt: 1 }],
      states: { t4: { points: 0, cores: 0, inventory: [], unlocked: [0] } },
      activeId: "t4", guideSeen: true, settings: {},
    });
    // A version-less file still warns if it references entries that no longer
    // exist in the data ("HyperQbe the Streamer" in the stub topology).
    const b2 = await boot("tree.html",
      { "chaosTree.v1": anon, "chaosTree.static.v1.t4": topo });
    const b2d = b2.dom.window.document;
    ok("tree: version-less file with vanished entries warns",
      b2d.getElementById("verWarn").style.display !== "none",
      b2d.getElementById("verWarnText").textContent.slice(0, 120));
    ok("tree: warning counts the vanished entries",
      /1 of its entries no longer exist/.test(b2d.getElementById("verWarnText").textContent),
      b2d.getElementById("verWarnText").textContent.slice(-90));
    ok("tree: row pill flags stale entries",
      /1 stale entry/.test(b2d.getElementById("treeList").textContent),
      b2d.getElementById("treeList").textContent.slice(0, 120));
    b2.dom.window.close();
    dom.window.close();
  }

  console.log(failures ? `${failures} FAILURES` : "ALL PASS");
  } finally {
    server.kill();
    process.exit(failures ? 1 : 0);
  }
})().catch(e => { console.log("FAIL harness:", e && e.stack || e); process.exit(1); });
