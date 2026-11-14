# Gacha-conversion scan

Items that are currently craftable but could, like the backpacks, be removed
from crafting and granted by gacha entries instead. Derived by scanning the
pinned mod jars for recipe outputs and item registrations.

Status: **partial**; backpacks, Artifacts and Apotheosis gems are converted. The rest is proposal.

## Converted already

| Mod | Item(s) | Mechanism |
| --- | --- | --- |
| Sophisticated Backpacks | `sophisticatedbackpacks:backpack`, `copper_backpack`, `iron_backpack`, `gold_backpack`, `diamond_backpack`, `netherite_backpack` | recipes disabled by `RecipeDisabler`; six `*_bag_of_holding` entries |
| Artifacts | all 49 trinkets | 49 `artifact_*` entries; loot disabled via `config/artifacts/general.toml` (`artifactRarity=10000`, equipment/archaeology chance 0) |
| Apotheosis gems | random gem (`apotheosis:gem`) | four `gem_cache_*` entries via the reflective `gacha:gem` adapter; Apotheosis gem GLMs blanked in the pack datapack |

## Strong candidates (equipment / utility; crafting can be disabled)

### Iron's Spellbooks
Craftable power items; good gacha rewards with tier scaling.

- Spell books: `copper_spell_book`, `iron_spell_book`, `gold_spell_book`, `diamond_spell_book`, `netherite_spell_book`, `dragonskin_spell_book`, `rotten_spell_book`, `blaze_spell_book`
- Rings/amulets: `affinity_ring`, `cast_time_ring`, `concentration_amulet`, `amethyst_resonance_charm`
- Upgrade orbs: `blood_upgrade_orb`, `cooldown_upgrade_orb`, `protection_upgrade_orb`, `spell_power_upgrade_orb`, etc.

### Ars Nouveau
Craftable spell books and accessories.

- Spell books: `apprentice_spell_book`, `archmage_spell_book`, `novice_spell_book`
- Accessories: `amulet_of_mana_boost`, `amulet_of_mana_regen`, `arcanist_hood`, `arcanist_robes`, `arcanist_leggings`, `arcanist_boots`, `alchemists_crown`
- Charms: `alakarkinos_charm`, `amethyst_golem_charm`, `starbuncle_charm`, `whirlisprig_charm`, `drygmy_charm`

### Tempad
Craftable travel utility; gacha-only would make fast travel a reward rather than a craft.

- `tempad:tempad`, `chronometer`, `time_steel`, `chronon_battery`, `chronon_cell`, `chronon_generator`
- Upgrades: `new_location_upgrade`, `player_teleport_upgrade`, `knowledge_repository_upgrade`

### Apotheosis
Craftable power consumables/tools.

- `sigil_of_enhancement`, `sigil_of_rebirth`, `sigil_of_socketing`, `sigil_of_withdrawal`
- `god_fused_pearl`, `gem_fused_slate`, `gem_case`, `ender_gem_case`

### Mekanism (equipment only, not machines)
- `jetpack`, `jetpack_armored`, `free_runners`, `free_runners_armored`, `hdpe_elytra`
- `mekasuit_helmet`, `mekasuit_bodyarmor`, `mekasuit_pants`, `mekasuit_boots`
- `atomic_disassembler`

### Simply Swords
354 craftable weapons. Converting all would break the mod's progression; sample
the named/unique weapons instead (`dreadtide`, `empowered_remnant`,
`contained_remnant`, and the runic/netherite tier weapons).

## Already gacha-shaped

- **Numismatics** — coins are already used as gacha rewards.

## Not recommended

- **Machines** (Mekanism, Oritech, Electrodynamics, Energized Power, Create):
  converting them to gacha breaks the tech-tree progression the pack is built
  around. Gate them by recipe clusters instead (see `RecipeGatingEngine`).
- **Vanilla basics** (shulker boxes, anvils): too central to remove.
- **Aether accessories**: still being mapped; revisit after the Aeronautics
  stack decision.

## Implementation path

`RecipeDisabler` already supports an allowlist. To convert a group:

1. Add the recipe ids to `RecipeDisabler.DISABLED`.
2. Add `gacha:item` entries under `mod/datapack/data/gacha/gacha/entry/coverage/`
   (one per tier).
3. Run the datapack validator, GameTests, and `make check`.
