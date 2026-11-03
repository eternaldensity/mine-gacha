package dev.eternaldensity.gacha.curse;

import com.mojang.serialization.Codec;
import com.mojang.serialization.Dynamic;
import com.mojang.serialization.codecs.RecordCodecBuilder;

/**
 * One curse (PROJECT_PLAN.md section 6.8, decision D2). Ids are derived from
 * the file path: {@code data/<namespace>/curse/<path>.json} is
 * {@code <namespace>:<path>}.
 *
 * <p>{@code hook} and {@code resolve} are carried as raw dynamics; the engine
 * interprets the hook types it implements and leaves the rest untouched, so
 * the schema can grow ahead of the code.
 */
public record Curse(
        String name,
        String description,
        int severity,
        boolean mature,
        Dynamic<?> hook,
        Dynamic<?> resolve) {

    public static final Codec<Curse> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.fieldOf("name").forGetter(Curse::name),
            Codec.STRING.fieldOf("description").forGetter(Curse::description),
            Codec.INT.fieldOf("severity").forGetter(Curse::severity),
            Codec.BOOL.optionalFieldOf("mature", false).forGetter(Curse::mature),
            Codec.PASSTHROUGH.fieldOf("hook").forGetter(Curse::hook),
            Codec.PASSTHROUGH.fieldOf("resolve").forGetter(Curse::resolve)
    ).apply(instance, Curse::new));
}
