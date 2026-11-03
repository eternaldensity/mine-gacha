"""Parse the snapshotted gacha corpus into data/corpus.jsonl and reports/."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .fetch import CATEGORY_FILES, FetchError, load_manifest

TIER_BOUNDS = (
    (1.0, "Trash"),
    (2.0, "Common"),
    (3.0, "Uncommon"),
    (4.0, "Rare"),
    (5.0, "Elite"),
    (6.0, "Epic"),
    (7.0, "Legendary"),
    (8.0, "Mythical"),
    (9.0, "Divine"),
    (float("inf"), "Transcendent"),
)
TIERS = [name for _, name in TIER_BOUNDS]

HEADER_RE = re.compile(r"^(\d+)\.\s*(.+)$")
RARITY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")
TAGS_RE = re.compile(r"\(\s*Tags?\s*:\s*([^)]*)\)", re.IGNORECASE)
MARKER_RE = re.compile(r"\(\s*(Nsfw|Noncon|Character|Tech|Tree|Gacha)\s*\)", re.IGNORECASE)
MARKER_NAMES = ("Nsfw", "Noncon", "Character", "Tech", "Tree", "Gacha")


def tier_of(rarity: float) -> str:
    for bound, name in TIER_BOUNDS:
        if rarity < bound:
            return name
    return "Transcendent"


def split_header(line: str) -> tuple[int, str, float | None, str | None, list[str]]:
    """Return (number, name, rarity, source, flags) for a candidate header line."""
    flags: list[str] = []
    head = HEADER_RE.match(line)
    if not head:
        raise ValueError("not a header")
    number = int(head.group(1))
    rest = head.group(2)
    fields = [f.strip() for f in rest.split(",")]
    name = fields[0]
    rarity: float | None = None
    source: str | None = None
    if len(fields) >= 2 and RARITY_RE.match(fields[1]):
        rarity = float(fields[1])
    else:
        flags.append("missing_rarity")
    if len(fields) >= 3:
        source = ", ".join(fields[2:]).strip() or None
    if len(fields) > 3:
        flags.append("comma_in_header")
    if rarity is not None and not (0.0 <= rarity <= 10.0):
        flags.append("rarity_out_of_range")
    return number, name, rarity, source, flags


def parse_category(text: str, category: str) -> tuple[list[dict], dict]:
    lines = text.splitlines()
    entries: list[dict] = []
    anomalies: list[str] = []
    # Leading lines before the first header are unaccounted prose, not entries.
    first = 0
    while first < len(lines) and not HEADER_RE.match(lines[first]):
        if lines[first].strip():
            anomalies.append(f"{category}:{first + 1}: text before first header ignored")
        first += 1

    index = 0
    blocks: list[tuple[int, int]] = []  # (header_index, next_header_index)
    header_rows: list[tuple[int, int, str, float | None, str | None, list[str]]] = []
    for i in range(first, len(lines)):
        if HEADER_RE.match(lines[i]):
            try:
                number, name, rarity, source, flags = split_header(lines[i])
            except ValueError:
                continue
            header_rows.append((i, number, name, rarity, source, flags))
    for pos, row in enumerate(header_rows):
        end = header_rows[pos + 1][0] if pos + 1 < len(header_rows) else len(lines)
        blocks.append((row[0], end))

    seen: dict[str, int] = {}
    for (start, end), row in zip(blocks, header_rows):
        _, number, name, rarity, source, flags = row
        body = lines[start + 1 : end]
        while body and not body[-1].strip():
            body.pop()
        raw_body = "\n".join(body)
        tags: list[str] = []
        for match in TAGS_RE.finditer(raw_body):
            tags.extend(t.strip() for t in re.split(r"[,;]", match.group(1)) if t.strip())
        markers = sorted({m.group(1).capitalize() for m in MARKER_RE.finditer(raw_body)})
        if markers:
            unexpected = [m for m in markers if m not in MARKER_NAMES]
            if unexpected:
                flags.append("unknown_marker")
        clean_lines = [ln for ln in body if not TAGS_RE.fullmatch(ln.strip())]
        description = "\n".join(clean_lines).strip()
        if not description:
            flags.append("empty_description")
        key = name.strip().lower()
        if key in seen:
            flags.append(f"duplicate_of:{seen[key]}")
        else:
            seen[key] = number
        if rarity is None:
            rarity = 0.0

        excluded = False
        reason = None
        if "Tree" in markers:
            excluded, reason = True, "tree"
        elif "Nsfw" in markers:
            excluded, reason = True, "nsfw"
        elif "Noncon" in markers:
            excluded, reason = True, "noncon"

        entries.append(
            {
                "id": f"{category}-{number:04d}",
                "category": category,
                "number": number,
                "name": name,
                "display_name": f"{number}. {name}",
                "rarity": rarity,
                "tier": tier_of(rarity),
                "source": source,
                "tags": tags,
                "markers": markers,
                "description": description,
                "start_line": start + 1,
                "end_line": start + 1 + len(body),
                "parse_flags": flags,
                "excluded": excluded,
                "exclude_reason": reason,
            }
        )
        index += 1

    # Unaccounted non-blank lines between blocks are reported, not silently kept.
    accounted = set()
    for (start, end) in blocks:
        accounted.update(range(start, end))
    for i, line in enumerate(lines):
        if line.strip() and i not in accounted:
            anomalies.append(f"{category}:{i + 1}: line outside any entry")
    return entries, {"anomalies": anomalies, "headers": len(header_rows)}


def run(root: Path, include_nsfw: bool = False) -> dict:
    manifest = load_manifest(root)
    source_dir = root / "data" / "source"
    all_entries: list[dict] = []
    per_file: dict[str, dict] = {}

    for category in CATEGORY_FILES:
        rel = f"gachafiles/{category}.txt"
        path = source_dir / rel
        if not path.exists():
            raise FetchError(f"snapshot is missing {rel}; rerun `chaoslab fetch --refresh`")
        entries, meta = parse_category(path.read_text(encoding="utf-8"), category)
        per_file[category] = meta
        all_entries.extend(entries)

    if not include_nsfw:
        for entry in all_entries:
            if entry["exclude_reason"] in ("nsfw", "noncon"):
                entry["excluded"] = True

    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = data_dir / "corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as fh:
        for entry in all_entries:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    _write_csv(reports / "entries.csv", all_entries)
    summary = _summary(all_entries, per_file, include_nsfw)
    (reports / "summary.md").write_text(summary, encoding="utf-8")
    (reports / "parse_report.md").write_text(_parse_report(all_entries, per_file), encoding="utf-8")

    return {
        "entries": len(all_entries),
        "included": sum(1 for e in all_entries if not e["excluded"]),
        "excluded": sum(1 for e in all_entries if e["excluded"]),
        "corpus": str(corpus_path),
    }


CSV_FIELDS = (
    "id",
    "category",
    "number",
    "name",
    "tier",
    "rarity",
    "source",
    "tags",
    "markers",
    "description",
    "start_line",
    "end_line",
    "excluded",
    "exclude_reason",
    "parse_flags",
)


def _write_csv(path: Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for entry in entries:
            row = {key: entry.get(key) for key in CSV_FIELDS}
            for key in ("tags", "markers", "parse_flags"):
                row[key] = ";".join(row[key] or [])
            writer.writerow(row)


def _summary(entries: list[dict], per_file: dict, include_nsfw: bool) -> str:
    counts: dict[str, Counter] = defaultdict(Counter)
    for entry in entries:
        if entry["excluded"]:
            continue
        counts[entry["category"]][entry["tier"]] += 1
    tier_order = TIERS
    lines = ["# ChaosGacha corpus summary", "", f"Included entries: {sum(1 for e in entries if not e['excluded'])} of {len(entries)}", "", "## By category and tier", ""]
    lines.append("| category | " + " | ".join(tier_order) + " | total |")
    lines.append("|---" * (len(tier_order) + 2) + "|")
    for category in CATEGORY_FILES:
        row = [str(counts[category][t]) for t in tier_order]
        lines.append(f"| {category} | " + " | ".join(row) + f" | {sum(counts[category].values())} |")

    sources = Counter(e["source"] for e in entries if not e["excluded"] and e["source"])
    tags = Counter(t for e in entries if not e["excluded"] for t in e["tags"])
    lines += ["", "## Top sources", ""]
    for name, n in sources.most_common(25):
        lines.append(f"- {name}: {n}")
    lines += ["", "## Top tags", ""]
    for name, n in tags.most_common(25):
        lines.append(f"- {name}: {n}")
    lines += ["", "## Exclusions", ""]
    reasons = Counter(e["exclude_reason"] for e in entries if e["excluded"])
    for name, n in sorted(reasons.items()):
        lines.append(f"- {name}: {n}")
    if not include_nsfw:
        lines.append("")
        lines.append("NSFW/Noncon entries are excluded unless `--include-nsfw` is passed.")
    return "\n".join(lines) + "\n"


def _parse_report(entries: list[dict], per_file: dict) -> str:
    flagged = [e for e in entries if e["parse_flags"]]
    lines = ["# Parse report", "", f"Entries: {len(entries)}; flagged: {len(flagged)}", ""]
    for category, meta in per_file.items():
        lines.append(f"## {category}")
        lines.append("")
        lines.append(f"- headers: {meta['headers']}")
        lines.append(f"- anomalies: {len(meta['anomalies'])}")
        for note in meta["anomalies"][:20]:
            lines.append(f"  - {note}")
        lines.append("")
    lines.append("## Flagged entries")
    lines.append("")
    for entry in flagged[:200]:
        lines.append(f"- {entry['id']} {entry['name']}: {', '.join(entry['parse_flags'])}")
    return "\n".join(lines) + "\n"
