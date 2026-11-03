"""Snapshot layer for the ChaosGacha source tree.

The layer copies a local checkout (preferred) or downloads the five gacha
category files, the curse data and roller, and license probes into
``data/source`` with a manifest of sha256 hashes and line counts. Every later
stage reads only the snapshot, so each report line is traceable to exact
bytes. An existing snapshot is never overwritten without ``refresh``.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CATEGORIES = ("ability", "familiar", "item", "skill", "trait")
EXTRA_FILES = (
    "web/data/curses.txt",
    "web/data/curses.js",
    "web/js/curse-app.js",
    "web/curse.html",
    "web/docs.html",
    "Gacha.py",
)
PROBES = ("README.md", "LICENSE", "LICENSE.md", "COPYING")
DEFAULT_REMOTE = "https://raw.githubusercontent.com/eternaldensity/ChaosGacha/master/"
USER_AGENT = "chaoslab/0.1 (ChaosGacha corpus tooling)"
SCHEMA = 1


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be created or already exists."""


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def count_lines(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def find_local_source(explicit: Optional[str] = None) -> Optional[Path]:
    """Return a ChaosGacha checkout containing ``gachafiles`` if one exists."""
    for candidate in (explicit, os.environ.get("CHAOSGACHA_DIR"), "ChaosGacha"):
        if not candidate:
            continue
        path = Path(candidate)
        if (path / "gachafiles").is_dir():
            return path
    return None


def category_candidates(category: str) -> List[str]:
    return ["gachafiles/%s.%s" % (category, ext) for ext in ("txt", "md")]


def _local_lookup(root: Path, rel: str) -> Optional[Tuple[str, bytes]]:
    path = root / rel
    if path.is_file():
        return rel, path.read_bytes()
    return None


def _remote_lookup(base: str, rel: str) -> Optional[Tuple[str, bytes]]:
    url = base + rel
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return url, response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise SnapshotError("HTTP %s while fetching %s" % (exc.code, url)) from exc
    except urllib.error.URLError as exc:
        raise SnapshotError("network error while fetching %s: %s" % (url, exc.reason)) from exc


def _write(out: Path, rel: str, data: bytes) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def snapshot(
    data_dir: str = "data",
    source_dir: Optional[str] = None,
    refresh: bool = False,
    offline: bool = False,
    remote_base: str = DEFAULT_REMOTE,
) -> Dict[str, object]:
    out = Path(data_dir) / "source"
    manifest_path = out / "manifest.json"
    if manifest_path.exists() and not refresh:
        raise SnapshotError(
            "snapshot already exists at %s; pass --refresh to replace it" % manifest_path
        )

    local = None if offline else find_local_source(source_dir)
    if local is not None:
        kind = "local"
        root = str(local)

        def lookup(rel: str) -> Optional[Tuple[str, bytes]]:
            found = _local_lookup(local, rel)
            if found is None:
                return None
            return "local:%s" % found[0], found[1]

    elif offline:
        raise SnapshotError("--offline requires a local ChaosGacha checkout")
    else:
        kind = "remote"
        root = remote_base

        def lookup(rel: str) -> Optional[Tuple[str, bytes]]:
            return _remote_lookup(remote_base, rel)

    files: List[Dict[str, object]] = []
    missing: List[str] = []
    probes: List[Dict[str, object]] = []

    def record(rel_written: str, origin: str, data: bytes, category: Optional[str] = None) -> None:
        _write(out, rel_written, data)
        entry: Dict[str, object] = {
            "path": rel_written,
            "origin": origin,
            "bytes": len(data),
            "lines": count_lines(data),
            "sha256": sha256(data),
            "fetched_at": utcnow(),
        }
        if category is not None:
            entry["category"] = category
        files.append(entry)

    for category in CATEGORIES:
        found = None
        for rel in category_candidates(category):
            result = lookup(rel)
            if result is not None:
                found = (rel, result)
                break
        if found is None:
            missing.append("gachafiles/%s.[txt|md]" % category)
            continue
        rel, (origin, data) = found
        record(rel, origin, data, category)

    for rel in EXTRA_FILES:
        result = lookup(rel)
        if result is None:
            missing.append(rel)
            continue
        origin, data = result
        record(rel, origin, data)

    license_info: Dict[str, object] = {}
    for rel in PROBES:
        result = lookup(rel)
        present = result is not None
        probe: Dict[str, object] = {"path": rel, "present": present}
        if present:
            origin, data = result
            probe.update({"bytes": len(data), "sha256": sha256(data), "origin": origin})
            if rel not in ("README.md",):
                text = data.decode("utf-8", "replace")
                probe["first_lines"] = "\n".join(text.splitlines()[:40])
                if not license_info:
                    license_info = dict(probe)
            _write(out, rel, data)
        probes.append(probe)

    manifest: Dict[str, object] = {
        "schema": SCHEMA,
        "created_at": utcnow(),
        "source": {"kind": kind, "root": root, "remote_base": remote_base},
        "files": files,
        "missing": missing,
        "probes": probes,
        "license": license_info,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(data_dir: str = "data") -> Dict[str, object]:
    path = Path(data_dir) / "source" / "manifest.json"
    if not path.is_file():
        raise SnapshotError("no snapshot manifest at %s; run `chaoslab fetch` first" % path)
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_file(data_dir: str, rel: str) -> Path:
    return Path(data_dir) / "source" / rel


def category_file(data_dir: str, category: str) -> Optional[Path]:
    for rel in category_candidates(category):
        path = snapshot_file(data_dir, rel)
        if path.is_file():
            return path
    return None
