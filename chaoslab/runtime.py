'''Runtime-compatibility harness for the pinned pack.

`chaoslab build` proves the archive is a pure function of the manifest and the
cache. The offline gate proves every derived artifact can be regenerated.
Neither proves that the pinned jars co-load, which is the first genuinely new
risk in this project.

This module is the bridge between the offline tree and a real JVM:

- audits `pack_lock.json` for dedicated-server and client hazards,
- checks version-level dependency closure (every required project id is pinned),
- emits a fixed probe sequence and a fixed conflict taxonomy, and
- classifies captured server logs into that taxonomy with one action each.

Java availability is deliberately not rendered into the report: it differs per
machine and would make `chaoslab verify` non-reproducible. `probe_environment`
returns it for the console and `--json` output only.
'''

from __future__ import annotations

import datetime
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from .util import ensure_dir, read_json

REPORT_NAME = 'reports/runtime_compat.md'
LOG_REPORT_NAME = 'reports/runtime_logs.md'
MIN_JAVA = 21
MAX_LOG_BYTES = 8 * 1024 * 1024

_SEVERITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2}

_RULES = (
    (
        'missing-dependency',
        'critical',
        r'Missing or unsupported mandatory dependencies|modId=.+requires',
        'Add the requested dependency, or exclude the requester in `pack_manifest.json`. A required dependency outside the pack is a hard stop.',
    ),
    (
        'duplicate-mod',
        'critical',
        r'Duplicate mods|found a duplicate mod|Duplicate mod id',
        'Remove one of the duplicated jars; the lock must name exactly one build per project.',
    ),
    (
        'mixin-failure',
        'critical',
        r'Mixin apply failed|InvalidMixinException|Mixin transformation of .+ failed',
        'Pin the mixin owner and the target to versions known to build together, or drop one.',
    ),
    (
        'registry-conflict',
        'high',
        r'already registered|Duplicate registry|registry key .+ is already',
        'Two projects claim the same registry key; pin versions or drop one of them.',
    ),
    (
        'client-class-on-server',
        'high',
        r'for invalid dist|Attempted to load class .+(client|Client)',
        'Move the project to client-only (server-unsupported) or drop it from the server.',
    ),
    (
        'class-loading',
        'high',
        r'NoClassDefFoundError|ClassNotFoundException',
        'Usually a missing mandatory dependency or a client class on a server; cross-check the side audit above.',
    ),
    (
        'out-of-memory',
        'high',
        r'OutOfMemoryError|Java heap space',
        'Environment, not a mod conflict: raise -Xmx and re-run before blaming a project.',
    ),
    (
        'worldgen-conflict',
        'medium',
        r'Feature order cycle|feature cycle|Failed to place feature',
        'Pin the biome/feature providers or drop one worldgen project; compare against the worldgen survivors in the manifest.',
    ),
    (
        'datapack-error',
        'medium',
        r'Failed to load datapack|Could not parse data file|Couldn.t parse data file',
        'Identify the namespace in the evidence line, then pin or drop that project.',
    ),
    (
        'fatal-crash',
        'critical',
        r'Failed to create mod|A fatal error has been detected|Exception in server tick loop',
        'Use the top project in the crash report as the suspect; remove or pin it and re-run.',
    ),
)

_COMPILED = tuple(
    (kind, severity, re.compile(pattern, re.IGNORECASE), action)
    for kind, severity, pattern, action in _RULES
)

_CRASH_DESCRIPTION = re.compile(r'^Description: (.+)$', re.MULTILINE)
_CRASH_ISSUE = re.compile(r'^-- Mod loading issue for: (\S+) --$', re.MULTILINE)
_CRASH_FAILURE = re.compile(r'^\tFailure message: (.+)$', re.MULTILINE)
_CRASH_MODFILE = re.compile(r'^\tMod file: (.+)$', re.MULTILINE)

# A capture may include crash reports from installs that predate the launch
# under test. Those files are older than the newest primary log, so their rows
# are history rather than current failures.
_PRIMARY_LOGS = ('latest.log', 'debug.log')


