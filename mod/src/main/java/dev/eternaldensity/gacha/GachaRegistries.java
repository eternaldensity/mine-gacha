package dev.eternaldensity.gacha;

import com.mojang.serialization.Codec;
import dev.eternaldensity.gacha.curse.Curse;
import dev.eternaldensity.gacha.entry.Entry;
import dev.eternaldensity.gacha.feat.Feat;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DataPackRegistryEvent;

/**
 * Datapack registries (PROJECT_PLAN.md section 6.5). Entries are content, not
 * code: they live in {@code data/<pack_ns>/gacha/entry/} (NeoForge prefixes
 * non-minecraft registry namespaces) and are validated by
 * {@code chaoslab datapack} before the mod ever loads them.
 */
public final class GachaRegistries {
    public static final ResourceKey<Registry<Entry>> ENTRY =
            ResourceKey.createRegistryKey(ResourceLocation.fromNamespaceAndPath(GachaMod.MOD_ID, "entry"));
    public static final ResourceKey<Registry<Feat>> FEAT =
            ResourceKey.createRegistryKey(ResourceLocation.fromNamespaceAndPath(GachaMod.MOD_ID, "feat"));
    public static final ResourceKey<Registry<Curse>> CURSE =
            ResourceKey.createRegistryKey(ResourceLocation.fromNamespaceAndPath(GachaMod.MOD_ID, "curse"));

    private GachaRegistries() {
    }

    public static void register(IEventBus modBus) {
        modBus.addListener(GachaRegistries::onNewRegistry);
    }

    private static void onNewRegistry(DataPackRegistryEvent.NewRegistry event) {
        event.dataPackRegistry(ENTRY, Entry.CODEC);
        event.dataPackRegistry(FEAT, Feat.CODEC);
        event.dataPackRegistry(CURSE, Curse.CODEC);
    }
}
