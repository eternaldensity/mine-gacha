# Chaos Gacha for Minecraft — Project Plan

**Status legend** — Settled: confirmed by the user. Design: decided during design work, reversible but currently assumed. Proposed: recommendation awaiting a decision. Open: unresolved.

## 1. Goal

Recreate the experience of the Chaos Gacha inside Java Minecraft as a modpack plus a small custom mod. Existing mods supply content (items, structures, mounts, magic, bosses); the custom mod supplies only the mechanics no mod provides. This is not a 1:1 port of gacha entries: entries may be reworked, replaced or omitted where Minecraft has no implementation path.

## 2. Phase

Information discovery. Agreed sequence: mechanics spec, then mod survey, then iterate on the spec. This document is the mechanics spec plus the decision record. It does not choose the final mod list.

## 3. Target platform

- Java Edition, **NeoForge 1.21.1** — Settled.
- Rationale: Create Aeronautics was believed to be available only on 1.21.1 NeoForge. Older versions are excluded; newer versions sharply reduce mod availability.
- **Verified** (resolved offline from the cached Modrinth response, 2026-10-21): Create Aeronautics does have a 1.21.1 NeoForge build — version `1.3.2+mc1.21.1`, release type `release`, published 2026-08-29, file `create-aeronautics-bundled-1.21.1-1.3.2.jar` (33,123,131 bytes). 8 versions were checked for the 1.21.1/neoforge filter. The project declares `client_side: required` and `server_side: required`, so it needs to be on both sides of a dedicated server.
- Consequence: the 1.21.1 NeoForge decision is no longer conditional on this check.

## 4. What the source material does

Evidence drawn from `ChaosGacha/`: `Chaos Gacha Doc.md`, `gachafiles/ability.txt`, `trait.txt`, `item.txt`, `familiar.txt`, `Gacha.py`, `web/data/curses.txt`, `web/data/curses.js`, `web/js/curse-app.js`.

### 4.1 Rarity

- Continuous scalar 0.1 to 9.9, not a discrete tier.
- Ten display bands: Trash 0.1-0.9, Common 1.0-1.9, Uncommon 2.0-2.9, Rare 3.0-3.9, Elite 4.0-4.9, Epic 5.0-5.9, Legendary 6.0-6.9, Mythical 7.0-7.9, Divine 8.0-8.9, Transcendant 9.0-9.9.
- Rolls are parameterised by (minimum, average, maximum); bounded and unimodal around the average.
- Preset ticket names move the average, not the shape.

### 4.2 Ticket grammar

`[Prefix] [Rarity] [Category] Gacha Ticket`

- Prefix: Advantage only. Advantage means roll N times and **pick between the results** — a player choice, not an automatic keep-best.
- Category: ability, trait, skill, item, familiar, or Random (1-in-5). Themed tickets filter by tag.
- Ceiling observed in source data: 6x Advantage meta-tickets.
- Tickets themselves exist as gacha entries in `item.txt`.

Ticket-name to result-band mapping as inferred during discovery:

| Ticket | Result band centred on |
| --- | --- |
| Bronze | Common |
| Silver | Uncommon |
| Gold | Rare |
| Platinum | Elite |
| Diamond | Epic |
| Legendary | Legendary |
| Mythical | Mythical |
| Divine | Divine |

Twelve windows, not eight. The eight classic windows mirror `Gacha.py`'s preset block; `trash`, `aluminium`, `wild` and `transcendent` are the fork's extended tiers, defined in the fork's web exporter and reproduced by `chaoslab/simulate.py`:

| Ticket | min | avg | max |
| --- | --- | --- | --- |
| Trash | 0.1 | 0.5 | 1.5 |
| Bronze | 0.1 | 1.3 | 3.3 |
| Silver | 0.5 | 2.3 | 4.3 |
| Gold | 1.5 | 3.3 | 5.3 |
| Aluminium | 1.0 | 4.0 | 6.0 |
| Platinum | 2.5 | 4.3 | 6.3 |
| Diamond | 3.5 | 5.3 | 7.3 |
| Legendary | 4.5 | 6.3 | 8.3 |
| Mythical | 5.5 | 7.3 | 9.3 |
| Wild | 1.0 | 5.0 | 10.0 |
| Divine | 6.5 | 8.3 | 10.0 |
| Transcendent | 7.5 | 9.3 | 10.0 |

Wild is flat: exponent 1 and a ±1.0 entry window instead of the usual exponent 4 and ±0.2.

### 4.3 Feats (primary economy)

- Feats are the main ticket source and what makes gambling possible (doc line ~120).
- Two axes: objective impressiveness and impressiveness relative to current power (doc ~123-127).
- Non-decomposability: one action yields one feat; a kill does not also pay for every incidental descriptor (doc ~129-139). This is the anti-farm rule.
- Diminishing returns within a feat line: e.g. 10 pickpockets → Bronze Skill, 50 → Silver, then nothing (doc ~143).
- Tiers: Trash, Bronze, Silver, Gold, Platinum, Aluminium (joke tier between Gold and Platinum), Diamond, Legendary, Mythical, Divine, plus Wild (off-scale).
- Category heuristic: power/defeat → Ability; resilience/status quo → Trait; expertise → Skill; acquisition/heists → Item; companionship/taming/diplomacy → Familiar. Author discretion is explicitly allowed.
- Starting feats come from the origin (Transmigrated, Native, Take Over, Changed Fate), not from play.

### 4.4 Curses (borrowed power)

- Optional. Taken when ticket income feels insufficient for the challenge at hand (doc ~332).
- d20 severity: 1-6 Minor, 7-13 Medium, 14-17 Major, 18-19 Severe, 20 Ultimate.
- Payouts: Minor → Gold random; Medium → Gold random with 2x Advantage; Major → Gold with category choice; Severe → Platinum random; Ultimate → Platinum with category choice.
- Each curse has a severity, a description and a Resolve condition. The Resolve condition is what makes it content rather than a tax.

### 4.5 Tags and meta quirks

- Entries carry `#(Tag:...)` markers; suffixes `+` and `-` are semantic and must be preserved.
- `(Meta:...)` clusters: ticket-economy quirks, node/tree quirks, ability modifiers, charges/restock, and `(Gacha)` system entries.
- Node/tree quirks presuppose a visible progression graph; explicitly out of scope.
- Ticket-economy quirks are in scope as machine modules.
- Ability modifiers and charges/restock are general entry properties.

## 5. Design principles

1. **Voluntary risk.** Nothing is forced. Curses are chosen.
2. **Bounded, legible luck.** Bell-shaped rolls around a stated average; quality is manipulable through ticket tier and Advantage.
3. **Curses are content, not a tax.** Every curse needs a machine-checkable Resolve.
4. **Conservation of loot.** Anything removed from a chest table must be reachable through a ticket.
5. **Anti-farm.** One feat equals one grant, enforced by stable feat IDs and a granted set.
6. **Legibility over ceremony.** The machine is the ritual; extra opacity (e.g. sealed tickets) is not.

## 6. Mechanics spec v0.4

### 6.1 Three economies

| Source | Rewards | Failure mode if dominant |
| --- | --- | --- |
| Feats | Competence, escalation | Grind; nothing left when capped |
| Chests | Exploration, risk-taking | Structure-rushing replaces play |
| Curses | Impatience | Debt spiral, slot lock |

### 6.2 Core loop

1. Perform an impressive action → feat fires → ticket(s), tier adjusted by Power Score.
2. Explore → chest → ticket (shared, one-shot, depth-tiered).
3. Optionally spin a curse at the machine → curse occupies a slot plus a ticket per the severity table.
4. Take tickets to the machine → consume → sample a target rating → choose among Advantage results → entry granted, or Residue/Insight.
5. Resolve curses to free slots.

