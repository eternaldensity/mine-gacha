# skill clarity report (linked)

Auto-generated from `skill-clarity-report.md`. Entry names link to [entries/skill.md](entries/skill.md). Responses: [responses.tsv](responses.tsv).

---

# Skill Gacha — Stage 3: Clarity / Confusion Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/skill.txt` (302 entries)
Scope: entries that are especially confusing, unclear, badly defined, or need
human input. Typos (stage 1) and conciseness (stage 2) are already applied and
are NOT repeated here except where they block understanding.

Severity: **Blocker** = cannot implement / balance / adjudicate without an
owner decision. **Major** = highly ambiguous or requires outside knowledge.
**Minor** = joke / tone / wording obscures meaning but is playable.

---

## Blockers (need owner decision before stages 4–6 can be finalized)

### [20. All Life Eradication Fist](entries/skill.md#20-all-life-eradication-fist) — 8.4 Divine (One Punch Man), 8.4
Fuses "dozens of supernatural martial arts with knowledge granted by god" to
"replicate almost any known phenomenon". No god defined, no phenomenon list,
no scope. "Sufficiently physically strong" has no threshold.
**Ask:** wish-like "do anything if STR is high" or a closed effect list? Which
god, and what stat gate?

### [43. Renewal Taekwondo](entries/skill.md#43-renewal-taekwondo) — 6.6 Legendary (God of High School), 6.6
Capitalized `Recoilless` is never defined. No numbers or trigger.
**Ask:** what is Recoilless mechanically (passive buff, unlock, separate
skill)? What does it multiply/add?

### [57. Novice Physics](entries/skill.md#57-novice-physics) — 1.6 Common (Generic), 1.6
Novice tier includes "how to build a nuclear bomb", breaking the
Novice→Adept→Expert→Master progression.
**Ask:** joke to remove, or move practical nuke-building to Expert+?

### 31 / 91 / 115 / 139 — Taming line (Intermediate/Adept/Expert/Master)
"Apply to people to an extent / to a lesser extent", "eligible familiars"
undefined. No limits on sapient coercion, duration, or resistance.
**Ask:** can taming force obedience/loyalty on people? Hard limits,
resistance checks, duration? Or beasts-only?

### [32. Intermediate Pressure Points](entries/skill.md#32-intermediate-pressure-points) — 3.8 Rare (Generic), 3.8
"Paralyse people or cause pleasure and more" — "and more" is open-ended. No
duration, save, or human vs non-human scope.
**Ask:** closed effect list + duration/limits in combat?

### [170. Divine Formula](entries/skill.md#170-divine-formula) — 8.0 Divine (Highschool DxD), 8.0
"Replicate the Kankara formula from DxD" is undefined in-repo. "Vessel too
weak … melt your brain" — vessel has no mechanical meaning.
**Ask:** what should Kankara do in ChaosGacha terms (calculation?
precognition? magic hacking?), and what is the concrete overuse penalty?

### [218. Rokushiki](entries/skill.md#218-rokushiki) — 5.0 Epic (One Piece), 5.0
"6 techniques plus a secret 7th" never named. "Start knowing all but must
train to use them" is contradictory.
**Ask:** list the 6+1 by name with 1-line effects each; define starting state
(known-but-weak vs locked-until-trained).

### [219. Caryll Runecraft](entries/skill.md#219-caryll-runecraft) — 4.2 Elite (Bloodborne), 4.2
Entire mechanics outsourced to an external Bloodborne wiki URL (link-rot
risk). "Only three runes active" but acquisition undefined (all at once?
choose 3? random 3?).
**Ask:** inline a closed rune list + effects? How are runes acquired/swapped?

### [272. Army Breaker](entries/skill.md#272-army-breaker) — 4.1 Elite (Strike it Rich), 4.1
"Empower the attacks called Dawn" — Dawn never defined. "Control joints to
elongate arms" — range? supernatural stretch? permanent?
**Ask:** define Dawn (forms, trigger, cost) and arm-elongation limits.

### [273. Kaiwan Style](entries/skill.md#273-kaiwan-style) — 5.2 Epic (Kengan Ashura), 5.2
"Motionless to predict opponents' next moves" undefined (stance? passive
precog? active?). No cost/scope.
**Ask:** what is Motionless mechanically, and how does it differ from 279
Martial Foresight / 289 Pre-Initiative?

### [274. The Niko Style](entries/skill.md#274-the-niko-style) — 6.1 Legendary (Kengan Ashura), 6.1 + [275. Possessing Spirit](entries/skill.md#275-possessing-spirit) — 3.1 Rare (Kengan Ashura), 3.1
274 bundles 4 Katas + Demonsbane + Possessing Spirit + Fallen Demon in one
pull, while 275 is a separate entry for the same Advance. Free combo?
Fallen Demon vs Gear mechanics undefined numerically.
**Ask:** should Niko exclude Possessing Spirit/Fallen Demon (require separate
pull), or explicitly include? What do Gears 1–3 grant numerically?

---

## Majors (ambiguous or require outside fandom knowledge)

