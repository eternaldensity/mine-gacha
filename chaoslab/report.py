"""Regenerate the reports that can be derived offline from parsed data.

Parse owns the corpus tables (``entries.csv``, ``summary.md``,
``parse_report.md``); this module reruns it, then adds the mod-fit and curse
summaries. The Modrinth matrix is deliberately not touched: it needs cached
API responses and would otherwise be rewritten with offline errors.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import curses as curses_mod
from . import decisions as decisions_mod
from . import fit as fit_mod
from .fetch import FetchError
from .parse import run as parse_run

CURSE_TIERS = ("Minor", "Medium", "Major", "Severe", "Ultimate")


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

    return [str(path) for path in written]