### 6.3 Ticket item

One item type; all parameters in 1.21.1 **data components** (not raw NBT).

| Field | Meaning |
| --- | --- |
| `schema` | version for migration |
| `roll` | `{min, avg, max}` stored as numbers |
| `category` | ability / trait / skill / item / familiar / random / choice |
| `advantage` | 1-6 |
| `filter` | optional `{tags_all, tags_any, source_mod, pool}` |
| `origin` | `{type, id}` for feat / curse / chest / quest / trade |
| `depth` | cosmetic provenance for chest tickets |

- Store numbers at grant time, not a preset name. A ticket is a promise; do not silently rebalance hoarded tickets.
- No `sealed` field. Dropped: machine-only opening already provides the reveal, and hiding parameters makes trade and sorting worse.

### 6.4 The machine

- A block with one ticket input slot; the **only** place a ticket resolves.
- Atomic resolution: consume ticket → roll → present N results if Advantage > 1 → claim. No pending or half-open state.
- Also hosts Recast and module slots.
- No tier gating of machines.
- **Portable opener** (midgame item): opens one ticket. Charge-based, backtank-style: a stored charge pool is consumed per open and refilled from a charging source; no durability loss. No Recast, no modules, no automation. Capacity and recharge rate are tuning values. Settled; see §7 row 24.
- No auto-opener anywhere.

### 6.5 Entries

Kinds: ability, trait, skill, item, familiar, vehicle, location, modifier, system.

State per player per entry: `unowned` → `active` → `lost`. `lost` means previously held and eligible to be rolled again.

General effect hooks: `on_acquire`, `on_loss`, `on_resolve`, plus a small verb vocabulary: `grant_ticket`, `modify_ticket`, `reroll_ticket`, `gamble_tickets`, `attach_modifier`, `refund`, `unlock_machine_action`.

### 6.6 Duplicate policy

| Type | Duplicate behaviour |
| --- | --- |
| Artifact (unique item) | → Residue |
| Consumable / restock / loot-pool item | Stacks — intended |
| Ability / Trait / Skill | → Insight (rank up) or Residue |
| Immortal familiar | → Insight (bond); never leaves active |
| Mortal familiar | Impossible while active; after death → `lost` and re-rollable, no compensation |
| Group familiar | → increases count |
| Ephemeral familiar | → Insight (cooldown) |
| Vehicle / Location | → Residue |

### 6.7 Familiar lifecycle

| Class | Death behaviour | Examples |
| --- | --- | --- |
| Immortal / reforming | Returns; stays active | Kurama, Nrvnqsr (conditional), Ooze Drake, Dragonbone Golem |
| Mortal | Automatically `lost`; immediately re-rollable | War Dog, Grizzly |
| Group | Count decrements; at zero becomes `lost` | Gargoyles, Chicken pair, Nightfury pair, Xenomorph colony |
| Ephemeral | Never persistent; summon and vanish | Pepsi Man |

Lost Pages is a log of previously held, re-rollable entries — not a gate.

### 6.8 Curses

- Flat **3 slots**; resolving frees the slot. No severity weighting.
- Persist through death by default; config toggle to shed.
- Enforcement must be mechanical: attribute modifiers, mob targeting, inventory or blocking restrictions, hunger/sleep, persistent mobs.
- Resolve conditions must be machine-checkable: advancement triggers, stat thresholds, kill/collect/visit predicates.
- Social or psychological curses: rework into mechanical penalties, or route through villager/NPC interaction hooks where a real implementation path exists. If neither, drop or replace.
- Final set (D2, answered 2026-11-03): the triage table is the authored set; mature entries ship behind a default-off config; Infertile and Curse of Gray were reworked non-mature (slow crop growth and a chance to cancel animal breeding; armor-drop without nudity), leaving five gated entries. Evidence: `reports/curse_triage.md`.

### 6.9 Feats and Power Score

- Implementation order: **A** advancement-driven feats now; **B** power-relative tiering as the differentiator; **C** authored feats as a content layer.
- Quest mods are candidate feat sources and design references. Resolved for 1.21.1 NeoForge (2026-10-22): **Odyssey Quests** (`odyssey-quests`, project `lo90fZoB`, MIT) *is* Heracles — its 1.21.1 file is `heracles-neoforge-1.21.1-2.0.3.jar` (version 2.0.3, beta), and it requires Resourceful Lib (`G1hIVOrD`), which resolves `ok`. **JustQuests** (`justquests`, project `dHVehhni`, GPL-3.0-or-later) resolves `ok` at `neoforge-1.21.1-0.4.0` with no required dependencies. **Questify** is not a Modrinth project (404). **FTB Quests** is CurseForge-only and permanently out under the Modrinth-only policy (§7 row 27). Advancement-driven feats remain the baseline (implementation order A); Odyssey is the optional quest layer.
- Each feat has a stable ID and a `granted` set per player. Anti-farm is enforced by authoring feats at the right granularity, not by composing triggers.
- Power Score inputs: gear and attribute totals, owned entries, progression stage. The weights are a **configuration option** with a documented default and a stated range rather than hard-coded constants. The default is the sweep's vector — gear 0.36, entries 0.36, stage 0.28, range ±0.10, weight bounds 0.05–0.80, score clamp 0.0–1.0, reference gear 538.4 / entries 667 (D3 answered 2026-11-03; evidence `reports/power_score_sweep.md`). Practical play drives later tuning.

### 6.10 Residue, Recast, and ticket upgrade

- Duplicates convert to band-specific Residue (a Bronze duplicate gives Bronze Residue).
- **Ticket** rarity upgrade, not entry power: 5 Residue of a band plus one ticket of that band → one ticket of the next band. Shift the roll triple up by 1.0 and clamp at 9.9, preserving spread.
- Recast verbs: reroll category (cheap), +1 Advantage (moderate, cap 6), add or change tag filter (targeted pull), one-band ticket upgrade (expensive, 5:1).
- No pity timer. Residue is the pity system, paying in control rather than free power.
- No node graph. Tree-specific quirks are out of scope; a collection Codex may come later.

### 6.11 Machine modules

- **Gamble** (opt-in): stakes 2/4/6/10/12/16 tickets, d20 table: 20 tier up, 17-19 twin core, 13-16 new ticket kind, 8-12 nothing, 2-7 tier down, 1 destroyed. Modal outcome is bad by design. Rows read from a data table.
- **Downgrade-reroll** (opt-in): after a roll, reroll with rarity one band lower.
- Neither module can be automated.

### 6.12 Loot integration

Three layers, one principle (conservation of loot).

1. **Injection** — custom GLM `gacha:add_ticket`, JSON-driven, per loot table ID.
2. **Themed or mod-loot tickets** — `filter` names item tags; the pool adapter samples an item from the tag and maps it onto 0.1-9.9.
3. **Conversion** — custom GLM `gacha:remove_items` strips configured stacks; those items are registered as Item entries with rarity derived from the table tier.

Depth mapping (table ID → tier):

| Depth | Ticket |
| --- | --- |
| Village, shipwreck, mineshaft, ruined portal | Bronze, occasional Silver |
| Dungeon, outpost, pyramid, modded mid-tier | Silver, occasional Gold |
| Stronghold, mansion, bastion | Gold, occasional Platinum |
| Ancient city, End city, ominous trial chambers | Platinum, rare Diamond |
| Modded endgame | Diamond plus, only source of Wild |

