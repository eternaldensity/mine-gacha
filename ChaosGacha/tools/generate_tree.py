#!/usr/bin/env python3
"""Chaos Tree generator.

Distributes entries from the shared gacha definition files in a 3D sphere and
links neighbouring items into a graph ("tree"). Distance from the sphere
centre is driven by rarity magnitude (higher rarity -> further out).

Output: a JSON file (canonical, for the future viewer/selector) plus a
printed summary. Everything is deterministic given `--seed`.

Parameters
----------
Content:
  --files A,B,...            gacha files to include (default: all five)
  --rarity-min/--rarity-max  rarity window
  --sources X,Y,...          include only these sources (per-source filter)
  --exclude-sources X,Y,...  exclude these sources
  --include-gacha-only       also include (Gacha)-tagged entries
  --include-nsfw             also include (Nsfw)-tagged entries (excluded
                             by default)
  --include-noncon           also include (Noncon)-tagged entries (excluded
                             by default)
  --limit N                  randomly sample at most N entries

Placement:
  --radius F                 sphere radius (normalized units, default 10.0)
  --distance-variance F      radial jitter as a fraction of radius (0..1;
                             default 0.05)
  --clustering F             how strongly nodes pull toward cluster anchors
                             (0 = uniform on shells, 1 = tight clusters)
  --clusters N               number of cluster anchors

Links:
  --degree-dist {constant,poisson,powerlaw}
  --mean-degree F            mean number of links per node
  --degree-min N             minimum links per node (default 1)
  --degree-max N             maximum links per node
  --rejoin-bias F            penalty (0..1) against linking two nodes that
                             already share a neighbour (branch rejoining);
                             1.0 forbids it entirely (acyclic)
  --link-falloff F           exponent preferring short links (0 = none)
  --local-link-distance F    preferred search radius as a fraction of radius
                             (default 0.25); expands toward --max-link-distance
                             only while a node finds nothing, so links stay
                             local without stranding sparse nodes
  --max-link-distance F      link cap as a fraction of radius
  --no-connect               don't force a single connected component

Output:
  --out PATH                 JSON destination (default trees/chaos-tree-<seed>.json)
  --seed N                   RNG seed (default 12345)
  --root-links N             starting nodes linked to the Origin root
                             (nearest-to-centre, spread apart; default 3)

Examples
--------
  python3 tools/generate_tree.py --files ability --seed 7 --clustering 0.6
  python3 tools/generate_tree.py --sources 'Fate,One Piece' --mean-degree 3
  python3 tools/generate_tree.py --list-sources
"""
import argparse
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GACHA_DIR = os.path.join(ROOT, "gachafiles")
TREE_DIR = os.path.join(ROOT, "trees")
ALL_FILES = ["skill", "trait", "familiar", "item", "ability"]

HEADER_RE = re.compile(r"^(\d+)\.\s*(.*),\s*(\d+\.\d+)(?:,\s*(.*))?\s*$")
TOKEN_RE = re.compile(r"^#(?:\s*\(([^)]*)\)\s*)+")

# Thematic tags: (Tag:name) per tag, or (Tags: a, b) for several at once.
# Names follow the original site's taxonomy (see tools/tagdata/); stored
# lowercase, with "+" significant (fire+ = fire amplification, fire = fire).
# Aliases keep older/hand-written spellings resolving to the canonical name.
TAG_ALIASES = {
    "dragons": "draconic",
    "dragon": "draconic",
    "dragonic": "draconic",
    "angelic": "holy",
    "demonic": "infernal",
    "unholy": "infernal",
    "vampire": "vampiric",
    "lightning": "electric",
    "wind": "air",
    "shadow": "dark",
    "spectral": "spirit",
    "psychic": "mental",
    "insect": "insectoid",
    "slime": "amorphous",
}


def normalize_tag(raw: str):
    """Canonicalize one tag name; returns "" when invalid."""
    s = str(raw or "").strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9+]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or len(s) > 40 or not re.match(r"^[a-z0-9][a-z0-9+-]*$", s):
        return ""
    for _ in range(5):  # resolve alias chains
        nxt = TAG_ALIASES.get(s)
        if not nxt or nxt == s:
            break
        s = nxt
    return s


