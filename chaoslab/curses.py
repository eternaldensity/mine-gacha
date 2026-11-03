"""Parse the Curse Roulette list into data/curses.jsonl.

The snapshot is preferred when it carries ``web/data/curses.txt``; older
snapshots predate that file, so the ChaosGacha checkout the corpus was
snapshotted from is used as a fallback. Parsing mirrors
``ChaosGacha/tools/export_web_data.py``: a ``Name(severity)`` header starts an
entry, blank lines end it, and ``|Resolve: ...|`` is split out.
"""

from __future__ import annotations

import re
from pathlib import Path

from .fetch import FetchError, load_manifest
from .util import write_jsonl

# d20 roll -> severity tier, from the roulette's own table.
SEVERITY_BOUNDS = (
    (6, "Minor"),
    (13, "Medium"),
    (17, "Major"),
    (19, "Severe"),
    (20, "Ultimate"),
)

# Mature curse labels are not flagged in curses.txt; the upstream exporter
# keeps this list by hand (export_web_data.NSFW_CURSES).
NSFW_CURSES = frozenset(
    {
        "Infertile",
        "Curse of Gray",
        "1/2",
        "Perverted Aura",
        "Masochist",
        "Exhibitionist",
        "Lust",
    }
)

HEADER_RE = re.compile(r"^(.*?)\((\d+)\)$")
RESOLVE_PREFIX = "|Resolve:"


def tier_of(roll: int) -> str:
    """Map a d20 roll to the roulette's severity tier."""
    for upper, name in SEVERITY_BOUNDS:
        if roll <= upper:
            return name
    return "Ultimate"


def find_source(root: Path) -> Path:
    """Return the curse list, preferring the snapshot over a live checkout."""
    root = Path(root)
    for path in (
        root / "data" / "source" / "web" / "data" / "curses.txt",
        root / "ChaosGacha" / "web" / "data" / "curses.txt",
    ):
        if path.is_file():
            return path
    raise FetchError(
        "no curse list found; rerun `chaoslab fetch --refresh` from a ChaosGacha checkout"
    )


def parse_text(text: str) -> list[dict]:
    """Parse curses.txt into rows with description, resolve and NSFW flag."""
    raw: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current is not None:
                raw.append(current)
                current = None
            continue
        header = HEADER_RE.match(stripped)
        if header and current is None:
            current = {
                "label": header.group(1).strip(),
                "severity": int(header.group(2)),
                "lines": [],
            }
        elif current is not None:
            current["lines"].append(stripped)
    if current is not None:
        raw.append(current)

    curses: list[dict] = []
    for index, entry in enumerate(raw, start=1):
        description = [line for line in entry["lines"] if not line.startswith(RESOLVE_PREFIX)]
        resolves = [line for line in entry["lines"] if line.startswith(RESOLVE_PREFIX)]
        resolve = resolves[0].replace(RESOLVE_PREFIX, "").strip(" |") if resolves else None
        curses.append(
            {
                "id": f"curse-{index:04d}",
                "label": entry["label"],
                "severity": entry["severity"],
                "tier": tier_of(entry["severity"]),
                "description": " ".join(description),
                "resolve": resolve,
                "nsfw": entry["label"] in NSFW_CURSES,
            }
        )
    return curses


def run(root: Path, include_nsfw: bool = False) -> dict:
    root = Path(root)
    load_manifest(root)
    source = find_source(root)
    curses = parse_text(source.read_text(encoding="utf-8"))
    if not include_nsfw:
        curses = [curse for curse in curses if not curse["nsfw"]]
    output = root / "data" / "curses.jsonl"
    write_jsonl(output, curses)
    try:
        source_label = str(source.relative_to(root))
    except ValueError:
        source_label = str(source)
    return {"curses": len(curses), "source_file": source_label, "output": str(output)}
