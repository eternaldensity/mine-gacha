#!/usr/bin/env python3
"""Find tag combinations with no matching entry, and check whether untagged
entries (or mis-tagged ones) could fill them.

Pairs are only interesting when both tags are legal somewhere in the same
category (the taxonomy is per-category), so structurally impossible pairs are
skipped. For each empty pair the script scans every entry's name+description
for both concepts and reports:

    fill  — an entry already carries both tags (pair not actually empty)
    cand  — an entry mentions both concepts but is missing at least one tag
            (a tagging gap: tag it and the pair gains a member)
    none  — nothing in the data mentions the combination (a content gap)

    python3 tools/find_missing_archetypes.py
    python3 tools/find_missing_archetypes.py --min 20      # only common tags
"""
import argparse
import collections
import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_tree as gt          # noqa: E402
from propose_untagged_tags import NEG_CLAUSE, NEG_STRIP  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tagdata")

# concept -> words that indicate it in an entry's name/description
WORDS = {
    "draconic": r"dragon|drake|wyvern|wyrm|serpent|leviathan|hydra|dragonoid",
    "golem": r"golem|construct|automaton|android|robot|mech\b|statue|elemental",
    "avian": r"bird|hawk|eagle|owl|raven|crow|phoenix|harpy|griffin|roc\b|feather|winged",
    "amorphous": r"slime|ooze|\bgoo\b|blob|gelatinous|amorphous",
    "aquatic": r"fish|shark|kraken|leviathan|octopus|squid|mermaid|fishman|sea serpent|dolphin|whale",
    "plant": r"plant|flower|vine|moss|mushroom|forest|treant|dryad|root|leaf|bloom|flora",
    "undead": r"undead|zombie|lich|skeleton|wraith|ghoul|revenant|corpse|dullahan|mummy",
    "holy": r"holy|sacred|angel|seraph|divine|blessed|sanctif|exorcis",
    "infernal": r"demon|devil|infernal|\bhell\b|fiend|\bimp\b|succubus|unholy|profane",
    "necro": r"necro|death|decay|grave|tomb|reaper|bone",
    "nature": r"nature|plant|flora|vine|forest|moss|bloom",
    "bio": r"flesh|organ|blood|biolog|mutat|marrow|graft",
    "biokinetic": r"flesh|biolog|organ|biomass|gene",
    "regenerator": r"regenerat|heal|mend|recover",
    "flying": r"fly|flying|flight|wing|soar|glide",
    "parasitic": r"parasite|parasit|infect|symbio|host",
    "linked": r"link|bond|pact|contract|soul bond",
    "fighter": r"fighter|brawler|warrior|melee|martial artist|boxer",
    "mental": r"mind|mental|psychic|telepath|psionic|esper",
    "weapon": r"sword|blade|spear|axe|hammer|gun|rifle|bow|weapon|katana|scythe",
    "gun": r"gun|rifle|pistol|shotgun|carbine|revolver|blaster|cannon",
    "time": r"time|temporal|chrono|rewind|haste|stasis",
    "space": r"space|spatial|portal|dimension|teleport|warp|rift|wormhole",
    "light": r"light|radiant|sunlight|laser|beam",
    "dark": r"dark|shadow|void|abyss|umbra|gloom",
    "anti-monster": r"monster slay|slay.{0,12}monster|monster bane|beast slay",
    "anti-dragon": r"dragon slay|dragonslay|slay.{0,12}dragon|wyrm slay",
    "anti-undead": r"undead slay|slay.{0,12}undead|undead bane",
    "anti-holy": r"holy slay|slay.{0,12}holy",
    "anti-infernal": r"demon slay|slay.{0,12}demon|devil slay|demonbane|demon bane",
    "anti-magic": r"anti-?magic|dispel|counterspell|magic.?break",
    "shapeshifter": r"shapeshift|transform|morph|polymorph|doppelganger",
    "magic": r"magic|arcane|spell|mana|rune|enchant|witch|sorcer",
    "divine": r"divine|god|goddess|deity|celestial",
}

