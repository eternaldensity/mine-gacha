package dev.eternaldensity.gacha.healing;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;

public final class HealingEngine {
    private HealingEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(HealingEngine::onTick);
    }

    private static void onTick(PlayerTickEvent.Post event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        if (player.tickCount % 40 != 0) return;
        if (player.getHealth() >= player.getMaxHealth()) return;
        if (countCluster(player, "magic_healing") <= 0) return;
        player.heal(0.5f);
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