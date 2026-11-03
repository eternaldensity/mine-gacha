package dev.eternaldensity.gacha.ticket;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The twelve ticket windows from PROJECT_PLAN.md section 4.2, mirrored from
 * {@code chaoslab/simulate.py} so the debug command, the loot injection and the
 * sweep report speak the same vocabulary. Presets exist only at grant time:
 * the granted ticket stores the numbers.
 */
public final class TicketPresets {
    public static final Map<String, RollSpec> BY_NAME;

    private TicketPresets() {
    }

    private static void put(Map<String, RollSpec> target, String name, double min, double avg, double max, boolean flat) {
        target.put(name, new RollSpec(min, avg, max, flat));
    }

    static {
        Map<String, RollSpec> presets = new LinkedHashMap<>();
        put(presets, "trash", 0.1, 0.5, 1.5, false);
        put(presets, "bronze", 0.1, 1.3, 3.3, false);
        put(presets, "silver", 0.5, 2.3, 4.3, false);
        put(presets, "gold", 1.5, 3.3, 5.3, false);
        put(presets, "aluminium", 1.0, 4.0, 6.0, false);
        put(presets, "platinum", 2.5, 4.3, 6.3, false);
        put(presets, "diamond", 3.5, 5.3, 7.3, false);
        put(presets, "legendary", 4.5, 6.3, 8.3, false);
        put(presets, "mythical", 5.5, 7.3, 9.3, false);
        put(presets, "wild", 1.0, 5.0, 10.0, true);
        put(presets, "divine", 6.5, 8.3, 10.0, false);
        put(presets, "transcendent", 7.5, 9.3, 10.0, false);
        BY_NAME = Collections.unmodifiableMap(presets);
    }
}
