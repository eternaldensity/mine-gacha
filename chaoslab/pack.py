"""Assess the candidate pool for pack necessity and suitability.

N4's question is not "does it build" but "does the pack need it". Every candidate
gets a structural role, a necessity score (required by other candidates, named by
the fit rules), a suitability score (build, maintenance, licence, side, adoption)
and a pack verdict. Signals come from cached Modrinth responses, the cached
``.mrpack`` indexes and the survey's own transitive dependency audit, so the
report regenerates offline through ``chaoslab verify``.

This is decision support, not the decision: the role and the raw signal columns
sit next to the verdict so a reader can disagree without losing the evidence.
"""

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path

from . import modpacks as modpacks_mod
from . import mods
from . import survey as survey_mod
from .util import ensure_dir, read_json

REPORT_NAME = "pack_assessment.md"
RULES_NAME = "fit_rules.json"

# Ordered: the report emits roles in this sequence.
_ROLE_ORDER = (
    "core",
    "content",
    "add-on",
    "library",
    "support",
    "compatibility",
    "client-only",
    "design-conflict",
    "unusable",
    "excluded",
)

# Sections from the original candidate list. A candidate here was chosen
# deliberately, so cross-pack adoption is evidence rather than a gate.
_SEED_SECTIONS = (
    "Magic",
    "Tech",
    "Mobs / familiars",
    "Dimensions / worldgen",
    "RPG progression",
    "Gacha-adjacent / randomisation",
    "Endgame / gamebreaking",
    "Support / UI",
    "Add-ons: Ars Nouveau",
    "Add-ons: Iron's Spells",
    "Add-ons: Create / Aeronautics",
    "Add-ons: Apotheosis",
    "Quest systems",
)

# Ordered: the report emits verdicts in this sequence, strongest first.
_VERDICT_ORDER = (
    "include (core)",
    "include (seed)",
    "include (adoption)",
    "include (library)",
    "include (support)",
    "include (add-on)",
    "trial",
    "optional (client-only)",
    "review (unused library)",
    "defer",
    "exclude (dependency)",
    "exclude (design)",
    "excluded (no build)",
)

# Settled decisions that make a nominally buildable candidate wrong for this pack.
# Each entry cites the plan section so the conflict is auditable rather than taste.
_DESIGN_CONFLICTS = {
    "lootr": (
        "§6.12: chests are shared and one-shot; Lootr makes them per-player instanced"
    ),
}

_PERMISSIVE_PREFIXES = (
    "MIT",
    "Apache",
    "BSD",
    "ISC",
    "Unlicense",
    "CC0",
    "Zlib",
    "MPL",
    "OFL",
)

_LICENSE_POINTS = {
    "permissive": 8,
    "copyleft": 6,
    "noncommercial": 4,
    "other": 3,
    "restricted": 2,
    "unknown": 0,
}


def _license_class(value) -> str:
    """Classify a Modrinth licence id for distribution risk, not legal advice."""
    text = str(value or "")
    if not text:
        return "unknown"
    lowered = text.lower()
    if (
        "all-rights-reserved" in lowered
        or "arr" in lowered
        or "protected" in lowered
        or "terms-of-use" in lowered
        or "dont-be-a-jerk" in lowered
    ):
        return "restricted"
    if "-nc" in lowered or "noncommercial" in lowered:
        return "noncommercial"
    if any(text.startswith(prefix) for prefix in _PERMISSIVE_PREFIXES):
        return "permissive"
    if "GPL" in text or "MPL" in text:
        return "copyleft"
    return "other"


def _pack_adoption(root, packs) -> Counter:
    """Count canonical packs shipping each project ID.

    ``data/modpacks/`` also holds smoke-run packs; counting them would let a
    test pack change the assessment, so membership is restricted to the
    canonical set that ``chaoslab modpacks`` surveys.
    """
    counts: Counter = Counter()
    directory = Path(root) / modpacks_mod.PACKS_DIR
    if not directory.is_dir():
        return counts
    allowed = {mods._safe_slug(slug) for slug in packs}
    for path in sorted(directory.glob("*.mrpack")):
        if path.name.split("__", 1)[0] not in allowed:
            continue
        try:
            with zipfile.ZipFile(path) as handle:
                raw = handle.read("modrinth.index.json")
            index = json.loads(raw.decode("utf-8"))
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            continue
        files = index.get("files") if isinstance(index, dict) else None
        if not isinstance(files, list):
            continue
        ids, _unmapped = modpacks_mod._project_ids(files)
        for project_id in sorted({project_id for project_id, _path in ids}):
            counts[project_id] += 1
    return counts


