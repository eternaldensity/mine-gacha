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
    private static final List<String> CATEGORIES =
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
        if (data.advantage() > 1) {
            message(player, "Advantage tickets need the result chooser, which is not in this build yet.");
            return false;
        }
        Registry<Entry> registry = level.registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
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
        RollEngine.Draw<EntryPool.PoolEntry> result = draw.get();
        EntryPool.PoolEntry won = result.value();
        Entry entry = won.entry();
        String entryId = won.id().toString();

        if (state.ownedEntries().contains(entryId)) {
            // Duplicate policy (PROJECT_PLAN.md section 6.6).
            String duplicate = entry.duplicate().orElse("residue");
            if ("stack".equals(duplicate) || "count".equals(duplicate)) {
                if (!EntryAdapters.apply(player, won.id(), entry)) {
                    message(player, "Duplicate " + won.id() + " could not be applied; ticket kept.");
                    return false;
                }
                ticketStack.shrink(1);
                message(player, "Duplicate " + entry.name() + " granted again.");
            } else {
                String band = ticketBand(data);
                state = addResidue(state, band, 1);
                player.setData(GachaAttachments.PLAYER_DATA.get(), state);
                ticketStack.shrink(1);
                message(player, "Duplicate " + entry.name() + ": granted 1 " + band + " Residue.");
            }
            award(level, player, "first_duplicate");
            return true;
        }

        if (!EntryAdapters.apply(player, won.id(), entry)) {
            message(player, "Entry " + won.id() + " has an adapter this build cannot apply; the ticket was kept.");
            return false;
        }

        // Track ownership and recompute Power Score.
        Set<String> owned = new HashSet<>(state.ownedEntries());
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

        ticketStack.shrink(1);
        award(level, player, "first_roll");
        if (score >= 0.10) {
            award(level, player, "power_ten");
        }
        message(player, "Rolled " + Tiers.forRarity(result.rarity()) + " (" + format(result.rarity()) + ") - "
                + entry.name() + " [" + won.id() + "]  Power Score: " + String.format(java.util.Locale.ROOT, "%.2f", score));
        return true;
    }

    /** Award a code-granted advancement (the quest skeleton listens for these). */
    private static void award(ServerLevel level, Player player, String path) {
        if (!(player instanceof net.minecraft.server.level.ServerPlayer serverPlayer)) {
            return;
        }
        var holder = level.getServer().getAdvancements()
                .get(ResourceLocation.fromNamespaceAndPath("gacha", path));
        if (holder != null) {
            serverPlayer.getAdvancements().award(holder, "manual");
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
