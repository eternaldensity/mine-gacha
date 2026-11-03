package dev.eternaldensity.gacha;

import com.mojang.serialization.Codec;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DataPackRegistryEvent;

/**
 * Datapack registries (PROJECT_PLAN.md section 6.5). Entries are content, not
 * code: they live in {@code data/gacha/entry/} and are validated by
 * {@code chaoslab datapack} before the mod ever loads them.
 */
public final class GachaRegistries {
    public static final ResourceKey<Registry<Entry>> ENTRY =
            ResourceKey.createRegistryKey(ResourceLocation.fromNamespaceAndPath(GachaMod.MOD_ID, "entry"));

    private GachaRegistries() {
    }

    public static void register(IEventBus modBus) {
        modBus.addListener(GachaRegistries::onNewRegistry);
    }

    private static void onNewRegistry(DataPackRegistryEvent.NewRegistry event) {
        event.dataPackRegistry(ENTRY, Entry.CODEC);
    }
}
