# trait scaling report (linked)

Auto-generated from `trait-scaling-report.md`. Entry names link to [entries/trait.md](entries/trait.md). Responses: [responses.tsv](responses.tsv).

---

# Trait Gacha — Stage 6: Power Scaling Report

Branch: `cleanup/skill-gacha` · File: `gachafiles/trait.txt` (633 entries)
Scale: Trash 0.1–0.9 · Common 1.0–1.9 · Uncommon 2.0–2.9 · Rare 3.0–3.9 ·
Elite 4.0–4.9 · Epic 5.0–5.9 · Legendary 6.0–6.9 · Mythical 7.0–7.9 ·
Divine 8.0–8.9 · Transcendent 9.0–9.9.

Distribution: Trash 15 · Common 42 · Uncommon 124 · Rare 137 · Elite 137 ·
Epic 73 · Legendary 40 · Mythical 45 · Divine 12 · Transcendent 8.
Note the heavy top: EIGHT Transcendents (skill file has one). Only the top
1-3 should be true capstones; the rest should come down (see §2).

Method: per-line ladder gaps (healthy 0.8–1.2, flag <0.4 or >1.4),
same-niche cross-checks, absolute-effects-vs-price, and bundle/stack
interactions. No numbers changed here — all fixes are owner proposals.

---

## 1. Exemplary lines (reference standards)

- **Resistances** Fire 3.5 / Water 3.2 / Air 3.6 / Lightning 3.5 / Earth 3.0 /
  Ice 3.3 (+ Light 3.7 / Dark 3.5): tight 3.0–3.7 band.
- **Lich line** 3.8/4.7/5.8/6.7/7.9 and **Angel line** 3.4/4.2/5.4/6.5/7.2:
  clean ladders. **Lungs** 2.4/3.5/4.6 likewise.
- **Luck ladder** 2.7/3.7/4.7/5.7: perfect 1.0 steps.
- **Naruto bloodlines** Hyuga 5.1 (Elite unlock) / Uchiha 6.0 (Epic) /
  Uzumaki 6.4 (Epic+) / Senju 6.8 (Legendary): unlock-rank-indexed pricing.
- **Psyker system**: specialists 4.2–5.3 by utility, generalist (1 of 5)
  5.5, Greater (all 5) 6.5. Flexibility premium done right.
- **Death ladder**: 1hr overtime 4.5 < one revival 4.9 < soul-stuck 6.4 <
  nine lives 7.0 < continuous 7.6.
- **Income ladder**: Allowance 2.2 (capped daily) < Health Insurance 2.4
  (bounded by injury) < Money Glitch 6.9 (unbounded). Bounded-vs-unbounded
  priced correctly.
- **TCB-like dependency**: engine traits outrank style traits (cf. skill
  report); Water-breathing-style gating via training time consistently
  discounted (Saiyan 7.0, Dragonlord 7.0 need decades/ages of training).

## 2. Inversions and mispricings (fix first)

