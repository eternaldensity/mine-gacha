"use strict";
/* Chaos Tree shareable-view payloads.
 *
 * Builds a privacy-scoped snapshot of a tree: ONLY the nodes the owner can
 * currently see (visible + unlocked, minus display-hidden ones) and the
 * edges among them, plus the wallet/inventory and the precomputed
 * unlock-method buckets. It never includes the seed, generation params,
 * filters, or any hidden node's data. Hidden nodes that a skip/jump/hop
 * ticket can still reach are recorded by id and method only, so a viewer
 * can be told "something is reachable here" without seeing what it is.
 *
 * validate() hardens a snapshot fetched from an untrusted paste host. */
window.ChaosShare = (function () {
  const E = window.ChaosEngine;
  const ROOT_ID = 0;
  const MAX_NODES = 30000;
  const MAX_HIDDEN_JUMP = 500;

  const isNum = v => typeof v === "number" && isFinite(v);

  function pickNode(nd) {
    const out = {
      id: nd.id, file: nd.file, name: nd.name, rarity: nd.rarity,
      source: nd.source || "", description: nd.description || "",
      meta: (nd.meta || []).slice(), tags: (nd.tags || nd.tg || []).slice(),
      pos: nd.pos.slice(), r: nd.r
    };
    if (nd.nsfw) out.nsfw = true;
    if (nd.noncon) out.noncon = true;
    if (nd.tech) out.tech = true;
    return out;
  }

  // Build the snapshot. opts: { name, dataVersion, nodeVisible(nd) }
  function collect(tree, rt, st, opts) {
    opts = opts || {};
    const nodeVisible = opts.nodeVisible || (() => true);
    const meta = E.viewState(rt, st);
    const unl = new Set(st.unlocked);
    const visAll = new Set(E.visible(rt, st.unlocked, meta));

    // Everything the owner can see: all unlocked nodes (owned data is fair
    // game) plus locked-but-visible nodes that pass the display filter.
    const shareIds = new Set(unl);
    for (const id of visAll) {
      if (unl.has(id)) continue;
      const nd = rt.byId[id];
      if (nd && nodeVisible(nd)) shareIds.add(id);
    }

    const nodes = rt.nodes.filter(nd => shareIds.has(nd.id)).map(pickNode);

    // Edges among shared nodes, derived from live adjacency so tree-meta
    // added links are included. Distance is recomputed from positions.
    const edges = [];
    for (const nd of nodes) {
      for (const b of (rt.adj[nd.id] || [])) {
        if (!shareIds.has(b) || b <= nd.id) continue;
        const nb = rt.byId[b];
        edges.push({ a: nd.id, b, d: Math.round(Math.hypot(
          nd.pos[0] - nb.pos[0], nd.pos[1] - nb.pos[1], nd.pos[2] - nb.pos[2]) * 1e6) / 1e6 });
      }
    }

    const visible = [...visAll]
      .filter(id => shareIds.has(id) && !unl.has(id))
      .sort((a, b) => a - b);

    const ccx = E.costContext(st, rt);
    const frontier = [...E.frontier(rt, st.unlocked)]
      .filter(id => id !== ROOT_ID && shareIds.has(id))
      .sort((a, b) => a - b);
    const afford = {};
    for (const id of frontier) {
      const cost = E.nodeCostFor(st, rt, id, ccx);
      const cover = E.couponCover(st, cost);
      const cores = E.coreCostFor(st, rt, id, ccx);
      afford[id] = {
        cost: cost - cover, cores,
        ok: st.cores >= cores && st.points >= cost - cover
      };
    }

    // Hidden reachability: full-graph skip / hop / jump targets that are
    // NOT in the shared set, recorded without any node data.
    const { dist, prev } = E.hopDistances(rt, st.unlocked);
    const skips = st.inventory.filter(t => t.kind === "skip");
    const hops = st.inventory.filter(t => t.kind === "hop");
    const hiddenReach = { skip: [], hop: [], jump: [] };
    for (const id of Object.keys(dist).map(Number)) {
      if (id === ROOT_ID || unl.has(id) || shareIds.has(id)) continue;
      const d = dist[id];
      const best = skips.filter(t => d <= 1 + t.n).sort((a, b) => a.n - b.n)[0];
      if (best) hiddenReach.skip.push({ id, n: d });
      if (d >= 2 && hops.length) hiddenReach.hop.push({ id, via: prev[id] != null ? prev[id] : null });
    }
    const jumps = st.inventory.filter(t => t.kind === "jump" || t.kind === "choice");
    for (let ti = 0; ti < jumps.length && hiddenReach.jump.length < MAX_HIDDEN_JUMP; ti++) {
      const t = jumps[ti];
      const lim = t.kind === "choice" ? t.n : 1;
      for (const from of st.unlocked) {
        let cands;
        try { cands = E.jumpCandidates(rt, t.category, from, st.unlocked); }
        catch (e) { continue; }
        cands.forEach(([, nd], rank) => {
          if (rank >= lim) return;                       // only the actual pick(s)
          if (unl.has(nd.id) || shareIds.has(nd.id)) return;
          if (hiddenReach.jump.length >= MAX_HIDDEN_JUMP) return;
          hiddenReach.jump.push({ id: nd.id, from, ticket: ti, rank });
        });
      }
    }

    // Names the owner can read beyond sight (Survey meta) are still "seen".
    let surveyed = [];
    try { surveyed = E.surveyNames(rt, st.unlocked, meta).filter(([id]) => !shareIds.has(id)); }
    catch (e) { /* ignore */ }

    return {
      app: "chaos-tree-view", v: 1, createdAt: new Date().toISOString(),
      name: opts.name || (tree && tree.name) || "Shared tree",
      dataVersion: opts.dataVersion || null,
      state: {
        points: st.points || 0, cores: st.cores || 0,
        unlocked: st.unlocked.slice(),
        inventory: JSON.parse(JSON.stringify(st.inventory || [])),
        meta_used: JSON.parse(JSON.stringify(st.meta_used || {}))
      },
      nodes, edges,
      view: { visible, frontier, afford, hiddenReach, surveyed }
    };
  }

  function validate(p) {
    if (!p || typeof p !== "object") throw new Error("share data is not an object");
    if (p.app !== "chaos-tree-view") throw new Error("not a Chaos Tree view file");
    if (p.v !== 1) throw new Error("unsupported share version: " + p.v);
    if (!Array.isArray(p.nodes) || !p.nodes.length) throw new Error("share data has no nodes");
    if (p.nodes.length > MAX_NODES) throw new Error("share data is too large");
    if (!Array.isArray(p.edges)) throw new Error("share data has no edges");
    const ids = new Set();
    for (const nd of p.nodes) {
      if (!nd || !Number.isInteger(nd.id)) throw new Error("share data has a bad node id");
      if (!isNum(nd.rarity)) throw new Error("share data has a bad node rarity");
      if (!Array.isArray(nd.pos) || nd.pos.length !== 3 || !nd.pos.every(isNum)) {
        throw new Error("share data has a bad node position");
      }
      if (nd.meta != null && !Array.isArray(nd.meta)) throw new Error("share data has bad node meta");
      if (nd.tags != null && !Array.isArray(nd.tags)) throw new Error("share data has bad node tags");
      ids.add(nd.id);
    }
    for (const e of p.edges) {
      if (!e || !ids.has(e.a) || !ids.has(e.b)) throw new Error("an edge points at a missing node");
    }
    if (!p.state || !Array.isArray(p.state.unlocked)) throw new Error("share data has no state");
    for (const u of p.state.unlocked) {
      if (!ids.has(u)) throw new Error("the state references a missing node");
    }
    if (!p.view || !Array.isArray(p.view.visible)) throw new Error("share data has no view sets");
    p.view.frontier = Array.isArray(p.view.frontier) ? p.view.frontier : [];
    p.view.afford = p.view.afford || {};
    p.view.surveyed = Array.isArray(p.view.surveyed) ? p.view.surveyed : [];
    p.view.hiddenReach = p.view.hiddenReach || {};
    p.view.hiddenReach.skip = Array.isArray(p.view.hiddenReach.skip) ? p.view.hiddenReach.skip : [];
    p.view.hiddenReach.hop = Array.isArray(p.view.hiddenReach.hop) ? p.view.hiddenReach.hop : [];
    p.view.hiddenReach.jump = Array.isArray(p.view.hiddenReach.jump) ? p.view.hiddenReach.jump : [];
    return p;
  }

  return { collect, validate, MAX_NODES };
})();
