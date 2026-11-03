# Ability Gacha — Stage 6: Power Scaling Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/ability.txt` (1383 entries;
numbers 842/843/873 skipped)
Scale: Trash 0.1–0.9 · Common 1.0–1.9 · Uncommon 2.0–2.9 · Rare 3.0–3.9 ·
Elite 4.0–4.9 · Epic 5.0–5.9 · Legendary 6.0–6.9 · Mythical 7.0–7.9 ·
Divine 8.0–8.9 · Transcendent 9.0–9.9.

Distribution: Trash 25 · Common 80 · Uncommon 197 · Rare 304 · Elite 273 ·
Epic 202 · Legendary 160 · Mythical 83 · Divine 41 · Transcendent 18.
EIGHTEEN Transcendents — the worst top-overcrowding of all four files
(skill 1, trait 8, familiar 12). Same treatment needed (§2). Collision
clusters (observation only): 4.8 ×48, 3.6 ×45, 3.8 ×42 — natural under
±0.2 bands, no change.

Method: ladder probes (kinesis chains, Logia set, heal/regen chains,
Tinker tier lines), gate-discount checks, bundle/stack math, cross-file
parity. No numbers changed — proposals only.

---

## 1. Exemplary lines (reference standards)

- **Kinesis ladders** (the file's best pattern): base kinesis at Elite
  (Pyro 4.4, Cryo 4.5, Hydro 4.6, Aero 4.9, Electro 4.8) → Level-5 Toaru
  masters at Mythical (7.2–7.8), with Micro at Uncommon (2.2) below. A
  consistent +2.8–3.0 "Toaru premium" — document as the standard
  canon-mastery price.
- **Heal ladder** 2.3/3.5/4.3/5.5 → Divinity 8.6; **Regen ladder**
  2.7/3.6/4.8/5.5/6.9: clean, with the Divine jump (+3.1) as an explicit
  divinity premium — confirm intentional.
- **Logia ladder** Snow 4.9 < Desert/Swamp 6.2 < Darkness 7.0 < Ice 7.1 <
  Fire 7.6 < Magma 7.8 < Light 8.0: elemental hierarchy indexed. (Snow-vs-Ice
  gap 2.2 is the widest step — confirm or narrow.)
- **Tinker tier lines** (Vehicles/Bio/Mech/Alchemy/Augments/Defence/Ranged/
  Robotics I–V): mostly consistent ~1.2–1.5 steps (e.g. Alchemy
  2.1/3.8/5.2/6.4/7.8 — near-perfect). Copy this curve for future tiered
  lines.
- **Stones-style gating analogues**: Zanpakuto entries carry
  no-energy-given + no-evolution gates on EVERY entry; Conduit entries
  (Infamous) run on absorbed element, not user energy, with explicit
  no-time-travel carve-outs. Systematic risk-gating — the file's best habit.
- **Divinity band** (Water&Ice 8.0, Earth 8.4, Fire 8.5, Necromancy 8.5,
  Healing 8.6, Sky 8.6): tight, coherent god-tier pricing.
- **Top-end ordering** True Magics 9.0–9.2 < PtV 9.6 < Immortal/Exclusion
  9.7 < Invulnerable 9.8 < All Fiction 9.9: scope-indexed and correctly
  ordered — keep the order, demote the crowd (§2).

## 2. Inversions and mispricings (fix first)

| # | Entry | Now | Problem | Suggest |
|---|-------|-----|---------|---------|
| 267 | Black Hole (trainable REAL black holes) | 5.0 | Planet-killer at Epic | → 8.5+ or virtual-only |
| 938 | Tinker - The Baker (compress universes, atom-to-cookies) | 9.9 | Same joke-capstone disease as Spiral 9.9 (trait) | Defined set, nerf, or remove |
| 917 | Luck Manipulation | 9.7 | Luck-stat manip near top; vs item Draw of Fate 3.3? | Calibrate luck pricing cross-file |
| 676/675/686/681/1054 | Base-name Tinkers (Vehicles 4.2, Bio 7.8, Mecha 8.2, Ranged 5.6, Augments 4.5) | — | Duplicate tiered lines: Vehicles 4.2 ABOVE tier-III 4.1; Bio 7.8 EQUALS tier-IV 7.8; Mecha/Ranged/Augments sit between tiers | Merge into tiered lines or define base=tier-III rule |
| 1091 | Vehicles (IV) | 6.7 | III→IV gap 2.6 (line norm ~1.2–1.5) | → ~5.5 or justify |
| 713 | Twice (MHA cloning) | 8.3 | Clone cluster (401–403, 710–713) needs ordering; Twice above most | Confirm clone hierarchy + cross-check skill Clone Split |
| 682 | Kyokai Suigetsu Shikai | 7.0 | Above most Bankai (cf. item-file Kyokai note) | Confirm hypnosis-vs-power ordering |
| 111 | Divinity Water & Ice ("all that entails") | 8.0 | No mechanics (clarity blocker) | Concrete kit or cut |
| 548 | Wheel of Mahoraga | 8.2 | Adaptation engine + item Rinnegan Jar + familiar Mahoraga — three Mahoraga prices? | Cross-file parity check |
| 654 | Rinnegan (six-paths + Outer revive) | 8.8 | Bundle vs item Rinnegan Jar (implant) | Define bundle-vs-implant pricing |
| 731 | Divinity Fire ("domain over ALL fire") | 8.5 | Overrides other fire users? | Capped rank/scope or override rules |
| 694 | Dreadon (universe-range sniper, black-hole bombs) | 8.3 | Unpriceable open ceiling | Cap + arc-resource gating |
| 715 | Dark Matter (ANY property incl. life/clones/powers) | 9.5 | "Only limit is computational power" undefined | Whitelist + ban power-granting |
| 776 | Path to Victory (one-in-googol, nigh-omniscient) | 9.6 | No blind-spot/cost/combat rule | Ban/restrict or full mechanic |
| 879/885 | Immortal (stats PER DEATH) / Level Up (10% per kill) | 9.7/— | Infinite farms | Remove scaling / cap / sapient-farm ban |
| 1324 | Greater Guard (decapitation→nick transfer) | — | Inverted/lethal math | Rewrite, forbid lethal transfer |
| 809/801/808 | Save & Load / Clockwork / Flawed Return | 9.0/— | Scope undefined (self vs world? death?) | Self-checkpoint vs world-rewind ruling |
| 947 | D4C (death-transfers whole gacha!) | 8.8 | Death immunity + multiverse import | Ban transfer, travel-only |
| 654 | (above) | — | — | — |
| 918 | Wrath (uncapped, universe-ending) | 8.8 | No cap, mindless-beast endstate | Hard cap + stop condition |
| 921-923 | Magic Dominion / Void / Nihil | 8.1–8.5 | Near-limitless nullification/suction | Rank-difference + touch-range caps |
| 958 | Rule Breaker (remove gravity/magic/targetability…) | — | No table (remove death/costs?) | Whitelist + costs/durations |
| 1047 | Choosing Fate (enforce "absolutely improbable") | 8.5 | No cap/backlash/energy/paradox | Full mechanic or cut |
| 1079 | Hulk Out (no discernible limit) | — | Infinite strength | Hard cap / rage decay / cost |
| 1071 | The Tinkerer (ANY specialisation + multiversal/time) | 9.4 | Infinite breadth (Worm lore) | Whitelist + ban multiversal/time |
| 1112 | Defence (V) ("even gods cannot dent") | 8.6 | Unbreakable | Tier cap / counter |
| 1212 | Death Authority (point-to-kill, kill unkillable) | 9.4 | Immunity list? cost curve? | Full mechanic |
| 1350 | Grand Dissolution (melts flesh/stone/magic/space) | — | Resists? volume/speed? | Full mechanic |
| 1211 | Necromancy (100k controllable base-human?!) | 8.5 | Number/power caps by energy? | Full mechanic |
| 1292 | Inversion (Pyro→Cryo of ANY slotted ability) | — | Whitelist? Tinker/unique handling? | Whitelist / GM veto |
| 1298 | Tower Down (1km comms blackout, growing) | — | Scaling? allies? system/telepathy? | Full mechanic |

## 3. Uneven lines and ordering notes

- **Tinker base-vs-tier duplication** (§2 row 4): resolve by merging or by
  rule (base-name = tier-III equivalent? then reprice 676→4.1, 675→7.8
  already equal, 686/681/1054 to nearest tier).
- **Vehicles (IV) 2.6-gap** (§2): smooth to ~5.5.
- **Bio (III) 6.4 → plain Bio 7.8 = Bio (IV) 7.8**: exact duplicate price —
  fold plain Bio into the tiered line or differentiate.
- **Jutsu scrolls 5.2–6.0 by element / Bender spreads** (trait report):
  same arbitrariness — standardize or justify per element.
- **Zanpakuto Shikai-vs-Bankai premiums**: Kyokai 7.0 above most Bankai;
  Bankai premiums 1.3–2.6 uneven (item report) — confirm ordering
  principle (hax > raw power?).
- **Clone cluster** (401–403, 710–713 + Twice 8.3): order by autonomy
  (hive-mind < independent < self-replicating?) and cross-check skill
  Clone Split + item Duplication.
- **Heal/Regen Divine jumps**: confirm divinity-premium rule in Doc.
- **Logia Snow step**: confirm or narrow Snow 4.9 → Ice 7.1 gap.
- **Collision clusters** (4.8 ×48 etc.): observation only.

## 4. Cross-file parity (final pass — all four files now done)

- Revival ladder: Feather (item) vs Ygdar (trait 4.9) vs Nine Lives
  (trait 7.0) vs Puss (familiar 2.0!) vs Resuscitation (ability, 10-min)
  vs Rinnegan Outer Path (ability 8.8) — ONE ladder, price consistently
  (Puss is the outlier — confirm).
- Slot/slotless economy: slot-bypass grants (799/810/815 Fumos, 580/581
  slotless summons, 596 homunculus-copies-Elite, 27 sub-6.9 ability,
  563 Lily→Legendary Trait, 341 trains-only manual, Meruem slots,
  810 slotless Strength, Asauchi unlocks, Mahoraga-share?) — unify
  slot-bypass pricing across all four files.
- Teaching/training: Teaching skill tiers vs Tome learn-times vs
  Pearl-style static lists vs Hewg forge-time — one learning-curve rule.
- Tinker equivalence: skill Tinker costs vs ability Tinker tiers vs
  item Tinkertech ("Epic tinker level" rank ladder still missing!) —
  verify a Master-Mechanics build matches same-rarity Tinkertech.
- Mind/social offense vs defense: compulsions (ability batch) vs Mind
  Palace 6.2 (trait) vs Judging/Communication (skill) — price controllers
  up or bring a mid-tier resist.
- Luck: Draw of Fate 3.3 (item) vs Luck Manipulation 9.7 (ability) vs
  luck ladder (trait 2.7–5.7) — calibrate.
- Wish scales: Shenron (familiar/item) vs Shooting Star (item) vs Telos
  (item) vs PtV-adjacent — one wish-price curve.
- Energy storage/flow: Arc (item, GW-flow) vs Deka (item, hooked TW) vs
  Energy Abyss (trait 7.6, infinite stock) vs Mahoraga-style regen —
  flow-vs-stock calibration.

## 5. Recommended improvements (ordered)

1. Apply §2 table (economies, absolutes, loops, non-consensuals first).
2. Consent ruling (clarity report) — reprices a batch at once.
3. Demote Transcendent crowd (18!) to ~3–4 capstones with contest rules;
   cap universe/planet-scale effects explicitly.
4. Merge or rule the Tinker base-vs-tier duplicates; smooth Vehicles IV;
   publish the kinesis/Toaru/logia/divinity curves as Doc standards.
5. Inline all URL-only entries (519/634 + Tome spell lists) + unify
   teach-vs-cast; fix 1186–1189 tier→sacrifice copy-paste; rename/reorder
   Tinker Vehicles I-V; resolve 336's `Immutable` reference; confirm
   Logia package + Toaru baselines.
6. Final cross-file parity pass (§4) — the only task that needs all four
   files, and they are all ready now.
