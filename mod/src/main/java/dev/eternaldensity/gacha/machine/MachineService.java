package dev.eternaldensity.gacha.machine;

import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.entry.Entry;
import dev.eternaldensity.gacha.entry.EntryAdapters;
import dev.eternaldensity.gacha.entry.EntryPool;
import dev.eternaldensity.gacha.roll.Rng;
import dev.eternaldensity.gacha.roll.Rng;
import dev.eternaldensity.gacha.roll.RollEngine;
import dev.eternaldensity.gacha.roll.Tiers;
import dev.eternaldensity.gacha.roll.VanillaRng;
import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketPresets;
import net.minecraft.core.Registry;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Resolves a ticket against the entry registry. Atomic and single-shot: a
 * ticket is either fully consumed with its reward granted, or left untouched
 * (PROJECT_PLAN.md section 6.4).
 */
public final class MachineService {
    private static final List<String> CATEGORIES =
            List.of("ability", "trait", "skill", "item", "familiar");

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
        if (!EntryAdapters.apply(player, won.id(), won.entry())) {
            message(player, "Entry " + won.id() + " has an adapter this build cannot apply; the ticket was kept.");
            return false;
        }
        ticketStack.shrink(1);
        message(player, "Rolled " + Tiers.forRarity(result.rarity()) + " (" + format(result.rarity()) + ") - "
                + won.entry().name() + " [" + won.id() + "]");
        return true;
    }

    private static String format(double value) {
        return String.format(java.util.Locale.ROOT, "%.1f", value);
    }

    private static void message(Player player, String text) {
        player.displayClientMessage(net.minecraft.network.chat.Component.literal(text), false);
    }
}
