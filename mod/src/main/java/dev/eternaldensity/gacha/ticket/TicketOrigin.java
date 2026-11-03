package dev.eternaldensity.gacha.ticket;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * Cosmetic provenance for chest tickets (PROJECT_PLAN.md section 6.3), e.g.
 * {@code {"type": "chest", "id": "minecraft:chests/simple_dungeon"}}.
 */
public record TicketOrigin(String type, String id) {
    public static final Codec<TicketOrigin> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.fieldOf("type").forGetter(TicketOrigin::type),
            Codec.STRING.fieldOf("id").forGetter(TicketOrigin::id)
    ).apply(instance, TicketOrigin::new));
}
