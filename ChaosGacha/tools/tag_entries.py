#!/usr/bin/env python3
"""Auto-tag gacha entries with thematic (Tag:...) tokens.

Curated starter taxonomy (free-form; any lowercase tag is valid).
Names follow the original site's taxonomy (tools/tagdata/); the official
importer covers most entries, so this heuristics pass mainly serves new or
fork-only entries:
    draconic, undead, holy, infernal, vampiric, spirit, fae, eldritch,
    fire, water, ice, electric, earth, air, dark, nature, time, blood,
    poison, mental, healing, beastkin, aquatic, avian, insectoid,
    construct, amorphous, teleport, time

Heuristics are conservative (high precision): name matches + positive
description phrases. Mentions in "damage/effective against X" or
"vulnerable/weak to X" contexts alone do NOT tag, since those describe
targets/weaknesses, not what the entry IS.

Usage:
    python3 tools/tag_entries.py --dry-run        # preview matches
    python3 tools/tag_entries.py --apply          # persist (Tag:...) into gachafiles
    python3 tools/tag_entries.py --apply --tags holy,undead
    python3 tools/tag_entries.py --list-tags
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_tree as gt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GACHA_DIR = os.path.join(ROOT, "gachafiles")

# ---------------------------------------------------------------------------
# patterns: name = strong signal; desc = must be positive (what it IS, not
# what it hurts / fears). Negative contexts are stripped before desc matching
# so "damage to holy" etc. never tags on its own.
NEG_CTX = re.compile(
    r"(damage|damages|effective|super effective|strong against|bonus against|"
    r"extra damage|lethal to|punish|vulnerable|vulnerability|weak|weakness|"
    r"resist|resistance|immune|immunity|protect against|ward against|repel|"
    r"banish|purge|exorcis[^ ]* (against|of)?)[^.]*?(holy|unholy|dragon|draconic|"
    r"undead|demon|angel|vampir|ghost|spirit|wraith|fae|fairy|eldritch)",
    re.I)

# Mundane time phrasing ("at the same time", "half the time", ...) is never
# evidence of time powers. Stripped before matching like NEG_CTX, so only
# genuine temporal language can tag.
TIME_MUNDANE = re.compile(
    r"sometimes|at the same time|\bsame time\b|each time|every (single )?time|"
    r"first time|last time|next time|long time|short time|over time|"
    r"at a time|at one time|from time to time|\bon time\b|in time to\b|"
    r"period of time|amount of time|waste of time|spend\w* time|"
    r"free time|leisure time|downtime|half the time|all the time|"
    r"most of the time|at all times|(bad|good|hard|tough|great|difficult) time|"
    r"full[- ]time|part[- ]time|any time|training time|casting time|"
    r"(less|more) time|takes? \w+ time|take \w+ time|saves? (you |them |him |her )?time|"
    r"save time|time limit|time-consum|one more time|real time|nick of time|"
    r"pass the time|matter of time|only time will|limited-time|"
    r"\w+ of the time|with time to spare|given time|of all time|ahead of time|"
    r"o'clock",
    re.I)

# Material-skeleton traits are about bones, not undeath.
SKELETON_EXCL = re.compile(
    r"(mithril skeleton|adamantium skeleton|vibranium skeleton|adamantium bonding|"
    r"your skeleton (is|resembles|is bonded))", re.I)

RULES = {
    "draconic": {
        "name": [
            r"\bdragons?\b", r"draconic", r"dragonic", r"\bwyverns?\b",
            r"\bdrakes?\b", r"\bwyrms?\b", r"\bdragonoid\b",
            r"fafnir", r"midir", r"kalameet", r"shenron", r"rayquaza",
            r"garchomp", r"fatalis", r"velkhana", r"nergigante", r"amatsu",
            r"zinogr?e", r"rathalos", r"bahamut", r"tiamat", r"\bddraig\b",
            r"\balbion\b", r"acnologia", r"dragon slayer", r"dragon form",
            r"dragon scales", r"dragon projection", r"dragon kakuja",
            r"dragon'?s breath",
        ],
        "desc": [
            r"transform into (a |an )?.{0,80}dragon",
            r"take the form of (a |an )?.{0,80}dragon",
            r"you are (a |an )?.{0,40}dragon",
            r"dragonoid", r"dragon form", r"dragon scales",
            r"dragon slayer", r"dragonoid transformation",
            r"summon.{0,60}dragon", r"spawn.{0,40}dragon",
            r"draconic form", r"heavenly dragon",
        ],
        "excl": [r"dragonfly", r"dragon fruit"],
    },
    "undead": {
        "name": [
            r"\bundead\b", r"\bzombie", r"\blich", r"\bwraith",
            r"death knight", r"\bdullahan\b", r"\brevenant\b",
            r"animate undead", r"undead army", r"undead king",
            r"death mage", r"necro", r"grave buster",
        ],
        "desc": [
            r"\breanimate\b", r"raise.{0,40}undead", r"animate.{0,40}undead",
            r"you are (a |an )?.{0,40}undead",
            r"transform into.{0,40}(lich|zombie|death knight|wraith|dullahan)",
            r"true undead", r"lesser undead",
            r"greater undead", r"undead version", r"undead army",
            r"turn.{0,40}inhabitants undead", r"control.{0,20}undead",
            r"boost\w*.{0,20}necroman", r"necromancy abilities",
            r"use the dead as army",
        ],
        "excl": [],
    },
    "holy": {
        "name": [
            r"\bholy\b", r"\bangel", r"\bseraph", r"\barchangel",
            r"exorcis", r"\bsacred\b", r"\bhallow",
            r"\bholy water", r"\bholy sword", r"\bholy spear", r"\bholy light",
            r"\bholy flame", r"\bholy weapon", r"\bholy collider",
        ],
        "desc": [
            r"you are (an? )?(angel|archangel|seraph|principality|dominion|throne)",
            r"holy light", r"holy energy", r"holy fire", r"holy flame",
            r"holy water", r"wield.{0,30}holy", r"conjure.{0,30}holy",
            r"infuse.{0,30}holy", r"affinity for (Holy|holy)",
            r"holy affinity",
            r"your (light|holy)[ -]based abilities",
            r"sacred gear", r"holy sword", r"holy spear", r"holy aura",
            r"holy power", r"heavenly realm",
        ],
        "excl": [r"vulnerability to.{0,40}\bholy\b", r"vulnerable to.{0,40}\bholy\b", r"weak.{0,40}\bholy\b"],
    },
    "infernal": {
        "name": [
            r"\bunholy\b", r"profane", r"\bdemon\b", r"demonic",
            r"\bdevil\b", r"infernal", r"archdemon", r"pit fiend", r"balrog",
        ],
        "desc": [
            r"affinity for Unholy", r"affinity for Infernal",
            r"wield.{0,30}unholy", r"conjure.{0,30}unholy",
            r"you are.{0,30}unholy",
            r"unholy (power|energy|flames?|fire)",
            r"hell ?flames?", r"hell ?fire",
            r"profaned flames?", r"wield hell", r"infernal flames?",
            r"you are (a |an )?.{0,40}demon",
            r"transform into.{0,40}demon", r"summon.{0,40}demon",
            r"wield.*infernal",
            r"you are.*infernal", r"transform.*infernal",
            r"infernal (engine|flames?|fire|power|energy)",
            r"abyssal one",
        ],
        "excl": [r"devil's advocate",
                 r"speak of the devil", r"exorcis", r"anti-evil",
                 r"vaporizes.*infernal", r"sets Infernal.*alight"],
    },
    "vampiric": {
        "name": [
            r"vampir", r"blood suck", r"hemokin", r"dead apostle",
            r"alucard", r"dracula", r"shalltear", r"\bmorb\b", r"morbing",
        ],
        "desc": [
            r"vampirism", r"dead apostle", r"bloodsuck",
            r"you (are|become).{0,40}vampire", r"turn (others|people|humans).{0,30}vampire",
            r"true vampire (?!ablaze)",
        ],
        "excl": [r"sets?.*vampire ablaze", r"damage.*vampire"],
    },
    "spirit": {
        "name": [
            r"\bghost\b", r"spectr", r"\bwraith\b",
            r"\bphantom\b", r"\bhaunt\b", r"ectonurite",
            r"spirit affinity", r"spirit form", r"spirit dragon",
        ],
        "desc": [
            r"you are (a |an )?.{0,30}ghost",
            r"become (a |an )?.{0,30}ghost",
            r"transform into.{0,30}ghost",
            r"summon.{0,30}ghost",
            r"astral (form|projection|walk)",
            r"shift into spirit form",
            r"persist as a spirit",
            r"all things spirits",
            r"spiritual creatures",
        ],
        "excl": [r"spectre authority"],
    },
    "fae": {
        "name": [
            r"\bfae\b", r"\bfairy\b", r"\bfairies\b", r"\bpixie",
            r"\bsidhe\b", r"\bsprite\b", r"blessing of fae",
        ],
        "desc": [
            r"\bfae\b", r"light fair", r"\bpixie", r"fairy (king|queen|court)",
            r"fae('s| do not trick)",
        ],
        "excl": [],
    },
    "eldritch": {
        "name": [
            r"eldritch", r"cthulhu", r"nyarlath", r"shub", r"\byog\b",
            r"ryleh", r"r'lyeh",
        ],
        "desc": [
            r"eldritch constructs", r"invoke ryleh", r"abyssal ones",
            r"shub-?niggurath", r"yog-?sothoth",
        ],
        "excl": [],
    },    "fire": {
        "name": [
            r"\bfire\b", r"pyro", r"\bflames?\b", r"inferno",
            r"\bmagma\b", r"\blava\b", r"fireball", r"fire breath",
            r"fire slayer", r"fireborn", r"pyromaniac",
            r"hellflame", r"hellfire",
        ],
        "desc": [
            r"wield.{0,30}fire", r"pyrokinesis",
            r"hellflames?", r"infernal flames?",
            r"fire breath", r"produce and control .*flames",
            r"control .*flames", r"immune to .*fire", r"fire immunity",
            r"fire absorption", r"fire resistance",
            r"affinity for fire", r"fire affinity",
            r"your fire-based abilities", r"fire-born spirit",
        ],
        "excl": [],
    },
    "water": {
        "name": [
            r"\bwater\b", r"hydro", r"\baqua\b", r"\btide\b",
            r"water slayer", r"water breathing",
        ],
        "desc": [
            r"wield.{0,30}water", r"hydrokinesis", r"control water",
            r"control all water",
            r"water breath", r"breathe underwater", r"water affinity",
            r"affinity for water", r"your water-based abilities",
            r"immune to .*water", r"water resistance",
        ],
        "excl": [r"decreased water affinity", r"reduced water"],
    },
    "ice": {
        "name": [
            r"\bice\b", r"cryo", r"\bfrost\b", r"blizzard",
            r"\bglacier\b", r"ice monarch",
        ],
        "desc": [
            r"wield.{0,30}ice", r"cryokinesis", r"control ice",
            r"freeze", r"flash-freez", r"supercool", r"ice immunity",
            r"cold resistance",
            r"affinity for ice", r"ice affinity",
            r"your ice-based abilities",
        ],
        "excl": [],
    },
    "electric": {
        "name": [
            r"lightning", r"thunder", r"electro", r"\bvolt\b",
            r"thunderbird", r"lightning slayer",
        ],
        "desc": [
            r"wield.{0,30}lightning", r"electrokinesis",
            r"call down lightning", r"lightning breath",
            r"generate.*electricity",
            r"channel.{0,20}electricity",
            r"electricity.{0,20}discharge",
            r"sparks? of electricity", r"lightning blades?",
            r"lightning-based abilities",
            r"immune to .*electric",
        ],
        "excl": [],
    },
    "earth": {
        "name": [
            r"\bearth\b", r"terra", r"geomanc",
            r"\bmud\b", r"earth monarch", r"earthbend",
            r"earthquake", r"conjure rock", r"boulder hurl",
            r"ferrokinesis", r"geokinesis", r"terrakinesis",
        ],
        "desc": [
            r"control (earth|stone|rock|boulder|mud|clay|\bsand\b)",
            r"control.{0,30}(earth|stone|rock|boulder|mud|clay|\bsand\b|sandstorm)",
            r"manipulat.{0,30}(\bearth\b|stone|rock|boulder|mud|clay|\bsand\b)",
            r"creat.{0,30}(\bearth\b|stone|rock|\bsand\b|boulder|mud|clay)",
            r"conjure.{0,30}(rock|\bsand\b|sandstorm|boulder|stone)",
            r"bend.{0,30}(\bearth\b|stone|rock|\bsand\b)",
            r"shap.{0,30}(\bearth\b|stone|rock|\bsand\b)",
            r"(earth|stone|rock|sand) (spikes?|walls?|armor|pillars?|constructs?|golems?|spears?|shaping|manipulation)",
            r"earthquake",
            r"manipulate earth", r"earth affinity",
            r"earth-based abilities",
            r"control metal", r"magnetokinesis",
            r"immune to .*earth", r"earth resistance",
            r"earthen", r"seismic",
            r"living rock", r"made entirely of (sand|rock|stone)",
            r"crystal (spikes?|shower|projectiles|barriers?|walls?|armou?r)",
            r"crystals? to (shoot|impale|launch|fire|shape)",
        ],
        "excl": [r"brimstone", r"cornerstone", r"gemstone", r"touchstone",
                 r"stepping stone", r"stone mask", r"stone age",
                 r"flowing water crushing rock", r"sword in the stone",
                 r"philosopher'?s stone", r"rocket", r"shamrock"],
    },
    "air": {
        "name": [
            r"\bwind\b", r"\baero\b", r"\bgale\b",
            r"tornado", r"hurricane", r"wind slayer",
        ],
        "desc": [
            r"wield.{0,30}wind", r"aeromancy", r"control wind",
            r"wind affinity", r"wind-based abilities",
            r"immune to .*wind",
        ],
        "excl": [],
    },
    "dark": {
        "name": [
            r"\bshadow\b", r"umbra", r"\bdark\b", r"darkness",
            r"shadow slayer",
        ],
        "desc": [
            r"wield.{0,30}shadow", r"shadow manipulation",
            r"turn into.{0,30}shadow", r"merge with.{0,30}shadow",
            r"control darkness", r"shadow affinity",
            r"affinity for (shadow|darkness)",
            r"(shadow|darkness).{0,20}affinity",
            r"immune to .*(shadow|dark|darkness)",
        ],
        "excl": [],
    },
    "nature": {
        "name": [
            r"\bnature\b", r"\bdruid\b", r"\bplant\b", r"\bflora\b",
            r"\bvine\b", r"\bthorns?\b", r"wood release", r"\bforest\b", r"\bgrove\b",
        ],
        "desc": [
            r"control plants", r"chlorokinesis", r"grow plants",
            r"wood release", r"plant affinity", r"nature affinity",
            r"affinity for nature", r"nature-based abilities",
            r"goddess of (nature|harvest)",
        ],
        "excl": [],
    },
    "blood": {
        "name": [
            r"\bblood\b", r"hemo", r"sanguine",
        ],
        "desc": [
            r"hemokinesis", r"blood magic",
            r"consume.*blood", r"blood affinity", r"affinity for blood",
            r"vampirism",
        ],
        "excl": [],
    },
    "poison": {
        "name": [
            r"poison", r"venom", r"\btoxic\b", r"plague",
            r"poison slayer",
        ],
        "desc": [
            r"wield.{0,30}poison", r"poison magic", r"venom",
            r"poison affinity", r"affinity for poison", r"toxic.*breath",
        ],
        "excl": [],
    },
    "mental": {
        "name": [
            r"psychic", r"psion", r"telepath", r"thinker", r"esper",
        ],
        "desc": [
            r"mind control", r"telepathy", r"read minds",
            r"read micro-expressions", r"invade minds", r"psychic power",
            r"seize.{0,20}mind", r"turn .* into .*ally",
        ],
        "excl": [],
    },
    "healing": {
        "name": [
            r"\bheal\b", r"medic", r"doctor", r"cleric", r"remedy",
            r"\bcure\b", r"regen", r"recovery",
        ],
        "desc": [
            r"heal (others|allies|wounds|injuries|targets)",
            r"restore (health|limbs|injuries)", r"cure (all|any|almost|ailments)",
            r"rapid healing", r"healing magic",
            r"cured of all injuries",
        ],
        "excl": [],
    },
    "beastkin": {
        "name": [
            r"beastkin", r"werewolf", r"lycan", r"wolfkin", r"worgen",
            r"kitsune", r"nekomata", r"lunar lycan",
        ],
        "desc": [
            r"you are (a |an )?.{0,40}(beastkin|werewolf|wolfkin|lycan)",
            r"transform into.{0,40}(wolf|beast)",
        ],
        "excl": [],
    },
    "aquatic": {
        "name": [
            r"fishman", r"mermaid", r"kraken", r"leviathan", r"shark",
            r"octopus", r"\bsquid\b",
        ],
        "desc": [
            r"breathe underwater", r"you are (a |an )?.{0,30}(fishman|mermaid|shark)",
            r"summon.{0,30}(kraken|leviathan|tsunami)",
            r"control water",
        ],
        "excl": [r"karate"],
    },
    "avian": {
        "name": [
            r"\bbird\b", r"avian", r"harpy", r"phoenix", r"griffin",
            r"thunderbird", r"aerodactyl",
        ],
        "desc": [
            r"you are (a |an )?.{0,30}bird", r"transform into.{0,30}bird",
            r"bird of healing",
        ],
        "excl": [],
    },
    "insectoid": {
        "name": [
            r"insect", r"spider", r"\bant\b", r"\bbee\b", r"wasp",
            r"\bmoth\b", r"beetle", r"scorpion",
        ],
        "desc": [
            r"transform into.{0,30}insect", r"summon.{0,30}(spider|insect|swarm)",
            r"manifest features like",
        ],
        "excl": [],
    },
    "construct": {
        "name": [
            r"golem", r"automaton", r"homunculus", r"colossus",
        ],
        "desc": [
            r"you are (a |an )?.{0,30}golem", r"summon.{0,30}golem",
            r"iron golem", r"golem core", r"animate.*statue",
        ],
        "excl": [],
    },
    "amorphous": {
        "name": [
            r"\bslime\b", r"\booze\b", r"\bgoo\b",
        ],
        "desc": [
            r"you are.{0,30}slime", r"turn (your body|yourself) into slime",
            r"corrosive slime", r"slime form",
        ],
        "excl": [r"science"],
    },
    "teleport": {
        "name": [
            r"teleport", r"portal", r"\bblink\b", r"\bwarp\b",
            r"\brift\b",
        ],
        "desc": [
            r"teleport (yourself|a nearby|any)", r"open a (portal|gate|skipgate)",
            r"fold space", r"blink.*distance",
        ],
        "excl": [r"gate of babylon"],
    },
    "time": {
        "name": [
            r"\btime\b", r"temporal", r"chron\w*", r"rewind",
            r"time loop", r"time stop", r"time travel", r"time warp",
            r"time walk", r"time accel",
        ],
        "desc": [
            r"temporal", r"rewind", r"rewound", r"rewinding",
            r"time loop", r"time travel", r"time stop",
            r"time manipulat", r"time magic",
            r"chron\w*", r"frozen in time", r"time paradox",
            r"time bubble", r"back in time", r"through time",
            r"sands of time", r"hourglass", r"internal clock",
            r"stops time", r"stop time",
            r"slow the world", r"extra turn",
        ],
        "excl": [r"chronically early", r"o'clock", r"no time stop",
                 r"synchroniz", r"synchro", r"chronic", r"ride on time"],
    },
}


COMPILED = {}
for tag, rule in RULES.items():
    COMPILED[tag] = {
        "name": [re.compile(p, re.I) for p in rule["name"]],
        "desc": [re.compile(p, re.I) for p in rule["desc"]],
        "excl": [re.compile(p, re.I) for p in rule.get("excl", [])],
    }


def strip_neg_ctx(text: str) -> str:
    # Remove "damage to X / vulnerable to X / ..." clauses so they never
    # count as positive evidence. Crude but effective: blank the match.
    return NEG_CTX.sub(" ", text)


def suggest_tags(name: str, desc: str):
    found = []
    clean = TIME_MUNDANE.sub(" ", strip_neg_ctx(desc or ""))
    for tag, pats in COMPILED.items():
        if tag == "undead" and SKELETON_EXCL.search((name or "") + " " + (desc or "")):
            # Skeleton-material traits are not undeath; still allow if the
            # text has explicit undead-creation language.
            if not re.search(r"undead|necromanc|reanimate|raise|lich|wraith|zombie",
                             (name or "") + " " + clean, re.I):
                continue
        hit = False
        for rx in pats["excl"]:
            if rx.search(name or "") or rx.search(desc or ""):
                hit = None
                break
        if hit is None:
            continue
        for rx in pats["name"]:
            if rx.search(name or ""):
                hit = True
                break
        if not hit:
            for rx in pats["desc"]:
                if rx.search(clean):
                    hit = True
                    break
        if hit:
            found.append(tag)
    return sorted(found)


def iter_entries():
    out = []
    for fname in gt.ALL_FILES:
        path = os.path.join(GACHA_DIR, fname + ".txt")
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        cur = None
        desc_lines = []
        start_idx = 0
        for idx, line in enumerate(lines):
            m = gt.HEADER_RE.match(line)
            if m:
                if cur is not None:
                    out.append((fname, cur, desc_lines, start_idx))
                cur = {"num": int(m.group(1)), "name": m.group(2).strip(),
                       "line_idx": idx}
                desc_lines = []
                start_idx = idx + 1
            else:
                desc_lines.append((idx, line))
        if cur is not None:
            out.append((fname, cur, desc_lines, start_idx))
    return out


def existing_tags(desc_text: str):
    toks, _ = gt.parse_description(desc_text)
    return set(gt.parse_tags(toks))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tags", default="",
                    help="comma-separated subset to tag (default: all)")
    ap.add_argument("--list-tags", action="store_true")
    ap.add_argument("--only-untagged", action="store_true",
                    help="skip entries that already carry tags (e.g. from the "
                         "official import), so heuristics only fill the gaps")
    args = ap.parse_args()

    only = {t.strip().lower() for t in args.tags.split(",") if t.strip()} or None
    if only:
        bad = only - set(RULES)
        if bad:
            sys.exit(f"unknown tags: {sorted(bad)} (known: {sorted(RULES)})")

    if args.list_tags:
        for t in sorted(RULES):
            print(t)
        return 0

    # Load raw entries once for desc text.
    counts = {t: 0 for t in RULES}
    pending = []  # (fname, line_idx_to_edit, new_tags_sorted, name)
    for fname, cur, desc_lines, _ in iter_entries():
        full_desc = " ".join(l for _, l in desc_lines if l.strip())
        sugg = suggest_tags(cur["name"], full_desc)
        if only:
            sugg = [t for t in sugg if t in only]
        if not sugg:
            continue
        have = existing_tags(full_desc)
        if args.only_untagged and have:
            continue
        new = sorted(set(sugg) - have)
        if not new:
            continue
        # First non-empty desc line starting with # gets the tokens.
        target = None
        for idx, line in desc_lines:
            if line.strip().startswith("#"):
                target = (idx, line)
                break
        if target is None:
            continue
        for t in new:
            counts[t] += 1
        pending.append((fname, target[0], target[1], sorted(have | set(sugg)), cur["name"]))

    print(f"{len(pending)} entries would gain tags")
    for t in sorted(counts):
        if counts[t]:
            print(f"  {t}: +{counts[t]}")
    if args.dry_run or not args.apply:
        for fname, idx, line, tags, name in pending[:40]:
            print(f"{fname}:{idx + 1} {name} -> {tags}")
        if len(pending) > 40:
            print(f"... and {len(pending) - 40} more (use --apply to write)")
        if not args.apply and not args.dry_run:
            print("pass --apply to write, --dry-run to preview only")
        return 0

    # Apply: group by file.
    from collections import defaultdict
    by_file = defaultdict(list)
    for fname, idx, line, tags, _ in pending:
        # Reconstruct: insert missing tags after '#', preserving the rest.
        have_now = existing_tags(line)
        need = [t for t in tags if t not in have_now]
        if not need:
            continue
        m = re.match(r"^(\s*#\s*)(.*)$", line)
        if not m:
            continue
        prefix, rest = m.group(1), m.group(2)
        inject = "".join(f"(Tag:{t})" for t in sorted(need))
        by_file[fname].append((idx, f"{prefix}{inject}{rest}"))

    for fname, edits in by_file.items():
        path = os.path.join(GACHA_DIR, fname + ".txt")
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for idx, new_line in edits:
            lines[idx] = new_line
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"wrote {path} ({len(edits)} entries tagged)")
    print("done — rerun: python3 tools/export_web_data.py")


if __name__ == "__main__":
    main()
