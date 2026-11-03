#!/usr/bin/env python3
"""Export gacha entries + gacha tier presets for the static web apps.

Reads the gachafiles/*.txt sources (same parsing as the tree generator)
and writes web/data/entries.js, a small JS bundle assigning
window.CHAOS_DATA. Rerun after editing the data files:

    python3 tools/export_web_data.py
"""
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_tree as gt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "data", "entries.js")

# Ticket tiers mirrored from Gacha.py (presets / presetmin / presetavg /
# presetmax) plus the tree-mode point values from tools/chaos_tree_use.py
# and the button colors sampled from the original site's tier PNGs
# (bronze.png … divine.png; transcendent extrapolated darker than divine).
TIERS = [
    {"name": "trash", "min": 0.1, "avg": 0.5, "max": 1.5, "points": 5, "color": "#708090"},
    {"name": "bronze", "min": 0.1, "avg": 1.3, "max": 3.3, "points": 50, "color": "#74573e"},
    {"name": "silver", "min": 0.5, "avg": 2.3, "max": 4.3, "points": 500, "color": "#acb9b8"},
    {"name": "gold", "min": 1.5, "avg": 3.3, "max": 5.3, "points": 5000, "color": "#f6c54c"},
    {"name": "aluminium", "min": 1.0, "avg": 4.0, "max": 6.0, "points": 25000, "color": "#ede6d6"},
    {"name": "platinum", "min": 2.5, "avg": 4.3, "max": 6.3, "points": 50000, "color": "#bcd5eb"},
    {"name": "diamond", "min": 3.5, "avg": 5.3, "max": 7.3, "points": 500000, "color": "#9bf3eb"},
    {"name": "legendary", "min": 4.5, "avg": 6.3, "max": 8.3, "points": 5000000, "color": "#f5993d"},
    {"name": "mythical", "min": 5.5, "avg": 7.3, "max": 9.3, "points": 50000000, "color": "#ff6bae"},
    # Wild has no fixed points: award rolls 2d8, takes the smaller as N for
    # 10^(N+1) points, doubled on doubles. Points here is only a fallback.
    # Rank-wise it sits between mythical and divine, though mythical<->divine
    # rank straight past it (as gold<->platinum skip aluminium).
    {"name": "wild", "min": 1.0, "avg": 5.0, "max": 10.0,
     "points": 0, "color": "#228b22", "flat": True},
    {"name": "divine", "min": 6.5, "avg": 8.3, "max": 10.0, "points": 500000000, "color": "#f61e1e"},
    {"name": "transcendent", "min": 7.5, "avg": 9.3, "max": 10.0,
     "points": 5000000000, "color": "#8f1010"},
]

# Rarity classes mirrored from Gacha.py run_gacha().
CLASSES = [
    {"max": 1.0, "name": "Trash", "color": "#878d96"},
    {"max": 2.0, "name": "Common", "color": "#9c7e5a"},
    {"max": 3.0, "name": "Uncommon", "color": "#aed1d1"},
    {"max": 4.0, "name": "Rare", "color": "#11d939"},
    {"max": 5.0, "name": "Elite", "color": "#1172d9"},
    {"max": 6.0, "name": "Epic", "color": "#6811d9"},
    {"max": 7.0, "name": "Legendary", "color": "#f7d40a"},
    {"max": 8.0, "name": "Mythical", "color": "#fc61ff"},
    {"max": 9.0, "name": "Divine", "color": "#ff8c00"},
    {"max": 99.0, "name": "Transcendent", "color": "#ff0000"},
]

CATEGORIES = ["ability", "item", "skill", "trait", "familiar"]

# Curses with mature/sexual content. curses.txt is verbatim from the original
# site and (unlike the gacha entries) carries no content flags, so this list is
# maintained by hand and drives the web app's "Hide NSFW" filter.
NSFW_CURSES = {
    "Infertile", "Curse of Gray", "1/2", "Perverted Aura",
    "Masochist", "Exhibitionist", "Lust",
}


def flag_map():
    """Map (file, number) -> token set by re-scanning the raw data files.
    Used to preserve NSFW/Tech/Noncon flags that the tree pipeline strips."""
    out = {}
    for path in [os.path.join(gt.GACHA_DIR, f + ".txt") for f in gt.ALL_FILES]:
        file = os.path.basename(path)[:-4]
        cur = None
        desc_lines = []
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        def flush():
            if cur is not None:
                toks, _ = gt.parse_description(
                    " ".join(l.strip() for l in desc_lines if l.strip()))
                out[(file, cur)] = toks
        for line in lines:
            m = gt.HEADER_RE.match(line)
            if m:
                flush()
                cur = int(m.group(1))
                desc_lines = []
            else:
                desc_lines.append(line)
        flush()
    return out


def main():
    export_entries()
    export_curses()
    export_tags()


