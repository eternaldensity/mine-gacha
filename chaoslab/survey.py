"""Build the grouped mod survey report.

``mods matrix`` answers one question per slug: does it build for the target
version? A survey needs more than that. Candidates are grouped by intent, the
required dependencies are resolved from opaque project IDs to readable slugs,
and add-on / compatibility layers are carried alongside the content mods they
belong to.

The dependency audit is the second half: a resolved build is not usable if it
requires a project that is not in the candidate pool. Every candidate therefore
gets a verdict -- inside the pool, needs outside content, or has an unresolved
dependency -- so the pack decision is made from evidence, not from a flat matrix.

Section convention in the candidate file: a comment line ``# == Name`` starts a
group, and every slug below it belongs to that group until the next heading.
Lines that are not comments and do not start with ``#`` are candidate slugs,
optionally followed by ``| display name``.
"""

from __future__ import annotations

import re
from collections import Counter, deque
from pathlib import Path

from . import mods
from .util import ensure_dir

REPORT_NAME = "mods_survey.md"

_GROUP_RE = re.compile(r"^#\s*==\s*(?P<name>.+?)\s*$")


def parse_candidates(path: Path) -> list[tuple[str, str]]:
    """Return ``(group, slug)`` pairs in file order, de-duplicated by slug."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    group = "Ungrouped"
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        heading = _GROUP_RE.match(line)
        if heading:
            group = heading.group("name")
            continue
        if not line or line.startswith("#"):
            continue
        for slug in mods._candidate_slugs(line):
            if slug in seen:
                continue
            seen.add(slug)
            pairs.append((group, slug))
    return pairs


def _section_kind(group: str) -> str:
    """Classify a section as content, add-on or compatibility glue."""
    lowered = (group or "").lower()
    if "add-on" in lowered or "addon" in lowered:
        return "add-on"
    if "compat" in lowered:
        return "compatibility"
    if "librar" in lowered or "dependenc" in lowered:
        return "library"
    return "content"


def _dependency_records(root, dependencies, *, offline: bool, refresh: bool) -> list[dict]:
    """Resolve required-dependency project IDs, keeping the ID on failure."""
    records: list[dict] = []
    for dependency in dependencies:
        project_id = dependency.get("project_id")
        record = {
            "project_id": str(project_id) if project_id else None,
            "slug": None,
            "file_name": dependency.get("file_name"),
        }
        if project_id:
            try:
                payload = mods._get_json(
                    root,
                    mods._project_rel(str(project_id)),
                    mods._project_url(str(project_id)),
                    offline=offline,
                    refresh=refresh,
                )
            except mods.ModsError:
                payload = None
            if isinstance(payload, dict):
                record["slug"] = payload.get("slug")
        records.append(record)
    return records


def _labels_from_records(records) -> list[str]:
    labels: list[str] = []
    for record in records:
        slug = record.get("slug")
        project_id = record.get("project_id")
        if slug:
            labels.append(str(slug))
        elif project_id:
            labels.append(f"{project_id} (unresolved)")
        else:
            labels.append(record.get("file_name") or "unknown")
    return labels


def _dependency_labels(root, dependencies, *, offline: bool, refresh: bool) -> list[str]:
    """Resolve required-dependency project IDs to slugs, keeping IDs on failure."""
    return _labels_from_records(
        _dependency_records(root, dependencies, offline=offline, refresh=refresh)
    )


def _resolved_slugs(row) -> list[str]:
    records = row.get("dependency_records") or []
    return sorted({str(record["slug"]) for record in records if record.get("slug")})


def _unresolved_ids(row) -> list[str]:
    records = row.get("dependency_records") or []
    return sorted(
        {
            str(record["project_id"])
            for record in records
            if record.get("project_id") and not record.get("slug")
        }
    )


def _deps_cell(row) -> str:
    labels = row.get("dependencies") or []
    return ", ".join(labels) if labels else "none"


def _build_cell(row) -> str:
    if not row.get("project"):
        return "—"
    version = row.get("version")
    if not version:
        return "none"
    return f"{version.get('version_number')} ({mods._date(version.get('date_published'))})"


def _side_cell(row) -> str:
    project = row.get("project")
    if not project:
        return "—"
    return f"client {project.get('client_side')}, server {project.get('server_side')}"


def _status_cell(row) -> str:
    if row.get("status") == "error":
        return f"error: {row.get('detail') or 'unknown'}"
    return row.get("status") or "unknown"


def _table(rows) -> list[str]:
    lines = [
        "| Candidate | Build | Required dependencies | Maintenance | Side | License | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        project = row.get("project") or {}
        lines.append(
            "| "
            + " | ".join(
                mods._cell(value)
                for value in (
                    row.get("slug"),
                    _build_cell(row),
                    _deps_cell(row),
                    mods._maintenance_cell(row),
                    _side_cell(row),
                    project.get("license"),
                    _status_cell(row),
                )
            )
            + " |"
        )
    return lines


def _node_record(slug, status, detail, project, dependency_records) -> dict:
    """One node in the dependency graph: a candidate or a project it pulls in."""
    required = sorted(
        {str(record["slug"]) for record in dependency_records if record.get("slug")}
    )
    unresolved = sorted(
        {
            str(record["project_id"])
            for record in dependency_records
            if record.get("project_id") and not record.get("slug")
        }
    )
    return {
        "slug": slug,
        "status": status,
        "detail": detail,
        "project": project,
        "required": required,
        "unresolved": unresolved,
    }


def _resolve_node(root, slug, *, version, loader, offline, refresh) -> dict:
    """Resolve a non-candidate dependency so its own requirements are visible."""
    try:
        resolved = mods.resolve(
            root, slug, version, loader, offline=offline, refresh=refresh
        )
    except mods.NotFound:
        return _node_record(slug, "error", "not found on Modrinth", None, [])
    except mods.ModsError as exc:
        return _node_record(slug, "error", str(exc), None, [])
    version_record = resolved.get("version") or {}
    records = _dependency_records(
        root,
        version_record.get("required_dependencies") or [],
        offline=offline,
        refresh=refresh,
    )
    return _node_record(
        str(resolved["project"].get("slug") or slug),
        resolved["status"],
        None,
        resolved.get("project"),
        records,
    )


def _dependency_graph(root, rows, *, version, loader, offline, refresh) -> dict:
    """Resolve every candidate's dependency chain to a fixpoint.

    A one-hop audit cannot see that ``a`` requires ``b`` and ``b`` has no build,
    or that a library three links down is not in the pool. Each node records its
    own verdict plus the required slugs it points at; the graph is walked from
    every candidate so those cases surface as a chain rather than a flat row.
    """
    graph: dict[str, dict] = {}
    for row in rows:
        slug = row.get("slug")
        if not slug:
            continue
        graph[str(slug)] = _node_record(
            str(slug),
            row.get("status"),
            row.get("detail"),
            row.get("project"),
            row.get("dependency_records") or [],
        )

    def ensure(slug: str) -> dict:
        node = graph.get(slug)
        if node is not None:
            return node
        node = _resolve_node(
            root, slug, version=version, loader=loader, offline=offline, refresh=refresh
        )
        graph[slug] = node
        if node["slug"] and node["slug"] not in graph:
            graph[node["slug"]] = node
        return node

    queue = deque(graph)
    processed: set[str] = set()
    while queue:
        slug = queue.popleft()
        if slug in processed:
            continue
        processed.add(slug)
        node = graph.get(slug) or ensure(slug)
        for dependency in node["required"]:
            if dependency not in graph:
                ensure(dependency)
            if dependency not in processed:
                queue.append(dependency)
    return graph


def _is_library(node) -> bool:
    project = node.get("project") if node else None
    if not project:
        return False
    return "library" in (project.get("categories") or [])


def _walk(slug, graph, pool) -> dict:
    """Return every transitive issue and outside link reachable from ``slug``."""
    issues: list[dict] = []
    outside: dict[str, tuple] = {}
    stack = [(slug, (slug,))]
    while stack:
        current, path = stack.pop()
        node = graph.get(current)
        if node is None:
            issues.append(
                {
                    "kind": "undecidable",
                    "chain": path,
                    "detail": f"{current}: no record",
                }
            )
            continue
        if current != slug:
            if node["status"] == "no_build":
                issues.append(
                    {
                        "kind": "dependency-no-build",
                        "chain": path,
                        "detail": node.get("detail") or "no matching build",
                    }
                )
            elif node["status"] == "error":
                issues.append(
                    {
                        "kind": "undecidable",
                        "chain": path,
                        "detail": node.get("detail") or "unresolved",
                    }
                )
        for project_id in node["unresolved"]:
            issues.append(
                {"kind": "unresolved-id", "chain": path, "detail": project_id}
            )
        for dependency in node["required"]:
            if dependency in path:
                continue
            chain = path + (dependency,)
            if dependency not in pool:
                previous = outside.get(dependency)
                if previous is None or len(chain) < len(previous):
                    outside[dependency] = chain
            stack.append((dependency, chain))
    return {"issues": issues, "outside": outside}


def _chain_text(chain) -> str:
    return " -> ".join(str(link) for link in chain)


def _audit_row(row, candidate_slugs: set[str], graph) -> dict:
    """Return one per-candidate compatibility verdict over the whole chain."""
    slug = str(row.get("slug"))
    kind = _section_kind(row["group"])
    walk = _walk(slug, graph, candidate_slugs)
    issues = walk["issues"]
    outside = walk["outside"]
    node = graph.get(slug) or {}

    dep_no_build = [issue for issue in issues if issue["kind"] == "dependency-no-build"]
    # A required-dependency *project ID* that Modrinth cannot resolve (404) is a
    # metadata defect, not evidence that the candidate is unusable: the ID cannot
    # be installed or inspected, so it cannot make a buildable candidate
    # undecidable. It is reported on the row instead of deciding the verdict.
    unresolved_ids = sorted(
        {issue["detail"] for issue in issues if issue["kind"] == "unresolved-id"}
    )
    undecidable = [issue for issue in issues if issue["kind"] == "undecidable"]
    outside_content = {
        dep: chain for dep, chain in outside.items() if not _is_library(graph.get(dep))
    }
    outside_library = {
        dep: chain for dep, chain in outside.items() if _is_library(graph.get(dep))
    }

    if row.get("status") != "ok":
        key = "unusable"
        verdict = f"unusable: {_status_cell(row)}"
    elif dep_no_build:
        key = "unusable"
        issue = sorted(dep_no_build, key=lambda item: len(item["chain"]))[0]
        verdict = (
            "unusable: dependency has no build ("
            + _chain_text(issue["chain"])
            + ")"
        )
    elif undecidable:
        key = "undecidable"
        issue = sorted(undecidable, key=lambda item: len(item["chain"]))[0]
        verdict = (
            "undecidable: "
            + issue["detail"]
            + " ("
            + _chain_text(issue["chain"])
            + ")"
        )
    elif outside_content and kind == "add-on":
        key = "outside-content"
        verdict = "add-on needs outside content: " + ", ".join(sorted(outside_content))
    elif outside_content:
        key = "outside-content" if kind == "library" else "outside-dependency"
        label = "library" if kind == "library" else "hard dependency"
        verdict = f"{label} outside candidates: " + ", ".join(sorted(outside_content))
    elif outside_library:
        key = "outside-dependency"
        verdict = "needs outside libraries (add transitively): " + ", ".join(
            sorted(outside_library)
        )
    elif node.get("required"):
        key = "inside"
        verdict = "ok: every required dependency is a buildable candidate"
    else:
        key = "no-deps"
        verdict = "ok: no required dependencies"
    if unresolved_ids:
        verdict += "; unresolved dependency id " + ", ".join(unresolved_ids)

    return {
        "slug": slug,
        "group": row["group"],
        "kind": kind,
        "dependencies": node.get("required") or [],
        "outside": [
            {"slug": dep, "chain": chain, "library": dep not in outside_content}
            for dep, chain in sorted(outside.items())
        ],
        "unresolved": sorted(
            {issue["detail"] for issue in issues if issue["kind"] == "unresolved-id"}
        ),
        "issues": issues,
        "verdict": verdict,
        "key": key,
    }


def _audit(rows, candidate_slugs: set[str], graph) -> tuple[list[dict], Counter]:
    entries = []
    counts: Counter = Counter()
    for row in rows:
        entry = _audit_row(row, candidate_slugs, graph)
        counts[entry["key"]] += 1
        entries.append(entry)
    return entries, counts


def _write_report(
    path: Path,
    rows,
    version: str,
    loader: str,
    *,
    root,
    offline: bool,
    refresh: bool,
) -> Counter:
    ensure_dir(path.parent)
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row["group"], []).append(row)
    counts = Counter(row["status"] for row in rows)
    candidate_slugs = {row["slug"] for row in rows}
    graph = _dependency_graph(
        root, rows, version=version, loader=loader, offline=offline, refresh=refresh
    )
    audit, audit_counts = _audit(rows, candidate_slugs, graph)
    content_links = {
        link["slug"]: link
        for entry in audit
        for link in entry["outside"]
        if not link["library"]
    }
    library_links = {
        link["slug"]: link
        for entry in audit
        for link in entry["outside"]
        if link["library"]
    }
    unresolved_entries = [entry for entry in audit if entry["unresolved"]]

    lines = [
        f"# Mod survey: {version} / {loader}",
        "",
        f"{len(rows)} candidates in {len(groups)} sections. "
        f"ok: {counts.get('ok', 0)}, no_build: {counts.get('no_build', 0)}, "
        f"error: {counts.get('error', 0)}.",
        "",
        "Generated by `chaoslab survey` from cached Modrinth v2 responses; rerun with "
        "`--refresh` for current data. Required dependencies are resolved to project "
        "slugs, so a library that a candidate needs is visible rather than an opaque ID.",
        "",
        f"Dependency audit (transitive): {audit_counts.get('inside', 0)} candidates have every "
        f"required dependency inside the pool and buildable; {audit_counts.get('no-deps', 0)} "
        f"declare no required dependencies; {audit_counts.get('unusable', 0)} are unusable "
        f"because the candidate or a dependency has no build; {audit_counts.get('outside-content', 0)} "
        f"need content outside the pool ({len(content_links)} distinct links); "
        f"{audit_counts.get('outside-dependency', 0)} need only outside libraries "
        f"({len(library_links)} distinct links); and {audit_counts.get('undecidable', 0)} are "
        f"undecidable because a dependency ID cannot be resolved (Modrinth 404 or no cached response).",
        "",
    ]
    if unresolved_entries:
        lines += [
            f"{len(unresolved_entries)} candidate(s) name a required-dependency project ID that "
            "Modrinth cannot resolve (404). The ID cannot be installed or inspected, so it does "
            "not decide the verdict; it is listed on the audit row instead. The candidate's "
            "dependency metadata is incomplete, not proven broken.",
            "",
        ]
    for group, members in groups.items():
        ok = sum(1 for row in members if row["status"] == "ok")
        lines += [f"## {group}", "", f"{ok}/{len(members)} buildable.", ""]
        lines += _table(members)
        lines.append("")

    unavailable = [row for row in rows if row["status"] != "ok"]
    lines += ["## Unavailable or failing candidates", ""]
    if unavailable:
        lines += [
            "| Candidate | Section | Status |",
            "| --- | --- | --- |",
        ]
        for row in unavailable:
            lines.append(
                f"| {mods._cell(row.get('slug'))} | {mods._cell(row['group'])} "
                f"| {mods._cell(_status_cell(row))} |"
            )
    else:
        lines.append("None: every candidate resolved to a build for this target.")
    lines.append("")

    lines += [
        "## Dependency and compatibility audit",
        "",
        "A resolved build is not automatically usable: its dependency chain may contain a "
        "project with no build, a content mod outside `candidates.txt`, or an ID that cannot "
        "be resolved. Each row below is a decision point, not a failure. `unusable: dependency "
        "has no build` means the chain cannot run as listed; `undecidable` means Modrinth "
        "metadata is incomplete; `needs outside libraries` is expected transitive content.",
        "",
        "| Candidate | Section | Kind | Direct dependencies | Verdict |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in audit:
        lines.append(
            "| "
            + " | ".join(
                mods._cell(value)
                for value in (
                    entry["slug"],
                    entry["group"],
                    entry["kind"],
                    ", ".join(entry["dependencies"]) or "none",
                    entry["verdict"],
                )
            )
            + " |"
        )
    lines.append("")

    required_by: dict[str, set[str]] = {}
    for entry in audit:
        for dependency in entry["dependencies"]:
            required_by.setdefault(dependency, set()).add(str(entry["slug"]))
    load_bearing = sorted(
        ((slug, dependents) for slug, dependents in required_by.items() if slug in candidate_slugs),
        key=lambda item: (-len(item[1]), item[0]),
    )
    lines += ["### Candidates that other candidates require", ""]
    if load_bearing:
        lines += ["| Dependency | Required by | Count |", "| --- | --- | --- |"]
        for slug, dependents in load_bearing:
            lines.append(
                f"| {mods._cell(slug)} | {mods._cell(', '.join(sorted(dependents)))} "
                f"| {len(dependents)} |"
            )
    else:
        lines.append("None: no candidate requires another candidate by project slug.")
    lines.append("")

    lines += ["### Dependencies outside the candidate pool", ""]
    if content_links or library_links:
        lines.append(
            "Reachable required dependencies that are not candidates, with the chain that "
            "pulled them in. Libraries are expected to be added transitively; content is a "
            "scope decision."
        )
        lines.append("")
        if content_links:
            lines += ["Content:", ""]
            for slug, link in sorted(content_links.items()):
                lines.append(f"- `{slug}` via {_chain_text(link['chain'])}")
            lines.append("")
        if library_links:
            lines += ["Libraries:", ""]
            for slug, link in sorted(library_links.items()):
                lines.append(f"- `{slug}` via {_chain_text(link['chain'])}")
            lines.append("")
    else:
        lines.append("None: every reachable required dependency is itself a candidate.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)
    return audit_counts


def run(
    root,
    candidates: str = "candidates.txt",
    *,
    version: str = mods.DEFAULT_VERSION,
    loader: str = mods.DEFAULT_LOADER,
    offline: bool = False,
    refresh: bool = False,
    report: str | None = None,
) -> dict:
    root = Path(root)
    path = Path(candidates)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise mods.ModsError(f"candidates file not found: {path}")
    pairs = parse_candidates(path)
    if not pairs:
        raise mods.ModsError(f"no candidates in {path}")

    rows = []
    statuses = Counter()
    for group, slug in pairs:
        try:
            resolved = mods.resolve(
                root, slug, version, loader, offline=offline, refresh=refresh
            )
        except mods.NotFound:
            rows.append(
                {
                    "group": group,
                    "slug": slug,
                    "status": "error",
                    "detail": "not found on Modrinth",
                    "project": None,
                    "version": None,
                    "newest_release": None,
                    "dependencies": [],
                    "dependency_records": [],
                }
            )
            statuses["error"] += 1
            continue
        except mods.ModsError as exc:
            rows.append(
                {
                    "group": group,
                    "slug": slug,
                    "status": "error",
                    "detail": str(exc),
                    "project": None,
                    "version": None,
                    "newest_release": None,
                    "dependencies": [],
                    "dependency_records": [],
                }
            )
            statuses["error"] += 1
            continue

        version_record = resolved.get("version") or {}
        dependency_records = _dependency_records(
            root,
            version_record.get("required_dependencies") or [],
            offline=offline,
            refresh=refresh,
        )
        statuses[resolved["status"]] += 1
        rows.append(
            {
                "group": group,
                "slug": resolved["project"].get("slug") or slug,
                "status": resolved["status"],
                "detail": None,
                "project": resolved["project"],
                "version": resolved["version"],
                "newest_release": resolved["newest_release"],
                "dependencies": _labels_from_records(dependency_records),
                "dependency_records": dependency_records,
            }
        )

    if report:
        report_path = Path(report)
        if not report_path.is_absolute():
            report_path = root / report_path
    else:
        report_path = root / "reports" / REPORT_NAME
    audit_counts = _write_report(
        report_path,
        rows,
        version,
        loader,
        root=root,
        offline=offline,
        refresh=refresh,
    )
    return {
        "candidates": len(rows),
        "sections": len({row["group"] for row in rows}),
        "report": str(report_path),
        "statuses": dict(statuses),
        "audit": dict(audit_counts),
    }
