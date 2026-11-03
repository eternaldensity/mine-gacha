"""chaoslab command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _add_mods_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", default="1.21.1", help="Minecraft version (default: 1.21.1)")
    parser.add_argument("--loader", default="neoforge", help="mod loader (default: neoforge)")
    parser.add_argument("--offline", action="store_true", help="use cached responses only; fail on a miss")
    parser.add_argument("--refresh", action="store_true", help="ignore cached responses and refetch")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chaoslab", description="Chaos Gacha corpus and mod-evidence tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="snapshot the corpus and web assets")
    fetch.add_argument("--source-dir", default=None, help="path to a ChaosGacha clone")
    fetch.add_argument("--refresh", action="store_true", help="replace an existing snapshot")

    parse = sub.add_parser("parse", help="parse gacha entries into data/corpus.jsonl")
    parse.add_argument("--include-nsfw", action="store_true")

    curses = sub.add_parser("curses", help="parse the curse list into data/curses.jsonl")
    curses.add_argument("--include-nsfw", action="store_true")

    mods = sub.add_parser("mods", help="catalog candidate mods from Modrinth")
    mods_sub = mods.add_subparsers(dest="mods_command", required=True)
    search = mods_sub.add_parser("search", help="rank candidates, filtered to the target build")
    search.add_argument("--query", required=True)
    _add_mods_flags(search)
    search.add_argument("--limit", type=int, default=20, help="maximum hits to request (1-100)")
    resolve = mods_sub.add_parser("resolve", help="resolve the newest matching build for one project")
    resolve.add_argument("--project", required=True, help="Modrinth slug, id, or project URL")
    _add_mods_flags(resolve)
    matrix = mods_sub.add_parser("matrix", help="one row per candidate in the compatibility matrix")
    matrix.add_argument("--candidates", default="candidates.txt", help="candidate slugs, one per line")
    matrix.add_argument(
        "--report",
        default=None,
        help="report path (default: reports/mods_matrix.md); use a separate path for smoke runs",
    )
    _add_mods_flags(matrix)

    survey = sub.add_parser("survey", help="grouped mod survey with resolved dependencies")
    survey.add_argument("--candidates", default="candidates.txt", help="candidate slugs, grouped by '# ==' headings")
    survey.add_argument("--report", default="reports/mods_survey.md", help="report path (default: reports/mods_survey.md)")
    _add_mods_flags(survey)

    modpacks = sub.add_parser("modpacks", help="survey popular modpacks for candidate mods and quest examples")
    modpacks.add_argument("--limit", type=int, default=12, help="packs to inspect, by download rank")
    modpacks.add_argument("--packs", default=None, help="comma-separated pack slugs instead of the download ranking")
    modpacks.add_argument("--query", default="", help="narrow the download ranking, e.g. 'quests'")
    modpacks.add_argument(
        "--ranked",
        action="store_true",
        help="use the download ranking instead of the curated progression/magic/tech pack set",
    )
    modpacks.add_argument(
        "--max-lookups",
        type=int,
        default=2000,
        help="maximum distinct projects to resolve to names (bulk requests, 90 per call)",
    )
    modpacks.add_argument(
        "--cap",
        type=int,
        default=None,
        help="maximum bytes per .mrpack download (default: 400 MB)",
    )
    modpacks.add_argument("--report", default="reports/modpacks_survey.md", help="report path (default: reports/modpacks_survey.md)")
    _add_mods_flags(modpacks)

    pack = sub.add_parser("pack", help="score candidates for pack necessity and suitability")
    pack.add_argument("--candidates", default="candidates.txt", help="candidate slugs, grouped by '# ==' headings")
    pack.add_argument("--rules", default="fit_rules.json", help="fit rules file whose hosts count as necessity")
    pack.add_argument("--report", default="reports/pack_assessment.md", help="report path (default: reports/pack_assessment.md)")
    _add_mods_flags(pack)

    lint = sub.add_parser(
        "lint", help="expand the declared pack manifest and audit its dependency closure"
    )
    lint.add_argument("--manifest", default="pack_manifest.json", help="declared pack policy (default: pack_manifest.json)")
    lint.add_argument("--report", default="reports/pack_report.md", help="audit report path (default: reports/pack_report.md)")
    lint.add_argument("--doc", default="PACK.md", help="rendered pack document (default: PACK.md)")
    lint.add_argument("--rules", default="fit_rules.json", help="fit rules whose hosts must ship")
    _add_mods_flags(lint)

    build = sub.add_parser(
        "build", help="pin builds and emit a deterministic .mrpack plus pack_lock.json"
    )
    build.add_argument("--manifest", default="pack_manifest.json", help="declared pack policy")
    build.add_argument("--lock", default="pack_lock.json", help="lock output path")
    build.add_argument("--dist", default="dist", help="archive output directory")
    build.add_argument("--report", default="reports/pack_build.md", help="build report path")
    build.add_argument("--rules", default="fit_rules.json", help="fit rules used by the assessment")
    _add_mods_flags(build)

    runtime = sub.add_parser(
        "runtime",
        help="audit the pinned pack for runtime hazards and triage captured server logs",
    )
    runtime.add_argument("--lock", default="pack_lock.json", help="pinned build lock")
    runtime.add_argument("--manifest", default="pack_manifest.json", help="declared pack policy")
    runtime.add_argument(
        "--report", default="reports/runtime_compat.md", help="deterministic audit report"
    )
    runtime.add_argument(
        "--log",
        action="append",
        default=None,
        help="log file or directory to triage (repeatable)",
    )
    runtime.add_argument(
        "--log-report", default="reports/runtime_logs.md", help="triage report path"
    )
    runtime.add_argument(
        "--side",
        choices=("client", "server", "both"),
        default="both",
        help="exclude jars whose metadata marks them unsupported on this side",
    )
    runtime.add_argument("--json", action="store_true", help="print the payload as JSON")

    structures = sub.add_parser(
        "structures", help="collect structure jars and enumerate their loot tables (D1)"
    )
    structures.add_argument(
        "--collect",
        action="store_true",
        help="download the candidate jars into the jar cache before scanning",
    )
    structures.add_argument("--jar-dir", default="data/jars", help="jar cache directory")
    structures.add_argument(
        "--report", default="reports/structure_tables.md", help="report path"
    )
    structures.add_argument(
        "--cap",
        type=int,
        default=None,
        help="maximum bytes to download (default: 200 MB)",
    )
    structures.add_argument(
        "--offline", action="store_true", help="never download jar bytes"
    )
    structures.add_argument("--json", action="store_true", help="print a summary as JSON")

    fit = sub.add_parser("fit", help="join corpus entries to mod capabilities")
    fit.add_argument("--rules", default="fit_rules.json")

    datapack = sub.add_parser(
        "datapack", help="validate the custom mod's schemas, datapack and config"
    )
    datapack.add_argument("--schema", default="mod/schema", help="JSON Schema directory")
    datapack.add_argument("--datapack", default="mod/datapack", help="shipped datapack directory")
    datapack.add_argument("--examples", default="mod/examples", help="fixture directory (not shipped)")
    datapack.add_argument("--config", default="mod/config", help="default config directory")
    datapack.add_argument(
        "--report", default="reports/datapack_report.md", help="report path"
    )
    datapack.add_argument("--json", action="store_true", help="print the summary as JSON")
    datapack.add_argument(
        "--selftest",
        action="store_true",
        help="run the validator self-test and exit (no files are read or written)",
    )

    simulate = sub.add_parser("simulate", help="reproduce the gacha and curse rollers")
    simulate.add_argument("--roller", choices=("gacha", "curses"), default="gacha")
    simulate.add_argument("--preset", default="gold")
    simulate.add_argument("--draws", type=int, default=100000)
    simulate.add_argument("--seed", type=int, default=1)
    simulate.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="regenerate derived reports")
    report.add_argument("--rules", default="fit_rules.json")

    verify = sub.add_parser(
        "verify", help="regenerate derived reports offline and compare with a manifest"
    )
    verify.add_argument("--manifest", default="reports/MANIFEST.sha256")
    verify.add_argument("--report", default="reports/verify.md")
    verify.add_argument(
        "--update",
        action="store_true",
        help="write the manifest after a byte-identical offline regeneration",
    )
    verify.add_argument("--version", default="1.21.1", help="Minecraft version (default: 1.21.1)")
    verify.add_argument("--loader", default="neoforge", help="mod loader (default: neoforge)")
    verify.add_argument(
        "--inputs-only",
        action="store_true",
        help="validate inputs only; skip offline regeneration of derived artifacts",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "fetch":
        from .fetch import FetchError, fetch

        try:
            manifest = fetch(ROOT, args.source_dir, args.refresh)
        except FetchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"source: {manifest['source_kind']} ({manifest['source']})")
        print(f"files: {manifest['present']} present, {manifest['absent']} absent, {manifest['total_bytes']} bytes")
        for record in manifest["files"]:
            state = "ok" if record["present"] else "absent"
            print(f"  {state:6} {record['path']} ({record['bytes']} bytes)")
        return 0

    if args.command == "parse":
        from .fetch import FetchError
        from .parse import run

        try:
            result = run(ROOT, include_nsfw=args.include_nsfw)
        except FetchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"parsed {result['entries']} entries ({result['included']} included, {result['excluded']} excluded)")
        print(f"wrote {result['corpus']}")
        return 0

    if args.command == "curses":
        from .curses import run
        from .fetch import FetchError

        try:
            result = run(ROOT, include_nsfw=args.include_nsfw)
        except (FetchError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"parsed {result['curses']} curses from {result['source_file']}")
        print(f"wrote {result['output']}")
        return 0

    if args.command == "mods":
        from . import mods as mods_mod

        try:
            if args.mods_command == "search":
                rows = mods_mod.search(
                    ROOT,
                    args.query,
                    args.version,
                    args.loader,
                    args.limit,
                    offline=args.offline,
                    refresh=args.refresh,
                )
                for row in rows:
                    build = {True: "build", False: "no build", None: "unknown"}[row["has_build"]]
                    print(f"{row['slug']:40} {build:9} {row['downloads']:>12}  {row['title']}")
                return 0
            if args.mods_command == "resolve":
                row = mods_mod.resolve(
                    ROOT,
                    args.project,
                    args.version,
                    args.loader,
                    offline=args.offline,
                    refresh=args.refresh,
                )
                print(json.dumps(row, indent=2, sort_keys=True))
                return 0 if row["status"] == "ok" else 0
            result = mods_mod.matrix(
                ROOT,
                args.candidates,
                refresh=args.refresh,
                version=args.version,
                loader=args.loader,
                offline=args.offline,
                report=args.report,
            )
        except mods_mod.NotFound as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except mods_mod.ModsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        counts = ", ".join(f"{key}={value}" for key, value in sorted(result["statuses"].items()))
        print(f"matrix: {result['candidates']} candidates -> {result['report']}")
        print(f"statuses: {counts}")
        return 0

    if args.command == "survey":
        from . import mods as mods_mod
        from . import survey as survey_mod

        try:
            result = survey_mod.run(
                ROOT,
                args.candidates,
                version=args.version,
                loader=args.loader,
                offline=args.offline,
                refresh=args.refresh,
                report=args.report,
            )
        except mods_mod.ModsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        counts = ", ".join(f"{key}={value}" for key, value in sorted(result["statuses"].items()))
        audit = ", ".join(f"{key}={value}" for key, value in sorted(result.get("audit", {}).items()))
        print(f"survey: {result['candidates']} candidates in {result['sections']} sections -> {result['report']}")
        print(f"statuses: {counts}")
        print(f"audit: {audit}")
        return 0

    if args.command == "modpacks":
        from . import modpacks as modpacks_mod
        from . import mods as mods_mod

        packs = [slug.strip() for slug in (args.packs or "").split(",") if slug.strip()] or None
        try:
            result = modpacks_mod.run(
                ROOT,
                version=args.version,
                loader=args.loader,
                limit=args.limit,
                packs=packs,
                offline=args.offline,
                refresh=args.refresh,
                report=args.report,
                max_lookups=args.max_lookups,
                cap=args.cap,
                query=args.query,
                ranked=args.ranked,
            )
        except mods_mod.ModsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        counts = ", ".join(f"{key}={value}" for key, value in sorted(result["statuses"].items()))
        print(f"modpacks: {result['packs']} packs -> {result['report']}")
        print(
            f"mods: {result['mods']} distinct, {result['named']} named, "
            f"quest systems: {result['quest_systems']}"
        )
        print(f"statuses: {counts}")
        return 0

    if args.command == "pack":
        from . import mods as mods_mod
        from . import pack as pack_mod

        try:
            result = pack_mod.run(
                ROOT,
                args.candidates,
                version=args.version,
                loader=args.loader,
                offline=args.offline,
                refresh=args.refresh,
                report=args.report,
                rules=args.rules,
            )
        except mods_mod.ModsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        roles = ", ".join(f"{key}={value}" for key, value in sorted(result["roles"].items()))
        verdicts = ", ".join(
            f"{key}={value}" for key, value in sorted(result["verdicts"].items())
        )
        print(f"pack: {result['candidates']} candidates -> {result['report']}")
        print(f"roles: {roles}")
        print(f"verdicts: {verdicts}")
        return 0

    if args.command == "lint":
        from . import mods as mods_mod
        from . import packlint as packlint_mod

        try:
            result = packlint_mod.run(
                ROOT,
                manifest=args.manifest,
                report=args.report,
                doc=args.doc,
                rules=args.rules,
                version=args.version,
                loader=args.loader,
                offline=args.offline,
                refresh=args.refresh,
            )
        except (mods_mod.ModsError, packlint_mod.PackError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        milestones = ", ".join(
            f"{key}={value}" for key, value in sorted(result["milestones"].items())
        )
        print(f"lint: {'PASS' if result['ok'] else 'FAIL'}; {result['entries']} candidates -> {result['report']}")
        print(f"milestones: {milestones}")
        print(f"carried transitively: {result['carried']}")
        print(f"doc: {result['doc']}")
        for check in result["checks"]:
            if check["status"] != "pass":
                print(f"  FAIL {check['name']}: {check['detail']}")
        return 0 if result["ok"] else 1

    if args.command == "build":
        from . import mods as mods_mod
        from . import packbuild as packbuild_mod

        try:
            result = packbuild_mod.run(
                ROOT,
                manifest=args.manifest,
                lock=args.lock,
                dist=args.dist,
                report=args.report,
                rules=args.rules,
                version=args.version,
                loader=args.loader,
                offline=args.offline,
                refresh=args.refresh,
            )
        except (mods_mod.ModsError, packbuild_mod.BuildError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"build: {result['projects']} projects ({result['carried']} carried) -> {result['mrpack']}")
        print(f"lock: {result['lock']} (index sha256 {result['index_sha256'][:16]}…)")
        print(f"overrides: {result['overrides']}")
        print(f"wrote {result['report']}")
        return 0

    if args.command == "runtime":
        from . import runtime as runtime_mod

        try:
            result = runtime_mod.run(
                ROOT,
                lock=args.lock,
                manifest=args.manifest,
                report=args.report,
                log_report=args.log_report,
                logs=args.log,
                side=args.side,
            )
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            env = result.get("environment") or {}
            if env.get("java"):
                state = "ok" if env.get("java_ok") else "too old"
                print(
                    f"java: {env['java']} (major {env.get('java_major')}, {state}; "
                    f"need {env.get('min_java')}+)"
                )
            else:
                print(
                    "java: not found on PATH; the probe must run on a machine with a JVM "
                    f"({env.get('min_java')}+)"
                )
            missing = result["closure_missing"]
            print(
                f"runtime: {result['projects']} projects; closure "
                f"{'complete' if not missing else 'INCOMPLETE'}"
            )
            for dep, requesters in sorted(missing.items()):
                print(f"  missing {dep} required by {', '.join(sorted(requesters))}")
            for row in result["audit"]:
                print(f"  side {row['slug']}: {', '.join(row['concerns'])}")
            print(f"wrote {result['report']}")
            if result.get("log_report"):
                print(
                    f"triage: {result['log_matches']} match(es) in "
                    f"{result['logs_scanned']} file(s) -> {result['log_report']}"
                )
                identity = result.get("identity") or {}
                rows = identity.get("files") or []
                label = "pack_lock.json %s" % (
                    identity.get("pack_version") or "unknown"
                )
                drift = [row for row in rows if row["status"] == "drift"]
                matched = [row for row in rows if row["status"] == "match"]
                if drift:
                    print(
                        f"identity: DRIFT - the capture does not match {label}; "
                        f"{len(drift)} log file(s) differ"
                    )
                    for row in drift:
                        if row["log_only"]:
                            print(
                                f"  {row['file']} loaded but not locked: "
                                f"{', '.join(row['log_only'])}"
                            )
                        if row["lock_only"]:
                            print(
                                f"  {row['file']} locked but not loaded: "
                                f"{', '.join(row['lock_only'])}"
                            )
                elif matched:
                    print(
                        f"identity: MATCH - {matched[0]['file']} lists exactly the "
                        f"{identity['locked']} locked jars ({label})"
                    )
                else:
                    print(
                        "identity: UNVERIFIED - the captured primary logs contain "
                        "no mod-discovery lines"
                    )
        return 0 if result["ok"] else 1

    if args.command == "structures":
        from . import mods as mods_mod
        from . import structures as structures_mod

        try:
            result = structures_mod.run(
                ROOT,
                collect=args.collect,
                jar_dir=args.jar_dir,
                report=args.report,
                cap=args.cap,
                offline=args.offline,
            )
        except (mods_mod.ModsError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            summary = {
                key: result[key]
                for key in ("candidates", "collected", "jars", "tables", "chest_tables")
            }
            summary["report"] = result["report"]
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(
                f"structures: {result['candidates']} candidates, {result['collected']} jars "
                f"verified, {result['tables']} loot tables ({result['chest_tables']} chest) "
                f"-> {result['report']}"
            )
            for row in result["statuses"]:
                if row["status"] not in ("cached", "downloaded"):
                    print(f"  {row['status']:10} {row['slug']}: {row['detail']}")
        return 0

    if args.command == "fit":
        from .fit import run as fit_run

        try:
            result = fit_run(ROOT, ROOT / args.rules)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"fit: {result['rows']} rows, {result['mapped']} mapped, {result['unmapped']} unmapped")
        print(f"wrote {result['csv']}")
        return 0

    if args.command == "datapack":
        from . import datapack as datapack_mod

        if args.selftest:
            results = datapack_mod.selftest()
            failures = [row for row in results if not row["ok"]]
            for row in results:
                print(f"selftest: {'ok  ' if row['ok'] else 'FAIL'} {row['name']}")
            print(f"selftest: {len(results) - len(failures)}/{len(results)} passed")
            return 0 if not failures else 1
        try:
            result = datapack_mod.run(
                ROOT,
                schema=args.schema,
                datapack=args.datapack,
                examples=args.examples,
                config=args.config,
                report=args.report,
            )
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            summary = {
                "ok": result["ok"],
                "files": result["files"],
                "schemas": len(result["schemas"]),
                "errors": result["errors"],
            }
            summary["report"] = result["report"]
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            state = "PASS" if result["ok"] else "FAIL"
            print(
                f"datapack: {state}; {result['files']} file(s) against "
                f"{len(result['schemas'])} schema(s) -> {result['report']}"
            )
            for message in result["errors"][:10]:
                print(f"  {message}")
            if len(result["errors"]) > 10:
                print(f"  ... and {len(result['errors']) - 10} more")
        return 0 if result["ok"] else 1

    if args.command == "simulate":
        from .fetch import FetchError
        from .simulate import run as sim_run

        try:
            result = sim_run(ROOT, args.roller, args.preset, args.draws, args.seed)
        except (FetchError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{result['roller']} preset={result.get('preset')} draws={result['draws']} seed={result['seed']}")
            for tier, share in result["tiers"].items():
                print(f"  {tier:12} {share:.4f}")
        return 0

    if args.command == "verify":
        from . import verify as verify_mod

        try:
            result = verify_mod.run(
                ROOT,
                manifest=args.manifest,
                report=args.report,
                update=args.update,
                version=args.version,
                loader=args.loader,
                inputs_only=args.inputs_only,
            )
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        state = "PASS" if result["ok"] else "FAIL"
        scope = (
            "inputs only"
            if args.inputs_only
            else f"{result['matched']}/{result['checked']} artifacts match"
        )
        print(f"verify: {state}; {scope}")
        print(f"inputs: {result['inputs_valid']}/{result['inputs_checked']} valid")
        print(f"manifest: {result['manifest']}")
        print(f"wrote {result['report']}")
        for row in result["inputs"]:
            if row["status"] != "valid":
                print(f"  {row['status']:18} {row['path']}")
        for row in result["checks"]:
            if row["status"] != "match":
                print(f"  {row['status']:18} {row['path']}")
        return 0 if result["ok"] else 1

    if args.command == "report":
        from . import report as report_mod
        from .fetch import FetchError

        try:
            paths = report_mod.run(ROOT)
        except (FetchError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        for path in paths:
            print(f"wrote {path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