- Chests are shared and one-shot; no Lootr-style per-player loot.
- Unmapped modded tables fall back to table-ID prefix rules; anything still unmapped gets a low-rate Bronze.
- NeoForge GLMs receive the generated item list, so a custom GLM can remove as well as add. `neoforge:add_table` is only a prototype path.
- Removal default (user preference: removal). The two options and their trade-offs:
  - **Injection-only** — add tickets, never strip. Cheapest and safest: no interaction with other mods' loot tables, no accidental item loss, works in any pack. Cost: conservation of loot becomes one-directional and chests keep their original rewards, so tickets are a bonus layer rather than a replacement.
  - **Removal (selected)** — strip configured stacks via `gacha:remove_items` and register those items as Item entries with rarity derived from the table tier. Makes conservation real and turns chests into a gacha source rather than an addition. Cost: a wrong table ID silently deletes loot, so it needs a conservative starter list, an explicit per-table allowlist, and a dry-run audit mode.
  - Decision: removal is the default, gated behind an explicit per-table allowlist with a conservative starter list; injection-only remains a config switch for packs that do not want it.
- D1 answered 2026-11-03: all 305 chest tables in the 15 cached structure jars are accepted at their proposed bands (Bronze 61, Silver 156, Gold 60, Platinum 28; Diamond empty), shipped as four per-band `gacha:add_ticket` loot modifiers in `mod/datapack/data/gacha/loot_modifiers/`. The first playtest extended the allowlists to 536 tables by adding the vanilla chest tables and the shipped pack's structure chests (Aether, Apotheosis, Irons Spellbooks, Familiars, Artifacts, Supplementaries, Terralith, Mowzie's Mobs); each table sits in exactly one band. NeoForge only applies modifiers named in `data/neoforge/loot_modifiers/global_loot_modifiers.json`, so that manifest ships with the four files. The removal strip list stays open in §11.

### 6.13 Persistence

Per-player attachment: curse list and slots, owned entries with state, granted feat IDs, Residue balances, unlocked modules, RNG seed. Tickets are items. Death does not wipe curses by default; mortal familiars become `lost`.

### 6.14 Power ceiling

None. Game-breaking modded content is allowed; the source is game-breaking by design.

## 7. Decision register

| # | Decision | Status |
| --- | --- | --- |
| 1 | NeoForge 1.21.1, Java Edition | Settled |
| 2 | Experience-first, not a 1:1 port | Settled |
| 3 | Mechanics spec before mod survey | Settled |
| 4 | Feats are the primary economy; curses are a loan | Settled |
| 5 | Power-relative tiering, built A then B then C | Settled |
| 6 | Flat 3 curse slots, freed on resolve | Settled |
| 7 | Curses persist through death by default, config toggle | Settled |
| 8 | No power ceiling | Settled |
| 9 | Social curses reworked or replaced where unimplementable | Settled |
| 10 | Chest tickets shared, one-shot | Settled |
| 11 | Tickets are items with parameters in data components | Settled |
| 12 | Machine-only opening; midgame portable opener; no automation | Settled |
| 13 | No sealed tickets | Settled |
| 14 | No node/tree quirks | Settled |
| 15 | 5:1 duplicate Residue upgrades a ticket one band | Settled |
| 16 | Gamble module in | Settled |
| 17 | Familiar lifecycle classes and unowned/active/lost states | Settled |
| 18 | on_acquire / on_loss / on_resolve as general effects | Settled |
| 19 | Duplicate policy by entry type | Settled |
| 20 | No pity timer; Residue is the control-based sink | Design |
| 21 | NeoForge GLMs for ticket injection and item removal | Design |
| 22 | Rarity stored continuously; bands display-only | Design |
| 23 | Removal default: strip configured loot via explicit per-table allowlist and a conservative starter list; injection-only stays a config switch | Settled |
| 24 | Portable opener: charge pool consumed per open (backtank-style), no durability, no Recast/modules/automation | Settled |
| 25 | Quest mod: Odyssey Quests (= Heracles) optional layer; JustQuests also available; FTB Quests out (CurseForge-only); Questify does not exist on Modrinth | Settled |
| 26 | Power Score weights exposed as config with a documented default and range; default 0.36/0.36/0.28, ±0.10, bounds 0.05–0.80, score clamp 0.0–1.0, reference gear 538.4 / entries 667 (D3, 2026-11-03) | Settled |
| 27 | Modrinth-only sourcing; CurseForge-only projects are permanently out of scope | Settled |
| 28 | Tickets tradeable between players by default | Settled |
| 29 | Milestone A pack shape: option B — core + seed + support + add-on; adoption and library arrive transitively; trial and defer wait for milestone B | Settled |
| 30 | No-build replacements ratified as recorded; `asterism-arcanum` (dependency) and `lootr` (design) stay excluded | Settled |
| 31 | Delivery: `.mrpack` with Modrinth CDN URLs, jars not bundled | Settled |
| 32 | Fit scope: add 2–4 item-tag rules, declare the trait and ability remainder explicitly out of scope | Settled |
| 33 | Launcher and instrumentation: Prism for client verification, direct JVM for server smoke tests, the runtime harness reads log files and never invokes a launcher | Settled |
| 34 | Curse triage accepted as the implementation set (D2, 2026-11-03): mature entries gated; Infertile and Curse of Gray reworked non-mature, five gated entries remain | Settled |
| 35 | Structure loot bands accepted wholesale (D1, 2026-11-03): all 305 chest tables in the 15 cached structure jars at their proposed bands, encoded as per-band `gacha:add_ticket` modifiers | Settled |
| 36 | Race changes: Neo Origins (NeoForge Origins port) ships at milestone A; gacha race traits set an origin on `neoorigins:origin` through a `gacha:origin` adapter | Settled |

## 8. Custom mod scope

Irreducible scope:

- Ticket item and its data components.
- Machine block, portable opener, module slots.
- Curse engine: application, slots, persistence, Resolve tracking.
- Feat engine and Power Score.
- Entry adapter and registry, including effect hooks and states.
- Optional origin adapter: race traits set a Neo Origins origin on its origin layer (reflective, so the mod loads without it).
- Recast and Residue.
- Two loot GLMs.

Everything else — items, structures, mounts, magic, bosses, NPCs — comes from the pack.

## 9. Mod survey

Status: fourth pass complete (2026-10-22). `candidates.txt` now holds 162 slugs in 19 sections: the original seed list, replacements for the seven slugs with no 1.21.1 NeoForge build, per-candidate add-ons, cross-mod compatibility layers, a quest-systems section, a first pack-harvest batch, and a second batch of content, worldgen and progression mods surfaced by the expanded modpack survey. Reports: `reports/mods_survey.md` (grouped, required dependencies resolved to project slugs) and `reports/mods_matrix.md` (same set, flat).

Result: 154 `ok`, 8 `no_build`, 0 `error` (162 candidates; `chaoslab survey` and `mods matrix --offline` agree). The dependency audit is transitive: 76 candidates have every required dependency inside the pool and buildable, 77 declare none, 9 are unusable because a dependency has no build, 0 are undecidable, and none need content outside the pool after `kotlin-for-forge` was added as a library. The stale `cC0JkO8i` link that `ars-creo` 5.4.0 declares alongside `create` is reported on its audit row as an unresolved dependency ID instead of deciding the verdict: an ID that resolves to nothing cannot be installed or inspected, so it is incomplete metadata rather than proof the candidate is unusable. The second harvest added the YUNG's structure set, Structory Towers, Farmer's Delight, Supplementaries, Sophisticated Backpacks, Serene Seasons, advancement/quest helpers (Cerulean Advancements, Better Advancements, What Are They Up To, Villager Names), Create add-ons (Dragons Plus, Enchantment Industry, Aeroworks, Big Cannons, Steam 'n' Rails) and Polymorph; every one resolves `ok`. Late additions: `tempad` (1.21.1-3.0.4 beta of 2026-05-11, five matching versions) and one of its three required libraries, `resourceful-config`; both resolve `ok`. The seven unavailable content slugs are kept in a "Checked: no 1.21.1 NeoForge build" section so the negative evidence is not lost; the eighth `no_build` is `expandability`, recorded in the library section as negative evidence because `asterism-arcanum`'s 1.21.1 build links the creative-only version and the complete version is CurseForge-only. Replacements:

- botania → primal-magick, golem-magicka
- thermal-expansion → oritech, electrodynamics, energized-power
- alexs-mobs → mowzies-mobs, mobs-of-mythology, alexs-mobs-continued
- alexs-caves → no direct replacement; worldgen covers terrain
- ice-and-fire-dragons → cataclysm-spellbooks, mowzies-mobs
- blue-skies → aether, terralith, biomes-o-plenty
- relics → artifacts, curios

Add-ons and compatibility are surveyed alongside content: Ars Nouveau (ars-additions, ars-creo, ars-controle, reliquified-ars-nouveau), Iron's Spells (winds-spellbooks, paladin-spells, fundamental-principles, asterism-arcanum, cataclysm-spellbooks), Create/Aeronautics (create-aeronautics, create-aeronautics-compatability, offroad-stickywheels, lift-n-load, magneutica, steel-addon, waystones-sable, create-wizardry, createaddoncompatibility), Apotheosis (apotheosis-addon-compat, apothic-flux), compatibility glue (better-compatibility-checker, accessories-compat-layer, mekanism-tfmg-compat). Skill-tree content remains the thinnest area: justleveling-fork is the only resolvable leveling mod found here and Puffish Skills is CurseForge-only.

### 9.1 Modpack harvest

Popular packs are a second, independent source of candidates. A `.mrpack` index lists every bundled jar with a Modrinth CDN URL that embeds the project ID, so pack membership is exact rather than name-matched. `chaoslab modpacks` reads that index, resolves IDs to slugs, ranks them by how many packs ship them, and extracts quest chapters from the overrides.

