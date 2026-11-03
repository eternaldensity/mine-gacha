package dev.eternaldensity.gacha.ticket;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.eternaldensity.gacha.entry.Entry;

import java.util.List;

/**
 * Optional ticket filter (PROJECT_PLAN.md section 6.3). Tag filters are
 * implemented; {@code source_mod} and {@code pool} are declared in the schema
 * for later and are not yet consumed by the engine.
 */
public record TicketFilter(List<String> tagsAll, List<String> tagsAny) {
    public static final Codec<TicketFilter> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.listOf().optionalFieldOf("tags_all", List.of()).forGetter(TicketFilter::tagsAll),
            Codec.STRING.listOf().optionalFieldOf("tags_any", List.of()).forGetter(TicketFilter::tagsAny)
    ).apply(instance, TicketFilter::new));

    public static final TicketFilter EMPTY = new TicketFilter(List.of(), List.of());

    public boolean matches(Entry entry) {
        if (!tagsAll.isEmpty() && !entry.tags().containsAll(tagsAll)) {
            return false;
        }
        return tagsAny.isEmpty() || entry.tags().stream().anyMatch(tagsAny::contains);
    }
}
