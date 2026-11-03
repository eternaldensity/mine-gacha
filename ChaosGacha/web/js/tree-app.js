"use strict";
/* Chaos Tree web app: multiple named trees, localStorage saves,
 * import/export, canvas 3D view, SVG neighbour view, full engine UI. */
(function () {
  const E = window.ChaosEngine, G = window.ChaosGen;
  const DATA = window.CHAOS_DATA || { entries: [], tiers: [], classes: [] };
  const LS_KEY = "chaosTree.v1";
  const LS_STATIC = "chaosTree.static.v1";
  // Set when a ?share= link is opened: a frozen, read-only snapshot of
  // someone else's tree. Nothing is persisted while it is active.
  let SHARED = null;
  const isShared = () => !!SHARED;

  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  // Hosts whose URLs become clickable links (new tab, opener detached).
  // Anything else stays inert text, so arbitrary sites never auto-link.
  const LINK_SUFFIXES = [".fandom.com", ".fextralife.com"];
  const LINK_HOSTS = ["dnd5e.wikidot.com", "heroes.thelazy.net",
    "fallenaces.wiki.gg", "satisfactory.wiki.gg"];
  // Escape HTML, then linkify whitelisted http(s) URLs. Unbalanced
  // trailing ")" (MediaWiki titles contain balanced ones) and trailing
  // punctuation are left as plain text so links resolve.
  function linkify(text) {
    return String(text == null ? "" : text)
      .split(/(https?:\/\/[^\s<>"'\]]+)/g).map(part => {
        if (!/^https?:\/\//.test(part)) return esc(part);
        let url = part, trail = "";
        while (url.endsWith(")") &&
               (url.match(/\(/g) || []).length < (url.match(/\)/g) || []).length) {
          url = url.slice(0, -1);
          trail = ")" + trail;
        }
        const punct = url.match(/[.,;:!?]+$/);
        if (punct) {
          url = url.slice(0, -punct[0].length);
          trail = punct[0] + trail;
        }
        let host = "";
        try { host = new URL(url).hostname.toLowerCase(); }
        catch (e) { return esc(part); }
        const ok = LINK_HOSTS.includes(host) ||
          LINK_SUFFIXES.some(s => host === s.slice(1) || host.endsWith(s));
        if (!ok || !url) return esc(part);
        return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>${esc(trail)}`;
      }).join("");
  }
  // Whole-number rarities display with .0 for consistency.
  const fmtR = r => Number.isInteger(r) ? r.toFixed(1) : String(r);

  function nodeTags(nd) { return (nd && (nd.tags || nd.tg)) || []; }
  // Tags ordered by how many entries carry them (the official taxonomy is
  // large, so the pickers lead with the common ones).
  function tagCounts() {
    const c = (DATA.tagCounts) || null;
    if (c) return c;
    const out = {};
    for (const e of (DATA.entries || [])) {
      for (const t of ((e.tags || e.tg) || [])) out[t] = (out[t] || 0) + 1;
    }
    return out;
  }
  function allTags() {
    const counts = tagCounts();
    return [...new Set(Object.keys(counts))].sort(
      (a, b) => (counts[b] || 0) - (counts[a] || 0) || a.localeCompare(b));
  }
  // Tag descriptions come from the original site's dictionaries (data/tags.js).
  const TAGDOCS = window.CHAOS_TAGS || {};
  function tagDesc(tag, cat) {
    const hit = (cat && (TAGDOCS[cat] || [])).find(t => t.tag === tag);
    if (hit) return hit.desc;
    for (const c of Object.keys(TAGDOCS)) {
      const h = TAGDOCS[c].find(t => t.tag === tag);
      if (h) return h.desc;
    }
    return "";
  }
  function tagPills(tags, cat) {
    return (tags || []).map(t => {
      const d = tagDesc(t, cat);
      return `<span class="pill"${d ? ` title="${esc(d)}"` : ""}>🏷 ${esc(t)}</span>`;
    }).join(" ");
  }
  // Copy format mirrors the gacha result text: name on one line, metadata in
  // parentheses on the next, then the full description, so a pasted node
  // reads the same everywhere. Cost is in tree points (more relevant than
  // rarity here).
  function nodeText(nd) {
    const cls = classOf(nd.rarity);
    const tags = nodeTags(nd);
    return `#${nd.id} ${nd.name}\n(${E.fmt(Math.pow(10, nd.rarity))} pts, ${cls.name}, ${nd.file}` +
      `${nd.source ? ", " + nd.source : ""}${tags.length ? ", #" + tags.join(" #") : ""})` +
      (nd.description ? `\n${nd.description}` : "");
  }
  async function copyText(t, what) {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(t);
      } else {
        const ta = document.createElement("textarea");
        ta.value = t;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      toast(what ? `Copied ${what}!` : "Copied!");
    } catch (e) { toast("Copy failed.", true); }
  }

  function toast(msg, isErr) {
    const t = $("toast");
    t.textContent = msg;
    t.className = "toast" + (isErr ? " err" : "");
    t.style.display = "block";
    clearTimeout(t._h);
    t._h = setTimeout(() => { t.style.display = "none"; }, 3200);
  }
  function err(e) { toast(e && e.message ? e.message : String(e), true); }

  function classOf(r) {
    for (const c of DATA.classes) if (r < c.max) return c;
    return DATA.classes[DATA.classes.length - 1];
  }
  // Node colour encodes rarity tier (same classes as the gacha results);
  // category is still shown as text everywhere.
  const classColor = r => classOf(r).color;
  // Rarity-tier visibility toggles (legend doubles as the control).
  const hiddenClasses = new Set();
  function nodeShown(nd) { return !hiddenClasses.has(classOf(nd.rarity).name); }

  // Display preference: NSFW nodes are hidden everywhere unless opted in.
  // Noncon nodes hide behind a second opt-in, offered only with NSFW on.
  // (Generation excludes them by default separately, via filters.includeNsfw.)
  function showNsfw() { return !!(DB.settings && DB.settings.showNsfw); }
  function showNoncon() { return !!(DB.settings && DB.settings.showNoncon); }
  function visNode(nd) {
    return !nd || ((showNsfw() || !nd.nsfw) && (showNoncon() || !nd.noncon));
  }
  // The Noncon toggles only appear once NSFW content itself is allowed in.
  function updateNonconRows() {
    for (const [box, row] of [["showNsfw", "showNonconRow"],
                              ["newNsfw", "newNonconRow"]]) {
      const b = $(box), r = $(row);
      if (b && r) r.style.display = b.checked ? "" : "none";
    }
  }

  // ---- storage ---------------------------------------------------------
  function loadDB() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const db = JSON.parse(raw);
        db.trees = db.trees || []; db.states = db.states || {};
        db.settings = db.settings || {};
        return db;
      }
    } catch (e) { /* corrupted -> fresh */ }
    return { trees: [], states: {}, activeId: null, guideSeen: false, settings: {} };
  }
  function saveDB() {
    if (isShared()) return; // never persist a shared snapshot over local saves
    try { localStorage.setItem(LS_KEY, JSON.stringify(DB)); }
    catch (e) { toast("Storage full: export your trees to keep them safe.", true); }
  }
  let DB = loadDB();
  const runtimes = new Map();   // treeId -> runtime
  const memoryStatic = new Map(); // treeId -> payload (quota fallback)
  const memoryGen = new Map(); // treeId -> {key, res} generated-tree cache
  const LS_GEN = "chaosTree.gen.v1";
  function loadStatic(id) {
    if (memoryStatic.has(id)) return memoryStatic.get(id);
    try {
      const raw = localStorage.getItem(LS_STATIC + "." + id);
      if (raw) { const p = JSON.parse(raw); memoryStatic.set(id, p); return p; }
    } catch (e) { /* ignore */ }
    return null;
  }
  function saveStatic(id, payload) {
    memoryStatic.set(id, payload);
    try { localStorage.setItem(LS_STATIC + "." + id, JSON.stringify(payload)); }
    catch (e) { toast("Tree too big for browser storage; it will live in memory until you export it.", true); }
  }
  function getTree(id) { return DB.trees.find(t => t.id === id) || null; }
  function activeTree() { return getTree(DB.activeId); }
  function activeState() {
    const t = activeTree();
    if (!t) return null;
    if (!DB.states[t.id]) DB.states[t.id] = E.newState();
    return DB.states[t.id];
  }

  async function getRuntime(tree) {
    if (runtimes.has(tree.id)) return runtimes.get(tree.id);
    if (tree.shared) {
      // The snapshot's nodes/edges are already the owner's final topology
      // (swaps/added links baked in) and only span the shared set, so no
      // engine mutation is applied and the view sets come precomputed.
      const p = SHARED.payload;
      const rt = G.buildRuntime({ nodes: p.nodes, edges: p.edges });
      rt.frozen = { vis: new Set(p.view.visible), unl: new Set(p.state.unlocked) };
      rt.sharedView = p.view;
      runtimes.set(tree.id, rt);
      return rt;
    }
    let rt;
    if (tree.static) {
      const payload = loadStatic(tree.id);
      if (!payload) throw new Error("static tree data missing (re-import the file)");
      rt = G.buildRuntime(payload);
      rt.params = payload.params || {};
    } else {
      // Regenerating a full tree costs seconds; reuse the cached result
      // when the seed/config/data haven't changed (quota failures fall
      // back to regenerating, as before).
      const key = genCacheKey(tree);
      const hit = key && loadGenerated(tree.id);
      let res = (hit && hit.key === key) ? hit.res : null;
      if (res) res = JSON.parse(JSON.stringify(res));
      if (!res && hit && hit.res && hit.res.nodes && hit.res.nodes.length) {
        // Same seed/config but new data: regenerating would silently
        // reassign entries (and links) under saved progress, because node
        // ids are positional into the sampled pool. Freeze the last good
        // generation instead; Upgrade is the path to current data. Only
        // when the mismatch is the data version alone — a config change
        // still regenerates from scratch as before.
        try {
          const hk = JSON.parse(hit.key), nk = JSON.parse(key);
          if (hk && nk && JSON.stringify(hk.slice(0, 4)) === JSON.stringify(nk.slice(0, 4))) {
            res = JSON.parse(JSON.stringify(hit.res));
            saveGenerated(tree.id, key, res);
            // Record where the frozen content came from: the snapshot now
            // answers to the current key, so nothing else can tell that the
            // entries inside it are older than the loaded data.
            const from = hk[4] || "unknown";
            if (tree.contentDataVersion !== from) {
              tree.contentDataVersion = from;
              if (!tree.dataVersion) tree.dataVersion = from === "unknown" ? null : from;
              saveDB();
            }
          }
        } catch (e) { /* fall through to regenerate */ }
      }
      if (!res) {
        res = await G.generate(DATA.entries, tree.seed, tree.params || {}, {
          limit: tree.limit || null, ...(tree.filters || {})
        }, () => {});
        if (key) saveGenerated(tree.id, key, res);
        // Freshly generated content: the record is current again.
        if (tree.contentDataVersion || tree.dataVersion !== DATA.dataVersion) {
          delete tree.contentDataVersion;
          tree.dataVersion = DATA.dataVersion || null;
          saveDB();
        }
      }
      rt = G.buildRuntime(res);
      rt.params = Object.assign({}, G.DEFAULTS, tree.params || {});
    }
    const st = DB.states[tree.id] || E.newState();
    E.applySwaps(rt, st);
    E.applyAddedLinks(rt, st);
    E.applyEntrySwaps(rt, st);
    runtimes.set(tree.id, rt);
    return rt;
  }
  function dropRuntime(id) { runtimes.delete(id); }
  function genCacheKey(tree) {
    try {
      return JSON.stringify([tree.seed, tree.params || {},
        tree.filters || {}, tree.limit || null, DATA.dataVersion || null]);
    } catch (e) { return null; }
  }
  function loadGenerated(id) {
    if (memoryGen.has(id)) return memoryGen.get(id);
    try {
      const raw = localStorage.getItem(LS_GEN + "." + id);
      if (raw) { const p = JSON.parse(raw); memoryGen.set(id, p); return p; }
    } catch (e) { /* ignore */ }
    return null;
  }
  function saveGenerated(id, key, res) {
    // Snapshot: the live runtime aliases its nodes, and swap application
    // mutates them in place, so the cache must own an isolated copy.
    let snap = null;
    try { snap = JSON.parse(JSON.stringify({ key, res })); }
    catch (e) { return; }
    memoryGen.set(id, snap);
    try { localStorage.setItem(LS_GEN + "." + id, JSON.stringify(snap)); }
    catch (e) { /* quota: regenerate next time, as today */ }
  }

  // All known gacha sources, sorted. Snapshotted onto tree records as
  // knownSources so upgrades can tell brand-new sources (default: include)
  // apart from deliberately excluded ones (stay out unless asked).
  function allSources() {
    return [...new Set((DATA.entries || []).map(e => e.s).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b));
  }

  // ---- tabs --------------------------------------------------------------
  let currentTab = "trees";
  document.querySelectorAll("#tabs button").forEach(b => {
    b.addEventListener("click", () => showTab(b.dataset.tab));
  });
  function showTab(name) {
    currentTab = name;
    document.querySelectorAll("#tabs button").forEach(b =>
      b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tabpage").forEach(p =>
      p.classList.toggle("active", p.id === "tab-" + name));
    if (name === "view3d") requestDraw();
    if (name === "node") { renderNode(); renderFinder(); }
    if (name === "owned") renderOwned();
    if (name === "tickets") renderTickets();
    if (name === "trees") renderTrees();
  }

  // ---- trees tab ---------------------------------------------------------
  function uid() {
    return Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
  }
  // Staleness is about the content, not just the recorded version: a tree can
  // be frozen from older data while its record still answers to the current
  // key (contentDataVersion), or predate versioning entirely (no dataVersion).
  // Static (imported/exported) trees carry their entries baked in, so they are
  // judged by the version recorded at export time — an external snapshot with
  // no version at all is left alone.
  function treeMismatch(t) {
    if (!DATA.dataVersion) return false;
    if (t.static) return !!t.dataVersion && t.dataVersion !== DATA.dataVersion;
    const content = t.contentDataVersion || null;
    if (content) return content !== DATA.dataVersion;
    if (t.dataVersion) return t.dataVersion !== DATA.dataVersion;
    return true;                     // no provenance recorded: assume old
  }
  function staleLabel(t) {
    const from = t.contentDataVersion || t.dataVersion || "unknown";
    return `data v${from}≠v${DATA.dataVersion}`;
  }
  // Entries a static snapshot references that the current data no longer has:
  // the most direct evidence that a snapshot predates the loaded data, and it
  // works even when the file carries no version at all.
  function staticMissing(t) {
    if (!t.static) return 0;
    const p = loadStatic(t.id);
    if (!p || !p.nodes || !p.nodes.length) return 0;
    const key = nd => nd.file + "\u0000" + nd.name;
    if (!DATA._entryKeys) DATA._entryKeys = new Set((DATA.entries || []).map(key));
    let n = 0;
    for (const nd of p.nodes) if (nd.id !== 0 && !DATA._entryKeys.has(key(nd))) n++;
    return n;
  }
  function renderTrees() {
    const ul = $("treeList");
    if (isShared()) {
      $("verWarn").style.display = "none";
      $("treeCount").textContent = "Shared view (read-only)";
      ul.innerHTML = "";
      const t = activeTree();
      if (t) {
        const st = DB.states[t.id];
        const li = document.createElement("li");
        li.innerHTML = `<div class="grow"><b>${esc(t.name)}</b><br>` +
          `<span class="muted small">shared view${st ? ` · ${st.unlocked.length} unlocked · ${E.fmt(st.points)} pts · ${st.cores} cores` : ""}</span></div>`;
        ul.appendChild(li);
      }
      return;
    }
    const at = activeTree();
    $("treeCount").textContent = DB.trees.length
      ? `${DB.trees.length} tree${DB.trees.length > 1 ? "s" : ""} · active: ${at ? at.name : "none"}`
      : "No trees yet: generate one below.";
    const warn = $("verWarn");
    const missCount = at ? staticMissing(at) : 0;
    if (at && (treeMismatch(at) || missCount)) {
      warn.style.display = "block";
      $("verWarnText").textContent =
        `"${at.name}" was built from data v${at.contentDataVersion || at.dataVersion || "an older version"}, current data is ` +
        `v${DATA.dataVersion}, so it keeps the entries it was built from (regenerating would silently reassign entries and links ` +
        `under your progress). ` +
        `Use Upgrade to keep your unlocked and visible nodes and resample the unseen ones from the current data` +
        (at.static ? `; this tree is an imported snapshot, so new entries and tags only enter it that way.`
                   : `, or generate a fresh tree below.`) +
        (missCount ? ` ${missCount} of its entries no longer exist in the current data.` : "") +
        ` Export a backup first if its progress matters.`;
    } else warn.style.display = "none";
    ul.innerHTML = "";
    for (const t of DB.trees) {
      const st = DB.states[t.id];
      const li = document.createElement("li");
      li.style.flexWrap = "wrap";
      const missing = staticMissing(t);
      const mis = treeMismatch(t) || !!missing;
      li.innerHTML =
        `<div class="grow"><b>${esc(t.name)}</b>` +
        (mis ? ` <span class="pill" style="border-color:var(--bad);color:var(--bad)">⚠ ${esc(t.dataVersion && treeMismatch(t) ? staleLabel(t) : `${missing} stale entr${missing === 1 ? "y" : "ies"}`)}</span>` : "") +
        `<br>` +
        `<span class="muted small">${t.static ? "imported file" : "seed " + esc(String(t.seed)) + (t.limit ? " · " + t.limit + " entries" : " · full")}` +
        (t.dataVersion ? " · data v" + esc(t.dataVersion) : "") +
        `${st ? " · " + st.unlocked.length + " unlocked · " + E.fmt(st.points) + " pts · " + st.cores + " cores" : ""}</span></div>`;
      const actions = document.createElement("div");
      actions.className = "row";
      actions.style.cssText = "width:100%;margin-top:6px";
      const open = document.createElement("button");
      open.textContent = t.id === DB.activeId ? "Active ✓" : "Open";
      open.disabled = t.id === DB.activeId;
      open.addEventListener("click", async () => {
        DB.activeId = t.id; selectedId = 0; saveDB(); renderTrees(); refreshAll();
        try { await getRuntime(t); showTab("view3d"); }
        catch (e) { err(e); }
      });
      const ren = document.createElement("button");
      ren.textContent = "✎";
      ren.title = "Rename";
      ren.addEventListener("click", () => {
        const name = prompt("Rename tree:", t.name);
        if (name && name.trim()) { t.name = name.trim().slice(0, 60); saveDB(); renderTrees(); }
      });
      const del = document.createElement("button");
      del.textContent = "🗑"; del.className = "danger"; del.title = "Delete";
      del.addEventListener("click", () => {
        if (!confirm(`Delete "${t.name}" and its saved progress?`)) return;
        DB.trees = DB.trees.filter(x => x.id !== t.id);
        delete DB.states[t.id];
        try { localStorage.removeItem(LS_STATIC + "." + t.id); } catch (e) {}
        try { localStorage.removeItem(LS_GEN + "." + t.id); } catch (e) {}
        memoryStatic.delete(t.id); memoryGen.delete(t.id); dropRuntime(t.id);
        if (DB.activeId === t.id) DB.activeId = DB.trees.length ? DB.trees[0].id : null;
        selectedId = 0;
        saveDB(); renderTrees(); refreshAll();
      });
      const copy = document.createElement("button");
      copy.textContent = "📋 Copy"; copy.title = "Copy tree with its progress";
      copy.addEventListener("click", () => {
        try {
          const nt = duplicateTree(t, false);
          toast(`Copied as "${nt.name}".`);
        } catch (e) { err(e); }
      });
      const fresh = document.createElement("button");
      fresh.textContent = "🌱 Fresh"; fresh.title = "Fresh copy: same parameters, new progress";
      fresh.addEventListener("click", () => {
        try {
          const nt = duplicateTree(t, true);
          toast(`Fresh copy "${nt.name}" started.`);
        } catch (e) { err(e); }
      });
      const up = document.createElement("button");
      up.textContent = "⬆ Upgrade";
      up.dataset.treeId = t.id;
      up.title = "Copy with progress: keep unlocked + visible entries, regenerate the unseen from current data (full trees also grow)";
      up.addEventListener("click", async () => {
        try {
          const { absent, precheck } = absentSources(t);
          if (!absent.length) { await upgradeTree(t, []); return; }
          const open = li.querySelector(".upPicker");
          if (open) { open.remove(); return; }
          document.querySelectorAll(".upPicker").forEach(el => el.remove());
          const counts = {};
          for (const e of (DATA.entries || [])) {
            if (e.t === "tree" || !e.s) continue;
            counts[e.s] = (counts[e.s] || 0) + 1;
          }
          const box = document.createElement("div");
          box.className = "upPicker";
          box.style.cssText = "width:100%;margin-top:6px;border-top:1px solid var(--line);padding-top:6px";
          const head = document.createElement("div");
          head.className = "muted small";
          head.textContent = absent.length +
            " sources aren't in this tree's filter, check the ones to include in the upgrade" +
            (precheck.size ? " (new ones pre-checked with · new; old exclusions stay out unless checked)."
              : " (nothing pre-checked: this tree can't tell new sources from old exclusions).");
          const list = document.createElement("div");
          list.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;max-height:160px;overflow:auto;margin:6px 0";
          const boxes = [];
          for (const s of absent) {
            const lab = document.createElement("label");
            lab.style.cssText = "display:flex;gap:6px;align-items:center;min-height:36px;flex:1;min-width:44%";
            const cb = document.createElement("input");
            cb.type = "checkbox"; cb.value = s;
            cb.checked = precheck.has(s);
            cb.style.cssText = "width:20px;height:20px";
            const nm = document.createElement("span");
            nm.className = "small";
            nm.textContent = `${s}${counts[s] ? ` [${counts[s]}]` : ""}${precheck.has(s) ? " · new" : ""}`;
            lab.append(cb, nm);
            list.appendChild(lab);
            boxes.push(cb);
          }
          const row = document.createElement("div");
          row.className = "row";
          const go = document.createElement("button");
          go.textContent = "⬆ Upgrade selected";
          go.className = "primary";
          go.addEventListener("click", async () => {
            try {
              await upgradeTree(t, boxes.filter(b => b.checked).map(b => b.value));
            } catch (e) { err(e); }
          });
          const no = document.createElement("button");
          no.textContent = "Cancel";
          no.addEventListener("click", () => box.remove());
          row.append(go, no);
          box.append(head, list, row);
          li.appendChild(box);
        } catch (e) { err(e); }
      });
      actions.append(open, ren, copy, fresh, up, del);
      if (!t.static) {
        const use = document.createElement("button");
        use.textContent = "⚙ Use options";
        use.title = "Load this tree's generator options into the form to tweak and regenerate";
        use.addEventListener("click", () => {
          writeGenForm(t);
          toast(`Options from "${t.name}" loaded: tweak and Generate.`);
        });
        actions.append(use);
      }
      li.appendChild(actions);
      ul.appendChild(li);
    }
    updateProgress();
  }

  async function updateProgress() {
    const box = $("progCard");
    const t = activeTree();
    if (!t) { box.style.display = "none"; return; }
    const myId = t.id;
    let rt;
    try { rt = await getRuntime(t); } catch (e) { box.style.display = "none"; return; }
    if (DB.activeId !== myId) return; // switched away mid-flight
    const st = activeState();
    const total = rt.nodes.length, have = st.unlocked.length;
    const pct = Math.round(have / Math.max(1, total) * 100);
    $("progHead").textContent = `${have}/${total} (${pct}%): ${t.name}`;
    $("progBar").style.width = pct + "%";
    const byFile = {}, byClass = {};
    for (const id of st.unlocked) {
      const nd = rt.byId[id];
      if (!nd) continue;
      byFile[nd.file] = (byFile[nd.file] || 0) + 1;
      const cn = classOf(nd.rarity).name;
      byClass[cn] = (byClass[cn] || 0) + 1;
    }
    const escJoin = ent => ent.map(([k, v]) => `${k} ${v}`).join(" · ");
    $("progBody").textContent = escJoin(Object.entries(byFile)) + ", " + escJoin(Object.entries(byClass));
    box.style.display = "block";
  }

  // Copy keeps the definition and duplicates progress; fresh keeps the
  // definition (seed/params/topology) but restarts progress. Generated
  // fresh copies record the current data version since they regenerate.
  function duplicateTree(t, fresh) {
    const nid = uid();
    const nt = {
      id: nid,
      name: (t.name + (fresh ? " (fresh)" : " (copy)")).slice(0, 60),
      seed: t.seed, params: JSON.parse(JSON.stringify(t.params || {})),
      limit: t.limit || null, filters: JSON.parse(JSON.stringify(t.filters || {})),
      knownSources: t.knownSources ? t.knownSources.slice() : undefined,
      static: !!t.static, createdAt: Date.now(),
      dataVersion: fresh && !t.static ? (DATA.dataVersion || null) : (t.dataVersion || null)
    };
    if (t.static) {
      const p = loadStatic(t.id);
      if (!p) throw new Error("static tree data missing (re-import the file)");
      saveStatic(nid, p);
    } else {
      const hit = loadGenerated(t.id);
      const nk = genCacheKey(nt);
      if (hit && nk && hit.key === nk) saveGenerated(nid, nk, hit.res);
    }
    DB.trees.push(nt);
    DB.states[nid] = fresh ? E.newState()
      : JSON.parse(JSON.stringify(DB.states[t.id] || E.newState()));
    DB.activeId = nid;
    selectedId = 0;
    saveDB(); renderTrees(); refreshAll();
    return nt;
  }
  // Upgrade: like Copy, but the copy's unseen nodes are resampled from the
  // current data version while unlocked + visible entries — and the whole
  // inventory, wallet, and history — carry over. Full (unlimited) trees
  // also grow: pool entries missing from the tree are appended as new
  // nodes. Positions and links bake in as displayed, so recorded
  // swaps/links/entry-swaps are dropped from the copied state. The result
  // is stored as a static (custom) tree stamped with the current data version.
  // Sources absent from a tree's filter, with the ones pre-checked that
  // should be added on upgrade. New sources default to included (matching
  // the New-Tree checkboxes); knownSources distinguishes them from
  // deliberately excluded ones, which stay unchecked. Trees predating
  // knownSources can't distinguish, so nothing is pre-checked.
  function absentSources(t) {
    const currentSources = allSources();
    const stored = new Set(((t.filters || {}).sources || []));
    if (!stored.size) return { absent: [], precheck: new Set() };
    const known = new Set(t.knownSources || []);
    const absent = currentSources.filter(s => !stored.has(s));
    const precheck = new Set(
      t.knownSources ? absent.filter(s => !known.has(s)) : []);
    return { absent, precheck };
  }
  async function upgradeTree(t, extraSources) {
    const rt = await getRuntime(t);
    const st = DB.states[t.id] || E.newState();
    const currentSources = allSources();
    const stored = new Set(((t.filters || {}).sources || []));
    const hasFilter = stored.size > 0;
    let filters = Object.assign({}, t.filters || {});
    const extra = (extraSources || []).filter(s => !stored.has(s));
    if (hasFilter && extra.length) filters.sources = [...stored, ...extra];
    const m = E.viewState(rt, st);
    const keep = new Set(st.unlocked || []);
    for (const id of E.visible(rt, st.unlocked, m)) keep.add(id);
    const pool = G.filterEntries(DATA.entries, filters);
    if (!pool.length) throw new Error("no entries match this tree's filters in the current data");
    const key = e => e.f + "#" + e.n;
    const used = new Set();
    for (const nd of rt.nodes) if (keep.has(nd.id)) used.add(nd.file + "#" + nd.number);
    const byKey = new Map(), byFile = new Map();
    for (const e of pool) {
      const k = e.f + "|" + classOf(e.r).name;
      if (!byKey.has(k)) byKey.set(k, []);
      byKey.get(k).push(e);
      if (!byFile.has(e.f)) byFile.set(e.f, []);
      byFile.get(e.f).push(e);
    }
    const pickFor = nd => {
      const lists = [byKey.get(nd.file + "|" + classOf(nd.rarity).name) || [],
        byFile.get(nd.file) || []];
      for (const list of lists) {
        const cands = list.filter(e => !used.has(key(e)));
        if (cands.length) return cands[Math.floor(Math.random() * cands.length)];
      }
      return null;
    };
    const stampFlags = (node, src) => {
      delete node.nsfw; delete node.noncon; delete node.tech;
      if (src.nsfw) node.nsfw = true;
      if (src.noncon) node.noncon = true;
      if (src.tech) node.tech = true;
      return node;
    };
    let refreshed = 0;
    const nodes = rt.nodes.map(nd => {
      const base = {
        id: nd.id, file: nd.file, number: nd.number, name: nd.name,
        rarity: nd.rarity, source: nd.source, tag: nd.tag,
        description: nd.description, meta: (nd.meta || []).slice(),
        tags: (nd.tags || nd.tg || []).slice(),
        pos: (nd.pos || [0, 0, 0]).slice(), r: nd.r
      };
      if (keep.has(nd.id)) return stampFlags(base, nd);
      const e = pickFor(nd);
      if (!e) return stampFlags(base, nd);
      used.add(key(e));
      refreshed++;
      return stampFlags(Object.assign(base, {
        file: e.f, number: e.n, name: e.name, rarity: e.r,
        source: e.s, tag: e.t, description: e.d,
        meta: (e.m || []).slice(), tags: (e.tags || e.tg || []).slice()
      }), e);
    });
    const edges = [];
    const byId = {};
    for (const nd of nodes) byId[nd.id] = nd;
    const distp = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
    for (const aStr of Object.keys(rt.adj)) {
      const a = Number(aStr);
      for (const b of rt.adj[aStr]) {
        if (b > a && byId[a] && byId[b]) {
          edges.push({ a, b, d: Math.round(distp(byId[a].pos, byId[b].pos) * 1e6) / 1e6 });
        }
      }
    }
    // Growth for full (unlimited) trees: the current pool may hold entries
    // the old tree never sampled. Append one node per missing entry so the
    // upgraded tree is complete again. Existing nodes and edges are never
    // touched — unlocked connections, frontier included, stay exactly as
    // displayed. New nodes take shell-appropriate positions (a few tries
    // each, keeping the least crowded), then link to nearest neighbours.
    let added = 0;
    if (!t.limit) {
      const P = Object.assign({}, G.DEFAULTS, rt.params || {});
      const radius = P.radius || 10;
      const inner = P.innerFraction != null ? P.innerFraction : 0.12;
      const prs = pool.map(e => e.r);
      const rmin = Math.min(...prs), span = (Math.max(...prs) - rmin) || 1.0;
      const maxd = (P.maxLinkDistance || 0.6) * radius;
      const kMax = Math.max(1, Math.round(P.meanDegree || 2.5));
      let nextId = nodes.reduce((mm, nd) => Math.max(mm, nd.id), 0) + 1;
      const place = radial => {
        let best = null, bestD = -1;
        for (let i = 0; i < 8; i++) {
          const z = Math.random() * 2 - 1, th = Math.random() * 2 * Math.PI;
          const rr = Math.sqrt(Math.max(0, 1 - z * z));
          const p = [radial * rr * Math.cos(th), radial * rr * Math.sin(th), radial * z];
          let md = Infinity;
          for (const nd of nodes) { const d = distp(p, nd.pos); if (d < md) md = d; }
          if (md > bestD) { bestD = md; best = p; }
        }
        return best.map(c => Math.round(c * 1e6) / 1e6);
      };
      const freshIds = [];
      for (const e of pool) {
        if (used.has(key(e))) continue;
        used.add(key(e));
        const t = (e.r - rmin) / span;
        const radial = Math.max(radius * 0.05, Math.min(radius, radius * (inner + (1 - inner) * t)));
        const nd = { id: nextId++, file: e.f, number: e.n, name: e.name,
          rarity: e.r, source: e.s, tag: e.t, description: e.d,
          meta: (e.m || []).slice(), tags: (e.tags || e.tg || []).slice(),
          pos: place(radial), r: Math.round(radial * 1e6) / 1e6 };
        if (e.nsfw) nd.nsfw = true;
        if (e.noncon) nd.noncon = true;
        if (e.tech) nd.tech = true;
        nodes.push(nd);
        byId[nd.id] = nd;
        freshIds.push(nd.id);
        added++;
      }
      for (const id of freshIds) {
        const nd = byId[id];
        const cands = nodes
          .filter(o => o.id !== id)
          .map(o => [distp(nd.pos, o.pos), o.id])
          .sort((x, y) => x[0] - y[0]);
        let linked = 0;
        for (const [d, oid] of cands) {
          if (linked >= kMax) break;
          if (d > maxd && linked > 0) break;
          edges.push({ a: Math.min(id, oid), b: Math.max(id, oid),
            d: Math.round(d * 1e6) / 1e6 });
          linked++;
        }
        if (!linked && cands.length) {
          const [d, oid] = cands[0];
          edges.push({ a: Math.min(id, oid), b: Math.max(id, oid),
            d: Math.round(d * 1e6) / 1e6 });
        }
      }
    }
    const nid = uid();
    saveStatic(nid, { nodes, edges });
    const nst = JSON.parse(JSON.stringify(st));
    delete nst.swaps; delete nst.added_links; delete nst.entry_swaps;
    const nt = {
      id: nid, name: (t.name + " (upgraded)").slice(0, 60),
      seed: t.seed, params: JSON.parse(JSON.stringify(t.params || {})),
      limit: t.limit || null, filters: JSON.parse(JSON.stringify(filters)),
      knownSources: currentSources.slice(),
      static: true, createdAt: Date.now(), dataVersion: DATA.dataVersion || null
    };
    DB.trees.push(nt);
    DB.states[nid] = nst;
    DB.activeId = nid;
    selectedId = 0;
    saveDB(); renderTrees(); refreshAll();
    const hidden = nodes.length - keep.size - added;
    toast(`Upgraded as "${nt.name}": kept ${keep.size}, refreshed ${refreshed} of ${hidden} unseen` +
      (added ? `, +${added} new` : "") + ".");
    return nt;
  }
  // Inverse of readGenForm: load a saved (generated, non-static) tree's
  // options into the New Tree form for tweaking. Missing fields fall back
  // to the form defaults, mirroring readGenForm.
  function writeGenForm(t) {
    const P = t.params || {}, F = t.filters || {};
    const set = (id, v) => { if ($(id)) $(id).value = v; };
    const check = (id, v) => { if ($(id)) $(id).checked = !!v; };
    const num = (v, def) => (v == null || isNaN(parseFloat(v))) ? def : v;
    $("newName").value = ((t.name || "Untitled tree") + " (tweak)").slice(0, 60);
    set("newSeed", t.seed != null ? t.seed : "");
    set("newSize", t.limit != null ? t.limit : "");
    set("newDegree", num(P.meanDegree, 2.5));
    set("newRejoin", num(P.rejoinBias, 0.7));
    set("newRoots", num(P.rootLinks, 3));
    set("newRadius", num(P.radius, 10.0));
    set("newVar", num(P.distanceVariance, 0.05));
    set("newCluster", num(P.clustering, 0.3));
    set("newClusters", num(P.clusters, 3));
    if ($("newDegDist") && P.degreeDist) $("newDegDist").value = P.degreeDist;
    set("newDegMin", (P.degreeMin != null && P.degreeMin !== 0) ? P.degreeMin : "");
    set("newDegMax", P.degreeMax != null ? P.degreeMax : "");
    set("newFalloff", num(P.linkFalloff, 4.0));
    set("newMaxDist", num(P.maxLinkDistance, 0.6));
    set("newLocalDist", num(P.localLinkDistance, 0.25));
    check("newConnect", P.connect !== false);
    const files = Array.isArray(F.files) ? F.files : [];
    document.querySelectorAll(".fFile").forEach(c => { c.checked = files.includes(c.value); });
    set("newRmin", (F.rarityMin != null) ? F.rarityMin : "");
    set("newRmax", (F.rarityMax != null) ? F.rarityMax : "");
    if ($("newTag")) {
      const tag = F.tag || (Array.isArray(F.tags) && F.tags[0]) || "";
      if ([...$("newTag").options].some(o => o.value === tag)) $("newTag").value = tag;
      else $("newTag").value = "";
    }
    const srcs = Array.isArray(F.sources) ? F.sources : null;
    document.querySelectorAll(".srcCheck").forEach(c => {
      if (srcs == null || !srcs.length) c.checked = true;
      else c.checked = srcs.includes(c.value);
    });
    check("newGachaOnly", F.includeGachaOnly);
    check("newNsfw", F.includeNsfw);
    check("newNoncon", F.includeNoncon);
    updateNonconRows();
  }
  function readGenForm() {
    const num = (id, def) => {
      const v = parseFloat($(id).value);
      return isNaN(v) ? def : v;
    };
    const files = [...document.querySelectorAll(".fFile")]
      .filter(c => c.checked).map(c => c.value);
    const srcs = [...document.querySelectorAll(".srcCheck")]
      .filter(c => c.checked).map(c => c.value);
    const tag = ($("newTag") && $("newTag").value) || "";
    return {
      name: ($("newName").value.trim() || "Untitled tree").slice(0, 60),
      seed: parseInt($("newSeed").value, 10) || Math.floor(Math.random() * 1e9),
      limit: $("newSize").value ? parseInt($("newSize").value, 10) : null,
      params: {
        meanDegree: num("newDegree", 2.5),
        rejoinBias: Math.max(0, Math.min(1, num("newRejoin", 0.7))),
        rootLinks: Math.max(1, Math.min(8, parseInt($("newRoots").value, 10) || 3)),
        radius: num("newRadius", 10.0),
        distanceVariance: num("newVar", 0.05),
        clustering: num("newCluster", 0.3),
        clusters: Math.max(1, parseInt($("newClusters").value, 10) || 3),
        degreeDist: $("newDegDist").value || "poisson",
        degreeMin: Math.max(0, parseInt($("newDegMin").value, 10) || 0),
        degreeMax: $("newDegMax").value === "" ? null : Math.max(1, parseInt($("newDegMax").value, 10)),
        linkFalloff: num("newFalloff", 4.0),
        maxLinkDistance: num("newMaxDist", 0.6),
        localLinkDistance: num("newLocalDist", 0.25),
        connect: !!$("newConnect").checked
      },
      filters: {
        files,
        rarityMin: $("newRmin").value === "" ? null : num("newRmin", null),
        rarityMax: $("newRmax").value === "" ? null : num("newRmax", null),
        sources: srcs,
        includeGachaOnly: !!$("newGachaOnly").checked,
        includeNsfw: !!$("newNsfw").checked,
        includeNoncon: !!($("newNoncon") && $("newNoncon").checked),
        ...(tag ? { tag } : {})
      },
      knownSources: allSources()
    };
  }

  // Live preview: render the form's settings into the 3D view without
  // saving. Tune + re-preview freely, then Generate to keep it.
  let preview = null; // {rt, stats}
  function previewStats(rt) {
    const degs = rt.nodes.map(nd => (rt.adj[nd.id] || new Set()).size);
    const lens = rt.edges.map(e => e.d);
    const seen = new Set();
    let comps = 0;
    for (const nd of rt.nodes) {
      if (seen.has(nd.id)) continue;
      comps++;
      const q = [nd.id];
      seen.add(nd.id);
      while (q.length) {
        for (const b of (rt.adj[q.pop()] || [])) {
          if (!seen.has(b)) { seen.add(b); q.push(b); }
        }
      }
    }
    const mean = a => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length);
    return {
      nodes: rt.nodes.length, edges: rt.edges.length, comps,
      degMean: mean(degs).toFixed(2), degMax: Math.max(...degs),
      linkMean: mean(lens).toFixed(3), linkMax: Math.max(...lens).toFixed(3),
      roots: (rt.adj[0] || new Set()).size
    };
  }

  $("btnCreate").addEventListener("click", async () => {
    const form = readGenForm();
    const btn = $("btnCreate");
    btn.disabled = true;
    $("genProg").style.display = "block";
    const bar = $("genProg").firstElementChild;
    try {
      const res = await G.generate(DATA.entries, form.seed, form.params,
        { limit: form.limit, ...form.filters }, (frac, label) => {
          bar.style.width = Math.round(frac * 100) + "%";
          $("genMsg").textContent = `${label}… ${Math.round(frac * 100)}%`;
        });
      const tree = {
        id: uid(), name: form.name, seed: form.seed, params: form.params,
        limit: form.limit, filters: form.filters,
        knownSources: form.knownSources || allSources(),
        createdAt: Date.now(), dataVersion: DATA.dataVersion || null
      };
      DB.trees.push(tree);
      DB.states[tree.id] = E.newState();
      DB.activeId = tree.id;
      dropRuntime(tree.id);
      runtimes.set(tree.id, G.buildRuntime(res));
      saveGenerated(tree.id, genCacheKey(tree), res);
      saveDB(); renderTrees(); refreshAll();
      $("genMsg").textContent = `Generated ${res.nodes.length} nodes.`;
      exitPreview();
      showTab("view3d");
    } catch (e) { err(e); }
    btn.disabled = false;
    setTimeout(() => { $("genProg").style.display = "none"; }, 1200);
  });

  $("btnPreview").addEventListener("click", async () => {
    const form = readGenForm();
    const btn = $("btnPreview");
    btn.disabled = true;
    $("genProg").style.display = "block";
    const bar = $("genProg").firstElementChild;
    try {
      const res = await G.generate(DATA.entries, form.seed, form.params,
        { limit: form.limit, ...form.filters }, (frac, label) => {
          bar.style.width = Math.round(frac * 100) + "%";
          $("genMsg").textContent = `Preview: ${label}… ${Math.round(frac * 100)}%`;
        });
      const rt = G.buildRuntime(res);
      const s = previewStats(rt);
      preview = { rt };
      $("previewStats").textContent =
        `${s.nodes} nodes · ${s.edges} edges · ${s.comps} component${s.comps === 1 ? "" : "s"} · ` +
        `degree ⌀${s.degMean} max ${s.degMax} · link ⌀${s.linkMean} max ${s.linkMax} · ${s.roots} root links`;
      $("previewBar").style.display = "block";
      $("genMsg").textContent = `Preview ready: ${s.nodes} nodes.`;
      lastFitKey = "";
      showTab("view3d");
    } catch (e) { err(e); }
    btn.disabled = false;
    setTimeout(() => { $("genProg").style.display = "none"; }, 1200);
  });
  $("btnPreviewCreate").addEventListener("click", () => $("btnCreate").click());
  $("btnPreviewExit").addEventListener("click", () => exitPreview());
  function exitPreview() {
    if (!preview) return;
    preview = null;
    selectedId = 0;
    $("previewBar").style.display = "none";
    lastFitKey = "";
    refreshAll();
  }
  $("btnExport").addEventListener("click", () => {
    const t = activeTree();
    if (!t) return toast("No active tree to export.", true);
    const payload = {
      app: "chaos-tree", v: 1, exportedAt: new Date().toISOString(),
      tree: { name: t.name, seed: t.seed, params: t.params || {}, limit: t.limit || null,
              filters: t.filters || {}, dataVersion: t.dataVersion || null,
              static: !!t.static, topology: t.static ? loadStatic(t.id) : null },
      state: DB.states[t.id] || E.newState()
    };
    const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = t.name.replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-").toLowerCase() + ".chaos-tree.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });
  $("btnImport").addEventListener("click", () => $("fileImport").click());
  $("fileImport").addEventListener("change", async () => {
    const f = $("fileImport").files[0];
    if (!f) return;
    try {
      const payload = JSON.parse(await f.text());
      if (payload && payload.app === "chaos-tree" && payload.tree) {
        const td = payload.tree;
        const tree = { id: uid(), name: String(td.name || f.name).slice(0, 60),
          seed: td.seed != null ? td.seed : Math.floor(Math.random() * 1e9),
          params: td.params || {}, limit: td.limit || null,
          filters: td.filters || {}, dataVersion: td.dataVersion || null,
          static: !!td.static, createdAt: Date.now() };
        if (td.static && td.topology) saveStatic(tree.id, td.topology);
        DB.trees.push(tree);
        DB.states[tree.id] = Object.assign(E.newState(), payload.state || {});
        DB.activeId = tree.id; selectedId = 0; saveDB(); renderTrees(); refreshAll();
        toast(`Imported "${tree.name}".`);
        showTab("view3d");
      } else if (payload && payload.format === "chaos-tree" && payload.nodes && payload.edges) {
        const tree = { id: uid(), name: f.name.replace(/\.json$/i, "").slice(0, 60),
          seed: payload.seed != null ? payload.seed : 0, params: {}, limit: null,
          dataVersion: null, static: true, createdAt: Date.now() };
        saveStatic(tree.id, { nodes: payload.nodes, edges: payload.edges });
        DB.trees.push(tree);
        DB.states[tree.id] = E.newState();
        DB.activeId = tree.id; selectedId = 0; saveDB(); renderTrees(); refreshAll();
        toast(`Imported Python tree "${tree.name}".`);
        showTab("view3d");
      } else throw new Error("unrecognised file (need a chaos-tree export or Python tree JSON)");
    } catch (e) { err(e); }
    $("fileImport").value = "";
  });

  // ---- selection + refresh -------------------------------------------------
  let selectedId = null;
  async function current() {
    const t = activeTree();
    if (!t) return null;
    try {
      const rt = await getRuntime(t);
      return { tree: t, rt, st: activeState() };
    } catch (e) { err(e); return null; }
  }
  async function refreshAll() {
    renderTrees();
    applyInvVisibility();
    if (currentTab === "view3d") requestDraw();
    if (currentTab === "node") await renderNode();
    if (currentTab === "owned") await renderOwned();
    if (currentTab === "tickets") await renderTickets();
    updateViewInfo();
  }
  async function mutate(fn) {
    if (isShared()) { toast("Shared views are read-only.", true); return null; }
    const c = await current();
    if (!c) return null;
    try {
      const out = fn(c);
      saveDB();
      await refreshAll();
      return out === undefined ? true : out;
    } catch (e) { err(e); return null; }
  }

  // ---- 3D view ---------------------------------------------------------------
  const PROJ_F = 3.0; // perspective focal length
  // View-space depth cutoff: the camera flies inside the cloud, so nodes at
  // or behind the camera plane would project mirrored and hugely magnified
  // (scale explodes as depth approaches -PROJ_F). Skip them instead.
  const NEAR = 0.5;
  const cam = { yaw: 0.6, pitch: 0.35, dist: 3.2, zoom: 1 };
  const canvas = $("view3d");
  const ctx = canvas.getContext("2d");
  let projected = []; // [{id,x,y,r,name,hex}]
  let showEdges = true;
  let showRadial = true; // r = radial distance, occasionally useful for debugging
  // A locked node is unlockable right now when it sits on the frontier
  // (normal unlocks are adjacency-only) and the wallet covers it.
  // Pass a precomputed frontier set when checking many nodes per frame,
  // and a costContext (E.costContext) so costs stay O(1) per node.
  function canUnlockNow(st, rt, nid, front, ccx) {
    if (nid === 0 || st.unlocked.includes(nid)) return false;
    if (!(front || E.frontier(rt, st.unlocked)).has(nid)) return false;
    if ((st.cores || 0) < E.coreCostFor(st, rt, nid, ccx)) return false;
    const cost = E.nodeCostFor(st, rt, nid, ccx);
    return st.points >= cost - E.couponCover(st, cost);
  }
  function hexPath(c, x, y, r) {
    c.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = -Math.PI / 2 + (Math.PI / 3) * i;
      const px = x + r * Math.cos(a), py = y + r * Math.sin(a);
      if (i) c.lineTo(px, py); else c.moveTo(px, py);
    }
    c.closePath();
  }
  let lastFitKey = "";
  // Frame the shown nodes: with only the root + one neighbour unlocked the
  // sphere is mostly empty, so magnify (zoom) in; as the tree fills out,
  // ease back to ~full-sphere framing. Runs only when the shown set changes,
  // so manual zoom/rotate is never overridden mid-session.
  function maybeAutoFit(d) {
    const key = d.tree.id + ":" + d.st.unlocked.length + ":" + d.vis.size + ":" +
      (d.st.swaps || []).length + ":" + (d.st.added_links || []).length;
    if (key === lastFitKey) return;
    lastFitKey = key;
    const shown = [];
    let maxR = 0.12;
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const nd of d.rt.nodes) {
      if (!d.vis.has(nd.id) && !d.unl.has(nd.id)) continue;
      const p = nd.pos;
      shown.push(p);
      const r = Math.hypot(p[0], p[1], p[2]);
      if (r > maxR) maxR = r;
      if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0];
      if (p[1] < y0) y0 = p[1]; if (p[1] > y1) y1 = p[1];
      if (p[2] < z0) z0 = p[2]; if (p[2] > z1) z1 = p[2];
    }
    cam.dist = Math.max(1.05, Math.min(4.2, 1.05 + maxR * 2.15));
    const proj = PROJ_F / (PROJ_F + cam.dist); // scale at origin
    // zoom so the shown cloud's diameter fills ~60% of the smaller side
    const spreadWorld = Math.max(0.04, Math.hypot(x1 - x0, y1 - y0, z1 - z0));
    cam.zoom = Math.max(0.05, Math.min(15, 1.476 / (spreadWorld * proj)));
    // With only a few nodes out, the default angle can stack them along the
    // view axis (one hidden dot). Pick an angle that spreads them on screen
    // (full perspective projection, so foreshortening counts).
    if (shown.length > 1 && shown.length <= 8) {
      const spread = (yw, pt) => {
        const cy = Math.cos(yw), sy = Math.sin(yw);
        const cp = Math.cos(pt), sp = Math.sin(pt);
        let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
        for (const p of shown) {
          const x = p[0] * cy - p[2] * sy, z = p[0] * sy + p[2] * cy;
          const y2 = p[1] * cp - z * sp, z2 = p[1] * sp + z * cp;
          const s = PROJ_F / (PROJ_F + z2 + cam.dist);
          const sx = x * s, syy = y2 * s;
          if (sx < x0) x0 = sx; if (sx > x1) x1 = sx;
          if (syy < y0) y0 = syy; if (syy > y1) y1 = syy;
        }
        return Math.hypot(x1 - x0, y1 - y0);
      };
      let best = null;
      for (let i = 0; i < 8; i++) {
        for (const pt of [0.2, 0.55, 0.95]) {
          const yw = (i / 8) * Math.PI * 2;
          const sp = spread(yw, pt);
          if (!best || sp > best[0]) best = [sp, yw, pt];
        }
      }
      if (best && best[0] > 1e-6) { cam.yaw = best[1]; cam.pitch = best[2]; }
    }
  }
  window.__treeDebug = { cam, getProjected: () => projected, stackTickets, ticketLabel };
  function fitCanvas() {
    const r = canvas.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
  }
  window.addEventListener("resize", () => { fitCanvas(); requestDraw(); });

  // Coalesce redraw requests onto one frame: drag/zoom handlers fire far
  // more often than the display refreshes, and each full redraw walks the
  // whole tree, so uncoalesced draws queue up and tank the framerate.
  // A request arriving mid-draw sets a dirty flag for one follow-up frame.
  let drawQueued = false, drawDirty = false, drawing = false;
  function requestDraw() {
    if (currentTab !== "view3d") return;
    if (drawing || drawQueued) { drawDirty = true; return; }
    drawQueued = true;
    requestAnimationFrame(async () => {
      drawQueued = false;
      if (currentTab !== "view3d") return;
      drawing = true;
      try { await draw3D(); } finally { drawing = false; }
      if (drawDirty && currentTab === "view3d") {
        drawDirty = false;
        requestDraw();
      } else drawDirty = false;
    });
  }

  function project(p) {
    const { yaw, pitch, dist } = cam;
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    let x = p[0] * cy - p[2] * sy, z = p[0] * sy + p[2] * cy, y = p[1];
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const y2 = y * cp - z * sp, z2 = y * sp + z * cp;
    const depth = z2 + dist;
    if (depth < NEAR) return null;
    const scale = PROJ_F / (PROJ_F + depth);
    return [x * scale, y2 * scale, scale];
  }

  async function viewData() {
    if (preview) {
      const all = new Set(preview.rt.nodes.map(n => n.id));
      return {
        tree: { name: "Preview", id: "preview" }, rt: preview.rt,
        st: E.newState(), meta: {}, vis: all, unl: new Set(), isPreview: true
      };
    }
    const c = await current();
    if (!c) return null;
    const meta = E.viewState(c.rt, c.st);
    if (c.rt.frozen) return { ...c, meta, vis: c.rt.frozen.vis, unl: c.rt.frozen.unl };
    const vis = new Set(E.visible(c.rt, c.st.unlocked, meta));
    const unl = new Set(c.st.unlocked);
    return { ...c, meta, vis, unl };
  }
  async function updateViewInfo() {
    const d = await viewData();
    if (!d) { $("viewInfo").textContent = "No tree selected."; return; }
    if (d.isPreview) {
      $("viewInfo").textContent =
        `Preview · ${d.rt.nodes.length} nodes · not saved: tune the form and re-preview, or create the tree.`;
      return;
    }
    $("viewInfo").textContent =
      `${esc(d.tree.name)} · ${d.st.unlocked.length}/${d.rt.nodes.length} unlocked · ${d.vis.size} visible`;
  }
  async function draw3D() {
    fitCanvas();
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    const d = await viewData();
    if (!d) return;
    updateViewInfo();
    maybeAutoFit(d);
    const cx = W / 2, cy = H / 2, base = Math.min(W, H) * 0.42 * cam.zoom;
    // edges between shown nodes; links with both ends unlocked draw
    // brighter so owned routes stand out from the fog of locked ones
    ctx.lineWidth = 1;
    const dim = new Path2D(), lit = new Path2D();
    if (showEdges) for (const nd of d.rt.nodes) {
      if (!visNode(nd) || !nodeShown(nd)) continue;
      if (!d.vis.has(nd.id) && !d.unl.has(nd.id)) continue;
      for (const b of (d.rt.adj[nd.id] || [])) {
        if (b < nd.id) continue;
        const nb = d.rt.byId[b];
        if (!visNode(nb) || !nodeShown(nb)) continue;
        if (!d.vis.has(b) && !d.unl.has(b)) continue;
        const p1 = project(nd.pos), p2 = project(d.rt.byId[b].pos);
        if (!p1 || !p2) continue;
        const [x1, y1] = p1, [x2, y2] = p2;
        const path = (d.unl.has(nd.id) && d.unl.has(b)) ? lit : dim;
        path.moveTo(cx + x1 * base, cy - y1 * base);
        path.lineTo(cx + x2 * base, cy - y2 * base);
      }
    }
    ctx.strokeStyle = "rgba(140,150,175,0.28)";
    ctx.stroke(dim);
    ctx.strokeStyle = "rgba(238,194,95,0.75)";
    ctx.stroke(lit);
    // nodes, far first
    const items = [];
    for (const nd of d.rt.nodes) {
      if (!visNode(nd) || !nodeShown(nd)) continue;
      if (!d.vis.has(nd.id) && !d.unl.has(nd.id)) continue;
      const pr = project(nd.pos);
      if (!pr) continue;
      const [x, y, s] = pr;
      items.push({ nd, x: cx + x * base, y: cy - y * base, s });
    }
    items.sort((a, b) => a.s - b.s);
    projected = [];
    const dotScale = Math.min(cam.zoom, 3.5);
    const front = E.frontier(d.rt, d.st.unlocked);
    const ccx = E.costContext(d.st, d.rt);
    for (const it of items) {
      const unlocked = d.unl.has(it.nd.id);
      const col = classColor(it.nd.rarity);
      const rad = Math.max(1.2, Math.min(10, (unlocked ? 3.4 : 2.6) + it.nd.rarity * 0.55) * dotScale * (window.devicePixelRatio || 1) / 1.5);
      const hex = !unlocked && canUnlockNow(d.st, d.rt, it.nd.id, front, ccx);
      ctx.beginPath();
      if (hex) hexPath(ctx, it.x, it.y, rad);
      else ctx.arc(it.x, it.y, rad, 0, Math.PI * 2);
      if (unlocked) { ctx.fillStyle = col; ctx.fill(); }
      else { ctx.globalAlpha = 0.55; ctx.fillStyle = "#20242e"; ctx.fill(); ctx.strokeStyle = col; ctx.stroke(); ctx.globalAlpha = 1; }
      if (it.nd.id === selectedId) {
        if (hex) hexPath(ctx, it.x, it.y, rad + 4);
        else { ctx.beginPath(); ctx.arc(it.x, it.y, rad + 4, 0, Math.PI * 2); }
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.stroke(); ctx.lineWidth = 1;
      }
      const rOrigin = it.nd.r != null ? it.nd.r
        : Math.hypot(it.nd.pos[0], it.nd.pos[1], it.nd.pos[2]);
      const rTxt = showRadial ? ` · r ${rOrigin.toFixed(2)}` : "";
      projected.push({ id: it.nd.id, x: it.x, y: it.y, r: rad + 8, name: `#${it.nd.id} ${it.nd.name} · ${it.nd.rarity}${rTxt}`, hex });
    }
    if (selectedId != null && d.rt.byId[selectedId]) {
      const nd = d.rt.byId[selectedId];
      const rSel = nd.r != null ? nd.r : Math.hypot(nd.pos[0], nd.pos[1], nd.pos[2]);
      $("selInfo").textContent =
        `#${nd.id} ${nd.name} [${nd.file} | ${nd.source}] rarity ${nd.rarity}` +
        (showRadial ? ` · r ${rSel.toFixed(2)}` : "") +
        (d.unl.has(nd.id) ? " · unlocked" : " · locked");
    }
  }

  (function bindCamera() {
    const pts = new Map();
    let lastPinch = 0, moved = 0;
    const tip = $("hoverTip");
    function hideTip() { tip.style.display = "none"; }
    function hover(e) {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const x = (e.clientX - r.left) * dpr, y = (e.clientY - r.top) * dpr;
      let best = null, bd = 1e9;
      // need runtime names: look up via the last drawn frame's ids
      for (const p of projected) {
        const d = Math.hypot(p.x - x, p.y - y);
        if (d < p.r && d < bd) { bd = d; best = p; }
      }
      if (best && best.name) {
        tip.textContent = best.name;
        tip.style.display = "block";
        tip.style.left = (e.clientX - r.left) + "px";
        tip.style.top = (e.clientY - r.top) + "px";
      } else hideTip();
    }
    canvas.addEventListener("pointerdown", e => {
      canvas.setPointerCapture(e.pointerId);
      pts.set(e.pointerId, [e.clientX, e.clientY]);
      moved = 0;
    });
    canvas.addEventListener("pointermove", e => {
      if (e.pointerType !== "touch" && !pts.has(e.pointerId)) { hover(e); return; }
      if (!pts.has(e.pointerId)) return;
      hideTip();
      const prev = pts.get(e.pointerId);
      pts.set(e.pointerId, [e.clientX, e.clientY]);
      moved += Math.abs(e.clientX - prev[0]) + Math.abs(e.clientY - prev[1]);
      if (pts.size === 1) {
        cam.yaw += (e.clientX - prev[0]) * 0.008;
        cam.pitch = Math.max(-1.4, Math.min(1.4, cam.pitch + (e.clientY - prev[1]) * 0.008));
        requestDraw();
      } else if (pts.size === 2) {
        const [p, q] = [...pts.values()];
        const d = Math.hypot(p[0] - q[0], p[1] - q[1]);
        if (lastPinch) cam.zoom = Math.max(0.05, Math.min(15, cam.zoom * (d / lastPinch)));
        lastPinch = d;
        requestDraw();
      }
    });
    const up = e => {
      pts.delete(e.pointerId);
      if (pts.size < 2) lastPinch = 0;
      if (moved < 8) tapSelect(e);
    };
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("pointerleave", hideTip);
    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      cam.zoom = Math.max(0.05, Math.min(15, cam.zoom * (1 - e.deltaY * 0.0015)));
      requestDraw();
    }, { passive: false });

    function tapSelect(e) {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const x = (e.clientX - r.left) * dpr, y = (e.clientY - r.top) * dpr;
      let best = null, bd = 1e9;
      for (const p of projected) {
        const d = Math.hypot(p.x - x, p.y - y);
        if (d < p.r && d < bd) { bd = d; best = p.id; }
      }
      if (best != null) {
        selectedId = best;
        requestDraw();
        if (!preview) showTab("node");
      }
    }
  })();
  $("btnResetCam").addEventListener("click", () => {
    cam.yaw = 0.6; cam.pitch = 0.35;
    lastFitKey = ""; // force re-fit on next draw
    requestDraw();
  });
  $("btnOrigin").addEventListener("click", () => {
    selectedId = 0;
    requestDraw();
  });
  $("showEdges").addEventListener("change", () => {
    showEdges = $("showEdges").checked;
    requestDraw();
  });
  $("showRadial").addEventListener("change", () => {
    showRadial = $("showRadial").checked;
    requestDraw();
  });

  // ---- node finder ------------------------------------------------------------
  // Rotate the camera to face a node head-on (it then projects to center).
  function faceCamera(rt, nid) {
    const p = rt.byId[nid].pos;
    const rxz = Math.hypot(p[0], p[2]);
    if (rxz < 1e-9) return; // at the origin: already centered
    cam.yaw = Math.atan2(p[0], p[2]);
    cam.pitch = Math.max(-1.4, Math.min(1.4, Math.atan2(p[1], rxz)));
  }
  async function renderFinder() {
    const ul = $("findList");
    ul.innerHTML = "";
    const c = await current();
    if (!c) return;
    const q = ($("findQ").value || "").trim().toLowerCase();
    if (q.length < 2) {
      ul.innerHTML = "<li class='muted'>Type at least 2 characters.</li>";
      return;
    }
    const hits = c.rt.nodes
      .filter(nd => nd.id !== 0 && visNode(nd) &&
        (nd.name.toLowerCase().includes(q) ||
          nodeTags(nd).some(t => t.toLowerCase().includes(q))))
      .sort((a, b) => a.name.localeCompare(b.name))
      .slice(0, 15);
    if (!hits.length) {
      ul.innerHTML = "<li class='muted'>No matches.</li>";
      return;
    }
    for (const nd of hits) {
      const li = document.createElement("li");
      const tags = nodeTags(nd);
      li.innerHTML = `<div class="grow"><b>#${nd.id} ${esc(nd.name)}</b> ` +
        `<span class="pill">${esc(nd.file)} ${nd.rarity}</span>` +
        (tags.length ? " " + tagPills(tags, nd.file) : "") + `<br>` +
        `<span class="muted small">${esc(nd.source || "—")}${c.st.unlocked.includes(nd.id) ? " · unlocked" : ""}</span></div>`;
      li.style.cursor = "pointer";
      li.addEventListener("click", () => { selectedId = nd.id; showTab("node"); });
      const go = document.createElement("button");
      go.textContent = "View";
      go.title = "Face the camera at this node";
      go.addEventListener("click", (ev) => {
        if (ev.stopPropagation) ev.stopPropagation();
        selectedId = nd.id;
        faceCamera(c.rt, nd.id);
        lastFitKey = "finder"; // keep this framing until the tree changes
        showTab("view3d");
      });
      li.appendChild(go);
      ul.appendChild(li);
    }
  }

  // ---- node tab (detail + 2D neighbours) --------------------------------------
  // Neighbour dots page at 16 (two full rings); hubs here peak ~13, but
  // power-law trees can exceed that.
  const NBR_PAGE = 16;
  let nbrPage = 0, lastNbrId = null;
  function shortName(s) {
    s = String(s == null ? "" : s);
    return s.length > 16 ? s.slice(0, 15) + "…" : s;
  }
  function nodeLine(nd, unl, extra) {
    const cls = classOf(nd.rarity);
    const tags = nodeTags(nd);
    return `<div><span class="dot" style="background:${esc(cls.color)}"></span>` +
      `<b>#${nd.id} ${esc(nd.name)}</b> <span class="pill">${esc(nd.file)}</span> ` +
      `<span class="pill">${esc(nd.source || "—")}</span>` +
      (tags.length ? " " + tagPills(tags, nd.file) : "") + `</div>` +
      `<div class="small muted">${esc(cls.name)} · rarity ${nd.rarity} · cost ${unl ? "—" : E.fmt(Math.pow(10, nd.rarity))}` +
      (extra || "") + `</div>` +
      (nd.description ? `<p class="small">${linkify(nd.description)}</p>` : "");
  }
  // First held jump/choice ticket that can reach nid, with the launch node
  // and pick the engine will accept (mirrors unlockJump's ticket choice).
  function nodeJumpPlay(rt, st, nid) {
    const jt = st.inventory.find(t => t.kind === "jump" || t.kind === "choice");
    if (!jt) return null;
    const limit = jt.kind === "choice" ? jt.n : 1;
    for (const u of st.unlocked) {
      const cands = E.jumpCandidates(rt, jt.category, u, st.unlocked).slice(0, limit);
      const idx = cands.findIndex(([dd, cand]) => cand.id === nid);
      if (idx >= 0) return { ticket: jt, from: u, pick: idx };
    }
    return null;
  }
  async function renderNode() {
    const card = $("nodeCard"), svg = $("nbrSvg");
    svg.innerHTML = "";
    const c = await current();
    if (!c) { card.innerHTML = "<h2>No tree selected</h2>"; return; }
    if (selectedId == null || !c.rt.byId[selectedId]) {
      const first = c.rt.byId[0] ? [...(c.rt.adj[0] || [])][0] : null;
      selectedId = first != null ? first : 0;
    }
    const nd = c.rt.byId[selectedId];
    const meta = E.viewState(c.rt, c.st);
    const unl = c.st.unlocked.includes(nd.id);
    const frontSet = E.frontier(c.rt, c.st.unlocked);
    const front = frontSet.has(nd.id);
    const ccx = E.costContext(c.st, c.rt);
    let actions = "";
    if (isShared()) {
      actions = `<div class="muted small" style="margin-top:8px">` +
        (unl ? "Unlocked ✓" : "Shared view (read-only).") + `</div>`;
    } else if (!unl && nd.id !== 0) {
      if (front) {
        const cost = E.nodeCostFor(c.st, c.rt, nd.id, ccx);
        const cover = E.couponCover(c.st, cost);
        const cc = E.coreCostFor(c.st, c.rt, nd.id, ccx);
        const coreTxt = cc ? ` + ${cc} core` : " · no core";
        const ok = c.st.cores >= cc && c.st.points >= cost - cover;
        actions = `<div class="row" style="margin-top:8px"><button class="primary" data-act="unlock" ${ok ? "" : "disabled"}>` +
          `Unlock (${E.fmt(cost - cover)} pts${coreTxt}${cover ? ` · coupon −${E.fmt(cover)}` : ""})</button></div>` +
          `<div class="muted small" style="margin-top:4px">Wallet: ${E.fmt(c.st.points)} pts · ${c.st.cores} cores.</div>` +
          (ok ? "" : `<div class="muted small" style="margin-top:4px">Needs ${cc ? cc + " core + " : ""}${E.fmt(cost - cover)} pts (have ${c.st.cores} / ${E.fmt(c.st.points)}).</div>`);
      } else {
        const { dist } = E.hopDistances(c.rt, c.st.unlocked);
        const skipOk = c.st.inventory.some(t => t.kind === "skip" &&
          dist[nd.id] != null && dist[nd.id] <= 1 + t.n);
        const play = nodeJumpPlay(c.rt, c.st, nd.id);
        if (!skipOk && !play) {
          actions = `<div class="muted small" style="margin-top:8px">Not adjacent: reach it with a skip / jump / hop ticket (Tickets tab).</div>`;
        } else {
          actions = `<div class="row" style="margin-top:8px">` +
            (skipOk ? `<button class="primary" data-act="skip">Unlock with Skip →</button>` : "") +
            (play ? `<button class="primary" data-act="jump">Unlock with Jump →</button>` : "") + `</div>` +
            `<div class="muted small" style="margin-top:4px">Wallet: ${E.fmt(c.st.points)} pts · ${c.st.cores} cores.</div>`;
        }
      }
    } else if (unl) {
      actions = `<div class="muted small" style="margin-top:8px">Unlocked ✓</div>`;
    }
    card.innerHTML = `<h2>Selected node</h2>` + nodeLine(nd, unl) + actions +
      `<div class="row" style="margin-top:8px"><button data-act="copy" title="Copy this node's text">📋 Copy</button></div>`;
    const cb = card.querySelector('[data-act="copy"]');
    if (cb) cb.addEventListener("click", () => copyText(nodeText(nd), nd.name));
    const ub = card.querySelector('[data-act="unlock"]');
    if (ub) ub.addEventListener("click", async () => {
      const done = await mutate(({ st, rt }) => E.unlock(st, rt, nd.id));
      if (done) toast(`Unlocked ${nd.name}.`);
    });
    // Skip / jump straight from the node view when a held ticket reaches it.
    const sb = card.querySelector('[data-act="skip"]');
    if (sb) sb.addEventListener("click", async () => {
      const done = await mutate(({ st, rt }) => E.unlockSkip(st, rt, nd.id));
      if (done) toast(`Unlocked ${nd.name} (skip).`);
    });
    const jb = card.querySelector('[data-act="jump"]');
    if (jb) jb.addEventListener("click", async () => {
      const done = await mutate(({ st, rt }) => {
        const play = nodeJumpPlay(rt, st, nd.id);
        if (!play) throw new E.ChaosError("no held jump ticket reaches this node");
        return E.unlockJump(st, rt, play.ticket.category, play.from, play.pick);
      });
      if (done) toast(`Unlocked ${nd.name} (jump).`);
    });

    // 2D neighbour view: center + ring(s). Only neighbours you can actually
    // see (unlocked, frontier, or revealed by an ability) are shown; hidden
    // nodes stay hidden. Normal unlocks stay frontier-only (engine-enforced);
    // abilities (lifeline/gacha/duplicate/…) are the only other paths.
    // One ring fits ~8; beyond that neighbours split across two rings so
    // dots and labels keep breathing room (hubs here peak ~13; two rings
    // hold ~16 with room to spare). The viewBox grows taller to fit.
    const NS = "http://www.w3.org/2000/svg";
    const cx = 180, cyy = 150;
    const unlSet = new Set(c.st.unlocked);
    const vis = c.rt.frozen ? new Set(c.rt.frozen.vis) : new Set(E.visible(c.rt, c.st.unlocked, meta));
    const nbs = [...(c.rt.adj[nd.id] || [])]
      .filter(b => (unlSet.has(b) || vis.has(b)) && visNode(c.rt.byId[b]))
      .sort((a, b) => a - b);
    if (selectedId !== lastNbrId) { nbrPage = 0; lastNbrId = selectedId; }
    const nbrPages = Math.max(1, Math.ceil(nbs.length / NBR_PAGE));
    nbrPage = Math.max(0, Math.min(nbrPage, nbrPages - 1));
    const pageIds = nbs.slice(nbrPage * NBR_PAGE, (nbrPage + 1) * NBR_PAGE);
    $("nbrPrev").onclick = () => { if (nbrPage > 0) { nbrPage--; renderNode(); } };
    $("nbrNext").onclick = () => { if (nbrPage < nbrPages - 1) { nbrPage++; renderNode(); } };
    $("nbrPrev").disabled = nbrPage === 0;
    $("nbrNext").disabled = nbrPage >= nbrPages - 1;
    $("nbrPage").textContent = nbrPages > 1
      ? `${nbrPage * NBR_PAGE + 1}–${Math.min(nbs.length, (nbrPage + 1) * NBR_PAGE)} of ${nbs.length}` : "";
    const RINGS = pageIds.length <= 8 ? [{ r: 96, dot: 15, fs: 10, ids: pageIds }]
      : (() => {
        const inner = pageIds.slice(0, Math.min(7, Math.ceil(pageIds.length / 2)));
        return [
          { r: 80, dot: 13, fs: 9, ids: inner },
          { r: 134, dot: 11, fs: 9, ids: pageIds.slice(inner.length) },
        ];
      })();
    const maxR = RINGS[RINGS.length - 1].r;
    const viewH = Math.max(300, 2 * (maxR + 34));
    svg.setAttribute("viewBox", `0 0 360 ${viewH}`);
    function circle(x, y, r, fill, stroke, id, label, hex, fs) {
      const g = document.createElementNS(NS, "g");
      g.style.cursor = "pointer";
      if (hex) {
        const pts = [];
        for (let i = 0; i < 6; i++) {
          const a = -Math.PI / 2 + (Math.PI / 3) * i;
          pts.push((x + r * Math.cos(a)).toFixed(1) + "," + (y + r * Math.sin(a)).toFixed(1));
        }
        const pg = document.createElementNS(NS, "polygon");
        pg.setAttribute("points", pts.join(" "));
        pg.setAttribute("fill", fill); pg.setAttribute("stroke", stroke || "#333947");
        g.appendChild(pg);
      } else {
        const ci = document.createElementNS(NS, "circle");
        ci.setAttribute("cx", x); ci.setAttribute("cy", y); ci.setAttribute("r", r);
        ci.setAttribute("fill", fill); ci.setAttribute("stroke", stroke || "#333947");
        g.appendChild(ci);
      }
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", x); t.setAttribute("y", y + r + 13);
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("fill", "#9aa0b0"); t.setAttribute("font-size", fs || 10);
      t.textContent = label;
      g.appendChild(t);
      g.addEventListener("click", () => { selectedId = id; renderNode(); });
      svg.appendChild(g);
    }
    for (const [ri, ring] of RINGS.entries()) {
      // Offset outer rings by half a step so their dots sit in the gaps.
      const off = ri === 0 ? 0 : Math.PI / Math.max(1, ring.ids.length);
      ring.ids.forEach((b, i) => {
        const a = (2 * Math.PI * i) / Math.max(1, ring.ids.length) - Math.PI / 2 + off;
        const x = cx + ring.r * Math.cos(a), y = cyy + ring.r * Math.sin(a);
        const l = document.createElementNS(NS, "line");
        l.setAttribute("x1", cx); l.setAttribute("y1", cyy);
        l.setAttribute("x2", x); l.setAttribute("y2", y);
        l.setAttribute("stroke", "#333947");
        svg.appendChild(l);
      });
    }
    circle(cx, cyy, 26, classColor(nd.rarity), "#fff", nd.id, shortName(nd.name),
      !unl && canUnlockNow(c.st, c.rt, nd.id, frontSet, ccx));
    for (const [ri, ring] of RINGS.entries()) {
      const off = ri === 0 ? 0 : Math.PI / Math.max(1, ring.ids.length);
      ring.ids.forEach((b, i) => {
        const a = (2 * Math.PI * i) / Math.max(1, ring.ids.length) - Math.PI / 2 + off;
        const x = cx + ring.r * Math.cos(a), y = cyy + ring.r * Math.sin(a);
        const bnd = c.rt.byId[b];
        const isUnl = c.st.unlocked.includes(b);
        const bcol = classColor(bnd.rarity);
        circle(x, y, ring.dot, isUnl ? bcol : "#20242e", bcol, b, shortName(bnd.name),
          !isUnl && canUnlockNow(c.st, c.rt, b, frontSet, ccx), ring.fs);
      });
    }
    const legend = document.createElementNS(NS, "text");
    legend.setAttribute("x", 8); legend.setAttribute("y", viewH - 8);
    legend.setAttribute("fill", "#9aa0b0"); legend.setAttribute("font-size", "10");
    const totalConns = new Set(c.rt.adj[nd.id] || []).size;
    const hidden = totalConns - nbs.length;
    legend.textContent = `${nd.name}: ${nbrPages > 1 ? `${pageIds.length} of ` : ""}${nbs.length} shown` +
      (hidden ? ` · ${hidden} hidden` : "") + " (tap a dot to inspect)";
    svg.appendChild(legend);
  }

  // ---- owned tab (sortable/filterable table, unlock order by default) ------
  let ownedSort = { key: "order", dir: 1 };
  // Unlock-planner state (module scope: init listeners mutate these).
  // Collapsed by default like a hidden list; the toggle mirrors the
  // unlockable-now/inventory show/hide buttons.
  let planPage = 0, planJumpTi = 0, planJumpFrom = null, planOpen = false;
  function applyPlanVisibility() {
    $("planList").style.display = planOpen ? "" : "none";
    $("planPage").style.display = planOpen ? "" : "none";
    $("planPrev").style.display = planOpen ? "" : "none";
    $("planNext").style.display = planOpen ? "" : "none";
    $("planToggle").textContent = planOpen ? "Hide" : "Show";
  }
  const OWN_COLS = [
    { key: "order", label: "#" },
    { key: "name", label: "Name" },
    { key: "file", label: "Cat" },
    { key: "rarity", label: "Rarity" },
    { key: "cost", label: "Cost" },
    { key: "source", label: "Source" },
    { key: "tags", label: "Tags" }
  ];
  function ownedRows(rt, st, ccx) {
    const pos = new Map((st.history || []).map((id, i) => [id, i]));
    return st.unlocked.map(id => ({
      id, nd: rt.byId[id], order: pos.has(id) ? pos.get(id) : -1,
      cost: id === 0 ? -1 : E.nodeCostFor(st, rt, id, ccx)
    })).filter(r => r.nd && visNode(r.nd));
  }
  async function renderOwned() {
    const head = $("ownedHead"), body = $("ownedBody");
    head.innerHTML = ""; body.innerHTML = "";
    const c = await current();
    if (!c) { $("ownedCount").textContent = ""; return; }
    const { st, rt } = c;
    const ccx = E.costContext(st, rt);
    for (const col of OWN_COLS) {
      const th = document.createElement("th");
      th.style.cssText = "text-align:left;padding:4px;border-bottom:1px solid var(--line);white-space:nowrap";
      const b = document.createElement("button");
      b.style.cssText = "min-height:44px;padding:6px 8px;font-size:0.85rem;";
      b.textContent = col.label + (ownedSort.key === col.key ? (ownedSort.dir > 0 ? " ▲" : " ▼") : "");
      b.addEventListener("click", () => {
        if (ownedSort.key === col.key) ownedSort.dir *= -1;
        else ownedSort = { key: col.key, dir: 1 };
        renderOwned();
      });
      th.appendChild(b);
      head.appendChild(th);
    }
    let rows = ownedRows(rt, st, ccx);
    const q = ($("ownQ").value || "").trim().toLowerCase();
    const cat = $("ownCat").value || "";
    const ownTag = ($("ownTag") && $("ownTag").value) || "";
    if (q) rows = rows.filter(r =>
      r.nd.name.toLowerCase().includes(q) ||
      (r.nd.source || "").toLowerCase().includes(q) ||
      nodeTags(r.nd).some(t => t.toLowerCase().includes(q)));
    if (cat) rows = rows.filter(r => r.nd.file === cat);
    if (ownTag) rows = rows.filter(r => nodeTags(r.nd).includes(ownTag));
    const val = (r) => {
      switch (ownedSort.key) {
        case "order": return r.order;
        case "name": return r.nd.name.toLowerCase();
        case "file": return r.nd.file;
        case "rarity": return r.nd.rarity;
        case "cost": return r.cost;
        case "source": return (r.nd.source || "").toLowerCase();
        case "tags": return nodeTags(r.nd).join(",");
        default: return 0;
      }
    };
    rows.sort((a, b) => {
      const va = val(a), vb = val(b);
      const d = va < vb ? -1 : va > vb ? 1 : a.order - b.order;
      return d * ownedSort.dir;
    });
    $("ownedCount").textContent = `(${rows.length}/${st.unlocked.length})`;
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.style.cssText = "border-top:1px solid var(--line);cursor:pointer";
      const cls = classOf(r.nd.rarity);
      const cost = r.id === 0 ? "—" : E.fmt(r.cost);
      const tags = nodeTags(r.nd);
      tr.innerHTML =
        `<td style="padding:8px">${r.order < 0 ? "★" : r.order + 1}</td>` +
        `<td style="padding:8px"><span class="dot" style="background:${esc(cls.color)}"></span>${esc(r.nd.name)}</td>` +
        `<td style="padding:8px">${esc(r.nd.file)}</td>` +
        `<td style="padding:8px">${r.nd.rarity}</td>` +
        `<td style="padding:8px">${cost}</td>` +
        `<td style="padding:8px">${esc(r.nd.source || "—")}</td>` +
        `<td style="padding:8px">${tags.map(t => tagPills([t], r.nd.file)).join(" ")}</td>`;
      tr.addEventListener("click", () => { selectedId = r.id; showTab("node"); });
      body.appendChild(tr);
    }
    if (!rows.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="7" class="muted" style="padding:8px">No owned nodes match.</td>`;
      body.appendChild(tr);
    }
  }

  // ---- tickets tab --------------------------------------------------------------
  const TICKET_TIERS = ["trash", "bronze", "silver", "gold", "aluminium", "platinum", "diamond", "legendary", "mythical", "wild", "divine", "transcendent"];
  function fillTicketForm() {
    $("tkTier").innerHTML = TICKET_TIERS.map(t => `<option>${t}</option>`).join("") +
      `<option value="">tierless</option>`;
    $("tkTier").value = "bronze"; // preserve the historical default
    $("tkCat").innerHTML = E.CATEGORIES.map(c => `<option>${c}</option>`).join("");
  }
  function ticketLabel(t) {
    // Skip/jump/choice/hop tickets spend no tier: their points paid out at
    // award time, so the label shows only what the action needs. Coupons
    // are the exception: their banked value is live information.
    if (t.kind === "coupon") return `coupon · ${E.fmt(t.value || 0)} pts`;
    let s = (t.kind === "plain" && t.tier ? t.tier + " " : "") + t.kind;
    if (t.kind === "skip" || t.kind === "choice") s += ` ${t.n}`;
    if (t.category) s += ` ${t.category}`;
    if (t.twin) s += " 👯";
    if (t.d20 != null) {
      const ds = Array.isArray(t.d20) ? t.d20.join("+") : t.d20;
      s += ` 🎲${ds}`;
    }
    return s;
  }
  // Collapse runs of tickets that render the same into stacks. Only
  // consecutive runs group; identical tickets either side of a different
  // one stay separate so the display order still matches the inventory.
  function stackTickets(inv) {
    const out = [];
    for (let i = 0; i < inv.length;) {
      const t = inv[i];
      const key = ticketLabel(t);
      let j = i + 1;
      while (j < inv.length && ticketLabel(inv[j]) === key) j++;
      out.push({ t, count: j - i });
      i = j;
    }
    return out;
  }
  function nodeOptions(ids, rt, extra) {
    return ids.filter(id => visNode(rt.byId[id])).map(id => {
      const nd = rt.byId[id];
      return `<option value="${id}">#${id} ${esc(nd.name)} (${nd.file}, ${nd.rarity}${extra ? ", " + extra(nd) : ""})</option>`;
    }).join("");
  }

  async function renderTickets() {
    const c = await current();
    const inv = $("invList"), meta = $("metaBox");
    if (!c) {
      inv.innerHTML = "<li class='muted'>No tree selected.</li>";
      $("unlockList").innerHTML = "<li class='muted'>No tree selected.</li>";
      return;
    }
    const { st, rt } = c;
    const m = E.viewState(rt, st);
    // One cost context per render: costs stay O(1) in sorts and rows.
    const ccx = E.costContext(st, rt);
    $("wPoints").textContent = E.fmt(st.points);
    $("wCores").textContent = st.cores;
    $("wBonus").textContent = `+${m.ticket_bonus}%`;
    const echoLeft = m.echo - (st.echo_used || 0);
    const bits = [];
    if (m.sight) bits.push(`sight+${m.sight}`);
    if (m.see_far) bits.push("see-far");
    if (m.survey) bits.push(`survey+${m.survey}`);
    if (m.trace_name) bits.push("trace-name");
    if (m.trace_desc) bits.push("trace-desc");
    if (m.compass) bits.push("compass");
    if (m.reveal_full) bits.push("reveal-full");
    if (echoLeft > 0) bits.push(`echo×${echoLeft}`);
    if (m.root_pact) bits.push("root-pact");
    if (Object.keys(m.cat_sight).length) bits.push("cat-sight");
    for (const k of ["lock_refund", "add_link", "gacha", "lifeline", "recall", "duplicate", "shuffle", "swap", "shake", "chaosquake", "gamble", "trace_name_use"]) {
      if (m[k]) bits.push(`${k.replace(/_/g, "-")}×${m[k] - ((st.meta_used || {})[k] || 0)}`);
    }
    if (m.reshuffle) bits.push("reshuffle");
    if (m.gamble_reroll) bits.push(`reroll≤${m.gamble_reroll}`);
    if (m.gamble_twice) bits.push("second-roll");
    $("wMeta").textContent = bits.length ? bits.join(", ") : "none";

    // inventory — consecutive identical tickets render as one stacked row,
    // but each action still spends a single ticket. Grouping is by label so
    // only runs that look the same collapse.
    inv.innerHTML = "";
    if (!st.inventory.length) inv.innerHTML = "<li class='muted'>No tickets: award one above.</li>";
    const renderTicketRow = (t, count) => {
      const li = document.createElement("li");
      // Wrap: the label takes the first line, the 100%-wide controls
      // their own line below, instead of squeezing the label to nothing.
      li.style.flexWrap = "wrap";
      const note = E.gambleNote(t);
      const stack = count > 1
        ? ` <span class="pill" title="Stack of ${count} identical tickets: each action spends one.">×${count}</span>`
        : "";
      li.innerHTML = `<div class="grow"><b${note ? ` title="${esc(note)}"` : ""}>${esc(ticketLabel(t))}${stack}</b>` +
        (note ? `<div class="small muted">🎲 ${esc(note)}</div>` : "") + `</div>`;
      const ctl = document.createElement("div");
      ctl.className = "row";
      ctl.style.marginTop = "6px";
      const emptyNote = text => {
        const span = document.createElement("span");
        span.className = "muted small";
        span.textContent = text;
        return span;
      };
      const useBtn = (label, fn) => {
        const b = document.createElement("button");
        b.textContent = label; b.className = "primary";
        b.addEventListener("click", async () => {
          const ok = await mutate(fn);
          if (ok) toast("Done.");
        });
        return b;
      };
      if (t.kind === "skip") {
        const { dist } = E.hopDistances(rt, st.unlocked);
        const cands = rt.nodes.filter(nd => !st.unlocked.includes(nd.id) && nd.id !== 0 &&
          (dist[nd.id] != null && dist[nd.id] <= 1 + t.n)).map(nd => nd.id)
          .sort((a, b) => (dist[a] - dist[b]) ||
            (E.nodeCost(rt, a) - E.nodeCost(rt, b)));
        const sel = document.createElement("select");
        sel.innerHTML = nodeOptions(cands, rt, nd => `${dist[nd.id]} hop${dist[nd.id] === 1 ? "" : "s"}, cost ` + E.fmt(E.nodeCost(rt, nd.id)));
        if (!sel.options.length) {
          ctl.appendChild(emptyNote("No node in reach of this ticket."));
        } else {
          ctl.append(sel, useBtn(`Skip →`, ({ st, rt }) => E.unlockSkip(st, rt, parseInt(sel.value, 10), t.n)));
        }
      } else if (t.kind === "jump" || t.kind === "choice") {
        const fromIds = st.unlocked.filter(u => u !== 0);
        if (!fromIds.length) {
          ctl.appendChild(emptyNote("Unlock a node first: jumps launch from unlocked nodes."));
        } else {
          const fromSel = document.createElement("select");
          fromSel.innerHTML = nodeOptions(fromIds, rt);
          const cat = t.category;
          const showCands = () => {
            const { dist } = E.hopDistances(rt, st.unlocked);
            const list = E.jumpCandidates(rt, cat, parseInt(fromSel.value, 10), st.unlocked)
              .slice(0, t.kind === "choice" ? t.n : 1);
            pickSel.innerHTML = list.map(([dd, nd], i) => {
              const hops = dist[nd.id] == null ? "isolated"
                : `${dist[nd.id]} hop${dist[nd.id] === 1 ? "" : "s"}`;
              return `<option value="${i}">#${nd.id} ${esc(nd.name)} (${nd.rarity}, ${dd.toFixed(1)} away, ${hops})</option>`;
            }).join("");
          };
          const pickSel = document.createElement("select");
          fromSel.addEventListener("change", showCands);
          ctl.append(fromSel, pickSel);
          showCands();
          ctl.append(useBtn(t.kind === "choice" ? "Choice jump →" : "Jump →",
            ({ st, rt }) => E.unlockJump(st, rt, cat, parseInt(fromSel.value, 10), parseInt(pickSel.value || "0", 10))));
        }
      } else if (t.kind === "hop") {
        const { dist } = E.hopDistances(rt, st.unlocked);
        const cands = rt.nodes.filter(nd => !st.unlocked.includes(nd.id) && (dist[nd.id] || 0) >= 2).map(nd => nd.id);
        const sel = document.createElement("select");
        sel.innerHTML = nodeOptions(cands.slice(0, 400), rt);
        if (!sel.options.length) {
          ctl.appendChild(emptyNote("No node far enough away for this ticket."));
        } else {
          ctl.append(sel, useBtn("Hop →", ({ st, rt }) => E.unlockHop(st, rt, parseInt(sel.value, 10))));
        }
      } else {
        const span = document.createElement("span");
        span.className = "muted small";
        span.textContent = "spent via Unlock buttons";
        ctl.appendChild(span);
      }
      const wrap = document.createElement("div");
      wrap.style.width = "100%";
      wrap.appendChild(ctl);
      li.appendChild(wrap);
      inv.appendChild(li);
    };
    for (const { t, count } of stackTickets(st.inventory)) renderTicketRow(t, count);

    // meta abilities
    meta.innerHTML = "";
    const vis = rt.frozen ? [...rt.frozen.vis] : E.visible(rt, st.unlocked, m);
    const unl = new Set(st.unlocked);
    const lockedVisIds = vis.filter(id => !unl.has(id));
    const used = k => (st.meta_used || {})[k] || 0;
    function addMeta(title, desc, controls) {
      const d = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = title;
      d.appendChild(s);
      const p = document.createElement("p");
      p.className = "muted small"; p.textContent = desc;
      d.appendChild(p);
      d.appendChild(controls);
      meta.appendChild(d);
    }
    function btn(label, fn) {
      const b = document.createElement("button");
      b.textContent = label; b.className = "primary";
      b.addEventListener("click", async () => {
        const ok = await mutate(fn);
        if (ok) toast("Done.");
      });
      return b;
    }
    function nodeSel(ids, costFn) {
      const sel = document.createElement("select");
      sel.innerHTML = nodeOptions(ids, rt, costFn);
      return sel;
    }
    let any = false;
    const have = (k) => m[k] - used(k) > 0;
    if (m.lock_refund && have("lock_refund")) {
      any = true;
      const sel = nodeSel(st.unlocked.filter(u => u !== 0), rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(sel, btn("Lock + refund", ({ st, rt }) => E.useLockRefund(st, rt, parseInt(sel.value, 10))));
      addMeta(`Undo Stone ×${m.lock_refund - used("lock_refund")}`, "Lock an unlocked node, refund its core + points.", row);
    }
    if (m.add_link && have("add_link")) {
      any = true;
      const a = nodeSel(lockedVisIds, rt), b = nodeSel(lockedVisIds, rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(a, b, btn("Graft link", ({ st, rt }) =>
        E.useAddLink(st, rt, parseInt(a.value, 10), parseInt(b.value, 10))));
      addMeta(`Tree Graft ×${m.add_link - used("add_link")}`, `Link two close unconnected nodes (≤ ${E.ADD_LINK_DISTANCE}).`, row);
    }
    if (m.reveal_temp && (st.reveal_temp_until || 0) < Date.now() / 1000) {
      any = true;
      addMeta("Glimpse", "Reveal the full tree for 10 seconds.",
        btn("Reveal 10s", ({ st, rt }) => E.useReveal(st, rt)));
    }
    if (m.gacha && have("gacha")) {
      any = true;
      addMeta(`Chaos Die ×${m.gacha - used("gacha")}`, `Random free unlock, rarity ${m.gacha_min}–${m.gacha_max}.`,
        btn("Roll", ({ st, rt }) => {
          const nd = E.useGacha(st, rt);
          selectedId = nd.id;
          toast(`Rolled #${nd.id} ${nd.name}.`);
        }));
    }
    if (m.lifeline && have("lifeline")) {
      any = true;
      const sel = nodeSel([...E.frontier(rt, st.unlocked)], rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(sel, btn("Free unlock", ({ st, rt }) => E.useLifeline(st, rt, parseInt(sel.value, 10))));
      addMeta(`Lifeline ×${m.lifeline - used("lifeline")}`, "Free unlock of a frontier (adjacent) node.", row);
    }
    if (m.recall && have("recall")) {
      any = true;
      addMeta(`Recall ×${m.recall - used("recall")}`, "Undo your most recent unlock (refund core + points).",
        btn("Undo last unlock", ({ st, rt }) => E.useRecall(st, rt)));
    }
    if (m.duplicate && have("duplicate")) {
      any = true;
      addMeta(`Duplicate ×${m.duplicate - used("duplicate")}`, `Random unlock sharing an owned non-Generic source, rarity ≤ ${m.duplicate_max}.`,
        btn("Duplicate", ({ st, rt }) => {
          const nd = E.useDuplicate(st, rt);
          selectedId = nd.id;
          toast(`Duplicated #${nd.id} ${nd.name}.`);
        }));
    }
    if (m.shuffle && have("shuffle")) {
      any = true;
      const sel = nodeSel(lockedVisIds, rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(sel, btn("Shuffle", ({ st, rt }) => E.useShuffle(st, rt, parseInt(sel.value, 10))));
      addMeta(`Shuffle ×${m.shuffle - used("shuffle")}`, "Swap a visible locked node with a random unseen one of similar rarity.", row);
    }
    if (m.swap && have("swap")) {
      any = true;
      const a = nodeSel(lockedVisIds, rt), b = nodeSel(lockedVisIds, rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(a, b, btn("Swap", ({ st, rt }) => E.useSwap(st, rt, parseInt(a.value, 10), parseInt(b.value, 10))));
      addMeta(`Swap ×${m.swap - used("swap")}`, "Swap two visible locked nodes of your choice.", row);
    }
    if (m.reshuffle) {
      any = true;
      const sel = nodeSel(lockedVisIds, rt);
      const row = document.createElement("div"); row.className = "row";
      row.append(sel, btn("Reshuffle (¼ cost)", ({ st, rt }) => E.useReshuffle(st, rt, parseInt(sel.value, 10))));
      addMeta("Reshuffle (unlimited)", "Shuffle at a quarter of the node's points cost.", row);
    }
    if (m.shake && have("shake")) {
      any = true;
      addMeta(`Shake the Tree ×${m.shake - used("shake")}`, "Reassign entries among locked nodes. Positions and links stay put; rarities stay similar.",
        btn("Shake", ({ st, rt }) => {
          const n = E.useShake(st, rt);
          toast(`Shook the tree: ${n} locked nodes reassigned.`);
        }));
    }
    if (m.chaosquake && have("chaosquake")) {
      any = true;
      addMeta(`ChaosQuake ×${m.chaosquake - used("chaosquake")}`, "Reassign entries among ALL non-root nodes. Unlocked nodes keep their places but not their faces.",
        btn("ChaosQuake", ({ st, rt }) => {
          const n = E.useChaosquake(st, rt);
          toast(`ChaosQuake: ${n} nodes reassigned.`);
        }));
    }
    if (!any) meta.innerHTML = "<span class='muted small'>Unlock tree-meta nodes (Sight, Graft, Chaos Die…) to gain abilities.</span>";

  // Frontier nodes, cheapest first, with one-tap unlock.
  const UNLOCK_PAGE = 20;
  let unlockPage = 0, unlockOpen = true, lastUnlockCtx = null;
  function applyUnlockVisibility() {
    $("unlockList").style.display = unlockOpen ? "" : "none";
    $("unlockPage").style.display = unlockOpen ? "" : "none";
    $("unlockPrev").style.display = unlockOpen ? "" : "none";
    $("unlockNext").style.display = unlockOpen ? "" : "none";
    $("unlockToggle").textContent = unlockOpen ? "Hide" : "Show";
  }
  $("unlockToggle").addEventListener("click", () => {
    unlockOpen = !unlockOpen;
    applyUnlockVisibility();
  });
  $("unlockPrev").addEventListener("click", async () => {
    if (unlockPage > 0) { unlockPage--; if (lastUnlockCtx) await renderUnlockable(lastUnlockCtx); }
  });
  $("unlockNext").addEventListener("click", async () => {
    unlockPage++; if (lastUnlockCtx) await renderUnlockable(lastUnlockCtx);
  });
  async function renderUnlockable(c, ccx) {
    lastUnlockCtx = c;
    ccx = ccx || E.costContext(c.st, c.rt);
    const box = $("unlockList");
    box.innerHTML = "";
    const { st, rt } = c;
    $("unlockWallet").textContent = `Wallet: ${E.fmt(st.points)} pts · ${st.cores} cores.`;
    const ids = [...E.frontier(rt, st.unlocked)]
      .filter(id => id !== 0 && visNode(rt.byId[id]));
    ids.sort((a, b) => E.nodeCostFor(st, rt, a, ccx) - E.nodeCostFor(st, rt, b, ccx));
    const pages = Math.max(1, Math.ceil(ids.length / UNLOCK_PAGE));
    unlockPage = Math.max(0, Math.min(unlockPage, pages - 1));
    $("unlockPage").textContent = ids.length
      ? `${unlockPage * UNLOCK_PAGE + 1}–${Math.min(ids.length, (unlockPage + 1) * UNLOCK_PAGE)} of ${ids.length}` : "";
    $("unlockPrev").disabled = unlockPage === 0;
    $("unlockNext").disabled = unlockPage >= pages - 1;
    applyUnlockVisibility();
    $("unlockCopy").onclick = () => {
      if (!ids.length) return toast("Nothing to copy.", true);
      copyText(ids.map(id => nodeText(rt.byId[id])).join("\n\n"),
        `${ids.length} unlockable node${ids.length === 1 ? "" : "s"}`);
    };
    if (!ids.length) {
      box.innerHTML = "<li class='muted'>Nothing on the frontier: reach further with tickets.</li>";
      return;
    }
    for (const id of ids.slice(unlockPage * UNLOCK_PAGE, (unlockPage + 1) * UNLOCK_PAGE)) {
      const nd = rt.byId[id];
      const cost = E.nodeCostFor(st, rt, id, ccx);
      const cc = E.coreCostFor(st, rt, id, ccx);
      const ok = st.cores >= cc && st.points >= cost - E.couponCover(st, cost);
      const li = document.createElement("li");
      const tags = nodeTags(nd);
      li.innerHTML = `<div class="grow"><b>${esc(nd.name)}</b> ` +
        `<span class="pill">${esc(nd.file)} ${fmtR(nd.rarity)}</span>` +
        (tags.length ? " " + tagPills(tags, nd.file) : "") + `<br>` +
        `<span class="muted small">${E.fmt(cost)} pts${cc ? " + 1 core" : " · no core"}</span></div>`;
      const go = document.createElement("button");
      go.textContent = "View";
      go.title = `Open ${nd.name} in the node view`;
      go.addEventListener("click", () => { selectedId = id; showTab("node"); });
      li.appendChild(go);
      if (!isShared()) {
        const b = document.createElement("button");
        b.textContent = "Unlock";
        b.className = "primary";
        b.disabled = !ok;
        b.title = ok ? `Unlock ${nd.name}` : (st.cores < cc ? `Needs ${cc} core${cc === 1 ? "" : "s"} (award a ticket)` : `Needs ${E.fmt(cost)} pts`);
        b.addEventListener("click", async () => {
          const done = await mutate(({ st, rt }) => E.unlock(st, rt, id));
          if (done) toast(`Unlocked ${nd.name}.`);
        });
        li.appendChild(b);
      }
      box.appendChild(li);
    }
  }
  // ---- unlock planner: sortable/filterable over frontier, visible,
  // skip- and jump-reachable nodes. Frontier duplicates Unlockable now
  // with sorting + filters; visible covers everything sight reveals
  // (the planning view for big view distances); skip/jump replace the
  // cramped ticket dropdowns with a real list.
  const PLAN_PAGE = 20;
  function planAfford(st, rt, id, ccx) {
    if (id === 0 || st.unlocked.includes(id)) return false;
    if ((st.cores || 0) < E.coreCostFor(st, rt, id, ccx)) return false;
    const cost = E.nodeCostFor(st, rt, id, ccx);
    return st.points >= cost - E.couponCover(st, cost);
  }
  async function renderPlanner(c, ccx) {
    const box = $("planList");
    box.innerHTML = "";
    const { st, rt } = c;
    ccx = ccx || E.costContext(st, rt);
    const scope = ($("planScope") && $("planScope").value) || "frontier";
    const showJump = scope === "jump";
    $("planJumpCtl").style.display = showJump ? "" : "none";
    $("planJumpFromCtl").style.display = showJump ? "" : "none";
    const m = E.viewState(rt, st);
    const unl = new Set(st.unlocked);
    const { dist } = E.hopDistances(rt, st.unlocked);
    const skips = st.inventory.filter(t => t.kind === "skip");
    const jumps = st.inventory.filter(t => t.kind === "jump" || t.kind === "choice");
    const fromIds = st.unlocked.filter(u => u !== 0);
    const hopTxt = h => h == null ? "isolated" : `${h} hop${h === 1 ? "" : "s"}`;
    let rows = [];
    if (scope === "frontier") {
      for (const id of E.frontier(rt, st.unlocked)) {
        if (id === 0 || !visNode(rt.byId[id])) continue;
        rows.push({ id, hops: 1, via: "frontier", act: "unlock" });
      }
    } else if (scope === "visible") {
      const front = E.frontier(rt, st.unlocked);
      const visIds = rt.frozen ? rt.frozen.vis : E.visible(rt, st.unlocked, m);
      for (const id of visIds) {
        if (unl.has(id) || !visNode(rt.byId[id])) continue;
        let via = "beyond tickets", act = null;
        if (front.has(id)) { via = "frontier"; act = "unlock"; }
        else {
          const best = skips
            .filter(t => dist[id] != null && dist[id] <= 1 + t.n)
            .sort((a, b) => a.n - b.n)[0];
          if (best) { via = `skip ${best.n}`; act = "skip"; }
          else if (dist[id] != null && dist[id] >= 2 &&
              st.inventory.some(t => t.kind === "hop")) { via = "hop"; act = "hop"; }
        }
        rows.push({ id, hops: dist[id] == null ? null : dist[id], via, act });
      }
    } else if (scope === "skip") {
      if (!skips.length) {
        $("planCount").textContent = "";
        box.innerHTML = "<li class='muted'>No skip tickets held: award one above.</li>";
        $("planPage").textContent = "";
        return;
      }
      const seen = new Set();
      const front = E.frontier(rt, st.unlocked);
      for (const id of Object.keys(dist).map(Number)) {
        // Frontier nodes unlock normally — no sense spending a ticket.
        if (id === 0 || unl.has(id) || seen.has(id) || front.has(id) || !visNode(rt.byId[id])) continue;
        // Smallest sufficient ticket, mirroring the engine auto-pick.
        const best = skips
          .filter(t => dist[id] <= 1 + t.n)
          .sort((a, b) => a.n - b.n)[0];
        if (!best) continue;
        seen.add(id);
        rows.push({ id, hops: dist[id], via: `skip ${best.n}`, act: "skip" });
      }
    } else if (scope === "jump") {
      if (!jumps.length || !fromIds.length) {
        $("planCount").textContent = "";
        box.innerHTML = "<li class='muted'>" +
          (!jumps.length ? "No jump/choice tickets held: award one above."
            : "Unlock a node first: jumps launch from unlocked nodes.") + "</li>";
        $("planPage").textContent = "";
        return;
      }
      const jtSel = $("planJumpTicket"), jfSel = $("planJumpFrom");
      jtSel.innerHTML = jumps.map((t, i) => `<option value="${i}">${esc(ticketLabel(t))}</option>`).join("");
      planJumpTi = Math.max(0, Math.min(planJumpTi, jumps.length - 1));
      jtSel.value = String(planJumpTi);
      const t = jumps[planJumpTi];
      const defFrom = (selectedId != null && fromIds.includes(selectedId)) ? selectedId : fromIds[0];
      jfSel.innerHTML = fromIds.map(u => {
        const und = rt.byId[u];
        return `<option value="${u}">#${u} ${esc(und ? und.name : "?")}</option>`;
      }).join("");
      if (!fromIds.includes(planJumpFrom)) planJumpFrom = defFrom;
      jfSel.value = String(planJumpFrom);
      const from = planJumpFrom;
      const lim = t.kind === "choice" ? t.n : 1;
      E.jumpCandidates(rt, t.category, from, st.unlocked).slice(0, 200)
        .forEach(([dd, nd], idx) => {
          if (!visNode(nd)) return;
          rows.push({
            id: nd.id, hops: dist[nd.id] == null ? null : dist[nd.id],
            via: `${ticketLabel(t)} from #${from} · ${dd.toFixed(1)} away`,
            act: idx < lim ? "jump" : null,
            jump: { ticket: t, from },
          });
        });
    }
    // Filters.
    const q = (($("planQ") && $("planQ").value) || "").trim().toLowerCase();
    const cat = ($("planCat") && $("planCat").value) || "";
    const tag = ($("planTag") && $("planTag").value) || "";
    const affordOnly = $("planAfford") && $("planAfford").checked;
    if (q) rows = rows.filter(r => {
      const nd = rt.byId[r.id];
      return nd.name.toLowerCase().includes(q) ||
        (nd.source || "").toLowerCase().includes(q) ||
        nodeTags(nd).some(t => t.toLowerCase().includes(q));
    });
    if (cat) rows = rows.filter(r => rt.byId[r.id].file === cat);
    if (tag) rows = rows.filter(r => nodeTags(rt.byId[r.id]).includes(tag));
    if (affordOnly) rows = rows.filter(r => planAfford(st, rt, r.id, ccx));
    // Sort.
    const sort = ($("planSort") && $("planSort").value) || "cost";
    // Costs memoized per row: comparators must not call nodeCostFor.
    for (const r of rows) {
      r.cost = E.nodeCostFor(st, rt, r.id, ccx);
      r.cc = E.coreCostFor(st, rt, r.id, ccx);
    }
    const costOf = r => r.cost;
    const hopsOf = r => r.hops == null ? 1e9 : r.hops;
    const cmp = {
      cost: (a, b) => costOf(a) - costOf(b),
      costDesc: (a, b) => costOf(b) - costOf(a),
      rarity: (a, b) => rt.byId[b.id].rarity - rt.byId[a.id].rarity || costOf(a) - costOf(b),
      hops: (a, b) => hopsOf(a) - hopsOf(b) || costOf(a) - costOf(b),
      name: (a, b) => rt.byId[a.id].name.localeCompare(rt.byId[b.id].name),
      id: (a, b) => a.id - b.id,
    }[sort] || ((a, b) => costOf(a) - costOf(b));
    rows.sort(cmp);
    // Shared view: append reachable-but-hidden targets (id + method only),
    // unless a filter would need data we deliberately did not share.
    if (isShared() && !q && !cat && !tag && !affordOnly) {
      const hv = (rt.sharedView && rt.sharedView.hiddenReach) || {};
      const hidden = [];
      if (scope === "skip") {
        for (const h of (hv.skip || [])) hidden.push({ hidden: true, id: h.id, hops: h.n });
      } else if (scope === "hop") {
        for (const h of (hv.hop || [])) hidden.push({ hidden: true, id: h.id, hops: null });
      } else if (scope === "jump") {
        for (const h of (hv.jump || [])) {
          if (h.ticket === planJumpTi && h.from === planJumpFrom) hidden.push({ hidden: true, id: h.id, hops: null, from: h.from });
        }
      }
      hidden.sort((a, b) => a.id - b.id);
      rows = rows.concat(hidden);
    }
    const copyable = rows.filter(r => !r.hidden);
    $("planCount").textContent = `(${rows.length} node${rows.length === 1 ? "" : "s"})`;
    $("planCopy").onclick = () => {
      if (!copyable.length) return toast("Nothing to copy.", true);
      copyText(copyable.map(r => nodeText(rt.byId[r.id])).join("\n\n"),
        `${copyable.length} planned node${copyable.length === 1 ? "" : "s"}`);
    };
    const pages = Math.max(1, Math.ceil(rows.length / PLAN_PAGE));
    planPage = Math.max(0, Math.min(planPage, pages - 1));
    $("planPage").textContent = rows.length
      ? `${planPage * PLAN_PAGE + 1}–${Math.min(rows.length, (planPage + 1) * PLAN_PAGE)} of ${rows.length}` : "";
    $("planPrev").disabled = planPage === 0;
    $("planNext").disabled = planPage >= pages - 1;
    applyPlanVisibility();
    if (!rows.length) {
      box.innerHTML = "<li class='muted'>Nothing matches: loosen the filters.</li>";
      return;
    }
    for (const r of rows.slice(planPage * PLAN_PAGE, (planPage + 1) * PLAN_PAGE)) {
      if (r.hidden) {
        const li = document.createElement("li");
        li.innerHTML = `<div class="grow"><b>Hidden node #${r.id}</b> <span class="pill">hidden</span><br>` +
          `<span class="muted small">reachable by ${esc(scope)}${r.from != null ? ` from #${r.from}` : ""}` +
          `${r.hops != null ? ` · ${hopTxt(r.hops)}` : ""}: not included in this shared view</span></div>`;
        box.appendChild(li);
        continue;
      }
      const nd = rt.byId[r.id];
      const cost = r.cost, cc = r.cc;
      const ok = planAfford(st, rt, r.id, ccx);
      const tags = nodeTags(nd);
      const li = document.createElement("li");
      li.innerHTML = `<div class="grow"><b>#${r.id} ${esc(nd.name)}</b> ` +
        `<span class="pill">${esc(nd.file)} ${fmtR(nd.rarity)}</span>` +
        (tags.length ? " " + tagPills(tags, nd.file) : "") + `<br>` +
        `<span class="muted small">${E.fmt(cost)} pts${cc ? " + 1 core" : " · no core"} · ${hopTxt(r.hops)} · ${esc(r.via)}</span></div>`;
      const go = document.createElement("button");
      go.textContent = "View";
      go.title = `Open ${nd.name} in the node view`;
      go.addEventListener("click", () => { selectedId = r.id; showTab("node"); });
      li.appendChild(go);
      const cp = document.createElement("button");
      cp.textContent = "📋";
      cp.title = `Copy ${nd.name} text`;
      cp.addEventListener("click", () => copyText(nodeText(nd), nd.name));
      li.appendChild(cp);
      if (!isShared() && (r.act === "unlock" || r.act === "skip" || r.act === "hop")) {
        const b = document.createElement("button");
        const isSkip = r.act === "skip", isHop = r.act === "hop";
        b.textContent = isSkip ? "Skip →" : isHop ? "Hop →" : "Unlock";
        b.className = "primary";
        b.disabled = !ok;
        b.title = ok ? `${isSkip ? "Unlock with skip ticket: " : isHop ? "Unlock with hop ticket: " : "Unlock "}${nd.name}`
          : (st.cores < cc ? `Needs ${cc} core${cc === 1 ? "" : "s"} (award a ticket)` : `Needs ${E.fmt(cost)} pts`);
        b.addEventListener("click", async () => {
          const done = await mutate(({ st, rt }) =>
            isSkip ? E.unlockSkip(st, rt, r.id)
            : isHop ? E.unlockHop(st, rt, r.id)
            : E.unlock(st, rt, r.id));
          if (done) toast(`Unlocked ${nd.name}${isSkip ? " (skip)" : isHop ? " (hop)" : ""}.`);
        });
        li.appendChild(b);
      } else if (!isShared() && r.act === "jump" && r.jump) {
        const { ticket, from } = r.jump;
        const b = document.createElement("button");
        b.textContent = "Jump →";
        b.className = "primary";
        b.disabled = !ok;
        b.title = ok ? `Unlock with ${ticketLabel(ticket)} from #${from}`
          : (st.cores < cc ? `Needs ${cc} core${cc === 1 ? "" : "s"} (award a ticket)` : `Needs ${E.fmt(cost)} pts`);
        b.addEventListener("click", async () => {
          const done = await mutate(({ st, rt }) => {
            const lim = ticket.kind === "choice" ? ticket.n : 1;
            const list = E.jumpCandidates(rt, ticket.category, from, st.unlocked).slice(0, lim);
            const idx = list.findIndex(([, cand]) => cand.id === r.id);
            if (idx < 0) throw new E.ChaosError("no longer in reach of that ticket");
            return E.unlockJump(st, rt, ticket.category, from, idx);
          });
          if (done) toast(`Unlocked ${nd.name} (jump).`);
        });
        li.appendChild(b);
      }
      box.appendChild(li);
    }
  }
    const surveyed = rt.frozen
      ? ((rt.sharedView && rt.sharedView.surveyed) || [])
      : E.surveyNames(rt, st.unlocked, m).filter(([i]) => visNode(rt.byId[i]));
    if (surveyed.length) {
      const d = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = `Surveyed names (${surveyed.length})`;
      d.appendChild(s);
      const ul = document.createElement("ul");
      ul.className = "list";
      for (const [id, name] of surveyed.slice(0, 60)) {
        const li = document.createElement("li");
        li.innerHTML = `<div class="grow"><b>#${id} ${esc(name)}</b>` +
          (rt.byId[id] ? "" : ` <span class="pill">hidden</span>`) + `</div>`;
        if (rt.byId[id]) {
          const go = document.createElement("button");
          go.textContent = "View";
          go.addEventListener("click", () => { selectedId = id; showTab("node"); });
          li.appendChild(go);
        }
        ul.appendChild(li);
      }
      d.appendChild(ul);
      meta.appendChild(d);
    }
    await renderUnlockable(c, ccx);
    await renderPlanner(c, ccx);
  }

  // Inventory collapses to just its header, matching the unlock list toggle.
  let invOpen = true;
  function applyInvVisibility() {
    $("invList").style.display = invOpen ? "" : "none";
    $("invToggle").textContent = invOpen ? "Hide" : "Show";
  }
  $("invToggle").addEventListener("click", () => {
    invOpen = !invOpen;
    applyInvVisibility();
  });

  $("btnAward").addEventListener("click", async () => {
    const tier = $("tkTier").value, kind = $("tkKind").value;
    const n = parseInt($("tkN").value, 10) || 2;
    const cat = $("tkCat").value;
    const count = Math.max(1, Math.min(10, parseInt($("tkCount").value, 10) || 1));
    const wantTwin = $("tkTwin") && $("tkTwin").checked;
    const wantGamble = $("tkGamble") && $("tkGamble").checked;
    let spec = tier;
    if (kind === "skip") spec = `${tier} skip${n}`;
    else if (kind === "jump") spec = `${tier} ${cat} jump`;
    else if (kind === "choice") spec = `${tier} choice ${n} jump`;
    else if (kind === "hop") spec = `${tier} hop`;
    else if (kind === "coupon") spec = `${tier} coupon`;
    if (wantTwin) spec += " twin";
    let totalPts = 0, totalCores = 0;
    const notes = [];
    const ok = await mutate(({ st, rt }) => {
      const m = E.viewState(rt, st);
      if (wantGamble) {
        const have = m.gamble - ((st.meta_used || {}).gamble || 0);
        if (have < count) throw new E.ChaosError(`need ${count} gamble charges, have ${have}`);
      }
      let echoLeft = m.echo - (st.echo_used || 0);
      for (let i = 0; i < count; i++) {
        const useEcho = echoLeft > 0;
        const r = E.award(st, spec, m.ticket_bonus, useEcho, wantGamble, rt);
        if (useEcho) echoLeft--;
        totalPts += r.pts;
        totalCores += r.cores;
        const note = E.gambleNote(r.params);
        if (note) notes.push(note);
        if (r.params.value != null) notes.push(`coupon ${E.fmt(r.params.value)} pts`);
        if (r.params.wild) {
          const [d1, d2] = r.params.wild;
          notes.push(`wild ${d1}+${d2}` + (d1 === d2 ? " double!" : ""));
        }
      }
    });
    if (ok) toast(`Awarded ${count}× ${spec}: +${totalCores} core${totalCores === 1 ? "" : "s"}, +${E.fmt(totalPts)} pts.` +
      (notes.length ? ` 🎲 ${notes.join(" · ")}` : ""));
  });

  $("btnTrace").addEventListener("click", async () => {
    const c = await current();
    if (!c) return;
    const field = $("trField").value, q = $("trQ").value.trim();
    const ul = $("traceList");
    ul.innerHTML = "";
    if (!q) return toast("Type something to trace.", true);
    try {
      const res = E.trace(c.rt, c.st, field, q, 5).filter(r => visNode(r.node));
      saveDB(); // single-use traces (e.g. Scent Hound) spend a charge
      if (!res.length) ul.innerHTML = "<li class='muted'>No matches.</li>";
      for (const r of res) {
        const li = document.createElement("li");
        const tags = nodeTags(r.node);
        li.innerHTML = `<div class="grow"><b>#${r.node.id} ${esc(r.node.name)}</b> ` +
          `<span class="pill">${r.dist} hop${r.dist === 1 ? "" : "s"}</span>` +
          (tags.length ? " " + tagPills(tags, r.node.file) : "") + `<br>` +
          `<span class="muted small">${esc(r.path.map(p => c.rt.byId[p] ? c.rt.byId[p].name : "#" + p).join(" → "))}</span></div>`;
        const go = document.createElement("button");
        go.textContent = "View";
        go.addEventListener("click", () => { selectedId = r.node.id; showTab("node"); });
        li.appendChild(go);
        ul.appendChild(li);
      }
    } catch (e) { err(e); }
  });

  // ---- sharing (read-only snapshots) -------------------------------------
  function applySharedMode() {
    document.body.classList.add("shared-mode");
    for (const id of ["newTreeCard", "ioCard", "awardCard", "metaCard", "guideCard"]) {
      const el = $(id); if (el) el.style.display = "none";
    }
    const bs = $("btnShare"); if (bs) bs.style.display = "none";
    const banner = $("shareBanner");
    if (banner) {
      $("shareBannerText").textContent =
        "Only the owner's visible and unlocked nodes are included: never the seed, " +
        "generation settings, or hidden nodes. Unlocking and awarding are disabled." +
        (SHARED && SHARED.url ? " Data loaded from " + SHARED.url : "");
      banner.style.display = "block";
    }
  }

  async function loadSharedView(url) {
    if (!window.ChaosShare) throw new Error("share support failed to load");
    const res = await fetch(url, { redirect: "follow" });
    if (!res.ok) throw new Error(`couldn't load the shared view (HTTP ${res.status})`);
    let payload;
    try { payload = await res.json(); }
    catch (e) { throw new Error("the shared view isn't valid JSON"); }
    window.ChaosShare.validate(payload);
    const tree = { id: uid(), name: payload.name || "Shared tree", shared: true,
      static: true, dataVersion: payload.dataVersion || null, createdAt: Date.now() };
    SHARED = { url, payload, treeId: tree.id };
    DB.trees = [tree];
    DB.states = {};
    DB.states[tree.id] = Object.assign(E.newState(), payload.state);
    DB.activeId = tree.id;
    selectedId = 0;
    applySharedMode();
    renderTrees();
    await refreshAll();
    showTab("view3d");
    toast("Shared view loaded (read-only).");
  }

  // Share this view: snapshot -> paste host -> tree.html?share=<raw-url>.
  function shareLinkFor(rawUrl) {
    let base = "tree.html";
    try {
      const u = new URL("tree.html", location.href);
      u.search = ""; u.hash = "";
      base = u.href;
    } catch (e) { /* keep relative */ }
    return base + "?share=" + encodeURIComponent(rawUrl);
  }
  let shareUpload = null;
  function openShare() {
    if (isShared()) return;
    if (!activeTree()) return toast("Create or open a tree first, then share its view.", true);
    $("shareModal").classList.add("open");
    if ($("shareModal").scrollIntoView) $("shareModal").scrollIntoView({ block: "nearest" });
  }
  function closeShare() { $("shareModal").classList.remove("open"); }
  async function runShare() {
    const c = await current();
    if (!c) { $("shareStatus").textContent = "No active tree to share."; return; }
    let payload;
    try {
      payload = window.ChaosShare.collect(c.tree, c.rt, c.st, {
        name: c.tree.name, dataVersion: DATA.dataVersion,
        nodeVisible: nd => visNode(nd) && nodeShown(nd)
      });
    } catch (e) { err(e); return; }
    const text = JSON.stringify(payload);
    const whole = payload.nodes.length >= c.rt.nodes.length;
    $("shareJson").value = text;
    $("shareSize").textContent =
      `${payload.nodes.length} node${payload.nodes.length === 1 ? "" : "s"} · ${(text.length / 1024).toFixed(1)} KB`;
    $("shareFallback").open = false;
    $("shareResult").style.display = "none";
    $("shareStatus").textContent = "Uploading…";
    try {
      const out = await window.ChaosPaste.upload(text, {
        title: (c.tree.name || "Chaos Tree") + " (shared view)",
        expiration: $("shareExpiry").value
      });
      shareUpload = out;
      $("shareLink").value = shareLinkFor(out.rawUrl);
      $("shareResult").style.display = "block";
      $("shareStatus").textContent = "Uploaded via " + out.provider +
        (out.expiresAt ? " · expires " + out.expiresAt : "") +
        (whole ? " · notice: this view includes every node (a full reveal is active)." : "");
    } catch (e) {
      $("shareFallback").open = true;
      $("shareStatus").textContent = e.message + " You can still share manually below.";
    }
  }

  if ($("btnShare")) $("btnShare").addEventListener("click", openShare);
  if ($("btnShareSetup")) $("btnShareSetup").addEventListener("click", openShare);
  if ($("shareGo")) $("shareGo").addEventListener("click", runShare);
  if ($("shareClose")) $("shareClose").addEventListener("click", closeShare);
  if ($("shareModal")) $("shareModal").addEventListener("click", ev => {
    if (ev.target === $("shareModal")) closeShare();
  });
  if ($("shareCopy")) $("shareCopy").addEventListener("click", () => {
    if ($("shareLink").value) copyText($("shareLink").value, "link");
  });
  if ($("shareUseUrl")) $("shareUseUrl").addEventListener("click", () => {
    const u = $("shareManualUrl").value.trim();
    if (!/^https?:\/\//.test(u)) return toast("Enter the raw https:// URL of your paste.", true);
    $("shareLink").value = shareLinkFor(u);
    $("shareResult").style.display = "block";
    $("shareStatus").textContent = "Link ready: copying it shares this view.";
  });
  if ($("shareDelete")) $("shareDelete").addEventListener("click", async () => {
    if (!shareUpload) return;
    try {
      await window.ChaosPaste.remove(shareUpload);
      shareUpload = null;
      $("shareResult").style.display = "none";
      $("shareStatus").textContent = "Upload deleted.";
      toast("Upload deleted.");
    } catch (e) { err(e); }
  });
  window.__treeDebug = Object.assign(window.__treeDebug || {},
    { shareLinkFor, runShare, loadSharedView, openShare });

  // ---- boot ---------------------------------------------------------------
  fillTicketForm();
  $("showNsfw").checked = showNsfw();
  $("showNsfw").addEventListener("change", () => {
    DB.settings.showNsfw = $("showNsfw").checked;
    saveDB();
    updateNonconRows();
    refreshAll();
  });
  if ($("showNoncon")) {
    $("showNoncon").checked = showNoncon();
    $("showNoncon").addEventListener("change", () => {
      DB.settings.showNoncon = $("showNoncon").checked;
      saveDB();
      refreshAll();
    });
  }
  if ($("newNsfw")) $("newNsfw").addEventListener("change", updateNonconRows);
  updateNonconRows();
  if (!DB.guideSeen) $("guideCard").style.display = "block";
  $("btnGuideOk").addEventListener("click", () => {
    DB.guideSeen = true;
    saveDB();
    $("guideCard").style.display = "none";
  });
  // The mismatch banner is the moment a player notices their tree is on old
  // data, so offer the Upgrade flow right there instead of only in the rows.
  $("btnUpgradeActive").addEventListener("click", () => {
    const at = activeTree();
    if (!at) return;
    const row = document.querySelector(`#treeList button[data-tree-id="${at.id}"]`);
    if (!row) { toast("Couldn't find that tree's Upgrade button.", true); return; }
    if (row.scrollIntoView) row.scrollIntoView({ block: "nearest" });
    row.click();
  });
  $("findQ").addEventListener("input", () => { if (currentTab === "node") renderFinder(); });
  $("fileChecks").innerHTML = "";
  for (const f of ["ability", "item", "skill", "trait", "familiar"]) {
    const lab = document.createElement("label");
    lab.style.cssText = "display:flex;gap:6px;align-items:center;min-height:44px;flex:1;";
    lab.title = `Draw entries from ${f}. Uncheck all = use all five.`;
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.className = "fFile"; cb.value = f; cb.checked = true;
    cb.style.cssText = "width:22px;height:22px";
    const nm = document.createElement("span");
    nm.textContent = f;
    lab.append(cb, nm);
    $("fileChecks").appendChild(lab);
  }
  function refreshSrcCount() {
    const boxes = [...document.querySelectorAll(".srcCheck")];
    const n = boxes.filter(c => c.checked).length;
    $("srcCount").textContent = n === boxes.length ? "all" : `${n}/${boxes.length}`;
  }
  function srcExcluded() {
    return [...document.querySelectorAll(".srcCheck")]
      .filter(c => !c.checked).map(c => c.value);
  }
  function saveSrcExcluded() {
    DB.formExcluded = srcExcluded();
    saveDB();
  }
  function downloadJson(filename, obj) {
    const blob = new Blob([JSON.stringify(obj)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }
  (function buildSrcChecks() {
    const host = $("srcChecks");
    host.innerHTML = "";
    const FILES = ["ability", "item", "skill", "trait", "familiar"];
    const LETTER = { ability: "A", item: "I", skill: "S", trait: "T", familiar: "F" };
    const counts = {};
    for (const e of (DATA.entries || [])) {
      if (e.t === "tree" || !e.s) continue;
      counts[e.s] = counts[e.s] || {};
      counts[e.s][e.f] = (counts[e.s][e.f] || 0) + 1;
    }
    const breakdown = s => FILES.filter(f => counts[s][f])
      .map(f => `${counts[s][f]}${LETTER[f]}`).join(", ");
    const total = s => Object.values(counts[s]).reduce((a, b) => a + b, 0);
    for (const s of Object.keys(counts).sort((a, b) => a.localeCompare(b))) {
      const lab = document.createElement("label");
      lab.style.cssText = "display:flex;gap:6px;align-items:center;min-height:44px;flex:1;min-width:44%;";
      lab.title = `${total(s)} entries: ${breakdown(s)}`;
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.className = "srcCheck"; cb.value = s;
      cb.checked = true;
      cb.style.cssText = "width:22px;height:22px";
      cb.addEventListener("change", () => { refreshSrcCount(); saveSrcExcluded(); });
      const nm = document.createElement("span");
      nm.className = "srcbreak";
      nm.textContent = `${s} [${breakdown(s)}]`;
      lab.append(cb, nm);
      host.appendChild(lab);
    }
    const saved = new Set(DB.formExcluded || []);
    if (saved.size) {
      host.querySelectorAll("input").forEach(c => { c.checked = !saved.has(c.value); });
    }
    refreshSrcCount();
  })();
  $("srcAll").addEventListener("click", () => {
    document.querySelectorAll(".srcCheck").forEach(c => { c.checked = true; });
    refreshSrcCount(); saveSrcExcluded();
  });
  $("srcNone").addEventListener("click", () => {
    document.querySelectorAll(".srcCheck").forEach(c => { c.checked = false; });
    refreshSrcCount(); saveSrcExcluded();
  });
  $("srcExport").addEventListener("click", () => {
    downloadJson("chaos-tree-source-exclusions.json", {
      app: "chaos-tree", kind: "source-exclusions", version: 1,
      excluded: srcExcluded().sort()
    });
  });
  $("srcImport").addEventListener("click", () => $("fileSrc").click());
  $("fileSrc").addEventListener("change", async () => {
    const f = $("fileSrc").files[0];
    if (!f) return;
    try {
      const p = JSON.parse(await f.text());
      const listed = Array.isArray(p.excluded) ? p.excluded : null;
      if (!listed) throw new Error("not a source-exclusions file");
      const known = new Set([...document.querySelectorAll(".srcCheck")].map(c => c.value));
      const valid = listed.filter(s => known.has(s));
      document.querySelectorAll(".srcCheck").forEach(c => { c.checked = !valid.includes(c.value); });
      refreshSrcCount(); saveSrcExcluded();
      toast(`Excluded ${valid.length} source${valid.length === 1 ? "" : "s"}` +
        (listed.length > valid.length ? ` (${listed.length - valid.length} unknown ignored)` : "") + ".");
    } catch (e) { toast(e.message || "Import failed.", true); }
    $("fileSrc").value = "";
  });
  $("classLegend").innerHTML = "";
  for (const cl of (DATA.classes || [])) {
    const b = document.createElement("button");
    b.className = "pill";
    b.style.cssText = "margin:2px;min-height:36px;";
    b.dataset.cls = cl.name;
    b.title = `rarity < ${cl.max}: click to hide/show`;
    b.innerHTML = `<span class="dot" style="background:${esc(cl.color)}"></span>${esc(cl.name)}`;
    b.addEventListener("click", () => {
      if (hiddenClasses.has(cl.name)) hiddenClasses.delete(cl.name);
      else hiddenClasses.add(cl.name);
      b.style.opacity = hiddenClasses.has(cl.name) ? "0.35" : "1";
      requestDraw();
    });
    $("classLegend").appendChild(b);
  }
  const key = document.createElement("span");
  key.className = "pill";
  key.style.cssText = "margin:2px";
  key.title = "Locked, on the frontier, and covered by your wallet";
  key.textContent = "⬡ unlockable now";
  $("classLegend").appendChild(key);
  $("ownCat").innerHTML = `<option value="">All</option>` +
    E.CATEGORIES.map(c => `<option>${c}</option>`).join("");
  const tagOpts = `<option value="">All tags</option>` +
    allTags().map(t => `<option value="${esc(t)}">${esc(t)} (${tagCounts()[t] || 0})</option>`).join("");
  if ($("ownTag")) $("ownTag").innerHTML = tagOpts;
  if ($("newTag")) $("newTag").innerHTML = `<option value="">Any tag</option>` +
    allTags().map(t => `<option value="${esc(t)}">${esc(t)} (${tagCounts()[t] || 0})</option>`).join("");
  $("ownQ").addEventListener("input", () => { if (currentTab === "owned") renderOwned(); });
  $("ownCat").addEventListener("change", () => { if (currentTab === "owned") renderOwned(); });
  if ($("ownTag")) $("ownTag").addEventListener("change", () => { if (currentTab === "owned") renderOwned(); });
  if ($("planCat")) $("planCat").innerHTML = `<option value="">All</option>` +
    E.CATEGORIES.map(c => `<option>${c}</option>`).join("");
  if ($("planTag")) $("planTag").innerHTML = tagOpts;
  const rerenderTickets = () => { if (currentTab === "tickets") renderTickets(); };
  if ($("planScope")) $("planScope").addEventListener("change", () => { planPage = 0; rerenderTickets(); });
  if ($("planToggle")) $("planToggle").addEventListener("click", () => {
    planOpen = !planOpen;
    applyPlanVisibility();
  });
  if ($("planQ")) $("planQ").addEventListener("input", rerenderTickets);
  if ($("planCat")) $("planCat").addEventListener("change", rerenderTickets);
  if ($("planTag")) $("planTag").addEventListener("change", rerenderTickets);
  if ($("planSort")) $("planSort").addEventListener("change", rerenderTickets);
  if ($("planAfford")) $("planAfford").addEventListener("change", rerenderTickets);
  if ($("planJumpTicket")) $("planJumpTicket").addEventListener("change", ev => {
    planJumpTi = parseInt(ev.target.value || "0", 10) || 0; planPage = 0; rerenderTickets();
  });
  if ($("planJumpFrom")) $("planJumpFrom").addEventListener("change", ev => {
    planJumpFrom = parseInt(ev.target.value || "", 10) || null; planPage = 0; rerenderTickets();
  });
  if ($("planPrev")) $("planPrev").addEventListener("click", async () => {
    if (planPage > 0) { planPage--; rerenderTickets(); }
  });
  if ($("planNext")) $("planNext").addEventListener("click", async () => { planPage++; rerenderTickets(); });
  try {
    const n = (DATA.entries || []).length;
    $("dataVer").textContent = `data v${DATA.dataVersion || "?"} · ${n} entries`;
  } catch (e) {}
  renderTrees();
  if (DB.activeId && getTree(DB.activeId)) showTab("view3d");
  else showTab("trees");
  refreshAll();

  // Opening a ?share= link loads a read-only snapshot instead of local trees.
  (function () {
    let url = null;
    try { url = new URLSearchParams(location.search).get("share"); } catch (e) {}
    if (!url) return;
    loadSharedView(url).catch(e => { err(e); showTab("trees"); });
  })();
})();
