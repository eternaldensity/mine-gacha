# Item Gacha — Stage 3: Clarity / Confusion Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/item.txt` (850 entries)
Scope: entries needing human input. Typos (stage 1) and conciseness (stage 2)
are done and not repeated here.

Structural notes (fixed in stage 1, confirm): duplicate ID blocks resolved
— second 670–689 block is now 829–849, Costume Wardrobe fills 666, and the
headerless Erdtree Seed entry is now 850. Open: "Hota" vs "HOTA" (file uses
Hota ~30×; one rewrite batch briefly used HOTA and was reverted — confirm
which is canonical).

Severity: **Blocker** = cannot implement/balance, infinite exploit, consent
violation, or game-breaking. **Major** = undefined mechanics/quantities or
heavy outside-knowledge dependence. **Minor** = moderation/tone/small
vagueness.

Doc reference: `Cooldown` = delay between active uses (reducible);
`Restock Timer` = delay until another copy can be taken. Many entries misuse
one for the other — the single biggest systemic fix below.

---

## Blockers

### Absolutes without rank caps
- **10. Master Key (5.2)**: "any lock, barrier, ward" — Divine/conceptual/
  living vaults included? Rank cap?
- **20. Enuma Elish (8.7)**: zero-cost planet-texture beam, spammable?
  Cost/charge/cooldown for full power?
- **36. The Assembly (5.2)**: disassemble ANY item to snowflake size +
  reassemble with blueprint — Divine artifacts? Living familiars? Infinite
  duplication via restock items? Blueprint source, energy cost, rank limit?
- **39. Black Barrel (7.4)**: mortality imposed on "anything it hits, even
  absolute immortals" — resist/rank save? Graze = permanent? Vs
  Transcendent immortality?
- **78. Dimension Lost (8.2)**: "inviolable" barriers/portals — what beats
  it? Size/duration/inhabitants/energy?
- **85. Returner's Clock (4.9)**: 3 unrefillable day-resets — memories/
  items/rolls retained? Paradox? Undo death / re-farm feats?
- **242/243** (Mehrunes Razor, Skeleton Key): "only limit is the user" —
  define mechanically (energy? rank? skill?) or confirm Transcendent-tier
  at 7–8.
- **251. Telos Karma (8.5)**: causality wish, larger = more energy — rank
  cap? Paradox formula? Death-of-gods / ticket-gain affirmations?
- **274. Armageddon Blade (5.4)**: world-ending hellfire rain at Epic —
  area/rank cap/friendly-fire/cost?
- **282. Cloak of Silence (3.6)**: sub-Epic magic immunity (including own
  healing?) at Rare — intended permanent? Threshold correct?
- **296. Orb of Vulnerability (5.2)**: bypass immunities incl. Divine/
  Transcendent? Cost/toggle? If absolute, why 5.2?
- **464. Stopwatch (8.5)**: stops universe time — duration/cost/cooldown/
  resistance/range? Or ban?
- **477. Mansion of the Boundary (8.8)**: Outer-One-proof + multiverse
  doors — confirm as absolute safehouse + travel? Cost/cooldown/trace?
- **485/486** (Ultimate Nullifier 9.8, Infinity Gauntlet 9.9): universe/
  timeline destruction "as long as they can handle it" — handling
  undefined. Ban, single-use nerf, or wield check (rank/stat/death)?
- **488. Shooting Star (7.3)**: 3× Wish of Mythical-or-below — adjudicator?
  Recharge or permanent 3? Ban list (time-stop, resurrection, slots)?
- **715. Ascalon (9.6)**: cleave realms/reality/spacetime, cut energy
  itself, drain stabbed powers — rank cap? Energy cost? Portal cooldown?
  Split into separate abilities?
- **849. The City (9.6)**: Dyson megastructure, millions of impossibly
  advanced techs, absolute command — breaks tech scarcity. Whitelist or
  lore-library downgrade? Portal size/cooldown?
- **800. Flandre Fumo (5.4)**: bypass ALL immunities/resistances except
  durability — no rank limit? Divine/plot wards? Cap (e.g. Epic max)?

