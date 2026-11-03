"""Expand the declared pack manifest into milestones and audit the result.

``pack_manifest.json`` is the only hand-maintained pack declaration: which
verdict classes ship in milestone A, which sections are promoted wholesale, which
candidates are deliberately deferred, and the invariants the declaration must
satisfy. This module expands that policy over ``candidates.txt`` and the pack
assessment, walks the required-dependency closure to a fixpoint, and renders two
derived artefacts from the same expansion:

* ``reports/pack_report.md`` -- the machine-checked audit.
* ``PACK.md`` -- the declared pack, so the prose cannot drift from the checks.

A lint failure is a defect in the declaration (a milestone A candidate with no
build, a required dependency outside the pool, a fit host left out, a required
section with no content), not cosmetic drift.
"""

from __future__ import annotations

from collections import Counter, deque
from pathlib import Path

from . import mods
from . import pack as pack_mod
from .util import ensure_dir, read_json

MANIFEST_NAME = "pack_manifest.json"
REPORT_NAME = "reports/pack_report.md"
DOC_NAME = "PACK.md"
RULES_NAME = "fit_rules.json"

# Ordered: the report lists milestones strongest first.
_MILESTONES = ("A", "B", "T", "optional", "excluded")

# Ordered: a verdict class maps to exactly one milestone bucket. Every verdict
# the assessment can emit must appear in one of these lists; `audit` fails when a
# new verdict class appears unmapped rather than silently dropping the row.
_VERDICT_CLASSES = (
    ("include_verdicts", "A"),
    ("milestone_b_verdicts", "B"),
    ("transitive_verdicts", "T"),
    ("optional_verdicts", "optional"),
    ("exclude_verdicts", "excluded"),
)


class PackError(ValueError):
    """The pack manifest is missing, malformed or internally inconsistent."""


