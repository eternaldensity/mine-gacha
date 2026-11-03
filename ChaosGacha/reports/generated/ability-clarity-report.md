# ability clarity report (linked)

Auto-generated from `ability-clarity-report.md`. Entry names link to [entries/ability.md](entries/ability.md). Responses: [responses.tsv](responses.tsv).

---

# Ability Gacha — Stage 3: Clarity / Confusion Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/ability.txt` (1383 entries;
numbers 842/843/873 skipped file-wide)
Scope: entries needing human input. Typos (stage 1) and conciseness (stage 2)
are done and not repeated here.

Severity: **Blocker** = cannot implement/balance, consent violation,
infinite exploit, or game-breaking. **Major** = undefined scaling/mechanics
or heavy outside-knowledge dependence. **Minor** = small vagueness, typos
needing owner canon decisions.

Systemic gaps (define once, fix everywhere): energy-cost formulas ("more
energy = more" with no numbers); rank/tier vocabulary ("Epic rank",
"Legendary", "below Elite" — no ladder in file); range defaults (sensory
range? line of sight? touch? — varies per entry); resistance mechanics (who
resists, by power gap or willpower?); familiar/summon tiers ("Uncommon
Familiar power" — no stat table); slot/slotless economy (ability slots,
slotless grants, slot-bypass pricing).

---

## Blockers — absolutes without counters

