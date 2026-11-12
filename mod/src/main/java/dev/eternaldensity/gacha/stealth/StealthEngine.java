package dev.eternaldensity.gacha.stealth;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

public final class StealthEngine {
    private static final ResourceLocation MODIFIER_ID =
            ResourceLocation.parse("gacha:stealth_skill");

    private StealthEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(StealthEngine::onLogin);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(StealthEngine::onRespawn);
    }

    private static void onLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer p) apply(p);
    }

    private static void onRespawn(PlayerEvent.PlayerRespawnEvent event) {
        if (event.getEntity() instanceof ServerPlayer p) apply(p);
    }

    private static void apply(ServerPlayer player) {
        int stealth = countCluster(player, "stealth");
        var instance = player.getAttribute(Attributes.MOVEMENT_SPEED);
        if (instance == null) return;
        instance.removeModifier(MODIFIER_ID);
        if (stealth > 0) {
            instance.addTransientModifier(new AttributeModifier(
                    MODIFIER_ID, 0.05 * stealth, AttributeModifier.Operation.ADD_MULTIPLIED_BASE));
        }
    }

    private static int countCluster(ServerPlayer player, String cluster) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.ownedEntries().isEmpty()) return 0;
        var registry = player.level().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        int count = 0;
        for (String id : state.ownedEntries()) {
            ResourceLocation rl = ResourceLocation.tryParse(id);
            if (rl == null) continue;
            Entry entry = registry.get(rl);
            if (entry != null && entry.tags().contains(cluster)) count++;
        }
        return count;
    }
}
