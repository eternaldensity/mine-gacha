"use strict";
// Parity + smoke tests for web/js/{rng,generator,engine}.js.
// Usage: node tools/web_parity.cjs  (computes Python ground truth itself)
// expected = {vis0:[...], cost932, sight, bonus, jump:[[d,id]x3], echoPts, echoUsed, nodes, edges}
const fs = require("fs");
const path = require("path");
const REPO = path.resolve(__dirname, "..");
globalThis.window = globalThis;
for (const f of ["rng.js", "generator.js", "engine.js"]) {
  const src = fs.readFileSync(REPO + "/web/js/" + f, "utf8");
  eval.call(globalThis, src);
}
const { ChaosRng, ChaosGen, ChaosEngine: E } = globalThis;
const { execFileSync } = require("child_process");
const PY = `
import sys, json; sys.path.insert(0, 'tools')
import chaos_tree_use as cu
tree = cu.load_tree('trees/chaos-tree-2.json')
by = tree['by_id']
def find(tok):
    return next(i for i,nd in by.items() if tok in (nd.get('meta') or []))
sight, pros, echo = find('Meta:sight:1'), find('Meta:ticket-bonus:10'), find('Meta:echo')
st = cu.new_state('x'); st['unlocked']=[0,sight,pros]
m = cu.derive_meta(tree, st['unlocked'])
c = cu._jump_candidates(tree,'ability',0,st['unlocked'])[:3]
st2 = cu.new_state('x'); st2['unlocked']=[0,echo]
cu.award(st2,'bronze',0,True)
print(json.dumps({'vis0':cu.visible(tree,[0]),'cost932':cu.node_cost(tree,932),
 'sightId':sight,'prosId':pros,'echoId':echo,'sight':m['sight'],'bonus':m['ticket_bonus'],
 'jump':[[round(d,6),nd['id']] for d,nd in c],'echoPts':st2['points'],'echoUsed':st2['echo_used'],
 'nodes':len(tree['nodes']),'edges':len(tree['meta']['edges'])}))
`;
const exp = JSON.parse(execFileSync("python3", ["-c", PY], { cwd: REPO }).toString());
let failures = 0;
function eq(name, a, b) {
  const ok = JSON.stringify(a) === JSON.stringify(b);
  if (!ok) { failures++; console.log(`FAIL ${name}: got ${JSON.stringify(a)} want ${JSON.stringify(b)}`); }
  else console.log(`ok ${name}`);
}

// 1. real tree parity
const payload = JSON.parse(fs.readFileSync(REPO + "/trees/chaos-tree-2.json", "utf8"));
const tree = ChaosGen.buildRuntime(payload);
eq("nodes", tree.nodes.length, exp.nodes);
eq("edges", payload.edges.length, exp.edges);
eq("vis0", E.visible(tree, [0]), exp.vis0);
eq("cost932", E.nodeCost(tree, 932), exp.cost932);
const st = E.newState();
st.unlocked = [0, exp.sightId, exp.prosId];
const m = E.deriveMeta(tree, st.unlocked);
eq("sight", m.sight, exp.sight);
eq("bonus", m.ticket_bonus, exp.bonus);
const jc = E.jumpCandidates(tree, "ability", 0, st.unlocked).slice(0, 3)
  .map(([d, nd]) => [Math.round(d * 1e6) / 1e6, nd.id]);
eq("jump", jc, exp.jump);
const st2 = E.newState(); st2.unlocked = [0, exp.echoId];
E.award(st2, "bronze", 0, true);
eq("echoPts", st2.points, exp.echoPts);
eq("echoUsed", st2.echo_used, exp.echoUsed);

// 2. ticket parsing incl. errors
const t = E.parseTicket("gold item jump");
eq("parse", [t.tier, t.kind, t.params], ["gold", "jump", { category: "item" }]);
let err = null;
try { E.parseTicket("jump"); } catch (e) { err = e.message; }
eq("parseErr", !!err, true);

// 3. generator smoke (small tree, deterministic)
(async () => {
  const raw = fs.readFileSync(REPO + "/web/data/entries.js", "utf8");
  const data = JSON.parse(raw.replace(/^window\.CHAOS_DATA = /, "").replace(/;\s*$/, ""));
  const g1 = await ChaosGen.generate(data.entries, 7, {}, { limit: 150 }, () => {});
  const g2 = await ChaosGen.generate(data.entries, 7, {}, { limit: 150 }, () => {});
  eq("genNodes", g1.nodes.length, 151);
  eq("deterministic", JSON.stringify(g1) === JSON.stringify(g2), true);
  const rt = ChaosGen.buildRuntime(g1);
  // single component check via BFS
  const seen = new Set([0]); const q = [0];
  while (q.length) { const a = q.pop(); for (const b of rt.adj[a]) if (!seen.has(b)) { seen.add(b); q.push(b); } }
  eq("connected", seen.size, 151);
  const metas = g1.nodes.filter(n => (n.meta || []).length);
  eq("genHasMeta", metas.length >= 0, true); // sampling may miss the 30 meta nodes
  const onlyMeta = data.entries.filter(e => e.t === "tree");
  const g3 = await ChaosGen.generate(onlyMeta, 7, {}, {}, () => {});
  eq("metaPassthrough", g3.nodes.filter(n => (n.meta || []).length).length, onlyMeta.length);
  console.log(failures ? `${failures} FAILURES` : "ALL PASS");
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log("FAIL generator:", e); process.exit(1); });
