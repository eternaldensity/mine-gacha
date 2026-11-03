"use strict";
/* Chaos Tree usage-engine port (tools/chaos_tree_use.py). Same rules:
 * synthetic root free; every node costs 1 core + 10^rarity points (under
 * Root Pact, nodes within two connections of the root cost no core but 10x
 * points); tickets pool tier points into
 * a shared wallet; sight/reveal extend visibility; special tickets and
 * tree-meta abilities reach further. Operates on a runtime tree from
 * ChaosGen.buildRuntime(). */
window.ChaosEngine = (function () {
  // Tier ladder, lowest first. Wild has no fixed value: awarding a wild
  // ticket rolls 2d8, takes the smaller as N for 10^(N+1) points, doubled
  // on doubles.
  const TIER_POINTS = {
    trash: 5, bronze: 50, silver: 500, gold: 5000, aluminium: 25000,
    platinum: 50000, diamond: 500000,
    legendary: 5000000, mythical: 50000000, wild: 0, divine: 500000000,
    transcendent: 5000000000
  };
  const TIERS = ["trash", "bronze", "silver", "gold", "aluminium",
    "platinum", "diamond",
    "legendary", "mythical", "wild", "divine", "transcendent"];
  const CATEGORIES = ["ability", "item", "skill", "trait", "familiar"];
  const ROOT_ID = 0;
  const SEE_FAR_DISTANCE = 3.5;
  const ADD_LINK_DISTANCE = 2.5;
  const TRACE_DEFAULT_N = 3;

  class ChaosError extends Error {}

  function fmt(n) {
    return Number(n).toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  }

  function newState() {
    return {
      points: 0, cores: 0, inventory: [], unlocked: [ROOT_ID],
      meta_used: {}, added_links: [], swaps: [], entry_swaps: [],
      reveal_temp_until: 0, history: [], echo_used: 0
    };
  }

  // ---- meta tokens ------------------------------------------------------
  const META_RE = /\(Meta:([^)]+)\)/g;
  function splitToken(raw) {
    const key = raw.startsWith("Meta:") ? raw.slice(5) : raw;
    const i = key.indexOf(":");
    if (i < 0) return [key, true];
    const v = key.slice(i + 1);
    const num = /^-?\d+$/.test(v) ? parseInt(v, 10) : v;
    return [key.slice(0, i), num];
  }
  function iterMeta(nd) {
    const out = [];
    for (const raw of (nd.meta || [])) out.push(splitToken(raw));
    const desc = nd.description || "";
    let m;
    META_RE.lastIndex = 0;
    while ((m = META_RE.exec(desc)) !== null) {
      const key = m[1], i = key.indexOf(":");
      if (i < 0) out.push([key, true]);
      else {
        const v = key.slice(i + 1);
        out.push([key.slice(0, i), /^-?\d+$/.test(v) ? parseInt(v, 10) : v]);
      }
    }
    return out;
  }

  function deriveMeta(tree, unlocked) {
    const meta = {
      sight: 0, see_far: false, trace_name: false, trace_desc: false,
      reveal_full: false, reveal_temp: false, ticket_bonus: 0,
      lock_refund: 0, add_link: 0, gacha: 0, gacha_min: 0, gacha_max: 0,
      echo: 0, survey: 0, compass: false, duplicate: 0, duplicate_max: 0,
      cat_sight: {}, lifeline: 0, recall: 0, root_pact: false,
      shuffle: 0, swap: 0, reshuffle: 0, shake: 0, chaosquake: 0,
      gamble: 0, gamble_reroll: 0, gamble_twice: false, trace_name_use: 0
    };
    for (const u of unlocked) {
      const nd = tree.byId[u];
      if (!nd) continue;
      for (const [k, v] of iterMeta(nd)) {
        if (k === "sight") meta.sight = Math.max(meta.sight, v | 0);
        else if (k === "see-far") meta.see_far = true;
        else if (k === "trace-name") meta.trace_name = true;
        else if (k === "trace-desc") meta.trace_desc = true;
        else if (k === "reveal-full") meta.reveal_full = true;
        else if (k === "reveal-temp") meta.reveal_temp = true;
        else if (k === "ticket-bonus") meta.ticket_bonus += v | 0;
        else if (k === "lock-refund") meta.lock_refund += 1;
        else if (k === "add-link") meta.add_link += v | 0;
        else if (k === "gacha") {
          meta.gacha += 1;
          if (typeof v === "string" && v.includes("-")) {
            const [lo, hi] = v.split("-", 2).map(Number);
            meta.gacha_min = Math.max(meta.gacha_min, lo);
            meta.gacha_max = Math.max(meta.gacha_max, hi);
          } else meta.gacha_max = Math.max(meta.gacha_max, v | 0);
        }
        else if (k === "echo") meta.echo += 1;
        else if (k === "survey") meta.survey = Math.max(meta.survey, v === true ? 1 : (v | 0));
        else if (k === "compass") meta.compass = true;
        else if (k === "duplicate") {
          meta.duplicate += 1;
          meta.duplicate_max = Math.max(meta.duplicate_max, v | 0);
        }
        else if (k === "sight-cat") {
          let cat, depth;
          if (typeof v === "string" && v.includes(":")) [cat, depth] = v.split(":", 2);
          else { cat = String(v); depth = 1; }
          meta.cat_sight[cat] = Math.max(meta.cat_sight[cat] || 0, depth | 0);
        }
        else if (k === "lifeline") meta.lifeline += 1;
        else if (k === "recall") meta.recall += 1;
        else if (k === "root-pact") meta.root_pact = true;
        else if (k === "shuffle") meta.shuffle += 1;
        else if (k === "swap") meta.swap += 1;
        else if (k === "reshuffle") meta.reshuffle += 1;
        else if (k === "shake") meta.shake += 1;
        else if (k === "chaosquake") meta.chaosquake += 1;
        else if (k === "gamble") meta.gamble += v | 0;
        else if (k === "gamble-reroll") meta.gamble_reroll = Math.max(meta.gamble_reroll, v | 0);
        else if (k === "gamble-twice") meta.gamble_twice = true;
        else if (k === "trace-name-use") meta.trace_name_use += 1;
      }
    }
    return meta;
  }

  function viewState(tree, state) {
    const meta = deriveMeta(tree, state.unlocked);
    meta.reveal_temp_until = state.reveal_temp_until || 0;
    return meta;
  }

  // ---- graph helpers ----------------------------------------------------
  function dist3(a, b) {
    return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  }

  function frontier(tree, unlocked) {
    const set = new Set(unlocked), out = new Set();
    for (const u of unlocked) for (const b of (tree.adj[u] || [])) {
      if (!set.has(b)) out.add(b);
    }
    return out;
  }

  function hopDistances(tree, unlocked) {
    const dist = {}, prev = {}, q = [];
    for (const u of unlocked) { dist[u] = 0; q.push(u); }
    // Index pointer, not shift(): shift() is O(n) per pop.
    for (let h = 0; h < q.length; h++) {
      const a = q[h];
      for (const b of (tree.adj[a] || [])) {
        if (!(b in dist)) { dist[b] = dist[a] + 1; prev[b] = a; q.push(b); }
      }
    }
    return { dist, prev };
  }

  function visible(tree, unlocked, meta) {
    meta = meta || {};
    const now = Date.now() / 1000;
    const unlockedSet = new Set(unlocked);
    if (meta.reveal_full || (meta.reveal_temp_until || 0) >= now) {
      return tree.nodes.filter(nd => !unlockedSet.has(nd.id)).map(nd => nd.id)
        .sort((a, b) => a - b);
    }
    const sight = meta.sight || 0, catSight = meta.cat_sight || {};
    if (sight <= 0 && !meta.see_far && !Object.keys(catSight).length) {
      return [...frontier(tree, unlocked)].sort((a, b) => a - b);
    }
    const { dist } = hopDistances(tree, unlocked);
    const vis = new Set();
    for (const k in dist) {
      const i = Number(k);
      if (!unlockedSet.has(i) && dist[k] <= 1 + sight) vis.add(i);
    }
    for (const cat in catSight) {
      for (const k in dist) {
        const i = Number(k);
        if (!unlockedSet.has(i) && tree.byId[i].file === cat &&
            dist[k] <= 1 + catSight[cat]) vis.add(i);
      }
    }
    if (meta.see_far) {
      // Node-major order with early exit: same union as before, but a
      // node stops scanning launch points once one is in range.
      for (const nd of tree.nodes) {
        if (unlockedSet.has(nd.id) || vis.has(nd.id)) continue;
        for (const u of unlocked) {
          if (dist3(tree.byId[u].pos, nd.pos) <= SEE_FAR_DISTANCE) { vis.add(nd.id); break; }
        }
      }
    }
    return [...vis].sort((a, b) => a - b);
  }

  function surveyNames(tree, unlocked, meta) {
    meta = meta || {};
    const depth = meta.survey || 0;
    if (!depth) return [];
    const { dist } = hopDistances(tree, unlocked);
    const shown = new Set(visible(tree, unlocked, meta));
    const unlockedSet = new Set(unlocked);
    const out = [];
    for (const k in dist) {
      const i = Number(k);
      if (!unlockedSet.has(i) && !shown.has(i) &&
          dist[k] > 1 && dist[k] <= 1 + depth) {
        out.push([i, tree.byId[i].name]);
      }
    }
    return out.sort((a, b) => a[0] - b[0]);
  }

  // ---- costs / awards ---------------------------------------------------
  function nodeCost(tree, nid) { return Math.pow(10, tree.byId[nid].rarity); }

  // Nodes within `depth` connections of the Origin. Not cached: the tree is
  // sparse, so a 2-hop walk is tiny, and Shuffle/Swap/Add-Link mutate
  // adjacency.
  function rootShell(tree, depth) {
    const seen = new Set([ROOT_ID]);
    let frontier = [ROOT_ID];
    for (let d = 0; d < depth; d++) {
      const next = [];
      for (const a of frontier) for (const b of (tree.adj[a] || [])) {
        if (!seen.has(b)) { seen.add(b); next.push(b); }
      }
      frontier = next;
    }
    return seen;
  }

  function rootPactApplies(tree, state, nid, ctx) {
    const pact = ctx ? !!ctx.pact : !!deriveMeta(tree, state.unlocked).root_pact;
    if (!pact) return false;
    return (ctx ? ctx.shell : rootShell(tree, 2)).has(nid);
  }

  // One deriveMeta (+ at most one rootShell) per render; thread the
  // result through nodeCostFor/coreCostFor so per-node and per-comparison
  // calls stay O(1) instead of re-deriving meta every time.
  function costContext(state, tree) {
    const pact = !!deriveMeta(tree, state.unlocked).root_pact;
    return { pact, shell: pact ? rootShell(tree, 2) : new Set() };
  }

  function nodeCostFor(state, tree, nid, ctx) {
    const cost = nodeCost(tree, nid);
    // Root Pact: no core, but the points price climbs tenfold.
    return rootPactApplies(tree, state, nid, ctx) ? cost * 10 : cost;
  }

  function coreCostFor(state, tree, nid, ctx) {
    return rootPactApplies(tree, state, nid, ctx) ? 0 : 1;
  }

  function couponCover(state, cost) {
    const t = (state.inventory || []).find(t => t.kind === "coupon");
    return t ? Math.min(cost, t.value) : 0;
  }

  function pay(state, tree, nid) {
    const coreCost = coreCostFor(state, tree, nid);
    if (state.cores < coreCost) throw new ChaosError("not enough cores (award a ticket first)");
    const cost = nodeCostFor(state, tree, nid);
    const cover = cost > 0 ? couponCover(state, cost) : 0;
    const pick = cover > 0
      ? state.inventory.find(t => t.kind === "coupon") : null;
    if (state.points < cost - cover) {
      throw new ChaosError(`not enough points: need ${fmt(cost - cover)}, have ${fmt(state.points)}`);
    }
    if (pick) state.inventory.splice(state.inventory.indexOf(pick), 1);
    state.cores -= coreCost;
    state.points -= cost - cover;
  }

  function unlockNode(state, nid, extra) {
    const add = [nid].concat(extra || []);
    for (const i of add) if (!state.unlocked.includes(i)) state.unlocked.push(i);
    state.unlocked.sort((a, b) => a - b);
    state.history = (state.history || []).concat(add);
  }

  function parseTicket(spec) {
    const toks = String(spec).toLowerCase().replace(/,/g, " ").split(/\s+/).filter(Boolean);
    let tier = null, kind = "plain", n = null, category = null, twin = false;
    for (let i = 0; i < toks.length; i++) {
      const t = toks[i];
      if (t in TIER_POINTS) tier = t;
      else if (CATEGORIES.includes(t)) category = t;
      else if (t === "skip") {
        kind = "skip";
        if (i + 1 < toks.length && /^\d+$/.test(toks[i + 1])) n = parseInt(toks[++i], 10);
      }
      else if (/^skip\d+$/.test(t)) { kind = "skip"; n = parseInt(t.slice(4), 10); }
      else if (t === "hop") kind = "hop";
      else if (t === "jump") { if (kind === "plain") kind = "jump"; }
      else if (t === "choice") {
        kind = "choice";
        if (i + 1 < toks.length && /^\d+$/.test(toks[i + 1])) n = parseInt(toks[++i], 10);
      }
      else if (/^choice\d+$/.test(t)) { kind = "choice"; n = parseInt(t.slice(6), 10); }
      else if (t === "twin") twin = true;
      else if (t === "coupon") kind = "coupon";
      else throw new ChaosError(`unrecognised ticket token: ${t}`);
    }
    const params = {};
    if (twin) params.twin = true;
    if (twin) params.twin = true;
    if (kind === "skip") params.n = n || 1;
    else if (kind === "jump") {
      if (!category) throw new ChaosError("jump ticket needs a category");
      params.category = category;
    }
    else if (kind === "choice") { params.n = n || 3; params.category = category || null; }
    if (!tier && kind === "plain") throw new ChaosError("a plain ticket needs a tier");
    if (!tier && kind === "coupon") throw new ChaosError("a coupon ticket needs a tier");
    return { tier, kind, params };
  }

  function award(state, spec, bonusPct, echo, gamble, tree, rng) {
    bonusPct = bonusPct || 0;
    let { tier, kind, params } = parseTicket(spec);
    let twin = !!params.twin, destroyed = false;
    if (gamble) {
      if (!tree) throw new ChaosError("gambling a ticket needs its tree");
      ({ tier, kind, params, destroyed } = gambleTicket(state, tree, tier, kind, params, rng));
      twin = !!params.twin;
    }
    let cores = 1 + (twin ? 1 : 0);
    let pts;
    if (tier === "wild") {
      const d1 = 1 + Math.floor(Math.random() * 8);
      const d2 = 1 + Math.floor(Math.random() * 8);
      pts = wildPoints(d1, d2) * (1 + bonusPct / 100);
      params.wild = [d1, d2];
    } else {
      pts = (TIER_POINTS[tier] || 0) * (1 + bonusPct / 100);
    }
    if (destroyed) {
      cores = twin ? 1 : 0;
      pts /= 2;
    }
    state.cores += cores;
    if (echo) {
      pts *= 2;
      state.echo_used = (state.echo_used || 0) + 1;
    }
    if (kind === "coupon") {
      // Coupons bank their would-be payout instead of paying the wallet.
      params.value = pts;
      pts = 0;
    }
    state.points += pts;
    if (kind !== "plain" && !destroyed) {
      const t = Object.assign({ kind, tier }, params);
      state.inventory.push(t);
    }
    return { tier, kind, params, pts, cores };
  }

  const GAMBLE_LABELS = { rankUp: "Rank Up", twin: "Twin", changeType: "New Kind",
    nothing: "No change", rankDown: "Rank Down", destroyed: "Destroyed" };

  function wildPoints(d1, d2) {
    let pts = Math.pow(10, Math.min(d1, d2) + 1);
    if (d1 === d2) pts *= 2;
    return pts;
  }

  function gamblerEffect(d) {
    if (d === 20) return "rankUp";
    if (d >= 17) return "twin";
    if (d >= 13) return "changeType";
    if (d >= 8) return "nothing";
    if (d >= 2) return "rankDown";
    return "destroyed";
  }

  // Rank graph (not plain ladder order): gold<->platinum skip over
  // aluminium, mythical<->divine skip over wild.
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
  function shiftTier(tier, delta) {
    const table = delta > 0 ? RANK_UP : RANK_DOWN;
    let t = tier;
    for (let i = 0; i < Math.abs(delta); i++) {
      if (t == null) return delta > 0 ? "bronze" : null;
      if (!(t in table)) break;
      t = table[t];
    }
    return t;
  }

  function gambleNewKind(kind, rng) {
    const pool = ["plain", "skip", "jump", "choice", "hop"].filter(k => k !== kind);
    return rng ? rng.pick(pool) : pool[Math.floor(Math.random() * pool.length)];
  }

  function gambleKindParams(kind, rng) {
    if (kind === "skip") return { n: 1 };
    if (kind === "jump") return { category: rng ? rng.pick(CATEGORIES) : CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)] };
    if (kind === "choice") return { n: 2, category: null };
    return {};
  }

  function settleRoll(threshold, rng) {
    const roll = () => rng ? rng.int(20) + 1 : 1 + Math.floor(Math.random() * 20);
    const trail = [];
    let d = roll();
    while (d <= threshold) { trail.push(d); d = roll(); }
    return [d, trail];
  }

  function gambleTicket(state, tree, tier, kind, params, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "gamble") >= meta.gamble) throw new ChaosError("no gamble charge left");
    consume(state, "gamble");
    const threshold = meta.gamble_reroll;
    const rerolls = [];
    let [d, trail] = settleRoll(threshold, rng);
    rerolls.push(...trail);
    const rolls = [[d, gamblerEffect(d)]];
    if (meta.gamble_twice && d !== 20) {
      [d, trail] = settleRoll(threshold, rng);
      rerolls.push(...trail);
      rolls.push([d, gamblerEffect(d)]);
    }
    let twin = !!params.twin, destroyed = false;
    for (const [v, effect] of rolls) {
      if (effect === "rankUp") tier = shiftTier(tier, 1);
      else if (effect === "twin") twin = true;
      else if (effect === "changeType") {
        kind = gambleNewKind(kind, rng);
        delete params.n; delete params.category;
        Object.assign(params, gambleKindParams(kind, rng));
      }
      else if (effect === "rankDown") tier = shiftTier(tier, -1);
      else if (effect === "destroyed") destroyed = true;
    }
    if (twin) params.twin = true;
    if (rolls.length === 1) { params.d20 = rolls[0][0]; params.geffect = rolls[0][1]; }
    else { params.d20 = rolls.map(r => r[0]); params.geffect = rolls.map(r => r[1]); }
    if (rerolls.length) params.rerolls = rerolls;
    if (destroyed) params.destroyed = true;
    return { tier, kind, params, destroyed };
  }

  function gambleNote(params) {
    if (params.d20 == null) return "";
    const ds = Array.isArray(params.d20) ? params.d20 : [params.d20];
    const es = Array.isArray(params.geffect) ? params.geffect : [params.geffect];
    let note = "d20 " + ds.map((v, i) => `${v} ${GAMBLE_LABELS[es[i]]}`).join("+");
    if (params.rerolls && params.rerolls.length) note += ` (rerolled ${params.rerolls.join(", ")})`;
    if (params.destroyed) note += " DESTROYED";
    return note;
  }

  // ---- unlocks ----------------------------------------------------------
  function unlock(state, tree, nid) {
    if (nid === ROOT_ID) throw new ChaosError("the root is free");
    if (state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is already unlocked`);
    if (!frontier(tree, state.unlocked).has(nid)) {
      throw new ChaosError(`node ${nid} is not adjacent to an unlocked node (use a skip/jump/hop ticket to reach it)`);
    }
    pay(state, tree, nid);
    unlockNode(state, nid);
  }

  function unlockSkip(state, tree, nid, n) {
    if (!Number.isInteger(nid)) throw new ChaosError("choose a target node first");
    if (state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is already unlocked`);
    const { dist } = hopDistances(tree, state.unlocked);
    if (!(nid in dist)) throw new ChaosError(`node ${nid} is not connected to the unlocked set`);
    const tickets = state.inventory.filter(t => t.kind === "skip");
    let pick = null;
    if (n != null) {
      pick = tickets.find(t => t.n === n) || null;
      if (!pick) throw new ChaosError(`no skip ${n} ticket in inventory`);
    } else {
      const ok = tickets.filter(t => 1 + t.n >= dist[nid])
        .sort((a, b) => a.n - b.n);
      pick = ok[0] || null;
      if (!pick) throw new ChaosError(`no skip ticket reaches node ${nid} (${dist[nid]} hops)`);
    }
    state.inventory.splice(state.inventory.indexOf(pick), 1);
    pay(state, tree, nid);
    unlockNode(state, nid);
  }

  function jumpCandidates(tree, category, fromId, unlocked) {
    if (!Number.isInteger(fromId)) throw new ChaosError("unlock a node first: jumps launch from unlocked nodes");
    const unlockedSet = new Set(unlocked);
    if (!unlockedSet.has(fromId)) throw new ChaosError(`chosen node ${fromId} is not unlocked`);
    const from = tree.byId[fromId];
    const cands = [];
    for (const nd of tree.nodes) {
      if (nd.id === ROOT_ID) continue;
      if (category != null && nd.file !== category) continue;
      if (unlockedSet.has(nd.id) || (tree.adj[fromId] || new Set()).has(nd.id)) continue;
      cands.push([dist3(from.pos, nd.pos), nd]);
    }
    cands.sort((a, b) => (a[0] - b[0]) || (a[1].id - b[1].id));
    return cands;
  }

  function unlockJump(state, tree, category, fromId, pick) {
    pick = pick || 0;
    const tickets = state.inventory.filter(t =>
      (t.kind === "jump" || t.kind === "choice") &&
      (t.category == null || t.category === category));
    if (!tickets.length) throw new ChaosError(`no ${(category || "any")} jump/choice ticket in inventory`);
    const ticket = tickets[0];
    const eff = category != null ? category : ticket.category;
    const cands = jumpCandidates(tree, eff, fromId, state.unlocked);
    if (!cands.length) throw new ChaosError("no unlockable nodes not directly connected to node " + fromId);
    const limit = ticket.kind === "choice" ? ticket.n : 1;
    const list = cands.slice(0, limit);
    if (pick < 0 || pick >= list.length) throw new ChaosError(`pick ${pick} out of range`);
    state.inventory.splice(state.inventory.indexOf(ticket), 1);
    const target = list[pick][1].id;
    pay(state, tree, target);
    unlockNode(state, target);
    return target;
  }

  function unlockHop(state, tree, nid) {
    if (!Number.isInteger(nid)) throw new ChaosError("choose a target node first");
    const tickets = state.inventory.filter(t => t.kind === "hop");
    if (!tickets.length) throw new ChaosError("no hop ticket in inventory");
    if (state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is already unlocked`);
    const { dist, prev } = hopDistances(tree, state.unlocked);
    if (!(nid in dist)) throw new ChaosError(`node ${nid} is not connected to the unlocked set`);
    if (dist[nid] < 2) throw new ChaosError(`node ${nid} is too close for a hop ticket (needs 2+ hops)`);
    const path = [nid];
    let cur = nid;
    while (cur in prev) { cur = prev[cur]; path.push(cur); }
    path.reverse();
    const intermediate = path[1];
    state.inventory.splice(state.inventory.indexOf(tickets[0]), 1);
    pay(state, tree, nid);
    unlockNode(state, nid, [intermediate]);
  }

  // ---- meta abilities ---------------------------------------------------
  function used(state, key) { return (state.meta_used || {})[key] || 0; }
  function consume(state, key) {
    state.meta_used = state.meta_used || {};
    state.meta_used[key] = used(state, key) + 1;
  }

  function applyAddedLinks(tree, state) {
    for (const [a, b] of (state.added_links || [])) {
      if (tree.adj[a] && tree.adj[b]) { tree.adj[a].add(b); tree.adj[b].add(a); }
    }
    return tree;
  }

  function swapNodes(tree, a, b) {
    if (a === b) return;
    const na = tree.byId[a], nb = tree.byId[b];
    const t = na.pos; na.pos = nb.pos; nb.pos = t;
    if ("r" in na && "r" in nb) { const r = na.r; na.r = nb.r; nb.r = r; }
    const adj = tree.adj;
    const sa = new Set([...(adj[a] || [])].filter(x => x !== b));
    const sb = new Set([...(adj[b] || [])].filter(x => x !== a));
    const ab = (adj[a] || new Set()).has(b);
    for (const x of sa) adj[x].delete(a);
    for (const x of sb) adj[x].delete(b);
    adj[a] = sb; adj[b] = sa;
    for (const x of sb) adj[x].add(a);
    for (const x of sa) adj[x].add(b);
    if (ab) { adj[a].add(b); adj[b].add(a); }
  }

  function applySwaps(tree, state) {
    for (const [a, b] of (state.swaps || [])) {
      if (tree.byId[a] && tree.byId[b]) swapNodes(tree, a, b);
    }
    return tree;
  }

  function swapTol(tree) {
    const p = tree.params || {};
    const v = Number(p.distance_variance ?? p.distanceVariance ?? 0.05);
    return v > 0 ? v : 0.05;
  }

  function swapEntries(tree, a, b) {
    const na = tree.byId[a], nb = tree.byId[b];
    for (const key of new Set([...Object.keys(na), ...Object.keys(nb)])) {
      if (key === "id" || key === "pos" || key === "r") continue;
      const t = na[key]; na[key] = nb[key]; nb[key] = t;
    }
  }

  function applyEntrySwaps(tree, state) {
    for (const [a, b] of (state.entry_swaps || [])) {
      if (tree.byId[a] && tree.byId[b]) swapEntries(tree, a, b);
    }
    return tree;
  }

  function shuffleEntryBucket(state, tree, ids, rng) {
    const order = ids.slice();
    if (rng) rng.shuffle(order);
    else {
      for (let i = order.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [order[i], order[j]] = [order[j], order[i]];
      }
    }
    state.entry_swaps = state.entry_swaps || [];
    let n = 0;
    for (let j = 1; j < order.length; j++) {
      const a = order[0], b = order[j];
      swapEntries(tree, a, b);
      state.entry_swaps.push([a, b]);
      n++;
    }
    return n;
  }

  function entryBuckets(tree, ids) {
    const tol = swapTol(tree), buckets = {};
    for (const i of ids) {
      const k = Math.round(tree.byId[i].rarity / tol);
      (buckets[k] = buckets[k] || []).push(i);
    }
    return Object.values(buckets).filter(v => v.length > 1);
  }

  function useShake(state, tree, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "shake") >= meta.shake) throw new ChaosError("no shake charge left");
    const unlockedSet = new Set(state.unlocked);
    const ids = tree.nodes.filter(nd => nd.id !== ROOT_ID && !unlockedSet.has(nd.id)).map(nd => nd.id);
    const buckets = entryBuckets(tree, ids);
    if (!buckets.length) throw new ChaosError("no locked nodes share a rarity band to shuffle");
    const n = buckets.reduce((s, b) => s + shuffleEntryBucket(state, tree, b, rng), 0);
    consume(state, "shake");
    return n;
  }

  function useChaosquake(state, tree, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "chaosquake") >= meta.chaosquake) throw new ChaosError("no chaosquake charge left");
    const ids = tree.nodes.filter(nd => nd.id !== ROOT_ID).map(nd => nd.id);
    const buckets = entryBuckets(tree, ids);
    if (!buckets.length) throw new ChaosError("no nodes share a rarity band to shuffle");
    const n = buckets.reduce((s, b) => s + shuffleEntryBucket(state, tree, b, rng), 0);
    consume(state, "chaosquake");
    return n;
  }

  function useLockRefund(state, tree, nid) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "lock_refund") >= meta.lock_refund) throw new ChaosError("no lock-refund charge left");
    if (nid === ROOT_ID) throw new ChaosError("the root cannot be locked");
    if (!state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is not unlocked`);
    const refund = nodeCostFor(state, tree, nid);
    const refundCore = coreCostFor(state, tree, nid);
    state.unlocked.splice(state.unlocked.indexOf(nid), 1);
    state.points += refund;
    state.cores += refundCore;
    consume(state, "lock_refund");
    return refund;
  }

  function useAddLink(state, tree, a, b) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "add_link") >= meta.add_link) throw new ChaosError("no add-link charge left");
    if (a === b || a === ROOT_ID || b === ROOT_ID) throw new ChaosError("links join two real nodes");
    if ((tree.adj[a] || new Set()).has(b)) throw new ChaosError(`nodes ${a} and ${b} are already connected`);
    const d = dist3(tree.byId[a].pos, tree.byId[b].pos);
    if (d > ADD_LINK_DISTANCE) throw new ChaosError(`nodes ${a} and ${b} are too far apart`);
    tree.adj[a].add(b); tree.adj[b].add(a);
    state.added_links = state.added_links || [];
    state.added_links.push([a, b]);
    consume(state, "add_link");
    return d;
  }

  function useReveal(state, tree) {
    const meta = deriveMeta(tree, state.unlocked);
    if (!meta.reveal_temp) throw new ChaosError("you have no Glimpse (reveal) charge");
    state.reveal_temp_until = Date.now() / 1000 + 10;
    return state.reveal_temp_until;
  }

  function useGacha(state, tree, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "gacha") >= meta.gacha) throw new ChaosError("no gacha charge left");
    const unlockedSet = new Set(state.unlocked);
    const eligible = tree.nodes.filter(nd =>
      nd.id !== ROOT_ID && !unlockedSet.has(nd.id) &&
      nd.rarity >= meta.gacha_min && nd.rarity <= meta.gacha_max);
    if (!eligible.length) throw new ChaosError("no locked node in the rarity range to roll");
    const target = rng ? rng.pick(eligible) : eligible[Math.floor(Math.random() * eligible.length)];
    unlockNode(state, target.id);
    consume(state, "gacha");
    return target;
  }

  function useLifeline(state, tree, nid) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "lifeline") >= meta.lifeline) throw new ChaosError("no lifeline charge left");
    if (nid === ROOT_ID) throw new ChaosError("the root is free already");
    if (state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is already unlocked`);
    if (!frontier(tree, state.unlocked).has(nid)) throw new ChaosError(`node ${nid} is not adjacent to an unlocked node`);
    unlockNode(state, nid);
    consume(state, "lifeline");
  }

  function useRecall(state, tree) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "recall") >= meta.recall) throw new ChaosError("no recall charge left");
    const hist = state.history || [];
    if (!hist.length) throw new ChaosError("no unlocks to undo");
    const nid = hist.pop();
    if (!state.unlocked.includes(nid)) throw new ChaosError(`node ${nid} is already locked`);
    // Refund what was actually paid, before removing the node (the discount
    // may depend on the unlocked set).
    const refund = nodeCostFor(state, tree, nid);
    const refundCore = coreCostFor(state, tree, nid);
    state.unlocked.splice(state.unlocked.indexOf(nid), 1);
    state.points += refund;
    state.cores += refundCore;
    consume(state, "recall");
    return nid;
  }

  function useDuplicate(state, tree, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "duplicate") >= meta.duplicate) throw new ChaosError("no duplicate charge left");
    const sources = new Set(state.unlocked.map(u => tree.byId[u].source));
    sources.delete("Generic"); sources.delete("");
    if (!sources.size) throw new ChaosError("you own no nodes with a real source to duplicate");
    const arr = [...sources].sort();
    const src = rng ? rng.pick(arr) : arr[Math.floor(Math.random() * arr.length)];
    const unlockedSet = new Set(state.unlocked);
    const eligible = tree.nodes.filter(nd =>
      nd.id !== ROOT_ID && !unlockedSet.has(nd.id) &&
      nd.source === src && nd.rarity <= meta.duplicate_max);
    if (!eligible.length) throw new ChaosError(`no locked ${src} node with rarity <= ${meta.duplicate_max} to duplicate`);
    const target = rng ? rng.pick(eligible) : eligible[Math.floor(Math.random() * eligible.length)];
    unlockNode(state, target.id);
    consume(state, "duplicate");
    return target;
  }

  function chooseShufflePartner(tree, state, a) {
    const meta = deriveMeta(tree, state.unlocked);
    const vis = new Set(visible(tree, state.unlocked, meta));
    if (!vis.has(a)) throw new ChaosError(`node ${a} is not a visible locked node`);
    const ra = tree.byId[a].rarity;
    const unlockedSet = new Set(state.unlocked);
    let cands = tree.nodes.filter(nd =>
      !unlockedSet.has(nd.id) && !vis.has(nd.id) &&
      Math.abs(nd.rarity - ra) <= 0.2);
    if (!cands.length) cands = tree.nodes.filter(nd => vis.has(nd.id) && nd.id !== a);
    if (!cands.length) throw new ChaosError(`no node to shuffle with node ${a}`);
    return cands;
  }

  function doSwapRecord(state, tree, a, b) {
    swapNodes(tree, a, b);
    state.swaps = state.swaps || [];
    state.swaps.push([a, b]);
  }

  function useShuffle(state, tree, a, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "shuffle") >= meta.shuffle) throw new ChaosError("no shuffle charge left");
    if (state.unlocked.includes(a)) throw new ChaosError(`node ${a} is already unlocked`);
    const cands = chooseShufflePartner(tree, state, a);
    const b = (rng ? rng.pick(cands) : cands[Math.floor(Math.random() * cands.length)]).id;
    doSwapRecord(state, tree, a, b);
    consume(state, "shuffle");
    return b;
  }

  function useSwap(state, tree, a, b) {
    const meta = deriveMeta(tree, state.unlocked);
    if (used(state, "swap") >= meta.swap) throw new ChaosError("no swap charge left");
    if (a === b) throw new ChaosError("swap needs two different nodes");
    if (state.unlocked.includes(a) || state.unlocked.includes(b)) throw new ChaosError("both nodes must be locked");
    const vis = new Set(visible(tree, state.unlocked, meta));
    if (!vis.has(a) || !vis.has(b)) throw new ChaosError("both nodes must be visible");
    doSwapRecord(state, tree, a, b);
    consume(state, "swap");
  }

  function useReshuffle(state, tree, a, rng) {
    const meta = deriveMeta(tree, state.unlocked);
    if (!meta.reshuffle) throw new ChaosError("you have no reshuffle ability");
    if (state.unlocked.includes(a)) throw new ChaosError(`node ${a} is already unlocked`);
    const cost = nodeCost(tree, a) / 4;
    if (state.points < cost) throw new ChaosError(`not enough points: need ${fmt(cost)}, have ${fmt(state.points)}`);
    const cands = chooseShufflePartner(tree, state, a);
    const b = (rng ? rng.pick(cands) : cands[Math.floor(Math.random() * cands.length)]).id;
    state.points -= cost;
    doSwapRecord(state, tree, a, b);
    return { cost, b };
  }

  function trace(tree, state, field, x, n) {
    n = n || TRACE_DEFAULT_N;
    const meta = deriveMeta(tree, state.unlocked);
    const cap = field === "name" ? "trace_name" : field === "desc" ? "trace_desc" : "compass";
    if (!meta[cap]) {
      if (field === "name" && used(state, "trace_name_use") < meta.trace_name_use) {
        consume(state, "trace_name_use");
      } else {
        const verb = field === "source" ? "compass" : "trace-by-" + field;
        throw new ChaosError(`you lack the ${verb} ability`);
      }
    }
    const q = String(x).toLowerCase();
    const { dist, prev } = hopDistances(tree, state.unlocked);
    const unlockedSet = new Set(state.unlocked);
    const matches = [];
    for (const nd of tree.nodes) {
      if (nd.id === ROOT_ID || unlockedSet.has(nd.id)) continue;
      const hay = field === "name" ? nd.name.toLowerCase()
        : field === "desc" ? (nd.description || "").toLowerCase()
        : (nd.source || "").toLowerCase();
      if (hay.includes(q) && (nd.id in dist)) {
        let near = Infinity;
        for (const u of state.unlocked) {
          const d = dist3(tree.byId[u].pos, nd.pos);
          if (d < near) near = d;
        }
        matches.push([dist[nd.id], near, nd]);
      }
    }
    matches.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]) || (a[2].id - b[2].id));
    return matches.slice(0, n).map(([d, , nd]) => {
      const path = [nd.id];
      let cur = nd.id;
      while (cur in prev) { cur = prev[cur]; path.push(cur); }
      path.reverse();
      return { dist: d, node: nd, path };
    });
  }

  return {
    TIER_POINTS, TIERS, CATEGORIES, ROOT_ID,
    SEE_FAR_DISTANCE, ADD_LINK_DISTANCE, TRACE_DEFAULT_N,
    ChaosError, fmt, newState,
    iterMeta, deriveMeta, viewState,
    dist3, frontier, hopDistances, visible, surveyNames,
    nodeCost, nodeCostFor, coreCostFor, costContext, rootShell, parseTicket, award,
    unlock, unlockSkip, jumpCandidates, unlockJump, unlockHop,
    useLockRefund, useAddLink, useReveal, useGacha, useLifeline,
    useRecall, useDuplicate, useShuffle, useSwap, useReshuffle,
    useShake, useChaosquake, gambleTicket, gamblerEffect, gambleNote,
    wildPoints,
    trace, applyAddedLinks, applySwaps, swapNodes, unlockNode,
    couponCover,
    swapEntries, applyEntrySwaps
  };
})();
