"""Structure loot-table inventory for decision D1.

``PROJECT_PLAN.md`` §6.12 maps chest tables to ticket bands, but the mapping
needs real loot-table IDs and those only exist inside the mod jars. This module
is the ``reports/structure_tables.md`` generator and has two halves:

``collect``
    Resolve the structure/worldgen candidates through the cached Modrinth
    responses, download their pinned jars into a bounded cache and verify every
    byte against the published sha1 and size.

``scan``
    Open each verified jar and list the loot tables it ships, with the table
    type and a *proposed* band derived from the whole table id.

The band is a proposal, never a decision: an id that carries no depth keyword
is reported ``unknown`` rather than being given a confident label, and the
removal allowlist in §7 row 23 stays empty until a human accepts the rows.

Structure jars are not in ``pack_lock.json`` — they are trial/adoption
candidates outside milestone A — so this pass resolves them from the cached
version responses rather than from the pack lock.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import mods
from .util import USER_AGENT, ensure_dir, write_json

JAR_DIR = Path("data") / "jars"
REPORT_NAME = Path("reports") / "structure_tables.md"
MANIFEST_NAME = "manifest.json"
DEFAULT_CAP = 200 * (1 << 20)
_CHUNK = 1 << 20

# The structure and worldgen candidates from ``candidates.txt``.
STRUCTURE_SLUGS = (
    "yungs-better-dungeons",
    "yungs-better-nether-fortresses",
    "yungs-better-ocean-monuments",
    "yungs-better-strongholds",
    "yungs-better-mineshafts",
    "yungs-better-desert-temples",
    "yungs-better-jungle-temples",
    "yungs-better-witch-huts",
    "yungs-better-end-island",
    "yungs-bridges",
    "yungs-extras",
    "structory",
    "structory-towers",
    "dungeons-and-taverns",
    "towns-and-towers",
)

_TABLE_RE = re.compile(r"^data/(?P<ns>[^/]+)/loot_tables?/(?P<path>.+)\.json$")

# ``PROJECT_PLAN.md`` §6.12, most specific band first. Matching runs over the
# whole table id (namespace *and* path): structure mods name their family in
# the namespace, so ``betterstrongholds:chests/armoury`` carries no keyword in
# the path alone.
#
# The hint set was extended 2026-11-03 (D1 feedback: more matchable hints for
# coverage). Every added hint is a structure-family word; they are checked in
# band order, so a stronger match in an earlier band wins (``end_castle`` is
# Platinum even though it also contains ``castle``).
_BANDS = (
    ("Platinum", ("ancient_city", "end_city", "end_island", "end_castle", "end_lighthouse", "trial_chambers")),
    ("Gold", ("stronghold", "mansion", "bastion", "fortress", "keep", "citadel", "castle", "donjon")),
    (
        "Silver",
        (
            "dungeon",
            "monument",
            "outpost",
            "pyramid",
            "temple",
            "witch",
            "crypt",
            "tomb",
            "catacomb",
            "shrine",
            "fort",
            "tower",
            "lair",
            "hideout",
            "outstation",
            "skeleton",
            "library",
            "conduit",
            "bunker",
            "nether_port",
            "piglin_camp",
            "illager",
            "toxic",
        ),
    ),
    (
        "Bronze",
        (
            "village",
            "shipwreck",
            "mineshaft",
            "ruined_portal",
            "hamlet",
            "tavern",
            "supply",
            "supplies",
            "ruin",
            "grave",
            "mood",
            "harvest",
            "outcast",
            "bandit",
            "mining",
            "mine/",
            "settlement",
            "desert",
            "jungle",
            "pots",
            "extra/",
            "manor",
        ),
    ),
)


def propose_band(table_id: str) -> dict:
    """Propose a ticket band from the table id, or ``unknown``."""
    text = str(table_id).lower()
    for band, keywords in _BANDS:
        for keyword in keywords:
            if keyword in text:
                return {"band": band, "hint": keyword, "confidence": "keyword"}
    return {"band": "unknown", "hint": None, "confidence": "none"}


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(url: str, dest: Path, *, cap: int, sha1: str | None, size: int | None) -> tuple[int, str]:
    """Download one jar atomically, enforcing a byte cap and the sha1."""
    dest = Path(dest)
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha1()
    written = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as handle:
            while True:
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if cap is not None and written > cap:
                    raise ValueError(f"{url}: download exceeds the {cap}-byte budget")
                digest.update(chunk)
                handle.write(chunk)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"{url}: {exc}") from exc

    actual = digest.hexdigest()
    if sha1 and actual != sha1:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"{url}: sha1 {actual} does not match the pinned {sha1}")
    if size is not None and written != size:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"{url}: {written} bytes, the pinned size is {size}")
    tmp.replace(dest)
    return written, actual


def collect_jars(
    root,
    *,
    slugs=STRUCTURE_SLUGS,
    directory=JAR_DIR,
    cap: int | None = None,
    download: bool = True,
    write_manifest: bool = True,
) -> list[dict]:
    """Resolve every structure candidate and, when allowed, fetch its jar.

    One row per candidate. ``cached`` and ``downloaded`` mean the jar on disk
    matches the pinned sha1; anything else is a reported gap, never a silent
    skip.
    """
    root = Path(root)
    base = ensure_dir(root / Path(directory))
    budget = DEFAULT_CAP if cap is None else max(0, int(cap))
    spent = 0
    rows: list[dict] = []

    for slug in slugs:
        row = {
            "slug": slug,
            "status": "unresolved",
            "jar": None,
            "bytes": None,
            "sha1": None,
            "version": None,
            "detail": "",
        }
        try:
            resolved = mods.resolve(root, slug, offline=True)
        except mods.ModsError as exc:
            row["detail"] = str(exc)
            rows.append(row)
            continue
        version = resolved.get("version") or {}
        if resolved.get("status") != "ok" or not version:
            row["status"] = resolved.get("status") or "no_build"
            row["detail"] = "no matching build in the cached responses"
            rows.append(row)
            continue
        build = version.get("file") or {}
        filename = build.get("filename")
        url = build.get("url")
        if not filename or not url:
            row["detail"] = "build has no downloadable file"
            rows.append(row)
            continue

        dest = base / filename
        row["jar"] = (Path(directory) / filename).as_posix()
        row["version"] = version.get("version_number")
        sha1 = build.get("sha1")
        size = build.get("size")

        if dest.exists():
            actual = _sha1_file(dest)
            if sha1 and actual != sha1:
                row["status"] = "corrupt"
                row["detail"] = f"cached sha1 {actual[:12]} != pinned {sha1[:12]}"
            else:
                row["status"] = "cached"
                row["bytes"] = dest.stat().st_size
                row["sha1"] = actual
                spent += row["bytes"]
            rows.append(row)
            continue

        if not download:
            row["status"] = "absent"
            row["detail"] = "jar bytes are not cached and downloads are disabled"
            rows.append(row)
            continue

        if size is not None and spent + int(size) > budget:
            row["status"] = "skipped"
            row["detail"] = f"download budget of {budget} bytes exhausted"
            rows.append(row)
            continue

        try:
            written, actual = _fetch(url, dest, cap=budget - spent, sha1=sha1, size=size)
        except (OSError, ValueError) as exc:
            row["status"] = "failed"
            row["detail"] = str(exc)
            rows.append(row)
            continue

        row["status"] = "downloaded"
        row["bytes"] = written
        row["sha1"] = actual
        spent += written
        rows.append(row)

    if write_manifest:
        write_json(
            base / MANIFEST_NAME,
            {"cap": budget, "directory": Path(directory).as_posix(), "jars": rows},
        )
    return rows


def scan_jars(root, *, directory=JAR_DIR) -> list[dict]:
    """Return one entry per jar on disk, each with the loot tables it ships."""
    root = Path(root)
    base = root / Path(directory)
    jars: list[dict] = []
    for path in sorted(base.glob("*.jar")):
        entry = {
            "jar": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha1": _sha1_file(path),
            "tables": [],
            "error": None,
        }
        try:
            with zipfile.ZipFile(path) as handle:
                names = sorted(
                    name for name in handle.namelist() if _TABLE_RE.match(name)
                )
                for name in names:
                    match = _TABLE_RE.match(name)
                    table_id = f"{match.group('ns')}:{match.group('path')}"
                    payload = None
                    error = None
                    try:
                        payload = json.loads(handle.read(name).decode("utf-8"))
                    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                        error = str(exc)
                    table_type = payload.get("type") if isinstance(payload, dict) else None
                    band = propose_band(table_id)
                    entry["tables"].append(
                        {
                            "id": table_id,
                            "type": str(table_type) if table_type else None,
                            "path": name,
                            "jar": entry["jar"],
                            "band": band["band"],
                            "hint": band["hint"],
                            "confidence": band["confidence"],
                            "error": error,
                        }
                    )
        except (OSError, zipfile.BadZipFile) as exc:
            entry["error"] = str(exc)
        jars.append(entry)
    return jars


def _cell(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _is_chest(table: dict) -> bool:
    return str(table.get("type") or "").endswith("chest")


def _status(row: dict) -> str:
    """Collapse the transient download state into a reproducible label.

    Whether this invocation fetched a jar or found it already cached is a
    property of the run, not of the set; the report records the durable fact so
    the offline gate regenerates the same bytes from the same cache.
    """
    return "verified" if row["status"] in ("cached", "downloaded") else row["status"]


def _render(rows: list[dict], jars: list[dict], report_rel: Path) -> str:
    slugs = {row["jar"]: row["slug"] for row in rows if row.get("jar")}
    present = [row for row in rows if row["status"] in ("cached", "downloaded")]
    on_disk = sum(1 for entry in jars if entry["error"] is None)
    total_bytes = sum(entry["bytes"] for entry in jars)
    tables = [table for entry in jars for table in entry["tables"]]
    chest = [table for table in tables if _is_chest(table)]
    other = [table for table in tables if not _is_chest(table)]
    chest.sort(key=lambda table: (table["id"], table["jar"], table["path"]))

    lines = [
        "# Structure loot tables",
        "",
        "Generated by `chaoslab structures` for decision D1. Bands are proposals",
        "derived from the whole table id under `PROJECT_PLAN.md` §6.12; the removal",
        "allowlist in §7 row 23 stays empty until a human accepts rows.",
        "",
        "Structure jars are not part of `pack_lock.json` (they are trial/adoption",
        "candidates outside milestone A), so they are resolved from the cached",
        "Modrinth version responses instead.",
        "",
        "The PrismLauncher instance supplied for the survey holds 59 jars",
        "(391.2 MB) and none of the 15 structure candidates, so the cache below was",
        "populated from Modrinth rather than copied from that folder.",
        "",
        "## Collection",
        "",
        f"Jars on disk: {on_disk} ({total_bytes} bytes). Candidates collected: "
        f"{len(present)} of {len(rows)}.",
        "",
        "| Candidate | Version | Status | Jar | Bytes | Detail |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                _cell(row["slug"]),
                _cell(row.get("version")),
                _cell(_status(row)),
                _cell(row.get("jar")),
                _cell(row.get("bytes")),
                _cell(row.get("detail")),
            )
        )

    lines += ["", "## Chest loot tables", ""]
    if not jars:
        lines.append(
            "No jars are cached, so no loot table could be enumerated. Run "
            "`chaoslab structures --collect` on a machine with network access to "
            "populate `data/jars/`."
        )
    elif not chest:
        lines.append("No chest-typed loot table was found in the cached jars.")
    else:
        lines += [
            f"{len(chest)} chest table(s) across {on_disk} jar(s).",
            "",
            "| Table id | Type | Mod | Jar | Matched hint | Proposed band | Confidence |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for table in chest:
            lines.append(
                "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                    _cell(table["id"]),
                    _cell(table.get("type")),
                    _cell(slugs.get(table["jar"])),
                    _cell(table["jar"]),
                    _cell(table.get("hint")),
                    _cell(table["band"]),
                    _cell(table["confidence"]),
                )
            )

    lines += ["", "## Other tables", ""]
    if other:
        counts: dict[str, int] = {}
        for table in other:
            key = table.get("type") or "unknown"
            counts[key] = counts.get(key, 0) + 1
        lines.append(f"{len(other)} non-chest table(s), by type:")
        lines.append("")
        for key in sorted(counts):
            lines.append(f"- `{key}`: {counts[key]}")
    else:
        lines.append("None.")

    if chest:
        band_order = ("Bronze", "Silver", "Gold", "Platinum", "Diamond", "unknown")
        grouped: dict[str, list[str]] = {}
        for table in chest:
            grouped.setdefault(str(table["band"]), []).append(table["id"])
        summary = ", ".join(
            f"{band} {len(grouped.get(band, []))}"
            for band in ("Bronze", "Silver", "Gold", "Platinum", "unknown")
        )
        lines += [
            "",
            "## D1 answer sheet",
            "",
            "A ready-to-paste block for `DECISIONS.md` D1, grouped by proposed band:",
            f"{summary}.",
            "The proposal lists every chest table the heuristic matched; delete the ids",
            "you reject, or list them under `reject:`. Diamond is never proposed because a",
            "loot-table id does not identify modded endgame depth (§6.12), so it stays a",
            "human assignment.",
            "",
            "```text",
        ]
        for band in band_order:
            ids = sorted(grouped.get(band, []))
            if band == "unknown" and not ids:
                continue
            lines.append(f"band: {band}")
            lines.append("accept:")
            lines.extend(f"  {table_id}" for table_id in ids)
            lines.append("reject:")
            lines.append("")
        lines.append("```")

    unreadable = [table for table in tables if table.get("error")]
    if unreadable:
        lines += ["", "### Unreadable tables", ""]
        for table in unreadable:
            lines.append(f"- `{table['id']}` in `{table['jar']}`: {table['error']}")

    empty = [entry for entry in jars if not entry["tables"] and not entry["error"]]
    if empty:
        lines += ["", "### Jars with no loot tables", ""]
        for entry in empty:
            lines.append(f"- `{entry['jar']}`")

    broken = [entry for entry in jars if entry["error"]]
    if broken:
        lines += ["", "### Unreadable jars", ""]
        for entry in broken:
            lines.append(f"- `{entry['jar']}`: {entry['error']}")

    lines += [
        "",
        "## Not decided here",
        "",
        "- A band is a table-id keyword heuristic, not a verified depth. `unknown`",
        "  means the id carried no keyword from §6.12 — it is not a low band.",
        "- Diamond is unreachable from this heuristic: §6.12 reserves it for modded",
        "  endgame, which a loot-table id does not identify. Those rows must be",
        "  assigned by the human rather than inferred from a keyword.",
        "- No CVE, licence or version-conflict check is performed.",
        "- The accept/reject allowlist is a human answer in `DECISIONS.md`; this",
        "  report supplies the evidence and the paste-ready draft above, not the decision.",
        "",
        f"Report: `{report_rel.as_posix()}`.",
    ]
    return "\n".join(lines) + "\n"


def run(
    root,
    *,
    collect: bool = False,
    jar_dir=JAR_DIR,
    report=REPORT_NAME,
    cap: int | None = None,
    offline: bool = False,
    write_manifest: bool = True,
) -> dict:
    """Collect (optionally) and scan the structure jars, writing the report.

    ``write_manifest=False`` leaves ``data/jars/manifest.json`` untouched, which
    the reproducibility gate needs: it borrows the jar cache read-only.
    """
    root = Path(root)
    report_rel = Path(report)
    rows = collect_jars(
        root,
        directory=jar_dir,
        cap=cap,
        download=collect and not offline,
        write_manifest=write_manifest,
    )
    jars = scan_jars(root, directory=jar_dir)
    text = _render(rows, jars, report_rel)

    path = report_rel if report_rel.is_absolute() else root / report_rel
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

    tables = sum(len(entry["tables"]) for entry in jars)
    return {
        "candidates": len(rows),
        "collected": sum(1 for row in rows if row["status"] in ("cached", "downloaded")),
        "jars": len(jars),
        "tables": tables,
        "chest_tables": sum(
            1 for entry in jars for table in entry["tables"] if _is_chest(table)
        ),
        "report": str(path),
        "statuses": rows,
        "scanned": jars,
    }