### Gacha-meta / ticket manipulation
- **27. Dragon Ball (2.3)** vs **731. Dragon Balls (6.4)**: how are the
  other 6 obtained — re-roll only? 1 pull = 1 tracked ball? Does <6.9
  ability bypass Ability Tickets/slots? "Within his power" judge? Same
  pool for both entries?
- **52. ITOPOD (3.0)**: "death is permanent" vs resurrection items? A/N
  normative? Who GMs floors? One-shot despite Ticket pattern?
- **212. Modified Compound V (3.4)**: free random Gold ability, even in
  storage — permanent? Slot? Who rolls? Farmable (no restock listed)?
- **232–234. Ability/Trait/Skill Tickets (5.x)**: Item rolling free
  Platinum Ability rolls? Why Epic-rated for ~4.3-avg Platinum? One-shot
  or reusable? Chaining bans?
- **576. Familiar Card (4.8)**: steal another player's familiar? Range/
  resistance/consent? Single-use?
- **607. Reroll Chip (3.8)** vs **793. Alice Fumo (4.8)**: eligible types?
  Timing window? Reroll-itself / mutual loops? Original to pool or void?
- **794. Node Fumo (5.0)**: 5× faster cooldowns/restocks while asleep in
  building — sleep definition (nap/KO/coma)? Stack Nodes? Building = camp?
- **795. Mabel Fumo (5.7)**: free Gold Ticket/168h — infinite Gold economy?
  Auto-claim? Unclaimed cap?
- **796. Mary Sue Fumo (5.3)**: change any ticket type by wall-slam —
  any→any? Blacklist? Fail state?
- **839. Cursed Ticket (2.0)**: spins undefined Roulette — table? Odds?
  Refusable? Link target?
- **810. Yuugi Fumo (3.3)**: slotless passive [Strength (Rare)] — slot
  bypass precedent? Stolen/dropped mid-fight?

### Slavery / mind-control / non-consensual
- **109. Collar of Obedience (2.7)**: "cannot be placed on resisters" =
  save-less slavery if placeable. Resist check (rank/will/ability)?
  Consent / PG flag / rank cap?
- **114. Monstergirls and You (3.3)**: any monster → attractive female,
  target sees as natural — rank limit (dragons/gods/familiars)?
  Permanent? Reversible? Consent? Why no (Nsfw)?
- **397–401. Heart Tickets**: "not mind control but retroactive reality
  bending" love-potions with no side effects — permanent? Stackable?
  Resist? Love-potion date pattern — PG flag / PC ban / rank cap?
- **443. Door to Jail (5.8)**: ability-stripping jail — capture method/
  resistance? Max occupants? Sentence length? Warden if traded? Escape?
- **473. Cupid's Arrow (6.8)**: forced love, Legendary+ resist — duration?
  Cure? PvP consent policy?
- **549. Favour Cheque (4.8)**: compelled favour short of
  strongly-against-morals — morals judge? Target aware? Rank/resistance?
- **553. Forgiveness Ticket (5.0)**: forced forgiveness except murder —
  emotion or social edge? Duration? Neutrality tracking? Boss/deity
  immunity?
- **580/581. Summon contracts (5.5)**: equal-rank Demon/Angel without slot
  for 3 equal sacrifices — rank appraisal? Sacrifices lost? Refund
  meaning? Familiar-exclusion mismatch (580 excludes Skills; 581 excludes
  Skills+Familiars)? Slot bypass intended?
- **598. Icon of Greed (5.8)**: possess-at-any-cost compulsion incl.
  kin-killing — range/duration/resistance? Wealth-extraction cap? PvP ban?
- **630. Job Application (1.5)**: guaranteed hire any job — scope cap
  (king/god)? Employer mind-control? Employment duration?
- **693. Thalasin (2.0)**: emotion pills incl. Lust, restock/24h, count
  undefined — dose count? Duration? Resistance? Lust use = assault
  vector — self-only or ban Lust?
- **738. Slave Waiver (4.6)**: read-and-sign rights-relinquishment — rules
  text missing! Intelligence threshold? Coerced reading allowed?
  Revocation/resale? Ban or rework?
