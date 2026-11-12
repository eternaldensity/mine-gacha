package dev.eternaldensity.gacha.feat;

import com.mojang.serialization.Dynamic;
import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketPresets;

import net.minecraft.core.Registry;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.event.entity.player.AdvancementEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Feat engine (PROJECT_PLAN.md section 6.9). Advancement-driven feats (order A)
 * plus stat/kill/collect/visit triggers (order B). Granted feats are persisted
 * in PlayerData; kill/collect progress is persisted via FEAT_PROGRESS.
 */
public final class FeatEngine {
    private static final List<String> TIER_ORDER = List.of(
            "Trash", "Bronze", "Silver", "Gold", "Platinum", "Aluminium",
            "Diamond", "Legendary", "Mythical", "Divine", "Wild");

    private FeatEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(FeatEngine::onAdvancementEarned);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(FeatEngine::onLivingDeath);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(FeatEngine::onServerTick);
    }

    private static void onAdvancementEarned(AdvancementEvent.AdvancementEarnEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        grantMatching(player, feat -> {
            Feat.Trigger t = feat.trigger();
            return "advancement".equals(t.type())
                    && t.advancement().equals(event.getAdvancement().id().toString());
        });
    }

    private static void onLivingDeath(LivingDeathEvent event) {
        if (!(event.getSource().getEntity() instanceof ServerPlayer player)) return;
        String victimId = net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE
                .getKey(event.getEntity().getType()).toString();
        Registry<Feat> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.FEAT);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        Set<String> granted = new HashSet<>(state.grantedFeats());
        Map<String, Integer> progress = player.getData(GachaAttachments.FEAT_PROGRESS.get());
        if (progress == null) {
            progress = new java.util.HashMap<>();
        }
        List<String> toGrant = new ArrayList<>();
        for (var entry : registry.entrySet()) {
            String featId = entry.getKey().location().toString();
            if (granted.contains(featId)) continue;
            Feat feat = entry.getValue();
            Feat.Trigger t = feat.trigger();
            if (!"kill".equals(t.type())) continue;
            if (!t.entity().isEmpty() && !t.entity().equals(victimId) && !"*".equals(t.entity())) continue;
            int threshold = Math.max(1, t.count());
            int next = progress.getOrDefault(featId, 0) + 1;
            progress.put(featId, next);
            if (next >= threshold) {
                toGrant.add(featId);
            }
        }
        player.setData(GachaAttachments.FEAT_PROGRESS.get(), progress);
        grantList(player, toGrant, granted);
    }

    private static void onServerTick(ServerTickEvent.Post event) {
        if (event.getServer().getTickCount() % 20 != 0) return;
        for (ServerPlayer player : event.getServer().getPlayerList().getPlayers()) {
            checkNonKillFeats(player);
        }
    }

    private static void checkNonKillFeats(ServerPlayer player) {
        grantMatching(player, feat -> {
            Feat.Trigger t = feat.trigger();
            String type = t.type();
            if ("stat".equals(type)) {
                double value = readStat(player, t.stat());
                return t.threshold() > 0 && value >= t.threshold();
            }
            if ("collect".equals(type)) {
                int count = countItem(player, t.item());
                return count >= Math.max(1, t.count());
            }
            if ("visit".equals(type)) {
                return atLocation(player, t.location());
            }
            return false;
        });
    }

    private static void grantMatching(ServerPlayer player, java.util.function.Predicate<Feat> condition) {
        Registry<Feat> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.FEAT);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        Set<String> granted = new HashSet<>(state.grantedFeats());
        List<String> toGrant = new ArrayList<>();
        for (var entry : registry.entrySet()) {
            String featId = entry.getKey().location().toString();
            if (granted.contains(featId)) continue;
            Feat feat = entry.getValue();
            if (!condition.test(feat)) continue;
            toGrant.add(featId);
        }
        grantList(player, toGrant, granted);
    }

    private static void grantList(ServerPlayer player, List<String> toGrant, Set<String> granted) {
        if (toGrant.isEmpty()) return;
        Registry<Feat> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.FEAT);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        for (String featId : toGrant) {
            Feat feat = registry.getOptional(ResourceLocation.parse(featId)).orElse(null);
            if (feat == null) continue;
            grantFeat(player, featId, feat, state);
            granted.add(featId);
        }
        PlayerData updated = new PlayerData(
                state.ownedEntries(), state.lostEntries(), granted,
                state.residue(), state.modules(), state.curses(), state.rngSeed(), state.powerScore());
        player.setData(GachaAttachments.PLAYER_DATA.get(), updated);
    }

    private static void grantFeat(ServerPlayer player, String featId, Feat feat, PlayerData state) {
        Feat.Tickets tickets = feat.tickets();
        String tier = feat.tier();
        if (feat.powerRelative()) {
            tier = shiftTier(tier, state.powerScore());
        }
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
                + " (" + tier + ")"), false);
    }

    private static String shiftTier(String tier, double powerScore) {
        if (powerScore < 0.5) return tier;
        int idx = TIER_ORDER.indexOf(tier);
        if (idx < 0 || idx >= TIER_ORDER.size() - 1) return tier;
        return TIER_ORDER.get(idx + 1);
    }

    private static double readStat(ServerPlayer player, String stat) {
        if (stat.isEmpty()) return 0.0;
        if (stat.startsWith("minecraft:")) {
            try {
                ResourceLocation id = ResourceLocation.parse(stat);
                var holder = net.minecraft.core.registries.BuiltInRegistries.ATTRIBUTE.getHolder(id).orElse(null);
                if (holder != null) {
                    var inst = player.getAttribute(holder);
                    if (inst != null) return inst.getValue();
                }
            } catch (Exception ignored) {
            }
        }
        try {
            if (stat.contains("/")) {
                String[] parts = stat.split("/", 2);
                ResourceLocation type = ResourceLocation.parse(parts[0]);
                ResourceLocation id = ResourceLocation.parse(parts[1]);
                net.minecraft.stats.StatType<?> statType = net.minecraft.core.registries.BuiltInRegistries.STAT_TYPE.get(type);
                if (statType != null) {
                    Object statObj = ((net.minecraft.stats.StatType<net.minecraft.resources.ResourceLocation>) statType).get(id);
                    if (statObj != null) {
                        return player.getStats().getValue((net.minecraft.stats.StatType) statType, statObj);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return 0.0;
    }

    private static int countItem(ServerPlayer player, String itemId) {
        if (itemId.isEmpty()) return 0;
        ResourceLocation id = ResourceLocation.tryParse(itemId);
        if (id == null) return 0;
        net.minecraft.world.item.Item item = net.minecraft.core.registries.BuiltInRegistries.ITEM.get(id);
        if (item == null) return 0;
        int total = 0;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack s = player.getInventory().getItem(i);
            if (!s.isEmpty() && s.is(item)) total += s.getCount();
        }
        return total;
    }

    private static boolean atLocation(ServerPlayer player, String location) {
        if (location.isEmpty()) return false;
        ResourceLocation id = ResourceLocation.tryParse(location);
        if (id == null) return false;
        if (player.level().dimension().location().equals(id)) return true;
        try {
            var biome = player.level().getBiome(player.blockPosition());
            if (biome.unwrapKey().isPresent() && biome.unwrapKey().get().location().equals(id)) return true;
        } catch (Exception ignored) {
        }
        return false;
    }
}
