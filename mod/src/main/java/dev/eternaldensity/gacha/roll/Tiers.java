package dev.eternaldensity.gacha.roll;

import java.util.Map;

/**
 * Display bands over the continuous rarity scale (PROJECT_PLAN.md section 4.1).
 * Display-only: rarity is never quantised.
 */
public final class Tiers {
    private static final Map.Entry<String, Double>[] BOUNDS = new Map.Entry[] {
            Map.entry("Trash", 1.0),
            Map.entry("Common", 2.0),
            Map.entry("Uncommon", 3.0),
            Map.entry("Rare", 4.0),
            Map.entry("Elite", 5.0),
            Map.entry("Epic", 6.0),
            Map.entry("Legendary", 7.0),
            Map.entry("Mythical", 8.0),
            Map.entry("Divine", 9.0),
    };

    private Tiers() {
    }

    public static String forRarity(double rarity) {
        for (Map.Entry<String, Double> bound : BOUNDS) {
            if (rarity < bound.getValue()) {
                return bound.getKey();
            }
        }
        return "Transcendent";
    }
}