| # | Entry | Now | Problem | Suggest |
|---|-------|-----|---------|---------|
| [376](entries/trait.md#376-spiral) | Spiral | 9.9 | Highest price in file for one mechanics-free sentence ("find a way") | Rewrite with limits or → ~7.x |
| [132](entries/trait.md#132-golden-shot) | Golden Shot (forces pregnancy "even if barren") | 1.3 | Strongest absolute/price ratio violation in file (also clarity blocker) | Consensual-only rework, no forced pregnancy |
| [30](entries/trait.md#30-mmmm-milk) | Mmmm Milk (milk replenishes Energy, amount undefined) | 3.8 | Liquid energy economy break if literal (buy milk → full bar) | Define amount (e.g. glass = 10%?) or → 5.5+ |
| [393](entries/trait.md#393-no-weakness) | No Weakness (zero ANY negative resistance) | 6.0 | Negates the racial weaknesses that define 5–7 cost races (sunlight-lethal, Holy vulnerability) | 7.5+, or exclude racial weaknesses |
| 580/150 | Literary Devouring (eat → memorize all) 1.2 vs Scholar (read 50/day) 2.1 | — | Faster method cheaper than slower one | Devouring → 2.4+ or Scholar → 1.8 |
| 105/348/349/350/351 | Iron Skeleton 3.5 / Mithril 4.1 / Adamantium Skeleton 5.7 / Vibranium 6.6 / Bonding (REAL adamantium + poison) 4.2 | — | Real-but-poisonous 1.5 cheaper than fake-but-safe; Mithril→Adamantium jumps 1.6 | Bonding → 4.9, or 349 → 5.2 |
| 422–428 | Demon line 2.1/3.7/4.9/5.7/6.8/7.7/7.7 | — | Imp→Demon 1.6; Daemon→Kaiser 0.0 (same price, different entries) | Demon → 3.5; Kaiser → 8.0 (primordial capstone) |
| [166](entries/trait.md#166-sky-monarch) | Sky Monarch | 7.9 | +0.5–0.8 above identical-template siblings (Sea 7.1 … Earth 7.4) | → 7.3 |
| [617](entries/trait.md#617-waterbending) | Waterbending | 6.2 | +1.1 over Fire 5.1; Air 5.8 also floats above Earth 5.2 | Water → 5.9, Air → 5.6 (or justify bloodbend/heal premium) |
| [483](entries/trait.md#483-royal-beastkin) | Royal Beastkin | 6.1 | Noble→Royal gap 0.4 (line: 3.5/4.4/5.7/6.1) | Royal → 6.4 |
| 99/584/585 | Iron Fist 2.1 → Mythril Fist 4.8 | — | +2.7 skips Rare entirely | Add Steel Fist ~3.4, or Iron → 2.8 |
| 204/205/206 | Bloodless 2.2 / Bloodbank 2.7 / Eternal Bleed 4.2 | — | Gaps 0.5/1.5 (clan-feeding utility jump) | 205 → 3.0 |
| 169/176 | Relentless 4.3 vs Boundless 4.4 | — | Near-identical effects 0.1 apart | Merge (keep one ~4.3) or split stamina-vs-energy |
| [575](entries/trait.md#575-dullahans-deception) | Dullahan's Deception (decapitation immunity) | 2.2 | Kill-vector immunity at Uncommon floor | → 3.2+ or require head proximity |
| [572](entries/trait.md#572-path-of-dragon) | Path of Dragon (can BECOME 6.8 Everlasting Dragon) | 4.2 | Legendary transformation at Elite price (flesh costs vague) | Quantify flesh or → 5.5+ |
| [104](entries/trait.md#104-mysterious-stranger) | Mysterious Stranger (pays out a GOLD ticket when obsolete) | 3.3 | Profitable trait: negative net cost | Remove refund (clarity) |
| 601/160/627 | Shoulder to Shoulder 4.0 + slot traits | — | Weakest-slot buff interacts unruled with +1/+2 slots | Define interaction with 160/627 |
| 160/627 | High Capacity 5.3 (+1 slot) / Super 6.0 (+2) | — | Static price for scaling benefit (slot ≈ best ability owned) | Cap slottable rank or scale price |

## 3. Underpriced absolutes / offense-defense parity

- Mind/social offense is systematically cheaper than mental defense: auras
  and compulsions at 2.2–3.8 (charms, Peerless, Harem, Dealmaker) vs Mind
  Palace immunity at 6.2. Either price controllers up or bring a
  mid-tier (4.5–5.5) resist into the file.
- 275+ similar: 286/287/302/306, 320/321, 254/230 compulsions (see clarity
  blockers) — scaling follows the consent ruling: resisted-bonus versions
  keep current prices; literal versions go up 1.5–2.5.
- 575 (above), 109/112/131/132/300 (above), 247/141/259/260-261 (above).
- 546 (enslavement engine 5.1), 254 (serve-compulsion 5.6): compulsions of
  sapients should start at 6.5+ even rewritten, or stay cheap only as
  willing-only reaction bonuses.

## 4. Uneven lines and gaps

- **Stat-boost doubles**: Enhanced line (182–185 at 2.4–2.8, "in
  proportion") vs Surging line (436–444 at 3.4–4.8, "greatly"). Two
  overlapping ladders with no stack rule → double-dip exploit. Give both
  numeric multipliers (e.g. +20% / +50%) and ban stacking.
- **Fist/skeleton**: see §2 (add Steel Fist; Bonding inversion).
- **Demon/Angel/Beastkin/Avian/Lycan**: see §2 + clean ones noted in §1.
- **Blood**: see §2.
- **Stamina quad**: see §2 (merge 169/176).
- **Kitsune time-evolution**: 536 (1-tail, grows to 9 with age/energy) vs
  537 Kyubi (9-tail) 5.7 (+1.1 for time). If 536 reaches 9 tails free,
  537 is overpriced; rule the evolution (clarity race canon).
- **Chosen 7.7 vs True Hero 5.8** (+1.9 for permanent blessings +
  Mythical-rank-up): steep "chosen" premium; fine if intentional — confirm.
- **Pendragon 5.3** (five buffs: ruling, charisma, physical, energy,
  blades) vs True Hero 5.8 (similar scope): –0.5 looks cheap. → 5.6?
- **Skeleton 2.2** (FULL sustenance removal + affinity, one vulnerability)
  vs Steel Man 4.1 (1/100th reduction, no downside): 1.9 gap needs the
  race-discount principle written down (vulnerability offsets) — or narrow
  to ~1.0 (Skeleton → 2.8).
- **Gambler 4.3**: negative-expected-value roulette (destroy/rank-down
  outcomes) at Elite. Price assumes upside-seeking; self-consistent while
  toggleable — keep, note the assumption.
- **Transcendent crowd (8)**: keep 2–3 true capstones (e.g. Absolute
  Victory, Immortality, Spiral-if-rewritten); demote the rest to high
  Divine/Mythical: Broken Limiter → 8.5–8.8 (gated growth, cf. Kryptonian
  8.8), Beast → 8.8–9.0 (cap open-ended clause), Infinite/Absorber/
  Deathless → 8.5–9.0 with contest rules.
- **Collision clusters** (observation only): 3.5 ×22, 4.8 ×21, 3.7 ×19,
  4.2 ×19. Natural under ±0.2 pull bands; no change.

## 5. Cross-file parity (for the full-gacha pass)

- Tinker-equivalence statements (87/93/252 + skill 102/103/126/127/149)
  vs actual Tinkertech *items*: verify a Master-Mechanics build matches an
  item of the same rarity.
- Ability-slot traits (160/627/316) vs ability-file power at each rarity.
- Free-ability grants (322–325 unlocks, 471/473/555/536 bracket abilities,
  509–518 Necromancy set, 602 skill grants): link to ability.txt IDs with
  rank caps, or require GM design.
- MindImmunity (122/370) vs skill/ability mind-affecting at each rarity.

## 6. Recommended improvements (ordered)

1. Apply §2 table (Spiral, Golden Shot, Milk, No Weakness, Devouring,
   Bonding, Demon/Kaiser, Sky, Waterbending, Royal, Fist gap, Blood,
   169/176 merge, Dullahan, Path, refund, slots).
2. Consent ruling first (clarity report) — it reprices §3 as a batch.
3. Demote Transcendent crowd to 2–3 capstones with contest rules.
4. Numeric multipliers for both stat lines + stacking ban; slot-content
   caps; karma/duplication ban list (clarity).
5. Write the pricing principles into the Doc (as found working):
   (a) mundane professions cheap (1–2), power expensive;
   (b) vulnerability/gate/training-time discounts (Saiyan, Dragonlord,
   Skeleton, Akuma-style risk);
   (c) bundle discounts scale (All Trades, Psyker Greater, Niko-style);
   (d) flexibility premium (generalist Psyker +0.7 over fixed);
   (e) unlock-indexed pricing (Naruto line);
   (f) bounded-vs-unbounded income (Allowance → Glitch).
6. Cross-file parity checks during ability/item/familiar passes.
