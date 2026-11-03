"""Discover candidate mods and quest examples from popular modpacks.

A ``.mrpack`` is a small zip, not a full instance: ``modrinth.index.json`` lists
every bundled jar with a Modrinth CDN download URL that embeds the project ID,
and ``overrides/`` carries the pack's config. That makes popular packs a precise
source of two things this project needs:

- **candidate mods**, mapped by project ID rather than fuzzy title matching, and
- **worked quest examples**, since a pack that ships a quest mod also ships the
  chapters its author wrote.

Packs are ranked by downloads inside the same 1.21.1 / neoforge filter used by
``chaoslab mods``, and the raw ``.mrpack`` bytes are cached so reruns can be
offline.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

from . import mods
from .util import USER_AGENT, ensure_dir, write_json

PACKS_DIR = Path("data") / "modpacks"
REPORT_NAME = "modpacks_survey.md"
DEFAULT_LIMIT = 12
DEFAULT_MAX_LOOKUPS = 2000
DEFAULT_CAP = 400_000_000
RETRIES = 2
BULK_CHUNK = 90

# Curated for progression, magic and tech identity rather than raw downloads.
# The first six are the original pack set that produced the first survey; the
# rest came from the 1.21.1 / neoforge download ranking for quest, RPG, magic
# and tech search terms and replace a ranking that was creature-pack heavy.
DEFAULT_PACKS = (
    "better-mc-neoforge-bmc5",
    "rubius-cobblemon",
    "fom",
    "cobblemon-neoforge",
    "the-pixelmon-modpack",
    "create_plus",
    "irons-magic",
    "industrial-odyssey",
    "arcadia",
    "mythcraft",
    "medival-magic-tech",
    "rpg-create-plus",
    "antique-runes",
    "travelers-reborn",
    "crafted-knowledge-3",
    "lyrrans-magicraft",
    # Added 2026-10-22 from the user's request: a popular Create/Aeronautics pack
    # with a quests category, a current 1.21.1/neoforge release (12.0.0) and a
    # large embedded-dependency set, so it exercises both the tech and quest
    # harvest paths. Included as a named pack rather than through the download
    # ranking, which is creature-pack heavy.
    "create-ultimate-selection-2",
)

_CDN_RE = re.compile(r"/data/([A-Za-z0-9]{8})/versions/")
_PREFIX = r"(?:overrides|client-overrides|server-overrides)"

# Ordered: the first matching label wins, so generic "quest" configs do not
# double-count packs that already have a named quest system.
_QUEST_PATTERNS = (
    ("FTB Quests", re.compile(rf"^{_PREFIX}/config/ftbquests/.*\.snbt$")),
    ("Better Questing", re.compile(rf"^{_PREFIX}/config/betterquesting/.*\.(json|snbt)$")),
    ("Heracles", re.compile(rf"^{_PREFIX}/config/heracles/.*\.(json|snbt)$")),
    ("Odyssey Quests", re.compile(rf"^{_PREFIX}/config/odyssey[a-z_]*/.*\.(json|snbt)$")),
    ("Puffish Skills", re.compile(rf"^{_PREFIX}/config/puffish_skills/.*\.(json|snbt)$")),
    ("JustLeveling", re.compile(rf"^{_PREFIX}/config/justleveling/.*\.(json|toml)$")),
    ("Generic quest config", re.compile(rf"^{_PREFIX}/config/[^/]*quest[^/]*/.*\.(json|snbt|toml)$", re.I)),
)

_TITLE_RE = re.compile(r'(?m)^\s*"?title"?\s*[:=]\s*"?([^"\n]{1,120})"?')
_FILENAME_RE = re.compile(r'(?m)^\s*filename:\s*"([^"\n]{1,120})"')
_NAME_RE = re.compile(r'(?m)^\s*"name"\s*:\s*"([^"\n]{1,120})"')
_QUEST_MARKER = "tasks: ["
_MAX_QUEST_BYTES = 1_000_000

def _pack_search_rel(version: str, loader: str, limit: int, query: str = "") -> str:
    key = f"modpack|{query}|{version}|{loader}|{limit}".encode("utf-8")
    return f"search/{hashlib.sha1(key).hexdigest()[:16]}.json"


def _pack_search_url(version: str, loader: str, limit: int, query: str = "") -> str:
    facets = json.dumps(
        [
            ["project_type:modpack"],
            [f"versions:{version}"],
            [f"categories:{loader}"],
        ],
        separators=(",", ":"),
    )
    params = {"query": query, "facets": facets, "limit": str(limit), "index": "downloads"}
    return f"{mods.API_ROOT}/search?" + urllib.parse.urlencode(params)


def _projects_url(project_ids) -> str:
    """Return the bulk project URL for up to ``BULK_CHUNK`` project IDs.

    Modrinth accepts a JSON array of IDs on ``/v2/projects`` and answers with
    full project records, which turns an O(n) name lookup into O(n / 90).
    """
    joined = json.dumps(list(project_ids), separators=(",", ":"))
    return f"{mods.API_ROOT}/projects?ids=" + urllib.parse.quote(joined)


def search_packs(
    root,
    version: str,
    loader: str,
    limit: int,
    *,
    offline: bool,
    refresh: bool,
    query: str = "",
) -> list:
    """Return modpack search hits ranked by downloads for the target build.

    ``query`` narrows the ranking to packs whose metadata mentions a term, which
    is how quest-driven packs are reached when they are not download leaders.
    """
    limit = max(1, min(int(limit), 50))
    query = query.strip()
    payload = mods._get_json(
        root,
        _pack_search_rel(version, loader, limit, query),
        _pack_search_url(version, loader, limit, query),
        offline=offline,
        refresh=refresh,
    )
    hits = payload.get("hits") if isinstance(payload, dict) else None
    if not isinstance(hits, list):
        raise mods.ModsError("unexpected modpack search payload")
    return hits


def _binary_rel(slug: str, version: str, loader: str) -> str:
    return f"{mods._safe_slug(slug)}__{mods._safe_slug(version)}__{mods._safe_slug(loader)}.mrpack"


def _binary_path(root, rel: str) -> Path:
    return Path(root) / PACKS_DIR / rel


def _load_binary(root, rel: str):
    try:
        return _binary_path(root, rel).read_bytes()
    except FileNotFoundError:
        return None


def _store_binary(root, rel: str, url: str, payload: bytes) -> None:
    path = _binary_path(root, rel)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)
    write_json(
        path.with_suffix(path.suffix + ".json"),
        {"url": url, "fetched_at": mods._now(), "bytes": len(payload)},
    )


def _http_bytes(url: str, cap: int) -> bytes:
    delay = 1.0
    last_error = "unknown error"
    for attempt in range(RETRIES + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            chunks = []
            total = 0
            with urllib.request.urlopen(request, timeout=60) as response:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > cap:
                        raise mods.ModsError(f"download exceeds {cap} bytes: {url}")
                    chunks.append(chunk)
            return b"".join(chunks)
        except urllib.error.HTTPError as exc:
            if (exc.code == 429 or 500 <= exc.code < 600) and attempt < RETRIES:
                last_error = f"HTTP {exc.code}"
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise mods.ModsError(f"{url}: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            last_error = str(exc.reason)
            if attempt < RETRIES:
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise mods.ModsError(f"{url}: {last_error}") from exc
        except (TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempt < RETRIES:
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise mods.ModsError(f"{url}: {exc}") from exc
    raise mods.ModsError(f"{url}: {last_error}")


def pack_bytes(root, slug: str, version: str, loader: str, *, url: str, size, cap: int, offline: bool, refresh: bool) -> bytes:
    """Return cached ``.mrpack`` bytes, downloading at most ``cap`` bytes."""
    rel = _binary_rel(slug, version, loader)
    if offline:
        payload = _load_binary(root, rel)
        if payload is None:
            raise mods.ModsError(f"offline: no cached .mrpack for {slug}")
        return payload
    if not refresh:
        payload = _load_binary(root, rel)
        if payload is not None:
            return payload
    if not url:
        raise mods.ModsError(f"{slug}: version has no .mrpack download")
    if isinstance(size, int) and size > cap:
        raise mods.ModsError(f"{slug}: .mrpack is {size} bytes, above the {cap} byte cap")
    payload = _http_bytes(str(url), cap)
    _store_binary(root, rel, str(url), payload)
    return payload


def _project_ids(files) -> tuple[list, int]:
    ids: list[tuple[str, str]] = []
    unmapped = 0
    for entry in files:
        downloads = entry.get("downloads") or []
        found = None
        for url in downloads:
            match = _CDN_RE.search(str(url))
            if match:
                found = match.group(1)
                break
        if found is None:
            unmapped += 1
        else:
            ids.append((found, str(entry.get("path") or "")))
    return ids, unmapped


def _first_title(text: str):
    match = _TITLE_RE.search(text) or _FILENAME_RE.search(text) or _NAME_RE.search(text)
    return match.group(1).strip() if match else None


def _quest_count(text: str) -> int:
    """Count quests by their task blocks; FTB writes one ``tasks: [`` per quest."""
    return text.count(_QUEST_MARKER)

_INDEX_STEMS = {"chapter_groups", "chapters", "data", "quest_links", "reward_tables"}


def _example_order(path: str):
    """Rank real chapter files ahead of index files inside a quest directory."""
    name = path.rsplit("/", 1)[-1]
    stem = name.split(".", 1)[0]
    return (
        0 if "/chapters/" in path else 1,
        0 if stem not in _INDEX_STEMS else 1,
        path,
    )


def _quest_examples(handle: zipfile.ZipFile, names) -> dict:
    systems: dict[str, list[str]] = {}
    for name in names:
        for label, pattern in _QUEST_PATTERNS:
            if pattern.match(name):
                systems.setdefault(label, []).append(name)
                break

    examples: dict[str, dict] = {}
    for label, paths in systems.items():
        picked = []
        for path in sorted(paths, key=_example_order)[:3]:
            try:
                with handle.open(path) as entry:
                    raw = entry.read(_MAX_QUEST_BYTES)
            except (KeyError, OSError):
                continue
            text = raw.decode("utf-8", "replace")
            picked.append({"path": path, "title": _first_title(text), "quests": _quest_count(text)})
        examples[label] = {"files": len(paths), "examples": picked}
    return examples


def _inspect_pack(payload: bytes) -> dict:
    try:
        handle = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise mods.ModsError(f"not a valid .mrpack zip: {exc}") from exc
    with handle:
        names = handle.namelist()
        try:
            raw = handle.read("modrinth.index.json")
        except KeyError as exc:
            raise mods.ModsError("missing modrinth.index.json") from exc
        try:
            index = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise mods.ModsError(f"invalid modrinth.index.json: {exc}") from exc
        files = index.get("files") if isinstance(index, dict) else None
        if not isinstance(files, list):
            raise mods.ModsError("modrinth.index.json has no files list")
        ids, unmapped = _project_ids(files)
        overrides = [name for name in names if name.startswith(("overrides/", "client-overrides/", "server-overrides/"))]
        quests = _quest_examples(handle, overrides)
    return {
        "mod_ids": ids,
        "unmapped": unmapped,
        "quests": quests,
        "overrides": len(overrides),
        "entries": len(files),
    }


def _bulk_projects(root, project_ids, *, offline: bool, refresh: bool) -> dict:
    """Return ``{project_id: payload}`` using cache first, then bulk requests.

    Cached single-project entries stay authoritative so ``--offline`` works and
    ``--refresh`` is honoured. Missing IDs are requested in bulk; if a chunk
    fails, it falls back to individual lookups so one bad ID cannot sink the
    whole chunk. Successful records are stored under the same per-project cache
    path that ``mods.resolve`` uses.
    """
    payloads = {}
    missing = []
    for project_id in project_ids:
        if not refresh:
            cached = mods._load_cached(root, mods._project_rel(project_id))
            if isinstance(cached, dict):
                payloads[project_id] = cached
                continue
        if offline:
            continue
        missing.append(project_id)
    if offline:
        return payloads

    for start in range(0, len(missing), BULK_CHUNK):
        chunk = missing[start : start + BULK_CHUNK]
        try:
            body = mods._http_json(_projects_url(chunk))
        except mods.ModsError:
            body = None
        if isinstance(body, list):
            for record in body:
                if not isinstance(record, dict):
                    continue
                project_id = record.get("id")
                if not project_id:
                    continue
                project_id = str(project_id)
                mods._store_cached(
                    root,
                    mods._project_rel(project_id),
                    mods._project_url(project_id),
                    record,
                )
                payloads[project_id] = record
        else:
            for project_id in chunk:
                try:
                    record = mods._http_json(mods._project_url(project_id))
                except mods.ModsError:
                    continue
                if not isinstance(record, dict):
                    continue
                mods._store_cached(
                    root,
                    mods._project_rel(project_id),
                    mods._project_url(project_id),
                    record,
                )
                payloads[project_id] = record
        if start + BULK_CHUNK < len(missing):
            time.sleep(0.25)
    return payloads


def _resolve_projects(root, project_ids, version: str, loader: str, *, offline: bool, refresh: bool, cap: int) -> dict:
    """Resolve project IDs to records, in bulk where the cache misses.

    A batch big enough to cover a large pack can exhaust Modrinth's per-minute
    quota, so missing IDs are grouped into bulk requests (with a serial
    fallback) instead of one request per project. Cached entries are reused, so
    reruns remain offline-reproducible.
    """
    wanted = list(project_ids)[:cap]
    payloads = _bulk_projects(root, wanted, offline=offline, refresh=refresh)
    records = {}
    for project_id in wanted:
        payload = payloads.get(project_id)
        records[project_id] = mods._project_record(payload) if isinstance(payload, dict) else None
    return records


def _side(project) -> str:
    if not project:
        return "—"
    client = project.get("client_side")
    server = project.get("server_side")
    return f"client {client}, server {server}"


def _server_usable(project) -> bool:
    if not project:
        return False
    if project.get("project_type") != "mod":
        return False
    categories = project.get("categories") or []
    if "library" in categories:
        return False
    return project.get("server_side") in ("required", "optional")


def _write_report(path: Path, rows, version: str, loader: str, records: dict, candidates: set[str]) -> None:
    ensure_dir(path.parent)
    pack_count = len(rows)
    mapped = sum(len(row["mod_ids"]) for row in rows)
    unmapped = sum(row["unmapped"] for row in rows)
    systems = {label for row in rows for label in row["quests"]}
    named = sum(1 for project in records.values() if project)
    noun = "modpack" if pack_count == 1 else "modpacks"
    ids = Counter()
    for row in rows:
        for project_id in sorted({pair[0] for pair in row["mod_ids"]}):
            ids[project_id] += 1

    lines = [
        f"# Modpack survey: {version} / {loader}",
        "",
        f"{pack_count} {noun} inspected, ranked by downloads inside the {version} / {loader} filter. "
        f"{mapped} Modrinth-hosted files mapped to project IDs, {unmapped} files used non-Modrinth downloads. "
        f"{len(ids)} distinct projects seen; {named} resolved to names.",
        "",
        "Generated by `chaoslab modpacks` from cached Modrinth v2 responses and cached `.mrpack` "
        "files under `data/modpacks/`; rerun with `--refresh` for current data.",
        "",
        "## Packs",
        "",
        "| Pack | Downloads | Pack version | Size | Entries | Mapped | Unmapped | Quest / progression systems |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["status"] == "ok":
            version_cell = f"{row['pack_version']} ({mods._date(row['published'])})"
            size_cell = f"{row['size']:,} B" if isinstance(row.get("size"), int) else "—"
            systems_cell = ", ".join(sorted(row["quests"])) or "none"
            values = (
                row["slug"],
                f"{row['downloads']:,}",
                version_cell,
                size_cell,
                str(row["entries"]),
                str(len(row["mod_ids"])),
                str(row["unmapped"]),
                systems_cell,
            )
        else:
            values = (row["slug"], f"{row['downloads']:,}", "—", "—", "—", "—", "—", row["detail"] or row["status"])
        lines.append("| " + " | ".join(mods._cell(value) for value in values) + " |")
    lines.append("")

    lines += ["## Quest and progression examples", ""]
    if systems:
        for row in rows:
            if not row["quests"]:
                continue
            lines += [f"### {row['slug']}", ""]
            for label, info in sorted(row["quests"].items()):
                lines.append(f"- **{label}** — {info['files']} file(s)")
                for example in info["examples"]:
                    title = f" — {example['title']}" if example["title"] else ""
                    quests = f" ({example['quests']} quests)" if example.get("quests") else ""
                    lines.append(f"  - `{example['path']}`{title}{quests}")
            lines.append("")
    else:
        lines += ["No quest or progression configs were found in the inspected pack overrides.", ""]

    lines += [
        "## Cross-pack mod frequency",
        "",
        "| Mod | Packs | Downloads | Side | License | In candidates |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    resolved_rows = []
    unresolved_counts = []
    skipped_counts = []
    for project_id, count in ids.most_common():
        if project_id not in records:
            skipped_counts.append((project_id, count))
            continue
        project = records[project_id]
        if not project:
            unresolved_counts.append((project_id, count))
            continue
        slug = project.get("slug") or project_id
        resolved_rows.append((slug, count, project))
        lines.append(
            "| "
            + " | ".join(
                mods._cell(value)
                for value in (
                    slug,
                    str(count),
                    f"{(project or {}).get('downloads', 0):,}" if project else "—",
                    _side(project),
                    (project or {}).get("license"),
                    "yes" if slug in candidates else "",
                )
            )
            + " |"
        )
    lines.append("")

    suggestions = [
        (slug, count, project)
        for slug, count, project in resolved_rows
        if count >= 2 and slug not in candidates and _server_usable(project)
    ]
    lines += ["## Suggested additions", ""]
    if suggestions:
        lines.append("Server-usable mods seen in at least two packs and absent from `candidates.txt`:")
        lines.append("")
        for slug, count, project in sorted(suggestions, key=lambda item: (-item[1], item[0])):
            downloads = f"{(project or {}).get('downloads', 0):,}"
            lines.append(f"- `{slug}` — {count} packs, {downloads} downloads, {(project or {}).get('license') or 'unknown license'}")
    else:
        lines.append("None: every repeated, server-usable mod is already in `candidates.txt`.")
    lines.append("")

    lines += ["## Unresolved project IDs", ""]
    if unresolved_counts:
        lines.append("Looked up, but the project record could not be fetched:")
        lines.append("")
        lines += [
            f"- `{project_id}` ({count} file(s))"
            for project_id, count in sorted(unresolved_counts, key=lambda item: (-item[1], item[0]))
        ]
    else:
        lines.append("None: every project that was looked up resolved to a name.")
    lines.append("")

    if skipped_counts:
        lines += [
            "## Not looked up",
            "",
            f"{len(skipped_counts)} project(s) fell outside `--max-lookups`, so they are unnamed "
            "here rather than missing from Modrinth. Raise `--max-lookups` to resolve them.",
            "",
        ]

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(
    root,
    *,
    version: str = mods.DEFAULT_VERSION,
    loader: str = mods.DEFAULT_LOADER,
    limit: int = DEFAULT_LIMIT,
    packs=None,
    offline: bool = False,
    refresh: bool = False,
    report: str | None = None,
    max_lookups: int = DEFAULT_MAX_LOOKUPS,
    cap: int | None = None,
    query: str = "",
    ranked: bool = False,
) -> dict:
    cap = DEFAULT_CAP if cap is None else int(cap)
    root = Path(root)

    def named_hits(slugs):
        hits = []
        for slug in slugs:
            title = slug
            downloads = 0
            try:
                payload = mods._get_json(
                    root,
                    mods._project_rel(slug),
                    mods._project_url(slug),
                    offline=offline,
                    refresh=refresh,
                )
            except mods.ModsError:
                payload = None
            if isinstance(payload, dict):
                title = payload.get("title") or slug
                downloads = int(payload.get("downloads") or 0)
            hits.append({"slug": slug, "title": title, "downloads": downloads})
        return hits

    if packs:
        hits = named_hits(packs)
    elif ranked or query:
        hits = search_packs(
            root, version, loader, limit, offline=offline, refresh=refresh, query=query
        )
    else:
        hits = named_hits(DEFAULT_PACKS)

    rows = []
    per_pack_ids = []
    statuses = Counter()
    for hit in hits:
        slug = str(hit.get("slug") or "").strip()
        if not slug:
            continue
        try:
            resolved = mods.resolve(root, slug, version, loader, offline=offline, refresh=refresh)
        except mods.ModsError as exc:
            rows.append(
                {
                    "slug": slug,
                    "downloads": int(hit.get("downloads") or 0),
                    "status": "error",
                    "detail": str(exc),
                    "mod_ids": [],
                    "unmapped": 0,
                    "quests": {},
                    "entries": 0,
                }
            )
            statuses["error"] += 1
            continue

        version_record = resolved.get("version")
        if not version_record:
            rows.append(
                {
                    "slug": slug,
                    "downloads": int(hit.get("downloads") or 0),
                    "status": "no_build",
                    "detail": "no matching build",
                    "mod_ids": [],
                    "unmapped": 0,
                    "quests": {},
                    "entries": 0,
                }
            )
            statuses["no_build"] += 1
            continue

        file = version_record.get("file") or {}
        try:
            payload = pack_bytes(
                root,
                resolved["project"].get("slug") or slug,
                version,
                loader,
                url=file.get("url"),
                size=file.get("size"),
                cap=cap,
                offline=offline,
                refresh=refresh,
            )
            inspected = _inspect_pack(payload)
        except mods.ModsError as exc:
            rows.append(
                {
                    "slug": slug,
                    "downloads": int(hit.get("downloads") or 0),
                    "status": "error",
                    "detail": str(exc),
                    "mod_ids": [],
                    "unmapped": 0,
                    "quests": {},
                    "entries": 0,
                }
            )
            statuses["error"] += 1
            continue

        rows.append(
            {
                "slug": resolved["project"].get("slug") or slug,
                "downloads": int(hit.get("downloads") or 0),
                "status": "ok",
                "detail": None,
                "pack_version": version_record.get("version_number"),
                "published": version_record.get("date_published"),
                "size": file.get("size"),
                "entries": inspected["entries"],
                "mod_ids": inspected["mod_ids"],
                "unmapped": inspected["unmapped"],
                "quests": inspected["quests"],
                "overrides": inspected["overrides"],
            }
        )
        statuses["ok"] += 1
        per_pack_ids.append({project_id for project_id, _path in inspected["mod_ids"]})

    counts = Counter()
    for pack_ids in per_pack_ids:
        counts.update(pack_ids)
    lookup_ids = [project_id for project_id, _count in counts.most_common(max_lookups)]
    records = _resolve_projects(
        root,
        lookup_ids,
        version,
        loader,
        offline=offline,
        refresh=refresh,
        cap=max_lookups,
    )

    candidates = set()
    candidates_path = root / "candidates.txt"
    if candidates_path.exists():
        try:
            from .survey import parse_candidates

            candidates = {slug for _group, slug in parse_candidates(candidates_path)}
        except mods.ModsError:
            candidates = set()

    if report:
        report_path = Path(report)
        if not report_path.is_absolute():
            report_path = root / report_path
    else:
        report_path = root / "reports" / REPORT_NAME
    _write_report(report_path, rows, version, loader, records, candidates)
    return {
        "packs": len(rows),
        "mods": sum(len({project_id for project_id, _path in row["mod_ids"]}) for row in rows),
        "named": sum(1 for project in records.values() if project),
        "quest_systems": len({label for row in rows for label in row["quests"]}),
        "report": str(report_path),
        "statuses": dict(statuses),
    }
