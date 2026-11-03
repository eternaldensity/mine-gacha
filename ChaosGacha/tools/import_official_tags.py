#!/usr/bin/env python3
"""Import the original site's official tags into the gacha files.

Merges the vendored snapshot in tools/tagdata/ with our curated theme tags:

  * matched entries (same category + name) get the official tags,
  * our existing tags are renamed to the official spelling where the two name
    the same concept (see generate_tree.TAG_ALIASES),
  * where the official taxonomy has no equivalent (eldritch, fae, vampiric,
    beastkin, construct, teleport, healing, blood, ...) our tags stay.

Tags are written as leading `#(Tag:name)` tokens, so everything downstream
(tree generator, web export, desktop app) sees one tag field. Idempotent:
re-running rewrites the same tokens.

    python3 tools/import_official_tags.py --dry-run
    python3 tools/import_official_tags.py --apply
    python3 tools/import_official_tags.py --apply --report   # per-tag counts
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_tree as gt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GACHA_DIR = os.path.join(ROOT, "gachafiles")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tagdata")
TAG_TOKEN_RE = re.compile(r"\((Tags?:[^)]*)\)")

# Corrections to the vendored official tags, applied after the merge above.
# Each is a case where the site's own tagging misses an explicit property of
# the entry (verified against the entry text). Keyed (category, name).
FIXES = {
    ("item", "Dragonslayer Swordspear"): ["anti-dragon"],
    ("item", "Dragon Slayer"): ["anti-dragon"],
    ("ability", "Curse Breaker"): ["anti-curse"],
    ("familiar", "Dark Eater Midir"): ["anti-dark"],
    # draconic/creature-kind omissions the site's taggers left out, per the
    # entry text ("transform into a Hydra", "a Sea Serpent or Hybrid",
    # "winged ... in the form of an imposing golden Phoenix", "general of the
    # Demon King", "fused with a bioengineered parasite")
    ("ability", "Hydra Form"): ["draconic"],
    ("trait", "Sea Serpent"): ["draconic"],
    ("familiar", "Haspid"): ["draconic", "aquatic"],
    ("familiar", "Winged Dragon of Ra"): ["avian"],
    ("familiar", "Hans"): ["infernal"],
    ("familiar", "Alcina Dimitrescu"): ["bio", "parasitic"],
    ("familiar", "Metroid"): ["aquatic"],          # "a floating ... jellyfish"
    # Consistency: the site tags the vampire Alucard "Undead" but not the other
    # undead vampires; traits use Necro for the same idea. Dio also grafts
    # flesh, so he gets Bio.
    ("familiar", "Vlad Dracula"): ["undead"],
    ("familiar", "Dio Brando"): ["bio", "undead"],
    ("familiar", "Shalltear Bloodfallen"): ["undead"],
    ("familiar", "Vlov Arkangel"): ["undead"],
    ("familiar", "Nrvnqsr Chaos"): ["undead"],
}

# Curated tags that duplicate a concept the official taxonomy already names on
# the same entry. When any of the listed official tags is present ours is
# dropped, so filters see the official name only (the user's "replace our
# names with official names where they overlap").
SUBSUME = {
    "undead": {"necro", "undead"},
    "healing": {"recovery", "health-recovery", "healer", "medical"},
    "teleport": {"movement", "teleporter"},
    "blood": {"bio", "biokinetic"},
    "psychic": {"mental", "manipulator", "psychic"},
    "construct": {"golem", "mechanical", "machine"},
}


def norm_key(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def load_official():
    with open(os.path.join(DATA, "entry_tags.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    out = {}
    for cat, name, tags in rows:
        key = (cat, norm_key(name))
        out.setdefault(key, set()).update(tags)
    return out


def iter_files():
    for fname in gt.ALL_FILES:
        path = os.path.join(GACHA_DIR, fname + ".txt")
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        cur = None
        desc_lines = []
        for idx, line in enumerate(lines):
            m = gt.HEADER_RE.match(line)
            if m:
                if cur is not None:
                    yield fname, cur, desc_lines, path, lines
                cur = {"name": m.group(2).strip(), "idx": idx}
                desc_lines = []
            else:
                desc_lines.append((idx, line))
        if cur is not None:
            yield fname, cur, desc_lines, path, lines


def tag_line_index(desc_lines):
    for idx, line in desc_lines:
        if line.strip().startswith("#"):
            return idx, line
    return None, None


def rewrite_line(line, tags):
    m = re.match(r"^(\s*#\s*)(.*)$", line)
    if not m:
        return line
    prefix, rest = m.group(1), m.group(2)
    rest = TAG_TOKEN_RE.sub("", rest).lstrip()
    return prefix + "".join(f"(Tag:{t})" for t in sorted(tags)) + rest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="print per-tag entry counts (after merge)")
    args = ap.parse_args()

    official = load_official()
    edits = defaultdict(list)     # path -> [(line idx, new line)]
    stats = Counter()
    counts = Counter()
    unmatched = []
    unknown = Counter()

    for fname, cur, desc_lines, path, lines in iter_files():
        idx, line = tag_line_index(desc_lines)
        if idx is None:
            continue
        tok_tokens, _ = gt.parse_description(line.strip())
        ours = set(gt.parse_tags(tok_tokens))          # already alias-normalized
        key = (fname, norm_key(cur["name"]))
        off = official.get(key)
        official_norm = set()
        if off is not None:
            stats["matched"] += 1
            for raw in off:
                n = gt.normalize_tag(raw)
                if not n:
                    unknown[raw] += 1
                    continue
                official_norm.add(n)
        else:
            stats["unmatched"] += 1
            if ours:
                stats["unmatched_curated"] += 1
            unmatched.append((fname, cur["name"]))
        union = official_norm | {
            o for o in ours
            if not (SUBSUME.get(o, set()) & official_norm)
        }
        for extra in FIXES.get((fname, cur["name"]), ()):
            union.add(gt.normalize_tag(extra))
        if not union:
            continue
        stats["tagged"] += 1
        counts.update(union)
        new_line = rewrite_line(line, union)
        if new_line != line:
            edits[path].append((idx, new_line))
        if line != new_line:
            stats["changed"] += 1

    print(f"matched to official: {stats['matched']}  "
          f"unmatched: {stats['unmatched']} (of which curated: {stats['unmatched_curated']})")
    print(f"entries tagged: {stats['tagged']}  lines changed: {stats['changed']}")
    print(f"distinct tags: {len(counts)}")
    if unknown:
        print(f"tags dropped by normalizer: {dict(unknown)}")
    if args.report:
        for t, n in counts.most_common():
            print(f"  {t}: {n}")
    if not args.apply:
        print("dry run — pass --apply to rewrite gachafiles/")
        print(f"sample unmatched: {unmatched[:8]}")
        return 0

    for path, pending in edits.items():
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for idx, new_line in pending:
            lines[idx] = new_line
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"wrote {os.path.relpath(path, ROOT)} ({len(pending)} lines)")
    print("done — rerun: python3 tools/export_web_data.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
