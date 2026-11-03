#!/usr/bin/env python3
"""Render a fiction pull sequence into a formatted pull list + categorized markdown.

Sequence file format (see fiction/mechadragon-seq.txt): one entry per line,
`<file>:<number>` where file is ability|item|skill|trait|familiar, or
`curse:<label>` for curse-roller curses (labels from web/data/curses.txt,
case-insensitive), with an optional trailing flag such as `(not chosen)` or
`(replaced)`. Blank lines and #-comments are ignored. References are by
file+number (or curse label) so they survive renames; names, tiers and
descriptions resolve live from gachafiles/ and web/data/curses.txt.

Usage:
    python3 tools/pull_sequence.py fiction/mechadragon-seq.txt
    python3 tools/pull_sequence.py SEQ [--list OUT] [--md OUT]

Defaults write <stem>.list.txt and <stem>.md next to the sequence file.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_tree as gt  # noqa: E402

FILES = ["ability", "item", "skill", "trait", "familiar"]
TYPE_SINGULAR = {"ability": "Ability", "item": "Item", "skill": "Skill",
                 "trait": "Trait", "familiar": "Familiar"}
TYPE_PLURAL = {"ability": "Abilities", "item": "Items", "skill": "Skills",
               "trait": "Traits", "familiar": "Familiars"}
# Rarest first (mirrors the Gacha.py rarity bands).
TIERS = ["Transcendent", "Divine", "Mythical", "Legendary", "Epic",
         "Elite", "Rare", "Uncommon", "Common", "Trash"]

SEQ_RE = re.compile(r"^([a-z]+):(.+?)\s*(\([^)]*\))?\s*$")
CURSES_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "web", "data", "curses.txt")


def rarity_tier(r):
    if r < 1.0:
        return "Trash"
    if r < 2.0:
        return "Common"
    if r < 3.0:
        return "Uncommon"
    if r < 4.0:
        return "Rare"
    if r < 5.0:
        return "Elite"
    if r < 6.0:
        return "Epic"
    if r < 7.0:
        return "Legendary"
    if r < 8.0:
        return "Mythical"
    if r < 9.0:
        return "Divine"
    return "Transcendent"


def load_sequence(path, curses):
    picks = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = SEQ_RE.match(line)
            if not m:
                raise SystemExit(
                    f"{path}:{lineno}: bad line {raw.strip()!r} "
                    f"(want file:number or curse:Label)")
            kind, ref, flag = m.group(1), m.group(2), m.group(3) or ""
            if kind in FILES:
                if not ref.isdigit():
                    raise SystemExit(
                        f"{path}:{lineno}: bad number {ref!r}")
                picks.append({"kind": "entry", "key": (kind, int(ref)),
                              "flag": flag, "lineno": lineno})
            elif kind == "curse":
                hit = curses.get(ref.lower())
                if hit is None:
                    raise SystemExit(
                        f"{path}:{lineno}: unknown curse {ref!r}")
                picks.append({"kind": "curse", "key": ("curse", ref.lower()),
                              "flag": flag, "lineno": lineno})
            else:
                raise SystemExit(
                    f"{path}:{lineno}: bad file {kind!r} "
                    f"(want {','.join(FILES)} or curse)")
    return picks


def load_curses():
    """Parse web/data/curses.txt (same shape as the exporter's source)."""
    curses = {}
    cur = None
    with open(CURSES_PATH, encoding="utf-8") as fh:
        for line in fh.read().splitlines():
            s = line.strip()
            if not s:
                cur = None
                continue
            m = re.match(r"^(.*?)\((\d+)\)$", s)
            if m and cur is None:
                cur = {"label": m.group(1).strip(),
                       "sev": int(m.group(2)), "desc": []}
                curses[cur["label"].lower()] = cur
            elif cur is not None:
                cur["desc"].append(s)
    out = {}
    for label, c in curses.items():
        desc = [d for d in c["desc"] if not d.startswith("|Resolve:")]
        res = [d for d in c["desc"] if d.startswith("|Resolve:")]
        out[label] = {"label": c["label"], "sev": c["sev"],
                      "desc": " ".join(desc),
                      "resolve": (res[0].replace("|Resolve:", "").strip(" |")
                                  if res else None)}
    return out


def load_index():
    index = {}
    items = gt.load_entries(FILES, None, None, set(), set(), True, True, True)
    for e in items:
        index[(e["file"], e["number"])] = e
    return index


def render_list(picks, index, curses):
    blocks = []
    for i, p in enumerate(picks, 1):
        if p["kind"] == "curse":
            c = curses[p["key"][1]]
            block = (f"{i}\n[{c['label']}]\n|Severity {c['sev']}|\n"
                     f"{c['desc']}")
            if c["resolve"]:
                block += f"\n|Resolve: {c['resolve']}|"
            blocks.append(block)
            continue
        e = index[p["key"]]
        blocks.append(f"{i}\n[{e['name']}]\n"
                      f"|{rarity_tier(e['rarity'])} "
                      f"{TYPE_SINGULAR[e['file']]}|\n"
                      f"{e['description']}")
    return "\n\n".join(blocks) + "\n"


def render_markdown(picks, index, curses):
    by_type = {f: [] for f in FILES}
    curse_picks = []
    for p in picks:
        if p["kind"] == "curse":
            curse_picks.append(p)
        else:
            by_type[p["key"][0]].append(p)
    out = []
    for f in FILES:
        group = by_type[f]
        if not group:
            continue
        out.append(f"## {TYPE_PLURAL[f]}\n")
        tiers_present = [t for t in TIERS
                         if any(rarity_tier(index[p["key"]]["rarity"]) == t
                                for p in group)]
        for t in tiers_present:
            out.append(f"### {t}\n")
            for p in group:
                e = index[p["key"]]
                if rarity_tier(e["rarity"]) != t:
                    continue
                head = f"#### {e['name']}"
                if p["flag"]:
                    head += f" {p['flag']}"
                out.append(f"{head}\n\n{e['description']}\n\nSource: {e['source']}\n")
    if curse_picks:
        out.append("## Curses\n")
        for p in curse_picks:
            c = curses[p["key"][1]]
            head = f"#### {c['label']}"
            if p["flag"]:
                head += f" {p['flag']}"
            block = f"{head}\n\n|Severity {c['sev']}|\n\n{c['desc']}\n"
            if c["resolve"]:
                block += f"\n|Resolve: {c['resolve']}|\n"
            out.append(block)
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sequence")
    ap.add_argument("--list", dest="list_out", default=None)
    ap.add_argument("--md", dest="md_out", default=None)
    args = ap.parse_args(argv)

    curses = load_curses()
    picks = load_sequence(args.sequence, curses)
    if not picks:
        raise SystemExit("sequence is empty")
    index = load_index()
    for p in picks:
        if p["kind"] == "entry" and p["key"] not in index:
            raise SystemExit(
                f"{args.sequence}:{p['lineno']}: unknown entry "
                f"{p['key'][0]}:{p['key'][1]}")

    stem, _ = os.path.splitext(args.sequence)
    list_out = args.list_out or stem + ".list.txt"
    md_out = args.md_out or stem + ".md"
    with open(list_out, "w", encoding="utf-8") as fh:
        fh.write(render_list(picks, index, curses))
    with open(md_out, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(picks, index, curses))
    print(f"{len(picks)} entries -> {list_out}, {md_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