Canonical run: 17 packs (the six originals plus Irons Magic, Industrial Odyssey, Arcadia, Mythcraft, Medieval Magic Tech, RPG Create Plus, Antique Runes, Travelers Reborn, Crafted Knowledge 3, Lyrran's Magicraft and Create Ultimate Selection 2) → 3,215 Modrinth-hosted files, 1,490 distinct projects, all 1,490 resolved to names with `--max-lookups 2000`; none fell outside the lookup budget. Report: `reports/modpacks_survey.md`; smoke runs are in `reports/modpacks_smoke.md`, `reports/modpacks_quests.md` and `reports/modpacks_travelers.md`.

Added to `candidates.txt` after resolving each against 1.21.1/neoforge: `waystones`, `structory`, `toms-storage`, `trading-post`, `functional-storage`, and `odyssey-quests`. Every one resolves `ok`.

Game-breaking content: **Re:Avaritia** (`re-avaritia`, project `QeB3NRC5`) resolves `ok` for 1.21.1 NeoForge — MIT, client and server required, no required dependencies, newest matching build `1.21.1-1.4.2-release` (4 versions checked, 4 matching). It sits in the "Endgame / gamebreaking" section; §6.14 permits it by design.

Quest examples: two packs ship quest data. Better MC BMC5 — 17 FTB Quests files, including `chapters/7dragons.snbt` (13 quests) and `chapters/decoration.snbt` (14 quests). Rubius Cobblemon — 44 FTB Quests files plus 43 files under `config/quests/chapters`, including `ae2_main.snbt` (27 quests), `cobblemon_main.snbt` (32–33 quests) and `create_01_core.snbt` (41–42 quests). These are worked examples of chapter structure, gating and reward shape. FTB Quests itself is CurseForge-only and out of scope under the Modrinth-only policy; the resolvable quest layer is Odyssey Quests (which ships the `heracles-neoforge` jar) with JustQuests as a lightweight alternative.

### 9.2 Pack assessment (N4)

`chaoslab pack` scores every candidate for pack necessity and suitability from cached data only: the survey's transitive dependency audit (does another candidate require it?), `fit_rules.json` (does a fit rule name it?), the 17 canonical pack indexes under `data/modpacks/` (do popular packs ship it?), and Modrinth metadata (build, release type, update recency, licence, side). Report: `reports/pack_assessment.md`.

Result (offline, 2026-10-28): 162 candidates assessed, 154 buildable, 8 `no_build`, 0 errors. Verdicts — 16 `include (core)`, 6 `include (seed)`, 17 `include (adoption)`, 54 `include (library)`, 4 `include (support)`, 1 `include (add-on)`, 28 `trial`, 22 `defer`, 2 `optional (client-only)`, 2 `review (unused library)`, 1 `exclude (dependency)`, 1 `exclude (design)`, 8 `excluded (no build)`.

Two exclusions are policy, not build failures:

- `asterism-arcanum-addon-for-irons-spells-and-spellbooks` → `exclude (dependency)`. Its 1.21.1 build requires `expandability`, which has no 1.21.1 NeoForge build; the complete version is CurseForge-only, so the Modrinth-only policy (§7 row 27) rules the add-on out.
- `lootr` → `exclude (design)`. §6.12 settles chests as shared and one-shot; Lootr makes them per-player instanced.

`trial` and `defer` are decision support, not verdicts: each row carries its raw signals (packs, dependents, fit host, licence, side, necessity, suitability) so a reader can override the score without losing the evidence. `citadel` reads `review (unused library)` because its only surveyed consumer, `alexs-mobs`, has no 1.21.1 NeoForge build.

### 9.3 Pack declaration (Phase 2)

`chaoslab lint` turns the assessment into a declared pack. `pack_manifest.json` is the hand-maintained policy: which verdict classes ship in milestone A, which sections are promoted, which candidates are excluded or deferred by name, the required sections and the milestone-A budget. The command expands that policy over the same scored rows, walks the required-dependency closure from milestone A to a fixpoint, and renders two derived artifacts: `PACK.md` (the declared pack) and `reports/pack_report.md` (the machine-checked audit). Editing either derived file is a mistake; the manifest is the source.

Recorded policy (D4–D6): milestone A is core + seed + support + add-on, with Tech, Dimensions/worldgen and Quest systems promoted so full tech breadth, untrimmed worldgen and the Odyssey quest layer ship together; magic is limited to Ars Nouveau and Iron's Spells (Primal Magick and Golem Magicka are milestone B overrides); outside those promoted sections, adoption, trial and defer wait for milestone B, while a promoted section ships whole; libraries arrive transitively. `lootr` (design conflict, §6.12) and `asterism-arcanum` (needs `expandability`, CurseForge-only) are excluded. `curios` is explicitly included because a fit rule names it and nothing else pulls it in.

Result (offline, 2026-10-28): 162 candidates expanded → 33 in milestone A, 51 at milestone T (declared transitive, of which 26 are carried into milestone A), 65 at milestone B, 3 optional, 10 excluded, 0 unclassified. Every dependency reachable from milestone A is a candidate and resolves `ok`; the closure contains no excluded candidate; every resolvable fit host ships either explicitly or transitively; all required sections are populated; no milestone-A candidate is client-only. `python3 -m chaoslab lint` exits non-zero on any failed invariant.

Filter list for candidates:

- Create Aeronautics build availability on 1.21.1 NeoForge — done, see §3.
- GLM compatibility, data components, item tags, loot table IDs.
- Advancement and quest reward hooks.
- Attribute, energy and slot systems.
- Villager/NPC interaction hooks.
- Content breadth for the gacha pool.

## 10. Tooling

`chaoslab` is a Python CLI: `fetch`, `parse`, `curses`, `mods`, `survey`, `modpacks`, `pack`, `lint`, `build`, `runtime`, `structures`, `datapack`, `fit`, `simulate`, `report`, `verify`.

- `chaoslab/mods.py` implements Modrinth v2 JSON access: `search`, `resolve`, `matrix`. No HTML scraping.
- `chaoslab/survey.py` groups candidates by the `# == Section` headings in the candidate file, resolves each selected version's required-dependency project IDs to readable slugs, and writes `reports/mods_survey.md`.
- `chaoslab/modpacks.py` searches Modrinth for modpacks under the target filter, caches each `.mrpack` under `data/modpacks/`, reads `modrinth.index.json` for project IDs, extracts quest chapter files from the overrides, and writes `reports/modpacks_survey.md`. `--packs` targets named packs, `--query` narrows the download ranking, and `--max-lookups` bounds name resolution. Re-runs honour `--offline` and `--refresh` through the same cache helpers as `mods.py`.
- `chaoslab/pack.py` scores candidates for pack necessity and suitability and writes `reports/pack_assessment.md`. Roles come from section, Modrinth categories and side metadata; necessity from candidate dependents plus fit-rule hosts; suitability from build, release type, recency, licence, side and canonical pack adoption. Two verdicts are policy exclusions (the `expandability` chain and `lootr`), recorded with their reason.
- `chaoslab/packlint.py` expands the declared policy in `pack_manifest.json` over the scored candidates, walks the required-dependency closure from milestone A, audits the declaration's invariants and renders `PACK.md` plus `reports/pack_report.md`. The manifest is the only hand-maintained pack declaration; the document and the report are derived from it.
- `chaoslab/packbuild.py` pins each declared project to one build from the cached version responses, writes `pack_lock.json` (version id, filename, sha1/sha512, size and per-side env) and renders the byte-stable archive into `dist/` with fixed zip metadata, so the output is a pure function of the manifest plus the cache; `reports/pack_build.md` records the archive and index digests. Local content that is not on Modrinth (the custom mod jar, its default config and the quest files) is assembled under `overrides/` from `pack/` and `mod/config/`; `make mod-jar` refreshes the tracked release jar and `make pack` rebuilds the archive.
- `chaoslab/report.py` regenerates the corpus tables, fit and curse summaries, the power-score sweep, the pack coverage measurement and the datapack validation report. `reports/pack_measurements.md` computes preset/category coverage from the shipped entry registry, ticket income from the shipped GLM chances, and the remaining curse coverage; it is a content measurement, not a playtest.
- `chaoslab/runtime.py` audits the pinned lock for dedicated-server and client hazards, emits the probe sequence and triages captured logs into a fixed conflict taxonomy, including the build-identity check that compares the jars NeoForge reports discovering against the lock's filename values (`match` / `drift` / `unverified`); it writes `reports/runtime_compat.md`.
- `chaoslab/datapack.py` validates the custom mod's configuration contract offline: the JSON Schemas in `mod/schema/`, the shipped datapack in `mod/datapack/`, the default config in `mod/config/` and the fixtures in `mod/examples/`. It implements a strict JSON Schema subset plus the semantic rules the schemas cannot express, writes `reports/datapack_report.md` and proves its own strictness with `chaoslab datapack --selftest`.
- `mod/` is the custom mod's Gradle workspace (NeoForge 21.1.247, ModDevGradle 2.0.91, Java 21): the ticket item, machine block, roll engine, entry registry, item/attribute/effect/origin adapters, per-player persistence, Power Score, the feats and curse engines, the two loot GLMs (registered through `data/neoforge/loot_modifiers/global_loot_modifiers.json`), code-granted advancements, debug command and 66 entries (8 starter + 50 coverage + 8 race). `./gradlew build test` and `./gradlew runGameTestServer` are green (five tests); the dedicated-server boot is verified. The GameTest end-to-end pass (ticket → roll → reward → Power Score → advancement, the machine right-click path, and chest injection) runs against a mock server player and lives in `mod/src/main/java/dev/eternaldensity/gacha/test/GachaGameTest.java`. The datapack tree is included as a resources source set, so `mod/datapack/` stays the single content source; datapack registries follow NeoForge's prefixed layout (`mod/datapack/data/gacha/gacha/<registry>/`). The quest skeleton is pack content in `pack/quests/` and installs to `config/heracles/quests/`; Heracles stays off the GameTest classpath because its quest-sync payload cannot reach a mock player.
- `fit_rules.json` v3 cites only mods that resolve `ok` for 1.21.1/neoforge; `chaoslab fit` regenerates `reports/fit.csv` and `reports/fit_summary.md` (4233 rows, 3332 mapped, 901 unmapped).
- Defaults are `1.21.1` and `neoforge` (`chaoslab/cli.py`).
- Raw responses are cached under `data/mods/` (`project/`, `versions/`, `search/`, plus `index.json`); offline and refresh are supported.
- Matrix columns: build, required dependencies, maintenance, side, license, status (`ok`, `no_build`, `error`).
- Report written to `reports/mods_matrix.md`.
- `chaoslab/verify.py` regenerates every manifest-pinned derived report inside a scratch root from cached responses and tracked inputs, then compares the bytes with the committed reports and `reports/MANIFEST.sha256`; that manifest, not the whole `reports/` directory, defines the gate's scope, and the Makefile lists the deliberately ungated reports. `chaoslab verify --update` rewrites the manifest only after a byte-identical run.

**Verified** (offline, against cached responses):

- `mods resolve --project create-aeronautics --offline` → `status: ok`, version `1.3.2+mc1.21.1`, 8 versions checked and 8 matching the 1.21.1/neoforge filter.
- `mods matrix --candidates data/smoke_candidates.txt --offline` → 5 candidates, statuses `ok=4`, `no_build=0`, `error=1`. The single error is the deliberately invalid slug `definitely-not-a-real-mod-xyz`, which confirms a not-found project is reported as `error` and never as `no_build`.
- `survey` over the full `candidates.txt`, then `mods matrix --offline` over the same list → 162 candidates in 19 sections, `ok=154`, `no_build=8`, `error=0`; the matrix agrees. The transitive audit reports 76 fully inside, 77 with no dependencies and 9 unusable.
- `survey --candidates data/smoke_candidates.txt --offline` → 5 candidates in 1 section, `ok=4`, `error=1`; the invalid slug is reported, not silently dropped.
- `modpacks --packs create_plus,lucky-block-challenge --offline` → 2 packs, 183 distinct projects, 97 named, 0 quest systems. The negative quest result is real: neither pack ships quest configs.
- `modpacks --packs better-mc-neoforge-bmc5 --offline` → 1 pack, 261 distinct projects, 73 named, 1 quest system (FTB Quests, 17 files) with per-chapter quest counts.
- `modpacks --offline` over the canonical 17-pack set → 17 packs, `ok=17`, 3,215 Modrinth-hosted files, 1,490 distinct projects, all 1,490 named, 3 quest systems. The gated artifact is `reports/modpacks_survey.md`, regenerated byte-for-byte by `chaoslab verify`; the hand-run duplicate that used to sit at reports/modpacks_offline_check.md has been deleted rather than left to drift, and the earlier six-pack `--max-lookups 300` run is superseded.
- `pack --offline` → 162 candidates scored into `reports/pack_assessment.md`: roles 16 core, 41 content, 19 add-on, 56 library, 15 support, 3 compatibility, 2 client-only, 1 design-conflict, 1 unusable, 8 excluded; verdicts 16 core, 6 seed, 17 adoption, 54 library, 4 support, 1 add-on, 28 trial, 22 defer, 2 client-only, 2 unused library, 1 dependency exclusion, 1 design exclusion, 8 no-build.
- `lint --offline` → PASS: 162 candidates expanded from `pack_manifest.json` into 33 milestone A, 51 at milestone T (declared transitive, of which 26 are carried into milestone A), 65 at milestone B, 3 optional, 10 excluded, 0 unclassified; every lint invariant passes (12/12). `verify --update` afterwards → PASS, 19/19 artifacts match, 24/24 inputs valid.

Both reports are current for the 162-slug `candidates.txt`. One required-dependency project ID (`cC0JkO8i`, declared by `ars-creo` 5.4.0 alongside `create`) does not resolve — Modrinth returns 404. The audit keeps the ID on the row as unresolved metadata rather than omitting it, and that metadata defect does not flip a buildable candidate to undecidable.

- Superseded earlier `verify --update` run (it reported `PASS; 11/11 artifacts match` against the then-smaller generator set; the current result and scope are the 19/19, 24/24 figures above). The gate regenerates every manifest-pinned report inside a scratch root with no network access, then compares bytes. That run caught one real defect: the cross-pack frequency table ordered ties by set iteration, so `reports/modpacks_survey.md` depended on Python's hash seed; the ordering is now explicit and sorted.

## 11. Open items

Resolved:

- The Create Aeronautics 1.21.1 NeoForge build is confirmed and recorded in §3.
- The literal ticket preset triples are extracted and recorded in §4.2. Source: `tools/export_web_data.py` in the vendored `ChaosGacha` snapshot at commit `af084bf` (sha256 `a069238d370dbc12bfeb182b02342ba3dca125319dd4261016134aaf81f79e4b`); GitHub reports that repository as `fork: true` with parent `Bronzdeck/ChaosGacha`. That sha256 is provenance for the snapshot, not for current `master`: a fetch on 2026-10-29 advanced `origin/master` `af084bf..00739d6` (six commits), touching `tools/export_web_data.py`, `web/js/gacha.js`, `gachafiles/item.txt`, `gachafiles/ability.txt` and `gachafiles/skill.txt`. `Gacha.py` is untouched, so the twelve preset windows in §4.2 are unaffected. The delta is additive — `railway` tags on ability, item and skill entries, plus an advantage-wheel duplicate-prize rule — so the committed corpus and fit reports stay valid, but re-snapshot the vendored copy before the next corpus/fit regeneration so the fit mapping sees the new tags.

Closed 2026-10-22:

- Removal default (§6.12, row 23): removal selected; both options' trade-offs recorded; per-table allowlist with a conservative starter list; injection-only keeps a config switch.
- Portable opener (§6.4, row 24): charge pool consumed per open, backtank-style; no durability; no Recast/modules/automation.
- Quest integration (row 25): Odyssey Quests is Heracles and resolves for 1.21.1 NeoForge; JustQuests also resolves; Questify is not on Modrinth; FTB Quests excluded by the Modrinth-only policy.
- Power Score (row 26): weights become a config value with a documented default and range, tuned from corpus data; the numeric default was answered 2026-11-03 (D3).
- CurseForge policy (row 27): Modrinth only; CurseForge-only projects stay out permanently.
- Ticket trading (row 28): tradeable between players by default. A Trait exists that grants tradeability, but making trading default is less work than enforcing non-trading.

Answered 2026-11-03:

- D1 (structure loot bands): all 305 chest tables accepted at their proposed bands, reject none; encoded as four per-band `gacha:add_ticket` modifiers in `mod/datapack/data/gacha/loot_modifiers/`. Mirror: §6.12 and §7 row 35. Evidence: `reports/structure_tables.md`.
- D2 (curse triage): the triage table is the implementation set; mature entries stay behind a default-off config; Infertile and Curse of Gray were reworked non-mature (slow crop growth and breeding failure; armor-drop without nudity), leaving five gated entries. Mirror: §6.8 and §7 row 34. Evidence: `reports/curse_triage.md`.
- D3 (Power Score): weights 0.36/0.36/0.28, range ±0.10, weight bounds 0.05–0.80, score clamp 0.0–1.0, reference gear 538.4 / entries 667; practical play tunes them. Mirror: §6.9 and §7 row 26. Evidence: `reports/power_score_sweep.md`; the values already ship in `mod/config/power_score.json`.

Resolved 2026-11-03 by the first playtest:

- The four `gacha:add_ticket` files were inert: NeoForge only applies modifiers named in `data/neoforge/loot_modifiers/global_loot_modifiers.json`, and no manifest shipped. Added the manifest, plus a validator that rejects an unlisted modifier file or a listed id with no file. A GameTest now generates a village chest through the modifier.
- The D1 allowlist covered the 15 cached structure jars, not the shipped pack. Extended the four bands to 536 tables: all vanilla chest tables plus the shipped pack's structure chests (Aether, Apotheosis, Irons Spellbooks, Familiars, Artifacts, Supplementaries, Terralith, Mowzie's Mobs). The validator now rejects a table repeated across bands.
- The Heracles quest files used the wrong field names (`advancement`, `xp_type`, snake_case settings) and an empty group, so they parsed into defaults or vanished. They now use `advancements`, `xptype`, the camelCase settings, `"hidden": "IN_PROGRESS"` and `"Main"` group positions. A server boot with a deliberately invalid quest confirms the loader logs only that file.
- Quest titles rendered as "New Quest": Heracles uses `ComponentSerialization.FLAT_CODEC` for `display.title`/`subtitle`, which expects a string containing JSON, not a plain string. The titles are now `"{\"text\":\"First Roll\"}"`-style strings; `chaoslab verify` validates the pack quests as an input (FLAT_CODEC form, non-empty groups, `advancements`, `xptype`).
- The three code-granted advancements rendered as separate tabs with missing backgrounds. `first_roll` is now the root with the vanilla stone background, `first_duplicate` parents to it, and `power_ten` parents to the duplicate. The datapack validator rejects a root display without a background or a parent that names no advancement.
- The tab was named "First Roll" because that was the root. A `gacha:root` advancement titled "Chaos Gacha" (auto-completed by `minecraft:tick`, no toast) is now the tab root, and `first_roll` parents to it; the tab reads Chaos Gacha.
- Attribute traits and Glass Bones used 1.21.2-style ids (`minecraft:max_health`), which do not exist in 1.21.1 (`minecraft:generic.max_health`), so they silently did nothing. All shipped entries, the curse and the fixtures now use the `minecraft:generic.*` ids; the validator rejects an unknown `minecraft:` attribute, and owned traits reapply on login and respawn.

