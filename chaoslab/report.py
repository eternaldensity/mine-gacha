"""Regenerate the reports that can be derived offline from parsed data.

Parse owns the corpus tables (``entries.csv``, ``summary.md``,
``parse_report.md``); this module reruns it, then adds the mod-fit and curse
summaries, the power-score sweep and the custom mod's datapack validation
report. The Modrinth matrix is deliberately not touched: it needs cached API
responses and would otherwise be rewritten with offline errors.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import curses as curses_mod
from . import datapack as datapack_mod
from . import decisions as decisions_mod
from . import fit as fit_mod
from . import simulate as simulate_mod
from .fetch import FetchError
from .parse import run as parse_run

CURSE_TIERS = ("Minor", "Medium", "Major", "Severe", "Ultimate")
ENTRY_CATEGORIES = ("ability", "trait", "skill", "item", "familiar")


def _shipped_entries(root: Path) -> list[dict]:
    """Read the entry registry the mod actually ships, from its datapack tree."""
    base = root / "mod" / "datapack" / "data" / "gacha" / "gacha" / "entry"
    rows = []
    if not base.is_dir():
        return rows
    for path in sorted(base.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rarity = payload.get("rarity")
        if not isinstance(rarity, (int, float)):
            continue
        rows.append(
            {
                "id": "gacha:" + path.relative_to(base).with_suffix("").as_posix(),
                "kind": str(payload.get("kind") or ""),
                "rarity": float(rarity),
                "duplicate": payload.get("duplicate") or "default",
            }
        )
    return rows


def _preset_coverage(entries: list[dict], category: str, minimum: float, average: float, maximum: float, flat: bool) -> float:
    """Probability that a category draw finds an entry, including retries.

    ``sampleRarity`` walks the 0.1 grid with weight ``1 / exponent^|avg - x|``
    and returns ``x + 0.1``; a target resolves when an entry is within the
    preset's entry window. ``RollEngine.draw`` takes 200 independent rarity
    targets, so the per-target share is raised to that many attempts. This is
    the engine's actual chance, not a single-target estimate.
    """
    rarities = sorted(entry["rarity"] for entry in entries if entry["kind"] == category)
    if not rarities:
        return 0.0
    exponent = 1 if flat else 4
    window = 1.0 if flat else 0.2
    total = 0.0
    hit = 0.0
    x = float(minimum)
    while x < float(maximum):
        target = x + 0.1
        weight = 1.0 / (exponent ** abs(average - x))
        total += weight
        if any(abs(rarity - target) <= window for rarity in rarities):
            hit += weight
        x += 0.1
    per_target = hit / total if total else 0.0
    return 1.0 - (1.0 - per_target) ** 200


def _random_coverage(entries: list[dict], minimum: float, average: float, maximum: float, flat: bool) -> float:
    """Random tickets pick a category uniformly and retry up to 10 times."""
    per_attempt = sum(
        _preset_coverage(entries, category, minimum, average, maximum, flat)
        for category in ENTRY_CATEGORIES
    ) / len(ENTRY_CATEGORIES)
    return 1.0 - (1.0 - per_attempt) ** 10


def _ticket_tables(root: Path) -> list[dict]:
    base = root / "mod" / "datapack" / "data" / "gacha" / "loot_modifiers"
    rows = []
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("add_ticket_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "file": path.name,
                "tables": len(payload.get("tables") or []),
                "chance": float(payload.get("chance", 1.0)),
            }
        )
    return rows


def _curse_rows(root: Path) -> list[dict]:
    base = root / "mod" / "datapack" / "data" / "gacha" / "gacha" / "curse"
    rows = []
    if not base.is_dir():
        return rows
    for path in sorted(base.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "id": "gacha:" + path.relative_to(base).with_suffix("").as_posix(),
                "severity": payload.get("severity"),
                "hook": (payload.get("hook") or {}).get("type"),
            }
        )
    return rows


def _curse_tier(value) -> str:
    if isinstance(value, int):
        return curses_mod.tier_of(value)
    return str(value)


def _measurements(root: Path) -> str:
    entries = _shipped_entries(root)
    tables = _ticket_tables(root)
    curses = _curse_rows(root)
    by_category = Counter(entry["kind"] for entry in entries)
    rarities = [entry["rarity"] for entry in entries]

    lines = [
        "# Pack measurements",
        "",
        "Generated by `chaoslab report` from the shipped content alone, with no",
        "network access. This is a coverage measurement of what the current mod",
        "build can actually resolve, not a playtest. A live session may differ.",
        "",
        f"Shipped entries: {len(entries)}; shipped curses: {len(curses)}; "
        f"ticket loot modifiers: {len(tables)}.",
        "",
        "## Entry coverage",
        "",
        "| Category | Entries | Rarity range |",
        "| --- | --- | --- |",
    ]
    for category in ENTRY_CATEGORIES:
        subset = sorted(entry["rarity"] for entry in entries if entry["kind"] == category)
        span = f"{subset[0]:.1f} – {subset[-1]:.1f}" if subset else "—"
        lines.append(f"| {category} | {by_category.get(category, 0)} | {span} |")
    if rarities:
        lines += [
            "",
            f"Overall rarity range: {min(rarities):.1f} – {max(rarities):.1f}. "
            "The corpus is imported across all categories (tag-sampled items, "
            "thematic effects/attributes and spawn-egg familiars); the coverage "
            "set remains as extra low/mid-band entries.",
        ]

    lines += [
        "",
        "## Preset coverage",
        "",
        "The engine's chance of finding any entry in each category, including",
        "its 200 rarity attempts per category pick and 10 category picks for",
        "`random` tickets. Values are exact weighted shares over the 0.1 target",
        "grid, not sampled.",
        "",
        "| Preset | Window | " + " | ".join(ENTRY_CATEGORIES) + " | random |",
        "| --- | --- | " + " | ".join("---" for _ in ENTRY_CATEGORIES) + " | --- |",
    ]
    dead = []
    for name, (minimum, average, maximum, flat) in simulate_mod.PRESETS.items():
        cells = [
            _preset_coverage(entries, category, minimum, average, maximum, flat)
            for category in ENTRY_CATEGORIES
        ]
        random = _random_coverage(entries, minimum, average, maximum, flat)
        if random <= 0.0:
            dead.append(name)
        window = f"{minimum:.1f}–{maximum:.1f}" + (" flat" if flat else "")
        lines.append(
            "| "
            + " | ".join(
                [name, window]
                + [f"{cell * 100:.1f}%" for cell in cells]
                + [f"{random * 100:.1f}%"]
            )
            + " |"
        )

    lines += [
        "",
        "## Ticket income",
        "",
        "Each modifier injects one ticket into every matching chest roll at its",
        "declared chance. The shipped band files use a 0.25 first-pass chance, so",
        "one in four listed chests yields a ticket; the D3 sweep assumed",
        "4–30 tickets per day, so the injection rate is the dominant balance knob.",
        "",
        "| Band file | Tables | Chance | Tickets per listed chest |",
        "| --- | --- | --- | --- |",
    ]
    total_tables = 0
    weighted_chance = 0.0
    for row in tables:
        total_tables += row["tables"]
        weighted_chance += row["chance"] * row["tables"]
        lines.append(
            f"| `{row['file']}` | {row['tables']} | {row['chance']:.2f} | {row['chance']:.2f} |"
        )
    chance = weighted_chance / total_tables if total_tables else 0.0
    lines += [
        "",
        f"Listed chest tables: {total_tables}. At 10 / 20 / 30 chests per hour and",
        f"the weighted chance {chance:.2f}, the current injection yields "
        f"{10 * chance:.1f} / {20 * chance:.1f} / {30 * chance:.1f} tickets per hour, "
        f"i.e. {240 * chance:.0f} / {480 * chance:.0f} / {720 * chance:.0f} per day, "
        "versus the sweep's 4 / 12 / 30 per day. A two-hour session at 20 chests/hour "
        "gives about 10 tickets, close to the sweep's regular profile; treat 0.25 as "
        "the first tuning point, not a measured verdict.",
        "",
        "## Curse coverage",
        "",
    ]
    if curses:
        severity = Counter(_curse_tier(row["severity"]) for row in curses)
        hooks = Counter(str(row["hook"]) for row in curses)
        lines += [
            "| Severity | Curses |",
            "| --- | --- |",
        ]
        for tier in CURSE_TIERS:
            lines.append(f"| {tier} | {severity.get(tier, 0)} |")
        lines += [
            "",
            "Hooks: " + ", ".join(f"`{hook}` ×{count}" for hook, count in sorted(hooks.items())) + ".",
        ]
    else:
        lines.append("No curse entries ship yet.")

    lines += ["", "## Dead ends", ""]
    if dead:
        lines.append(
            "Presets with no resolvable entry at all: "
            + ", ".join(f"`{name}`" for name in dead)
            + ". These tickets are kept rather than consumed, but they are a"
            " content gap, not a reward."
        )
    else:
        lines.append("No preset is completely unresolvable.")
    empty_categories = [category for category in ENTRY_CATEGORIES if not by_category.get(category)]
    if empty_categories:
        lines.append(
            "Empty categories: "
            + ", ".join(f"`{category}`" for category in empty_categories)
            + ". Category tickets for these fail; random tickets can still land"
            " in a populated category."
        )
    if not curses:
        lines.append("Curses: no content, so the curse slots cannot fill.")
    return "\n".join(lines) + "\n"


def _fit_summary(rows: list[dict], rules_path: Path) -> str:
    mapped = [row for row in rows if row["rule_id"]]
    unmapped = [row for row in rows if not row["rule_id"]]
    lines = [
        "# Corpus fit summary",
        "",
        f"Rows: {len(rows)}; mapped: {len(mapped)}; unmapped: {len(unmapped)}",
        f"Rules: {rules_path.name}",
        "",
        "## By rule",
        "",
        "| rule | fit type | confidence | rows |",
        "| --- | --- | --- | --- |",
    ]
    seen: dict[str, dict] = {}
    for row in mapped:
        seen.setdefault(row["rule_id"], row)
    for rule_id, count in Counter(row["rule_id"] for row in mapped).most_common():
        sample = seen[rule_id]
        lines.append(f"| {rule_id} | {sample['fit_type']} | {sample['confidence']} | {count} |")

    lines += ["", "## By fit type", ""]
    for fit_type, count in Counter(row["fit_type"] for row in rows).most_common():
        lines.append(f"- {fit_type}: {count}")

    mods = Counter(
        mod for row in mapped for mod in row["candidate_mods"].split(";") if mod
    )
    lines += ["", "## Candidate mods", ""]
    for mod, count in mods.most_common():
        lines.append(f"- {mod}: {count}")

    lines += ["", "## Unmapped entries by category", ""]
    for category, count in Counter(row["category"] for row in unmapped).most_common():
        lines.append(f"- {category}: {count}")

    tags = Counter(tag for row in unmapped for tag in row["tags"].split(";") if tag)
    lines += ["", "## Unmapped top tags", ""]
    for tag, count in tags.most_common(20):
        lines.append(f"- {tag}: {count}")

    lines += ["", "## Unmapped examples", ""]
    for row in unmapped[:25]:
        suffix = f" [{row['tags']}]" if row["tags"] else ""
        lines.append(f"- {row['id']} {row['name']}{suffix}")
    return "\n".join(lines) + "\n"


def _curse_summary(curses: list[dict]) -> str:
    counts = Counter(curse["tier"] for curse in curses)
    mature = sum(1 for curse in curses if curse.get("nsfw"))
    resolvable = sum(1 for curse in curses if curse.get("resolve"))
    lines = [
        "# Curse summary",
        "",
        f"Curses: {len(curses)}; mature entries: {mature}",
        "",
        "## By severity tier",
        "",
    ]
    for tier in CURSE_TIERS:
        lines.append(f"- {tier}: {counts.get(tier, 0)}")
    lines += [
        "",
        f"Resolvable: {resolvable}; one-and-done: {len(curses) - resolvable}",
        "",
    ]
    return "\n".join(lines) + "\n"


def run(root: Path) -> list[str]:
    root = Path(root)
    parsed = parse_run(root)
    written = [
        Path(parsed["corpus"]),
        root / "reports" / "entries.csv",
        root / "reports" / "summary.md",
        root / "reports" / "parse_report.md",
    ]

    rules_path = root / "fit_rules.json"
    rows = fit_mod.build_rows(root, rules_path)
    written.append(fit_mod.write_rows(root / "reports" / "fit.csv", rows))
    fit_summary = root / "reports" / "fit_summary.md"
    fit_summary.write_text(_fit_summary(rows, rules_path), encoding="utf-8")
    written.append(fit_summary)

    try:
        source = curses_mod.find_source(root)
        curses = curses_mod.parse_text(source.read_text(encoding="utf-8"))
    except FetchError:
        curses = []
    if curses:
        curse_summary = root / "reports" / "curse_summary.md"
        curse_summary.write_text(_curse_summary(curses), encoding="utf-8")
        written.append(curse_summary)
        curse_triage = root / "reports" / "curse_triage.md"
        curse_triage.write_text(decisions_mod.curse_triage(curses), encoding="utf-8")
        written.append(curse_triage)

    sweep = root / "reports" / "power_score_sweep.md"
    sweep.write_text(decisions_mod.power_score_sweep(root), encoding="utf-8")
    written.append(sweep)

    measurements = root / "reports" / "pack_measurements.md"
    measurements.write_text(_measurements(root), encoding="utf-8")
    written.append(measurements)

    datapack_result = datapack_mod.run(root)
    written.append(Path(datapack_result["report"]))

    return [str(path) for path in written]
