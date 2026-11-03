package dev.eternaldensity.gacha;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Per-player gacha state (PROJECT_PLAN.md sections 6.13 and 6.5).
 *
 * <p>Persisted through restarts and copied through death by default (curses
 * persist; mortal familiars become lost on death, which the engine handles).
 * The attachment is registered in {@link GachaAttachments}.
 */
public record PlayerData(
        Set<String> ownedEntries,
        Set<String> lostEntries,
        Set<String> grantedFeats,
        Map<String, Integer> residue,
        Set<String> modules,
        List<String> curses,
        long rngSeed,
        double powerScore) {

    public static final Codec<PlayerData> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.listOf().optionalFieldOf("owned", List.of())
                    .xmap(Set::copyOf, List::copyOf).forGetter(PlayerData::ownedEntries),
            Codec.STRING.listOf().optionalFieldOf("lost", List.of())
                    .xmap(Set::copyOf, List::copyOf).forGetter(PlayerData::lostEntries),
            Codec.STRING.listOf().optionalFieldOf("feats", List.of())
                    .xmap(Set::copyOf, List::copyOf).forGetter(PlayerData::grantedFeats),
            Codec.unboundedMap(Codec.STRING, Codec.INT).optionalFieldOf("residue", Map.of())
                    .forGetter(PlayerData::residue),
            Codec.STRING.listOf().optionalFieldOf("modules", List.of())
                    .xmap(Set::copyOf, List::copyOf).forGetter(PlayerData::modules),
            Codec.STRING.listOf().optionalFieldOf("curses", List.of())
                    .forGetter(PlayerData::curses),
            Codec.LONG.optionalFieldOf("rngSeed", 0L).forGetter(PlayerData::rngSeed),
            Codec.DOUBLE.optionalFieldOf("powerScore", 0.0).forGetter(PlayerData::powerScore)
    ).apply(instance, PlayerData::new));

    public static PlayerData empty() {
        return new PlayerData(Set.of(), Set.of(), Set.of(), Map.of(), Set.of(), List.of(),
                System.currentTimeMillis(), 0.0);
    }
}
