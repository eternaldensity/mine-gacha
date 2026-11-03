#!/usr/bin/env python3
"""Chaos Tree usage engine + CLI.

The tree (a JSON file produced by tools/generate_tree.py) is explored by
unlocking nodes. The synthetic root (node 0) is free; every other node costs
1 core plus points equal to 10^rarity. Tickets provide 1 core each and add
their tier's points to a shared wallet, so points pool across tickets while
cores keep the 1-node-per-ticket rule.

By default only nodes adjacent to an unlocked node are visible/unlockable.
Special tickets reach further (see below).

Ticket tiers (points; cores always 1)
    trash 5, bronze 50, silver 500, gold 5k, aluminium 25k, platinum 50k,
    diamond 500k, legendary 5M, mythical 50M, divine 500M, transcendent 5B.
    Wild tickets roll 2d8 instead: smaller die N pays 10^(N+1) points,
    doubled on doubles.
    (points pool in the wallet, so higher rarities are reachable by
    combining several tickets)

Special tickets (tier optional; if present the tier still adds its core's
points, otherwise the ticket is traversal-only and adds 0 points):
    skip N           unlock a node up to N extra hops beyond the frontier
                     (hop distance <= 1+N from the unlocked set)
    <cat> jump       unlock the closest node of category <cat> (ability,
                     item, skill, trait, familiar) that is not directly
                     connected to a chosen unlocked node (Euclidean distance)
    choice N jump    same, but choose from the N closest candidates
    hop              unlock a node at hop distance >= 2, plus ONE free
                     intermediate node on the shortest path from the
                     unlocked set to it
    coupon           pays no points; instead banks its tier value, spent
                     automatically (oldest first, remainder lost) against
                     the points cost of a later unlock (cores still due)

Ticket options:
    twin             any ticket may carry the twin token ('gold twin');
                     it grants a second core at award (free, always allowed)

Tree meta nodes: normal ability/item/trait entries carrying a (Tree) tag
and a (Meta:<key>:<value>) token in their description (stored in the JSON
'meta' field). While unlocked they grant an effect:
    sight:N            view locked nodes N extra connections away
    sight-cat:<cat>:N  view <cat> nodes N extra connections away
    see-far            view locked nodes within SEE_FAR_DISTANCE of unlocked
                       nodes even if unconnected
    survey:N           see the names of locked nodes N extra connections away
    trace-name         allow the trace command against node names (free,
                       unlimited while unlocked)
    trace-name-use     one use: trace routes to a node by name
    trace-desc         allow the trace command against descriptions
    compass            allow trace --source against sources
    reveal-full        permanently reveal the whole tree
    ticket-bonus:N     every ticket awarded grants N% extra points (additive)
    echo               one use: the next awarded ticket pays double points
    reveal-temp        one use: reveal the full tree for 10 seconds
    lock-refund        one use: lock an unlocked node and refund core+points
    lifeline           one use: free unlock of a frontier (adjacent) node
    recall             one use: undo the most recent unlock (refund)
    add-link:N         N uses: add an edge between two close unconnected nodes
    gacha:R or R-S     one use: randomly unlock a locked node in that rarity
                       range (e.g. gacha:5 = 0..5, gacha:5-7 = 5..7)
    duplicate:R        one use: unlock a random locked node sharing a source
                       with one of your nodes (Generic excluded), rarity <= R
    shuffle            one use: swap a visible locked node with a random
                       not-visible one of similar rarity (+-0.2)
    swap               one use: swap two visible locked nodes of your choice
    reshuffle          unlimited shuffle, costs a quarter of the node's cost
    shake              one use: reassign entries among locked nodes
                       (rarity-preserving; positions and links stay put)
    chaosquake         one use: reassign entries among ALL non-root nodes;
                       unlocked nodes keep their places but not their faces
    gamble:N           N gambled tickets: roll a d20 per awarded ticket
                       (20: tier up, 17-19: twin, 13-16: new kind,
                       8-12: nothing, 2-7: tier down, 1: destroyed for
                       no base core and half points)
    gamble-reroll:N    reroll gamble d20s of N and below (best die wins)
    gamble-twice       gambles get a second d20 unless the first is a 20
    root-pact          nodes within two connections of the root cost no core
                       but 10x points
Unlocking is adjacency-based: sight/reveal only let you SEE further; the
skip/jump/hop tickets are still how you travel.

Modes of use (CLI):
    init STATE --tree TREE.json          create a fresh player state
    award STATE [--gamble] TICKET [...]  award tickets (adds cores + points;
                                         --gamble rolls a d20 per ticket)
    state STATE                          show wallet, cores, inventory, nodes
    visible STATE                        list unlockable nodes and their costs
    unlock STATE NODE                    normal unlock (must be adjacent)
    skip STATE NODE [--n N]              unlock with a skip ticket
    jump STATE CATEGORY --from ID [--pick I]   jump / choice-N jump
    hop STATE NODE                       unlock with a hop ticket
    use STATE ACTION [ARGS]              lockrefund NODE | addlink A B |
                                         reveal | gacha | lifeline NODE |
                                         recall | duplicate | shuffle NODE |
                                         swap A B | reshuffle NODE |
                                         shake | chaosquake
    trace STATE --name X [--n N]         trace routes to closest matches
           STATE --desc X [--n N]
           STATE --source X [--n N]      (needs the matching ability)
"""
import argparse
import json
import math
import os
import random
import re
import sys
import time
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- editable tuning -------------------------------------------------------
# Tier ladder, lowest first. Wild has no fixed value: awarding a wild ticket
# rolls 2d8, takes the smaller as N for 10^(N+1) points, doubled on doubles.
# Rank-ups/downs follow _RANK_UP/_RANK_DOWN below rather than this order:
# gold<->platinum and mythical<->divine skip over aluminium and wild.
TIER_POINTS = {
    "trash": 5,
    "bronze": 50,
    "silver": 500,
    "gold": 5000,
    "aluminium": 25000,
    "platinum": 50000,
    "diamond": 500000,
    "legendary": 5000000,
    "mythical": 50000000,
    "wild": 0,
    "divine": 500000000,
    "transcendent": 5000000000,
}
CATEGORIES = ["ability", "item", "skill", "trait", "familiar"]
ROOT_ID = 0
SEE_FAR_DISTANCE = 3.5      # sphere units (radius 10); used by the Far Sight meta node
ADD_LINK_DISTANCE = 2.5     # sphere units (radius 10); max span for Graft
TRACE_DEFAULT_N = 3
META_RE = re.compile(r"\(Meta:([^)]+)\)")


# --- tree + state ----------------------------------------------------------

