"""Modrinth catalog: search, resolve, and the compatibility matrix.

Only the keyless JSON API is used. Raw responses are cached under data/mods/
so derived rows can be recomputed without another network call.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .util import USER_AGENT, ensure_dir, read_json, write_json

API_ROOT = "https://api.modrinth.com/v2"
DEFAULT_VERSION = "1.21.1"
DEFAULT_LOADER = "neoforge"
MODS_DIR = Path("data") / "mods"
REPORT_NAME = "mods_matrix.md"
REQUEST_TIMEOUT = 30
RETRIES = 3

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ModsError(RuntimeError):
    """A mod record could not be retrieved or interpreted."""


class NotFound(ModsError):
    """The requested project does not exist on Modrinth."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _published(value) -> datetime:
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _http_json(url: str):
    delay = 1.0
    last_error = "unknown error"
    for attempt in range(RETRIES + 1):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise NotFound(f"not found: {url}") from exc
            if (exc.code == 429 or 500 <= exc.code < 600) and attempt < RETRIES:
                last_error = f"HTTP {exc.code}"
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise ModsError(f"{url}: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            last_error = str(exc.reason)
            if attempt < RETRIES:
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise ModsError(f"{url}: {last_error}") from exc
        except (TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempt < RETRIES:
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            raise ModsError(f"{url}: {exc}") from exc
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModsError(f"{url}: invalid JSON: {exc}") from exc
    raise ModsError(f"{url}: {last_error}")


def _cache_root(root) -> Path:
    return Path(root) / MODS_DIR


def _load_cached(root, rel: str):
    payload = read_json(_cache_root(root) / rel, None)
    if payload is None:
        return None
    if not isinstance(payload, dict) or "body" not in payload:
        raise ModsError(f"cache entry {rel} is malformed; rerun with --refresh")
    return payload["body"]


def _store_cached(root, rel: str, url: str, body) -> None:
    path = _cache_root(root) / rel
    write_json(path, {"url": url, "fetched_at": _now(), "body": body})
    index_path = _cache_root(root) / "index.json"
    index = read_json(index_path, {"entries": {}})
    if not isinstance(index, dict):
        index = {"entries": {}}
    entries = index.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        index["entries"] = entries
    entries[rel] = {"url": url, "fetched_at": _now()}
    write_json(index_path, index)


def _get_json(root, rel: str, url: str, *, offline: bool, refresh: bool):
    if offline:
        cached = _load_cached(root, rel)
        if cached is None:
            raise ModsError(f"offline: no cached response for {rel}")
        return cached
    if not refresh:
        cached = _load_cached(root, rel)
        if cached is not None:
            return cached
    body = _http_json(url)
    _store_cached(root, rel, url, body)
    return body


def _safe_slug(slug: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", slug)


def _project_rel(slug: str) -> str:
    return f"project/{_safe_slug(slug)}.json"


def _versions_rel(slug: str, version: str, loader: str) -> str:
    return f"versions/{_safe_slug(slug)}__{_safe_slug(version)}__{_safe_slug(loader)}.json"


def _search_rel(query: str, version: str, loader: str, limit: int) -> str:
    key = f"{query}|{version}|{loader}|{limit}".encode("utf-8")
    return f"search/{hashlib.sha1(key).hexdigest()[:16]}.json"


def _project_url(slug: str) -> str:
    return f"{API_ROOT}/project/{urllib.parse.quote(slug, safe='')}"


def _versions_url(slug: str, version: str, loader: str) -> str:
    params = {
        "game_versions": json.dumps([version], separators=(",", ":")),
        "loaders": json.dumps([loader], separators=(",", ":")),
    }
    return (
        f"{API_ROOT}/project/{urllib.parse.quote(slug, safe='')}/version?"
        + urllib.parse.urlencode(params)
    )


def _search_url(query: str, version: str, loader: str, limit: int) -> str:
    facets = json.dumps(
        [
            ["project_type:mod"],
            [f"versions:{version}"],
            [f"categories:{loader}"],
        ],
        separators=(",", ":"),
    )
    params = {
        "query": query,
        "facets": facets,
        "limit": str(limit),
        "index": "relevance",
    }
    return f"{API_ROOT}/search?" + urllib.parse.urlencode(params)


def _license_id(project):
    info = project.get("license")
    if isinstance(info, dict):
        return info.get("id") or info.get("name")
    if isinstance(info, str):
        return info
    return None


def _project_record(project) -> dict:
    return {
        "slug": project.get("slug"),
        "id": project.get("id"),
        "title": project.get("title"),
        "summary": project.get("description"),
        "project_type": project.get("project_type"),
        "downloads": int(project.get("downloads") or 0),
        "followers": int(project.get("followers") or 0),
        "updated": project.get("updated"),
        "license": _license_id(project),
        "client_side": project.get("client_side"),
        "server_side": project.get("server_side"),
        "categories": sorted(project.get("categories") or []),
        "loaders": sorted(project.get("loaders") or []),
        "game_versions": sorted(project.get("game_versions") or []),
    }


def _version_record(version) -> dict:
    files = version.get("files") or []
    primary = None
    for candidate in files:
        if candidate.get("primary"):
            primary = candidate
            break
    if primary is None and files:
        primary = files[0]
    dependencies = []
    for dep in version.get("dependencies") or []:
        dependencies.append(
            {
                "project_id": dep.get("project_id"),
                "version_id": dep.get("version_id"),
                "dependency_type": dep.get("dependency_type"),
                "file_name": dep.get("file_name"),
            }
        )
    return {
        "id": version.get("id"),
        "version_number": version.get("version_number"),
        "name": version.get("name"),
        "version_type": version.get("version_type"),
        "date_published": version.get("date_published"),
        "game_versions": version.get("game_versions") or [],
        "loaders": version.get("loaders") or [],
        "dependencies": dependencies,
        "required_dependencies": [
            dep for dep in dependencies if dep.get("dependency_type") == "required"
        ],
        "file": None
        if primary is None
        else {
            "filename": primary.get("filename"),
            "size": primary.get("size"),
            "sha1": (primary.get("hashes") or {}).get("sha1"),
            "sha512": (primary.get("hashes") or {}).get("sha512"),
            "url": primary.get("url"),
        },
    }


def _hit_row(hit, version: str, loader: str) -> dict:
    versions = hit.get("versions")
    categories = hit.get("categories")
    has_build = None
    if isinstance(versions, list) and isinstance(categories, list):
        has_build = version in versions and loader in categories
    return {
        "slug": hit.get("slug"),
        "title": hit.get("title"),
        "project_type": hit.get("project_type"),
        "description": hit.get("description"),
        "downloads": int(hit.get("downloads") or 0),
        "followers": int(hit.get("follows") or 0),
        "has_build": has_build,
        "categories": sorted(categories or []),
    }


def search(
    root,
    query: str,
    version: str = DEFAULT_VERSION,
    loader: str = DEFAULT_LOADER,
    limit: int = 20,
    *,
    offline: bool = False,
    refresh: bool = False,
) -> list:
    query = query.strip()
    if not query:
        raise ModsError("search query is empty")
    limit = max(1, min(int(limit), 100))
    url = _search_url(query, version, loader, limit)
    payload = _get_json(
        root,
        _search_rel(query, version, loader, limit),
        url,
        offline=offline,
        refresh=refresh,
    )
    hits = payload.get("hits") if isinstance(payload, dict) else None
    if not isinstance(hits, list):
        raise ModsError(f"{url}: unexpected search payload")
    return [_hit_row(hit, version, loader) for hit in hits]


def resolve(
    root,
    project: str,
    version: str = DEFAULT_VERSION,
    loader: str = DEFAULT_LOADER,
    *,
    offline: bool = False,
    refresh: bool = False,
) -> dict:
    slug = str(project).strip().rstrip("/")
    if "modrinth.com" in slug:
        slug = slug.rsplit("/", 1)[-1]
    if not slug:
        raise ModsError("project slug is empty")

    project_payload = _get_json(
        root,
        _project_rel(slug),
        _project_url(slug),
        offline=offline,
        refresh=refresh,
    )
    if not isinstance(project_payload, dict):
        raise ModsError(f"{slug}: unexpected project payload")
    resolved_slug = project_payload.get("slug") or slug

    versions_payload = _get_json(
        root,
        _versions_rel(resolved_slug, version, loader),
        _versions_url(resolved_slug, version, loader),
        offline=offline,
        refresh=refresh,
    )
    if not isinstance(versions_payload, list):
        raise ModsError(f"{resolved_slug}: unexpected version payload")

    matching = [
        entry
        for entry in versions_payload
        if isinstance(entry, dict)
        and version in (entry.get("game_versions") or [])
        and loader in (entry.get("loaders") or [])
    ]
    matching.sort(key=lambda entry: _published(entry.get("date_published")), reverse=True)
    releases = [entry for entry in matching if entry.get("version_type") == "release"]
    pool = releases or matching
    chosen = pool[0] if pool else None
    newest_release = releases[0] if releases else None

    return {
        "status": "ok" if chosen else "no_build",
        "project": _project_record(project_payload),
        "query": {"version": version, "loader": loader},
        "versions_checked": len(versions_payload),
        "matching_versions": len(matching),
        "version": _version_record(chosen) if chosen else None,
        "newest_release": None
        if newest_release is None
        else {
            "version_number": newest_release.get("version_number"),
            "date_published": newest_release.get("date_published"),
        },
    }


def _candidate_slugs(text: str) -> list:
    seen = set()
    slugs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for marker in ("\t#", " #"):
            index = line.find(marker)
            if index != -1:
                line = line[:index].strip()
        if not line:
            continue
        token = None
        for part in line.replace("\t", " ").split(" "):
            candidate = part.strip("()[]<>,;\"'")
            if candidate and _SLUG_RE.match(candidate):
                token = candidate
                break
        if token is None:
            token = re.sub(r"[^a-z0-9._-]+", "-", line.lower()).strip("-")
        if token and token not in seen:
            seen.add(token)
            slugs.append(token)
    return slugs


def _cell(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _date(value) -> str:
    return (value or "")[:10]


def _build_cell(row) -> str:
    version = row.get("version")
    if not row.get("project"):
        return "—"
    if not version:
        return "none"
    return f"{version.get('version_number')} ({_date(version.get('date_published'))})"


def _deps_cell(row) -> str:
    version = row.get("version")
    if not version:
        return "—"
    deps = version.get("required_dependencies") or []
    if not deps:
        return "none"
    return ", ".join(str(dep.get("project_id") or "unknown") for dep in deps)


def _maintenance_cell(row) -> str:
    version = row.get("version")
    if not version:
        return "—"
    release = row.get("newest_release")
    parts = []
    if release:
        parts.append(f"release {_date(release.get('date_published'))}")
    else:
        parts.append("no release")
    build = f"{version.get('version_type')} {_date(version.get('date_published'))}"
    if build not in parts:
        parts.append(build)
    return "; ".join(parts)


def _side_cell(project) -> str:
    if not project:
        return "—"
    return f"client {project.get('client_side')}, server {project.get('server_side')}"


def _status_cell(row) -> str:
    if row.get("status") == "error":
        return f"error: {row.get('detail') or 'unknown'}"
    return row.get("status") or "unknown"


def _write_report(path: Path, rows, version: str, loader: str) -> None:
    ensure_dir(path.parent)
    lines = [
        f"# Mod matrix: {version} / {loader}",
        "",
        f"{len(rows)} candidates checked.",
        "",
        "| Candidate | Build | Required dependencies | Maintenance | Side | License | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        project = row.get("project") or {}
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    row.get("slug"),
                    _build_cell(row),
                    _deps_cell(row),
                    _maintenance_cell(row),
                    _side_cell(project),
                    project.get("license"),
                    _status_cell(row),
                )
            )
            + " |"
        )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def matrix(
    root,
    candidates: str = "candidates.txt",
    refresh: bool = False,
    *,
    version: str = DEFAULT_VERSION,
    loader: str = DEFAULT_LOADER,
    offline: bool = False,
    report: str | None = None,
) -> dict:
    root = Path(root)
    path = Path(candidates)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise ModsError(f"candidates file not found: {path}")
    slugs = _candidate_slugs(path.read_text(encoding="utf-8"))
    if not slugs:
        raise ModsError(f"no candidates in {path}")

    rows = []
    statuses = {"ok": 0, "no_build": 0, "error": 0}
    for slug in slugs:
        try:
            resolved = resolve(
                root,
                slug,
                version,
                loader,
                offline=offline,
                refresh=refresh,
            )
        except NotFound:
            rows.append(
                {
                    "slug": slug,
                    "status": "error",
                    "detail": "not found on Modrinth",
                    "project": None,
                    "version": None,
                    "newest_release": None,
                }
            )
            statuses["error"] += 1
            continue
        except ModsError as exc:
            rows.append(
                {
                    "slug": slug,
                    "status": "error",
                    "detail": str(exc),
                    "project": None,
                    "version": None,
                    "newest_release": None,
                }
            )
            statuses["error"] += 1
            continue
        statuses[resolved["status"]] += 1
        rows.append(
            {
                "slug": resolved["project"]["slug"] or slug,
                "status": resolved["status"],
                "detail": None,
                "project": resolved["project"],
                "version": resolved["version"],
                "newest_release": resolved["newest_release"],
            }
        )

    if report:
        report_path = Path(report)
        if not report_path.is_absolute():
            report_path = root / report_path
    else:
        report_path = root / "reports" / REPORT_NAME
    _write_report(report_path, rows, version, loader)
    return {
        "candidates": len(rows),
        "report": str(report_path),
        "statuses": statuses,
    }
