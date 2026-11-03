package dev.eternaldensity.gacha.ticket;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * A ticket's rarity window (PROJECT_PLAN.md section 4.2).
 *
 * <p>{@code flat} marks a Wild ticket: exponent 1 and a +/-1.0 entry window
 * instead of the usual exponent 4 and +/-0.2. The roll triple is stored, never
 * a preset name, so a hoarded ticket cannot be silently rebalanced.
 */
public record RollSpec(double min, double avg, double max, boolean flat) {
    public static final Codec<RollSpec> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.DOUBLE.fieldOf("min").forGetter(RollSpec::min),
            Codec.DOUBLE.fieldOf("avg").forGetter(RollSpec::avg),
            Codec.DOUBLE.fieldOf("max").forGetter(RollSpec::max),
            Codec.BOOL.optionalFieldOf("flat", false).forGetter(RollSpec::flat)
    ).apply(instance, RollSpec::new));
}
