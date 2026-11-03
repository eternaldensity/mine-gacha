"use strict";
/* Full entry database: sortable/filterable/searchable table over every
 * gacha entry, with expandable descriptions. */
(function () {
  const DATA = window.CHAOS_DATA || { entries: [], tiers: [], classes: [] };
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
  const CATS = ["ability", "item", "skill", "trait", "familiar"];
  const PAGE = 200;
  // Whole-number rarities display with .0, matching the gacha/tree copy text.
  const fmtR = r => Number.isInteger(r) ? r.toFixed(1) : String(r);

  function toast(msg, isErr) {
    const t = $("toast");
    t.textContent = msg;
    t.className = "toast" + (isErr ? " err" : "");
    t.style.display = "block";
    clearTimeout(t._h);
    t._h = setTimeout(() => { t.style.display = "none"; }, 3200);
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
  // Shared entry copy format used across the site: name on its own line,
  // then the metadata in parentheses, then the full description.
  function entryText(e) {
    const cls = classOf(e.r);
    const tags = entryTags(e);
    return `${e.name}\n(${fmtR(e.r)}, ${cls.name}, ${e.f}` +
      `${e.s ? ", " + e.s : ""}${tags.length ? ", #" + tags.join(" #") : ""})` +
      (e.d ? `\n${e.d}` : "");
  }

  function entryTags(e) { return (e && (e.tags || e.tg)) || []; }
  // Tag descriptions come from the original site's per-category dictionaries
  // (web/data/tags.js, generated from tools/tagdata/).
  const TAGDOCS = window.CHAOS_TAGS || {};
  function tagDesc(tag, cat) {
    const list = (cat && TAGDOCS[cat]) || [];
    const hit = list.find(t => t.tag === tag);
    if (hit) return hit.desc;
    for (const c of Object.keys(TAGDOCS)) {
      const h = TAGDOCS[c].find(t => t.tag === tag);
      if (h) return h.desc;
    }
    return "";
  }
  function tagPill(tag, cat) {
    const d = tagDesc(tag, cat);
    return `<span class="pill"${d ? ` title="${esc(d)}"` : ""}>🏷 ${esc(tag)}</span>`;
  }

  function checkedSources() {
    return [...document.querySelectorAll(".eqSrc")].filter(c => c.checked).map(c => c.value);
  }

  const state = {
    sort: { key: "name", dir: 1 },
    q: "", cats: new Set(CATS), tags: new Set(),
    rmin: null, rmax: null,
    shown: PAGE
  };

  function classOf(r) {
    for (const c of DATA.classes) if (r < c.max) return c;
    return DATA.classes[DATA.classes.length - 1];
  }
  function checkedSources() {
    return [...document.querySelectorAll(".eqSrc")].filter(c => c.checked).map(c => c.value);
  }

  const COLS = [
    { key: "n", label: "#" },
    { key: "name", label: "Name" },
    { key: "f", label: "Cat" },
    { key: "r", label: "Rarity" },
    { key: "s", label: "Source" },
    { key: "tags", label: "Tags" }
  ];

  function filtered() {
    const q = state.q.trim().toLowerCase();
    const srcs = checkedSources();
    return DATA.entries.filter(e => {
      if (!state.cats.has(e.f)) return false;
      if (srcs.length && !srcs.includes(e.s)) return false;
      if (state.rmin != null && e.r < state.rmin) return false;
      if (state.rmax != null && e.r > state.rmax) return false;
      if (state.tags.size) {
        const et = entryTags(e);
        let hit = false;
        for (const t of state.tags) if (et.includes(t)) { hit = true; break; }
        if (!hit) return false;
      }
      if (!q) return true;
      if (e.name.toLowerCase().includes(q)) return true;
      if ((e.s || "").toLowerCase().includes(q)) return true;
      if ((e.d || "").toLowerCase().includes(q)) return true;
      if (entryTags(e).some(t => t.toLowerCase().includes(q))) return true;
      return false;
    });
  }

  function renderHead() {
    const head = $("eqHead");
    head.innerHTML = "";
    for (const col of COLS) {
      const th = document.createElement("th");
      th.style.cssText = "text-align:left;padding:4px;border-bottom:1px solid var(--line);white-space:nowrap";
      const b = document.createElement("button");
      b.style.cssText = "min-height:44px;padding:6px 8px;font-size:0.85rem;";
      b.textContent = col.label + (state.sort.key === col.key ? (state.sort.dir > 0 ? " ▲" : " ▼") : "");
      b.addEventListener("click", () => {
        if (state.sort.key === col.key) state.sort.dir *= -1;
        else state.sort = { key: col.key, dir: 1 };
        state.shown = PAGE;
        render();
      });
      th.appendChild(b);
      head.appendChild(th);
    }
  }

  function val(e) {
    switch (state.sort.key) {
      case "n": return e.n;
      case "name": return e.name.toLowerCase();
      case "f": return e.f;
      case "r": return e.r;
      case "s": return (e.s || "").toLowerCase();
      case "tags": return entryTags(e).join(",");
      default: return 0;
    }
  }

  function render() {
    renderHead();
    const body = $("eqBody");
    body.innerHTML = "";
    const rows = filtered();
    rows.sort((a, b) => {
      const va = val(a), vb = val(b);
      const d = va < vb ? -1 : va > vb ? 1 : a.n - b.n;
      return d * state.sort.dir;
    });
    const tagBit = state.tags.size ? ` · tags: ${[...state.tags].sort().join(", ")}` : "";
    $("eqCount").textContent = `${rows.length} of ${DATA.entries.length} entries${tagBit} (tap a row for its description)`;
    const more = $("eqMore");
    more.style.display = rows.length > state.shown ? "" : "none";
    more.textContent = `Show more (${rows.length - state.shown} remaining)`;
    for (const e of rows.slice(0, state.shown)) {
      const cls = classOf(e.r);
      const tags = entryTags(e);
      const tr = document.createElement("tr");
      tr.style.cssText = "border-top:1px solid var(--line);cursor:pointer";
      tr.innerHTML =
        `<td style="padding:8px">${e.n}</td>` +
        `<td style="padding:8px"><span class="dot" style="background:${esc(cls.color)}"></span>${esc(e.name)}</td>` +
        `<td style="padding:8px">${esc(e.f)}</td>` +
        `<td style="padding:8px">${e.r}</td>` +
        `<td style="padding:8px">${esc(e.s || "—")}</td>` +
        `<td style="padding:8px">${tags.map(t => tagPill(t, e.f)).join(" ")}</td>`;
      const cp = document.createElement("button");
      cp.textContent = "📋";
      cp.title = `Copy ${e.name}`;
      cp.style.cssText = "margin-left:6px";
      cp.addEventListener("click", ev => {
        ev.stopPropagation();
        copyText(entryText(e), e.name);
      });
      tr.children[1].appendChild(cp);
      tr.addEventListener("click", () => {
        const next = tr.nextSibling;
        if (next && next.classList && next.classList.contains("desc")) {
          next.remove();
          return;
        }
        const dr = document.createElement("tr");
        dr.className = "desc";
        const td = document.createElement("td");
        td.setAttribute("colspan", "6");
        td.style.cssText = "padding:8px 8px 12px 26px";
        td.innerHTML = (tags.length ? tags.map(t => tagPill(t, e.f)).join(" ") + "<br><br>" : "") +
          linkify(e.d || "(no description)");
        dr.appendChild(td);
        tr.after(dr);
      });
      body.appendChild(tr);
    }
  }

  // Tag chips: only tags used by the selected categories, sorted by how many
  // entries carry them, with a text filter (the official taxonomy has 260).
  function renderTagChips() {
    const tg = $("eqTags");
    if (!tg) return;
    const q = ($("eqTagQ") && $("eqTagQ").value || "").trim().toLowerCase();
    const tagCounts = {};
    for (const e of (DATA.entries || [])) {
      if (!state.cats.has(e.f)) continue;
      for (const t of entryTags(e)) tagCounts[t] = (tagCounts[t] || 0) + 1;
    }
    const tags = Object.keys(tagCounts)
      .filter(t => !q || t.includes(q) || tagDesc(t).toLowerCase().includes(q))
      .sort((a, b) => tagCounts[b] - tagCounts[a] || a.localeCompare(b));
    tg.innerHTML = "";
    const shown = q ? tags : tags.slice(0, 60);
    for (const t of shown) {
      const b = document.createElement("button");
      b.textContent = `${t} (${tagCounts[t]})`;
      const d = tagDesc(t);
      b.title = d ? `${t} — ${d}` : `Show entries tagged ${t}`;
      if (state.tags.has(t)) b.classList.add("sel");
      b.addEventListener("click", () => {
        if (state.tags.has(t)) state.tags.delete(t);
        else state.tags.add(t);
        b.classList.toggle("sel", state.tags.has(t));
        state.shown = PAGE;
        render();
      });
      tg.appendChild(b);
    }
    if (!shown.length) {
      tg.innerHTML = "<span class='muted small'>No tags match.</span>";
    } else if (!q && tags.length > shown.length) {
      const more = document.createElement("button");
      more.textContent = `+${tags.length - shown.length} more (search above)`;
      more.addEventListener("click", () => {
        for (const t of tags.slice(shown.length)) {
          const b = document.createElement("button");
          b.textContent = `${t} (${tagCounts[t]})`;
          const d = tagDesc(t);
          b.title = d ? `${t} — ${d}` : `Show entries tagged ${t}`;
          if (state.tags.has(t)) b.classList.add("sel");
          b.addEventListener("click", () => {
            if (state.tags.has(t)) state.tags.delete(t);
            else state.tags.add(t);
            b.classList.toggle("sel", state.tags.has(t));
            state.shown = PAGE;
            render();
          });
          tg.insertBefore(b, more);
        }
        more.remove();
      });
      tg.appendChild(more);
    }
    if ($("eqTagCount")) {
      $("eqTagCount").textContent = state.tags.size
        ? `· ${state.tags.size} selected` : `· ${tags.length} available`;
    }
  }

  function refreshSrcCount() {
    const boxes = [...document.querySelectorAll(".eqSrc")];
    const n = boxes.filter(c => c.checked).length;
    $("eqSrcCount").textContent = n === boxes.length ? "all" : `${n}/${boxes.length}`;
  }

  // category chips + tag chips + source checkboxes
  (function bootFilters() {
    const cg = $("eqCats");
    for (const c of CATS) {
      const b = document.createElement("button");
      b.className = "sel";
      b.textContent = c;
      b.addEventListener("click", () => {
        if (state.cats.has(c)) state.cats.delete(c);
        else state.cats.add(c);
        b.classList.toggle("sel", state.cats.has(c));
        state.shown = PAGE;
        renderTagChips();
        render();
      });
      cg.appendChild(b);
    }
    renderTagChips();
    const counts = {};
    for (const e of (DATA.entries || [])) {
      if (!e.s) continue;
      counts[e.s] = (counts[e.s] || 0) + 1;
    }
    const host = $("eqSources");
    for (const s of Object.keys(counts).sort((a, b) => a.localeCompare(b))) {
      const lab = document.createElement("label");
      lab.style.cssText = "display:flex;gap:6px;align-items:center;min-height:44px;flex:1;min-width:44%;";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.className = "eqSrc"; cb.value = s; cb.checked = true;
      cb.style.cssText = "width:22px;height:22px";
      cb.addEventListener("change", () => { refreshSrcCount(); state.shown = PAGE; render(); });
      const nm = document.createElement("span");
      nm.textContent = `${s} (${counts[s]})`;
      lab.append(cb, nm);
      host.appendChild(lab);
    }
    refreshSrcCount();
  })();

  $("eq").addEventListener("input", () => { state.q = $("eq").value; state.shown = PAGE; render(); });
  $("eqMin").addEventListener("change", () => {
    const v = parseFloat($("eqMin").value);
    state.rmin = isNaN(v) ? null : v;
    state.shown = PAGE; render();
  });
  $("eqMax").addEventListener("change", () => {
    const v = parseFloat($("eqMax").value);
    state.rmax = isNaN(v) ? null : v;
    state.shown = PAGE; render();
  });
  $("eqAll").addEventListener("click", () => {
    document.querySelectorAll(".eqSrc").forEach(c => { c.checked = true; });
    refreshSrcCount(); state.shown = PAGE; render();
  });
  $("eqNone").addEventListener("click", () => {
    document.querySelectorAll(".eqSrc").forEach(c => { c.checked = false; });
    refreshSrcCount(); state.shown = PAGE; render();
  });
  $("eqMore").addEventListener("click", () => { state.shown += PAGE; render(); });
  if ($("eqTagQ")) $("eqTagQ").addEventListener("input", renderTagChips);

  try {
    const n = (DATA.entries || []).length;
    $("dataVer").textContent = `data v${DATA.dataVersion || "?"} · ${n} entries`;
  } catch (e) {}
  window.__entries = { state, filtered, render };
  render();
})();
