"""Shared helpers: paths, rarity tiers, JSON/JSONL IO, HTTP."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SOURCE_DIR = DATA_DIR / "source"
CACHE_DIR = ROOT / "cache"
REPORT_DIR = ROOT / "reports"

USER_AGENT = "chaoslab/0.1 (local research; Chaos Gacha corpus and mod evidence)"

# Source rarity is a float on 0..10; these are the upper bounds per tier.
_TIERS = (
    ("Trash", 1.0),
    ("Common", 2.0),
    ("Uncommon", 3.0),
    ("Rare", 4.0),
    ("Elite", 5.0),
    ("Epic", 6.0),
    ("Legendary", 7.0),
    ("Mythical", 8.0),
    ("Divine", 9.0),
)
TIER_NAMES = tuple(name for name, _ in _TIERS) + ("Transcendent",)


class FetchError(RuntimeError):
    """A remote or local source could not be read."""


def tier_for(rarity: float) -> str:
    """Map a 0..10 rarity to the source's tier vocabulary."""
    for name, upper in _TIERS:
        if rarity < upper:
            return name
    return "Transcendent"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def line_count(payload: bytes) -> int:
    if not payload:
        return 0
    return payload.count(b"\n") + (0 if payload.endswith(b"\n") else 1)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default=None):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def write_json(path: Path, payload) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def write_jsonl(path: Path, rows) -> int:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    written = 0
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")
            written += 1
    tmp.replace(path)
    return written


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def http_get(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise FetchError(f"{url}: {exc}") from exc
