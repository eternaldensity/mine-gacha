"""Join parsed corpus entries to candidate mod capabilities.

``fit_rules.json`` is a hand-maintained set of judged rules: category,
thematic tag, or keyword matches that propose host mods for a gacha entry.
Output is one row per included corpus entry in ``reports/fit.csv``; entries
no rule matches keep the payload's ``default_fit_type``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .util import read_json, read_jsonl

CSV_FIELDS = (
    "id",
    "category",
    "name",
    "tier",
    "rarity",
    "tags",
    "rule_id",
    "fit_type",
    "confidence",
    "candidate_mods",
    "rationale",
)


def load_rules(path: Path) -> dict:
    path = Path(path)
    payload = read_json(path, None)
    if payload is None:
        raise FileNotFoundError(f"fit rules not found: {path}")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"fit rules at {path} define no rules")
    return payload


def load_entries(root: Path) -> list[dict]:
    path = Path(root) / "data" / "corpus.jsonl"
    rows = [row for row in read_jsonl(path) if not row.get("excluded")]
    if not rows:
        raise FileNotFoundError(f"no parsed corpus at {path}; run `chaoslab parse` first")
    return rows


def _entry_tags(entry: dict) -> set[str]:
    return {str(tag).lower() for tag in entry.get("tags") or []}


def rule_matches(entry: dict, rule: dict) -> bool:
    match = rule.get("match") or {}
    categories = match.get("category")
    if categories and entry.get("category") not in categories:
        return False
    tags_any = match.get("tags_any")
    if tags_any and not (_entry_tags(entry) & {str(tag).lower() for tag in tags_any}):
        return False
    keywords_any = match.get("keywords_any")
    if keywords_any:
        haystack = f"{entry.get('name', '')}\n{entry.get('description', '')}".lower()
        if not any(str(word).lower() in haystack for word in keywords_any):
            return False
    return True


def _confidence(rule: dict) -> float:
    try:
        return float(rule.get("confidence"))
    except (TypeError, ValueError):
        return 0.0


def build_rows(root: Path, rules_path: Path) -> list[dict]:
    root = Path(root)
    payload = load_rules(Path(rules_path))
    default_fit = payload.get("default_fit_type") or "unmapped"
    rows: list[dict] = []
    for entry in load_entries(root):
        best = None
        for rule in payload["rules"]:
            if rule_matches(entry, rule) and (best is None or _confidence(rule) > _confidence(best)):
                best = rule
        row = {
            "id": entry.get("id", ""),
            "category": entry.get("category", ""),
            "name": entry.get("name", ""),
            "tier": entry.get("tier", ""),
            "rarity": entry.get("rarity", ""),
            "tags": ";".join(entry.get("tags") or []),
            "rule_id": "",
            "fit_type": default_fit,
            "confidence": "",
            "candidate_mods": "",
            "rationale": "",
        }
        if best is not None:
            row.update(
                {
                    "rule_id": best.get("id", ""),
                    "fit_type": best.get("fit_type") or default_fit,
                    "confidence": best.get("confidence", ""),
                    "candidate_mods": ";".join(best.get("candidate_mods") or []),
                    "rationale": best.get("rationale", ""),
                }
            )
        rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)
    return path


def run(root: Path, rules_path: Path) -> dict:
    root = Path(root)
    rows = build_rows(root, rules_path)
    path = write_rows(root / "reports" / "fit.csv", rows)
    mapped = sum(1 for row in rows if row["rule_id"])
    return {
        "rows": len(rows),
        "mapped": mapped,
        "unmapped": len(rows) - mapped,
        "csv": str(path),
    }