def _project_index(root) -> dict:
    """Map cached Modrinth project ID to slug, using every cached project body."""
    directory = Path(root) / mods.MODS_DIR / "project"
    mapping: dict[str, str] = {}
    if not directory.is_dir():
        return mapping
    for path in sorted(directory.glob("*.json")):
        payload = read_json(path, None)
        body = payload.get("body") if isinstance(payload, dict) else None
        if not isinstance(body, dict):
            continue
        project_id = body.get("id")
        slug = body.get("slug")
        if project_id and slug:
            mapping[str(project_id)] = str(slug)
    return mapping


def _fit_hosts(root, rules: str) -> set[str]:
    payload = read_json(Path(root) / rules, {})
    hosts: set[str] = set()
    if not isinstance(payload, dict):
        return hosts
    for rule in payload.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        for slug in rule.get("candidate_mods") or []:
            hosts.add(str(slug))
    return hosts


def _row(root, group: str, slug: str, version: str, loader: str, *, offline, refresh):
    try:
        resolved = mods.resolve(
            root, slug, version, loader, offline=offline, refresh=refresh
        )
    except mods.NotFound:
        return {
            "group": group,
            "slug": slug,
            "status": "error",
            "detail": "not found on Modrinth",
            "project": None,
            "version": None,
            "newest_release": None,
            "dependency_records": [],
        }
    except mods.ModsError as exc:
        return {
            "group": group,
            "slug": slug,
            "status": "error",
            "detail": str(exc),
            "project": None,
            "version": None,
            "newest_release": None,
            "dependency_records": [],
        }
    version_record = resolved.get("version") or {}
    return {
        "group": group,
        "slug": resolved["project"].get("slug") or slug,
        "status": resolved["status"],
        "detail": None,
        "project": resolved.get("project"),
        "version": resolved.get("version"),
        "newest_release": resolved.get("newest_release"),
        "dependency_records": survey_mod._dependency_records(
            root,
            version_record.get("required_dependencies") or [],
            offline=offline,
            refresh=refresh,
        ),
    }


def _suitability(row, packs: int, dependents: int, fit_host: bool, reference) -> int:
    if row.get("status") != "ok":
        return 0
    project = row.get("project") or {}
    version = row.get("version") or {}
    score = 30
    score += {"release": 10, "beta": 6, "alpha": 2}.get(version.get("version_type"), 0)
    if reference is not None:
        published = mods._published(project.get("updated"))
        days = (reference - published).days
        if days <= 120:
            score += 10
        elif days <= 365:
            score += 7
        elif days <= 730:
            score += 3
    score += _LICENSE_POINTS[_license_class(project.get("license"))]
    side = project.get("server_side")
    score += 5 if side == "required" else 3 if side == "optional" else 0
    score += min(packs * 2, 8)
    score += min(dependents * 2, 6)
    if fit_host:
        score += 4
    return max(0, min(score, 100))


def _role(row, kind: str, audit) -> str:
    if row.get("status") != "ok":
        return "excluded"
    if row["slug"] in _DESIGN_CONFLICTS:
        return "design-conflict"
    if audit is not None and audit.get("key") == "unusable":
        return "unusable"
    project = row.get("project") or {}
    categories = set(project.get("categories") or [])
    if kind == "library" or "library" in categories:
        return "library"
    if kind == "compatibility":
        return "compatibility"
    if kind == "add-on":
        return "add-on"
    if project.get("server_side") == "unsupported":
        return "client-only"
    if row.get("fit_host") or row.get("dependents", 0) >= 2:
        return "core"
    if "utility" in categories or "optimization" in categories:
        return "support"
    return "content"


def _verdict(row, role: str) -> str:
    if role == "excluded":
        return "excluded (no build)"
    if role == "design-conflict":
        return "exclude (design)"
    if role == "unusable":
        return "exclude (dependency)"
    if role == "client-only":
        return "optional (client-only)"
    packs = int(row.get("packs") or 0)
    dependents = int(row.get("dependents") or 0)
    suitability = int(row.get("suitability") or 0)
    if role == "library":
        if dependents or packs >= 8:
            return "include (library)"
        return "review (unused library)"
    if role == "compatibility":
        return "trial"
    if role == "support":
        if packs >= 8:
            return "include (support)"
        if packs >= 3:
            return "trial"
        return "defer"
    if role == "add-on":
        if packs >= 5:
            return "include (add-on)"
        if suitability >= 65:
            return "trial"
        return "defer"
    if role == "core":
        return "include (core)"
    if row.get("origin") == "seed":
        return "include (seed)" if suitability >= 55 else "trial"
    if packs >= 5:
        return "include (adoption)"
    if packs >= 2:
        return "trial"
    return "defer"