- **[7. Intermediate Programming](entries/skill.md#7-intermediate-programming) — 2.1 Uncommon (Generic)** — "all / any programming language you
  encounter": mundane only, or auto-adapts to alien/magical/future code?
- **[19. Polar Channel Flow - Cellular Overdrive](entries/skill.md#19-polar-channel-flow-cellular-overdrive) — 3.5 Rare (Generic)** — `Pugilist` undefined;
  "augment all stats to their limits" + "permanent damage" need
  multiplier/duration/cost and what permanent damage does.
- **[21. Spear of Untraceable Trajectory](entries/skill.md#21-spear-of-untraceable-trajectory) — 6.7 Legendary (Everyone Else is a Returnee)** — simultaneous-hit count scales
  with mastery but no numbers; requires Fate (Tsubame Gaeshi) knowledge.
- **[65. Novice Item Construction](entries/skill.md#65-novice-item-construction) — 2.1 Uncommon (Generic)** — "proper item" is undefined gacha jargon.
  Define tier limit vs self-heating plate / air-purifying mask examples.
- **[74. Literacy](entries/skill.md#74-literacy) — 2.2 Uncommon (Generic)** — auto-learns "all common and mundane languages of the
  world you are in"? Auto-updates per world? Magical/dead/secret included?
- **102/103/126/127/149 (+228)** — "low-level Tinker ability / Tinkertech /
  generalized Tinker Tech" requires Worm knowledge, undefined in-repo.
  Define buildable tech per tier without the external reference.
- **[124. Master Shooting](entries/skill.md#124-master-shooting) — 5.3 Epic (Generic)** — "You have … or you could with enough training":
  have it now or train to it? Baseline hit/dodge? Orion/Arash needs context.
- **128/129/130. Master Biology/Physics/Chemistry** — "need study to digest"
  contradicts instant-grant; invention (hybrids, anti-gravity, serum) needs
  time/cost/lab and guarantee-vs-knowledge ruling.
- **[132. Master Blacksmithing](entries/skill.md#132-master-blacksmithing) — 5.9 Epic (Generic)** — "Noble Phantasm-level … Muramasa" needs
  Fate knowledge; give in-repo stat meaning.
- **[134. Master Blade Weapon Mastery](entries/skill.md#134-master-blade-weapon-mastery) — 5.9 Epic (Generic)** — "cusp of the sword saint realm"
  undefined; what does cusp grant vs withhold?
- **[147. Grandmaster Hand-to-Hand Combat](entries/skill.md#147-grandmaster-hand-to-hand-combat) — 6.5 Legendary (Generic)** — soul-shatter + magic-dispel:
  literal always-on or high-damage flavor? What resists?
- **[150. Grandmaster Biology](entries/skill.md#150-grandmaster-biology) — 7.0 Mythical (Generic)** — "simple scan … genetic blueprint": what
  action (visual/touch/sense), range, time, consent?
- **167/168/169. Principles of Life/Law/Matter** — "creator's knowledge …
  mortal vessel … instinctive comprehension" gives no day-1 usable actions
  and overlaps Divine Biology/Medicine/Mechanics. Give 1–2 concrete examples
  per Principle for fresh vs late-game holders.
- **180–184. Interfacing chain** — non-standard term covering lockpick +
  pickpocket + machines/terminals. Physical thievery, digital hacking, or
  both? Overlaps Mechanics/Programming/297 Hacking. Rename to
  Thievery/Sleight or define as hybrid?
- **185–189. Savoir Faire chain** — French term vague (dance/parkour/
  acrobatics). Master "dance around bullets" as baseline human: supernatural
  or hyperbole? Nerf to aim-dodge?
- **[194. Master Stealth](entries/skill.md#194-master-stealth) — 5.8 Epic (Generic)** — "greatest of the Hassassin": Fate Hassans,
  historical Hashashin, or typo? Keep/rename to generic master assassins?
- **195–198. Jack/Queen/King/Ace of All Trades** — scope is exactly 5 trades
  (Blacksmithing, Medicine, Mechanics, Cooking, Interfacing): why these?
  Rank names are non-standard and gendered; mapping to Novice/Intermediate/
  Adept/Expert is fuzzy. Confirm scope and consider neutral tiered names.
- **224/225. Master/Divine Conceptualization** — "converse with old ones …
  infant Outer God": type change? sanity immunity? reality-bending limits?
  Define mechanical benefits vs flavor.
- **[230. Prana Bindu](entries/skill.md#230-prana-bindu) — 4.8 Elite (Dune)** — end-state sentence lacks verb/object ("…your nerves
  and bioelectrical signals" do what?). Define intended control (pain/poison
  resist? puppetry?).
- **[250. Gooning](entries/skill.md#250-gooning) — 2.3 Uncommon (Generic)** — file means "low-rank thug", but modern slang reads as
  NSFW edging trance. "Brooklyn accent at will": power or joke? Consider
  rename to Thug/Goon and drop accent line.
- **[253. Aura Farming](entries/skill.md#253-aura-farming) — 2.1 Uncommon (Generic)** — meme term ("farm aura", caped ledge poses). Real
  Charisma buff, situational Performance bonus, or pure flavor?
- **[254. Fishman Karate](entries/skill.md#254-fishman-karate) — 5.0 Epic (One Piece)** — "start as white belt": belt system undefined;
  starting power? Needs ambient water? Does airborne-moisture transmission
  work on land?
- **291/292/293. Ryu's / Akuma's / The Shotokan** — three overlapping
  entries; Kyoi vs Satsui no Hado unlock rules undefined; demonization (real
  transformation vs flavor? corruption meter vs overuse risk?); 293's "may
  awaken one Hado": player choice or random?
- **[295. Dapping](entries/skill.md#295-dapping) — 0.2 Trash (Generic)** — joke skill? Any bonus beyond social flavor?
- **[297. Hacking](entries/skill.md#297-hacking) — 2.5 Uncommon (Generic) vs 102/126/148/165 Programming chain** — single-line
  network breach massively overlaps Expert→Divine Programming. Merge or
  define Hacking's narrow applied scope?
- **[299. Judging](entries/skill.md#299-judging) — 2.7 Uncommon (Generic)** — supernatural alignment-detect or mundane insight?
  Infallible? Countered by Acting/Stealth?
- **[301. Tax Evasion](entries/skill.md#301-tax-evasion) — 1.0 Common (Generic)** — supernatural bureaucracy-blindness or mundane
  accounting? Auto-updates to each world's tax laws (cf. 249 Litigation)?

## Minors (jokes/tone/wording)

- **37/71/95/119/143 Charisma family** — "people of note" undefined (named
  NPCs? high-stat? plot-relevant?). Stacking across tiers?
- **[45. Suppression](entries/skill.md#45-suppression) — 4.0 Elite (Generic)** — "does not seem out of place with foliage" simile;
  what detection (mundane/magical/godlike) does it defeat?
- **62/63/64 Novice weapon trio** — joke tone ("stabby end", "large stick",
  "long stick") vs technical Adept+ entries. Keep jokes or set clear
  baseline?
- **[85. Adept Teaching](entries/skill.md#85-adept-teaching) — 3.2 Rare (Generic)** — "(Call yourself GTO …)" needs Great Teacher
  Onizuka knowledge; mechanical title or removable joke?
- **[98. Grooming](entries/skill.md#98-grooming) — 1.9 Common (Generic)** — "NOT THAT KIND": which kind is excluded? Reword to
  explicit hygiene/beauty scope.
- **111/116/117** — hyperbole ("brown pants", "grandpa", "outrace a
  motorcycle on a tricycle"): literal feats or flavor? Testable benchmarks?
- **135/141** — "shatter castle walls with a tree branch",
  "rollerblades to star-sized spacecraft": literal ceiling or exaggeration?
- **[229. Salt Distillation](entries/skill.md#229-salt-distillation) — 0.1 Trash (Generic)** — joke-narrow ("or tears") 0.1; merge into
  Survival/Cooking?
- **[247. Begging](entries/skill.md#247-begging) — 2.4 Uncommon (Generic)** — supernatural compulsion or mundane pity? Stack with
  Persuasion? Adjudication?
- **[249. Litigation](entries/skill.md#249-litigation) — 2.5 Uncommon (Generic)** — auto-grants local law on world-hop or starting-world
  only?
- **[296. Boggart's Boiling Brilliance](entries/skill.md#296-boggarts-boiling-brilliance) — 1.4 Common (Elden Ring)** — Elden Ring knowledge needed;
  Cooking sub-skill for crustaceans or special buffs from magical
  ingredients?
- **[298. Crying](entries/skill.md#298-crying) — 0.5 Trash (Generic)** — synergy with 247 Begging / Acting, or standalone flavor?
- **[302. Kidnapping](entries/skill.md#302-kidnapping) — 1.8 Common (Generic)** — "planning + practiced moves": keep abstract
  (planning + stealth bonus vs unaware) without methodology detail.

---

## Recommended human actions (minimal set)

1. Define: Recoilless (43), Motionless (273), Dawn (272), white belt (254),
   proper item (65), eligible familiars + people-taming limits (31 family),
   scan (150), vessel (170), Hado/demonization (291–293).
2. Resolve duplicates/overlaps: Niko (274) vs Possessing Spirit (275);
   Hacking (297) vs Programming chain; Interfacing (180–184) vs
   Mechanics/Programming/Hacking; Tax Evasion (301) vs Litigation (249).
3. Rule on absolute-scope skills: Programming languages (7), Literacy (74),
   Taming people (31 family), Pressure Points "and more" (32), Judging (299).
4. Decide tone: keep or cut GTO (85), NOT THAT KIND (98), Brooklyn accent
   (250), tricycle/grandpa/brown-pants hyperbole (111/116/117), foliage (45).
5. Confirm or rename: Gooning (250, NSFW collision), Hassassin (194),
   Savoir Faire (185–189, keep French or rename), Jack/Queen/King/Ace
   (195–198, neutral tier names?).
6. External references: replace or gloss Tinker (102/103/126/127/149/228),
   Noble Phantasm/Muramasa (132), Tsubame Gaeshi (21), Kankara (170),
   Boggart (296); inline Caryll runes (219) instead of bare URL.
