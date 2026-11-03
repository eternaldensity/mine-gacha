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

- **8. Amaterasu**: "burn anything", unextinguishable by normal means. Rank
  that resists? What CAN extinguish it?
- **20. Profaned Flames**: "ignore all fire resistance" at 6.2 — bypass
  Epic+ immunities, Logias, Divine warding? Counter?
- **247/248. Reaper's Scythe / Death's Instrument**: full durability
  ignore, regen+resurrection block, soul wounds. What rank resists? Is
  rez-block permanent?
- **267. Black Hole**: trainable REAL black holes — size/lifetime cap, or
  virtual-only?
- **320. Genesis**: country-erasing, no Unholy survives + allies healed.
  Who counts Unholy? Rank/resistance? Collateral/consent?
- **390. Reality Slash / 392. Stillness / 456. Vector Manipulation /
  458. Lockdown / 462. Absolute Gateway / 465. Adamantine Skin / 481. Full
  Counter / 482-484 (Destruction/Incarnate, Ice Man, Phoenix Force) /
  485. Stinger / 490. Immune / 511. Unlock / 534. Penetrate / 544. Gravity /
  564. Overhaul / 579-581 True Magics / 650. Dust Release / 654. Rinnegan /
  715. Dark Matter / 718. Calamity / 731. Divinity Fire / 794. Schrodinger /
  809. Save & Load (+801/808) / 878-881 (Invulnerable, Immortal,
  Exclusion, All Fiction) / 885. Level Up / 912-916 time/space set /
  918. Wrath / 921-923 (Magic Dominion, Void, Nihil) / 947. D4C /
  958. Rule Breaker / 938. Baker / 1047. Choosing Fate / 1079. Hulk Out /
  1112. Defence (V) / 1199. Kill Process / 1211. Necromancy / 1212. Death
  Authority / 1230. Vanish / 1298. Tower Down / 1321. Recovery /
  1324. Greater Guard / 1350. Grand Dissolution**: each is absolute,
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

- **69 (+68/66/67) Hydrokinesis / 193. Ferrokinesis (blood) / 162. Stun
  Shock (open puppetry) / 239. Shadow Puppeteer / 303. Confessor's Light
  (forced truth) / 238. Sethan (forced de-aging) / 338. Bone Manipulation
  (others' skeletons) / 424. Metallica (no resist clause — add 378/379's
  strength rule) / 429. Fabric Manipulation (forced restraint/undress) /
  435. Enchantment Eyes / 438. Death Perception (absolute no-save kill —
  what is immune?) / 452. Absolute Accuracy / 493. Authority of Lust
  (mass affection + financial ruin) / 497. Arousal (NSFW, vision-range) /
  511. Unlock / 534. Penetrate / 541. Condemnation (karma judge?) /
  556. Date Scouter (non-consensual kink reveal) / 561-562 (mimic/drain —
  theft vs copy? storage? consent?) / 570. Devil Control / 572. Contractual
  Recreation (receipt power — who defines? bans?) / 576. Phantom Touch
  (sexual-touch vector) / 577. Collaring (PC slavery — defeat threshold?
  release? ban?) / 601. Tantric Healing (sex-gated healing scaling) /
  630. Angel Style (nudity-gated power) / 641. Phasing (phase-inside
  instant-kill?) / 663-664 (ripen/forced activation — living targets?
  unconscious = consent?) / 674-675 + 669 (sentient/AI/bio builds —
  sapience, loyalty, bioweapon, clone-rights limits?) / 700. Toggle
  (off-state for abilities?) / 707. Soft & Wet (steal sight/strength/life?
  limits?) / 747/745 (dream view + influence — OOC consent? sleeping PCs
  immune by default?) / 753. Healing Kiss / 775. Path to Love (target-side
  effects without consent?) / 841. Capture Token (PC capture consent? max
  hold? release?) / 893. Idle Transfiguration (permanent reshaping? heal?) /
  925. Karmic Enforcement ("any action" incl. slavery/murder — whitelist,
  ban PC forcing) / 934. Spirit Dragon (possession + post-death survival —
  OOC consent? death still removes?) / 952. Tiamat's Gift (PC transform
  consent? permanent?) / 977. Klyntar (forced takeover? power-share cap?) /
  986. Man in the Mirror (indefinite prison — detention cap? exit rights?) /
  993. Tentacled Creature (explicit sexual ability — adult-only + consent +
  non-consensual ban?) / 994. Madness Wavelength (town-wide madness — resist
  + opt-out or single-target?) / 997. Soul Bet (PC soul wagering — ban or
  OOC consent + release?) / 1001/1021/1023 (see-through senses, vision
  hijack, 2.5km live tracking — private-area blocks + hijack/tracking
  consent?) / 1033. Erotics Tinker (adult-only + aphrodisiac-consent ban?) /
  1037. Genderswap / 1140-1142 (Knighting/Burden/Greed's Deal — permanent
  mind-control slavery, murder market — ban on PCs? thresholds? release?
  price table?) / 1170. Edict (NSFW/self-harm edicts? range/duration/max
  targets?) / 1171. Phantom Sensation (remote sexual assault/torture —
  consent? remove sexual uses?) / 1173. Geass Command (free absolute control
  — comparison/eye-contact/duration rules?) / 1250. Lactation / 1261. Eros
  Hide / 1122. Taimanin (NSFW tech) / 1160. Fumofication (immunity +
  pain-farming engine) / 1069. Greedy Healing (people as fuel — forbid +
  price curve?) / 369. Tentacles ("molest" listed — reword non-sexual or
  NSFW+consent) / 345. Ghoul hunger (forced cannibalism PvP — NPC sources?
  opt-out?) / 312. Resuscitation (soul/player consent? max extension?) /
  369/497/556/576/577/601/630/630-cluster (above) / 810. Xavier (mind-molding
  at tens of km — consent/resist/energy or ban?) / 814-815 (suicidal urges,
  body hijack — ban self-harm commands + OOC consent + duration/body rules?) /
  833. Nice Guy (unopposed PvP — allow on PCs? threshold? consent?)**:
  rule as a batch: resistible, consensual-only defaults for PCs, explicit
  opt-outs, no sexual/non-consensual uses without OOC consent; ban list for
  the worst (slavery markets, soul wagering, remote sexual assault).

## Majors — undefined scaling / system terms / outside knowledge

- Numbers missing: 11. Conflagration (area/energy?), 110. Absolute Zero
  (radius/charge/resist?), 95. Frozen Heart (mental-resist strength?),
  137. Heavy Wind (density-vs-durability formula?), 139/140 (O2 volume,
  hold-breath rules, friendly fire?), 142 (pressure delta/radius/lethality?),
  191. Earthquake (radius/magnitude?), 231. View Earth (stealth counter?
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
  caps vs fixed effects?), 265. Cursecraft (power cap? duration? cleanse?
  allow/ban lists?), 283. Shadow Monarch (count/rank caps? PC corpses?
  immortality breaks?), 336. Immunity System (references non-existent
  `Immutable` — typo for itself? condition?), 111. Divinity (concrete kit
  or cut?), 297. Regression (who defines "intended"? forced
  de-transformation consent?), 307. Blessing of Arms (stage map + skill
  list?), 385. Apport (who prices "worth"? exploit guard?), 399/400
  (radius? allies? resist? energy curve?), 404. King Crimson (skip
  duration/cost/trackability?), 411/656 (conversion rate + hard cap?),
  415. Resurrection (who values sacrifice? unwilling revival allowed?),
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
