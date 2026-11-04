package dev.eternaldensity.gacha.machine;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.PowerScore;
import dev.eternaldensity.gacha.entry.Entry;
import dev.eternaldensity.gacha.entry.EntryAdapters;
import dev.eternaldensity.gacha.entry.EntryPool;
import dev.eternaldensity.gacha.entry.OriginAdapter;
import dev.eternaldensity.gacha.roll.Rng;
import dev.eternaldensity.gacha.roll.RollEngine;
import dev.eternaldensity.gacha.roll.Tiers;
import dev.eternaldensity.gacha.roll.VanillaRng;
import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketItem;
import dev.eternaldensity.gacha.ticket.TicketPresets;

import net.minecraft.core.Registry;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.*;

/**
 * Resolves a ticket against the entry registry. Atomic and single-shot: a
 * ticket is either fully consumed with its reward granted, or left untouched
 * (PROJECT_PLAN.md section 6.4).
 *
 * <p>Persistence and Power Score are wired here: ownership is tracked in the
 * player's attachment, duplicates follow the section 6.6 policy, and the score
 * is recomputed and stored after every grant.
 */
public final class MachineService {
    public static final List<String> CATEGORIES =
            List.of("ability", "trait", "skill", "item", "familiar");
    private static final Set<String> SUPPORTED_ADAPTERS = Set.of("gacha:item", "gacha:attribute", "gacha:effect");

    private MachineService() {
    }

    public static boolean open(ServerLevel level, Player player, ItemStack ticketStack) {
        TicketData data = ticketStack.get(GachaComponents.TICKET.get());
        if (data == null) {
            message(player, "This ticket has no data and cannot be opened.");
            return false;
        }
        if ("choice".equals(data.category()) || data.advantage() > 1) {
            if (player instanceof net.minecraft.server.level.ServerPlayer serverPlayer) {
                return ChoiceService.begin(level, serverPlayer, ticketStack, data);
            }
            message(player, "The result chooser needs a server player.");
            return false;
        }
        Registry<Entry> registry = level.registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        Rng rng = new VanillaRng(level.getRandom());
        Optional<RollEngine.Draw<EntryPool.PoolEntry>> draw;
        String category = data.category();
        if ("random".equals(category)) {
            Map<String, List<RollEngine.Candidate<EntryPool.PoolEntry>>> pools = new LinkedHashMap<>();
            for (String name : CATEGORIES) {
                pools.put(name, EntryPool.candidates(registry, name, data.filter()));
            }
            draw = RollEngine.drawRandomCategory(
                    rng, data.roll().min(), data.roll().avg(), data.roll().max(), data.roll().flat(), pools, CATEGORIES);
        } else if (CATEGORIES.contains(category)) {
            List<RollEngine.Candidate<EntryPool.PoolEntry>> pool =
                    EntryPool.candidates(registry, category, data.filter());
            draw = RollEngine.draw(
                    rng, data.roll().min(), data.roll().avg(), data.roll().max(), data.roll().flat(), pool);
        } else {
            message(player, "Ticket category '" + category + "' needs a chooser UI; use a category or random ticket.");
            return false;
        }
        if (draw.isEmpty()) {
            message(player, "The roll found no entry in this pool; the ticket was kept.");
            return false;
        }
        if (!grant(level, player, draw.get().value(), data)) {
            return false;
        }
        ticketStack.shrink(1);
        return true;
    }

    /**
     * Apply one already-drawn entry without touching a ticket stack. Used by
     * the direct machine path and by the chat result chooser.
     */
    public static boolean grant(ServerLevel level, Player player, EntryPool.PoolEntry won, TicketData data) {
        Registry<Entry> registry = level.registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        Entry entry = won.entry();
        String entryId = won.id().toString();

        if (state.ownedEntries().contains(entryId)) {
            // Duplicate policy (PROJECT_PLAN.md section 6.6).
            String duplicate = entry.duplicate().orElse("residue");
            if ("stack".equals(duplicate) || "count".equals(duplicate)) {
                if (!EntryAdapters.apply(player, won.id(), entry)) {
                    message(player, "Duplicate " + won.id() + " could not be applied; the ticket was kept.");
                    return false;
                }
                message(player, "Duplicate " + entry.name() + " granted again.");
            } else {
                String band = ticketBand(data);
                state = addResidue(state, band, 1);
                player.setData(GachaAttachments.PLAYER_DATA.get(), state);
                message(player, "Duplicate " + entry.name() + ": granted 1 " + band + " Residue.");
            }
            award(level, player, "first_duplicate");
            return true;
        }

        if (!EntryAdapters.apply(player, won.id(), entry)) {
            message(player, "Entry " + won.id() + " has an adapter this build cannot apply; the ticket was kept.");
            return false;
        }

        // Track ownership and recompute Power Score. Race origins are exclusive:
        // the new origin replaces the old one in the same layer, so drop the old
        // race entry from the owned set as well.
        Set<String> owned = new HashSet<>(state.ownedEntries());
        String originLayer = OriginAdapter.layer(entry);
        if (originLayer != null) {
            for (String id : new HashSet<>(owned)) {
                ResourceLocation otherId = ResourceLocation.tryParse(id);
                if (otherId == null) {
                    continue;
                }
                Entry other = registry.get(otherId);
                if (other != null && originLayer.equals(OriginAdapter.layer(other))) {
                    owned.remove(id);
                }
            }
        }
        owned.add(entryId);
        PlayerData updated = new PlayerData(
                owned,
                state.lostEntries(),
                state.grantedFeats(),
                state.residue(),
                state.modules(),
                state.curses(),
                state.rngSeed(),
                0.0);
        PowerScore.Config cfg = PowerScore.load();
        double score = PowerScore.compute(cfg, registry, updated);
        updated = new PlayerData(
                updated.ownedEntries(),
                updated.lostEntries(),
                updated.grantedFeats(),
                updated.residue(),
                updated.modules(),
                updated.curses(),
                updated.rngSeed(),
                score);
        player.setData(GachaAttachments.PLAYER_DATA.get(), updated);

        award(level, player, "first_roll");
        if (score >= 0.10) {
            award(level, player, "power_ten");
        }
        message(player, "Rolled " + Tiers.forRarity(entry.rarity()) + " (" + format(entry.rarity()) + ") - "
                + entry.name() + " [" + won.id() + "]  Power Score: "
                + String.format(java.util.Locale.ROOT, "%.2f", score));
        return true;
    }

