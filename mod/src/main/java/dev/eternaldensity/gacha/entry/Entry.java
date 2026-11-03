package dev.eternaldensity.gacha.entry;

import com.mojang.serialization.Codec;
import com.mojang.serialization.Dynamic;
import com.mojang.serialization.codecs.RecordCodecBuilder;

import java.util.List;
import java.util.Optional;

/**
 * One gacha entry, loaded from the {@code gacha:entry} datapack registry.
 *
 * <p>The record mirrors {@code mod/schema/entry.schema.json}, which is the
 * validated contract. {@code familiar}, {@code adapter} and {@code hooks} are
 * carried as raw dynamics for now: the engine interprets the adapter types it
 * implements and leaves the rest untouched, so the schema can grow ahead of the
 * code without breaking datapack loading.
 */
public record Entry(
        String kind,
        String name,
        String description,
        double rarity,
        List<String> tags,
        Optional<String> duplicate,
        Optional<Dynamic<?>> familiar,
        Optional<Dynamic<?>> adapter,
        Optional<Dynamic<?>> hooks) {

    public static final Codec<Entry> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.fieldOf("kind").forGetter(Entry::kind),
            Codec.STRING.fieldOf("name").forGetter(Entry::name),
            Codec.STRING.fieldOf("description").forGetter(Entry::description),
            Codec.DOUBLE.fieldOf("rarity").forGetter(Entry::rarity),
            Codec.STRING.listOf().optionalFieldOf("tags", List.of()).forGetter(Entry::tags),
            Codec.STRING.optionalFieldOf("duplicate").forGetter(Entry::duplicate),
            Codec.PASSTHROUGH.optionalFieldOf("familiar").forGetter(Entry::familiar),
            Codec.PASSTHROUGH.optionalFieldOf("adapter").forGetter(Entry::adapter),
            Codec.PASSTHROUGH.optionalFieldOf("hooks").forGetter(Entry::hooks)
    ).apply(instance, Entry::new));
}