Still open:

1. Removal strip list (§6.12 layer 3): which item stacks `gacha:remove_items` converts
   per band. The per-table allowlist is answered; the conversion list is not, so the
   removal path stays inert until it exists.
2. Injection's occasional upgrades (§6.12): the depth mapping's "occasional
   Silver/Gold/Platinum/Diamond" step is not yet expressed in the loot-modifier schema;
   the shipped per-band files carry the base band only. Settle with the engine phase.
3. Entry corpus scale-out (Phase 5): a 50-entry coverage set now fills every category
   (ability, trait, skill, item, familiar) and every rarity step from 0.5 to 9.3, so no
   preset or category is dead; the registry ships 66 entries including 8 race traits.
   The coverage rewards are generic, not the authored corpus; the 4,328-row corpus still
   needs a concrete adapter mapping. The race traits map onto Neo Origins' built-in
   origins; the rest of the 98 `race-change` entries need a mapping policy.
4. Curse corpus scale-out (Phase 5): one curse ships (`Glass Bones`, attribute hook).
   The D2 implementation set and the non-attribute hooks remain to be imported and
   implemented; `reports/pack_measurements.md` tracks the shipped count.
5. Ticket injection rate (Phase 5): all four `gacha:add_ticket` modifiers use chance 1.0,
   so every listed chest yields a ticket. At 10–30 chests/hour that is 240–720
   tickets/day, versus the D3 sweep's 4–30/day. Pick a chance against a measured
   chest-opening rate before tuning tiers.

Playtest round 2026-11-03: the assembled archive was imported into Prism and played. Commands, ticket opening, village/ruined-portal/Apotheosis chest injection, the First Roll and Deja Vu quests, and the advancement tab (background and shared chain) all worked. The tested build predates the `gacha:root` tab-name change; that is display-only. Recorded in `reports/runtime_compat.md`.

