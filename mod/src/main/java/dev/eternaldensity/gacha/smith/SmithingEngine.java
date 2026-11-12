package dev.eternaldensity.gacha.smith;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.event.entity.player.AnvilRepairEvent;

public final class SmithingEngine {
    private SmithingEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(SmithingEngine::onAnvilRepair);
    }

    private static void onAnvilRepair(AnvilRepairEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        int smithing = countCluster(player, "tech_tool");
        if (smithing <= 0) return;
        // Reduce anvil break chance and grant a little XP.
        float breakChance = event.getBreakChance();
        event.setBreakChance(Math.max(0.0f, breakChance - 0.05f * smithing));
        player.giveExperiencePoints(smithing);
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