def load_tree(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    nodes = data["nodes"]
    by_id = {nd["id"]: nd for nd in nodes}
    adj = {i: set() for i in by_id}
    for e in data["edges"]:
        adj[e["a"]].add(e["b"])
        adj[e["b"]].add(e["a"])
    return {"nodes": nodes, "by_id": by_id, "adj": adj,
            "edges": data["edges"], "meta": data, "path": path}


def new_state(tree_path):
    return {"tree": tree_path, "points": 0.0, "cores": 0,
            "inventory": [], "unlocked": [ROOT_ID],
            "meta_used": {}, "added_links": [], "reveal_temp_until": 0,
            "history": [], "swaps": [], "echo_used": 0,
            "entry_swaps": []}


def load_state(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


# --- core helpers ----------------------------------------------------------

def fmt(n):
    return f"{n:,.2f}"


def node_cost(tree, nid):
    return 10.0 ** tree["by_id"][nid]["rarity"]


def parse_meta(desc):
    """Extract (Meta:key:value) / (Meta:flag) tokens from a description."""
    out = []
    for m in META_RE.finditer(desc):
        key = m.group(1)
        if ":" in key:
            k, v = key.split(":", 1)
            try:
                v = int(v)
            except ValueError:
                pass
        else:
            k, v = key, True
        out.append((k, v))
    return out


def iter_meta(nd):
    """Meta tokens for a node: from the JSON 'meta' field if present, plus
    any (Meta:...) tokens left in the raw description (e.g. hand-made trees)."""
    for raw in nd.get("meta") or []:
        key = raw[5:] if raw.startswith("Meta:") else raw
        if ":" in key:
            k, v = key.split(":", 1)
            try:
                v = int(v)
            except ValueError:
                pass
        else:
            k, v = key, True
        yield k, v
    yield from parse_meta(nd["description"])


def derive_meta(tree, unlocked):
    """Capabilities granted by currently unlocked meta nodes."""
    meta = {"sight": 0, "see_far": False, "trace_name": False,
            "trace_desc": False, "reveal_full": False, "reveal_temp": False,
            "ticket_bonus": 0, "lock_refund": 0, "add_link": 0,
            "gacha": 0, "gacha_min": 0, "gacha_max": 0,
            "echo": 0, "survey": 0, "compass": False, "duplicate": 0,
            "duplicate_max": 0, "cat_sight": {}, "lifeline": 0,
            "recall": 0, "root_pact": False, "shuffle": 0, "swap": 0,
            "reshuffle": 0, "shake": 0, "chaosquake": 0,
            "gamble": 0, "gamble_reroll": 0, "gamble_twice": False,
            "trace_name_use": 0}
    for u in unlocked:
        nd = tree["by_id"][u]
        for k, v in iter_meta(nd):
            if k == "sight":
                meta["sight"] = max(meta["sight"], int(v))
            elif k == "see-far":
                meta["see_far"] = True
            elif k == "trace-name":
                meta["trace_name"] = True
            elif k == "trace-desc":
                meta["trace_desc"] = True
            elif k == "reveal-full":
                meta["reveal_full"] = True
            elif k == "reveal-temp":
                meta["reveal_temp"] = True
            elif k == "ticket-bonus":
                meta["ticket_bonus"] += int(v)
            elif k == "lock-refund":
                meta["lock_refund"] += 1
            elif k == "add-link":
                meta["add_link"] += int(v)
            elif k == "gacha":
                meta["gacha"] += 1
                if isinstance(v, str) and "-" in v:
                    lo, hi = v.split("-", 1)
                    meta["gacha_min"] = max(meta["gacha_min"], int(lo))
                    meta["gacha_max"] = max(meta["gacha_max"], int(hi))
                else:
                    meta["gacha_max"] = max(meta["gacha_max"], int(v))
            elif k == "echo":
                meta["echo"] += 1
            elif k == "survey":
                meta["survey"] = max(meta["survey"], 1 if v is True else int(v))
            elif k == "compass":
                meta["compass"] = True
            elif k == "duplicate":
                meta["duplicate"] += 1
                meta["duplicate_max"] = max(meta["duplicate_max"], int(v))
            elif k == "sight-cat":
                if isinstance(v, str) and ":" in v:
                    cat, depth = v.split(":", 1)
                else:
                    cat, depth = str(v), 1
                meta["cat_sight"][cat] = max(meta["cat_sight"].get(cat, 0),
                                             int(depth))
            elif k == "lifeline":
                meta["lifeline"] += 1
            elif k == "recall":
                meta["recall"] += 1
            elif k == "root-pact":
                meta["root_pact"] = True
            elif k == "shuffle":
                meta["shuffle"] += 1
            elif k == "swap":
                meta["swap"] += 1
            elif k == "reshuffle":
                meta["reshuffle"] += 1
            elif k == "shake":
                meta["shake"] += 1
            elif k == "chaosquake":
                meta["chaosquake"] += 1
            elif k == "gamble":
                meta["gamble"] += int(v)
            elif k == "gamble-reroll":
                meta["gamble_reroll"] = max(meta["gamble_reroll"], int(v))
            elif k == "gamble-twice":
                meta["gamble_twice"] = True
            elif k == "trace-name-use":
                meta["trace_name_use"] += 1
    return meta


def view_state(tree, state):
    """Derived capabilities plus the temporary-reveal timestamp."""
    meta = derive_meta(tree, state["unlocked"])
    meta["reveal_temp_until"] = state.get("reveal_temp_until", 0)
    return meta


def _frontier(tree, unlocked):
    adj = tree["adj"]
    f = set()
    for u in unlocked:
        f.update(adj[u])
    f.difference_update(unlocked)
    return f


def visible(tree, unlocked, meta=None):
    """Locked nodes you can see. Base = neighbours of unlocked nodes; the
    sight/see-far/cat-sight/reveal meta nodes extend this."""
    meta = meta or {}
    now = time.time()
    if meta.get("reveal_full") or meta.get("reveal_temp_until", 0) >= now:
        return sorted(i for i in tree["by_id"] if i not in unlocked)
    adj = tree["adj"]
    sight = meta.get("sight", 0)
    cat_sight = meta.get("cat_sight", {})
    if sight <= 0 and not meta.get("see_far") and not cat_sight:
        vis = set()
        for u in unlocked:
            vis.update(adj[u])
        vis.difference_update(unlocked)
        return sorted(vis)
    dist, _ = hop_distances(tree, unlocked)
    vis = {i for i in dist if dist[i] <= 1 + sight and i not in unlocked}
    for cat, depth in cat_sight.items():
        for i in dist:
            if (i not in unlocked and tree["by_id"][i]["file"] == cat
                    and dist[i] <= 1 + depth):
                vis.add(i)
    if meta.get("see_far"):
        for u in unlocked:
            unode = tree["by_id"][u]
            for nd in tree["nodes"]:
                if nd["id"] in unlocked or nd["id"] in vis:
                    continue
                if distance3(unode, nd) <= SEE_FAR_DISTANCE:
                    vis.add(nd["id"])
    return sorted(vis)


def survey_names(tree, unlocked, meta=None):
    """Names of locked nodes within 1+survey extra connections that are not
    already shown in full detail by the visible list."""
    meta = meta or {}
    depth = meta.get("survey", 0)
    if not depth:
        return []
    dist, _ = hop_distances(tree, unlocked)
    shown = set(visible(tree, unlocked, meta))
    out = []
    for i in dist:
        if (i not in unlocked and i not in shown
                and 1 < dist[i] <= 1 + depth):
            out.append((i, tree["by_id"][i]["name"]))
    return sorted(out)


def hop_distances(tree, unlocked):
    """BFS over the full graph from the unlocked set. Returns (dist, prev)."""
    adj = tree["adj"]
    dist, prev = {}, {}
    q = deque()
    for u in unlocked:
        dist[u] = 0
        q.append(u)
    while q:
        a = q.popleft()
        for b in adj[a]:
            if b not in dist:
                dist[b] = dist[a] + 1
                prev[b] = a
                q.append(b)
    return dist, prev


def distance3(a, b):
    return math.dist(a["pos"], b["pos"])


def _root_shell(tree, depth):
    """Ids within `depth` connections of the Origin (the root included). Not
    cached: the tree is sparse and Shuffle/Swap/Add-Link mutate adjacency."""
    adj = tree["adj"]
    seen = {ROOT_ID}
    frontier = [ROOT_ID]
    for _ in range(depth):
        nxt = []
        for a in frontier:
            for b in adj[a]:
                if b not in seen:
                    seen.add(b)
                    nxt.append(b)
        frontier = nxt
    return seen


def _node_cost_for(state, tree, nid):
    """Points cost to unlock nid now. Under Root Pact, nodes within two
    connections of the root cost 10x points."""
    cost = node_cost(tree, nid)
    meta = derive_meta(tree, state["unlocked"])
    if meta.get("root_pact") and nid in _root_shell(tree, 2):
        cost *= 10
    return cost


def _core_cost_for(state, tree, nid):
    """Cores needed to unlock nid now. Under Root Pact, nodes within two
    connections of the root cost no core."""
    meta = derive_meta(tree, state["unlocked"])
    if meta.get("root_pact") and nid in _root_shell(tree, 2):
        return 0
    return 1


def _pay(state, tree, nid):
    core_cost = _core_cost_for(state, tree, nid)
    if state["cores"] < core_cost:
        raise UsageError("not enough cores (award a ticket first)")
    cost = _node_cost_for(state, tree, nid)
    pick, cover = None, 0
    if cost > 0:
        for t in state["inventory"]:
            if t["kind"] == "coupon":
                pick, cover = t, min(cost, t["value"])
                break
    if state["points"] < cost - cover:
        raise UsageError(
            f"not enough points: need {fmt(cost - cover)}, have {fmt(state['points'])}")
    if pick is not None:
        state["inventory"].remove(pick)
    state["cores"] -= core_cost
    state["points"] -= cost - cover


def _unlock(state, nid, extra=None):
    add = [nid] + (extra or [])
    state["unlocked"].extend(add)
    state["unlocked"] = sorted(set(state["unlocked"]))
    state.setdefault("history", []).extend(add)


def _swap_nodes(tree, a, b):
    """Exchange the position and adjacency of two nodes (Shuffle/Swap)."""
    if a == b:
        return
    na, nb = tree["by_id"][a], tree["by_id"][b]
    na["pos"], nb["pos"] = nb["pos"], na["pos"]
    if "r" in na and "r" in nb:
        na["r"], nb["r"] = nb["r"], na["r"]
    adj = tree["adj"]
    sa = set(adj[a]) - {b}
    sb = set(adj[b]) - {a}
    ab = b in adj[a]
    for n in sa:
        adj[n].discard(a)
    for n in sb:
        adj[n].discard(b)
    adj[a] = sb
    adj[b] = sa
    for n in sb:
        adj[n].add(a)
    for n in sa:
        adj[n].add(b)
    if ab:
        adj[a].add(b)
        adj[b].add(a)


class UsageError(Exception):
    pass


# --- ticket parsing / awarding ---------------------------------------------

def parse_ticket(spec):
    """Parse a ticket spec like 'gold', 'gold skip2', 'item jump',
    'choice 3 jump ability', 'hop gold', 'gold twin'. Returns
    (tier, kind, params). Tier is optional for special tickets (0 points,
    traversal only). The 'twin' token flags a +1 bonus core at award."""
    toks = spec.lower().replace(",", " ").split()
    tier, kind = None, "plain"
    n, category, twin = None, None, False
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in TIER_POINTS:
            tier = t
        elif t in CATEGORIES:
            category = t
        elif t == "skip":
            kind = "skip"
            if i + 1 < len(toks) and toks[i + 1].isdigit():
                n = int(toks[i + 1])
                i += 1
        elif t.startswith("skip") and t[4:].isdigit():
            kind, n = "skip", int(t[4:])
        elif t == "hop":
            kind = "hop"
        elif t == "jump":
            if kind == "plain":
                kind = "jump"
        elif t == "choice":
            kind = "choice"
            if i + 1 < len(toks) and toks[i + 1].isdigit():
                n = int(toks[i + 1])
                i += 1
        elif t.startswith("choice") and t[6:].isdigit():
            kind, n = "choice", int(t[6:])
        elif t == "twin":
            twin = True
        elif t == "coupon":
            kind = "coupon"
        else:
            raise UsageError(f"unrecognised ticket token: {t!r}")
        i += 1

    params = {}
    if twin:
        params["twin"] = True
    if kind == "skip":
        params["n"] = n or 1
    elif kind == "jump":
        if category is None:
            raise UsageError(
                f"jump ticket needs a category ({', '.join(CATEGORIES)})")
        params["category"] = category
    elif kind == "choice":
        params["n"] = n or 3
        params["category"] = category  # None = any category
    if tier is None and kind == "plain":
        raise UsageError("a plain ticket needs a tier "
                         f"({', '.join(TIER_POINTS)})")
    if tier is None and kind == "coupon":
        raise UsageError("a coupon ticket needs a tier "
                         f"({', '.join(TIER_POINTS)})")
    return tier, kind, params


def award(state, spec, bonus_pct=0, echo=False, gamble=False, tree=None):
    """Award a ticket: +1 core (a 'twin' ticket grants a second core) plus
    tier points. Special tickets also land in the inventory. With
    gamble=True one gamble charge is spent rolling a d20 for the ticket
    (needs tree=... to read unlocked dice). Returns
    (tier, kind, params, pts) with the points actually paid."""
    tier, kind, params = parse_ticket(spec)
    twin = params.get("twin", False)
    destroyed = False
    if gamble:
        if tree is None:
            raise UsageError("gambling a ticket needs its tree")
        tier, kind, params, destroyed = gamble_ticket(
            state, tree, tier, kind, params)
        twin = params.get("twin", False)
    cores = 1 + (1 if twin else 0)
    if tier == "wild":
        d1, d2 = _wild_rolls()
        base = wild_points(d1, d2)
        params["wild"] = [d1, d2]
    else:
        base = TIER_POINTS.get(tier, 0)
    if destroyed:
        # generosity rule: the base core is lost but a twin keeps one
        cores = 1 if twin else 0
        base = base / 2
    state["cores"] += cores
    pts = base * (1.0 + bonus_pct / 100.0)
    if echo:
        pts *= 2.0
        state["echo_used"] = state.get("echo_used", 0) + 1
    if kind == "coupon":
        # coupons pay no points now; the would-be payout becomes the
        # coupon's value toward a later unlock (remainder lost on use)
        params["value"] = pts
        pts = 0
    state["points"] += pts
    if kind != "plain" and not destroyed:
        ticket = {"kind": kind, "tier": tier}
        ticket.update(params)
        state["inventory"].append(ticket)
    return tier, kind, params, pts


def _wild_rolls():
    """2d8 for a wild ticket. Module-level so tests can script rolls."""
    return random.randint(1, 8), random.randint(1, 8)


def wild_points(d1, d2):
    """Wild ticket base points: smaller die N -> 10^(N+1), doubled on doubles."""
    pts = 10.0 ** (min(d1, d2) + 1)
    if d1 == d2:
        pts *= 2.0
    return pts


def _d20():
    """One d20 roll. Module-level indirection so tests can script rolls."""
    return random.randint(1, 20)


def gambler_effect(d):
    """d20 value -> effect key (mirrors the Gacha Gambler trait)."""
    if d == 20:
        return "rankUp"
    if d >= 17:
        return "twin"
    if d >= 13:
        return "changeType"
    if d >= 8:
        return "nothing"
    if d >= 2:
        return "rankDown"
    return "destroyed"


def _shift_tier(tier, delta):
    """Move a tier up/down the rank graph (not plain ladder order):
    gold<->platinum skip over aluminium, and mythical<->divine skip over
    wild; aluminium and wild rank to their neighbours. Bottom-1 falls to
    tierless, top floors."""
    table = _RANK_UP if delta > 0 else _RANK_DOWN
    for _ in range(abs(delta)):
        if tier is None:
            tier = "bronze" if delta > 0 else None
            continue
        tier = table.get(tier, tier)
    return tier


_RANK_UP = {
    "trash": "bronze", "bronze": "silver", "silver": "gold",
    "gold": "platinum", "aluminium": "platinum",
    "platinum": "diamond", "diamond": "legendary",
    "legendary": "mythical", "mythical": "divine",
    "wild": "divine", "divine": "transcendent",
    "transcendent": "transcendent",
}
_RANK_DOWN = {
    "trash": None, "bronze": "trash", "silver": "bronze",
    "gold": "silver", "aluminium": "gold", "platinum": "gold",
    "diamond": "platinum", "legendary": "diamond",
    "mythical": "legendary", "wild": "mythical",
    "divine": "mythical", "transcendent": "divine",
}


def _gamble_new_kind(kind):
    pool = ["plain", "skip", "jump", "choice", "hop"]
    pool.remove(kind)
    return random.choice(pool)


def _gamble_kind_params(kind):
    if kind == "skip":
        return {"n": 1}
    if kind == "jump":
        return {"category": random.choice(CATEGORIES)}
    if kind == "choice":
        return {"n": 2, "category": None}
    return {}


def _settle_roll(threshold):
    """Roll until above the reroll threshold; returns (d, discarded)."""
    trail = []
    d = _d20()
    while d <= threshold:
        trail.append(d)
        d = _d20()
    return d, trail


def gamble_ticket(state, tree, tier, kind, params):
    """Spend one gamble charge rolling a d20 for a ticket. Applies rank,
    twin, kind-change and destroy effects; returns
    (tier, kind, params, destroyed) with the rolls stamped into params
    (d20, geffect, and rerolls when any were discarded)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "gamble") >= meta["gamble"]:
        raise UsageError("no gamble charge left")
    state["meta_used"]["gamble"] = _used(state, "gamble") + 1
    threshold = meta["gamble_reroll"]
    rerolls = []
    d, trail = _settle_roll(threshold)
    rerolls.extend(trail)
    rolls = [(d, gambler_effect(d))]
    if meta["gamble_twice"] and d != 20:
        d2, trail2 = _settle_roll(threshold)
        rerolls.extend(trail2)
        rolls.append((d2, gambler_effect(d2)))
    twin = params.get("twin", False)
    destroyed = False
    for d, effect in rolls:
        if effect == "rankUp":
            tier = _shift_tier(tier, +1)
        elif effect == "twin":
            twin = True
        elif effect == "changeType":
            kind = _gamble_new_kind(kind)
            for k in ("n", "category"):
                params.pop(k, None)
            params.update(_gamble_kind_params(kind))
        elif effect == "rankDown":
            tier = _shift_tier(tier, -1)
        elif effect == "destroyed":
            destroyed = True
    if twin:
        params["twin"] = True
    if len(rolls) == 1:
        params["d20"], params["geffect"] = rolls[0]
    else:
        params["d20"] = [d for d, _ in rolls]
        params["geffect"] = [e for _, e in rolls]
    if rerolls:
        params["rerolls"] = rerolls
    if destroyed:
        params["destroyed"] = True
    return tier, kind, params, destroyed


GAMBLE_LABELS = {"rankUp": "Rank Up", "twin": "Twin",
                 "changeType": "New Kind", "nothing": "No change",
                 "rankDown": "Rank Down", "destroyed": "Destroyed"}


def gamble_note(params):
    """Short human-readable summary of a gambled ticket's rolls."""
    if "d20" not in params:
        return ""
    d, e = params["d20"], params["geffect"]
    if not isinstance(d, list):
        d, e = [d], [e]
    note = "d20 " + "+".join(f"{v} {GAMBLE_LABELS[g]}" for v, g in zip(d, e))
    if params.get("rerolls"):
        note += f" (rerolled {', '.join(map(str, params['rerolls']))})"
    if params.get("destroyed"):
        note += " DESTROYED"
    return note


# --- unlocks ---------------------------------------------------------------

def unlock(state, tree, nid):
    """Normal unlock: node must be adjacent to an unlocked node."""
    if nid == ROOT_ID:
        raise UsageError("the root is free")
    if nid in state["unlocked"]:
        raise UsageError(f"node {nid} is already unlocked")
    if nid not in _frontier(tree, state["unlocked"]):
        raise UsageError(f"node {nid} is not adjacent to an unlocked node "
                         f"(use a skip/jump/hop ticket to reach it)")
    _pay(state, tree, nid)
    _unlock(state, nid)


def unlock_skip(state, tree, nid, n=None):
    """Unlock a node up to n extra hops beyond the frontier."""
    if nid in state["unlocked"]:
        raise UsageError(f"node {nid} is already unlocked")
    dist, _ = hop_distances(tree, state["unlocked"])
    if nid not in dist:
        raise UsageError(f"node {nid} is not connected to the unlocked set")
    tickets = [t for t in state["inventory"] if t["kind"] == "skip"]
    pick = None
    if n is not None:
        pick = next((t for t in tickets if t["n"] == n), None)
        if pick is None:
            raise UsageError(f"no skip {n} ticket in inventory")
    else:
        pick = next((t for t in sorted(tickets, key=lambda t: t["n"])
                     if 1 + t["n"] >= dist[nid]), None)
        if pick is None:
            raise UsageError(
                f"no skip ticket reaches node {nid} ({dist[nid]} hops; "
                f"need 1+N >= {dist[nid]})")
    state["inventory"].remove(pick)
    _pay(state, tree, nid)
    _unlock(state, nid)


def _jump_candidates(tree, category, from_id, unlocked):
    adj = tree["adj"]
    if from_id not in unlocked:
        raise UsageError(f"chosen node {from_id} is not unlocked")
    cands = []
    for nd in tree["nodes"]:
        if nd["id"] == ROOT_ID:
            continue
        if category is not None and nd["file"] != category:
            continue
        if nd["id"] in unlocked or nd["id"] in adj[from_id]:
            continue
        cands.append((distance3(tree["by_id"][from_id], nd), nd))
    cands.sort(key=lambda c: (c[0], c[1]["id"]))
    return cands


def unlock_jump(state, tree, category, from_id, pick=0):
    """Jump / choice-N jump. pick is the 0-based index into the closest list.
    category may be None for category-less choice tickets. Returns the
    unlocked node id."""
    tickets = [t for t in state["inventory"]
               if t["kind"] in ("jump", "choice")
               and (t.get("category") is None or t.get("category") == category)]
    if not tickets:
        label = category or "any"
        raise UsageError(f"no {label} jump/choice ticket in inventory")
    ticket = tickets[0]
    eff_cat = category if category is not None else ticket.get("category")
    cands = _jump_candidates(tree, eff_cat, from_id, state["unlocked"])
    if not cands:
        raise UsageError(f"no unlockable {'nodes' if eff_cat is None else eff_cat}"
                         f" nodes not directly connected to node {from_id}")
    limit = ticket["n"] if ticket["kind"] == "choice" else 1
    cands = cands[:limit]
    if pick < 0 or pick >= len(cands):
        raise UsageError(f"pick {pick} out of range (0..{len(cands) - 1})")
    state["inventory"].remove(ticket)
    target = cands[pick][1]["id"]
    _pay(state, tree, target)
    _unlock(state, target)
    return target


def unlock_hop(state, tree, nid):
    """Unlock a distant node plus one free intermediate on the shortest path."""
    tickets = [t for t in state["inventory"] if t["kind"] == "hop"]
    if not tickets:
        raise UsageError("no hop ticket in inventory")
    if nid in state["unlocked"]:
        raise UsageError(f"node {nid} is already unlocked")
    dist, prev = hop_distances(tree, state["unlocked"])
    if nid not in dist:
        raise UsageError(f"node {nid} is not connected to the unlocked set")
    if dist[nid] < 2:
        raise UsageError(f"node {nid} is only {dist[nid]} hop(s) away; "
                         f"a hop ticket needs a node at least 2 hops out")
    path = [nid]
    cur = nid
    while cur in prev:
        cur = prev[cur]
        path.append(cur)
    path.reverse()  # seed ... nid
    intermediate = path[1]
    state["inventory"].remove(tickets[0])
    _pay(state, tree, nid)
    _unlock(state, nid, extra=[intermediate])


# --- meta abilities ---------------------------------------------------------

def _used(state, key):
    return state["meta_used"].get(key, 0)


def apply_added_links(tree, state):
    for a, b in state.get("added_links", []):
        tree["adj"][a].add(b)
        tree["adj"][b].add(a)
    return tree


def apply_swaps(tree, state):
    for a, b in state.get("swaps", []):
        _swap_nodes(tree, a, b)
    return tree


def _swap_tol(tree):
    """Rarity tolerance for entry shuffles: the tree's placement variance
    (0.05 when unknown, e.g. hand-made trees)."""
    try:
        return float(tree.get("meta", {}).get("params", {}).get(
            "distance_variance", 0.05))
    except (AttributeError, TypeError, ValueError):
        return 0.05


def _swap_entries(tree, a, b):
    """Exchange two nodes' entries (everything but id/pos/radius)."""
    na, nb = tree["by_id"][a], tree["by_id"][b]
    for key in set(na) | set(nb):
        if key in ("id", "pos", "r"):
            continue
        na[key], nb[key] = nb.get(key), na.get(key)


def apply_entry_swaps(tree, state):
    for a, b in state.get("entry_swaps", []):
        if a in tree["by_id"] and b in tree["by_id"]:
            _swap_entries(tree, a, b)
    return tree


def _shuffle_entry_bucket(state, tree, ids):
    """Permute a bucket's entries (one n-cycle through a shuffled order)."""
    order = list(ids)
    random.shuffle(order)
    swaps = state.setdefault("entry_swaps", [])
    n = 0
    for j in range(1, len(order)):
        a, b = order[0], order[j]
        _swap_entries(tree, a, b)
        swaps.append([a, b])
        n += 1
    return n


def _entry_buckets(tree, ids):
    tol = _swap_tol(tree)
    buckets = {}
    for i in ids:
        buckets.setdefault(round(tree["by_id"][i]["rarity"] / tol), []).append(i)
    return [v for v in buckets.values() if len(v) > 1]


def use_shake(state, tree):
    """Single use: reassign entries among LOCKED nodes. Positions, links
    and rarities-per-position stay put (within placement variance)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "shake") >= meta["shake"]:
        raise UsageError("no shake charge left")
    unlocked = set(state["unlocked"])
    ids = [nd["id"] for nd in tree["nodes"]
           if nd["id"] != ROOT_ID and nd["id"] not in unlocked]
    buckets = _entry_buckets(tree, ids)
    if not buckets:
        raise UsageError("no locked nodes share a rarity band to shuffle")
    n = sum(_shuffle_entry_bucket(state, tree, b) for b in buckets)
    state["meta_used"]["shake"] = _used(state, "shake") + 1
    return n


def use_chaosquake(state, tree):
    """Single use: reassign entries among ALL non-root nodes, locked or
    unlocked. Unlocked nodes keep their places but not their faces."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "chaosquake") >= meta["chaosquake"]:
        raise UsageError("no chaosquake charge left")
    ids = [nd["id"] for nd in tree["nodes"] if nd["id"] != ROOT_ID]
    buckets = _entry_buckets(tree, ids)
    if not buckets:
        raise UsageError("no nodes share a rarity band to shuffle")
    n = sum(_shuffle_entry_bucket(state, tree, b) for b in buckets)
    state["meta_used"]["chaosquake"] = _used(state, "chaosquake") + 1
    return n


def use_lock_refund(state, tree, nid):
    """Lock an unlocked node and refund its core + points (single use)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "lock_refund") >= meta["lock_refund"]:
        raise UsageError("no lock-refund charge left")
    if nid == ROOT_ID:
        raise UsageError("the root cannot be locked")
    if nid not in state["unlocked"]:
        raise UsageError(f"node {nid} is not unlocked")
    refund = _node_cost_for(state, tree, nid)
    refund_core = _core_cost_for(state, tree, nid)
    state["unlocked"].remove(nid)
    state["points"] += refund
    state["cores"] += refund_core
    state["meta_used"]["lock_refund"] = _used(state, "lock_refund") + 1
    return refund


def use_add_link(state, tree, a, b):
    """Add an edge between two close, unconnected nodes (limited uses)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "add_link") >= meta["add_link"]:
        raise UsageError("no add-link charge left")
    if a == b or a == ROOT_ID or b == ROOT_ID:
        raise UsageError("links join two real nodes")
    if b in tree["adj"][a]:
        raise UsageError(f"nodes {a} and {b} are already connected")
    d = distance3(tree["by_id"][a], tree["by_id"][b])
    if d > ADD_LINK_DISTANCE:
        raise UsageError(f"nodes {a} and {b} are too far apart "
                         f"({fmt(d)} > {ADD_LINK_DISTANCE})")
    tree["adj"][a].add(b)
    tree["adj"][b].add(a)
    state["added_links"].append([a, b])
    state["meta_used"]["add_link"] = _used(state, "add_link") + 1
    return d


def use_reveal(state, tree):
    """Temporary full reveal (10 seconds)."""
    meta = derive_meta(tree, state["unlocked"])
    if not meta["reveal_temp"]:
        raise UsageError("you have no Glimpse (reveal) charge")
    state["reveal_temp_until"] = time.time() + 10
    return state["reveal_temp_until"]


def use_gacha(state, tree):
    """Randomly unlock a locked node in the ticket's rarity range."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "gacha") >= meta["gacha"]:
        raise UsageError("no gacha charge left")
    lo, hi = meta["gacha_min"], meta["gacha_max"]
    eligible = [nd for nd in tree["nodes"]
                if nd["id"] != ROOT_ID and nd["id"] not in state["unlocked"]
                and lo <= nd["rarity"] <= hi]
    if not eligible:
        raise UsageError(f"no locked node in the rarity range "
                         f"{lo}..{hi} to roll")
    target = random.choice(eligible)
    _unlock(state, target["id"])
    state["meta_used"]["gacha"] = _used(state, "gacha") + 1
    return target


def use_lifeline(state, tree, nid):
    """Unlock a frontier node (adjacent to an unlocked node) for free."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "lifeline") >= meta["lifeline"]:
        raise UsageError("no lifeline charge left")
    if nid == ROOT_ID:
        raise UsageError("the root is free already")
    if nid in state["unlocked"]:
        raise UsageError(f"node {nid} is already unlocked")
    if nid not in _frontier(tree, state["unlocked"]):
        raise UsageError(f"node {nid} is not adjacent to an unlocked node")
    _unlock(state, nid)
    state["meta_used"]["lifeline"] = _used(state, "lifeline") + 1


def use_recall(state, tree):
    """Undo the most recent unlock (lock it and refund core + points)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "recall") >= meta["recall"]:
        raise UsageError("no recall charge left")
    hist = state.get("history", [])
    if not hist:
        raise UsageError("no unlocks to undo")
    nid = hist.pop()
    if nid not in state["unlocked"]:
        raise UsageError(f"node {nid} is already locked")
    refund = _node_cost_for(state, tree, nid)
    refund_core = _core_cost_for(state, tree, nid)
    state["unlocked"].remove(nid)
    state["points"] += refund
    state["cores"] += refund_core
    state["meta_used"]["recall"] = _used(state, "recall") + 1
    return nid


def use_duplicate(state, tree):
    """Unlock a random locked node sharing a source with an unlocked node
    (Generic sources excluded), capped by rarity (single use)."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "duplicate") >= meta["duplicate"]:
        raise UsageError("no duplicate charge left")
    sources = {tree["by_id"][u]["source"] for u in state["unlocked"]}
    sources.discard("Generic")
    sources.discard("")
    if not sources:
        raise UsageError("you own no nodes with a real source to duplicate")
    src = random.choice(sorted(sources))
    eligible = [nd for nd in tree["nodes"]
                if nd["id"] != ROOT_ID and nd["id"] not in state["unlocked"]
                and nd["source"] == src
                and nd["rarity"] <= meta["duplicate_max"]]
    if not eligible:
        raise UsageError(f"no locked {src} node with rarity <= "
                         f"{meta['duplicate_max']} to duplicate")
    target = random.choice(eligible)
    _unlock(state, target["id"])
    state["meta_used"]["duplicate"] = _used(state, "duplicate") + 1
    return target


def _shuffle_candidate(tree, state, a):
    """Pick the node to swap with a: a not-visible locked node of similar
    rarity (±0.2), else a random visible locked node."""
    meta = derive_meta(tree, state["unlocked"])
    vis = set(visible(tree, state["unlocked"], meta))
    if a not in vis:
        raise UsageError(f"node {a} is not a visible locked node")
    ra = tree["by_id"][a]["rarity"]
    cands = [nd for nd in tree["nodes"]
             if nd["id"] not in state["unlocked"] and nd["id"] not in vis
             and abs(nd["rarity"] - ra) <= 0.2]
    if not cands:
        cands = [nd for nd in tree["nodes"]
                 if nd["id"] in vis and nd["id"] != a]
    if not cands:
        raise UsageError(f"no node to shuffle with node {a}")
    return random.choice(cands)["id"]


def use_shuffle(state, tree, a):
    """Single use. Swap node a (a visible locked node) with a random
    not-visible locked node of similar rarity."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "shuffle") >= meta["shuffle"]:
        raise UsageError("no shuffle charge left")
    if a in state["unlocked"]:
        raise UsageError(f"node {a} is already unlocked")
    b = _shuffle_candidate(tree, state, a)
    _swap_nodes(tree, a, b)
    state["swaps"].append([a, b])
    state["meta_used"]["shuffle"] = _used(state, "shuffle") + 1
    return b


def use_swap(state, tree, a, b):
    """Single use. Swap two visible locked nodes of your choice."""
    meta = derive_meta(tree, state["unlocked"])
    if _used(state, "swap") >= meta["swap"]:
        raise UsageError("no swap charge left")
    if a == b:
        raise UsageError("swap needs two different nodes")
    if a in state["unlocked"] or b in state["unlocked"]:
        raise UsageError("both nodes must be locked")
    vis = set(visible(tree, state["unlocked"], meta))
    if a not in vis or b not in vis:
        raise UsageError("both nodes must be visible")
    _swap_nodes(tree, a, b)
    state["swaps"].append([a, b])
    state["meta_used"]["swap"] = _used(state, "swap") + 1


def use_reshuffle(state, tree, a):
    """Unlimited Shuffle that costs a quarter of the chosen node's cost."""
    meta = derive_meta(tree, state["unlocked"])
    if meta["reshuffle"] <= 0:
        raise UsageError("you have no reshuffle ability")
    if a in state["unlocked"]:
        raise UsageError(f"node {a} is already unlocked")
    cost = node_cost(tree, a) / 4.0
    if state["points"] < cost:
        raise UsageError(f"not enough points: need {fmt(cost)}, "
                         f"have {fmt(state['points'])}")
    b = _shuffle_candidate(tree, state, a)
    state["points"] -= cost
    _swap_nodes(tree, a, b)
    state["swaps"].append([a, b])
    return cost, b


def trace(tree, state, field, x, n=TRACE_DEFAULT_N):
    """Trace routes to the n closest locked nodes whose name/description/
    source contains x. Returns a list of (dist, node, [path ids]).
    Name traces are free while a trace-name node is unlocked, otherwise
    each one spends a trace-name-use charge (e.g. Scent Hound)."""
    meta = derive_meta(tree, state["unlocked"])
    cap = {"name": "trace_name", "desc": "trace_desc",
           "source": "compass"}[field]
    if not meta[cap]:
        if field == "name" and \
                _used(state, "trace_name_use") < meta["trace_name_use"]:
            state["meta_used"]["trace_name_use"] = \
                _used(state, "trace_name_use") + 1
        else:
            verb = {"name": "trace-by-name", "desc": "trace-by-desc",
                    "source": "compass"}[field]
            raise UsageError(f"you lack the {verb} ability")
    x = x.lower()
    dist, prev = hop_distances(tree, state["unlocked"])
    matches = []
    for nd in tree["nodes"]:
        if nd["id"] == ROOT_ID or nd["id"] in state["unlocked"]:
            continue
        if field == "name":
            hay = nd["name"].lower()
        elif field == "desc":
            hay = nd["description"].lower()
        else:
            hay = nd["source"].lower()
        if x in hay and nd["id"] in dist:
            near = min((distance3(tree["by_id"][u], nd)
                        for u in state["unlocked"]), default=math.inf)
            matches.append((dist[nd["id"]], near, nd))
    matches.sort(key=lambda m: (m[0], m[1], m[2]["id"]))
    out = []
    for d, _near, nd in matches[:n]:
        path = [nd["id"]]
        cur = nd["id"]
        while cur in prev:
            cur = prev[cur]
            path.append(cur)
        path.reverse()
        out.append((d, nd, path))
    return out


# --- CLI -------------------------------------------------------------------

def _visible_lines(tree, unlocked, meta=None):
    rows = []
    for nid in visible(tree, unlocked, meta):
        nd = tree["by_id"][nid]
        rows.append((nid, nd["name"], nd["rarity"], nd["file"],
                     nd["source"], node_cost(tree, nid)))
    return rows


def _prompt_choice(cands):
    for i, (d, nd) in enumerate(cands):
        print(f"  [{i}] {nd['id']}. {nd['name']} ({nd['file']}, "
              f"rarity {nd['rarity']}, cost {fmt(10.0 ** nd['rarity'])})")
    if sys.stdin.isatty():
        try:
            return int(input("choose: ").strip())
        except (EOFError, ValueError):
            raise UsageError("no valid choice given")
    raise UsageError("--pick is required when not interactive")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        return sub.add_parser(name, help=kw.pop("help", None), **kw)

    p = add("init", help="create a fresh player state")
    p.add_argument("state")
    p.add_argument("--tree", required=True)

    p = add("award", help="award one or more tickets")
    p.add_argument("state")
    p.add_argument("tickets", nargs="+")
    p.add_argument("--gamble", action="store_true",
                   help="roll a d20 for each ticket (1 gamble charge each)")

    p = add("state", help="show wallet, cores, inventory and unlocked nodes")
    p.add_argument("state")

    p = add("visible", help="list unlockable nodes and costs")
    p.add_argument("state")

    p = add("unlock", help="normal unlock of a visible node")
    p.add_argument("state")
    p.add_argument("node", type=int)

    p = add("skip", help="unlock with a skip ticket")
    p.add_argument("state")
    p.add_argument("node", type=int)
    p.add_argument("--n", type=int, help="skip distance (default: smallest sufficient)")

    p = add("jump", help="jump / choice-N jump (category optional for choice tickets)")
    p.add_argument("state")
    p.add_argument("category", nargs="?", default=None, choices=CATEGORIES,
                   help="target category (omit for a category-less choice ticket)")
    p.add_argument("--from", dest="from_id", type=int, required=True)
    p.add_argument("--pick", type=int, help="0-based candidate (required for choice tickets)")

    p = add("hop", help="unlock with a hop ticket")
    p.add_argument("state")
    p.add_argument("node", type=int)

    p = add("use", help="use a meta ability")
    p.add_argument("state")
    p.add_argument("action", choices=["lockrefund", "addlink", "reveal", "gacha",
                                      "lifeline", "recall", "duplicate",
                                      "shuffle", "swap", "reshuffle",
                                      "shake", "chaosquake"])
    p.add_argument("args", nargs="*", type=int, help="node ids")

    p = add("trace", help="trace routes to closest matching locked nodes")
    p.add_argument("state")
    p.add_argument("--name", help="match a substring in node names")
    p.add_argument("--desc", help="match a substring in descriptions")
    p.add_argument("--source", help="match a source label (needs Compass)")
    p.add_argument("--n", type=int, default=TRACE_DEFAULT_N,
                   help="number of matches to trace (default 3)")
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.cmd == "init":
        os.makedirs(os.path.dirname(os.path.abspath(args.state)), exist_ok=True)
        save_state(new_state(args.tree), args.state)
        print(f"created {args.state} (root free, unlocked)")
        return 0

    state = load_state(args.state)
    tree = load_tree(state["tree"])
    apply_swaps(tree, state)
    apply_added_links(tree, state)
    apply_entry_swaps(tree, state)
    meta = view_state(tree, state)

    if args.cmd == "award":
        bonus_pct = meta["ticket_bonus"]
        echo_left = meta["echo"] - state.get("echo_used", 0)
        if args.gamble:
            need, have = len(args.tickets), meta["gamble"] - _used(state, "gamble")
            if have < need:
                raise UsageError(
                    f"need {need} gamble charges, have {have}")
        for spec in args.tickets:
            use_echo = echo_left > 0
            tier, kind, params, pts = award(
                state, spec, bonus_pct,
                echo=use_echo, gamble=args.gamble, tree=tree)
            if use_echo:
                echo_left -= 1
            if params.get("destroyed"):
                cores_n = 1 if params.get("twin") else 0
            else:
                cores_n = 1 + (1 if params.get("twin") else 0)
            extra = f" [{kind}]" if kind != "plain" else ""
            echo_mark = " (echo!)" if use_echo else ""
            note = gamble_note(params)
            wild_mark = ""
            if params.get("wild"):
                d1, d2 = params["wild"]
                wild_mark = f" (wild {d1}+{d2}" + \
                    (" double!" if d1 == d2 else "") + ")"
            coupon_mark = ""
            if kind == "coupon" and not params.get("destroyed"):
                coupon_mark = f" (coupon worth {fmt(params['value'])} pts)"
            print(f"awarded {tier or 'tierless'}{extra}: +{cores_n} core(s), "
                  f"+{fmt(pts)} pts{echo_mark}{wild_mark}{coupon_mark}"
                  + (f" [{note}]" if note else ""))
    elif args.cmd == "state":
        print(f"tree: {tree['path']}")
        print(f"points: {fmt(state['points'])}   cores: {state['cores']}")
        print(f"unlocked: {len(state['unlocked'])} node(s)")
        meta_bits = [f"sight+{meta['sight']}"] if meta["sight"] else []
        if meta["see_far"]:
            meta_bits.append("see-far")
        if meta["trace_name"]:
            meta_bits.append("trace-name")
        if meta["trace_desc"]:
            meta_bits.append("trace-desc")
        if meta["reveal_full"]:
            meta_bits.append("reveal-full")
        if meta["ticket_bonus"]:
            meta_bits.append(f"ticket+{meta['ticket_bonus']}%")
        for key, label in (("lock_refund", "lock-refund"),
                           ("add_link", "add-link"), ("gacha", "gacha"),
                           ("lifeline", "lifeline"), ("recall", "recall"),
                            ("duplicate", "duplicate"), ("shuffle", "shuffle"),
                            ("swap", "swap"), ("shake", "shake"),
                            ("chaosquake", "chaosquake"),
                            ("gamble", "gamble"),
                            ("trace_name_use", "trace-name-use")):
            if meta[key]:
                left = meta[key] - state["meta_used"].get(key, 0)
                meta_bits.append(f"{label}x{left}")
        if meta["gamble_reroll"]:
            meta_bits.append(f"reroll<={meta['gamble_reroll']}")
        if meta["gamble_twice"]:
            meta_bits.append("second-roll")
        if meta["reshuffle"]:
            meta_bits.append("reshuffle")
        if meta["survey"]:
            meta_bits.append(f"survey+{meta['survey']}")
        if meta["compass"]:
            meta_bits.append("compass")
        if meta["root_pact"]:
            meta_bits.append("root-pact")
        if meta["cat_sight"]:
            meta_bits.append("cat-sight:" + ",".join(
                f"{c}+{d}" for c, d in sorted(meta["cat_sight"].items())))
        echo_left = meta["echo"] - state.get("echo_used", 0)
        if echo_left > 0:
            meta_bits.append(f"echo x{echo_left}")
        if meta["reveal_temp"] and state["reveal_temp_until"] <= time.time():
            meta_bits.append("reveal(10s)")
        print("meta: " + (", ".join(meta_bits) if meta_bits else "none"))
        print("inventory:")
        for i, t in enumerate(state["inventory"]):
            print(f"  [{i}] {t['tier']} {t['kind']} "
                  f"({', '.join(f'{k}={v}' for k, v in t.items() if k not in ('kind', 'tier'))})")
        print("visible:")
        for nid, name, r, f, src, cost in _visible_lines(tree, state["unlocked"], meta):
            print(f"  {nid}. {name} [{f} | {src}] rarity {r} cost {fmt(cost)}")
        for i, name in survey_names(tree, state["unlocked"], meta):
            print(f"  surveyed: {i}. {name}")
    elif args.cmd == "visible":
        for nid, name, r, f, src, cost in _visible_lines(tree, state["unlocked"], meta):
            print(f"{nid}. {name} [{f} | {src}] rarity {r} cost {fmt(cost)}")
        for i, name in survey_names(tree, state["unlocked"], meta):
            print(f"surveyed: {i}. {name}")
    elif args.cmd == "unlock":
        unlock(state, tree, args.node)
        print(f"unlocked {args.node}. {tree['by_id'][args.node]['name']}")
    elif args.cmd == "skip":
        unlock_skip(state, tree, args.node, args.n)
        print(f"unlocked {args.node}. {tree['by_id'][args.node]['name']} (skip)")
    elif args.cmd == "jump":
        if args.pick is None:
            tickets = [t for t in state["inventory"]
                       if t["kind"] in ("jump", "choice")
                       and (t.get("category") is None
                            or t.get("category") == args.category)]
            if not tickets:
                raise UsageError("no jump/choice ticket in inventory")
            if tickets[0]["kind"] == "choice":
                eff = args.category or tickets[0].get("category")
                cands = _jump_candidates(tree, eff, args.from_id,
                                         state["unlocked"])[:tickets[0]["n"]]
                args.pick = _prompt_choice(cands)
            else:
                args.pick = 0
        target = unlock_jump(state, tree, args.category, args.from_id, args.pick)
        print(f"jumped to {tree['by_id'][target]['file']} node "
              f"{target}. {tree['by_id'][target]['name']}")
    elif args.cmd == "hop":
        unlock_hop(state, tree, args.node)
        print(f"unlocked {args.node}. {tree['by_id'][args.node]['name']} (hop)")
    elif args.cmd == "use":
        if args.action == "lockrefund":
            if len(args.args) != 1:
                raise UsageError("use lockrefund NODE")
            refund_core = _core_cost_for(state, tree, args.args[0])
            refund = use_lock_refund(state, tree, args.args[0])
            print(f"locked {args.args[0]} and refunded {fmt(refund)} pts "
                  f"+ {refund_core} core(s)")
        elif args.action == "addlink":
            if len(args.args) != 2:
                raise UsageError("use addlink A B")
            d = use_add_link(state, tree, args.args[0], args.args[1])
            print(f"linked {args.args[0]} -- {args.args[1]} (span {fmt(d)})")
        elif args.action == "reveal":
            until = use_reveal(state, tree)
            print(f"full tree revealed for 10s (until {until:.0f})")
        elif args.action == "gacha":
            target = use_gacha(state, tree)
            print(f"rolled {target['id']}. {target['name']} "
                  f"({target['file']}, rarity {target['rarity']})")
        elif args.action == "lifeline":
            if len(args.args) != 1:
                raise UsageError("use lifeline NODE")
            use_lifeline(state, tree, args.args[0])
            print(f"free unlocked {args.args[0]}. "
                  f"{tree['by_id'][args.args[0]]['name']}")
        elif args.action == "recall":
            nid = use_recall(state, tree)
            print(f"locked {nid}. {tree['by_id'][nid]['name']} again "
                  f"and refunded its core + points")
        elif args.action == "duplicate":
            target = use_duplicate(state, tree)
            print(f"duplicated {target['id']}. {target['name']} "
                  f"({target['source']}, rarity {target['rarity']})")
        elif args.action == "shuffle":
            if len(args.args) != 1:
                raise UsageError("use shuffle NODE")
            b = use_shuffle(state, tree, args.args[0])
            print(f"shuffled {args.args[0]} with {b}. "
                  f"{tree['by_id'][b]['name']}")
        elif args.action == "swap":
            if len(args.args) != 2:
                raise UsageError("use swap A B")
            use_swap(state, tree, args.args[0], args.args[1])
            print(f"swapped {args.args[0]} -- {args.args[1]}")
        elif args.action == "reshuffle":
            if len(args.args) != 1:
                raise UsageError("use reshuffle NODE")
            cost, b = use_reshuffle(state, tree, args.args[0])
            print(f"reshuffled {args.args[0]} with {b} "
                  f"for {fmt(cost)} pts")
        elif args.action == "shake":
            n = use_shake(state, tree)
            print(f"shook the tree: {n} locked nodes reassigned")
        elif args.action == "chaosquake":
            n = use_chaosquake(state, tree)
            print(f"chaosquake: {n} nodes reassigned")
    elif args.cmd == "trace":
        if args.source is None:
            if args.name is None and args.desc is None:
                raise UsageError("trace needs --name X, --desc X or --source X")
            field = "name" if args.name is not None else "desc"
            x = args.name if args.name is not None else args.desc
        else:
            if args.name is not None or args.desc is not None:
                raise UsageError("give only one of --name/--desc/--source")
            field, x = "source", args.source
        for d, nd, path in trace(tree, state, field, x, args.n):
            route = " -> ".join(
                f"{p}.{tree['by_id'][p]['name']}" for p in path)
            print(f"[{d} hop] {nd['id']}. {nd['name']} "
                  f"(rarity {nd['rarity']}) :: {route}")

    save_state(state, args.state)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