def parse_tags(tokens) -> list:
    """Extract thematic tags from a description's token set.

    Accepts (Tag:name) repeated per tag and (Tags: a, b, ...) lists.
    Prefix match is case-insensitive; names are normalized."""
    out = set()
    for tok in tokens or []:
        low = tok.lower()
        if low.startswith("tags:"):
            rest = tok[5:]
            parts = rest.split(",") if "," in rest else rest.split()
            for part in parts:
                n = normalize_tag(part)
                if n:
                    out.add(n)
        elif low.startswith("tag:"):
            n = normalize_tag(tok[4:])
            if n:
                out.add(n)
    return sorted(out)


def parse_description(desc: str):
    """Split '#'-leading tokens (Nsfw/Tech/Character/Gacha/Tree/Tome/Tag/.../Meta:...)
    from the visible description text. Returns (token_set, visible_text)."""
    m = TOKEN_RE.match(desc)
    if not m:
        return set(), desc.lstrip("#").strip()
    # collect all groups: (Gacha)(Nsfw) style
    tokens = set()
    end = 0
    for tm in re.finditer(r"\(([^)]*)\)", desc[:m.end()]):
        tokens.add(tm.group(1))
        end = tm.end()
    rest = desc[end:].lstrip(" \t").lstrip("#").strip()
    return tokens, rest


def load_entries(files, rarity_min, rarity_max, sources, exclude_sources,
                 include_gacha_only, include_nsfw=False, include_noncon=False,
                 tags=None):
    entries = []
    want = None
    if tags:
        if isinstance(tags, str):
            tags = [tags]
        want = {normalize_tag(t) for t in tags}
        want.discard("")
    for file in files:
        path = os.path.join(GACHA_DIR, file + ".txt")
        if not os.path.exists(path):
            sys.exit(f"missing gacha file: {path}")
        cur = None
        desc_lines = []
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for line in lines:
            m = HEADER_RE.match(line)
            if m:
                if cur is not None:
                    _finalize(file, cur, desc_lines, rarity_min, rarity_max,
                              sources, exclude_sources, include_gacha_only,
                              include_nsfw, include_noncon, entries, want)
                cur = {
                    "num": int(m.group(1)),
                    "name": m.group(2).strip(),
                    "rarity": float(m.group(3)),
                    "source": (m.group(4) or "").strip(),
                }
                desc_lines = []
            else:
                desc_lines.append(line)
        if cur is not None:
            _finalize(file, cur, desc_lines, rarity_min, rarity_max,
                      sources, exclude_sources, include_gacha_only,
                      include_nsfw, include_noncon, entries, want)
    return entries


def _finalize(file, cur, desc_lines, rmin, rmax, sources, exclude_sources,
              include_gacha_only, include_nsfw, include_noncon, entries,
              want_tags=None):
    desc = " ".join(l.strip() for l in desc_lines if l.strip())
    tokens, visible = parse_description(desc)
    if "Tree" in tokens:
        tag = "tree"
    elif "Gacha" in tokens:
        tag = "gacha"
    else:
        tag = "both"
    if rmin is not None and cur["rarity"] < rmin:
        return
    if rmax is not None and cur["rarity"] > rmax:
        return
    if sources and cur["source"] not in sources:
        return
    if cur["source"] in exclude_sources:
        return
    if tag == "gacha" and not include_gacha_only:
        return
    if "Nsfw" in tokens and not include_nsfw:
        return
    if "Noncon" in tokens and not include_noncon:
        return
    entry_tags = parse_tags(tokens)
    if want_tags and not want_tags.issubset(set(entry_tags)):
        return
    entries.append({
        "file": file,
        "number": cur["num"],
        "name": cur["name"],
        "rarity": cur["rarity"],
        "source": cur["source"] or "Generic",
        "tag": tag,
        "description": visible,
        "meta": sorted(t for t in tokens if t.startswith("Meta:")),
        "tags": entry_tags,
        **({"nsfw": True} if "Nsfw" in tokens else {}),
        **({"noncon": True} if "Noncon" in tokens else {}),
    })