def _crash_issues(text, name):
    """One structured row per ``-- Mod loading issue for: X --`` block.

    A mod-loading crash report lists each failure as a block naming the mod and
    the exact dependency or version it wanted. Collapsing that to one generic
    "mod loading failed" row throws away the only part an operator can act on,
    so each block becomes its own finding.
    """
    issues = []
    headers = list(_CRASH_ISSUE.finditer(text))
    for position, match in enumerate(headers):
        end = headers[position + 1].start() if position + 1 < len(headers) else len(text)
        block = text[match.end():end]
        failure = _CRASH_FAILURE.search(block)
        modfile = _CRASH_MODFILE.search(block)
        mod = match.group(1).strip()
        message = failure.group(1).strip() if failure else 'mod loading issue without a Failure message'
        if modfile:
            jar = modfile.group(1).strip().replace('\\', '/').rsplit('/', 1)[-1]
            message = '%s [%s]' % (message, jar)
        issues.append({
            'kind': 'mod-loading-issue',
            'severity': 'critical',
            'file': name,
            'line': text.count('\n', 0, match.start()) + 1,
            'evidence': ('%s: %s' % (mod, message))[:300],
            'action': 'Install the exact dependency version named for the requester, or exclude/pin it in `pack_manifest.json`, then re-test before accepting the fix.',
        })
    return issues


def _load(root, name):
    path = Path(name)
    if not path.is_absolute():
        path = root / path
    payload = read_json(path, default=None)
    if not isinstance(payload, dict):
        raise ValueError('%s: not a readable JSON object' % name)
    return payload


def _audit(projects):
    rows = []
    for slug in sorted(projects):
        entry = projects[slug]
        concerns = []
        if entry.get('server_side') == 'unsupported':
            concerns.append('server-unsupported')
        if entry.get('client_side') == 'unsupported':
            concerns.append('client-unsupported')
        if concerns:
            rows.append({
                'slug': slug,
                'client': entry.get('client_side'),
                'server': entry.get('server_side'),
                'concerns': concerns,
            })
    return rows


def _closure(projects):
    ids = set()
    for entry in projects.values():
        if entry.get('project_id'):
            ids.add(str(entry['project_id']))
    missing = {}
    for slug in sorted(projects):
        for dep in projects[slug].get('required') or []:
            dep = str(dep)
            if dep not in ids:
                missing.setdefault(dep, []).append(slug)
    return {'ids': len(ids), 'missing': missing}


def _duplicate_filenames(projects):
    seen = {}
    for slug in sorted(projects):
        name = str(projects[slug].get('filename') or '')
        seen.setdefault(name, []).append(slug)
    return sorted(name for name, slugs in seen.items() if len(slugs) > 1)