- **739. Phone A Friend (2.4)**: call anyone pictured+named, they receive
  copy — unwilling/unaware/gods/dead? Refuse/trace? Cross-dimension?
- **741. Census (6.8)**: name/address/bio of every named sapient in 1M km
  — live updates? Wards/aliases resistance? Interdimensional? Intended
  manhunt tool?
- **743/744. Hell/Heaven Taxes (2.6/2.8)**: 100 souls / 100 Holy doses per
  336h — infinite soul economy? Sentience/suffering? Summon stats/
  duration? Trade/fuel loops (with 596/723)?
- **837. Monster Fucker Permit (4.2)**: non-consensual transformation +
  intelligence uplift, sexual purpose — ban or rework? Reversibility?
  Sapient consent? "Monster" scope (sapient races)?
- **704. Can of Whoopass (3.0)**: summons 6 Gold Familiars to beat opener
  to death — suicide on self-open? Stats/control? Forced PvP kill
  allowed? Dimension-escape?

### Wishes / infinite power / economies
- **513. Holy Grail (6.8)**: mana-source OR sub-Legendary wishes, 720h
  restock — wish consumes cycle? Mana quantity numbers?
- **599. Heal Juice (6.0)**: "heals anything except death", full dose —
  rank cap (plot curses? divine corruption)? Trait-removal vs consumable?
- **601. Pocket Universe (6.1)**: replica universe, 5cm–50m gate, at 0.0 —
  time flow? Entry for others? Export mining/farming at scale?
- **677. Bucket of Milk (3.8)**: 1L dispels ALL unnatural afflictions, no
  rank cap — cap? Strips wanted buffs? "Become part of drinker" defined?
- **703. Trumpet (7.7)**: permanent free angel army incl. 4 Seraphim —
  intended? Numbers/duration/upkeep/disobedience caps?
- **821. Master Sword (5.5)**: ALL-Unholy/Darkness ignore-resistance +
  infinite Holy-growth — bypass cap (e.g. Legendary)? Growth table?
  Worthiness mechanic?
- **823. Mirror Shield (5.1)**: reflect ALL Light/Magic off mirror, no cap
  — rank cap? Facing/size limits? Retained power?
- **596 + 743 soul loop**: Human-Transmutation soul-fuel + soul taxes =
  infinite. Ban or hard-cap (see also trait report)?
- **561/585/587/642/643/696/705/725/826/830/825 + 601/588/602** (all keys,
  Slaughterhouse, Morgue, Casino, Suite): GLOBAL key rule missing — size
  requirement? Consumed or reusable? Concurrent portals? Access control?
  Destruction/death-inside? Export limits? Then per-key: universe-size
  complex (561) weaponizable? Morgue+Nail+Garden+Erdtree infinite-corpse
  loop rates? Dust infinite mine vs 538 crate economy? Lake water export?
  Apartment power absurd size or typo? Farmland growth/golem rules? Forge
  removals/fuel/speed? Bathhouse homunculi rights + heal numbers + water
  export? Earth strip-mining? Suite duration/trap failsafe? Casino
  manifestation/revenue/workers? House of Leaves lethality/mapping/
  infohazards? (full per-key questions in audit.)
- **730. House of Leaves**, **826. Bathhouse**, **825. Earth**,
  **642. Dust Mines**, **561. Slaughterhouse**, **585+586+850 corpse
  loop** — see above; set caps.
- **811/817. Utsuho Fumos**: 50MT nuke it ignores (240h) + 100TW/s passive
  + 50MT eye beams — blast/fallout/friendly/indoor rules? Grid-breaking
  export cap? Hook interface? Beam cost/cooldown?
- **510. Deeds' Bell (2.8)**: butler does anything incl. killing, sandwich
  without ingredients, gold without gold — kill cap? Gold amount (infinite
  economy)? "Butler-capable" boundary?
- **582. Dimensional Courier (2.3)**: buys anything civilian-purchasable
  anywhere visited incl. realities, 8h, 10% — civilian defined by which
  world? Weight/legality/rarity caps? Currency conversion? Artifacts/
  souls/drugs blocked?
