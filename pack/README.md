# Pack content (`pack/`)

Content that ships with the pack rather than the custom mod. Currently the
Odyssey Quests (Heracles) skeleton, the local mod jar bundled into the archive,
and the packaging notes.

## Archive assembly

`make pack` builds the mod, refreshes `pack/mod/gacha-<version>.jar`, and runs
`chaoslab build`. The archive has two kinds of content:

- **CDN mods.** The 59 pinned projects in `pack_lock.json` are `files[]`
  entries in `modrinth.index.json` with Modrinth download URLs. They are not
  bundled (delivery option A, §7 row 31).
- **Overrides.** The custom mod is not published, so `chaoslab build` bundles
  three local sources under `overrides/`:
  - `overrides/mods/gacha-<version>.jar` from `pack/mod/`;
  - `overrides/config/gacha/power_score.json` from `mod/config/`;
  - `overrides/config/heracles/quests/*.json` from `pack/quests/`.

`pack/mod/gacha-<version>.jar` is a tracked release artifact because the offline
gate cannot invoke Gradle. Refresh it with `make mod-jar` after any mod change;
`make pack` does both. `make check` verifies that the committed archive is
reproducible from the committed jar and the cached Modrinth metadata.

## Quests

`quests/` holds Heracles quest JSON. Per the plan (§7 row 25), Odyssey Quests
is the settled quest layer; the mod does not depend on Heracles at runtime, so
this is pack content and is installed into the dedicated server / instance:

```text
<instance>/config/heracles/quests/
```

The three starter quests form one chapter chain:

| Quest | Task | Depends on |
| --- | --- | --- |
| `first_roll` | advancement `gacha:first_roll` | — |
| `first_duplicate` | advancement `gacha:first_duplicate` | `first_roll` |
| `power_ten` | advancement `gacha:power_ten` | `first_duplicate` |

The advancements are code-granted by the mod:

- `gacha:first_roll` on the first successful ticket resolution;
- `gacha:first_duplicate` on the first duplicate;
- `gacha:power_ten` when the Power Score reaches 0.10.

This is the skeleton, not the final quest set: the plan asks for five to seven
chapters mapped onto the tier bands (first rolls, tier gates, curse management,
dimension/boss milestones, endgame). Author the rest in the Heracles in-game
editor and export the JSON into `quests/`.
