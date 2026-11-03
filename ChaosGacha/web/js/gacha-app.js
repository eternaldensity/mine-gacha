"use strict";
/* Chaos Gacha web app: mobile-first roller with ticket wallet + history. */
(function () {
  const G = window.ChaosGacha;
  const DATA = window.CHAOS_DATA || { entries: [], tiers: [], classes: [] };
  const LS = "chaosGacha.v1";
  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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
  // Whole-number rarities display with .0 so the wheel reads consistently.
  const fmtR = r => Number.isInteger(r) ? r.toFixed(1) : String(r);

  function entryTags(e) {
    if (G && typeof G.entryTags === "function") {
      try { return G.entryTags(e) || []; } catch (err) { /* fall through */ }
    }
    return (e && (e.tags || e.tg)) || [];
  }
  function tagPills(tags, cat) {
    return (tags || []).map(t => {
      const d = tagDesc(t, cat);
      return `<span class="pill"${d ? ` title="${esc(d)}"` : ""}>🏷 ${esc(t)}</span>`;
    }).join(" ");
  }
  // Tag descriptions from the original site's dictionaries (data/tags.js).
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
  function tagCount(tag) {
    if (DATA.tagCounts && DATA.tagCounts[tag] != null) return DATA.tagCounts[tag];
    let n = 0;
    for (const e of (DATA.entries || [])) if (entryTags(e).includes(tag)) n++;
    return n;
  }
  // Tags offered in the pickers follow the selected category (the original
  // taxonomy is per-category), so "random" lists everything.
  function tagsForCategory(cat) {
    const s = new Set();
    for (const e of (DATA.entries || [])) {
      if (e.t === "tree") continue;
      if (cat && cat !== "random" && e.f !== cat) continue;
      for (const t of entryTags(e)) s.add(t);
    }
    return [...s].sort((a, b) => tagCount(b) - tagCount(a) || a.localeCompare(b));
  }
  function fillTagSelects() {
    for (const id of ["fTag", "tkTag"]) {
      const sel = $(id);
      if (!sel) continue;
      const cur = sel.value;
      const list = tagsForCategory(category);
      sel.innerHTML = `<option value="">Any tag</option>` +
        list.map(t => `<option value="${esc(t)}">${esc(t)} (${tagCount(t)})</option>`).join("");
      if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
    }
    if ($("fTag")) {
      $("fTag").title = "Original-site tags for the selected category. " +
        "Hover an entry's pill to see what a tag means.";
    }
  }

  function toast(msg, isErr) {
    const t = $("toast");
    t.textContent = msg;
    t.className = "toast" + (isErr ? " err" : "");
    t.style.display = "block";
    clearTimeout(t._h);
    t._h = setTimeout(() => { t.style.display = "none"; }, 3000);
  }

  function load() {
    try {
      const raw = localStorage.getItem(LS);
      if (raw) {
        const d = JSON.parse(raw);
        d.tickets = d.tickets || []; d.history = d.history || [];
        d.settings = d.settings || { spin: "normal" };
        d.settings.filters = d.settings.filters || {};
        return d;
      }
    } catch (e) {}
    return { tickets: [], history: [], settings: { spin: "normal", filters: {} } };
  }
  function save() {
    try { localStorage.setItem(LS, JSON.stringify(DB)); }
    catch (e) { toast("Storage full.", true); }
  }
  let DB = load();
  const uid = () => Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
  let lastResult = null;

  function resultText(r) {
    const cls = G.rarityClass(DATA.classes, r.rarity);
    const tags = entryTags(r);
    return `${r.name}\n(${fmtR(r.rarity)}, ${cls.name}, ${r.category}${r.source ? ", " + r.source : ""}${tags.length ? ", #" + tags.join(" #") : ""})` +
      (r.d20 != null ? ` 🎲${r.d20} ${G.gamblerLabel({ effect: r.geffect })}` : "") +
      (r.description ? `\n${r.description}` : "");
  }
  window.__gacha = window.__gacha || {};
  window.__gacha.resultText = resultText;

  // tabs
  document.querySelectorAll("#tabs button").forEach(b =>
    b.addEventListener("click", () => {
      document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("active", x === b));
      document.querySelectorAll(".tabpage").forEach(p =>
        p.classList.toggle("active", p.id === "tab-" + b.dataset.tab));
      if (b.dataset.tab === "history") renderHistory();
    }));

  // Tier button colors (sampled from the original site's tier art).
  function hexRgb(h) {
    return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  }
  function mix(h, target, amt) {
    const [r, g, b] = hexRgb(h);
    const m = (c, t) => Math.round(c + (t - c) * amt);
    return `rgb(${m(r, target[0])},${m(g, target[1])},${m(b, target[2])})`;
  }
  function tierStyle(t) {
    const base = t.color || "#555";
    const [r, g, b] = hexRgb(base);
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    const fg = lum > 0.6 ? "#1a1a1a" : "#ffffff";
    return `background:linear-gradient(180deg, ${mix(base, [255, 255, 255], 0.35)} 0%, ${base} 45%, ${mix(base, [0, 0, 0], 0.3)} 100%);` +
      `color:${fg};text-shadow:${lum > 0.6 ? "0 1px 0 rgba(255,255,255,.35)" : "0 1px 2px rgba(0,0,0,.6)"};`;
  }

  // preset + category pickers
  let preset = "gold", category = "random";
  const CATS = ["random", "ability", "item", "skill", "trait", "familiar"];

  // The source selection is global and independent of which category is on
  // screen: switching category only changes which sources are shown, never
  // which are allowed. Exclusions are tracked explicitly so a partial view
  // can never silently shrink the allowed set (the old DOM-read did).
  function allSourceNames() {
    const set = new Set();
    for (const e of DATA.entries) if (e.t !== "tree" && e.s) set.add(e.s);
    return [...set].sort((a, b) => a.localeCompare(b));
  }
  let excludedSources = new Set();
  const sourceAllowed = s => !excludedSources.has(s);
  function allowedSourceList() {
    return allSourceNames().filter(sourceAllowed);
  }
  function refreshSources() {
    const host = $("gfSources");
    host.innerHTML = "";
    const FILES = ["ability", "item", "skill", "trait", "familiar"];
    const LETTER = { ability: "A", item: "I", skill: "S", trait: "T", familiar: "F" };
    const counts = {};
    for (const e of DATA.entries) {
      if (e.t === "tree" || !e.s) continue;
      if (category !== "random" && e.f !== category) continue;
      counts[e.s] = counts[e.s] || {};
      counts[e.s][e.f] = (counts[e.s][e.f] || 0) + 1;
    }
    const breakdown = s => FILES.filter(f => counts[s][f])
      .map(f => `${counts[s][f]}${LETTER[f]}`).join(", ");
    for (const s of Object.keys(counts).sort((a, b) => a.localeCompare(b))) {
      const lab = document.createElement("label");
      lab.style.cssText = "display:flex;gap:6px;align-items:center;min-height:44px;flex:1;min-width:44%;";
      lab.title = `${s}: ${breakdown(s)}`;
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.className = "gfCheck"; cb.value = s;
      cb.checked = sourceAllowed(s);
      cb.style.cssText = "width:22px;height:22px";
      cb.addEventListener("change", () => {
        if (cb.checked) excludedSources.delete(s); else excludedSources.add(s);
        refreshSrcCount(); updatePoolCount(); collectFilters();
      });
      const nm = document.createElement("span");
      nm.className = "srcbreak";
      nm.textContent = `${s} [${breakdown(s)}]`;
      lab.append(cb, nm);
      host.appendChild(lab);
    }
    refreshSrcCount();
    updatePoolCount();
  }
  function refreshSrcCount() {
    const total = allSourceNames().length;
    const allowed = allowedSourceList().length;
    $("gfCount").textContent = allowed === total ? "all" : `${allowed}/${total}`;
  }
  function collectFilters() {
    const rmin = parseFloat($("fRmin").value), rmax = parseFloat($("fRmax").value);
    const tag = $("fTag") ? $("fTag").value || "" : "";
    const F = {
      q: $("q").value,
      sources: allowedSourceList(),
      rmin: isNaN(rmin) ? null : rmin,
      rmax: isNaN(rmax) ? null : rmax,
      hideNsfw: !!$("fNsfw").checked,
      hideNoncon: !!$("fNoncon").checked,
      hideTech: !!$("fTech").checked,
      dedup: !!$("fDedup").checked
    };
    if (tag) F.tag = tag;
    DB.settings.filters = {
      q: F.q, sources: F.sources, sourcesExcluded: [...excludedSources],
      rmin: $("fRmin").value, rmax: $("fRmax").value,
      hideNsfw: F.hideNsfw, hideNoncon: F.hideNoncon, hideTech: F.hideTech, dedup: F.dedup,
      tag
    };
    save();
    return F;
  }
  function restoreFilters() {
    const F = (DB.settings && DB.settings.filters) || {};
    $("q").value = F.q || "";
    $("fRmin").value = F.rmin || "";
    $("fRmax").value = F.rmax || "";
    $("fNsfw").checked = F.hideNsfw !== false; // safe by default
    $("fNoncon").checked = F.hideNoncon !== false; // safe by default
    $("fTech").checked = !!F.hideTech;
    $("fDedup").checked = !!F.dedup;
    if ($("fTag")) $("fTag").value = F.tag || "";
    updateNonconRow();
    // Exclusions are authoritative; migrate the older "allowed list" format
    // (and the even older single-source setting) once, then keep exclusions.
    const known = new Set(allSourceNames());
    if (Array.isArray(F.sourcesExcluded)) {
      excludedSources = new Set(F.sourcesExcluded.filter(s => known.has(s)));
    } else if ((Array.isArray(F.sources) && F.sources.length) || F.source) {
      const allowed = new Set(F.sources || [F.source]);
      excludedSources = new Set([...known].filter(s => !allowed.has(s)));
    } else {
      excludedSources = new Set();
    }
    refreshSources();
  }
  function updatePoolCount() {
    try {
      const F = {
        q: $("q").value, sources: allowedSourceList(),
        rmin: parseFloat($("fRmin").value) || null,
        rmax: parseFloat($("fRmax").value) || null,
        hideNsfw: !!$("fNsfw").checked, hideNoncon: !!$("fNoncon").checked, hideTech: !!$("fTech").checked,
        tag: $("fTag") ? $("fTag").value || "" : ""
      };
      if (!F.tag) delete F.tag;
      const cats = category === "random" ? CATS.slice(1) : [category];
      let n = 0;
      for (const c of cats) {
        const ql = (F.q || "").trim().toLowerCase();
        n += DATA.entries.filter(e => {
          if (e.f !== c || e.t === "tree") return false;
          if (F.sources.length && !F.sources.includes(e.s)) return false;
          if (F.rmin != null && e.r < F.rmin) return false;
          if (F.rmax != null && e.r > F.rmax) return false;
          if (F.hideNsfw && e.nsfw) return false;
          if (F.hideNoncon && e.noncon) return false;
          if (F.hideTech && e.tech) return false;
          if (F.tag && !entryTags(e).includes(F.tag)) return false;
          if (ql && !(e.name.toLowerCase().includes(ql) || (e.s || "").toLowerCase().includes(ql))) return false;
          return true;
        }).length;
      }
      const tagBit = F.tag ? ` · #${F.tag}` : "";
      $("poolCount").textContent = `≈${n} entr${n === 1 ? "y" : "ies"} in pool${tagBit}.`;
    } catch (e) { /* controls not ready */ }
  }
  function renderPickers() {
    const pg = $("presetGrid");
    pg.innerHTML = "";
    for (const t of DATA.tiers) {
      const b = document.createElement("button");
      b.className = "pick" + (preset === t.name ? " sel" : "");
      b.setAttribute("style", tierStyle(t));
      b.innerHTML = `<b>${esc(t.name)}</b><br><span class="small" style="opacity:.85">⌀${t.avg}</span>`;
      b.addEventListener("click", () => {
        preset = t.name;
        $("cMin").value = t.min; $("cAvg").value = t.avg; $("cMax").value = t.max;
        renderPickers();
      });
      pg.appendChild(b);
    }
    const cg = $("catGrid");
    cg.innerHTML = "";
    for (const c of CATS) {
      const b = document.createElement("button");
      b.className = "pick" + (category === c ? " sel" : "");
      b.textContent = c === "random" ? "🎲 random" : c;
      b.addEventListener("click", () => { category = c; renderPickers(); refreshSources(); });
      cg.appendChild(b);
    }
    $("tkTier").innerHTML = DATA.tiers.map(t => `<option>${t.name}</option>`).join("");
    $("tkCat").innerHTML = CATS.map(c => `<option>${c}</option>`).join("");
    fillTagSelects();
  }

  function showResult(r, keepMulti) {
    lastResult = r;
    const cls = G.rarityClass(DATA.classes, r.rarity);
    const tags = entryTags(r);
    $("resultCard").style.display = "block";
    $("resultCard").style.boxShadow = `0 0 32px ${cls.color}44, var(--shadow)`;
    if (!keepMulti) $("multiCard").style.display = "none";
    $("resultBody").innerHTML =
      `<div class="small" style="color:${esc(cls.color)}">${esc(cls.name)} ${esc(r.category)}${r.source ? " [" + esc(r.source) + "]" : ""}</div>` +
      `<div class="result-name"><span class="dot" style="background:${esc(cls.color)}"></span><b>${esc(r.name)}</b> · ${fmtR(r.rarity)}</div>` +
      (tags.length ? `<div style="margin:4px 0">${tagPills(tags, r.category)}</div>` : "") +
      `<div class="small muted">${r.odds.toFixed(2)}% odds</div>` +
      (r.d20 != null ? `<div class="small muted">🎲 Gambler d20 → ${r.d20}: ${esc(G.gamblerLabel({ effect: r.geffect }))}${r.gambleNote ? ` (${esc(r.gambleNote)})` : ""}</div>` : "") +
      (r.advantage > 1 ? `<div class="small muted">⚡ Advantage ×${r.advantage}: your pick from ${r.advantage} wheels</div>` : "") +
      (r.description ? `<p>${linkify(r.description)}</p>` : "");
    $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showDestroyed(g, note) {
    lastResult = null;
    const cls = G.rarityClass(DATA.classes, 0);
    $("resultCard").style.display = "block";
    $("resultCard").style.boxShadow = "";
    $("multiCard").style.display = "none";
    $("resultBody").innerHTML =
      `<div class="result-name">💥 Ticket destroyed</div>` +
      `<div class="small muted">🎲 Gambler d20 → ${g.d20}: Destroyed. ` +
      (note || "No roll, no history entry.") + `</div>`;
    $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function tierNames() { return DATA.tiers.map(t => t.name); }
  function presetNums(name) {
    const t = DATA.tiers.find(t => t.name === name);
    return t ? { min: t.min, avg: t.avg, max: t.max } : null;
  }

  // Advantage rolls a batch at once and the roller picks which result to
  // keep (rarity is no judge): a ticket's Advantage prefix rolls that many
  // wheels; the Gambler trait's "Advantage" d20 result adds one more.
  // Everything else (odds, filters, category) is unchanged.
  function doRoll(min, max, avg, cat, ticketId, tierName, ticketTag, advantage) {
    if (spinning) return;
    $("filterBox").open = false;
    const F = collectFilters();
    // Ticket theme tags combine with the filter-box tag (AND): a ticket for
    // #holy rolled with the filter on #undead needs both (likely empty, and
    // the error tells you to loosen filters).
    if (ticketId && !ticketTag) {
      const t = DB.tickets.find(x => x.id === ticketId);
      if (t && t.tag) ticketTag = t.tag;
    }
    if (ticketTag) {
      const both = [...new Set([F.tag, ticketTag].filter(Boolean))];
      delete F.tag;
      if (both.length) F.tags = both;
    }
    const tp = DATA.tiers.find(t => t.name === (tierName || preset));
    F.flat = !!(tp && tp.flat);
    if (F.dedup) F.exclude = DB.history.map(h => h.name);
    let g = null;
    if (DB.settings.gambler) {
      g = G.gamblerApply(tierNames(), tierName || "bronze", cat);
      if (g.effect === "rankUp" || g.effect === "rankDown") {
        const pn = presetNums(g.tier);
        if (pn) { min = pn.min; avg = pn.avg; max = pn.max; }
      }
      cat = g.cat;
      if (g.effect === "destroyed") {
        if (ticketId) DB.tickets = DB.tickets.filter(t => t.id !== ticketId);
        save(); renderTickets();
        showDestroyed(g);
        return;
      }
    }
    const rolls = Math.max(1, advantage | 0) + (g && g.effect === "advantage" ? 1 : 0);
    const rollOnce = () => G.roll(DATA.entries, DATA.tiers, cat, min, max, avg, F);
    let results;
    try {
      results = [];
      for (let i = 0; i < rolls; i++) results.push(rollOnce());
    } catch (e) { toast(e.message, true); return; }
    // The ticket is spent as soon as the wheels land, but nothing is
    // recorded until the roller has chosen what to keep (advantage) — the
    // kept result is whatever they pick, not simply the highest rarity.
    if (ticketId) DB.tickets = DB.tickets.filter(t => t.id !== ticketId);
    save(); renderTickets();
    const keep = (chosen) => {
      if (rolls > 1) chosen.advantage = rolls;
      if (g) { chosen.d20 = g.d20; chosen.geffect = g.effect; }
      DB.history.unshift(Object.assign({ id: uid(), at: Date.now(), min, max, avg }, chosen));
      if (DB.history.length > 500) DB.history.length = 500;
      save(); renderStats();
      showResult(chosen, rolls > 1);
      if (rolls > 1) renderResultList(results, chosen, `⚡ Advantage ×${rolls}: kept your pick`, "★ kept");
    };
    // How the batch is presented once the wheels settle.
    const present = () => {
      if (rolls <= 1) { keep(results[0]); return; }
      showChoicePrompt(rolls);
      renderChoiceList(results, keep);
    };
    const speed = (DB.settings && DB.settings.spin) || "normal";
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (speed === "off" || reduced || !window.requestAnimationFrame) { present(); return; }
    spinReels(results, min, max, avg, F, SPIN_SPEEDS[speed] || SPIN_SPEEDS.normal, cat, present);
  }

  const SPIN_SPEEDS = {
    fast: { dur: 1200, n: 16 },
    normal: { dur: 2600, n: 30 },
    slow: { dur: 4200, n: 46 },
    slower: { dur: 6200, n: 64 }
  };
  const TRAIL_ROWS = 8; // decoys past the winner so the list end never shows
  let spinning = false;

  // One row in the batch list: colour dot, name, category/rarity pill,
  // tags, an optional trailing marker, source, and a 👁 button to read the
  // full description.
  function resultListItem(r, extra) {
    const cls = G.rarityClass(DATA.classes, r.rarity);
    const li = document.createElement("li");
    li.innerHTML = `<div class="grow"><span class="dot" style="background:${esc(cls.color)}"></span>` +
      `<b>${esc(r.name)}</b> <span class="pill">${esc(r.category)} ${fmtR(r.rarity)}</span>` +
      (entryTags(r).length ? " " + tagPills(entryTags(r), r.category) : "") +
      (extra || "") +
      `<br><span class="muted small">${esc(r.source || "—")}</span></div>`;
    const b = document.createElement("button");
    b.textContent = "👁";
    b.title = `Read ${r.name}`;
    b.addEventListener("click", () => showResult(r, true));
    li.appendChild(b);
    return li;
  }

  // Summary of a batch (×10 multi-pull, or an advantage roll once kept),
  // with the kept/best result starred.
  function renderResultList(results, best, headText, bestLabel) {
    $("multiHead").textContent = headText;
    const ul = $("multiList");
    ul.innerHTML = "";
    results.slice().sort((a, b) => b.rarity - a.rarity).forEach(r => {
      const star = r === best
        ? ` <span class="pill" style="border-color:var(--accent);color:var(--accent)">${esc(bestLabel || "★ best")}</span>`
        : "";
      ul.appendChild(resultListItem(r, star));
    });
    $("multiCard").style.display = "block";
  }

  // Advantage batch before the roller has chosen: every result gets a
  // Keep button (plus 👁 to read it), because the best one is their call.
  function renderChoiceList(results, onKeep) {
    $("multiHead").textContent = `⚡ Advantage ×${results.length}: read them, then keep one`;
    const ul = $("multiList");
    ul.innerHTML = "";
    for (const r of results) {
      const li = resultListItem(r);
      const keep = document.createElement("button");
      keep.textContent = "✓ Keep";
      keep.className = "primary";
      keep.title = `Keep ${r.name} and discard the rest`;
      keep.addEventListener("click", () => onKeep(r));
      li.appendChild(keep);
      ul.appendChild(li);
    }
    $("multiCard").style.display = "block";
  }

  function showChoicePrompt(n) {
    lastResult = null;
    $("resultCard").style.display = "block";
    $("resultCard").style.boxShadow = "";
    $("multiCard").style.display = "block";
    $("resultBody").innerHTML =
      `<div class="result-name">⚡ Advantage ×${n}</div>` +
      `<div class="small muted">${n} wheels landed: read the results below and keep the one you want.</div>`;
    $("resultCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Spin one reel per result simultaneously (advantage rolls several at
  // once); all lanes share the same easing so they settle together. onDone
  // runs once every lane has stopped, to present the results.
  function spinReels(rolls, min, max, avg, filt, opt, reqCat, onDone) {
    const host = $("reelRow");
    host.innerHTML = "";
    const lanes = [];
    for (const r of rolls) {
      let items;
      try {
        items = G.drawStrip(DATA.entries, reqCat || r.category, min, max, avg, filt, opt.n + TRAIL_ROWS);
      } catch (e) { continue; }
      const winIdx = opt.n;
      items.splice(winIdx, 0, { name: r.name, rarity: r.rarity, source: r.source, category: r.category, tags: entryTags(r).slice() });
      // The winner is predetermined; don't let a decoy double it up visually.
      for (const j of [winIdx - 1, winIdx + 1]) {
        if (j < 0 || j >= items.length || items[j].name !== r.name) continue;
        const other = j < winIdx ? items[j - 1] : items[j + 1];
        for (let t = 0; t < 30; t++) {
          const k = Math.floor(Math.random() * items.length);
          if (Math.abs(k - winIdx) <= 1 || Math.abs(k - j) <= 1) continue;
          const a = items[k];
          if (a.name === r.name) continue;
          if (other && a.name === other.name) continue;
          if (k > 0 && items[k - 1].name === r.name) continue;
          if (k < items.length - 1 && items[k + 1].name === r.name) continue;
          items[k] = items[j];
          items[j] = a;
          break;
        }
      }
      const reel = document.createElement("div");
      reel.className = "reel";
      reel.title = "Tap to skip";
      const inner = document.createElement("div");
      inner.className = "reel-inner";
      for (const it of items) {
        const cls = G.rarityClass(DATA.classes, it.rarity);
        const row = document.createElement("div");
        row.className = "rrow";
        const itTags = entryTags(it);
        row.innerHTML = `<span class="dot" style="background:${esc(cls.color)}"></span>` +
          `<span class="nm">${esc(it.name)}${itTags.length ? ` <span class="muted small">#${itTags.map(esc).join(" #")}</span>` : ""}</span>` +
          `<span class="pill">${esc(it.category)} ${fmtR(it.rarity)}</span>`;
        inner.appendChild(row);
      }
      reel.appendChild(inner);
      host.appendChild(reel);
      lanes.push({ r, reel, inner, winIdx, rows: Array.from(inner.children) });
    }
    if (!lanes.length) { if (onDone) onDone(); return; }
    $("reelCard").style.display = "block";
    $("resultCard").style.display = "none";
    $("rollBtn").disabled = true;
    spinning = true;
    const first = lanes[0];
    const rowh = first.rows.length ? first.rows[0].offsetHeight || 54 : 54;
    const viewH = first.reel.clientHeight || rowh * 5;
    for (const lane of lanes) {
      lane.total = Math.max(0, lane.winIdx * rowh + rowh / 2 - viewH / 2);
    }
    const t0 = performance.now();
    let done = false;
    const finish = () => { done = true; };
    for (const lane of lanes) lane.reel.onclick = finish;
    function frame(now) {
      if (done) now = t0 + opt.dur;
      const t = Math.min(1, (now - t0) / opt.dur);
      const p = 1 - Math.pow(1 - t, 4); // ease-out: fast whizz, gentle settle
      for (const lane of lanes) {
        const off = lane.total * p;
        lane.inner.style.transform = `translateY(${-off}px)`;
        for (let i = 0; i < lane.rows.length; i++) {
          const center = i * rowh + rowh / 2 - off;
          const d = Math.min(1, Math.abs(center - viewH / 2) / (viewH / 2));
          lane.rows[i].style.transform = `scaleY(${(1 - 0.6 * Math.pow(d, 1.3)).toFixed(3)})`;
          lane.rows[i].style.opacity = (1 - 0.8 * Math.pow(d, 1.5)).toFixed(3);
        }
      }
      if (t >= 1) {
        for (const lane of lanes) {
          const w = lane.rows[lane.winIdx];
          if (w) w.classList.add("winner");
          lane.reel.onclick = null;
        }
        spinning = false;
        $("rollBtn").disabled = false;
        if (onDone) onDone();
        return;
      }
      window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  $("rollBtn").addEventListener("click", () => {
    const min = parseFloat($("cMin").value), avg = parseFloat($("cAvg").value), max = parseFloat($("cMax").value);
    if (!(min < max) || isNaN(avg)) return toast("Need min < max and a numeric avg.", true);
    doRoll(min, max, avg, category, null, preset);
  });

  $("btnMulti").addEventListener("click", () => {
    if (spinning) return;
    $("filterBox").open = false;
    const min = parseFloat($("cMin").value), avg = parseFloat($("cAvg").value), max = parseFloat($("cMax").value);
    if (!(min < max) || isNaN(avg)) return toast("Need min < max and a numeric avg.", true);
    const F = collectFilters();
    const histExcl = F.dedup ? DB.history.map(h => h.name) : [];
    const useGamble = !!DB.settings.gambler;
    const results = [];
    let destroyed = 0;
    try {
      for (let i = 0; i < 10; i++) {
        let mm = min, ma = avg, mx = max, cc = category, g = null;
        if (useGamble) {
          g = G.gamblerApply(tierNames(), preset, category);
          if (g.effect === "rankUp" || g.effect === "rankDown") {
            const pn = presetNums(g.tier);
            if (pn) { mm = pn.min; ma = pn.avg; mx = pn.max; }
          }
          cc = g.cat;
          if (g.effect === "destroyed") { destroyed++; continue; }
        }
        // A batch never repeats itself: always exclude this batch's
        // results so far (plus history when skip-already-rolled is on).
        F.exclude = histExcl.concat(results.map(r => r.name));
        const effTier = g ? g.tier : preset;
        F.flat = !!((DATA.tiers.find(t => t.name === effTier) || {}).flat);
        const rollOnce = () => G.roll(DATA.entries, DATA.tiers, cc, mm, mx, ma, F);
        let r = rollOnce();
        if (g && g.effect === "advantage") {
          const r2 = rollOnce();
          if (r2.rarity >= r.rarity) {
            r2.gambleNote = `kept ${fmtR(r2.rarity)} over ${fmtR(r.rarity)}`;
            r = r2;
          } else {
            r.gambleNote = `kept ${fmtR(r.rarity)} over ${fmtR(r2.rarity)}`;
          }
        }
        if (g) { r.d20 = g.d20; r.geffect = g.effect; }
        results.push(r);
      }
    } catch (e) { toast(e.message + (results.length ? ` (${results.length} landed first)` : ""), true); }
    if (!results.length) {
      showDestroyed({ d20: "—" }, "Gambler destroyed all ten tickets. Brutal.");
      return;
    }
    const stamped = results.map(r => Object.assign({ id: uid(), at: Date.now(), min, max, avg }, r));
    DB.history.unshift(...stamped);
    if (DB.history.length > 500) DB.history.length = 500;
    save(); renderTickets(); renderStats();
    let best = results[0];
    for (const r of results) if (r.rarity > best.rarity) best = r;
    showResult(best);
    renderResultList(results, best, `best of ${results.length}` +
      (destroyed ? ` (${destroyed} destroyed)` : "") + ` below`);
  });

  $("btnCopy").addEventListener("click", async () => {
    if (!lastResult) return;
    const t = resultText(lastResult);
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
      toast("Copied!");
    } catch (e) { toast("Copy failed.", true); }
  });

  $("btnAddTicket").addEventListener("click", () => {
    const tag = $("tkTag") ? $("tkTag").value || "" : "";
    const adv = $("tkAdv") ? parseInt($("tkAdv").value, 10) || 1 : 1;
    const t = { id: uid(), tier: $("tkTier").value, cat: $("tkCat").value };
    if (tag) t.tag = tag;
    if (adv > 1) t.adv = adv;
    DB.tickets.push(t);
    save(); renderTickets();
  });

  function tierOf(name) { return DATA.tiers.find(t => t.name === name) || DATA.tiers.find(t => t.name === "gold"); }

  function renderTickets() {
    $("ticketCount").textContent = DB.tickets.length ? `(${DB.tickets.length})` : "";
    const ul = $("ticketList");
    ul.innerHTML = DB.tickets.length ? "" : "<li class='muted'>No tickets: quick-roll above, or add tickets here and spend them.</li>";
    for (const t of DB.tickets) {
      const li = document.createElement("li");
      const tp = tierOf(t.tier);
      const adv = t.adv | 0;
      li.innerHTML = `<div class="grow"><span class="pill" style="${esc(tierStyle(tp))}border:none">${esc(t.tier)}</span> <span class="pill">${esc(t.cat)}</span>` +
        (adv > 1 ? ` <span class="pill" style="border-color:var(--accent);color:var(--accent)">⚡ Advantage ×${adv}</span>` : "") +
        (t.tag ? ` <span class="pill">🏷 ${esc(t.tag)}</span>` : "") + `</div>`;
      const b = document.createElement("button");
      b.textContent = adv > 1 ? `Roll ${adv}⚡` : "Roll 🎲"; b.className = "primary";
      b.title = adv > 1 ? `Roll ${adv} wheels at once and pick which to keep` : "Roll this ticket";
      b.addEventListener("click", () => {
        const p = tierOf(t.tier);
        doRoll(p.min, p.max, p.avg, t.cat, t.id, t.tier, t.tag || "", adv);
      });
      li.appendChild(b);
      ul.appendChild(li);
    }
  }

  function renderStats() {
    const box = $("statBody");
    const h = DB.history;
    if (!h.length) { box.innerHTML = "<span class='muted'>No rolls yet.</span>"; return; }
    let best = h[0];
    const byClass = {};
    for (const r of h) {
      if (r.rarity > best.rarity) best = r;
      const cn = G.rarityClass(DATA.classes, r.rarity).name;
      byClass[cn] = (byClass[cn] || 0) + 1;
    }
    const bc = G.rarityClass(DATA.classes, best.rarity);
    box.innerHTML =
      `<div class="kv"><span class="k">Rolls</span><b>${h.length}</b></div>` +
      `<div class="kv"><span class="k">Best</span><b><span class="dot" style="background:${esc(bc.color)}"></span>${esc(best.name)} (${fmtR(best.rarity)})</b></div>` +
      `<div style="margin-top:4px">` +
      Object.entries(byClass).map(([k, v]) => `<span class="pill" style="margin:2px">${esc(k)}×${v}</span>`).join("") +
      `</div>`;
  }

  function renderHistory() {
    renderStats();
    $("histCount").textContent = DB.history.length ? `(${DB.history.length})` : "";
    const ul = $("histList");
    ul.innerHTML = DB.history.length ? "" : "<li class='muted'>No rolls yet.</li>";
    for (const h of DB.history.slice(0, 200)) {
      const cls = G.rarityClass(DATA.classes, h.rarity);
      const li = document.createElement("li");
      li.innerHTML = `<div class="grow"><span class="dot" style="background:${esc(cls.color)}"></span>` +
        `<b>${esc(h.name)}</b> <span class="pill">${esc(h.category)} ${fmtR(h.rarity)}</span>` +
        (entryTags(h).length ? " " + tagPills(entryTags(h), h.category) : "") +
        (h.d20 != null ? ` <span class="pill" title="${esc(G.gamblerLabel({ effect: h.geffect }))}">🎲${h.d20}</span>` : "") +
        (h.advantage > 1 ? ` <span class="pill" title="Kept the best of ${h.advantage} wheels">⚡${h.advantage}</span>` : "") + `<br>` +
        `<span class="muted small">${esc(h.source || "—")} · ${new Date(h.at).toLocaleString()} · ${h.odds.toFixed(2)}%</span></div>`;
      const b = document.createElement("button");
      b.textContent = "👁";
      b.title = "View";
      b.addEventListener("click", () => {
        const rollTab = [...document.querySelectorAll("#tabs button")]
          .find(x => x.dataset && x.dataset.tab === "roll");
        if (rollTab) rollTab.click();
        showResult(h);
      });
      li.appendChild(b);
      ul.appendChild(li);
    }
  }

  $("btnClearHist").addEventListener("click", () => {
    if (!DB.history.length || !confirm("Clear roll history?")) return;
    DB.history = []; save(); renderHistory();
  });
  $("btnExportHist").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify({ app: "chaos-gacha", v: 1, tickets: DB.tickets, history: DB.history })], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "chaos-gacha-history.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });
  $("btnImportHist").addEventListener("click", () => $("fileHist").click());
  $("fileHist").addEventListener("change", async () => {
    const f = $("fileHist").files[0];
    if (!f) return;
    try {
      const p = JSON.parse(await f.text());
      if (!p || (p.app && p.app !== "chaos-gacha")) throw new Error("not a chaos-gacha file");
      DB.tickets = Array.isArray(p.tickets) ? p.tickets : [];
      DB.history = Array.isArray(p.history) ? p.history : [];
      save(); renderTickets(); renderHistory();
      toast("Imported.");
    } catch (e) { toast(e.message || "Import failed.", true); }
    $("fileHist").value = "";
  });

  renderPickers();
  $("cMin").value = 1.5; $("cAvg").value = 3.3; $("cMax").value = 5.3;
  try {
    const n = (DATA.entries || []).length;
    $("dataVer").textContent = `data v${DATA.dataVersion || "?"} · ${n} entries`;
  } catch (e) {}
  $("spinSpeed").value = (DB.settings && DB.settings.spin) || "normal";
  $("gambler").checked = !!(DB.settings && DB.settings.gambler);
  $("gambler").addEventListener("change", () => {
    DB.settings.gambler = $("gambler").checked;
    save();
  });
  $("spinSpeed").addEventListener("change", () => {
    DB.settings.spin = $("spinSpeed").value;
    save();
  });
  fillTagSelects();
  restoreFilters();
  if ($("fTag")) {
    // restoreFilters repopulates the selects; re-apply the saved tag choice.
    const savedTag = (DB.settings && DB.settings.filters && DB.settings.filters.tag) || "";
    if (savedTag) $("fTag").value = savedTag;
    updatePoolCount();
  }
  $("gfAll").addEventListener("click", () => {
    excludedSources = new Set();
    refreshSources(); collectFilters();
  });
  $("gfNone").addEventListener("click", () => {
    excludedSources = new Set(allSourceNames());
    refreshSources(); collectFilters();
  });
  $("gfExport").addEventListener("click", () => {
    const excluded = [...excludedSources].sort();
    const blob = new Blob([JSON.stringify({
      app: "chaos-gacha", kind: "source-exclusions", version: 1, excluded
    })], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "chaos-gacha-source-exclusions.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });
  $("gfImport").addEventListener("click", () => $("fileGfSrc").click());
  $("fileGfSrc").addEventListener("change", async () => {
    const f = $("fileGfSrc").files[0];
    if (!f) return;
    try {
      const p = JSON.parse(await f.text());
      const listed = Array.isArray(p.excluded) ? p.excluded : null;
      if (!listed) throw new Error("not a source-exclusions file");
      const known = new Set(allSourceNames());
      const valid = listed.filter(s => known.has(s));
      excludedSources = new Set(valid);
      refreshSources(); collectFilters();
      toast(`Excluded ${valid.length} source${valid.length === 1 ? "" : "s"}` +
        (listed.length > valid.length ? ` (${listed.length - valid.length} unknown ignored)` : "") + ".");
    } catch (e) { toast(e.message || "Import failed.", true); }
    $("fileGfSrc").value = "";
  });
  for (const id of ["q", "fRmin", "fRmax", "fNsfw", "fNoncon", "fTech", "fDedup", "fTag"]) {
    if (!$(id)) continue;
    $(id).addEventListener("change", () => { collectFilters(); updatePoolCount(); });
    $(id).addEventListener("input", updatePoolCount);
  }
  // The Noncon toggle only appears once NSFW content itself is allowed in.
  function updateNonconRow() {
    const row = $("fNonconRow");
    if (row) row.style.display = $("fNsfw").checked ? "none" : "";
  }
  $("fNsfw").addEventListener("change", updateNonconRow);
  renderTickets();
})();