All seven questions — D1–D3 above and four pack-level ones raised during the survey — are
written up as sheets in `DECISIONS.md` (D1–D8), each with its evidence pointers, options
and a default.

Answered 2026-10-26: D4 (pack shape, option B), D5 (replacements ratified), D6 (CDN
`.mrpack`), D7 (fit scope option A). They are mirrored into §7 rows 29–32. Answered
2026-11-03: D1, D2 and D3, above; the D1 hint extension raised band coverage of the 305
chest tables from 117 to 305 and the accepted block is now the shipped allowlist.

## 12. Forward roadmap (Phase 2–5)

Recorded 2026-10-26 so the next run inherits the sequence instead of re-deriving it from chat. Phase 2 is complete (§9.3). Phase 3 is answered: D1 accepted wholesale, D2 and D3 recorded (all 2026-11-03); the chest-integration follow-ups are in §11. Phase 4 is complete: the configuration contract, the Java MVP (including feats, curses and the two loot GLMs), the starter quest skeleton and the player-in-the-loop end-to-end pass all landed 2026-11-03. Phase 5 has started: the archive now bundles the custom mod and its data, and a dedicated-server smoke test passes; the content scale-out and live balance measurements remain.

### Phase 2 — Declare the pack (complete)

Deliverables: `pack_manifest.json` (the declaration), `PACK.md` (rendered from it), `reports/pack_report.md` (the machine-checked audit) and the lint subcommand that produces both. Acceptance: every lint invariant passes, the gate is green with the three new artefacts pinned, and §9–§10 carry the refreshed figures.

### Phase 3 — Generate the three missing decision artefacts

These run once the pack shape is fixed, because the pack determines which structures and gear sources actually matter. Each produces one report plus one closed-form answer sheet in `DECISIONS.md`.

- **D1 — structure table to ticket band (answered 2026-11-03).** A subcommand of `chaoslab` reads the worldgen and structure jars, enumerates every chest loot table by namespace and path, and writes `reports/structure_tables.md`: table id, mod, jar path, inferred depth, proposed band, confidence, plus a paste-ready accept block. The answer was accepted wholesale — Bronze 61, Silver 156, Gold 60, Platinum 28; Diamond empty — and encoded as four per-band `gacha:add_ticket` loot modifiers. Hint extension 2026-11-03: every one of the 305 chest tables carries a proposed band, up from 117. Open follow-ups: the removal strip list and the vanilla/milestone-A enumeration (§11).
- **D2 — curse triage (answered 2026-11-03).** No new downloads. `reports/curse_triage.md` renders all 115 records from `data/curses.jsonl` with severity, tier, proposed hook class (stat modifier, event trigger, inventory restriction, mob/NPC behaviour, social/UI, rework, drop) and feasibility, plus an explicit ship-or-cut column for the mature entries. Result: the triage table is the implementation set; Infertile and Curse of Gray were reworked (rows marked `decided`), leaving 60 mechanical, 53 rework, 2 drop and 5 mature entries gated.
- **D3 — power-score sweep (answered 2026-11-03).** `chaoslab simulate` drives three ticket-income arcs (casual, regular, grinder) and reports P10/P50/P90 for gear and attribute totals, owned entries and progression stage. `reports/power_score_sweep.md` publishes the seeded 28-day sweep; its proposal — gear 0.36 / entries 0.36 / stage 0.28, range ±0.10, weights clamp 0.05–0.80 and score clamp 0.0–1.0, per §6.9 and §7 row 26 — is the shipped default. Adjustments wait for practical play. This unblocks milestone B, not the pack.

### Phase 4 — Vertical slice

- **Configuration and datapack (delivered 2026-11-03).** The mod's data contract is fixed before any code: `mod/schema` (six JSON Schemas), `mod/datapack` (the two machine modules), `mod/config/power_score.json` (the answered D3 default) and `mod/examples` (22 fixtures exercising every schema branch). `chaoslab datapack` validates all of it, `reports/datapack_report.md` is pinned in the gate, and `chaoslab datapack --selftest` proves the validator rejects malformed input. Java is written against this contract next; a schema change and its fixtures move together.
- **Java MVP (delivered 2026-11-03, extended).** The Gradle workspace (NeoForge 21.1.247, ModDevGradle 2.0.91, Java 21) lives in `mod/` and builds offline against the local toolchain. Delivered: the ticket item with data components, the Gacha Machine block, the roll/rarity engine ported from `chaoslab/simulate.py` and unit-tested, the entry datapack registry and adapters for items, attributes and effects, eight starter entries, and a `/gacha` debug command; per-player persistence (owned/lost entries, granted feats, Residue, modules, curses, RNG seed, Power Score); the config-driven Power Score; machine integration (ownership, duplicate policy, score recompute); the **feats engine** (advancement-driven triggers, granted set, diminishing lines, ticket rewards); the **curse engine** (three flat slots, attribute/effect hooks, advancement resolves); and the **two loot GLMs** (`gacha:add_ticket` injection and `gacha:remove_items` conversion). Power Score tuning, non-advancement feat triggers, non-advancement curse resolves and the remaining curse hooks are declared but not implemented. `./gradlew build test` passes (6 tests) and the dedicated-server boot is verified (`Done` in 4.6s with Heracles loaded, no registry or datapack errors).
- **Quest skeleton (delivered 2026-11-03).** Odyssey Quests is the settled layer (§7 row 25). A starter chapter chain lives in `pack/quests/`: `first_roll` → `first_duplicate` → `power_ten`, driven by code-granted advancements (`gacha:first_roll`, `gacha:first_duplicate`, `gacha:power_ten`). The plan's five to seven chapters (tier gates, curse management, dimension/boss milestones, endgame) remain to be authored in the Heracles in-game editor; the shipped chain is the skeleton and format reference.
- **One end-to-end path (proved 2026-11-03):** ticket → roll → reward → power score → quest advancement, exercised headlessly with NeoForge GameTests (`./gradlew runGameTestServer`) against a mock server player. `GachaGameTest` proves three paths: a narrow ticket resolves through `MachineService`, consumes the ticket, grants the item, records ownership and a positive Power Score, and awards `gacha:first_roll`; the same roll driven by right-clicking a placed machine block; and an insight duplicate policy converting a repeat trait to Bronze Residue while awarding `gacha:first_duplicate`. The Heracles quest files consume exactly those advancements. Two bugs were caught and fixed by the pass: NeoForge's prefixed datapack path (`data/<pack_ns>/gacha/<registry>/`) and the GameTest structure id (`gacha:gachagametest.empty` in a single file, not a directory). The dedicated-server boot also remains verified.

### Phase 5 — Assemble and prove

Build the `.mrpack` under delivery option A (§7 row 31), run a server smoke test, then measure: tickets per hour, tier distribution, the power-score curve over a play arc, and whether any curse or structure band produces a dead end. Balance from those measurements rather than from opinion.

