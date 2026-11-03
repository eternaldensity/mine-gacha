#!/usr/bin/env python3
"""Fetch the official Chaos Gacha tag taxonomy into tools/tagdata/.

The original site (chaosgacha.com, by BronzDeck) publishes per-category tag
dictionaries (`<category>_tags.txt`) and per-entry tags inline in
`gachalist.txt`. This script re-downloads both and rewrites the vendored
snapshot read by tools/import_official_tags.py. Needs network access; the
snapshot is committed so normal use is offline.

    python3 tools/fetch_official_tags.py
"""
import json
import os
import re
import sys
import urllib.request

BASE = "https://www.chaosgacha.com"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tagdata")

DICT_FILES = {"ability": "abilities_tags", "item": "items_tags",
              "skill": "skills_tags", "trait": "traits_tags",
              "familiar": "familiars_tags"}
CATMAP = {"Ability": "ability", "Item": "item", "Skill": "skill",
          "Trait": "trait", "Familiar": "familiar"}
HDR = re.compile(r"^(Ability|Item|Skill|Trait|Familiar),\s*(.*?),(\d+(?:\.\d+)?)\s*$")
# Tags used on entries but absent from the dictionaries; folded in by hand so
# the whitelist parse does not have to guess.
EXTRA = {"Large Size", "Mechanical", "Machine", "Passive", "Anti Draconic",
         "Instance Familiar"}


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def norm_key(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def fetch_dicts():
    dicts = {}
    for cat, name in DICT_FILES.items():
        out = []
        for line in get(f"{BASE}/{name}.txt").splitlines():
            m = re.match(r"^\|([^|]+)\|\s*-?\s*(.*)$", line.strip())
            if m:
                out.append({"name": m.group(1).strip(), "desc": m.group(2).strip()})
        dicts[cat] = out
    return dicts


def fetch_entries(dicts):
    known = {cat: {norm_key(t["name"]) for t in v} for cat, v in dicts.items()}
    rows = []
    cur, body = None, []

    def flush():
        if cur is None:
            return
        text = " ".join(x.strip() for x in body if x.strip())
        tags = []
        m = re.match(r"^\|((?:[^|]*\|)+)", text)
        if m:
            seen = set()
            for slot in (s.strip() for s in m.group(1).split("|") if s.strip()):
                if norm_key(slot) in known[cur["cat"]] or slot in EXTRA:
                    if slot not in seen:
                        seen.add(slot)
                        tags.append(slot)
        rows.append([cur["cat"], cur["name"], tags])

    for line in get(f"{BASE}/gachalist.txt").splitlines():
        m = HDR.match(line)
        if m and not line.startswith("|"):
            flush()
            cur = {"cat": CATMAP[m.group(1)], "name": m.group(2).strip()}
            body = []
        else:
            body.append(line)
    flush()
    merged = {}
    for cat, name, tags in rows:
        k = (cat, name)
        if k in merged:
            merged[k][2] = sorted(set(merged[k][2]) | set(tags))
        else:
            merged[k] = [cat, name, list(tags)]
    return list(merged.values())


def main():
    os.makedirs(OUT, exist_ok=True)
    dicts = fetch_dicts()
    entries = fetch_entries(dicts)
    with open(os.path.join(OUT, "dicts.json"), "w", encoding="utf-8") as fh:
        json.dump(dicts, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "entry_tags.json"), "w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"dict tags: { {k: len(v) for k, v in dicts.items()} }")
    print(f"entries: {len(entries)} "
          f"(tagged: {sum(1 for e in entries if e[2])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