    /** Award a code-granted advancement (the quest skeleton listens for these). */
    private static void award(ServerLevel level, Player player, String path) {        if (!(player instanceof net.minecraft.server.level.ServerPlayer serverPlayer)) {
            return;
        }
        var holder = level.getServer().getAdvancements()
                .get(ResourceLocation.fromNamespaceAndPath("gacha", path));
        if (holder != null) {
            serverPlayer.getAdvancements().award(holder, "manual");
        }
    }

    /**
     * Reapply permanent trait modifiers after a login or respawn. The owned set
     * is persisted, but attribute modifiers are transient on the entity, so a
     * new player instance starts without them.
     */
    public static void reapplyOwnedTraits(net.minecraft.server.level.ServerPlayer player) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.ownedEntries().isEmpty()) {
            return;
        }
        Registry<Entry> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        for (String id : state.ownedEntries()) {
            ResourceLocation entryId = ResourceLocation.tryParse(id);
            if (entryId == null) {
                continue;
            }
            Entry entry = registry.get(entryId);
            if (entry == null || !"trait".equals(entry.kind())) {
                continue;
            }
            String adapterType = EntryPool.adapterType(entry);
            if ("gacha:attribute".equals(adapterType)) {
                EntryAdapters.apply(player, entryId, entry);
            } else if ("gacha:effect".equals(adapterType)) {
                var adapter = entry.adapter().orElse(null);
                if (adapter != null && adapter.get("duration").asInt(1) == -1) {
                    EntryAdapters.apply(player, entryId, entry);
                }
            }
        }
    }

    private static String ticketBand(TicketData data) {
        if (data.depth().isPresent()) {
            return capitalise(data.depth().get());
        }
        double avg = data.roll().avg();
        String nearest = "Bronze";
        double best = Double.MAX_VALUE;
        for (String preset : new String[]{"Trash", "Bronze", "Silver", "Gold", "Aluminium", "Platinum",
                "Diamond", "Legendary", "Mythical", "Wild", "Divine", "Transcendent"}) {
            // Approximate preset averages from simulate.py.
            double presetAvg = presetAvg(preset);
            if (Math.abs(presetAvg - avg) < best) {
                best = Math.abs(presetAvg - avg);
                nearest = preset;
            }
        }
        return nearest;
    }

    private static double presetAvg(String preset) {
        return switch (preset) {
            case "Trash" -> 0.5;
            case "Bronze" -> 1.3;
            case "Silver" -> 2.3;
            case "Gold" -> 3.3;
            case "Aluminium" -> 4.0;
            case "Platinum" -> 4.3;
            case "Diamond" -> 5.3;
            case "Legendary" -> 6.3;
            case "Mythical" -> 7.3;
            case "Wild" -> 5.0;
            case "Divine" -> 8.3;
            case "Transcendent" -> 9.3;
            default -> 1.3;
        };
    }

    private static PlayerData addResidue(PlayerData state, String band, int count) {
        Map<String, Integer> residue = new HashMap<>(state.residue());
        residue.merge(band, count, Integer::sum);
        return new PlayerData(
                state.ownedEntries(), state.lostEntries(), state.grantedFeats(),
                residue, state.modules(), state.curses(), state.rngSeed(), state.powerScore());
    }

    private static String format(double value) {
        return String.format(java.util.Locale.ROOT, "%.1f", value);
    }

    private static String capitalise(String value) {
        if (value.isEmpty()) return value;
        return Character.toUpperCase(value.charAt(0)) + value.substring(1);
    }

    private static void message(Player player, String text) {
        player.displayClientMessage(net.minecraft.network.chat.Component.literal(text), false);
    }
}
