# Custom mod contract (`gacha`)

Phase 4 starts configuration-first: before any Java exists, this directory fixes
the custom mod's data contract so the code can be written against it. Every file
here is validated offline by `chaoslab datapack`, regenerated into
`reports/datapack_report.md` by the `chaoslab verify` gate.

Status: schema and seed only. No Java, no runtime behaviour.

## Layout

| Path | Ships | Purpose |
| --- | --- | --- |
| `schema/` | no | JSON Schemas, one per registry plus the config |
| `datapack/` | yes | the mod's built-in `data/` tree (currently the two machine modules) |
| `config/` | yes | default server config installed on first run |
| `examples/` | no | fixtures that exercise every schema branch; deleted or replaced when real content lands |

The datapack tree mirrors the future mod jar (`data/` at the jar root, no
standalone `pack.mcmeta`). When the Gradle workspace exists, `datapack/` and
`config/` move into the mod's resources and `examples/` becomes test data.

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
- **Loot modifiers** select tables by explicit allowlist; an empty list is a
  valid no-op and is the committed default until D1 is answered (6.12, row 23).
- **Config** is JSON (`config/power_score.json`), shipped as the answered D3
  default; if the code phase prefers NeoForge TOML, the schema and file move
  together.

## Validation

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
uniqueness, adapter requirements, familiar lifecycle, duplicate policy,
`attach_modifier` references, gamble-table coverage, power-score arithmetic and
ticket roll ordering.
