# Skill Gacha — Stage 6: Power Scaling Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/skill.txt` (302 entries)
Scale (per `Chaos Gacha Doc.md`): Trash 0.1–0.9 · Common 1.0–1.9 ·
Uncommon 2.0–2.9 · Rare 3.0–3.9 · Elite 4.0–4.9 · Epic 5.0–5.9 ·
Legendary 6.0–6.9 · Mythical 7.0–7.9 · Divine 8.0–8.9 · Transcendent 9.0–9.9.

Doc skill tiers: Basic (~1 yr) · Intermediate (~5 yrs) · Adept (~10 yrs) ·
Expert (~25 yrs) · Master (~100 yrs) · Grandmaster (beyond human) ·
Divine (god realm). Expected mapping: Novice≈Common, Intermediate≈Uncommon,
Adept≈Rare, Expert≈Elite, Master≈Epic, Grandmaster≈Legendary,
Divine≈Mythical/Divine.

Distribution: Trash 6 · Common 45 · Uncommon 54 · Rare 51 · Elite 48 ·
Epic 41 · Legendary 32 · Mythical 19 · Divine 5 · Transcendent 1.
Healthy pyramid with a thin, intentional capstone (8.0+: 170, 167, 169, 20,
168, 225). Empty bands 8.3, 8.6–8.9, 9.1–9.9 are future-design space, not bugs.
40 entries sit in Divine-preset range (6.5+), so top-end density is fine.

Method: checked every tier-progression line for gap regularity (healthy gap
0.8–1.2; flag <0.4 or >1.4), cross-checked same-niche entries (stealth vs
Suppression, general Masters vs specific-art apprentices), and absolute
effects (mind control, auto-success, immunity) against their price. No numbers
changed in this stage — all fixes below are proposals for the owner.

---

## 1. Exemplary lines (use as reference standards)

- **Cooking** 1.3/2.3/3.3/4.4/5.6/6.6/7.3 — near-perfect ~1.0 ladder.
- **Hand-to-Hand** 1.5/2.5/3.6/4.5/5.5/6.5/7.7 — clean ladder to Divine.
- **Taming** 1.1/2.1/3.1/4.1/5.1 — perfect 1.0 ladder.
- **Stealth** 1.4/2.4/3.6/4.7/5.8, **Savoir Faire** 1.8/2.7/3.8/4.9/5.9,
  **Management** 1.6/2.6/3.7/4.6/5.8, **Discipline** 1.2/2.5/3.6/4.8/6.0 —
  clean ladders.
- **TCB engine vs Breathing styles**: Novice TCB 2.4 < Water style 3.1;
  engine-mastery (6.1) outranks all styles (3.1–4.4). Correct dependency
  pricing — engine multiplies styles.
- **Spear 6.7 vs Grandmaster Polearm 6.8**, **Niko 6.1 vs Grandmaster H2H
  6.5**: specific styles sit just under the general grandmaster. Correct.

## 2. Inversions (specific > general, or cheap > expensive) — fix these first

| # | Entry | Now | Problem | Suggest |
|---|-------|-----|---------|---------|
| 1/23 | Water Stream Crushing Rock / Whirlwind Iron Cutting Fist (apprentice arts) | 5.9 / 5.6 | Apprentice in one art outranks **Master** Hand-to-Hand (125, 5.5) | 5.4 / 5.2, or document founder premium |
| 43 | Renewal Taekwondo | 6.6 | Outranks **Grandmaster** H2H (147, 6.5) | 6.4 (below Saint tier) |
| 45 | Suppression | 4.0 | Hides godlike presence — cheaper than Expert Stealth 4.7, far below Master Stealth 5.8 doing less | 5.2 |
| 280/281 | Novice / Intermediate Arms Mastery | 2.9 / 3.9 | "Basic proficiency" at Uncommon-top; Intermediate equals Adept-tier numbers | Re-ladder line to 2.0/3.0/4.0/5.0/6.0 (breadth premium kept at top) |
| 242 | Intermediate Ninjutsu | 3.8 | Front-loaded line (2.0→3.8 gap 1.8), clusters at dumped-on 3.8 | 3.0–3.2 |
| 89 | Adept Item Construction | 4.9 | Equals 4 Expert entries (107/110/120 at 4.9); emergency fire-barrier crafting at Adept | 4.3 |
| 159→137 | Grandmaster Item 6.7 vs Master Item 6.3 | 0.4 gap | Smallest Master-tier gap in file; national-treasure tier only +0.4 over castable-magic rings | Grandmaster → 7.0 |
| 225 vs 167–169 | Divine Conceptualization 9.0 (no vessel limit) vs Principles 8.1–8.5 (capped) | — | Uncapped strictly better than capped creator-knowledge; Master→Divine jump 2.8, largest in file | Keep as file capstone but add vessel limit mirroring Principles, or document as intended pinnacle |

## 3. Underpriced absolutes (literal reading too strong for price)

