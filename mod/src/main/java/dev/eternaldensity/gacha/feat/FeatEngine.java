package dev.eternaldensity.gacha.feat;

import com.mojang.serialization.Dynamic;
import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketItem;
import dev.eternaldensity.gacha.ticket.TicketPresets;

import net.minecraft.core.Registry;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.event.entity.player.AdvancementEvent;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Advancement-driven feats (PROJECT_PLAN.md section 6.9, implementation order A).
 *
 * <p>Stat, kill, collect and visit triggers are declared in the schema but not
 * yet implemented; only advancement triggers grant feats in this build.
 */
public final class FeatEngine {
    private static final int CURSE_SLOTS = 3;

    private FeatEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(FeatEngine::onAdvancementEarned);
    }

    private static void onAdvancementEarned(AdvancementEvent.AdvancementEarnEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        Registry<Feat> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.FEAT);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        Set<String> granted = new HashSet<>(state.grantedFeats());
        List<String> toGrant = new ArrayList<>();
        for (var entry : registry.entrySet()) {
            Feat feat = entry.getValue();
            Feat.Trigger trigger = feat.trigger();
            if (!"advancement".equals(trigger.type())) {
                continue;
            }
            if (!trigger.advancement().equals(event.getAdvancement().id().toString())) {
                continue;
            }
            String featId = entry.getKey().location().toString();
            if (granted.contains(featId)) {
                continue;
            }
            toGrant.add(featId);
        }
        if (toGrant.isEmpty()) {
            return;
        }
        for (String featId : toGrant) {
            Feat feat = registry.getOptional(ResourceLocation.parse(featId)).orElse(null);
            if (feat == null) continue;
            grantFeat(player, featId, feat);
            granted.add(featId);
        }
        PlayerData updated = new PlayerData(
                state.ownedEntries(), state.lostEntries(), granted,
                state.residue(), state.modules(), state.curses(), state.rngSeed(), state.powerScore());
        player.setData(GachaAttachments.PLAYER_DATA.get(), updated);
    }

    private static void grantFeat(ServerPlayer player, String featId, Feat feat) {
        Feat.Tickets tickets = feat.tickets();
        String tier = feat.tier();
        String presetName = tier.toLowerCase(java.util.Locale.ROOT);
        dev.eternaldensity.gacha.ticket.RollSpec roll = dev.eternaldensity.gacha.ticket.TicketPresets.BY_NAME.getOrDefault(
                presetName, dev.eternaldensity.gacha.ticket.TicketPresets.BY_NAME.get("bronze"));
        int advantage = Math.max(1, Math.min(6, tickets.advantage()));
        for (int i = 0; i < tickets.count(); i++) {
            dev.eternaldensity.gacha.ticket.TicketData data = new dev.eternaldensity.gacha.ticket.TicketData(
                    1, tickets.category(), roll, advantage, java.util.Optional.empty(),
                    java.util.Optional.empty(), java.util.Optional.of("feat:" + featId));
            ItemStack stack = new ItemStack(dev.eternaldensity.gacha.GachaItems.TICKET.get());
            stack.set(dev.eternaldensity.gacha.GachaComponents.TICKET.get(), data);
            if (!player.addItem(stack)) {
                player.drop(stack, false);
            }
        }
        player.displayClientMessage(Component.literal("Feat earned: " + feat.name()
                + " (" + feat.tier() + ")"), false);
    }
}
