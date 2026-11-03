"use strict";
/* Gacha roll logic port (Gacha.py run_gacha/randomizer/read_file_with_weight).
 * Pool = all entries except Tree-tagged ones; rarity-pull then ±0.2 filter,
 * weights 1/4^|avg-rarity|. */
window.ChaosGacha = (function () {
  function rarityPull(min, max, avg, rnd, exp) {
    rnd = rnd || Math.random;
    const k = exp || 4;
    const vals = [], weights = [];
    let x = min;
    while (x < max) {
      vals.push(x);
      x += 0.1;
      weights.push(1 / Math.pow(k, Math.abs(avg - x)));
    }
    let total = 0;
    for (const w of weights) total += w;
    let pick = rnd() * total, acc = 0, idx = vals.length - 1;
    for (let i = 0; i < vals.length; i++) {
      acc += weights[i];
      if (acc >= pick) { idx = i; break; }
    }
    return vals[idx] + 0.1;
  }

  function cleanDesc(d) {
    // Strip leading # markers and (Tag) tokens only; interior characters
    // (including # inside URLs) are content and must survive.
    return String(d || "").replace(/^#+/, "")
      .replace(/\((Nsfw|Tech|Character|Gacha|Noncon)\)/g, "")
      .replace(/\((Tags?:[^)]*)\)/g, "")
      .replace(/\((Tome|Tree)\)/g, "")
      .replace(/\(Meta:[^)]*\)/g, "").trim();
  }

  function entryTags(e) {
    return e.tags || e.tg || [];
  }

  // filters: {q, source|sources, rmin, rmax, hideNsfw, hideNoncon, hideTech, exclude[], flat, tag|tags}.
  // flat=true flattens rarity weighting to uniform (wild tickets).
  // A plain string is treated as {q} (backwards compatible); a single
  // source string behaves like a one-element sources list.
  // tag is a single thematic tag; tags is a list (entry must have all of them).
  function normFilt(f) {
    if (typeof f === "string") return { q: f };
    return f || {};
  }

  function wantedTags(F) {
    if (Array.isArray(F.tags) && F.tags.length) return F.tags.map(t => String(t).toLowerCase());
    if (F.tag) return [String(F.tag).toLowerCase()];
    return [];
  }

  // category: one of the 5, or "random".
  function buildPool(entries, category, filt, rnd) {
    rnd = rnd || Math.random;
    const F = normFilt(filt);
    const ql = (F.q || "").trim().toLowerCase();
    const srcs = F.sources || (F.source ? [F.source] : null);
    const excl = F.exclude && F.exclude.length ? new Set(F.exclude) : null;
    const wt = wantedTags(F);
    const matchCat = cat => entries.filter(e => {
      if (e.f !== cat || e.t === "tree") return false;
      if (srcs && srcs.length && !srcs.includes(e.s)) return false;
      if (F.rmin != null && e.r < F.rmin) return false;
      if (F.rmax != null && e.r > F.rmax) return false;
      if (F.hideNsfw && e.nsfw) return false;
      if (F.hideNoncon && e.noncon) return false;
      if (F.hideTech && e.tech) return false;
      if (excl && excl.has(e.name)) return false;
      if (wt.length) {
        const et = entryTags(e).map(t => String(t).toLowerCase());
        for (const w of wt) if (!et.includes(w)) return false;
      }
      if (ql && !(e.name.toLowerCase().includes(ql) || (e.s || "").toLowerCase().includes(ql))) return false;
      return true;
    });
    if (category === "random") {
      // Try categories in random order so sparse filters (e.g. a theme tag
      // with entries in only one or two categories) still resolve instead
      // of failing on an empty pick.
      const cats = ["ability", "item", "skill", "trait", "familiar"];
      for (let i = cats.length - 1; i > 0; i--) {
        const j = Math.floor(rnd() * (i + 1));
        [cats[i], cats[j]] = [cats[j], cats[i]];
      }
      for (const cat of cats) {
        const pool = matchCat(cat);
        if (pool.length) return { cat, pool };
      }
      throw new Error("no entries match (loosen the filters)");
    }
    const pool = matchCat(category);
    if (!pool.length) throw new Error("no entries match (loosen the filters)");
    return { cat: category, pool };
  }

  function drawOne(pool, min, max, avg, rnd, exp) {
    const pull = rarityPull(min, max, avg, rnd, exp);
    // Flat mode pairs its uniform pull with a wide window so sparse
    // regions (Trash, high tiers) actually resolve instead of missing.
    const window = (exp === 1) ? 1.0 : 0.2;
    const filt = pool.filter(e => Math.abs(e.r - pull) <= window);
    if (!filt.length) return null;
    const k = exp || 4;
    const fw = filt.map(e => 1 / Math.pow(k, Math.abs(avg - e.r)));
    let total = 0;
    for (const w of fw) total += w;
    let pick = rnd() * total, acc = 0, idx = filt.length - 1;
    for (let i = 0; i < filt.length; i++) {
      acc += fw[i];
      if (acc >= pick) { idx = i; break; }
    }
    return { entry: filt[idx], weight: fw[idx], pull };
  }

  function roll(entries, tiers, category, min, max, avg, filt, rnd) {
    rnd = rnd || Math.random;
    const exp = normFilt(filt).flat ? 1 : 4;
    const { cat, pool } = buildPool(entries, category, filt, rnd);
    const wOf = e => 1 / Math.pow(exp, Math.abs(avg - e.r));
    let weightsum = 0;
    for (const e of pool) if (e.r <= max && min < e.r) weightsum += wOf(e);
    if (weightsum <= 0) throw new Error("rarity range matches nothing");
    for (let attempt = 0; attempt < 200; attempt++) {
      const hit = drawOne(pool, min, max, avg, rnd, exp);
      if (!hit) continue;
      const e = hit.entry;
      return {
        category: cat, name: e.name, rarity: e.r,
        source: e.s || "", description: cleanDesc(e.d),
        meta: e.m || [], tags: entryTags(e).slice(),
        odds: 100 * hit.weight / weightsum, pull: Math.round(hit.pull * 10) / 10
      };
    }
    throw new Error("could not find a match (try widening the range)");
  }

  // Candidate strip for the spin animation: plausible results drawn through
  // the same pull/filter/weight path as roll(). Decoys only — the caller
  // splices the true result in afterwards, so this shapes the theater for
  // variety: never the same entry twice in a row, and preferably nothing
  // repeated within the last few rows. `category` may be "random", in
  // which case each row resolves its own category.
  function drawStrip(entries, category, min, max, avg, filt, count, rnd) {
    rnd = rnd || Math.random;
    // "random" resolves per row so a random ticket's wheel mixes types
    // instead of echoing the winner's category all the way down.
    const wanted = category === "random"
      ? ["ability", "item", "skill", "trait", "familiar"] : [category];
    const pools = [];
    for (const c of wanted) {
      try {
        const built = buildPool(entries, c, filt, rnd);
        if (built.pool.length) pools.push(built);
      } catch (e) { /* category filtered out entirely */ }
    }
    if (!pools.length) throw new Error("no entries match (loosen the filters)");
    const exp = normFilt(filt).flat ? 1 : 4;
    const distinct = new Set(
      pools.flatMap(p => p.pool.map(e => e.name))).size > 1;
    const items = [];
    const push = (e, c) => items.push(
      { name: e.name, rarity: e.r, source: e.s || "", category: c, meta: e.m || [], tags: entryTags(e).slice() });
    const prevName = () => items.length ? items[items.length - 1].name : null;
    // Uniform in-ticket-range pick, used when the weighted draw keeps
    // repeating: variety is mandatory for theater, exact odds are not.
    const rangedFallback = pool => {
      const prev = prevName();
      const cands = pool.filter(e => e.r > min && e.r <= max && e.name !== prev);
      if (!cands.length) return null;
      return cands[Math.floor(rnd() * cands.length)];
    };
    let guard = 0;
    while (items.length < count && guard++ < count * 60) {
      let pick = null, pickCat = null, fallback = null, fallbackCat = null;
      for (let t = 0; t < 12 && !pick; t++) {
        const P = pools[Math.floor(rnd() * pools.length)];
        const hit = drawOne(P.pool, min, max, avg, rnd, exp);
        if (!hit) continue;
        const e = hit.entry;
        if (distinct && e.name === prevName()) {
          fallback = fallback || e; fallbackCat = fallbackCat || P.cat;
          continue;
        }
        if (items.slice(-3).some(it => it.name === e.name)) {
          fallback = fallback || e; fallbackCat = fallbackCat || P.cat;
          continue;
        }
        pick = e; pickCat = P.cat;
      }
      const prev = prevName();
      let e = pick, c = pickCat;
      if (!e && fallback && fallback.name !== prev) { e = fallback; c = fallbackCat; }
      if (!e) {
        const P = pools[Math.floor(rnd() * pools.length)];
        e = rangedFallback(P.pool);
        if (e) c = P.cat;
        else if (fallback) { e = fallback; c = fallbackCat; }
      }
      if (e) push(e, c);
    }
    let i = 0, skips = 0, pi = 0;
    while (items.length < count && pools.length &&
           skips++ < count * 4 + pools.length) {
      const P = pools[pi++ % pools.length];
      const e = P.pool[i++ % P.pool.length];
      if (distinct && e.name === prevName()) continue;
      push(e, P.cat);
    }
    return items;
  }

  function rarityClass(classes, r) {
    for (const c of classes) if (r < c.max) return c;
    return classes[classes.length - 1];
  }

  // Gambler trait (d20 ticket mods). Tiers ordered lowest -> highest.
  function gamblerRoll(rnd) {
    rnd = rnd || Math.random;
    const d20 = 1 + Math.floor(rnd() * 20);
    const effect = d20 === 20 ? "rankUp"
      : d20 >= 17 ? "advantage"
      : d20 >= 13 ? "changeType"
      : d20 >= 8 ? "nothing"
      : d20 >= 2 ? "rankDown" : "destroyed";
    return { d20, effect };
  }
  const GAMBLE_CATS = ["ability", "item", "skill", "trait", "familiar"];
  // Gambler rank graph (mirrors the tree engine): gold<->platinum skip
  // over aluminium, mythical<->divine skip over wild.
  const RANK_UP = {
    trash: "bronze", bronze: "silver", silver: "gold",
    gold: "platinum", aluminium: "platinum",
    platinum: "diamond", diamond: "legendary",
    legendary: "mythical", mythical: "divine",
    wild: "divine", divine: "transcendent",
    transcendent: "transcendent"
  };
  const RANK_DOWN = {
    trash: null, bronze: "trash", silver: "bronze",
    gold: "silver", aluminium: "gold", platinum: "gold",
    diamond: "platinum", legendary: "diamond",
    mythical: "legendary", wild: "mythical",
    divine: "mythical", transcendent: "divine"
  };
  function gamblerApply(tiers, tier, cat, rnd) {
    const { d20, effect } = gamblerRoll(rnd);
    let t = tier, c = cat, advantage = false, destroyed = false;
    if (effect === "rankUp") t = RANK_UP[tier] != null ? RANK_UP[tier] : tier;
    else if (effect === "rankDown") t = RANK_DOWN[tier] || tier;
    else if (effect === "advantage") advantage = true;
    else if (effect === "destroyed") destroyed = true;
    else if (effect === "changeType") {
      const pool = GAMBLE_CATS.filter(x => x !== cat);
      c = pool[Math.floor((rnd || Math.random)() * pool.length)];
    }
    return { d20, effect, tier: t, cat: c, advantage, destroyed };
  }
  function gamblerLabel(g) {
    return { rankUp: "Rank Up", advantage: "Advantage", changeType: "Changed Type",
      nothing: "No change", rankDown: "Rank Down", destroyed: "Destroyed" }[g.effect];
  }

  return { rarityPull, cleanDesc, entryTags, roll, drawStrip, rarityClass,
    gamblerRoll, gamblerApply, gamblerLabel };
})();