- **Archive assembly (delivered 2026-11-03).** Upstream mods remain Modrinth CDN `files[]` entries; the unpublished custom mod and its data ship as overrides: `overrides/mods/gacha-0.1.0.jar` from `pack/mod/`, `overrides/config/gacha/power_score.json` from `mod/config/`, and `overrides/config/heracles/quests/*.json` from `pack/quests/`. `make mod-jar` refreshes the tracked release jar and `make pack` rebuilds the archive; `chaoslab verify` still reproduces the archive byte-for-byte from the committed jar and cached Modrinth metadata (22/22 artifacts, 28/28 inputs).
- **Dedicated-server smoke test (passed 2026-11-03).** A fresh NeoForge 21.1.247 server with the 58 server-side CDN jars plus `gacha-0.1.0.jar` reached `Done (11.041s cold, 4.596s warm)` with no fatal or load-blocking errors; Heracles found and loaded the three quest files, and Neo Origins loaded 77 origins across 2 layers with 928 powers. The two server-unsupported jars (`athena-ctm`, `simply-tooltips`) were withheld per the lock's side audit, and `chaoslab runtime --log ... --side server` reports `MATCH` against the 58 locked jars plus the bundled local jar. The triage keeps two expected client-class transformer probes (`ItemRenderer`, `AbstractClientPlayer`) as high-severity advisory findings; neither aborts the boot. Recorded in `reports/runtime_compat.md`; the captured log is `data/runtime/smoke-2026-11-03/latest.log`.
- **Loot injection fixed and widened (2026-11-03).** Playtest found no tickets in village, ruined-portal or Apotheosis chests. Two causes: NeoForge only loads modifiers named in `data/neoforge/loot_modifiers/global_loot_modifiers.json` (the mod shipped the four files but no manifest, so none were active), and the D1 allowlist covered the 15 cached structure jars rather than the pack's own chests. Added the manifest, extended the four band lists to 536 tables (vanilla chests plus the shipped pack's structure chests), added a GameTest that generates a village chest through the modifier, and taught `chaoslab datapack` to reject unlisted modifiers and cross-band duplicates.
- **Coverage measurement (published 2026-11-03).** `reports/pack_measurements.md` measures what the current content can resolve. The first run found the 8-entry starter set left `ability`, `skill` and `familiar` empty and every preset above 4.4 dead; the coverage pass below fixed that. Current state: 66 entries, every category and preset resolves with the engine's retry budget, one curse ships, and all four ticket modifiers still use chance 1.0 (one ticket per listed chest, 240–720 tickets/day at 10–30 chests/hour versus the D3 sweep's 4–30/day).
- **Coverage-first content pass (delivered 2026-11-03).** The original 8-entry starter set left `ability`, `skill` and `familiar` empty and every preset above the 4.4 ceiling dead. A generated 50-entry coverage set now supplies ten entries per category at rarity steps 0.5, 1.3, 2.3, 3.3, 4.3, 5.3, 6.3, 7.3, 8.3 and 9.3 (58 coverage entries; 66 total with the 8 race traits). Every preset and category now resolves with the engine's retry budget; `reports/pack_measurements.md` shows the per-preset coverage. The entries are deliberately generic coverage rewards (vanilla items, potion effects, attribute modifiers and spawn-egg familiars) and are the placeholder the authored corpus will replace. Attribute traits are reapplied on login and respawn, and a GameTest covers the respawn path. The 1.21.1 attribute ids are `minecraft:generic.*`; the starter/coverage traits and Glass Bones used the shortened forms, so they did nothing until this pass fixed them and the validator began checking vanilla attribute ids.
- **Race changes (delivered 2026-11-03).** Neo Origins (NeoForge Origins port) is pinned at milestone A after a clean co-load (`Done 4.596s`, 77 origins, 2 layers, 928 powers). A `gacha:origin` adapter sets an origin through `OriginChangeService.set(..., ADMIN)` reflectively, so the mod still loads without Neo Origins; origin entries in the same layer replace each other in the owned set. Eight corpus race traits ship first (Fishman→merling, Dryad→verdant, Gargoyle→stoneguard, Android→automaton, Angel→elytrian, Imp→cinderborn, Vampire→vampire, Dragonlord→draconic) and the remaining `race-change` entries wait for a mapping policy. The first live race roll exposed the API argument order: it is `set(player, layer, origin, mode)`, not `(player, origin, layer, mode)`; fixed, and a refusal now logs the returned result. The origin adapter needs a live player, so it is not covered by the mock-player GameTests.
- **Power Score calibration note (2026-11-03).** The formula is fully implemented, but the D3 reference is the full corpus (667 entries, 538.4 gear). With the current 66-entry slice the ceiling is ~0.105, and 24 unique entries reads ~0.038; the low number is calibration, not a missing implementation. The score rises as the corpus lands, or a pack can lower `reference.entries`/`reference.gear` in `config/gacha/power_score.json` for a shorter arc.
- **Still to do:** import the rest of the entry and curse corpus with adapters, choose the injection chance against a real chest-opening rate, install the new archive in a client, and run a sustained play arc. Balance from that evidence rather than from the coverage set.

### Ordering

1. Phase 3 before Phase 4: D1 depends on which structure mods ship, and the pack declaration now fixes that set.
2. D1 needs one jar-inspection pass over the cached mods; D2 and D3 are answered.
3. Phase 4, then Phase 5.

### Runtime identity check (complete)

`python3 -m chaoslab runtime --log <dir>` now refuses to treat a capture as evidence about the pack unless the jars NeoForge reports discovering under the instance `mods` folder match the `filename` values pinned in `pack_lock.json`. Three verdicts are recorded: `match` (the discovered set is exactly the locked set), `drift` (a jar loaded that is not locked, or a locked jar missing; the run fails), and `unverified` (no discovery lines — missing evidence, not a pass). Launcher framework jars (`client-*-srg.jar`, `neoforge-*-universal.jar`) are ignored because they are not pack content, and crash reports repeat only the failing jar so they never establish the set. Filenames are the strongest signal a log carries: a same-named jar re-uploaded with different bytes is indistinguishable without the lock hashes.

### Acceptance contract

`make check` is the project truth: it runs `python3 -m chaoslab verify`, which regenerates every manifest-pinned derived artefact offline into a scratch root and compares bytes with the committed files and `reports/MANIFEST.sha256`, and validates `PROJECT_PLAN.md`, `candidates.txt`, `pack_manifest.json` and the cached `.mrpack` set in place. `make check-fast` validates inputs only and is cheap enough for every edit. Host-level registration of that command lives outside the repository, so a write run can still end with an unqualified-handoff footer while the gate is green.

## 13. Evidence anchors

Recorded during discovery; line numbers refer to the source tree at snapshot time.

- Doc: 120 (feats central), 123-127 (relative impressiveness), 129-139 (anti-decomposition), 143 (diminishing returns), 147-157 (category mapping), 161-183 (tiers), 199 (Advantage choice), 205 and 383 (ticket/result calibration), 211 and 356 (Random category), 261-263 (ability slots), 267 (traits), 281-285 (items), 293 (familiars), 305 (skills), 332 (curses optional), 336-346 (curse payouts).
- `trait.txt` 938: downgrade-reroll meta quirk.
- `item.txt` 463-468: tickets as entries with 6x Advantage; 1012-1020: Gambler dice; 851-860 and 1010-1011: node/tree quirks (out of scope).
- `familiar.txt` 100, 110, 246, 460, 462, 474, 486, 1186, 1188: lifecycle examples.
- `Gacha.py` 96-97: `(Gacha)` marker stripping.
- `web/js/curse-app.js` and `web/data/curses.txt`: d20 severity table and payouts.
- `tools/export_web_data.py` 24-47: the ticket `TIERS` table with the twelve min/avg/max windows, plus the wild flat-ticket note. The header comment records that the table comes from `Gacha.py` presets and extended tree-mode tiers.
- GitHub API `/repos/eternaldensity/ChaosGacha` (read 2026-10-21): `fork: true`, parent `Bronzdeck/ChaosGacha`, default branch `master`. Raw `master` `tools/export_web_data.py` sha256 `a069238d370dbc12bfeb182b02342ba3dca125319dd4261016134aaf81f79e4b`, identical to the vendored `ChaosGacha/tools/export_web_data.py` at commit `af084bf`. A fetch on 2026-10-29 moved `origin/master` to `00739d6`; that file differs there, so the sha256 identifies the snapshot rather than current `master`.