- **611. Instant Death Soup (2.7)**: willing+knowing+whole-pot = death
  regardless constitution/abilities — bypasses immortality/divine?
  Coerced "willing" defined? Rank cap or PvP-poison ban?
- **626. St. Trina swords**: unbreakable-by-harm sleep — rank cap?
  Duration? Wake conditions? (Coup loop.)
- **627. Ferryman's Favor (3.7)**: any one dead soul + biggest corpse part,
  sealed — rank limit? Refusal? Soul awareness/consent? Safe opening?
  Necromancy combos?
- **637. Relic of Knowledge (4.7)**: Jinn answers anything a non-divine
  being knows, per 720h — "knows" judge? Privacy (passwords, true names)?
  Future/other-world limits?
- **819. Table (0.2)** / **843. Baby Oil** / **844. Soylent Green** /
  **394. Nick O' Teen** — moderation: assault reference reword; innuendo
  effect-or-cut; cannibalism disclosure + dietary warnings; smoking-joke
  keep/reflavor/remove?
- **634. Hera's Breastmilk (4.2)**: numbers (+cap)? Squick — rename/
  reflavor or confirm adult-context OK?
- **740 + 666–676 + 589 + 589-adjacent NSFW cluster** (Ejaculatte coffee
  orgasm-drug 8h restock; fetish-gear stat slots 670–674; bodysuit 676;
  invisible-clothes nudity confusion 589): NSFW policy (allowed? age
  gate? public vs private?) — combat stats on fetish gear: rework to
  non-sexual slots or confirm? 673 sacrilege/hygiene/consent rework? 740
  non-consensual drugging = assault vector — ban or self-only + cure?

## Majors (selection; full list in audit)

- Consumable-vs-permanent + dose/stockpile rules: 7/8 injections, 21
  Pokeballs (6 or 1 per restock? sapients/gods? rank cap?), 37/328–330/
  335/338 restock-stockpiling (infinite hoard? consumed-on-use? stored
  cap?), 56–63/228/298/299 permanents (one-shot? stacking caps?
  lifespan numbers?), 99 (how drink 3/day on 1-can restock? starting
  qty?), 115 (consumed or reusable? learnable?), 149/153/156/157
  (restock qty? stockpile to child/infinite traits? age floor? slot
  interaction?), 482/479/537/567/628/663/707/846/847/848 (single vs
  reusable? quantities? formulas? suicide-farming?).
- Cooldown-vs-Restock mislabels: 49/152/356/390 tickets, 171–192 Tarot
  line (reusable-Cooldown or consumable-Restock? Star<>Sun infinite loop
  exclusion? Mystery+Star/Sun stacking? 172 temp-or-permanent rank-up?
  stackable? 177 rank cap/gods/consent? 181 forced? empty pool? reroll
  cost? 184 why no cap vs 182's Epic cap? 192 bypass tickets? cost/
  fail?), 426/440/465/539/545/556/569–572/577/622/623/654–656 (daily
  Replace vs Restock Timer wording — auto-to-inventory or claim?).
- Grant-vs-cast + surgery: 375/389/393/414–417/424/452/459/475/483/
  524–526/536/594/723/724/756/766/767/784 (auto-install on rip vs doctor?
  rejection/death? permanent vs removable? upkeep? stacking? consent for
  others? Driver drain? compatibility roll? soul-fuel murder (596)?).
- Pocket keys: see Systemic + per-key list above (585/588/602/638–645/
  696/705/725/730/825/826/830/561/601/849).
- Implants: see Systemic 2 (524–526/536/737/483/475).
- Teigu line 757–785: global compatibility roll/trial? Sell/gift if
  incompatible? Trump list final? Per-entry: 759 range/sigils/cost/
  cooldown, 762 griefing save/scope, 763 corpse cap/consent/permanence,
  768 judge/death/A/N confirm, 771 cheerful-girl + 774 killer-beauty +
  781 strong-only + 784 busty-women-preference discriminatory filters —
  rework to neutral worthiness? 777 = Census duplicate (same Qs), 786 =
  effect text or remove?
- Zanpakuto 678–689: energy source (user stamina?) scaling formula?
  Hypnosis save/duration/PvP? Corpse-puppet consent/duration? Who authors
  Asauchi abilities (owner workload)?
