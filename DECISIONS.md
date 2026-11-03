# Decisions

Eight decision sheets. D1–D7 were written 2026-10-26 from on-disk evidence only; D8 was
added 2026-10-28 to record the launcher and instrumentation choice.

Answer under each sheet's `Answer:` line, in the closed form given. Every sheet carries a
default, so work can continue while it is blank.

## Why this file exists

`PROJECT_PLAN.md` §7 has 33 register rows and §11 has three open items. Four further
questions were raised while planning the pack survey (D4–D7) and were never written down,
so a later run could not look up what the names meant. This file collects all eight in one
place, with the evidence each one depends on.

Nothing here overrides the plan. Where a sheet disagrees with `PROJECT_PLAN.md`, the plan
is right and the sheet is wrong.

## How to answer

- One sheet per decision, stable IDs D1–D8. Do not renumber.
- Closed form preferred: tick a row, approve a list, fill numbers. The answers land in
  `fit_rules.json`, the config schema or `PACK.md`, so free prose costs a translation step.
- Answer in this file, then mirror the result into `PROJECT_PLAN.md` §7 or §11 in the same
  turn, and add a line to the Answer log at the bottom.
- `DECISIONS.md` is not a generated artefact, so it is outside `reports/MANIFEST.sha256`.
  The relevant check is `python3 -m chaoslab verify`, which must still pass.

## Work queue

Ordered by what blocks the next milestone, not by ID.

| Order | ID | Question | Blocks | Status |
| --- | --- | --- | --- | --- |
| 1 | D4 | Which sections ship in milestone A | N4 | Answered 2026-10-26 |
| 2 | D5 | Ratify the no-build replacements | N4 | Answered 2026-10-26 |
| 3 | D6 | CDN manifest or bundled jars | distribution | Answered 2026-10-26 |
| 4 | D7 | Fit coverage cut-off | fit report | Answered 2026-10-26 |
| 5 | D2 | Social curse set and NPC hooks | curses | Answered 2026-11-03 |
| 6 | D3 | Power Score weights and range | milestone B | Answered 2026-11-03 |
| 7 | D1 | Structure table to ticket band | chest removal | Answered 2026-11-03 |
| 8 | D8 | Launcher and instrumentation policy | runtime harness | Answered 2026-10-28 |

`Blocked` means the extraction artefact is still missing. `Extracted` means the artefact
exists and only the answer is outstanding. Each sheet names what it needs and what happens
if it stays blank.

## The numbers the sheets quote

- Candidates: 162 entries in 19 sections — 154 buildable, 8 with no build.
  Decomposed: 103 content / add-on / quest rows, 52 required-dependency libraries,
  7 negative-evidence slugs.
- Fit: 4233 corpus rows, 3332 mapped by 17 rules, 901 unmapped.
- Curses: 115 records, 7 mature, 114 resolvable, 1 one-and-done.
- Pack verdicts: 16 core, 6 seed, 17 adoption, 54 library, 4 support, 1 add-on, 28 trial,
  22 defer, 2 optional client-only, 2 review, 2 exclude, 8 no build.

---

## D4 — Pack shape

Status: Answered 2026-10-26 — see "Answers recorded 2026-10-26"

### Evidence

- `candidates.txt` — 19 sections, 162 entries, per-section line numbers below.
- `reports/pack_assessment.md` — necessity and suitability per candidate.
- `PROJECT_PLAN.md` §9.2 lines 320–331 — verdict counts and the two policy exclusions.
- `reports/fit_summary.md` lines 35–47 — which candidates are fit hosts, and for how many
  rows. A candidate that is not a fit host carries no gacha mapping.

### Section inventory