def _poisson(rng, mean):
    # Knuth's algorithm; fine for the small means used here.
    limit = math.exp(-mean)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def sample_degree(rng, dist, mean, dmin, dmax):
    if dist == "constant":
        return max(dmin, min(dmax, int(round(mean))))
    if dist == "poisson":
        d = _poisson(rng, mean)
        return max(dmin, min(dmax, d))
    if dist == "powerlaw":
        u = rng.random()
        span = max(1, dmax - dmin)
        d = dmin + int(span * (1 - u) ** 2)
        return max(dmin, min(dmax, d))
    raise ValueError(f"unknown degree distribution: {dist}")


def unit_sphere(rng):
    z = rng.uniform(-1.0, 1.0)
    th = rng.uniform(0.0, 2.0 * math.pi)
    r = math.sqrt(1.0 - z * z)
    return (r * math.cos(th), r * math.sin(th), z)


def norm3(v):
    l = math.sqrt(sum(c * c for c in v))
    if l == 0:
        return (1.0, 0.0, 0.0)
    return tuple(c / l for c in v)


def generate_tree(items, params, rng):
    """Distribute items and link them. Returns (nodes, edges, stats)."""
    n = len(items)
    radius = params["radius"]
    inner = params.get("inner_fraction", 0.12)
    rmin = min(i["rarity"] for i in items)
    rmax = max(i["rarity"] for i in items)
    span = (rmax - rmin) or 1.0

    # --- cluster anchors ---
    k = max(1, params["clusters"])
    anchors = [unit_sphere(rng) for _ in range(k)]
    cluster_prob = max(0.0, min(1.0, params["clustering"]))

    # --- place nodes ---
    nodes = []
    for idx, item in enumerate(items):
        t = (item["rarity"] - rmin) / span
        radial = radius * (inner + (1.0 - inner) * t)
        if params["distance_variance"] > 0:
            radial += rng.gauss(0.0, params["distance_variance"] * radius)
        radial = max(radius * 0.05, min(radius, radial))
        d = unit_sphere(rng)
        if cluster_prob > 0 and rng.random() < cluster_prob:
            a = anchors[rng.randrange(k)]
            c = cluster_prob
            d = norm3(tuple((1 - c) * u + c * v for u, v in zip(d, a)))
        pos = tuple(radius_ * u for radius_, u in zip((radial,) * 3, d))
        nodes.append({
            "id": idx,
            **{k_: v for k_, v in item.items()},
            "pos": [round(c, 6) for c in pos],
            "r": round(radial, 6),
        })

    # --- target degrees ---
    deg_max = params["degree_max"] or min(n - 1,
                                         max(2, int(round(params["mean_degree"] * 6))))
    targets = [sample_degree(rng, params["degree_dist"], params["mean_degree"],
                             params["degree_min"], deg_max)
               for _ in range(n)]
    if params["degree_min"] > 0 and n > 1:
        targets = [max(params["degree_min"], t) for t in targets]

    maxd = params["max_link_distance"] * radius
    # Local-first search: candidates are gathered inside a small radius
    # (default 0.35x) and the radius expands only while a node finds
    # nothing, so long links form solely where the neighbourhood is empty.
    # This keeps connectivity local without stranding sparse nodes the way
    # a small hard cap would.
    locald = params.get("local_link_distance", 0.25) * radius
    if not locald > 0:
        locald = maxd if maxd > 0 else radius
    falloff = max(0.0, params["link_falloff"])
    bias = max(0.0, min(1.0, params["rejoin_bias"]))

    def dist(a, b):
        return math.dist(a["pos"], b["pos"])

    edges = []
    adj = [set() for _ in range(n)]

    # Union-find over the graph built so far; used for the branch-rejoin test
    # and later for connectivity.
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Spatial grid for local neighbour lookup. Cell side = the local search
    # radius; wider searches walk additional rings of cells, so narrowing
    # the local radius also shrinks every lookup instead of scanning the
    # whole tree the way a maxd-sized cell does.
    cell = locald
    grid = {}
    for i, nd in enumerate(nodes):
        key = (int(nd["pos"][0] // cell), int(nd["pos"][1] // cell),
               int(nd["pos"][2] // cell))
        grid.setdefault(key, []).append(i)

    def candidates(a, radius):
        rings = max(1, int(math.ceil(radius / cell)))
        p = nodes[a]["pos"]
        cx, cy, cz = (int(p[0] // cell), int(p[1] // cell), int(p[2] // cell))
        out = []
        for dx in range(-rings, rings + 1):
            for dy in range(-rings, rings + 1):
                for dz in range(-rings, rings + 1):
                    for b in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        if b == a or b in adj[a]:
                            continue
                        d = dist(nodes[a], nodes[b])
                        if d <= radius:
                            out.append((b, d))
        return out

    order = list(range(n))
    rng.shuffle(order)
    for qi, a in enumerate(order):
        radius = min(locald, maxd) if maxd > 0 else locald
        while len(adj[a]) < targets[a]:
            cands = candidates(a, radius)
            if not cands:
                if maxd > 0 and radius < maxd:
                    radius = min(maxd, radius * 1.5)
                    continue
                break
            scores = []
            denom = maxd if maxd > 0 else radius
            for b, d in cands:
                s = (1.0 - d / denom) ** falloff if falloff > 0 else 1.0
                # branch rejoining: linking into the component a already
                # belongs to would close a loop. Higher bias makes that
                # progressively less likely; 1.0 forbids it (acyclic).
                if bias > 0 and find(a) == find(b):
                    s *= (1.0 - bias)
                scores.append(max(0.0, s))
            total = sum(scores)
            if total <= 0:
                break
            pick = rng.random() * total
            acc = 0.0
            chosen = cands[-1][0]
            for (b, d), s in zip(cands, scores):
                acc += s
                if acc >= pick:
                    chosen = b
                    break
            edges.append({"a": a, "b": chosen,
                          "d": round(dist(nodes[a], nodes[chosen]), 6)})
            adj[a].add(chosen)
            adj[chosen].add(a)
            union(a, chosen)
        if (qi + 1) % 1000 == 0 or qi + 1 == n:
            print(f"  linking... {qi + 1}/{n} nodes", flush=True)

    # --- connectivity pass (optional) ---
    # Cross-component search always runs at the full cap: components are by
    # definition beyond local reach, so this is where the rare long bridge
    # links legitimately come from.
    bridges = 0
    if params["connect"] and n > 1:
        comp = {find(i) for i in range(n)}
        span = maxd if maxd > 0 else locald
        while len(comp) > 1:
            best = None
            for a in range(n):
                for (b, d) in candidates(a, span):
                    if find(a) == find(b):
                        continue
                    if best is None or d < best[0]:
                        best = (d, a, b)
            if best is None:
                reps = {}
                for i in range(n):
                    reps.setdefault(find(i), i)
                rlist = list(reps.values())
                for i in range(len(rlist)):
                    for j in range(i + 1, len(rlist)):
                        d = dist(nodes[rlist[i]], nodes[rlist[j]])
                        if best is None or d < best[0]:
                            best = (d, rlist[i], rlist[j])
            if best is None:
                break
            _, a, b = best
            edges.append({"a": a, "b": b, "d": round(best[0], 6),
                          "bridge": True})
            adj[a].add(b)
            adj[b].add(a)
            union(a, b)
            bridges += 1
            comp = {find(i) for i in range(n)}

    # --- stats ---
    return nodes, edges, targets


def _dist_pos(a, b):
    return math.dist(a["pos"], b["pos"])


def add_root(nodes, edges, n_links=3, min_sep=None):
    """Insert the synthetic origin node (id 0, at the sphere centre) and link
    it to the n_links nearest-to-centre nodes (lowest rarity), spread apart
    so the player starts with options in different directions (separation
    defaults to 0.35x the nearest node's radius, relaxed if there aren't
    enough candidates). Real node ids are shifted up by one.
    Returns (nodes, edges)."""
    root = {
        "id": 0,
        "file": "__root__",
        "number": 0,
        "name": "Origin",
        "rarity": 0.0,
        "source": "System",
        "tag": "both",
        "description": "The Chaos Tree's root. Free to unlock; every other "
                       "node costs to unlock.",
        "pos": [0.0, 0.0, 0.0],
        "r": 0.0,
    }
    real = [dict(nd, id=nd["id"] + 1) for nd in nodes]
    out_edges = [{"a": e["a"] + 1, "b": e["b"] + 1, "d": e["d"],
                  **({"bridge": True} if e.get("bridge") else {})}
                 for e in edges]
    n_links = max(1, min(n_links, len(real)))
    cands = sorted(real, key=lambda nd: (nd["r"], nd["id"]))
    if min_sep is None:
        min_sep = 0.35 * (cands[0]["r"] if cands else 1.0)
    chosen = []
    for nd in cands:
        if len(chosen) >= n_links:
            break
        if all(_dist_pos(nd, c) >= min_sep for c in chosen):
            chosen.append(nd)
    for nd in cands:  # relax the separation rather than link fewer
        if len(chosen) >= n_links:
            break
        if all(nd["id"] != c["id"] for c in chosen):
            chosen.append(nd)
    for nd in chosen:
        out_edges.append({"a": 0, "b": nd["id"], "d": nd["r"]})
    return [root] + real, out_edges


def compute_stats(nodes, edges, targets):
    n = len(nodes)
    adj = [set() for _ in range(n)]
    for e in edges:
        adj[e["a"]].add(e["b"])
        adj[e["b"]].add(e["a"])
    degrees = Counter(len(adj[i]) for i in range(n))
    lens = [e["d"] for e in edges]
    parent = list(range(n))

    def find2(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        ra, rb = find2(e["a"]), find2(e["b"])
        if ra != rb:
            parent[ra] = rb
    components = len({find2(i) for i in range(n)})
    entries = [nd for nd in nodes if nd["file"] != "__root__"]
    stats = {
        "nodes": n,
        "entries": len(entries),
        "edges": len(edges),
        "components": components,
        "cycles": len(edges) - n + components,
        "bridges": sum(1 for e in edges if e.get("bridge")),
        "root": {"id": 0, "name": "Origin",
                 "children": [e["b"] for e in edges if e["a"] == 0]},
        "degree": {
            "min": min(degrees),
            "max": max(degrees),
            "requested_mean": round(sum(targets) / len(entries), 3)
                              if targets else 0,
            "mean": round(sum(d * c for d, c in degrees.items()) / n, 3),
            "histogram": {str(d): c for d, c in sorted(degrees.items())},
        },
        "link_distance": {
            "mean": round(sum(lens) / len(lens), 4) if lens else 0,
            "max": round(max(lens), 4) if lens else 0,
        },
        "tags": {t: sum(1 for nd in entries if nd["tag"] == t)
                 for t in ("gacha", "tree", "both")},
        "sources": {s: sum(1 for nd in entries if nd["source"] == s)
                    for s in sorted({nd["source"] for nd in entries})},
        "entry_tags": {t: sum(1 for nd in entries if t in (nd.get("tags") or []))
                       for t in sorted({tg for nd in entries
                                        for tg in (nd.get("tags") or [])})},
    }
    return stats


def save_tree(nodes, edges, stats, items, params, seed, out_path):
    payload = {
        "format": "chaos-tree",
        "version": 1,
        "seed": seed,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "params": params,
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return out_path


def list_sources():
    for file in ALL_FILES:
        srcs = set()
        for i in load_entries([file], None, None, set(), set(), True, True,
                              True, None):
            srcs.add(i["source"])
        print(f"{file}: {', '.join(sorted(srcs))}")


def list_tags():
    from collections import Counter
    c = Counter()
    for i in load_entries(ALL_FILES, None, None, set(), set(), True, True,
                          True, None):
        for t in i.get("tags", []):
            c[t] += 1
    for t, n in c.most_common():
        print(f"{t}: {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", default=",".join(ALL_FILES),
                    help="comma-separated gacha files")
    ap.add_argument("--rarity-min", type=float)
    ap.add_argument("--rarity-max", type=float)
    ap.add_argument("--sources", default="", help="comma-separated sources to include")
    ap.add_argument("--exclude-sources", default="")
    ap.add_argument("--include-gacha-only", action="store_true")
    ap.add_argument("--include-nsfw", action="store_true",
                    help="include (Nsfw)-tagged entries (excluded by default)")
    ap.add_argument("--include-noncon", action="store_true",
                    help="include (Noncon)-tagged entries (excluded by default)")
    ap.add_argument("--tags", default="",
                    help="comma-separated thematic tags to include (entry must have all of them)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--radius", type=float, default=10.0)
    ap.add_argument("--distance-variance", type=float, default=0.05)
    ap.add_argument("--clustering", type=float, default=0.3)
    ap.add_argument("--clusters", type=int, default=3)
    ap.add_argument("--degree-dist", default="poisson",
                    choices=["constant", "poisson", "powerlaw"])
    ap.add_argument("--mean-degree", type=float, default=2.5)
    ap.add_argument("--degree-min", type=int, default=1)
    ap.add_argument("--degree-max", type=int)
    ap.add_argument("--rejoin-bias", type=float, default=0.7)
    ap.add_argument("--root-links", type=int, default=3,
                    help="how many starting nodes link to the Origin root")
    ap.add_argument("--link-falloff", type=float, default=4.0)
    ap.add_argument("--local-link-distance", type=float, default=0.25)
    ap.add_argument("--max-link-distance", type=float, default=0.6)
    ap.add_argument("--no-connect", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--list-sources", action="store_true",
                    help="print available sources and exit")
    ap.add_argument("--list-tags", action="store_true",
                    help="print thematic tags and counts and exit")
    args = ap.parse_args()

    if args.list_sources:
        list_sources()
        return 0
    if args.list_tags:
        list_tags()
        return 0

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    if "all" in {f.lower() for f in files}:
        files = ALL_FILES
    sources = {s.strip() for s in args.sources.split(",") if s.strip()}
    excludes = {s.strip() for s in args.exclude_sources.split(",") if s.strip()}
    tag_filter = [t.strip() for t in args.tags.split(",") if t.strip()] or None

    items = load_entries(files, args.rarity_min, args.rarity_max,
                         sources, excludes, args.include_gacha_only,
                         args.include_nsfw, args.include_noncon, tag_filter)
    if args.limit and args.limit < len(items):
        rng = random.Random(args.seed)
        items = rng.sample(items, args.limit)

    if not items:
        sys.exit("no entries match the given filters")

    params = {
        "files": files,
        "rarity_min": args.rarity_min,
        "rarity_max": args.rarity_max,
        "sources": sorted(sources) or "all",
        "exclude_sources": sorted(excludes) or [],
        "include_gacha_only": args.include_gacha_only,
        "include_nsfw": args.include_nsfw,
        "include_noncon": args.include_noncon,
        "tags": sorted(tag_filter) if tag_filter else [],
        "limit": args.limit,
        "radius": args.radius,
        "distance_variance": args.distance_variance,
        "clustering": args.clustering,
        "clusters": args.clusters,
        "degree_dist": args.degree_dist,
        "mean_degree": args.mean_degree,
        "degree_min": args.degree_min,
        "degree_max": args.degree_max,
        "rejoin_bias": args.rejoin_bias,
        "link_falloff": args.link_falloff,
        "local_link_distance": args.local_link_distance,
        "max_link_distance": args.max_link_distance,
        "root_links": args.root_links,
        "connect": not args.no_connect,
    }

    rng = random.Random(args.seed)
    print(f"loaded {len(items)} entries, generating (seed {args.seed})...",
          flush=True)
    nodes, edges, targets = generate_tree(items, params, rng)
    print("linking done, adding root + stats...", flush=True)
    nodes, edges = add_root(nodes, edges, n_links=args.root_links)
    stats = compute_stats(nodes, edges, targets)

    out = args.out or os.path.join(TREE_DIR, f"chaos-tree-{args.seed}.json")
    save_tree(nodes, edges, stats, items, params, args.seed, out)

    print(f"tree: {stats['entries']} entries + root = {stats['nodes']} nodes, "
          f"{stats['edges']} edges, {stats['components']} component(s), "
          f"{stats['cycles']} cycle(s), {stats['bridges']} bridge(s)")
    print(f"degree: min {stats['degree']['min']}, mean "
          f"{stats['degree']['mean']}, max {stats['degree']['max']}")
    print(f"link distance: mean {stats['link_distance']['mean']}, "
          f"max {stats['link_distance']['max']} (radius {args.radius})")
    print(f"tags: {stats['tags']}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