- Devil Fruits 732–734: "still water" defined (rain/bath/cup/sea vs
  fresh)? Sheets linked where? Hidden-in-food tricks? Partial submersion?
- Outside knowledge: 33 Tome URLs — pin revisions or snapshot lists?
  Teach-vs-cast-from-book unified rule? Energy source? Dead-link
  fallback? Teach-only vagueness (31–34, 258, 341, 418–422 + chakra
  conversion + permission grant/revoke)? Tag bug: 290 Orb wrongly
  #(Tome) — fix tag.
- Cross-cutting: 124 (Divine copies downgraded to steel? artifact
  exclusion list?), 125 (keep coitus line? PG-gate? sheet author? why
  Epic for Elite-cap?), 129 (toggle/reversible? forced-on-others consent?),
  171 (numeric cap = Fool who?), 268/269 (copy Divine/ownership? Divine
  effects?), 224 (power/ISP/cross-world wiki = infinite knowledge?
  intended?), 227 (one-shot? warships/jets? who pays? legal limits?),
  230/388 (rank threshold? radius? toggle? weaker defined?), 231
  (multiplier? reversibility? lifespan?), 280 (mirror any rank? implosion
  damage? summon-loop?), 286 (others draw? mid-day drain? Telos loops?),
  323/324/340/364/402 (spawn/store large mechs — pocket or park? fuel/
  crew? suicide-detonation allowed?).

## Minors / moderation (selection)

Moderation queue: 25 (Eromancy Tome PG?), 155 (side-effect vagueness),
220 (skimpy+drain), 238 (sacrifice-everything), 358 (opposite-gender),
437 (lotion innuendo — clarify medical/crafting use?), 441/442 (retcon
  paradox, crew rights/wages/visibility), 445 (unspecified arsenal —
  list weapons/fuel), 446 (size threshold? magic-tech? consumed? power
  formula?), 450 (liability-only usable? accidents? griefing?), 462
  (betrayal-farming PvP allowed? friend tracked how?), 463 (alignment
  judge? fall handling? graze = kill vs players?), 466 (provide +X/+Y%
  numbers or formula), 474 (AND or OR? reversible? glove safety?), 496
  (memory scope? PvP consent? ranks? suggestibility duration?), 497
  (pill mechanics? hygiene policy? clarify), 498 (respawn where/delay?
  single-use confirmed? soul-destroy/old-age?), 510 (above), 520 (stack
  cap/decay? Infinity-Stone absorption?), 561+ (above), 577 (weight/
  legality/rarity caps? currency?), 590 (break consequence or remove
  tease?), 611/612 (above), 625/626 (above), 627 (above), 634 (above),
  666–676/740/589 (above), 704 (above), 726 (regicide encouraged?
  adjudication? title loss?), 727 (prison stats? release CR? farmable?),
  729 (decency rule? values? underwear?), 841 (minor access? privacy?
  stats? per-person tracking?), 845 (artificial/overcast/night? vs
  darkvision/thermal?).

## Recommended human actions (minimal set)

1. Cooldown-vs-Restock audit: relabel every entry per Doc definitions;
   close Star<>Sun and Node loops; rule restock-stockpiling globally
   (consumed-on-use + stored cap).
2. Consent pass: slavery/mind-control/love/favor/forgiveness/summon-
   contract/greed/soul-taxes/census/slave-waiver/phone/slaughterhouse/
   morgue/NSFW-gear clusters (toggleable, resistible, consensual-only
   defaults; ban list).
3. Caps pass: all §Blockers numbers (areas, ranks, durations, costs,
   charges, quantities, cooldowns) + infinite economies (bars/purses/
   coins/ore/dust/cookies/souls/corpses/dust-mines/gold-tickets).
4. Keys/implants/tickets global rules (3 systemics) + per-key exceptions.
5. Inline the 33 URLs (snapshot spell lists) + unify teach-vs-cast;
   fix 290's tag; confirm Hota-vs-HOTA spelling.
6. Ticket-implant surgery rule; Teigu compatibility mechanic; Zanpakuto
   authorship; Devil Fruit water/ sheet definitions.