| Section | Line | Rows | Supplies |
| --- | --- | --- | --- |
| Magic | 25 | 4 | ability hosts (Ars Nouveau, Iron's Spells) |
| Tech | 31 | 8 | tech hosts (Create, Mekanism, Oritech, AnvilCraft, Electrodynamics, Tempad) |
| Mobs / familiars | 42 | 4 | familiar content (Alshanex's Familiars host) |
| Dimensions / worldgen | 48 | 3 | location hosts (Aether, Terralith, BOP) |
| RPG progression | 53 | 5 | item hosts (Apotheosis, Artifacts, Curios, Simply Swords, JustLeveling) |
| Gacha-adjacent / randomisation | 60 | 1 | randomisation (Lootr, excluded by §9.2) |
| Endgame / gamebreaking | 63 | 1 | game-breaking content (Re:Avaritia) |
| Support / UI | 69 | 6 | libraries and client QoL |
| Add-ons: Ars Nouveau | 77 | 4 | add-on |
| Add-ons: Iron's Spells | 83 | 5 | add-on |
| Add-ons: Create / Aeronautics | 90 | 9 | add-on |
| Add-ons: Apotheosis | 101 | 2 | add-on |
| Quest systems | 105 | 2 | Odyssey Quests, JustQuests |
| Survey additions (popular 1.21.1 NeoForge packs) | 115 | 5 | storage, trade, waystones |
| Survey additions, round 2 (content, worldgen, quest hooks) | 124 | 28 | structures, farming, Create add-ons |
| Compatibility | 158 | 3 | cross-mod glue |
| Survey additions, round 3 (modpack harvest: content and progression) | 163 | 13 | structures, biomes, AE2, Create tech |
| Required dependencies (libraries pulled by candidates) | 182 | 52 | libraries pulled by candidates |
| Checked: no 1.21.1 NeoForge build | 248 | 7 | negative evidence |

Totals: 103 + 52 + 7 = 162. Line numbers are the `# ==` heading lines in
`candidates.txt`; `reports/mods_survey.md` is authoritative if the two ever
disagree.

### Fit hosts, and what that implies

Only some candidates are hosts for a fit rule. From `reports/fit_summary.md`:

- Magic: `ars-nouveau` 1403 rows, `irons-spells-n-spellbooks` 1311 rows.
  `primal-magick` and `golem-magicka` are not fit hosts at all.
- Tech: `create` 234, `mekanism` 234, `oritech` 234, `anvilcraft` 104,
  `electrodynamics` 104.
- Items and progression: `apotheosis` 1412, `artifacts` 1056, `justleveling-fork` 1020,
  `curios` 360, `simply-swords` 360.
- Familiars: `alshanexs-familiars` 684. `mowzies-mobs`, `mobs-of-mythology` and
  `alexs-mobs-continued` are not fit hosts.
- Worldgen: `aether`, `terralith`, `biomes-o-plenty` at 23 rows each — they are the whole
  host set for `structure-placement`.

So pack shape is not only a taste question: dropping a fit host orphans the rules that
name it.

### Options

| Option | Shape | Cost |
| --- | --- | --- |
| A | Full 19 sections | Largest surface; most overlap and licence exposure; hardest to balance |
| B | Milestone A = core + seed + support + add-on (27 projects), adoption and library arrive transitively, trial and defer wait | Excludes no fit host; keeps the pack buildable in one pass |
| C | Core only (16 projects) | Drops the familiar and worldgen hosts; several rules lose their only target |

Recommendation: B, medium-high confidence. It covers every fit host, keeps the pack
small enough to test, and leaves the 28 trial and 21 defer rows as milestone B material.

### Sub-choices

1. Magic systems: keep 4, 2 or 1. Only Ars Nouveau and Iron's Spells are fit hosts;
   Primal Magick and Golem Magicka exist as Botania replacements and map no rows.
2. Tech breadth: Create only, or Create plus Mekanism/Oritech/AnvilCraft/Electrodynamics.
   The wider set is what actually hosts the tech rules.
3. Worldgen overlap: 22 worldgen and structure entries is a lot of terrain in one pack.
   15 of them are structure-oriented (11 YUNG's, Structory, Structory Towers, Dungeons and
   Taverns, Towns and Towers). Trimming terrain (Nullscape, Deeper Darker, Regions
   Unexplored, BOP, Terralith) is lower risk than trimming structures.
4. Quest layer in milestone A: yes or no. The mod choice is already settled (row 25,
   Odyssey Quests); this only asks whether the layer ships in A or B.

### Answer format

```
include: B            (default: all except the two policy exclusions)
defer:   ____
drop:    ____
magic systems:  2          (default 2: Ars Nouveau + Iron's Spells)
tech:  full         (default full)
worldgen:  keep all (default trim terrain)
quest layer in milestone A: yes  (default yes, Odyssey)
```

---

## D5 — Ratify the no-build slugs and the broken chains

Status: Answered 2026-10-26 — see "Answers recorded 2026-10-26"

### Evidence

- `candidates.txt:14–21` — the recorded replacements, with a reason per line.
- `candidates.txt:214–217` — `expandability` kept as negative evidence.
- `candidates.txt:238–240` — the permanent 404 `cC0JkO8i` and why it is not retried.
- `candidates.txt:242–249` — the 7 slugs with no 1.21.1 NeoForge build.
- `PROJECT_PLAN.md` §9.2 lines 326–331 — the two policy exclusions.

### The eight

| Slug | Bucket | Replacement already in file |
| --- | --- | --- |
| botania | replace | primal-magick, golem-magicka |
| thermal-expansion | replace | oritech, electrodynamics, energized-power |
| alexs-mobs | replace | mowzies-mobs, mobs-of-mythology, alexs-mobs-continued |
| alexs-caves | drop | none; worldgen section covers terrain |
| ice-and-fire-dragons | replace | cataclysm-spellbooks, mowzies-mobs |
| blue-skies | replace | aether, terralith, biomes-o-plenty |
| relics | replace | artifacts, curios |
| expandability | drop | none; complete version is CurseForge-only (row 27) |

### The three chains

1. `asterism-arcanum` → `expandability` (no build) → excluded by the Modrinth-only policy.
   Recorded as `exclude (dependency)` in §9.2. Closed, no action.
2. `simply-swords` → `fzzy-config` → `kotlin-for-forge`. `kotlin-for-forge` is now in the
   dependency section (`candidates.txt:219`), so the chain resolves. Closed.
3. `ars-creo` → `cC0JkO8i` returns 404 permanently. It sits beside a valid `create`
   requirement, so it is incomplete metadata rather than an uninstallable candidate.
   Recorded at `candidates.txt:238–240`. Closed.

### Answer format

```
replacements: approve as recorded / override: <slug> = <choice>
policy exclusions: approve asterism-arcanum and lootr / override: <slug>
```

Default: approve as recorded. Nothing is blocked while this is blank, because the file
already matches the table.

---

## D6 — Delivery model

Status: Answered 2026-10-26 — see "Answers recorded 2026-10-26"

### Evidence

- `PROJECT_PLAN.md` §7 row 27 — Modrinth-only sourcing, settled. It settles where mods
  come from, not how the pack is delivered.
- `reports/mods_survey.md` — a licence column per candidate.
- `reports/pack_assessment.md` — folds licence into each suitability score.

### Options

| Option | Mechanics | Cost |
| --- | --- | --- |
| A | `.mrpack` with Modrinth CDN URLs; jars are not included | Needs a launcher that resolves Modrinth URLs; no offline install; a delisted project breaks install until pinned |
| B | bundle jars under `overrides/mods` | Fully offline and immune to delisting; needs redistribution permission for every ARR mod, on every update |

Recommendation: A, high confidence. It keeps the pack a manifest rather than a
redistribution, so the licence question never reaches the critical path, and it matches
row 27's sourcing intent. Choose B only if offline installation becomes a hard requirement.

### Answer format

```
model: A
```

Default: A.

---

## D7 — Fit coverage cut-off

Status: Answered 2026-10-26 — see "Answers recorded 2026-10-26"

### Evidence

- `reports/fit_summary.md` lines 3–4, 56–84.
- `fit_rules.json` — 17 rules, all v3 and all citing resolvable mods.

### Numbers

901 unmapped of 4233 rows (21%). By entry kind: item 430, trait 237, ability 234 — those
three sum to the whole 901, so the gap is entirely within kinds that already have rules.

Top unmapped tags, as occurrences (a row may carry several tags, so these do not sum to
901): divination 39, time 37, tech 35, fumo 29, kinetic 27, mundane 25, nature 24, card 24,
meta 22, vehicle 22, dimension 22, ticket 20, resource 19, fire 17, implant 17, neutral 16,
spirit 16, lifestyle 16, earth 15, production 15.

Note that `tech` and `spirit` already appear as mapped tags through `tech-ability` and the
summon rules; an unmapped row carrying them is unmapped because of its entry kind, not
because the tag has no rule.

### Options

| Option | Effect | Cost |
| --- | --- | --- |
| A | Add 2–4 item-tag rules, then declare the trait and ability remainder out of scope | Removes the largest block (item 430); leaves roughly 470 rows labelled out of scope |
| B | Sweep the top 20 tags with a rule each | Maximum headline coverage; many thin rules claiming mechanics the pack may never implement |
| C | Freeze as is; label all 901 out of scope | No new false analogues; 21% of the corpus stays unclaimed in the report and looks unfinished |

Recommendation: A, medium confidence. Item rules are the highest-confidence fit type in
the report (`item-equipment` 0.75 Direct), so the item block is where mapping stays honest.
The trait and ability remainder should be declared out of scope explicitly rather than
left as an unexplained tail.

### Answer format

```
scope: B
if A: rules to add: ____ ; out-of-scope label: yes / no
if B: tag threshold: top 25
```

Default: A with the out-of-scope label on.

---

## D1 — Structure loot table to ticket band

Status: Answered 2026-11-03 — see "Answers recorded 2026-11-03"

### Evidence

- `PROJECT_PLAN.md` §6.12 — the five-band policy, already settled.
- `PROJECT_PLAN.md` §11 item 3 — the open mapping.
- `PROJECT_PLAN.md` §7 row 23 — removal is an explicit per-table allowlist.
- `candidates.txt` — 22 worldgen and structure entries, 15 of them structure-oriented
  (11 YUNG's, Structory, Structory Towers, Dungeons and Taverns, Towns and Towers).

### Why it was blocked, and what changed

The mapping needs loot table IDs. Those live inside jars, and every earlier pass had none
cached: `data/mods/` holds Modrinth JSON and `data/modpacks/` holds `.mrpack` indexes and
quest overrides. `chaoslab structures --collect` now resolves the 15 structure candidates
from the cached version responses, verifies each download against its published sha1 and
size, and caches the jars under `data/jars/` (15 jars, 36,147,670 bytes).

### Consequence of leaving it blank

No allowlist entries means no loot is stripped, which is exactly the injection-only mode
row 23 already keeps as a config switch. Milestone A is unaffected; only the
strip-from-chests behaviour waits.

### What was generated

`reports/structure_tables.md`, one row per loot table: table ID, mod, jar path, matched
hint, proposed band and confidence. It lists 419 tables across the cached jars, of which
305 are chest-typed. Source: list `data/<namespace>/loot_table*/**` inside each structure
jar, then join against the bands in §6.12. `chaoslab verify` regenerates the report
offline, so the band proposals cannot drift from the cache.

The bands are keyword proposals from the whole table id, not verified depths, and Diamond
is unreachable from the heuristic — §6.12 reserves it for modded endgame, which a loot
table id does not identify. Those rows need the human answer below.

D1 feedback (2026-11-03) asked for more matchable hints: the family-word hint set was
extended so every one of the 305 chest tables now carries a proposed band (previously 188
were `unknown`); the report regenerates with the new bands and zero unknown rows.

### Answer format, once the artefact exists

```
band: <name>  accept: <table ids, one per line>  reject: <ids>
```

Default until then: empty allowlist, injection-only.

---

## D2 — Social curse set and NPC hooks

Status: Answered 2026-11-03 — see "Answers recorded 2026-11-03"

### Evidence

- `data/curses.jsonl` — 115 records with id, label, severity, tier, resolve, nsfw.
- `reports/curse_summary.md` — band counts and the mature-entry count.
- `reports/curse_triage.md` — one row per curse: id, label, tier, hook class,
  feasibility, confidence, matched keywords and a proposed implementation.
- `PROJECT_PLAN.md` §6.8 and §7 row 9 — social curses are reworked or replaced where
  unimplementable. That policy is settled; this sheet is not asking whether to keep social
  curses, only which ones and what replaces the rest.

### Numbers

115 curses; 7 mature; Minor 29, Medium 39, Major 31, Severe 10, Ultimate 6; 114
resolvable, 1 one-and-done. Triage: 59 mechanical, 53 rework, 3 drop, 26 rows with no
keyword match.

### What the extraction records

Every curse now has a proposed hook class and feasibility, so the sheet no longer waits on
data. The 7 mature entries are marked `gated` in the table. What remains is the answer:
approve the sheet wholesale, or override the rows you disagree with.

### Answer format

```text
band policy: ____            (default: Minor and Medium mechanical, Major and above case by case)
mature entries: ship behind default-off config / cut    (default: ship, gated)
overrides: <id> = rework|drop   (one per line)
```

Default: the band policy above, nothing cut; the triage table's classifications stand
until an override is written.

---

## D3 — Power Score weights, default and range

Status: Answered 2026-11-03 — see "Answers recorded 2026-11-03"

### Evidence

- `PROJECT_PLAN.md` §6.9 line 195 — the named inputs: gear and attribute totals, owned
  entries, progression stage.
- `PROJECT_PLAN.md` §7 row 26 — weights are config with a documented default and range.
  Settled; this sheet is only the numbers.
- `reports/power_score_sweep.md` — the sweep itself: three profiles, P10/P50/P90 per
  snapshot, the proposed vector and an answer sheet.
- `data/corpus.jsonl`, `reports/summary.md`, `chaoslab simulate`.

### What the sweep shows

`reports/power_score_sweep.md` models casual (4 tickets/day), regular (12/day) and grinder
(30/day) income over a 28-day arc, with 15 seeded arcs per profile. It reports P10/P50/P90
for gear totals and owned entries at early, mid and late snapshots, and derives weights
from each input's observed spread: gear 0.36, entries 0.36, stage 0.28, with a ±0.10 range
and clamps at 0.05 and 0.80. Gear is the summed rarity of unique item draws, the closest
available proxy for gear and attribute totals, and stage is deterministic by design.

### Answer format

```text
weights: gear 0.__, entries 0.__, stage 0.__
range: ±0.__
weights clamp: min 0.__, max 0.__
score clamp: min 0.__, max 0.__
```

Default: the sweep's proposed vector (0.36 / 0.36 / 0.28, ±0.10, 0.05–0.80) stands until
you override it.

---

## D8 — Launcher and instrumentation policy

Status: Answered 2026-10-28 · Blocks: nothing (records an already-made choice) · Owner: you

### Evidence

- `reports/runtime_compat.md` records Prism Launcher as the launcher used for the manual
  client boot evidence.
- `PROJECT_PLAN.md` §12, “Runtime identity check (complete)” — the harness reads NeoForge
  discovery lines from a log directory and diffs jar filenames against `pack_lock.json`;
  it never invokes a launcher.
- `chaoslab/runtime.py` collects `.log` and `.txt` files from a directory, so any launcher
  that writes standard NeoForge logs can be used.
- Delivery is a `.mrpack` referencing Modrinth CDN URLs (§7 row 31), which Prism imports
  and which a plain server can be assembled from.

### Options considered

| Option | Client | Deterministic instance export | Log capture | Headless launch |
| --- | --- | --- | --- | --- |
| Prism Launcher | yes | yes — `.mrpack` import, one instance folder per pack | standard `logs/` under the instance | not verified |
| Direct JVM (server) | n/a | yes — fixed arguments and working directory | stdout plus `logs/latest.log` | yes |
| Custom organiser | would need building | would need building | would need building | would need building |

### Decision

```
client verification launcher: Prism
server smoke test:            direct JVM, no launcher
harness coupling:             none — a log directory is the only interface
custom organiser:             not built; no instrumentation need justifies it
```

### Consequences

- The identity check is launcher-agnostic: it works on Prism logs, a bare server log, or a
  hand-assembled instance, because it parses the log rather than the installation.
- Prism stays a convenience for humans, not a dependency of the gate.
- Headless Prism launch is not relied on and was not verified, so a WSL-side Prism is
  optional. The direct-JVM path is the supported headless route.

### Answer format

Already answered above; change it only if the client launcher changes.

---

## Answers recorded 2026-10-26

D4–D7 were accepted exactly as proposed. This block is the authoritative record; the
evidence stays in each sheet above. Mirrored into `PROJECT_PLAN.md` §7 rows 29–32.

### D4 — Pack shape

```
include: B
defer:   outside the promoted sections, the adoption / trial / defer rows wait for
         milestone B; a promoted section (Tech, Dimensions / worldgen, Quest systems)
         ships whole, so its trial and defer rows ship with it
drop:    the two policy exclusions only — asterism-arcanum-addon (dependency), lootr (design)
magic systems:  2       (Ars Nouveau + Iron's Spells; primal-magick and golem-magicka remain resolvable alternatives)
tech:  full            (Create + Mekanism + Oritech + AnvilCraft + Electrodynamics)
worldgen:  keep all    (no terrain trimming in milestone A)
quest layer in milestone A: yes   (Odyssey Quests)
```

### D5 — No-build slugs and broken chains

```
replacements: approve as recorded
policy exclusions: approve asterism-arcanum and lootr
```

### D6 — Delivery model

```
model: A
```

### D7 — Fit coverage cut-off

```
scope: A
if A: rules to add: 2–4 item-tag rules, chosen after re-measuring the item block; out-of-scope label: yes
```

---

## Answers recorded 2026-11-03

D1, D2 and D3 were answered as recorded below (D2 approved with two reworks; D1
accepted wholesale). Mirrored into `PROJECT_PLAN.md` §6.12, §6.8, §6.9, §7 rows 26,
34 and 35, and §11.

### D1 — Structure loot tables

```
band: all  accept: the D1 answer sheet wholesale  reject: none
```

All 305 chest tables are accepted at their proposed bands (Bronze 61, Silver 156,
Gold 60, Platinum 28; Diamond empty), encoded as four per-band `gacha:add_ticket`
loot modifiers in `mod/datapack/data/gacha/loot_modifiers/`. Two follow-ups stay
open in `PROJECT_PLAN.md` §11: the removal strip list (which stacks the conversion
strips per band) and the vanilla/milestone-A table enumeration, since the accepted
ids come from the 15 cached structure jars (milestone-B candidates).

### D2 — Curse triage

```
band policy: Minor and Medium mechanical by default; Major and above case by case
mature entries: ship behind a default-off config
overrides:
curse-0003 = rework  # Infertile: slow crop growth; a chance to cancel animal breeding
curse-0014 = rework  # Curse of Gray: armor pieces can drop when hit; not nudity
```

The rest of the triage table is approved as the implementation set. The two
reworked entries drop their source mature flag, leaving five gated entries
(`curse-0023`, `curse-0028`, `curse-0030`, `curse-0044`, `curse-0055`).
`reports/curse_triage.md` marks the two rows `decided` and carries this block.

### D3 — Power Score

```
weights: gear=0.36 entries=0.36 stage=0.28
range: ±0.10
weights clamp: 0.05 .. 0.80
score clamp: 0.0 .. 1.0
reference: gear=538.4 entries=667
```

Rationale recorded with the answer: practical play is needed before anything can
be adjusted, so the sweep's proposal becomes the shipped default
(`mod/config/power_score.json`); tuning waits for the measured arcs of Phase 5.

---

## Already settled, do not re-open

Listed so a later run does not mistake them for live questions.

- Removal default (§7 row 23).
- Portable opener charge model (row 24).
- Quest mod choice: Odyssey Quests (row 25).
- Power Score as config with a documented range (row 26).
- Modrinth-only sourcing (row 27).
- Tickets tradeable by default (row 28).
- Three curse slots, curses persist through death, no power ceiling (rows 6–8).

## Answer log

Append one line per answered sheet: date, ID, answer, where it was mirrored.

| Date | ID | Answer | Mirrored to |
| --- | --- | --- | --- |
| 2026-10-26 | D4 | Option B; 2 magic systems; full tech; keep all worldgen; quest layer in milestone A | `PROJECT_PLAN.md` §7 row 29 |
| 2026-10-26 | D5 | Approve replacements as recorded; approve the asterism-arcanum and lootr exclusions | `PROJECT_PLAN.md` §7 row 30 |
| 2026-10-26 | D6 | Option A — `.mrpack` with Modrinth CDN URLs, jars not bundled | `PROJECT_PLAN.md` §7 row 31 |
| 2026-10-26 | D7 | Option A — add 2–4 item-tag rules, declare the trait/ability remainder out of scope | `PROJECT_PLAN.md` §7 row 32 |
| 2026-10-28 | D8 | Prism for client verification; direct JVM for server smoke tests; harness launcher-agnostic; no custom organiser | `PROJECT_PLAN.md` §7 row 33 |
| 2026-11-03 | D2 | Approve triage; rework Infertile (crops/breeding) and Curse of Gray (armor drop, no nudity); mature gating stays, five gated | `PROJECT_PLAN.md` §6.8, §7 row 34, §11; `reports/curse_triage.md` |
| 2026-11-03 | D3 | Weights 0.36/0.36/0.28, ±0.10, bounds 0.05–0.80, score clamp 0.0–1.0, reference 538.4/667 | `PROJECT_PLAN.md` §6.9, §7 row 26, §11; `mod/config/power_score.json` already shipped it |
| 2026-11-03 | D1 | Accept all 305 chest tables at their proposed bands, reject none | `PROJECT_PLAN.md` §6.12, §7 row 35, §11; `mod/datapack/data/gacha/loot_modifiers/add_ticket_*.json` |
