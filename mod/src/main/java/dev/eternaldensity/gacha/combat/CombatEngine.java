package dev.eternaldensity.gacha.combat;

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

public final class CombatEngine {
    private static final ResourceLocation MODIFIER_ID =
            ResourceLocation.parse("gacha:combat_skill");

    private CombatEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CombatEngine::onLogin);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CombatEngine::onRespawn);
    }

    private static void onLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer p) apply(p);
    }

    private static void onRespawn(PlayerEvent.PlayerRespawnEvent event) {
        if (event.getEntity() instanceof ServerPlayer p) apply(p);
    }

    private static void apply(ServerPlayer player) {
        int melee = countCluster(player, "combat_melee");
        int ranged = countCluster(player, "combat_ranged");
        int total = melee + ranged;
        var instance = player.getAttribute(Attributes.ATTACK_DAMAGE);
        if (instance == null) return;
        instance.removeModifier(MODIFIER_ID);
        if (total > 0) {
            instance.addTransientModifier(new AttributeModifier(
                    MODIFIER_ID, 0.5 * total, AttributeModifier.Operation.ADD_VALUE));
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
