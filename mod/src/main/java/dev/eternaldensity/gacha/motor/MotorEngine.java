package dev.eternaldensity.gacha.motor;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;

public final class MotorEngine {
    private MotorEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(MotorEngine::onTick);
    }

    private static void onTick(PlayerTickEvent.Post event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        if (!player.isSprinting()) return;
        if (player.tickCount % 200 != 0) return;
        if (countCluster(player, "tech_movement") <= 0 && countCluster(player, "tech_machine") <= 0) return;
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