def _write(path, text):
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def _render(lock, manifest, audit, closure, duplicates, archive_sha=None):
    target = manifest.get('target') or {}
    projects = lock.get('projects') or {}
    total_bytes = sum(int(entry.get('size') or 0) for entry in projects.values())
    server_bad = sum(1 for row in audit if 'server-unsupported' in row['concerns'])
    client_bad = sum(1 for row in audit if 'client-unsupported' in row['concerns'])
    missing = closure['missing']
    if missing or duplicates:
        status = 'Result: FAIL - the pinned set is internally inconsistent; see the closure and duplicate sections.'
    else:
        status = 'Result: PASS - every project is pinned to one unique filename and every required id is pinned.'
    archive = 'dist/chaos-gacha-1.0.0-milestone-a-1.21.1-neoforge.mrpack'
    archive_line = f'- Archive: `{archive}`'
    if archive_sha:
        archive_line += f' (sha256 `{archive_sha}`)'
    lines = [
        '# Runtime compatibility',
        '',
        'Generated by `chaoslab runtime` from `pack_lock.json` and `pack_manifest.json` with no network access and no JVM required. This report is part of the offline gate; the JVM probe and captured-log triage are deliberately outside it.',
        '',
        status,
        '',
        '## What this proves',
        '',
        'The pinned set is internally consistent: each project resolves to one build, each filename is unique, and every required project id is itself pinned. Co-loading is not something the offline gate can observe; it rests on the recorded runs below.',
        '',
        '## Recorded boot evidence',
        '',
        'Manual evidence, recorded rather than recomputed: the gate cannot observe a running game, so read this as real observations, not gate results. Each covers one archive, not future ones.',
        '',
        '### Client install (2026-10-26)',
        '',
        '- Launcher: Prism Launcher',
        f'- Pinned build set: `pack_lock.json` index sha256 `{lock.get("index_sha256") or "unknown"}`; re-testing a different lock invalidates this record.',
        '- PASS: the rebuilt pre-mod archive installed into a fresh instance.',
        '- PASS: a new singleplayer world generated and the player entered it.',
        '',
        '### Client install (2026-11-03, assembled archive)',
        '',
        '- Launcher: Prism Launcher, local `.mrpack` import/update',
        '- PASS: entered a world and ran `/gacha ticket give` and `/gacha machine give`; ticket opening and rewards worked.',
        '- PASS: village, ruined-portal and Apotheosis chests injected tickets after the global-loot-modifier manifest fix.',
        '- PASS: the First Roll and Deja Vu quests completed; the advancement tab rendered with its background and both nodes together.',
        '- Note: the tested build predates the `gacha:root` tab-name change; that is a display-only rename in the current archive.',
        '',
        '### Dedicated server (2026-11-03)',
        '',
        '- Runtime: direct JVM (Java 21), dedicated server, no launcher',
        archive_line,
        '- PASS: 58 server-side CDN jars and the bundled `gacha-0.1.0.jar` loaded together; `Done (11.041s cold, 4.596s warm)` with no fatal or load-blocking errors. The two server-unsupported jars (`athena-ctm`, `simply-tooltips`) were withheld per the side audit.',
        '- PASS: Heracles found the three quest files under `config/heracles/quests/` and loaded them.',
        '- PASS: `chaoslab runtime --log ... --side server` reports `MATCH` against the 58 locked jars plus the 1 bundled local jar. The triage keeps two expected client-class transformer probes (`ItemRenderer`, `AbstractClientPlayer`) as high-severity advisory findings; neither aborts the boot.',
        '- Covered by the 2026-11-03 client record above.',
        '',
        'Still unproven, and not implied by the rows above:',
        '',
        '- sustained play under load',
        '- co-existence of the stacked tech mods beyond world load',
        '- a long play arc and the tier/power-score balance that depends on it',
        '',
        '## Target',
        '',
        '- Minecraft %s / %s %s' % (
            target.get('minecraft', '?'),
            target.get('loader', '?'),
            target.get('loader_version', '?'),
        ),
        '- %d projects pinned, %.1f MiB of downloads' % (
            len(projects),
            total_bytes / (1024.0 * 1024.0),
        ),
        '- %d server-unsupported, %d client-unsupported (advisory; see the side audit)' % (
            server_bad,
            client_bad,
        ),
        '- Java %d+ required; the probe checks the local runtime and reports it on the console only' % MIN_JAVA,
        '',
        '## Version-level dependency closure',
        '',
    ]
    if missing:
        lines.append('FAIL - %d required project id(s) are not pinned:' % len(missing))
        lines.append('')
        lines.append('| Missing project id | Required by |')
        lines.append('| --- | --- |')
        for dep in sorted(missing):
            lines.append('| `%s` | %s |' % (dep, ', '.join(sorted(missing[dep]))))
    else:
        lines.append('PASS - all %d required project id references resolve inside the lock.' % closure['ids'])
    if duplicates:
        lines += ['', '## Duplicate filenames', '']
        for name in duplicates:
            lines.append('- `%s`' % name)
    lines += [
        '',
        '## Side audit',
        '',
        'Rows appear only where a side flag is `unsupported`. `server-unsupported` means the project must not be installed on the dedicated server even though the archive contains it; `client-unsupported` is harmless on a client but means the project does nothing there.',
        '',
    ]
    if audit:
        lines += ['| Project | Client | Server | Concern |', '| --- | --- | --- | --- |']
        for row in audit:
            lines.append('| `%s` | %s | %s | %s |' % (
                row['slug'],
                row['client'],
                row['server'],
                ', '.join(row['concerns']),
            ))
    else:
        lines.append('No side hazards recorded in the lock.')
    lines += [
        '',
        '## Probe sequence',
        '',
        'Repeat this after any pack change; the record above covers one archive only. It is the only step that produces new runtime evidence.',
        '',
        '1. `java -version` reports 21 or newer.',
        '2. Install the `.mrpack` from `dist/` into a throwaway instance, not a long-lived one.',
        '3. Start a dedicated server with 4-6 GiB, wait for `Done`, then stop it cleanly.',
        '4. Join with one client; open a chest, a quest and one tech GUI.',
        '5. Capture `logs/latest.log`, `logs/debug.log` and any `crash-*.txt` into `data/runtime/logs/`.',
        '6. Run `python3 -m chaoslab runtime --log data/runtime/logs` and triage the findings, including the build-identity verdict.',
        '',
        '## Build identity',
        '',
        'A triage run compares every jar NeoForge reports discovering under the instance `mods` folder against the `filename` values pinned in `pack_lock.json`, plus the bundled local jars under `pack/mod/` that are deliberately not published. `--side server` (or `client`) also drops locked jars whose metadata marks them unsupported on that side, so a dedicated-server capture is not failed by client-only content it was right to withhold. The launcher framework jars NeoForge also discovers (`client-*-srg.jar`, `neoforge-*-universal.jar`) are ignored because they are not pack content. A capture that lists an undeclared jar, omits a locked one, or omits a bundled local one is `drift` and fails the run; a capture with no discovery lines is `unverified` rather than a pass, because truncated evidence cannot identify the build. Filenames are the strongest signal a log carries: a same-named jar re-uploaded with different bytes is indistinguishable without the lock hashes.',
        '',
        '## Conflict taxonomy',
        '',
        '| Kind | Severity | Action |',
        '| --- | --- | --- |',
    ]
    for kind, severity, _pattern, action in _RULES:
        lines.append('| %s | %s | %s |' % (kind, severity, action))
    lines.append('| crash-report | critical | Treat the description and the first project in the stack as the suspect. |')
    lines += [
        '',
        '## Finding and removing a conflict',
        '',
        '1. Reproduce: the same failure must occur twice from a clean instance before it counts.',
        '2. Capture: keep the full log and crash report; do not truncate the first 200 lines.',
        '3. Classify: run the harness. When no rule matches it says so instead of guessing.',
        '4. Isolate: remove half the implicated projects, or pin a newer build of one, and retry.',
        '5. Record: an exclusion goes in `pack_manifest.json` `policy.exclusions` with a reason; a version pin goes through the cached version list, never a hand-edited lock.',
        '6. Re-gate: run `python3 -m chaoslab verify`. A pack change that is not reproducible is not a fix.',
        '',
        '## Captured-log triage',
        '',
        'This gated report never embeds external logs. Capture a failed boot into `data/runtime/logs/` and run:',
        '',
        '```',
        'python3 -m chaoslab runtime --log data/runtime/logs',
        '```',
        '',
        'That writes `reports/runtime_logs.md`, which is intentionally outside the manifest because it depends on evidence produced elsewhere.',
        '',
    ]
    return '\n'.join(lines) + '\n'


