package dev.eternaldensity.gacha.machine;

import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.entry.Entry;
import dev.eternaldensity.gacha.entry.EntryPool;
import dev.eternaldensity.gacha.roll.Rng;
import dev.eternaldensity.gacha.roll.RollEngine;
import dev.eternaldensity.gacha.roll.Tiers;
import dev.eternaldensity.gacha.roll.VanillaRng;
import dev.eternaldensity.gacha.ticket.TicketData;
import net.minecraft.ChatFormatting;
import net.minecraft.core.Registry;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Chat-driven result chooser for Advantage tickets and category-choice tickets.
 *
 * <p>The ticket is removed from the player and held in a pending record until
 * the player clicks a result or category, or the five-minute timeout returns
 * it. This keeps the machine's single-shot contract without requiring a GUI:
 * the click runs {@code /gacha choose <n>} or {@code /gacha category <name>}.
 */
public final class ChoiceService {
    public record ResultView(String name, String tier, double rarity) {
    }
    private static final long TIMEOUT_TICKS = 6000L;
    private static final Map<UUID, Pending> PENDING = new HashMap<>();

    private enum Stage {
        CATEGORY,
        ADVANTAGE
    }

    private record Result(ResourceLocation id, String name, double rarity) {
    }

    private record Pending(ItemStack refund, TicketData data, Stage stage, List<Result> results, long expiresAt) {
    }

    private ChoiceService() {
    }

    public static boolean begin(ServerLevel level, ServerPlayer player, ItemStack ticketStack, TicketData data) {
        if (PENDING.containsKey(player.getUUID())) {
            message(player, "Finish your current ticket choice first.");
            return false;
        }
        long expiresAt = level.getGameTime() + TIMEOUT_TICKS;
        if ("choice".equals(data.category())) {
            Registry<Entry> registry = level.registryAccess().registryOrThrow(GachaRegistries.ENTRY);
            boolean any = false;
            for (String category : MachineService.CATEGORIES) {
                if (!EntryPool.candidates(registry, category, data.filter()).isEmpty()) {
                    any = true;
                    break;
                }
            }
            if (!any) {
                message(player, "No entries are available for a choice ticket; the ticket was kept.");
                return false;
            }
            PENDING.put(player.getUUID(), new Pending(
                    ticketStack.copy(), data, Stage.CATEGORY, List.of(), expiresAt));
            ticketStack.shrink(1);
            sendCategoryPrompt(player);
            openCategoryMenu(player);
            return true;
        }
        if (data.advantage() > 1) {
            List<Result> results = roll(level, data, data.category(), data.advantage());
            if (results.isEmpty()) {
                message(player, "The advantage roll found no entries; the ticket was kept.");
                return false;
            }
            PENDING.put(player.getUUID(), new Pending(
                    ticketStack.copy(), data, Stage.ADVANTAGE, results, expiresAt));
            ticketStack.shrink(1);
            sendResultPrompt(player, results);
            openResultMenu(player, results);
            return true;
        }
        message(player, "This ticket does not need a result choice.");
        return false;
    }

    public static boolean chooseCategory(ServerPlayer player, String category) {
        Pending pending = PENDING.get(player.getUUID());
        if (pending == null || pending.stage() != Stage.CATEGORY) {
            message(player, "There is no category choice pending.");
            return false;
        }
        if (!MachineService.CATEGORIES.contains(category) && !"random".equals(category)) {
            message(player, "Unknown category '" + category + "'.");
            return false;
        }
        ServerLevel level = player.serverLevel();
        if (pending.data().advantage() > 1) {
            List<Result> results = roll(level, pending.data(), category, pending.data().advantage());
            if (results.isEmpty()) {
                refund(player, pending);
                message(player, "That category has no entries; the ticket was returned.");
                return false;
            }
            PENDING.put(player.getUUID(), new Pending(
                    pending.refund(), pending.data(), Stage.ADVANTAGE, results,
                    level.getGameTime() + TIMEOUT_TICKS));
            sendResultPrompt(player, results);
            openResultMenu(player, results);
            return true;
        }
        List<Result> results = roll(level, pending.data(), category, 1);
        if (results.isEmpty()) {
            refund(player, pending);
            message(player, "That category has no entries; the ticket was returned.");
            return false;
        }
        PENDING.remove(player.getUUID());
        return grant(player, pending, results.get(0));
    }