def _path(root, path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else Path(root) / target


def load_manifest(root, path: str = MANIFEST_NAME) -> dict:
    """Read and shape-check the pack manifest, failing loudly on a bad one."""
    target = _path(root, path)
    payload = read_json(target, None)
    if not isinstance(payload, dict):
        raise PackError(f"pack manifest not found or not a JSON object: {target}")
    if not isinstance(payload.get("version"), int):
        raise PackError(f"{target}: missing integer 'version'")
    if not isinstance(payload.get("policy"), dict):
        raise PackError(f"{target}: missing 'policy' object")
    if not isinstance(payload.get("target"), dict):
        raise PackError(f"{target}: missing 'target' object")
    return payload


def _overrides(manifest) -> dict:
    entries: dict[str, dict] = {}
    for raw in manifest.get("overrides") or []:
        if isinstance(raw, dict) and raw.get("slug"):
            entries[str(raw["slug"])] = raw
    return entries


def _dep_slugs(row) -> list[str]:
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


def _verdict_milestone(verdict: str, policy: dict):
    for key, milestone in _VERDICT_CLASSES:
        if verdict in (policy.get(key) or []):
            return milestone
    return None


def _verdict_label(entry) -> str:
    """Render the verdict together with why the row landed in its milestone.

    A promoted section ships its trial and defer rows whole, so a milestone A
    table that printed the raw verdict would read ``defer`` for a mod that is
    actually in the release. The suffix makes the disposition explicit without
    changing the assessment vocabulary.
    """
    verdict = str(entry.get("verdict"))
    reason = str(entry.get("reason") or "")
    if reason.startswith("section promoted"):
        return f"{verdict} (promoted)"
    if reason.startswith("policy exclusion"):
        return f"{verdict} (excluded)"
    if not reason.startswith("verdict:"):
        return f"{verdict} (override)"
    return verdict


def expand(manifest: dict, rows) -> list[dict]:
    """Turn the policy plus the scored rows into one entry per candidate."""
    policy = manifest.get("policy") or {}
    promoted = {str(name) for name in policy.get("promote_sections") or []}
    exclusions = policy.get("exclusions") or {}
    overrides = _overrides(manifest)
    entries: list[dict] = []
    for row in rows:
        slug = str(row["slug"])
        verdict = str(row["verdict"])
        project = row.get("project") or {}
        milestone = _verdict_milestone(verdict, policy)
        reason = f"verdict: {verdict}"
        if milestone in ("B", "T", "optional") and row["group"] in promoted:
            milestone = "A"
            reason = f"section promoted ({row['group']}); verdict: {verdict}"
        if slug in exclusions:
            milestone = "excluded"
            reason = f"policy exclusion: {exclusions[slug]}"
        override = overrides.get(slug)
        if override:
            milestone = str(override.get("milestone") or milestone)
            reason = str(override.get("reason") or reason)
        entries.append(
            {
                "slug": slug,
                "section": str(row["group"]),
                "role": row.get("role"),
                "verdict": verdict,
                "status": row.get("status"),
                "milestone": milestone,
                "reason": reason,
                "project_id": project.get("id"),
                "licence": project.get("license"),
                "client_side": project.get("client_side"),
                "server_side": project.get("server_side"),
                "required": _dep_slugs(row),
                "unresolved": _unresolved_ids(row),
            }
        )
    return entries


def closure(entries) -> dict:
    """Walk every required dependency reachable from milestone A.

    A dependency that is a candidate is followed further, so a library three
    links down is caught even though the candidate declares only its direct
    requirement. A dependency that is not a candidate is recorded under
    ``missing``: the pack would need content the survey never vetted.
    """
    by_slug = {entry["slug"]: entry for entry in entries}
    from_a = sorted(entry["slug"] for entry in entries if entry["milestone"] == "A")
    pulled_by: dict[str, set] = {}
    missing: dict[str, set] = {}
    unresolved: dict[str, set] = {}
    seen = set(from_a)
    queue = deque(from_a)
    while queue:
        slug = queue.popleft()
        entry = by_slug.get(slug)
        if entry is None:
            continue
        for dep in entry["required"]:
            pulled_by.setdefault(dep, set()).add(slug)
            if dep in seen:
                continue
            target = by_slug.get(dep)
            if target is None:
                missing.setdefault(dep, set()).add(slug)
                continue
            seen.add(dep)
            queue.append(dep)
        for project_id in entry["unresolved"]:
            unresolved.setdefault(project_id, set()).add(slug)
    return {
        "from_a": from_a,
        "carried": sorted(seen - set(from_a)),
        "pulled_by": pulled_by,
        "missing": missing,
        "unresolved": unresolved,
        "by_slug": by_slug,
    }


def _fit_hosts(root, rules: str = RULES_NAME) -> list[str]:
    """Every candidate slug a fit rule names, in first-seen order."""
    payload = read_json(_path(root, rules), {})
    hosts: list[str] = []
    if not isinstance(payload, dict):
        return hosts
    for rule in payload.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        for slug in rule.get("candidate_mods") or []:
            if str(slug) not in hosts:
                hosts.append(str(slug))
    return hosts


def audit(manifest, rows, entries, walk, root, version: str, loader: str, *, rules=RULES_NAME) -> list[dict]:
    """Return one check per invariant the declaration must satisfy."""
    policy = manifest.get("policy") or {}
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    target = manifest.get("target") or {}
    declared = (str(target.get("minecraft") or ""), str(target.get("loader") or ""))
    add(
        "target matches the gate",
        declared == (version, loader),
        f"{version} / {loader}"
        if declared == (version, loader)
        else f"manifest declares {declared[0]}/{declared[1]}, gate checked {version}/{loader}",
    )

    known = {str(row["slug"]) for row in rows}
    overrides = _overrides(manifest)
    unknown = sorted(set(overrides) - known)
    add(
        "overrides resolve",
        not unknown,
        ", ".join(unknown) if unknown else f"{len(overrides)} override(s) name a candidate",
    )

    unclassified = sorted({str(entry["verdict"]) for entry in entries if entry["milestone"] is None})
    add(
        "verdicts classified",
        not unclassified,
        ", ".join(unclassified)
        if unclassified
        else f"{len({entry['verdict'] for entry in entries})} verdict class(es) mapped to a milestone",
    )

    included = [entry for entry in entries if entry["milestone"] == "A"]
    no_build = [entry["slug"] for entry in included if entry["status"] != "ok"]
    add(
        "milestone A builds",
        not no_build,
        ", ".join(no_build)
        if no_build
        else f"{len(included)} milestone A candidate(s) resolve ok for {version}/{loader}",
    )

    exclusions = policy.get("exclusions") or {}
    redefined = sorted(entry["slug"] for entry in included if entry["slug"] in exclusions)
    add(
        "policy exclusions hold",
        not redefined,
        ", ".join(redefined)
        if redefined
        else f"{len(exclusions)} exclusion(s) stay out of milestone A",
    )

    carried_broken = [slug for slug in walk["carried"] if walk["by_slug"][slug]["status"] != "ok"]
    add(
        "carried dependencies build",
        not carried_broken,
        ", ".join(carried_broken)
        if carried_broken
        else f"{len(walk['carried'])} carried dependenc(ies) resolve ok",
    )

    carried_excluded = sorted(
        slug for slug in walk["carried"] if walk["by_slug"][slug]["milestone"] == "excluded"
    )
    add(
        "closure avoids exclusions",
        not carried_excluded,
        ", ".join(carried_excluded)
        if carried_excluded
        else "no milestone A dependency resolves to an excluded candidate",
    )

    missing = walk["missing"]
    add(
        "dependency chain inside the pool",
        not missing,
        "; ".join(
            f"{dep} needed by {', '.join(sorted(sources))}" for dep, sources in sorted(missing.items())
        )
        if missing
        else "every reachable required dependency is a candidate",
    )

    host_rows = {str(row["slug"]): row for row in rows}
    hosts = [host for host in _fit_hosts(root, rules) if host_rows.get(host, {}).get("status") == "ok"]
    # A fit host satisfies the rule whether it ships explicitly in milestone A or
    # is pulled in as a required dependency of one: both install the host. The
    # property the rules need is "the mod is present", not "the mod is declared".
    shipped = {entry["slug"] for entry in included} | set(walk["carried"])
    absent = [host for host in hosts if host not in shipped]
    add(
        "fit hosts ship",
        not absent,
        ", ".join(absent)
        if absent
        else (
            f"all {len(hosts)} resolvable fit host(s) ship in milestone A "
            "or transitively"
        ),
    )

    sections = Counter(entry["section"] for entry in included)
    required = [str(name) for name in manifest.get("required_sections") or []]
    empty = [name for name in required if not sections.get(name)]
    add(
        "required sections populated",
        not empty,
        ", ".join(empty)
        if empty
        else f"{len(required)} required section(s) carry at least one milestone A candidate",
    )

    budget = (manifest.get("budgets") or {}).get("milestone_a")
    if isinstance(budget, int):
        add("milestone A budget", len(included) <= budget, f"{len(included)}/{budget} candidates")
    else:
        add("milestone A budget", False, "manifest declares no integer budgets.milestone_a")

    client_only_ok = {str(slug) for slug in policy.get("client_only_ok") or []}
    client_only = sorted(
        entry["slug"]
        for entry in included
        if entry["server_side"] == "unsupported" and entry["slug"] not in client_only_ok
    )
    add(
        "milestone A is server-usable",
        not client_only,
        ", ".join(client_only)
        if client_only
        else "no milestone A candidate is client-only",
    )
    return checks


def _table(header, rows) -> list[str]:
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(mods._cell(value) for value in row) + " |")
    return lines


