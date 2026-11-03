# Pack content (`pack/`)

Content that ships with the pack rather than the custom mod. Currently the
Odyssey Quests (Heracles) skeleton.

## Quests

`quests/` holds Heracles quest JSON. Per the plan (§7 row 25), Odyssey Quests
is the settled quest layer; the mod does not depend on Heracles at runtime, so
this is pack content and is installed into the dedicated server / instance:

```text
<instance>/config/heracles/quests/
```

The three starter quests form one chapter chain:

| Quest | Task | Depends on |
| --- | --- | --- |
| `first_roll` | advancement `gacha:first_roll` | — |
| `first_duplicate` | advancement `gacha:first_duplicate` | `first_roll` |
| `power_ten` | advancement `gacha:power_ten` | `first_duplicate` |

The advancements are code-granted by the mod:

- `gacha:first_roll` on the first successful ticket resolution;
- `gacha:first_duplicate` on the first duplicate;
- `gacha:power_ten` when the Power Score reaches 0.10.

This is the skeleton, not the final quest set: the plan asks for five to seven
chapters mapped onto the tier bands (first rolls, tier gates, curse management,
dimension/boss milestones, endgame). Author the rest in the Heracles in-game
editor and export the JSON into `quests/`.