    public static boolean chooseResult(ServerPlayer player, int index) {
        Pending pending = PENDING.get(player.getUUID());
        if (pending == null || pending.stage() != Stage.ADVANTAGE) {
            message(player, "There is no result choice pending.");
            return false;
        }
        if (index < 1 || index > pending.results().size()) {
            message(player, "Choose a result between 1 and " + pending.results().size() + ".");
            return false;
        }
        PENDING.remove(player.getUUID());
        return grant(player, pending, pending.results().get(index - 1));
    }

    public static void onLogout(ServerPlayer player) {
        Pending pending = PENDING.remove(player.getUUID());
        if (pending != null) {
            refund(player, pending);
            message(player, "Your ticket choice was returned because you logged out.");
        }
    }

    public static void tick(ServerLevel level) {
        if (PENDING.isEmpty()) {
            return;
        }
        long now = level.getGameTime();
        List<UUID> expired = new ArrayList<>();
        for (var entry : PENDING.entrySet()) {
            if (now > entry.getValue().expiresAt()) {
                expired.add(entry.getKey());
            }
        }
        for (UUID uuid : expired) {
            Pending pending = PENDING.remove(uuid);
            ServerPlayer player = level.getServer().getPlayerList().getPlayer(uuid);
            if (pending != null && player != null) {
                refund(player, pending);
                message(player, "Your ticket choice timed out; the ticket was returned.");
            }
        }
    }

    private static boolean grant(ServerPlayer player, Pending pending, Result result) {
        Registry<Entry> registry = player.serverLevel().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        Entry entry = registry.get(result.id());
        if (entry == null) {
            refund(player, pending);
            message(player, "The chosen entry no longer exists; the ticket was returned.");
            return false;
        }
        if (!MachineService.grant(player.serverLevel(), player, new EntryPool.PoolEntry(result.id(), entry), pending.data())) {
            refund(player, pending);
            message(player, "The chosen entry could not be applied; the ticket was returned.");
            return false;
        }
        return true;
    }

    private static List<Result> roll(ServerLevel level, TicketData data, String category, int count) {
        Registry<Entry> registry = level.registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        Rng rng = new VanillaRng(level.getRandom());
        List<Result> results = new ArrayList<>();
        if ("random".equals(category)) {
            Map<String, List<RollEngine.Candidate<EntryPool.PoolEntry>>> pools = new LinkedHashMap<>();
            for (String name : MachineService.CATEGORIES) {
                pools.put(name, EntryPool.candidates(registry, name, data.filter()));
            }
            for (int index = 0; index < count; index++) {
                Optional<RollEngine.Draw<EntryPool.PoolEntry>> draw = RollEngine.drawRandomCategory(
                        rng, data.roll().min(), data.roll().avg(), data.roll().max(), data.roll().flat(),
                        pools, MachineService.CATEGORIES);
                draw.ifPresent(value -> results.add(new Result(
                        value.value().id(), value.value().entry().name(), value.value().entry().rarity())));
            }
        } else {
            List<RollEngine.Candidate<EntryPool.PoolEntry>> pool =
                    EntryPool.candidates(registry, category, data.filter());
            for (int index = 0; index < count; index++) {
                Optional<RollEngine.Draw<EntryPool.PoolEntry>> draw = RollEngine.draw(
                        rng, data.roll().min(), data.roll().avg(), data.roll().max(), data.roll().flat(), pool);
                draw.ifPresent(value -> results.add(new Result(
                        value.value().id(), value.value().entry().name(), value.value().entry().rarity())));
            }
        }
        return results;
    }

