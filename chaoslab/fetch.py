"""CLI-facing snapshot adapter over :mod:`chaoslab.source`.

The snapshot implementation lives in ``source.py``. This module exposes the
names the CLI and the parser import (``CATEGORY_FILES``, ``FetchError``,
``load_manifest``, ``fetch``) and converts the raw manifest into the compact
summary the CLI prints. Keeping one adapter means the source layout is
described in exactly one place.
"""
from __future__ import annotations

from pathlib import Path

from . import source as _source

CATEGORIES = _source.CATEGORIES
CATEGORY_FILES = _source.CATEGORIES
SnapshotError = _source.SnapshotError
FetchError = _source.SnapshotError


def load_manifest(root) -> dict:
    """Load a manifest given either the data directory or the repo root."""
    root = Path(root)
    if (root / "source" / "manifest.json").is_file():
        return _source.load_manifest(str(root))
    return _source.load_manifest(str(root / "data"))


def fetch(root, source_dir=None, refresh: bool = False, offline: bool = False) -> dict:
    """Snapshot the corpus and report a flat, printable file inventory."""
    root = Path(root)
    raw = _source.snapshot(
        str(root / "data"),
        source_dir=source_dir,
        refresh=refresh,
        offline=offline,
    )

    files: list[dict] = []
    for record in raw.get("files", []):
        row = dict(record)
        row["present"] = True
        files.append(row)
    for rel in raw.get("missing", []):
        files.append(
            {
                "path": rel,
                "origin": None,
                "bytes": 0,
                "lines": 0,
                "sha256": None,
                "present": False,
            }
        )
    for probe in raw.get("probes", []):
        files.append(
            {
                "path": probe["path"],
                "origin": probe.get("origin"),
                "bytes": int(probe.get("bytes") or 0),
                "lines": 0,
                "sha256": probe.get("sha256"),
                "present": bool(probe.get("present")),
            }
        )
    files.sort(key=lambda row: row["path"])

    present = sum(1 for row in files if row["present"])
    return {
        "source_kind": raw["source"]["kind"],
        "source": raw["source"]["root"],
        "files": files,
        "present": present,
        "absent": len(files) - present,
        "total_bytes": sum(int(row.get("bytes") or 0) for row in files),
        "license": raw.get("license") or {},
        "manifest": raw,
    }