# the pairs worth watching (from the earlier gap analysis)
PAIRS = [
    ("draconic", "golem"), ("draconic", "avian"), ("draconic", "amorphous"),
    ("draconic", "aquatic"), ("draconic", "plant"), ("draconic", "undead"),
    ("draconic", "shapeshifter"), ("holy", "undead"), ("holy", "golem"),
    ("holy", "avian"), ("holy", "aquatic"), ("infernal", "golem"),
    ("infernal", "amorphous"), ("nature", "necro"), ("plant", "necro"),
    ("bio", "undead"), ("biokinetic", "necro"), ("regenerator", "undead"),
    ("flying", "aquatic"), ("parasitic", "bio"), ("linked", "parasitic"),
    ("fighter", "mental"), ("time", "space"), ("light", "dark"),
    ("anti-monster", "weapon"), ("anti-dragon", "gun"), ("anti-undead", "undead"),
    ("anti-holy", "infernal"), ("anti-infernal", "infernal"), ("anti-magic", "magic"),
]


def valid_cats(tag):
    with open(os.path.join(DATA, "dicts.json"), encoding="utf-8") as fh:
        dicts = json.load(fh)
    cats = {c for c, items in dicts.items()
            if tag in {gt.normalize_tag(x["name"]) for x in items}}
    return cats or {"ability", "item", "skill", "trait", "familiar"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min", type=int, default=10,
                    help="only report pairs where both tags have >= N entries")
    args = ap.parse_args()

    entries = gt.load_entries(gt.ALL_FILES, None, None, set(), set(), True, True, True)
    count = collections.Counter(t for e in entries for t in e["tags"])
    pair = collections.Counter()
    for e in entries:
        for a, b in itertools.combinations(sorted(set(e["tags"])), 2):
            pair[(a, b)] += 1

    def co(a, b):
        return pair.get(tuple(sorted((a, b))), 0)

    rx = {k: re.compile(v, re.I) for k, v in WORDS.items()}
    print(f"entries {len(entries)} · tagged {sum(1 for e in entries if e['tags'])} · "
          f"untagged {sum(1 for e in entries if not e['tags'])}")
    print(f"reporting pairs where both tags have >= {args.min} entries\n")

    for a, b in PAIRS:
        if count[a] < args.min or count[b] < args.min:
            continue
        n = co(a, b)
        shared = valid_cats(a) & valid_cats(b)
        if not shared and not n:
            continue          # structurally impossible and nobody carries it
        def clean(e):
            raw = e["description"] or ""
            keep = [c for c in re.split(r"[.;]", raw) if not NEG_CLAUSE.search(c)]
            return e["name"] + " " + NEG_STRIP.sub(" ", " . ".join(keep))

        both, one, untagged_hit = [], [], []
        for e in entries:
            text = clean(e)
            ha, hb = a in e["tags"], b in e["tags"]
            wa, wb = bool(rx[a].search(text)), bool(rx[b].search(text))
            if ha and hb:
                both.append(e)
            elif (ha and wb) or (hb and wa):
                one.append(e)           # missing one tag → tagging gap
            elif wa and wb:
                untagged_hit.append(e)  # untagged entry mentioning both
        n = co(a, b)
        verdict = "filled" if n else ("cand" if (one or untagged_hit) else "none")
        print(f"{a} × {b}: {n} entries  [{verdict}]"
              + (f"  untagged hits: {len(untagged_hit)}" if untagged_hit else ""))
        for e in untagged_hit[:4]:
            print(f"    UNTAGGED {e['file']:8} {e['name'][:28]:28} | {e['description'][:100]}")
        for e in one[:3]:
            print(f"    one-tag  {e['file']:8} {e['name'][:28]:28} tags={e['tags']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