def export_tags():
    """Mirror the original site's per-category tag dictionaries for the web UI
    (tooltips on tag pills, filter descriptions). Source snapshot:
    tools/tagdata/dicts.json; see tools/tagdata/README.md for provenance."""
    src = os.path.join(ROOT, "tools", "tagdata", "dicts.json")
    with open(src, encoding="utf-8") as fh:
        dicts = json.load(fh)
    payload = {}
    for cat in CATEGORIES:
        items = []
        for t in dicts.get(cat, []):
            tag = gt.normalize_tag(t["name"])
            if not tag:
                continue
            items.append({"name": t["name"], "tag": tag, "desc": t["desc"]})
        payload[cat] = items
    dest = os.path.join(ROOT, "web", "data", "tags.js")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("window.CHAOS_TAGS = ")
        fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        fh.write(";\n")
    n = sum(len(v) for v in payload.values())
    print(f"wrote {dest} ({os.path.getsize(dest)} bytes, {n} tag docs)")


def export_curses():
    # web/data/curses.txt mirrors the original site's curse list verbatim
    # (attribution: BronzDeck, see web README + site footer).
    path = os.path.join(ROOT, "web", "data", "curses.txt")
    out = []
    cur = None
    for line in open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s:
            if cur:
                out.append(cur)
                cur = None
            continue
        m = re.match(r"^(.*?)\((\d+)\)$", s)
        if m and cur is None:
            cur = {"label": m.group(1).strip(), "sev": int(m.group(2)),
                   "desc": []}
        elif cur is not None:
            cur["desc"].append(s)
    if cur:
        out.append(cur)
    compact = []
    for e in out:
        desc = [d for d in e["desc"] if not d.startswith("|Resolve:")]
        res = [d for d in e["desc"] if d.startswith("|Resolve:")]
        item = {
            "label": e["label"], "sev": e["sev"],
            "desc": " ".join(desc),
            "resolve": res[0].replace("|Resolve:", "").strip(" |") if res else None,
        }
        if e["label"] in NSFW_CURSES:
            item["nsfw"] = True
        compact.append(item)
    dest = os.path.join(ROOT, "web", "data", "curses.js")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("window.CHAOS_CURSES = ")
        fh.write(json.dumps(compact, ensure_ascii=False, separators=(",", ":")))
        fh.write(";\n")
    print(f"wrote {dest} ({os.path.getsize(dest)} bytes, "
          f"{len(compact)} curses)")


def export_entries():
    entries = gt.load_entries(gt.ALL_FILES, None, None, set(), set(), True,
                              True, True)
    flags = flag_map()
    # Data version: hash over topology/behaviour-relevant fields (file,
    # number, rarity, source, tag, meta tokens, thematic tags, nsfw/tech/noncon
    # flags). Display text (names, descriptions) is excluded so prose edits
    # don't invalidate trees. Trees record the version they were generated with;
    # a mismatch warns that regeneration may produce a different tree.
    h = hashlib.sha256()
    for e in entries:
        toks = flags.get((e["file"], e["number"]), set())
        h.update(("\x1f".join([e["file"], str(e["number"]), repr(e["rarity"]),
                               e["source"] or "", e["tag"],
                               ",".join(e.get("meta", [])),
                               ",".join(e.get("tags", [])),
                               "nsfw" if "Nsfw" in toks else "",
                               "tech" if "Tech" in toks else "",
                               "noncon" if "Noncon" in toks else ""]) + "\n").encode("utf-8"))
    data_version = h.hexdigest()[:10]
    compact = []
    for e in entries:
        toks = flags.get((e["file"], e["number"]), set())
        item = {"f": e["file"], "n": e["number"], "name": e["name"],
                "r": e["rarity"], "s": e["source"], "t": e["tag"],
                "d": e["description"], "m": e.get("meta", [])}
        if e.get("tags"):
            item["tags"] = e["tags"]
        if "Nsfw" in toks:
            item["nsfw"] = True
        if "Tech" in toks:
            item["tech"] = True
        if "Noncon" in toks:
            item["noncon"] = True
        compact.append(item)
    from collections import Counter
    tag_counts = Counter()
    for e in compact:
        for t in e.get("tags", []):
            tag_counts[t] += 1
    payload = {"generated_at": datetime.datetime.now(datetime.timezone.utc)
               .isoformat(timespec="seconds"),
               "dataVersion": data_version,
               "counts": {c: sum(1 for e in compact if e["f"] == c)
                          for c in CATEGORIES},
               "sources": {
                   c: sorted({e["s"] for e in compact if e["f"] == c})
                   for c in CATEGORIES},
               "tags": sorted(tag_counts),
               "tagCounts": dict(sorted(tag_counts.items())),
               "tiers": TIERS, "classes": CLASSES, "categories": CATEGORIES,
               "entries": compact}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("window.CHAOS_DATA = ")
        fh.write(json.dumps(payload, ensure_ascii=False,
                            separators=(",", ":")))
        fh.write(";\n")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes, "
          f"{len(compact)} entries)")


if __name__ == "__main__":
    main()
