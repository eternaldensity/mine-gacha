# Custom mod contract (`gacha`)

Phase 4 starts configuration-first: before any Java exists, this directory fixes
the custom mod's data contract so the code can be written against it. Every file
here is validated offline by `chaoslab datapack`, regenerated into
`reports/datapack_report.md` by the `chaoslab verify` gate.

Status: the schema, the seed datapack, the default config and the Java MVP are in
place: ticket item with data components, the Gacha Machine, the roll and rarity
engine, the entry registry and adapters for items, attributes and effects, plus a
debug command. Feats, curses, Power Score, the GLMs and persistence are not yet
implemented. `./gradlew build test` passes; the dedicated-server boot is the next
verification step.

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
  `data/<namespace>/<registry>/<path>.json` is `<namespace>:<path>`. The
  validator rejects a registry directory it has no schema for.
- **Registries**: `entry`, `feat`, `curse`, `module`, plus NeoForge's
  `loot_modifiers` and standard item `tags`.
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
