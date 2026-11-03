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

### Updating a Prism instance without a full reinstall

Prism's "update pack from file" re-runs the install and re-fetches every
`files[]` entry, even when the upstream jars are unchanged. For a local import
it also leaves `ManagedPackVersionName` empty, so the success dialog reads
"pack version  successfully" with a gap (the `.mrpack` itself has
`"versionId": "1.0.0-milestone-a"`; Prism only records a managed version for
Modrinth-hosted packs). Neither is something the archive can change.

During iteration only the local content moves, so patch the instance directly:

```sh
INSTANCE=/path/to/PrismLauncher/instances/<name>/minecraft
cp pack/mod/gacha-*.jar "$INSTANCE/mods/"
mkdir -p "$INSTANCE/config/gacha" "$INSTANCE/config/heracles/quests"
cp mod/config/power_score.json "$INSTANCE/config/gacha/"
cp pack/quests/*.json "$INSTANCE/config/heracles/quests/"
```

Use "update pack from file" only when the pinned mod list or overrides change.

## Loot injection

NeoForge only applies a global loot modifier that is named in
`data/neoforge/loot_modifiers/global_loot_modifiers.json`; a modifier file that
exists but is not listed is silently inert. The mod ships that manifest for the
four band modifiers, and `chaoslab datapack` rejects either direction of drift
(an unlisted modifier file, or a listed id with no file).

The per-band table allowlists cover the vanilla chest tables and the shipped
pack's structure chests (536 tables total), including the vanilla village and
ruined-portal chests and Apotheosis' tome tower. Each table appears in exactly
one band; the validator rejects duplicates.

## Entry content

The corpus is imported as thematic entries (4,193 total): items are
`gacha:item_tag` rolls over broad tags (`gacha:weapon`, `armor`, `tool`, `food`,
`magic`, `material`, `summon`, `vehicle`, `treasure`); traits are permanent
attribute modifiers or infinite-effect auras; abilities and skills are timed
effects; familiars are spawn eggs with a mortal lifecycle marker. The named
corpus items/abilities are reskins, not exact custom implementations. Eight
race traits set Neo Origins origins; the remaining `race-change` entries wait
for a mapping policy.

## Races / origins

Neo Origins is pinned in the pack (60 projects). Race traits use a
`gacha:origin` adapter with `layer: neoorigins:origin`; the custom mod sets the
origin through Neo Origins' `OriginChangeService` (reflectively, so it loads
without the mod). Origins in the same layer replace each other in the owned set.
The mod ships 77 origins and 2 layers; custom origin packs, if we outgrow them,
go under `config/originpacks/`.

## Quests

`quests/` holds Heracles quest JSON. Per the plan (§7 row 25), Odyssey Quests
is the settled quest layer; the mod does not depend on Heracles at runtime, so
this is pack content and is installed into the dedicated server / instance:

```text
<instance>/config/heracles/quests/
```

Heracles reads `display.title` and `display.subtitle` with
`ComponentSerialization.FLAT_CODEC`, which expects a **string containing JSON**,
for example `"title": "{\"text\":\"First Roll\"}"`. A plain string falls back to
the default "New Quest" without an error, so the pack validator checks the form.
Each quest must also name at least one group (the chain uses `Main`) or it is
invisible in the quest book.

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