def _table(members) -> list[str]:
    lines = [
        "| Candidate | Build | Packs | Required by | Fit | Licence | Side | Necessity | Suitability | Verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in members:
        project = row.get("project") or {}
        version = row.get("version")
        if version:
            build = (
                f"{version.get('version_number')} "
                f"({mods._date(version.get('date_published'))})"
            )
        else:
            build = "none"
        values = (
            row["slug"],
            build,
            str(row["packs"]),
            str(row["dependents"]),
            "yes" if row["fit_host"] else "",
            project.get("license"),
            mods._side_cell(project),
            str(row["necessity"]),
            str(row["suitability"]),
            row["verdict"],
        )
        lines.append("| " + " | ".join(mods._cell(value) for value in values) + " |")
    return lines


def _write_report(
    path: Path,
    rows,
    version: str,
    loader: str,
    *,
    pack_count: int,
) -> None:
    ensure_dir(path.parent)
    statuses = Counter(row["status"] for row in rows)
    verdict_counts = Counter(row["verdict"] for row in rows)
    ordered = sorted(
        rows,
        key=lambda row: (
            _VERDICT_ORDER.index(row["verdict"])
            if row["verdict"] in _VERDICT_ORDER
            else len(_VERDICT_ORDER),
            _ROLE_ORDER.index(row["role"]) if row["role"] in _ROLE_ORDER else len(_ROLE_ORDER),
            -row["suitability"],
            -row["necessity"],
            row["slug"],
        ),
    )

    lines = [
        f"# Pack assessment: {version} / {loader}",
        "",
        f"{len(rows)} candidates assessed. Buildable: {statuses.get('ok', 0)}. "
        f"Excluded for no build: {statuses.get('no_build', 0)}. "
        f"Errors: {statuses.get('error', 0)}. Cross-pack adoption measured over "
        f"{pack_count} canonical cached pack(s).",
        "",
        "Generated by `chaoslab pack` from cached Modrinth responses, cached "
        "`.mrpack` indexes and the survey's transitive dependency audit; rerun with "
        "`--refresh` for current data. Scores and verdicts are decision support, not "
        "the decision: the role and raw signals beside each verdict are the evidence.",
        "",
        "## Scoring",
        "",
        "Necessity is structural: 3 per candidate that requires this one + 2 if a "
        "fit rule names it, capped at 20. Cross-pack adoption is reported beside it "
        "as a separate signal rather than folded into necessity.",
        "",
        "Suitability = 30 build + up to 10 release type + up to 10 maintenance "
        "recency + up to 8 licence + up to 5 server side + up to 8 cross-pack "
        "adoption + up to 6 dependents + 4 fit host, capped at 100.",
        "",
        "Licence classes: permissive (MIT/Apache/BSD/MPL) 8; copyleft (GPL) 6; "
        "non-commercial 4; other 3; all-rights-reserved or custom-protective 2; "
        "unknown 0. This is a distribution-risk signal, not legal advice.",
        "",
        "Role is structural: `core` is content a fit rule names or that at least "
        "two candidates require; `library` and `support` use Modrinth's category "
        "metadata; `add-on`, `compatibility` and `client-only` follow the survey "
        "section and side metadata; `unusable` has a dependency with no build; "
        "`design-conflict` contradicts a settled plan decision; `excluded` has no "
        "build.",
        "",
        "Verdict is the pack recommendation. Seeds (the original content sections) "
        "are included when suitable because they were chosen deliberately; harvested "
        "content needs cross-pack evidence; support and add-ons need both adoption "
        "and suitability; libraries are marked unused when nothing requires them.",
        "",
        "## Role summary",
        "",
        "| Role | Count | Mean necessity | Mean suitability |",
        "| --- | --- | --- | --- |",
    ]
    for role in _ROLE_ORDER:
        members = [row for row in ordered if row["role"] == role]
        if not members:
            continue
        mean_necessity = sum(row["necessity"] for row in members) / len(members)
        mean_suitability = sum(row["suitability"] for row in members) / len(members)
        lines.append(
            f"| {role} | {len(members)} | {mean_necessity:.1f} | "
            f"{mean_suitability:.1f} |"
        )
    lines.append("")

    lines += ["## Verdict summary", "", "| Verdict | Count |", "| --- | --- |"]
    for verdict in _VERDICT_ORDER:
        count = verdict_counts.get(verdict, 0)
        if count:
            lines.append(f"| {verdict} | {count} |")
    lines.append("")

    for verdict in _VERDICT_ORDER:
        members = [row for row in ordered if row["verdict"] == verdict]
        if not members:
            continue
        lines += [f"## {verdict}", ""]
        lines += _table(members)
        lines.append("")

    conflicts = [row for row in ordered if row["role"] == "design-conflict"]
    if conflicts:
        lines += ["## Design conflicts", ""]
        for row in conflicts:
            lines.append(f"- `{row['slug']}` — {_DESIGN_CONFLICTS[row['slug']]}")
        lines.append("")

    defer = [row["slug"] for row in ordered if row["verdict"] == "defer"]
    lines += [
        "## Caveats",
        "",
        "- Adoption only counts the canonical packs cached under `data/modpacks/`; "
        "a mod that is popular outside that set looks less adopted here.",
        "- A missing dependents count means no *candidate* requires the mod, not "
        "that nothing does.",
        "- Licence strings are Modrinth metadata and can lag the project's actual "
        "terms.",
        "- `defer` is a prompt to look, not a removal: the survey already records "
        "why each candidate is listed.",
        "",
    ]
    if defer:
        lines.append("Deferred on current signals: " + ", ".join(defer) + ".")
        lines.append("")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(
    root,
    candidates: str = "candidates.txt",
    *,
    version: str = mods.DEFAULT_VERSION,
    loader: str = mods.DEFAULT_LOADER,
    offline: bool = False,
    refresh: bool = False,
    report: str | None = None,
    rules: str = RULES_NAME,
) -> dict:
    """Assess every candidate in two passes: signals first, then verdicts."""
    root = Path(root)
    path = Path(candidates)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise mods.ModsError(f"candidates file not found: {path}")

    pairs = survey_mod.parse_candidates(path)
    if not pairs:
        raise mods.ModsError(f"no candidates in {path}")

    rows = [
        _row(root, group, slug, version, loader, offline=offline, refresh=refresh)
        for group, slug in pairs
    ]

    id_to_slug = _project_index(root)
    dependents: dict[str, set[str]] = {}
    for row in rows:
        version_record = row.get("version") or {}
        for dependency in version_record.get("required_dependencies") or []:
            project_id = dependency.get("project_id")
            if not project_id:
                continue
            target = id_to_slug.get(str(project_id))
            if not target or target == row["slug"]:
                continue
            dependents.setdefault(target, set()).add(row["slug"])

    candidate_slugs = {row["slug"] for row in rows}
    graph = survey_mod._dependency_graph(
        root, rows, version=version, loader=loader, offline=offline, refresh=refresh
    )
    audit_entries, _audit_counts = survey_mod._audit(rows, candidate_slugs, graph)
    audit_by_slug = {entry["slug"]: entry for entry in audit_entries}

    adoption = _pack_adoption(root, modpacks_mod.DEFAULT_PACKS)
    pack_count = sum(
        1
        for slug in modpacks_mod.DEFAULT_PACKS
        if (
            Path(root)
            / modpacks_mod.PACKS_DIR
            / modpacks_mod._binary_rel(slug, version, loader)
        ).exists()
    )
    adoption_by_slug: Counter = Counter()
    for project_id, count in adoption.items():
        slug = id_to_slug.get(str(project_id))
        if slug:
            adoption_by_slug[slug] += count

    fit_hosts = _fit_hosts(root, rules)
    reference = None
    for row in rows:
        project = row.get("project")
        if not project:
            continue
        updated = mods._published(project.get("updated"))
        if reference is None or updated > reference:
            reference = updated

    for row in rows:
        slug = row["slug"]
        audit = audit_by_slug.get(slug)
        row["packs"] = adoption_by_slug.get(slug, 0)
        row["dependents"] = len(dependents.get(slug, ()))
        row["fit_host"] = slug in fit_hosts
        row["origin"] = "seed" if row["group"] in _SEED_SECTIONS else "harvest"
        row["necessity"] = min(
            3 * row["dependents"] + (2 if row["fit_host"] else 0),
            20,
        )
        row["suitability"] = _suitability(
            row, row["packs"], row["dependents"], row["fit_host"], reference
        )
        row["role"] = _role(row, survey_mod._section_kind(row["group"]), audit)
        row["verdict"] = _verdict(row, row["role"])

    if report:
        report_path = Path(report)
        if not report_path.is_absolute():
            report_path = root / report_path
    else:
        report_path = root / "reports" / REPORT_NAME
    _write_report(report_path, rows, version, loader, pack_count=pack_count)
    return {
        "candidates": len(rows),
        "report": str(report_path),
        "statuses": dict(Counter(row["status"] for row in rows)),
        "roles": dict(Counter(row["role"] for row in rows)),
        "verdicts": dict(Counter(row["verdict"] for row in rows)),
        # The scored rows are returned so `chaoslab lint` can expand the pack
        # manifest from the same assessment instead of re-deriving it.
        "rows": rows,
    }