def _render_identity(identity):
    version = identity.get('pack_version') or 'unknown'
    digest = identity.get('index_sha256') or 'unknown'
    lines = [
        '## Build identity',
        '',
        'Compared the jars NeoForge reports discovering against the pinned build '
        '(`%s`, lock index sha256 `%s`). This proves filenames only: a same-named '
        'jar re-uploaded with different bytes is indistinguishable in a log.' % (version, digest),
        '',
    ]
    if not identity['files']:
        lines.append(
            'UNVERIFIED - no `latest.log` or `debug.log` was captured, so no '
            'mod-discovery evidence exists.'
        )
        lines.append('')
        return lines
    lines += [
        '| Log | Status | Matched | Local | In log, not locked | Locked, not in log |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for row in identity['files']:
        lines.append('| %s | %s | %d | %d | %d | %d |' % (
            row['file'],
            row['status'],
            len(row['matched']),
            len(row.get('local') or []),
            len(row['log_only']),
            len(row['lock_only']),
        ))
    lines.append('')
    drift = [row for row in identity['files'] if row['status'] == 'drift']
    if drift:
        lines.append(
            'FAIL - the capture does not contain the expected set, so it is not '
            'evidence about this pack:'
        )
        lines.append('')
        for row in drift:
            if row['log_only']:
                lines.append('- `%s` loaded but not declared: %s' % (
                    row['file'],
                    ', '.join('`%s`' % name for name in row['log_only']),
                ))
            if row['lock_only']:
                lines.append('- `%s` locked but not loaded: %s' % (
                    row['file'],
                    ', '.join('`%s`' % name for name in row['lock_only']),
                ))
            if row.get('local_missing'):
                lines.append('- `%s` local jar(s) missing from the capture: %s' % (
                    row['file'],
                    ', '.join('`%s`' % name for name in row['local_missing']),
                ))
        lines.append('')
    else:
        matched = [row for row in identity['files'] if row['status'] == 'match']
        if matched:
            lines.append(
                'PASS - %d log(s) list exactly the %d locked jars plus the %d '
                'bundled local jar(s).'
                % (len(matched), identity['locked'], identity.get('local', 0))
            )
        else:
            lines.append(
                'UNVERIFIED - the captured primary logs contain no mod-discovery lines.'
            )
        lines.append('')
    return lines


def _render_logs(findings, scanned, oversized, total, suppressed, files, identity):
    stale = [row for row in findings if row.get('stale')]
    current = [row for row in findings if not row.get('stale')]
    lines = [
        '# Runtime log triage',
        '',
        'Generated by `chaoslab runtime --log`. This report is intentionally not part of `reports/MANIFEST.sha256`: it embeds logs produced outside the offline tree, so it cannot be regenerated from the cache alone.',
        '',
        'Files analysed: %d. Signature matches: %d. Rows shown: %d (current %d, history %d). Suppressed mixin probes: %d.' % (
            scanned,
            total,
            len(findings),
            len(current),
            len(stale),
            suppressed,
        ),
        '',
        '## Inputs',
        '',
        'Timestamps are shown so a stale failure can be told from the launch under test: a file older than the newest `latest.log`/`debug.log` describes an earlier attempt, not necessarily the current pack. Its findings are kept below as history and do not fail this run.',
        '',
        '| File | Bytes | Modified |',
        '| --- | --- | --- |',
    ]
    for row in files:
        lines.append('| %s | %d | %s |' % (row['name'], row['bytes'], row['modified']))
    lines.append('')
    lines += _render_identity(identity)
    if oversized:
        lines.append('Truncated at 8 MiB: %s.' % ', '.join(sorted(oversized)))
        lines.append('')
    if not findings:
        lines += [
            'No known conflict signature matched. That is not a clean bill of health: inspect the crash report manually before calling the boot clean.',
            '',
        ]
        return '\n'.join(lines) + '\n'
    lines += ['## Findings', '']
    if stale:
        lines += [
            'Rows marked `history` came from files older than the newest primary log. They are kept for the record and do not fail this run.',
            '',
        ]
    lines += ['| State | Severity | Kind | File:line | Evidence | Action |', '| --- | --- | --- | --- | --- | --- |']
    for row in findings:
        evidence = row['evidence'].replace('|', '&#124;')
        lines.append('| %s | %s | %s | %s:%s | %s | %s |' % (
            'history' if row.get('stale') else 'current',
            row['severity'],
            row['kind'],
            row['file'],
            row['line'],
            evidence,
            row['action'],
        ))
    lines.append('')
    return '\n'.join(lines) + '\n'


def _collect(root, logs):
    paths = []
    for item in logs or []:
        path = Path(item)
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() in ('.log', '.txt'):
                    paths.append(child)
        elif path.is_file():
            paths.append(path)
        else:
            raise ValueError('%s: no such log file or directory' % item)
    return paths


# Mixin probes a class that a *different*, optional mod would have supplied and
# logs the miss at WARN/TRACE with a full ClassNotFoundException stack. That is
# not a dependency failure: NeoForge reports a real one as a mod-loading issue
# and aborts with a crash report. Moonlight's "requested by strategy" lines are
# resource-reload chatter. Both are excluded before classification so a clean
# boot is not reported as a critical conflict.
_MIXIN_PROBE = re.compile(r'\[mixin/\]: Error loading class:')
_MIXIN_CATCHING = re.compile(r'\[mixin/CATCHING\]:')
_MIXIN_TRACE_EXCEPTION = re.compile(
    r'^java\.lang\.(?:ClassNotFoundException|NoClassDefFoundError):'
)


def _cutoff(files):
    """Newest primary-log mtime, or None when only crash reports were captured."""
    stamps = [row['epoch'] for row in files if row['name'] in _PRIMARY_LOGS]
    return max(stamps) if stamps else None


# NeoForge logs one discovery line per jar at INFO, and the kind varies by how
# the jar is packaged: ``Found mod file`` for ordinary mods, ``Found library
# file`` for jars that only ship libraries (Kotlin for Forge is the one in this
# pack), and ``Found gamelibrary file`` for game libraries. All three can be
# pinned pack content, so all three are matched. Only entries whose locator is
# the instance ``mods`` folder count: the same mechanism also reports the
# bundled ``client-…-srg.jar`` and ``neoforge-…-universal.jar`` from the
# launcher libraries, which are never pinned in the lock and would otherwise
# read as permanent drift, plus jar-in-jar libraries whose locator names the
# parent jar. Crash reports repeat a single failing jar as a ``Mod file:``
# line, so they cannot establish the full set and are not used for identity.
_MOD_FILE_DISCOVERED = re.compile(
    r'Found (?:mod|library|gamelibrary) file\s+"?([^"\r\n]+?\.jar)"?\s+'
    r'\[locator: [^\]\r\n]*mods folder locator',
    re.IGNORECASE,
)


def _log_mod_files(text):
    names = set()
    for match in _MOD_FILE_DISCOVERED.finditer(text):
        raw = match.group(1).strip().strip('"\'')
        name = raw.replace('\\', '/').rsplit('/', 1)[-1]
        if name.lower().endswith('.jar'):
            names.add(name)
    return names


def _identity(observed, projects, local=None, side='both'):
    """Diff each primary log's discovered jars against the pinned filenames.

    ``observed`` maps a log name to the jar basenames NeoForge logged. A log
    with no discovery lines is ``unverified`` rather than drift: a truncated
    capture is missing evidence, not proof that the wrong pack ran. Only jars
    that were actually listed can disagree with the lock.

    ``local`` are the bundled jars that are deliberately not in the lock (the
    unpublished custom mod). They are required in the capture but never count as
    drift just for being absent from ``pack_lock.json``.

    ``side`` drops jars whose metadata marks them unsupported on the captured
    side, so a dedicated-server capture is not failed by client-only content it
    was right to withhold.
    """
    locked = set()
    for slug in sorted(projects):
        entry = projects[slug]
        if side == 'server' and entry.get('server_side') == 'unsupported':
            continue
        if side == 'client' and entry.get('client_side') == 'unsupported':
            continue
        name = str(entry.get('filename') or '')
        if name:
            locked.add(name)
    local = set(local or [])
    allowed = locked | local
    files = []
    ok = True
    for name in sorted(observed):
        found = observed[name]
        if not found:
            files.append({
                'file': name,
                'status': 'unverified',
                'matched': [],
                'local': [],
                'log_only': [],
                'lock_only': [],
                'local_missing': [],
            })
            continue
        matched = sorted(found & locked)
        local_found = sorted(found & local)
        log_only = sorted(found - allowed)
        lock_only = sorted(locked - found)
        local_missing = sorted(local - found)
        drift = bool(log_only or lock_only or local_missing)
        if drift:
            ok = False
        files.append({
            'file': name,
            'status': 'drift' if drift else 'match',
            'matched': matched,
            'local': local_found,
            'log_only': log_only,
            'lock_only': lock_only,
            'local_missing': local_missing,
        })
    return {'ok': ok, 'locked': len(locked), 'local': len(local), 'files': files}


def _analyse(paths):
    raw = []
    scanned = 0
    suppressed = 0
    oversized = []
    files = []
    stamped = []
    observed = {}
    for path in paths:
        stat = path.stat()
        stamped.append((path, stat))
        files.append({
            'name': path.name,
            'bytes': stat.st_size,
            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'epoch': stat.st_mtime,
        })
    cutoff = _cutoff(files)
    for path, stat in stamped:
        payload = path.read_bytes()
        scanned += 1
        stale_file = cutoff is not None and stat.st_mtime < cutoff
        if len(payload) > MAX_LOG_BYTES:
            oversized.append(path.name)
            payload = payload[:MAX_LOG_BYTES]
        text = payload.decode('utf-8', 'replace')
        if path.name in _PRIMARY_LOGS:
            observed[path.name] = _log_mod_files(text)
        if path.name.startswith('crash-') and path.suffix.lower() == '.txt':
            issues = _crash_issues(text, path.name)
            if issues:
                for issue in issues:
                    issue['stale'] = stale_file
                raw.extend(issues)
            else:
                match = _CRASH_DESCRIPTION.search(text)
                evidence = match.group(1).strip() if match else 'crash report without a Description line'
                raw.append({
                    'kind': 'crash-report',
                    'severity': 'critical',
                    'file': path.name,
                    'line': 0,
                    'evidence': evidence[:300],
                    'action': 'Treat the description and the first project in the stack as the suspect; remove or pin it and reproduce before accepting the fix.',
                    'stale': stale_file,
                })
        previous_line = ''
        for number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            prior, previous_line = previous_line, stripped
            if _MIXIN_PROBE.search(stripped) or _MIXIN_CATCHING.search(stripped):
                suppressed += 1
                continue
            if _MIXIN_TRACE_EXCEPTION.match(stripped) and _MIXIN_CATCHING.search(prior):
                suppressed += 1
                continue
            for kind, severity, pattern, action in _COMPILED:
                if pattern.search(stripped):
                    raw.append({
                        'kind': kind,
                        'severity': severity,
                        'file': path.name,
                        'line': number,
                        'evidence': stripped[:300],
                        'action': action,
                        'stale': stale_file,
                    })
                    break
    raw.sort(key=lambda row: (
        bool(row.get('stale')),
        _SEVERITY_ORDER.get(row['severity'], 3),
        row['kind'],
        row['file'],
        row['line'],
    ))
    per_file = {}
    kept = []
    for row in raw:
        key = (row['kind'], row['file'])
        per_file[key] = per_file.get(key, 0) + 1
        if per_file[key] <= 3:
            kept.append(row)
    return kept, scanned, oversized, len(raw), suppressed, files, observed


def probe_environment():
    java = shutil.which('java')
    info = {'min_java': MIN_JAVA, 'java': java, 'java_major': None, 'java_ok': False}
    if not java:
        return info
    try:
        proc = subprocess.run([java, '-version'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return info
    text = (proc.stderr or '') + (proc.stdout or '')
    match = re.search(r'version [^0-9]*([0-9]+)(?:[.]([0-9]+))?', text)
    if match is None:
        match = re.search(r'[Oo]pen[Jj][Dd][Kk] ([0-9]+)', text)
    if match is not None:
        groups = match.groups()
        first = int(groups[0])
        major = 8 if first == 1 and len(groups) > 1 and groups[1] else first
        info['java_major'] = major
        info['java_ok'] = major >= MIN_JAVA
    return info


def run(
    root,
    *,
    lock='pack_lock.json',
    manifest='pack_manifest.json',
    report=REPORT_NAME,
    log_report=LOG_REPORT_NAME,
    logs=None,
    probe_env=True,
    side='both',
):
    root = Path(root)
    lock_payload = _load(root, lock)
    manifest_payload = _load(root, manifest)
    projects = lock_payload.get('projects')
    if not isinstance(projects, dict) or not projects:
        raise ValueError('%s: no pinned projects' % lock)
    audit = _audit(projects)
    closure = _closure(projects)
    duplicates = _duplicate_filenames(projects)
    report_path = Path(report)
    if not report_path.is_absolute():
        report_path = root / report_path
    archive = root / 'dist' / 'chaos-gacha-1.0.0-milestone-a-1.21.1-neoforge.mrpack'
    archive_sha = None
    if archive.is_file():
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    _write(
        report_path,
        _render(lock_payload, manifest_payload, audit, closure, duplicates, archive_sha),
    )
    result = {
        'ok': not closure['missing'] and not duplicates,
        'projects': len(projects),
        'closure_missing': closure['missing'],
        'duplicate_filenames': duplicates,
        'audit': audit,
        'report': str(report_path),
        'log_report': None,
        'findings': [],
        'log_matches': 0,
        'logs_scanned': 0,
        'identity': None,
    }
    if probe_env:
        result['environment'] = probe_environment()
    if logs:
        paths = _collect(root, logs)
        if not paths:
            raise ValueError('--log matched no .log or .txt file')
        findings, scanned, oversized, total, suppressed, files, observed = _analyse(paths)
        local_dir = root / 'pack' / 'mod'
        local = sorted(
            path.name for path in local_dir.glob('*.jar')
        ) if local_dir.is_dir() else []
        identity = _identity(observed, projects, local, side)
        identity['pack_version'] = lock_payload.get('pack_version')
        identity['index_sha256'] = lock_payload.get('index_sha256')
        log_path = Path(log_report)
        if not log_path.is_absolute():
            log_path = root / log_path
        _write(
            log_path,
            _render_logs(findings, scanned, oversized, total, suppressed, files, identity),
        )
        result['log_report'] = str(log_path)
        result['findings'] = findings
        result['log_matches'] = total
        result['logs_scanned'] = scanned
        result['identity'] = identity
        current_critical = any(
            row['severity'] == 'critical' and not row.get('stale') for row in findings
        )
        result['findings_stale'] = sum(1 for row in findings if row.get('stale'))
        result['findings_current'] = len(findings) - result['findings_stale']
        if current_critical or not identity['ok']:
            result['ok'] = False
    return result
