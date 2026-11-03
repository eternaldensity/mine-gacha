package dev.eternaldensity.gacha.entry;

import dev.eternaldensity.gacha.roll.RollEngine;
import dev.eternaldensity.gacha.ticket.TicketFilter;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceLocation;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * Builds the drawable pool for one ticket category.
 *
 * <p>Entries whose adapter this build cannot apply are excluded, so the machine
 * never consumes a ticket for a reward it cannot grant. The exclusion is
 * deliberate and grows away as adapters are implemented.
 */
public final class EntryPool {
    public static final Set<String> SUPPORTED_ADAPTERS = Set.of("gacha:item", "gacha:attribute", "gacha:effect", "gacha:origin");

    public record PoolEntry(ResourceLocation id, Entry entry) {
    }

    private EntryPool() {
    }

    public static List<RollEngine.Candidate<PoolEntry>> candidates(
            Registry<Entry> registry, String category, Optional<TicketFilter> filter) {
        List<RollEngine.Candidate<PoolEntry>> pool = new ArrayList<>();
        for (var registryEntry : registry.entrySet()) {
            Entry entry = registryEntry.getValue();
            if (!entry.kind().equals(category)) {
                continue;
            }
            if (!SUPPORTED_ADAPTERS.contains(adapterType(entry))) {
                continue;
            }
            if ("gacha:origin".equals(adapterType(entry)) && !OriginAdapter.available()) {
                continue;
            }
            if (filter.isPresent() && !filter.get().matches(entry)) {
                continue;
            }
            pool.add(new RollEngine.Candidate<>(entry.rarity(), new PoolEntry(registryEntry.getKey().location(), entry)));
        }
        pool.sort(Comparator.comparingDouble(RollEngine.Candidate::rarity));
        return pool;
    }

    public static String adapterType(Entry entry) {
        return entry.adapter().map(adapter -> adapter.get("type").asString("")).orElse("");
    }
}