| # | Entry | Now | Problem | Suggest |
|---|-------|-----|---------|---------|
| 270 | Mental Image Blocking | 1.9 | Blocks ALL mind readers at Common | 2.8, or "resists weak readers" clause |
| 301 | Tax Evasion ("government sees no more than you allow") | 1.0 | Supernatural audit immunity at Common floor | Reword to mundane accounting (keep 1.0) or → 4.0+ as supernatural |
| 247 | Begging ("most people grant request") | 2.4 | Mass mind-affecting at Uncommon | Add resistible/mundane-pity clause or → 3.2 |
| 299 | Judging (morality + ill intent) | 2.7 | Undercuts Adept Communication intent-reading (3.6) by 0.9 | 3.4 + resisted-by-Acting/Stealth clause |
| 74 | Literacy (all world languages + grimoire speed-read) | 2.2 | Multi-skill bundle at Uncommon | 3.0 |
| 250 | Gooning (thug skills + novice knives/pistols/unarmed) | 2.3 | Combat bundle ≈ Novice Blade 1.9 + guns + H2H 1.5 for 2.3 | Strip weapon grants (→ 1.8) or price bundle → 2.8 |
| 297 | Hacking vs Intermediate Programming 2.1 | 2.5 | Applied breach costs more than its enabling skill but less than Adept 3.1 — inverted dependency | Gate behind Intermediate Programming, or → 3.0 standalone |

## 4. Uneven lines (gap surgery)

- **Charisma** 1.9/3.8/4.4/5.2/5.6/7.9 (no Grandmaster): Novice→Intermediate
  jumps 1.9; Master→Divine jumps 2.3. → Intermediate 3.0, add Grandmaster
  ~6.6, keep Divine 7.9.
- **Persuasion** 1.9/2.7/3.9/4.8/6.2 vs **Communication** 1.2/2.3/3.6/4.6/5.2:
  Persuasion runs ~0.7–1.0 hotter at every tier. → Novice 1.6, Master 5.9,
  and document whether a persuasion premium is intended.
- **Kama Sutra** …/4.5/6.5 (no Grandmaster/Divine): Master jumps 2.0 and
  outranks Master Persuasion/Medicine. → Master 5.9.
- **Blacksmithing** 1.7/2.0/3.4/5.2/…: Intermediate only +0.3 over Novice
  ("real blacksmith" ≈ apprentice price); Adept→Expert jumps 1.8 (crosses a
  full tier). → Intermediate 2.4, Expert 4.7.
- **Teaching**: Novice 1.8 → Adept 3.2 with **no Intermediate Teaching at
  all**. Add Intermediate ~2.5.
- **Novice Leadership** 2.4 → 1.7 (Novice→Intermediate gap is only 0.3).
- **Expert Massage** 4.0 → 4.4 (Adept→Expert gap 0.4, then Expert→Master
  1.5); note Master Massage 5.5 heals injuries at −0.2 vs Master Medicine
  5.7 — keep (flavor) or → 5.3.
- **Master Performance** 5.6 → 5.2 (Expert→Master gap 1.5).
- **Biology** Novice→Intermediate 1.5 (1.1→2.6); **Physics/Chemistry**
  Expert→Master +1.7 each; **Programming/Mechanics** Expert→Master +1.6 each.
  Pattern: the *creation threshold* (homunculi, railguns, serum, AI,
  Tinkertech) costs +1.5–2.0 everywhere — accept as systematic, but document
  it so future entries price creation consistently.
- **Intimidation** 3.3 does more (active terror) for less than Intermediate
  Charisma 3.8 (subtle aura). → Intimidation 3.5.

## 5. Bundles and overlaps (design decisions, not bugs)

- **All Trades** (Jack 3.2 / Queen 4.6 / King 5.1 / Ace 6.2): each bundles 5
  trade skills at a steep vs-separate-pulls discount that grows with tier.
  Fine as a convenience discount — document as intentional; optionally
  +0.5–1.0 at Queen/King/Ace. Also confirm the 5-trade scope and consider
  neutral tier names (see clarity report).
- **Niko Style 6.1** bundles 4 Katas + Demonsbane + Advance/Fallen Demon
  while Possessing Spirit 3.1 sells separately. → explicitly exclude Advance
  from Niko (buy 275 to combo) with a synergy note.
- **Interfacing vs Mechanics/Programming/Hacking**, **Hacking vs Programming
  chain**, **Tax Evasion vs Litigation**, **Discipline 6.0 immunity vs Mind
  Control Resistance 3.1 scaling**: define boundaries (see clarity report).
- **Tinker equivalence** (Expert/Master/Grandmaster Programming & Mechanics,
  Edna Mode): Worm-relative power statements need an in-repo definition and
  cross-file parity check against Tinkertech *items* — defer to the
  full-gacha scaling pass.

## 6. Collision clusters (observation only)

Heaviest exact-rarity densities: 3.8 ×7, 5.8 ×7, 4.6 ×6, 2.4 ×7. The gacha
pulls within ±0.2 of a rolled rarity, so clusters share pull bands. Natural
and harmless — no change.

## 7. Recommended improvements (ordered)

1. Apply §2 inversion fixes (Suppression, Arms re-ladder, WSCR/Whirlwind,
   Renewal, Adept/Grandmaster Item, Conceptualization vessel note).
2. Rule absolutes in §3 (literal vs reword) — most are one-clause fixes.
3. Smooth §4 lines; add missing Intermediate Teaching (~2.5) and Grandmaster
   Charisma (~6.6); decide Performance/Fine Arts caps (intentional or missing
   top tiers).
4. Write the three design principles into the Doc for future entries:
   (a) mundane professions are cheap (1–2), power is expensive;
   (b) the creation threshold costs +1.5–2.0;
   (c) bundles discount vs separate pulls; risk gates (corruption, damage,
   dignity, experimentation) discount.
5. Add combo/stacking rules (TCB×styles, Foresight×Pre-Initiative,
   Crying×Begging, Discipline×Mind-Resist).
6. Cross-file Tinker parity check during the item/ability/trait/familiar
   passes.
