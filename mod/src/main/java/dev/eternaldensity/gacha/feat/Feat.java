package dev.eternaldensity.gacha.feat;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

import java.util.Optional;

/**
 * One feat (PROJECT_PLAN.md sections 4.3 and 6.9). Ids are derived from the
 * file path: {@code data/<namespace>/feat/<path>.json} is
 * {@code <namespace>:<path>}.
 *
 * <p>Implementation order A: advancement-driven feats now. Stat, kill, collect
 * and visit triggers are declared in the schema but not yet implemented.
 */
public record Feat(
        String name,
        String description,
        Trigger trigger,
        String tier,
        Tickets tickets,
        Optional<String> line,
        boolean powerRelative) {

    public static final Codec<Feat> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.fieldOf("name").forGetter(Feat::name),
            Codec.STRING.fieldOf("description").forGetter(Feat::description),
            Trigger.CODEC.fieldOf("trigger").forGetter(Feat::trigger),
            Codec.STRING.fieldOf("tier").forGetter(Feat::tier),
            Tickets.CODEC.fieldOf("tickets").forGetter(Feat::tickets),
            Codec.STRING.optionalFieldOf("line").forGetter(Feat::line),
            Codec.BOOL.optionalFieldOf("power_relative", false).forGetter(Feat::powerRelative)
    ).apply(instance, Feat::new));

    public record Tickets(int count, String category, int advantage) {
        public static final Codec<Tickets> CODEC = RecordCodecBuilder.create(instance -> instance.group(
                Codec.INT.fieldOf("count").forGetter(Tickets::count),
                Codec.STRING.fieldOf("category").forGetter(Tickets::category),
                Codec.INT.optionalFieldOf("advantage", 1).forGetter(Tickets::advantage)
        ).apply(instance, Tickets::new));
    }

    public record Trigger(String type, String advancement, String stat, double threshold,
                          String entity, int count, String item, String location) {
        public static final Codec<Trigger> CODEC = RecordCodecBuilder.create(instance -> instance.group(
                Codec.STRING.fieldOf("type").forGetter(Trigger::type),
                Codec.STRING.optionalFieldOf("advancement", "").forGetter(Trigger::advancement),
                Codec.STRING.optionalFieldOf("stat", "").forGetter(Trigger::stat),
                Codec.DOUBLE.optionalFieldOf("threshold", 0.0).forGetter(Trigger::threshold),
                Codec.STRING.optionalFieldOf("entity", "").forGetter(Trigger::entity),
                Codec.INT.optionalFieldOf("count", 1).forGetter(Trigger::count),
                Codec.STRING.optionalFieldOf("item", "").forGetter(Trigger::item),
                Codec.STRING.optionalFieldOf("location", "").forGetter(Trigger::location)
        ).apply(instance, Trigger::new));
    }
}
