package dev.eternaldensity.gacha;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.attachment.AttachmentType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

/**
 * Per-player persistence (PROJECT_PLAN.md sections 6.13 and 13).
 */
public final class GachaAttachments {
    public static final DeferredRegister<AttachmentType<?>> ATTACHMENTS =
            DeferredRegister.create(NeoForgeRegistries.ATTACHMENT_TYPES, GachaMod.MOD_ID);

    public static final DeferredHolder<AttachmentType<?>, AttachmentType<PlayerData>> PLAYER_DATA =
            ATTACHMENTS.register("player_data", () -> AttachmentType.<PlayerData>builder(PlayerData::empty)
                    .serialize(PlayerData.CODEC)
                    .copyOnDeath()
                    .build());

    public static final DeferredHolder<AttachmentType<?>, AttachmentType<java.util.Map<String, Integer>>> CURSE_PROGRESS =
            ATTACHMENTS.register("curse_progress", () -> AttachmentType.<java.util.Map<String, Integer>>builder(() -> new java.util.HashMap<>())
                    .serialize(com.mojang.serialization.Codec.unboundedMap(com.mojang.serialization.Codec.STRING, com.mojang.serialization.Codec.INT))
                    .copyOnDeath()
                    .build());

    private GachaAttachments() {
    }

    public static void register(IEventBus modBus) {
        ATTACHMENTS.register(modBus);
    }
}