def _by_section(entries, milestone) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for entry in entries:
        if entry["milestone"] == milestone:
            grouped.setdefault(entry["section"], []).append(entry["slug"])
    return {name: sorted(slugs) for name, slugs in grouped.items()}


def _write_report(
    path: Path,
    *,
    version: str,
    loader: str,
    manifest: dict,
    entries,
    walk,
    checks,
) -> None:
    ensure_dir(path.parent)
    counts = Counter(str(entry["milestone"]) for entry in entries)
    failed = [check for check in checks if check["status"] != "pass"]
    lines = [
        f"# Pack lint: {version} / {loader}",
        "",
        f"Result: {'PASS' if not failed else 'FAIL'} — {len(checks) - len(failed)}/{len(checks)} "
        f"checks pass. {len(entries)} candidates expanded from `{MANIFEST_NAME}`.",
        "",
        f"Milestones: A {counts.get('A', 0)} · B {counts.get('B', 0)} · "
        f"T {counts.get('T', 0)} (declared transitive; {len(walk['carried'])} carried into "
        f"milestone A) · optional {counts.get('optional', 0)} · "
        f"excluded {counts.get('excluded', 0)} · unclassified {counts.get('None', 0)}.",
        "",
        "Generated by `chaoslab lint` from cached Modrinth responses and "
        f"`{MANIFEST_NAME}`. The manifest is the declaration; this report is the audit of it.",
        "",
        "## Checks",
        "",
    ]
    lines += _table(
        ["Check", "Status", "Detail"],
        [[check["name"], check["status"], check["detail"]] for check in checks],
    )
    lines += ["", "## Milestone A", ""]
    table = [
        [
            entry["section"],
            entry["slug"],
            entry["project_id"],
            entry["role"],
            _verdict_label(entry),
            entry["server_side"],
            entry["licence"],
            entry["reason"],
        ]
        for entry in sorted(
            (entry for entry in entries if entry["milestone"] == "A"),
            key=lambda entry: (entry["section"], entry["slug"]),
        )
    ]
    lines += _table(
        ["Section", "Candidate", "Project ID", "Role", "Verdict", "Server side", "Licence", "Why"],
        table,
    )
    lines += ["", "## Carried transitively", ""]
    if walk["carried"]:
        lines += _table(
            ["Candidate", "Section", "Declared milestone", "Pulled by", "Build"],
            [
                [
                    slug,
                    walk["by_slug"][slug]["section"],
                    walk["by_slug"][slug]["milestone"],
                    ", ".join(sorted(walk["pulled_by"].get(slug, ()))),
                    walk["by_slug"][slug]["status"],
                ]
                for slug in walk["carried"]
            ],
        )
        lines.append("")
        lines.append(
            "These are required dependencies of a milestone A candidate, so they ship even "
            "though the declaration puts them at a later milestone; they are the subset of "
            "milestone T reachable from A. Milestone A has no unresolved link when this "
            "table is the whole closure."
        )
    else:
        lines.append("None: milestone A closes over itself.")

    lines += ["", "## Milestone T (declared transitive)", ""]
    transitive = _by_section(entries, "T")
    if transitive:
        lines.append(
            "Libraries and dependencies the declaration defers to a later milestone. The "
            "carried table above lists only the subset reachable from milestone A; rows "
            "that appear here and not there are deferred in full."
        )
        lines.append("")
        lines += _table(
            ["Section", "Count", "Candidates"],
            [[name, len(slugs), ", ".join(slugs)] for name, slugs in sorted(transitive.items())],
        )
    else:
        lines.append("None.")

    lines += ["", "## Milestone B (deferred)", ""]
    deferred = _by_section(entries, "B")
    if deferred:
        lines += _table(
            ["Section", "Count", "Candidates"],
            [[name, len(slugs), ", ".join(slugs)] for name, slugs in sorted(deferred.items())],
        )
    else:
        lines.append("None.")

    lines += ["", "## Optional / client-only", ""]
    optional = _by_section(entries, "optional")
    if optional:
        lines += _table(
            ["Section", "Count", "Candidates"],
            [[name, len(slugs), ", ".join(slugs)] for name, slugs in sorted(optional.items())],
        )
    else:
        lines.append("None.")

    lines += ["", "## Excluded", ""]
    excluded = [entry for entry in entries if entry["milestone"] == "excluded"]
    if excluded:
        lines += _table(
            ["Candidate", "Section", "Reason"],
            [[entry["slug"], entry["section"], entry["reason"]] for entry in excluded],
        )
    else:
        lines.append("None.")

    lines += ["", "## Unresolved dependency project IDs", ""]
    if walk["unresolved"]:
        for project_id, sources in sorted(walk["unresolved"].items()):
            lines.append(f"- `{project_id}` declared by {', '.join(sorted(sources))}")
        lines += [
            "",
            "A project ID Modrinth cannot resolve cannot be installed or inspected, so it is "
            "recorded as incomplete metadata rather than proof that the candidate is unusable "
            "(PROJECT_PLAN.md §9).",
        ]
    else:
        lines.append("None.")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_doc(
    path: Path,
    *,
    version: str,
    loader: str,
    manifest: dict,
    entries,
    walk,
    checks,
) -> None:
    ensure_dir(path.parent)
    failed = [check for check in checks if check["status"] != "pass"]
    included = [entry for entry in entries if entry["milestone"] == "A"]
    roles = Counter(str(entry["role"]) for entry in included)
    lines = [
        "# Pack declaration",
        "",
        f"Target: Minecraft {version} / {loader}. Sourcing: Modrinth only. Delivery: "
        "`.mrpack` referencing Modrinth CDN URLs; jars are not bundled.",
        "",
        "Generated from `pack_manifest.json` by `chaoslab lint`. Edit the manifest, not this "
        "file: the manifest is the declaration and this document plus "
        "`reports/pack_report.md` are rendered from it, so the prose cannot drift from what "
        "the gate checks.",
        "",
        "## Decisions applied",
        "",
    ]
    for key, value in sorted((manifest.get("decisions") or {}).items()):
        lines.append(f"- **{key}** — {value}")
    lines += [
        "",
        "## Milestone A",
        "",
        f"{len(included)} candidates"
        + (f" ({', '.join(f'{role} {count}' for role, count in sorted(roles.items()))})" if roles else "")
        + ", the release target.",
        "",
    ]
    lines += _table(
        ["Section", "Candidate", "Role", "Verdict", "Server side", "Why"],
        [
            [
                entry["section"],
                entry["slug"],
                entry["role"],
                _verdict_label(entry),
                entry["server_side"],
                entry["reason"],
            ]
            for entry in sorted(included, key=lambda entry: (entry["section"], entry["slug"]))
        ],
    )
    lines += ["", "## Carried transitively", ""]
    if walk["carried"]:
        for slug in walk["carried"]:
            entry = walk["by_slug"][slug]
            lines.append(
                f"- `{slug}` ({entry['role']}, declared {entry['milestone']}) — required by "
                f"{', '.join(sorted(walk['pulled_by'].get(slug, ())))}"
            )
    else:
        lines.append("None.")
    lines += ["", "## Deferred to milestone B", ""]
    deferred = _by_section(entries, "B")
    if deferred:
        for name, slugs in sorted(deferred.items()):
            lines.append(f"- **{name}** ({len(slugs)}): {', '.join(slugs)}")
    else:
        lines.append("None.")
    lines += ["", "## Excluded", ""]
    excluded = [entry for entry in entries if entry["milestone"] == "excluded"]
    if excluded:
        for entry in excluded:
            lines.append(f"- `{entry['slug']}` — {entry['reason']}")
    else:
        lines.append("None.")
    lines += ["", "## Gate", "", f"{len(checks) - len(failed)}/{len(checks)} lint checks pass."]
    if failed:
        lines.append("")
        for check in failed:
            lines.append(f"- FAIL {check['name']}: {check['detail']}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(
    root,
    *,
    manifest: str = MANIFEST_NAME,
    report: str = REPORT_NAME,
    doc: str = DOC_NAME,
    rules: str = RULES_NAME,
    version: str = mods.DEFAULT_VERSION,
    loader: str = mods.DEFAULT_LOADER,
    offline: bool = False,
    refresh: bool = False,
    rows=None,
) -> dict:
    """Expand the manifest, audit the closure and write both derived artefacts."""
    root = Path(root)
    payload = load_manifest(root, manifest)
    if rows is None:
        rows = pack_mod.run(
            root,
            version=version,
            loader=loader,
            offline=offline,
            refresh=refresh,
            rules=rules,
            report="reports/pack_assessment.md",
        )["rows"]
    entries = expand(payload, rows)
    walk = closure(entries)
    checks = audit(payload, rows, entries, walk, root, version, loader, rules=rules)
    failed = [check for check in checks if check["status"] != "pass"]
    report_path = _path(root, report)
    doc_path = _path(root, doc)
    _write_report(
        report_path,
        version=version,
        loader=loader,
        manifest=payload,
        entries=entries,
        walk=walk,
        checks=checks,
    )
    _write_doc(
        doc_path,
        version=version,
        loader=loader,
        manifest=payload,
        entries=entries,
        walk=walk,
        checks=checks,
    )
    return {
        "ok": not failed,
        "entries": len(entries),
        "milestones": dict(Counter(str(entry["milestone"]) for entry in entries)),
        "carried": len(walk["carried"]),
        "checks": checks,
        "entries": len(entries),
        "entry_rows": entries,
        "walk": walk,
        "report": str(report_path),
        "doc": str(doc_path),
    }
