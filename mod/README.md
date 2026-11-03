# Custom mod contract (`gacha`)

Phase 4 starts configuration-first: before any Java exists, this directory fixes
the custom mod's data contract so the code can be written against it. Every file
here is validated offline by `chaoslab datapack`, regenerated into
`reports/datapack_report.md` by the `chaoslab verify` gate.

Status: Phase 4 is implemented. The configuration contract (schemas, validator,
seed datapack, default config) and the Java MVP are in place: ticket item with
data components, the Gacha Machine, the roll and rarity engine, the entry
registry and adapters for items, attributes and effects, persistence, the
config-driven Power Score, feats, curses, the two loot GLMs, code-granted
advancements and a starter quest skeleton. The player-in-the-loop path
(ticket → roll → reward → Power Score → advancement) is covered by headless
NeoForge GameTests. `./gradlew build test` and `./gradlew runGameTestServer`
pass.

## Layout

| Path | Ships | Purpose |
| --- | --- | --- |
| `schema/` | no | JSON Schemas, one per registry plus the config |
| `datapack/` | yes | the mod's built-in `data/` tree (modules, loot modifiers, starter entries) |
| `config/` | yes | default server config installed on first run |
| `examples/` | no | fixtures that exercise every schema branch; deleted or replaced when real content lands |
| `src/` | yes | Java sources and resources |
| `build.gradle` | no | Gradle build (NeoForge ModDevGradle 2.0.91) |

## Conventions

- **Ids are derived from file paths**, never written into the file:
  `data/<namespace>/gacha/<registry>/<path>.json` is `<namespace>:<path>` for
  the `gacha` datapack registries, and `data/<namespace>/<registry>/<path>.json`
  for vanilla-style registries. The validator rejects a registry directory it
  has no schema for.
- **Registry paths follow NeoForge's prefixing rule.** A registry key outside
  `minecraft` is stored with its namespace as an extra directory
  (`CommonHooks.prefixNamespace`), so `gacha:entry` loads from
  `data/<pack_ns>/gacha/entry/`, not `data/<pack_ns>/entry/`. In this mod's own
  pack that is `datapack/data/gacha/gacha/entry/`.
- **Registries**: `entry`, `feat`, `curse`, `module` (all under
  `data/<pack_ns>/gacha/`), plus NeoForge's `loot_modifiers` and standard item
  `tags`.
- **Tickets** carry the roll triple `{min, avg, max}`, a category, up to 6
  Advantage, an optional filter and a cosmetic depth (PROJECT_PLAN.md 6.3).
- **Entries** carry kind, rarity, an optional duplicate policy (defaults
  derive from kind per 6.6), an adapter that applies the reward, and the
  `on_acquire` / `on_loss` / `on_resolve` hooks of 6.5.
- **Curses** carry a d20 severity, a mechanical hook, a machine-checkable
  Resolve and the `mature` flag (6.8 / D2).
- **Loot modifiers**: `loot_modifiers/add_ticket_<band>.json` carry the accepted
  D1 allowlist (305 tables from the 15 structure candidates) with the band's
  preset. An empty `tables` list is a valid no-op. Removal files are not shipped
  yet: the strip list (which stacks convert; 6.12 layer 3) and the depth
  mapping's "occasional" upgrade are open items in `PROJECT_PLAN.md` §11.
- **Config** is JSON (`config/power_score.json`), shipped as the answered D3
  default; if the code phase prefers NeoForge TOML, the schema and file move
  together.

## Build

Java 21 is required (the Temurin build used locally is at
`~/.local/opt/jdk21`). The Gradle wrapper downloads Gradle 8.14.2 and the
NeoForge userdev artifacts on the first run.

```sh
cd mod
JAVA_HOME="$HOME/.local/opt/jdk21" ./gradlew build test
```

## Run (development)

```sh
cd mod
JAVA_HOME="$HOME/.local/opt/jdk21" ./gradlew runServer
```

Accept the EULA in `mod/run/eula.txt` on the first run. In game or from the
console:

```text
/gacha ticket give @s bronze
/gacha machine give @s
```

Place the machine and right-click it while holding a ticket. Only tickets with
Advantage 1 resolve in this build; the result chooser is not implemented yet.
The ticket and machine currently reuse vanilla textures as placeholders.

To try it in a normal client:

```sh
cd mod
JAVA_HOME="$HOME/.local/opt/jdk21" ./gradlew runClient
```

Create a world with cheats enabled, then run the two commands above; `/gacha`
requires gamemaster permission. Heracles is not on the development classpath,
so the quest chapter does not render yet (Phase 5 installs the pack).

## End-to-end tests

The ticket → roll → reward → Power Score → advancement path runs headlessly
against a mock server player:

```sh
cd mod
JAVA_HOME="$HOME/.local/opt/jdk21" ./gradlew runGameTestServer
```

`GachaGameTest` covers three adjacent paths: a narrow ticket resolved through
`MachineService` (ownership, inventory, Power Score, `first_roll`); the same
roll driven by right-clicking a placed machine block (the full player path);
and a repeat trait roll (the insight duplicate policy converts it to Bronze
Residue and awards `first_duplicate`). The empty structure it runs in lives at
`src/main/resources/data/gacha/structure/gachagametest.empty.nbt`; the GameTest
template id is `gacha:gachagametest.empty` (a dot, not a slash). Add the
`gameTestServer` run configuration to `build.gradle` if you add more tests.

Quests are Heracles content and are not on the GameTest classpath: Heracles'
quest-sync payload cannot be sent to a mock player. The quest files in
`pack/quests/` hang off the same advancements the tests verify, so the
advancement assertions are the quest-side E2E check.

## Validation (offline)

```sh
python3 -m chaoslab datapack              # validate + write reports/datapack_report.md
python3 -m chaoslab datapack --selftest   # prove the validator rejects bad input
python3 -m chaoslab datapack --json       # machine-readable summary
make check                                # the full offline gate, including the report
```

The validator implements a JSON Schema 2020-12 **subset** and fails on unknown
keywords, so a typo in a schema cannot silently weaken it. Supported:
`type`, `enum`, `const`, `required`, `properties`, `additionalProperties`,
`items`, `minItems`, `maxItems`, `uniqueItems`, `minProperties`,
`maxProperties`, `minLength`, `maxLength`, `pattern`, `minimum`, `maximum`,
`exclusiveMinimum`, `exclusiveMaximum`, `oneOf`, `anyOf`, local `$ref` to
`$defs`. `oneOf`/`anyOf` are terminal at a node.

Rules a schema cannot express live in `chaoslab/datapack.py`: derived-id
uniqueness, adapter and familiar rules, duplicate policy, `attach_modifier`
references, gamble-table coverage, power-score arithmetic, ticket roll ordering
and the semantic checks the engine relies on.
