package dev.eternaldensity.gacha.social;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.ai.gossip.GossipType;
import net.minecraft.world.item.trading.MerchantOffer;
import net.neoforged.neoforge.event.entity.player.TradeWithVillagerEvent;

public final class SocialEngine {
    private SocialEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(SocialEngine::onTrade);
    }

    private static void onTrade(TradeWithVillagerEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        int socialTraits = countSocialTraits(player);
        if (socialTraits <= 0) {
            return;
        }
        // Discount the current trade: each social trait reduces the cost by 1
        // (clamped to at least 1).
        MerchantOffer offer = event.getMerchantOffer();
        if (offer != null) {
            int discount = Math.min(offer.getCostA().getCount() - 1, socialTraits);
            if (discount > 0) {
                offer.setSpecialPriceDiff(offer.getSpecialPriceDiff() - discount);
            }
        }
        // Improve reputation for future offers when trading with a villager.
        if (event.getAbstractVillager() instanceof Villager villager) {
            villager.getGossips().add(player.getUUID(), GossipType.MAJOR_POSITIVE,
                    Math.min(GossipType.MAJOR_POSITIVE.max, 10 * socialTraits));
        }
        // Small XP bonus per trade, scaling with owned social traits.
        player.giveExperiencePoints(socialTraits);
    }

    private static int countSocialTraits(ServerPlayer player) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.ownedEntries().isEmpty()) {
            return 0;
        }
        var registry = player.level().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        int count = 0;
        for (String id : state.ownedEntries()) {
            ResourceLocation rl = ResourceLocation.tryParse(id);
            if (rl == null) continue;
            Entry entry = registry.get(rl);
            if (entry != null && entry.tags().contains("social")) {
                count++;
            }
        }
        return count;
    }
}