- **[8. Amaterasu](entries/ability.md#8-amaterasu) — 6.8 Legendary (Naruto)**: "burn anything", unextinguishable by normal means. Rank
  that resists? What CAN extinguish it?
- **[20. Profaned Flames](entries/ability.md#20-profaned-flames) — 6.2 Legendary (Calamity Mod)**: "ignore all fire resistance" at 6.2 — bypass
  Epic+ immunities, Logias, Divine warding? Counter?
- **247/248. Reaper's Scythe / Death's Instrument**: full durability
  ignore, regen+resurrection block, soul wounds. What rank resists? Is
  rez-block permanent?
- **[267. Black Hole](entries/ability.md#267-black-hole) — 5.0 Epic (Generic)**: trainable REAL black holes — size/lifetime cap, or
  virtual-only?
- **[320. Genesis](entries/ability.md#320-genesis) — 7.7 Mythical (Epic Battle Fantasy)**: country-erasing, no Unholy survives + allies healed.
  Who counts Unholy? Rank/resistance? Collateral/consent?
- **[390. Reality Slash](entries/ability.md#390-reality-slash) — 5.7 Epic (Generic) / [392. Stillness](entries/ability.md#392-stillness) — 6.8 Legendary (Re:Zero) / [456. Vector Manipulation](entries/ability.md#456-vector-manipulation) — 8.8 Divine (Toaru) /
  [458. Lockdown](entries/ability.md#458-lockdown) — 6.0 Legendary (Generic) / [462. Absolute Gateway](entries/ability.md#462-absolute-gateway) — 6.0 Legendary (Generic) / [465. Adamantine Skin](entries/ability.md#465-adamantine-skin) — 6.8 Legendary (Generic) / 481. Full
  Counter / 482-484 (Destruction/Incarnate, Ice Man, Phoenix Force) /
  [485. Stinger](entries/ability.md#485-stinger) — 8.2 Divine (Generic) / [490. Immune](entries/ability.md#490-immune) — 5.5 Epic (Generic) / [511. Unlock](entries/ability.md#511-unlock) — 6.0 Legendary (Generic) / [534. Penetrate](entries/ability.md#534-penetrate) — 4.6 Elite (Generic) / 544. Gravity /
  [564. Overhaul](entries/ability.md#564-overhaul) — 7.6 Mythical (MHA) / 579-581 True Magics / [650. Dust Release](entries/ability.md#650-dust-release) — 7.2 Mythical (Naruto) / [654. Rinnegan](entries/ability.md#654-rinnegan) — 8.8 Divine (Naruto) /
  [715. Dark Matter](entries/ability.md#715-dark-matter) — 9.5 Transcendent (Toaru) / 718. Calamity / [731. Divinity Fire](entries/ability.md#731-divinity-fire) — 8.5 Divine (Generic) / [794. Schrodinger](entries/ability.md#794-schrodinger) — 7.9 Mythical (Hellsing) /
  [809. Save & Load](entries/ability.md#809-save-load) — 9.0 Transcendent (Generic) (+801/808) / 878-881 (Invulnerable, Immortal,
  Exclusion, All Fiction) / 885. Level Up / 912-916 time/space set /
  [918. Wrath](entries/ability.md#918-wrath) — 8.8 Divine (Generic) / 921-923 (Magic Dominion, Void, Nihil) / [947. D4C](entries/ability.md#947-d4c) — 8.8 Divine (JoJo) /
  [958. Rule Breaker](entries/ability.md#958-rule-breaker) — 6.4 Legendary (Generic) / 938. Baker / [1047. Choosing Fate](entries/ability.md#1047-choosing-fate) — 8.5 Divine (Generic) / [1079. Hulk Out](entries/ability.md#1079-hulk-out) — 7.6 Mythical (Marvel) /
  1112. Defence (V) / [1199. Kill Process](entries/ability.md#1199-kill-process) — 7.0 Mythical (Generic) / 1211. Necromancy / 1212. Death
  Authority / [1230. Vanish](entries/ability.md#1230-vanish) — 6.0 Legendary (Generic) / [1298. Tower Down](entries/ability.md#1298-tower-down) — 5.7 Epic (Generic) / 1321. Recovery /
  [1324. Greater Guard](entries/ability.md#1324-greater-guard) — 5.4 Epic (Generic) / [1350. Grand Dissolution](entries/ability.md#1350-grand-dissolution) — 7.2 Mythical (Generic)**: each is absolute,
  infinite-scaling, or rule-breaking with no cap, cost curve, resist, or
  counter defined. Per-entry questions in the full audits below; the
  global fix is caps + costs + resist mechanics + explicit ban lists.
  Highlights: 879 Immortal gains stats PER DEATH (infinite farm — remove
  scaling); 885 absorbs 10% of anything killed (sapient-farm ban? cap?);
  1324 damage-transfer math is inverted/lethal (rewrite, forbid lethal
  transfer); 809/801/808 save/load need scope (self checkpoint vs world
  rewind? death/soul-erasure? memories of others?); 947 death-transfers
  the whole gacha to a random self (ban transfer, travel-only?); 654
  six-paths bundle needs per-path limits + soul/revive consent; 581
  creates "anything creatable" + 580 infinite energy (inline bounds or
  cut); 715 takes ANY property incl. life/clones/powers (whitelist +
  ban power-granting); 718 auto-kills pursuers merely for awareness
  (awareness definition? resist? auto-death allowed?).

## Blockers — consent / mind-body control / moderation

- **69 (+68/66/67) Hydrokinesis / [193. Ferrokinesis](entries/ability.md#193-ferrokinesis) — 4.9 Elite (Generic) (blood) / 162. Stun
  Shock (open puppetry) / [239. Shadow Puppeteer](entries/ability.md#239-shadow-puppeteer) — 3.7 Rare (Naruto) / [303. Confessor's Light](entries/ability.md#303-confessors-light) — 3.3 Rare (Generic)
  (forced truth) / [238. Sethan](entries/ability.md#238-sethan) — 4.6 Elite (JoJo) (forced de-aging) / [338. Bone Manipulation](entries/ability.md#338-bone-manipulation) — 4.8 Elite (Worm)
  (others' skeletons) / [424. Metallica](entries/ability.md#424-metallica) — 4.8 Elite (Generic) (no resist clause — add 378/379's
  strength rule) / [429. Fabric Manipulation](entries/ability.md#429-fabric-manipulation) — 4.2 Elite (MHA) (forced restraint/undress) /
  435. Enchantment Eyes / 438. Death Perception (absolute no-save kill —
  what is immune?) / [452. Absolute Accuracy](entries/ability.md#452-absolute-accuracy) — 5.2 Epic (Generic) / [493. Authority of Lust](entries/ability.md#493-authority-of-lust) — 6.6 Legendary (Generic)
  (mass affection + financial ruin) / [497. Arousal](entries/ability.md#497-arousal) — 3.6 Rare (Generic) (NSFW, vision-range) /
  [511. Unlock](entries/ability.md#511-unlock) — 6.0 Legendary (Generic) / [534. Penetrate](entries/ability.md#534-penetrate) — 4.6 Elite (Generic) / [541. Condemnation](entries/ability.md#541-condemnation) — 7.1 Mythical (Generic) (karma judge?) /
  [556. Date Scouter](entries/ability.md#556-date-scouter) — 2.8 Uncommon (Generic) (non-consensual kink reveal) / 561-562 (mimic/drain —
  theft vs copy? storage? consent?) / [570. Devil Control](entries/ability.md#570-devil-control) — 8.3 Divine (Generic) / 572. Contractual
  Recreation (receipt power — who defines? bans?) / [576. Phantom Touch](entries/ability.md#576-phantom-touch) — 2.3 Uncommon (Generic)
  (sexual-touch vector) / [577. Collaring](entries/ability.md#577-collaring) — 3.8 Rare (Generic) (PC slavery — defeat threshold?
  release? ban?) / [601. Tantric Healing](entries/ability.md#601-tantric-healing) — 3.3 Rare (Generic) (sex-gated healing scaling) /
  [630. Angel Style](entries/ability.md#630-angel-style) — 2.7 Uncommon (Generic) (nudity-gated power) / [641. Phasing](entries/ability.md#641-phasing) — 6.1 Legendary (Marvel) (phase-inside
  instant-kill?) / 663-664 (ripen/forced activation — living targets?
  unconscious = consent?) / 674-675 + 669 (sentient/AI/bio builds —
  sapience, loyalty, bioweapon, clone-rights limits?) / [700. Toggle](entries/ability.md#700-toggle) — 2.5 Uncommon (Generic)
  (off-state for abilities?) / [707. Soft & Wet](entries/ability.md#707-soft-wet) — 5.8 Epic (JoJo) (steal sight/strength/life?
  limits?) / 747/745 (dream view + influence — OOC consent? sleeping PCs
  immune by default?) / [753. Healing Kiss](entries/ability.md#753-healing-kiss) — 4.2 Elite (MHA) / [775. Path to Love](entries/ability.md#775-path-to-love) — 5.3 Epic (Generic) (target-side
  effects without consent?) / [841. Capture Token](entries/ability.md#841-capture-token) — 4.5 Elite (Generic) (PC capture consent? max
  hold? release?) / [893. Idle Transfiguration](entries/ability.md#893-idle-transfiguration) — 7.3 Mythical (Jujutsu Kaisen) (permanent reshaping? heal?) /
  [925. Karmic Enforcement](entries/ability.md#925-karmic-enforcement) — 6.6 Legendary (Generic) ("any action" incl. slavery/murder — whitelist,
  ban PC forcing) / 934. Spirit Dragon (possession + post-death survival —
  OOC consent? death still removes?) / [952. Tiamat's Gift](entries/ability.md#952-tiamats-gift) — 6.8 Legendary (Generic) (PC transform
  consent? permanent?) / 977. Klyntar (forced takeover? power-share cap?) /
  [986. Man in the Mirror](entries/ability.md#986-man-in-the-mirror) — 4.8 Elite (JoJo) (indefinite prison — detention cap? exit rights?) /
  [993. Tentacled Creature](entries/ability.md#993-tentacled-creature) — 3.3 Rare (Generic) (explicit sexual ability — adult-only + consent +
  non-consensual ban?) / [994. Madness Wavelength](entries/ability.md#994-madness-wavelength) — 5.2 Epic (Generic) (town-wide madness — resist
  + opt-out or single-target?) / [997. Soul Bet](entries/ability.md#997-soul-bet) — 3.0 Rare (JoJo) (PC soul wagering — ban or
  OOC consent + release?) / 1001/1021/1023 (see-through senses, vision
  hijack, 2.5km live tracking — private-area blocks + hijack/tracking
  consent?) / 1033. Erotics Tinker (adult-only + aphrodisiac-consent ban?) /
  [1037. Genderswap](entries/ability.md#1037-genderswap) — 1.8 Common (Generic) / 1140-1142 (Knighting/Burden/Greed's Deal — permanent
  mind-control slavery, murder market — ban on PCs? thresholds? release?
  price table?) / [1170. Edict](entries/ability.md#1170-edict) — 4.8 Elite (Generic) (NSFW/self-harm edicts? range/duration/max
  targets?) / [1171. Phantom Sensation](entries/ability.md#1171-phantom-sensation) — 3.3 Rare (Generic) (remote sexual assault/torture —
  consent? remove sexual uses?) / 1173. Geass Command (free absolute control
  — comparison/eye-contact/duration rules?) / 1250. Lactation / 1261. Eros
  Hide / 1122. Taimanin (NSFW tech) / [1160. Fumofication](entries/ability.md#1160-fumofication) — 5.2 Epic (Generic) (immunity +
  pain-farming engine) / [1069. Greedy Healing](entries/ability.md#1069-greedy-healing) — 5.5 Epic (Generic) (people as fuel — forbid +
  price curve?) / [369. Tentacles](entries/ability.md#369-tentacles) — 3.4 Rare (Generic) ("molest" listed — reword non-sexual or
  NSFW+consent) / 345. Ghoul hunger (forced cannibalism PvP — NPC sources?
  opt-out?) / [312. Resuscitation](entries/ability.md#312-resuscitation) — 3.7 Rare (Generic) (soul/player consent? max extension?) /
  369/497/556/576/577/601/630/630-cluster (above) / [810. Xavier](entries/ability.md#810-xavier) — 7.7 Mythical (Generic) (mind-molding
  at tens of km — consent/resist/energy or ban?) / 814-815 (suicidal urges,
  body hijack — ban self-harm commands + OOC consent + duration/body rules?) /
  [833. Nice Guy](entries/ability.md#833-nice-guy) — 7.2 Mythical (Worm) (unopposed PvP — allow on PCs? threshold? consent?)**:
  rule as a batch: resistible, consensual-only defaults for PCs, explicit
  opt-outs, no sexual/non-consensual uses without OOC consent; ban list for
  the worst (slavery markets, soul wagering, remote sexual assault).

## Majors — undefined scaling / system terms / outside knowledge

- Numbers missing: [11. Conflagration](entries/ability.md#11-conflagration) — 4.8 Elite (Generic) (area/energy?), [110. Absolute Zero](entries/ability.md#110-absolute-zero) — 7.0 Mythical (Generic)
  (radius/charge/resist?), [95. Frozen Heart](entries/ability.md#95-frozen-heart) — 4.8 Elite (Generic) (mental-resist strength?),
  [137. Heavy Wind](entries/ability.md#137-heavy-wind) — 5.5 Epic (Generic) (density-vs-durability formula?), 139/140 (O2 volume,
  hold-breath rules, friendly fire?), 142 (pressure delta/radius/lethality?),
  [191. Earthquake](entries/ability.md#191-earthquake) — 2.8 Uncommon (Generic) (radius/magnitude?), [231. View Earth](entries/ability.md#231-view-earth) — 3.2 Rare (Generic) (stealth counter?
  sustain cost?), 313. Swords of Light (duration? rank? passives?),
  296-307 blessings (mimic lists? stacking with 293-295? stage mapping?),
  208-211 elementals + 211 golems + 1186-1189 demons + 1176-1184 elementals +
  1193-1197 angels (tier stat tables? permanent costs/caps? sacrifice
  consent — 1186-1189 tier→sacrifice text mismatched copy-paste, fix
  mapping!), 222-224 (crystal/gem allow-lists? diamond/mana gems? market
  + energy-storage caps? "vessels" for what?), Logias (24/50/104/105/234/
  277/324 — standard package? intangibility? counters?), Toaru Level 5s
  (18/77/141/161/200/456 — in-file baselines, not lore homework),
  draconic spears (166-168 — what counts? null scope?), weightless throws
  (179/187 — size/damage caps?), 186/206/251 (ranges? break DCs? volume?
  living beings?), 242-253 DxD line + 248-253 Longinus marbles (scaling-gear
  caps vs fixed effects?), [265. Cursecraft](entries/ability.md#265-cursecraft) — 4.8 Elite (Generic) (power cap? duration? cleanse?
  allow/ban lists?), [283. Shadow Monarch](entries/ability.md#283-shadow-monarch) — 6.7 Legendary (Solo Leveling) (count/rank caps? PC corpses?
  immortality breaks?), [336. Immunity System](entries/ability.md#336-immunity-system) — 3.9 Rare (Generic) (references non-existent
  `Immutable` — typo for itself? condition?), 111. Divinity (concrete kit
  or cut?), 297. Regression (who defines "intended"? forced
  de-transformation consent?), [307. Blessing of Arms](entries/ability.md#307-blessing-of-arms) — 3.6 Rare (Generic) (stage map + skill
  list?), [385. Apport](entries/ability.md#385-apport) — 3.1 Rare (Generic) (who prices "worth"? exploit guard?), 399/400
  (radius? allies? resist? energy curve?), [404. King Crimson](entries/ability.md#404-king-crimson) — 6.6 Legendary (JoJo) (skip
  duration/cost/trackability?), 411/656 (conversion rate + hard cap?),
  [415. Resurrection](entries/ability.md#415-resurrection) — 5.8 Epic (DnD) (who values sacrifice? unwilling revival allowed?),
  450/525/527 (hard caps or planet-scale allowed?), 452 (any defense ever?),
  458 (what breaks it? duration/size?), 462 (any barrier holds? cost/size?),
  465 (what at equal/higher power harms?), 481 (exclusions? timing
  window/cost?), 482-484 (yield caps? revive limits? enumerated powers?),
  490 (counter?), 501 (enumerated capped powers or cut?), 519/634
  (inline mechanics, no link-only rules!), 519 Nine Eyes URL + 634 Idle
  Death Gamble URL (inline or remove), 534 (what resists Penetrate
  itself?), 541 (karma judge? PvP adjudication?), 544 (mass/range/cost
  caps or planet+black-holes allowed?), 556 (consent/redaction?),
  561-562 (storage? duration? theft-vs-copy? resist?), 567 (cost? literal
  "unbreakable"?), 570 (proof mechanic? duration? release? PC ban?),
  572 (receipt power judge? bans?), 573 (trajectory control strength?),
  574 (accuracy scaling?), 576-578 (above), 579-581 (bounded or cut?),
  601 (consent?), 615/616/620 (stacking caps? anti-farm?), 625/626
  (banned orders/words? adjudication? scope?), 630 (above), 641 (above),
  650 (resists? cost/volume/size?), 654 (above), 663/664 (above),
  674-690 universe-Tinkers (bounded in-file tech lists or cut?),
  694. Dreadon (universe-range sniper + black-hole bombs — allowed at
  all? arc-resource gating? hard caps?), 700/753/747/775/775-cluster
  (above), 727-730 (above), 731 (god-domain absolute or capped? override
  other fire users?), 732-734 Devil Fruits ("still water" defined?
  sheets linked? hidden-in-food? partial submersion?), 735-736 (above),
  748/776 (blind spots? cooldown/cost? banned questions? combat auto-win?
  guidelines-only (776)?), 757-785 Teigu line (global compatibility roll?
  sell/gift if incompatible? per-entry ranges/costs/cooldowns? 762
  griefing save? 763 corpse cap/consent/permanence? 768 judge/death/A-N?
  771/774/781/784 discriminatory filters → neutral worthiness? 777 =
  Census duplicate; 786 = effect text or remove?), 759 (sigil limit/cost/
  cooldown?), 762 (above), 763 (above), 768 (above), 777 (surveillance
  Qs), 786 (above), 782 (ban internal-biology manipulation? external
  only?), 829 (cooldown/cost/kill-condition or ban?), 832 (radius?
  duration? cost? null Gacha itself? Epic/Legendary?), 833 (above),
  841 (above), 893 (above), 925 (above), 934 (above), 939 (nukes allowed?
  mundane + WMD ban?), 939 Militia contradiction (nuclear launcher vs
  Elite cap — ban WMDs), 952 (above), 959 (two cooldowns in one text —
  which is correct? temp-ticket runner?), 977 (above), 986 (above),
  993-994/997 (above), 1001/1021/1023 (above), 1033 (above), 1036 (limits?
  size/function/revert?), 1047 (improbability cap? backlash? energy?
  paradox?), 1048 (familiar definition? stacking? action cost?),
  1056 (barrier HP/counter? energy rate? portal size/range?), 1069
  (above), 1071 (whitelist? ban multiversal/time?), 1079 (above), 1092
  (rename, reorder I-V, FTL rules?), 1097 (scan mechanics? consent?
  grantable list? time/resource?), 1112 (above), 1122 (above), 1125
  (typo? boost %? entrance rules?), 1135 (GM spawn rules? persists?
  anti-farm?), 1140-1142 (above), 1160 (above), 1164 (outputs? tier cap?
  stack?), 1165 (22-effect table? scaling? roller? fumble?), 1170-1171
  (above), 1173 (above), 1176-1184 (above), 1186-1189 (above), 1190 (why
  Roentgenium? radius/mass cap?), 1192 (pull table? slot lock? scaling?),
  1199 (tech tiers? save? cooldown? oblivion defined?), 1211 (number/power
  caps by energy? retention?), 1212 (above), 1230 (above), 1252 (who
  decides event? range? cooldown? forced combat?), 1274 (minimums? action?
  rounds?), 1275 (cap? range? self-slot?), 1291 (player-judged? resist?),
  1292 (whitelist? GM veto? Tinker/unique handling?), 1298 (scaling?
  duration? allies? system/telepathy?), 1321 (rank defined? exclusions?
  Gacha Curses? permanent losses?), 1324 (above), 1335 (range? target
  count? both-slotted cost?), 1350 (above), 1360 (inline stats or link?
  gag counter? shout requirement?).
- Outside knowledge to inline: Toaru Level-5s, JoJo (404/414/658/947/
  973/983/986/795-798...), DxD Longinus/Sacred Gears, Naruto (517-518/
  635-637/654/714/1002-1003...), Fate (438/438-cluster/579-581/787-789/
  995...), Worm (161/196/243/255/338/363-364/386/396/437/540/651-652/716/
  758/776/812-814/833-834/871/939/1071...), Warhammer (1188 tech?
  Psyker?), MTG/DnD colors, Marvel (483-484/639/641/757/977...), DC
  (39...), Solo Leveling (283...), Katekyo (1278-1285), Ben 10
  (1309-1318, 904?), Infamous conduits (1242-1248), Tinker universes
  (686-690 + 694 + 696 + 699 + 1072/1075...), Skyrim Thu'um, Elden Ring
  sorceries, Monster Hunter (1368-1374 — pain/revert? asexual-repro
  excluded (1372) — confirm rest?), Tokyo Ghoul (340-347 — hunger
  consent above), One Piece (Logias/Haki/Hormones...), Black Clover
  grimoires, Jujutsu Kaisen (techniques + 634/1034 + 1379 Ten Shadows —
  ritual/death-fuse rules?), Chainsaw Man (960-961 + 1362-1367 Branches —
  vitality costs?), Deadman Wonderland (above), Medaka (880-881),
  Re:Zero (392/1133-1135...), Hellsing (501/794...), Soul Eater,bus...
  Rule: every fandom entry needs in-file numbers; links are hints, not
  rules (519/634 worst offenders).
- Tinker system terms (669/674-675 + 1036-1150 mass Tinker block +
  1056/1069/1071/1092/1097/1122/1125/1164...): specializations need
  power tiers, build times/costs, sapience/loyalty/bioweapon/clone-rights
  limits; "design and build" repeated verbatim across dozens — templates
  need per-tier differentiators; 1091→1092 skips III (later 1159) —
  rename/reorder I-V; FTL/starships need rules; multiversal/time builds
  need bans.

## Minors / typos needing canon answers

- 1125 indescrutable→? (indestructible? indescribable? — owner picks).
- 1291 Trial grayscale-by-OWN-morality (player-judged? spoofable?).
- 1190 Roentgenium (why this element?).
- 1036 Sex Manipulation ("absurd" undefined).
- 1335 Diction (hearing = range? target count?).
- 1252 Adventure Line ("interesting" subjective; lethal-murderer example).
- 1335/1165/1252 (above).
- 1190/1291/1036/1252/1335 (above).

## Recommended human actions (minimal set)

1. Consent pass (whole §2 batch): resistible, consensual-only PC
   defaults, opt-outs, no sexual/non-consensual uses without OOC consent;
   ban list (slavery markets, soul wagering, remote sexual assault,
   forced pregnancy-adjacent, collaring PCs).
2. Absolutes pass (whole §1 batch): caps + costs + resists + counters +
   explicit immunities list; delete infinite farms (879/885/411/616/620).
3. Numbers pass: ranges, radii, durations, cooldowns, costs, counts, and
   the missing global tables (rank ladder, familiar tiers, slot economy,
   energy formulas).
4. Inline pass: every URL-dependent entry gets self-contained mechanics;
   Tinker block gets tiers/times/costs/rights limits; universe-as-ability
   entries get bounded lists or cuts.
5. Structural: fix 1186-1189 tier→sacrifice copy-paste; rename/reorder
   Tinker Vehicles I-V; define Immutable/Immutable-System reference
   (336); confirm Logia standard package; confirm Toaru baselines.