    private static void sendResultPrompt(ServerPlayer player, List<Result> results) {
        player.sendSystemMessage(Component.literal(
                "Choose one result. The ticket is held for five minutes:").withStyle(ChatFormatting.YELLOW));
        for (int index = 0; index < results.size(); index++) {
            Result result = results.get(index);
            MutableComponent line = Component.literal(
                    "[" + (index + 1) + "] " + Tiers.forRarity(result.rarity())
                            + " (" + String.format(java.util.Locale.ROOT, "%.1f", result.rarity()) + ") "
                            + result.name() + " ");
            line.append(button("[Choose]", "/gacha choose " + (index + 1)));
            player.sendSystemMessage(line);
        }
    }

    private static void sendCategoryPrompt(ServerPlayer player) {
        MutableComponent line = Component.literal("Choose a category: ").withStyle(ChatFormatting.YELLOW);
        for (String category : MachineService.CATEGORIES) {
            line.append(button("[" + category + "]", "/gacha category " + category)).append(" ");
        }
        line.append(button("[random]", "/gacha category random"));
        player.sendSystemMessage(line);
    }

    private static MutableComponent button(String label, String command) {
        return Component.literal(label).withStyle(Style.EMPTY
                .withColor(ChatFormatting.GREEN)
                .withClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND, command)));
    }


    private static void openCategoryMenu(ServerPlayer player) {
        List<String> cats = new ArrayList<>();
        for (String category : MachineService.CATEGORIES) {
            cats.add(category);
        }
        cats.add("random");
        net.minecraft.world.MenuProvider provider = new net.minecraft.world.MenuProvider() {
            @Override
            public net.minecraft.network.chat.Component getDisplayName() {
                return net.minecraft.network.chat.Component.literal("Choose a category");
            }
            @Override
            public net.minecraft.world.inventory.AbstractContainerMenu createMenu(int id, net.minecraft.world.entity.player.Inventory inv, net.minecraft.world.entity.player.Player player) {
                return new GachaChoiceMenu(id, inv, GachaChoiceMenu.Stage.CATEGORY, List.of(), cats);
            }
            @Override
            public void writeClientSideData(net.minecraft.world.inventory.AbstractContainerMenu menu, net.minecraft.network.RegistryFriendlyByteBuf buf) {
                GachaChoiceMenu.writeBuf(buf, GachaChoiceMenu.Stage.CATEGORY, List.of(), cats);
            }
        };
        try {
            player.openMenu(provider);
        } catch (RuntimeException exception) {
            dev.eternaldensity.gacha.GachaMod.LOGGER.debug("Could not open chooser GUI: {}", exception.toString());
        }
    }

    private static void openResultMenu(ServerPlayer player, List<Result> results) {
        List<ResultView> views = new ArrayList<>();
        for (Result r : results) {
            views.add(new ResultView(r.name(), Tiers.forRarity(r.rarity()), r.rarity()));
        }
        net.minecraft.world.MenuProvider provider = new net.minecraft.world.MenuProvider() {
            @Override
            public net.minecraft.network.chat.Component getDisplayName() {
                return net.minecraft.network.chat.Component.literal("Choose a result");
            }
            @Override
            public net.minecraft.world.inventory.AbstractContainerMenu createMenu(int id, net.minecraft.world.entity.player.Inventory inv, net.minecraft.world.entity.player.Player player) {
                return new GachaChoiceMenu(id, inv, GachaChoiceMenu.Stage.ADVANTAGE, views, List.of());
            }
            @Override
            public void writeClientSideData(net.minecraft.world.inventory.AbstractContainerMenu menu, net.minecraft.network.RegistryFriendlyByteBuf buf) {
                GachaChoiceMenu.writeBuf(buf, GachaChoiceMenu.Stage.ADVANTAGE, views, List.of());
            }
        };
        try {
            player.openMenu(provider);
        } catch (RuntimeException exception) {
            dev.eternaldensity.gacha.GachaMod.LOGGER.debug("Could not open chooser GUI: {}", exception.toString());
        }
    }

    private static void refund(ServerPlayer player, Pending pending) {
        ItemStack stack = pending.refund();
        if (!player.addItem(stack)) {
            player.drop(stack, false);
        }
    }

    private static void message(ServerPlayer player, String text) {
        player.displayClientMessage(Component.literal(text), false);
    }
}
