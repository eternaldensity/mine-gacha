# Pack declaration

Target: Minecraft 1.21.1 / neoforge. Sourcing: Modrinth only. Delivery: `.mrpack` referencing Modrinth CDN URLs; jars are not bundled.

Generated from `pack_manifest.json` by `chaoslab lint`. Edit the manifest, not this file: the manifest is the declaration and this document plus `reports/pack_report.md` are rendered from it, so the prose cannot drift from what the gate checks.

## Decisions applied

- **D4** — Option B: milestone A is core + seed + support + add-on; outside the promoted sections (Tech, Dimensions / worldgen, Quest systems) adoption, trial and defer wait for milestone B, while a promoted section ships whole; libraries arrive transitively.
- **D4_magic** — Two magic systems only: Ars Nouveau and Iron's Spells. Primal Magick and Golem Magicka stay resolvable alternatives at milestone B.
- **D4_quests** — The quest layer ships in milestone A, so the Quest systems section is promoted.
- **D4_tech** — Full tech section ships in milestone A (Create, Mekanism, Oritech, AnvilCraft, Electrodynamics, plus the section's add-ons).
- **D4_worldgen** — No terrain trimming: every worldgen and structure candidate stays in the manifest at milestone A or milestone B; none is dropped.
- **D5** — Replacements for the seven no-build slugs are ratified as recorded; asterism-arcanum and lootr are excluded by policy.
- **D6** — Delivery option A: `.mrpack` referencing Modrinth CDN URLs, jars are not bundled.

## Milestone A

34 candidates (add-on 1, content 6, core 16, library 4, support 7), the release target.

| Section | Candidate | Role | Verdict | Server side | Why |
| --- | --- | --- | --- | --- | --- |
| Add-ons: Create / Aeronautics | create-aeronautics | add-on | include (add-on) | required | verdict: include (add-on) |
| Dimensions / worldgen | aether | core | include (core) | required | verdict: include (core) |
| Dimensions / worldgen | biomes-o-plenty | core | include (core) | required | verdict: include (core) |
| Dimensions / worldgen | terralith | core | include (core) | required | verdict: include (core) |
| Endgame / gamebreaking | re-avaritia | content | include (seed) | required | verdict: include (seed) |
| Magic | ars-nouveau | core | include (core) | required | verdict: include (core) |
| Magic | irons-spells-n-spellbooks | core | include (core) | required | verdict: include (core) |
| Mobs / familiars | alexs-mobs-continued | content | include (seed) | required | verdict: include (seed) |
| Mobs / familiars | alshanexs-familiars | core | include (core) | required | verdict: include (core) |
| Mobs / familiars | mobs-of-mythology | content | include (seed) | required | verdict: include (seed) |
| Mobs / familiars | mowzies-mobs | content | include (seed) | required | verdict: include (seed) |
| Quest systems | odyssey-quests | support | defer (promoted) | required | section promoted (Quest systems); verdict: defer |
| RPG progression | apotheosis | core | include (core) | required | verdict: include (core) |
| RPG progression | artifacts | core | include (core) | required | verdict: include (core) |
| RPG progression | curios | library | include (library) (override) | required | fit host for item-equipment (accessory slots); no milestone A candidate requires it, so it needs an explicit include |
| RPG progression | justleveling-fork | core | include (core) | required | verdict: include (core) |
| RPG progression | simply-swords | core | include (core) | required | verdict: include (core) |
| Races / origins | neo-origins | content | defer (override) | required | race-change traits need an origin layer; Neo Origins is a self-contained 1.21.1 NeoForge Origins port with 77 origins and 2 layers, and the server boot test is clean |
| Required dependencies (libraries pulled by candidates) | familiarslib | library | review (unused library) (override) | required | alshanex_familiars refuses to load without familiarslib 1.0.0+ (declared in the jar manifest); the Modrinth version metadata for the pinned build omits the link, so the closure cannot discover it |
| Required dependencies (libraries pulled by candidates) | irons-lib | library | include (library) (override) | required | irons_spellbooks refuses to load without irons_lib [1.21.1-2,1.21.1-3) (declared in the jar manifest); the pinned build's Modrinth metadata omits it |
| Required dependencies (libraries pulled by candidates) | playeranimator | library | include (library) (override) | required | irons_spellbooks refuses to load without playeranimator 2.0.1+1.21.1 (declared in the jar manifest); the pinned build's Modrinth metadata omits it |
| Support / UI | jade | support | include (support) | optional | verdict: include (support) |
| Survey additions (popular 1.21.1 NeoForge packs) | trading-post | core | include (core) | required | verdict: include (core) |
| Survey additions, round 2 (content, worldgen, quest hooks) | natures-compass | support | include (support) | required | verdict: include (support) |
| Survey additions, round 2 (content, worldgen, quest hooks) | polymorph | support | include (support) | required | verdict: include (support) |
| Survey additions, round 2 (content, worldgen, quest hooks) | supplementaries | support | include (support) | required | verdict: include (support) |
| Tech | anvilcraft | core | include (core) | required | verdict: include (core) |
| Tech | create | core | include (core) | required | verdict: include (core) |
| Tech | create-stuff-additions | support | trial (promoted) | required | section promoted (Tech); verdict: trial |
| Tech | electrodynamics | core | include (core) | required | verdict: include (core) |
| Tech | energized-power | content | include (seed) | required | verdict: include (seed) |
| Tech | mekanism | core | include (core) | required | verdict: include (core) |
| Tech | oritech | core | include (core) | required | verdict: include (core) |
| Tech | tempad | support | defer (promoted) | required | section promoted (Tech); verdict: defer |

## Carried transitively

- `apothic-attributes` (library, declared T) — required by apotheosis, apothic-enchanting
- `apothic-enchanting` (library, declared T) — required by apotheosis
- `apothic-spawners` (library, declared T) — required by apotheosis
- `architectury-api` (library, declared T) — required by justleveling-fork, mobs-of-mythology, oritech, simply-swords, simply-tooltips
- `athena-ctm` (library, declared T) — required by oritech
- `azurelib` (library, declared T) — required by mobs-of-mythology
- `cloth-config` (library, declared T) — required by justleveling-fork
- `codxlib` (library, declared T) — required by alexs-mobs-continued
- `fzzy-config` (library, declared T) — required by simply-swords, simply-tooltips
- `geckolib` (library, declared T) — required by mowzies-mobs, oritech
- `glitchcore` (library, declared T) — required by biomes-o-plenty
- `kotlin-for-forge` (library, declared T) — required by fzzy-config, tempad
- `lithostitched` (library, declared T) — required by terralith
- `moonlight` (library, declared T) — required by supplementaries
- `owo-lib` (library, declared T) — required by aether
- `patchouli` (library, declared T) — required by apotheosis
- `placebo` (library, declared T) — required by apotheosis, apothic-attributes, apothic-enchanting, apothic-spawners
- `puzzles-lib` (library, declared T) — required by trading-post
- `resourceful-config` (library, declared T) — required by tempad
- `resourceful-lib` (library, declared T) — required by odyssey-quests, tempad
- `sable` (library, declared T) — required by create-aeronautics
- `simply-tooltips` (library, declared T) — required by simply-swords
- `smartbrainlib` (library, declared T) — required by mobs-of-mythology
- `terrablender` (library, declared T) — required by biomes-o-plenty
- `voltaic` (library, declared T) — required by electrodynamics
- `yacl` (library, declared T) — required by justleveling-fork

## Deferred to milestone B

- **Add-ons: Apotheosis** (2): apotheosis-addon-compat, apothic-flux
- **Add-ons: Ars Nouveau** (4): ars-additions, ars-controle, ars-creo, reliquified-ars-nouveau
- **Add-ons: Create / Aeronautics** (8): create-aeronautics-compatability, create-aeronautics-offroad-addon-stickywheels, create-lift-n-load, create-magneutica, create-steel-addon, create-wizardry, createaddoncompatibility, waystones-sable
- **Add-ons: Iron's Spells** (4): cataclysm-spellbooks, fundamental-principles-irons-spells-addon, paladin-spells-irons-spells-addon, winds-spellbooks
- **Compatibility** (3): accessories-compat-layer, better-compatibility-checker, mekanism-tfmg-compat
- **Magic** (2): golem-magicka, primal-magick
- **Quest systems** (1): justquests
- **Survey additions (popular 1.21.1 NeoForge packs)** (4): functional-storage, structory, toms-storage, waystones
- **Survey additions, round 2 (content, worldgen, quest hooks)** (24): cerulean-advancements, create-aeroworks, create-big-cannons, create-dragons-plus, create-enchantment-industry, create-steam-n-rails-1.21.1, explorers-compass, farmers-delight, serene-seasons, sophisticated-backpacks, structory-towers, villager-names-serilum, what-are-they-up-to, yungs-better-desert-temples, yungs-better-dungeons, yungs-better-end-island, yungs-better-jungle-temples, yungs-better-mineshafts, yungs-better-nether-fortresses, yungs-better-ocean-monuments, yungs-better-strongholds, yungs-better-witch-huts, yungs-bridges, yungs-extras
- **Survey additions, round 3 (modpack harvest: content and progression)** (13): ae2, create-contraption-terminals, create-diesel-generators, create-encased, createaddition, deeperdarker, dungeons-and-taverns, l_enders-cataclysm, nullscape, oh-the-biomes-weve-gone, regions-unexplored, snow-real-magic, towns-and-towers

## Excluded

- `lootr` — policy exclusion: §6.12: chests are shared and one-shot; Lootr makes them per-player instanced
- `asterism-arcanum-addon-for-irons-spells-and-spellbooks` — policy exclusion: 1.21.1 build requires expandability, which is CurseForge-only; Modrinth-only policy (§7 row 27)
- `expandability` — verdict: excluded (no build)
- `botania` — verdict: excluded (no build)
- `thermal-expansion` — verdict: excluded (no build)
- `alexs-mobs` — verdict: excluded (no build)
- `alexs-caves` — verdict: excluded (no build)
- `ice-and-fire-dragons` — verdict: excluded (no build)
- `blue-skies` — verdict: excluded (no build)
- `relics` — verdict: excluded (no build)

## Gate

12/12 lint checks pass.
