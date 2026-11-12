package dev.eternaldensity.gacha.science;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

public final class ScienceEngine {
    private ScienceEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(ScienceEngine::onSmelted);
    }

    private static void onSmelted(PlayerEvent.ItemSmeltedEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        if (countCluster(player, "tech_science") <= 0) return;
        player.giveExperiencePoints(1);
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