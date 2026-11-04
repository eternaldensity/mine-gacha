package dev.eternaldensity.gacha.curse;

import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.ticket.RollSpec;
import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketPresets;
import net.minecraft.core.Registry;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;

import java.util.List;
import java.util.Optional;

/**
 * The voluntary curse roll (PROJECT_PLAN.md sections 4.4 and 6.8). A d20 maps to
 * a severity tier; one non-mature curse of that tier is taken, and the payout is
 * a ticket. The choice/advantage payouts are represented as extra random tickets
 * until the result chooser exists.
 */
public final class CurseService {
    private CurseService() {
    }

    public static boolean takeRandomCurse(ServerLevel level, ServerPlayer player) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().size() >= CurseEngine.MAX_SLOTS) {
            player.displayClientMessage(Component.literal(
                    "All " + CurseEngine.MAX_SLOTS + " curse slots are full."), false);
            return false;
        }
        Registry<Curse> registry = level.registryAccess().registryOrThrow(GachaRegistries.CURSE);
        int roll = level.getRandom().nextInt(20) + 1;
        String tier = tierFor(roll);
        List<Curse> candidates = registry.stream()
                .filter(curse -> !curse.mature() && tierFor(curse.severity()).equals(tier))
                .toList();
        if (candidates.isEmpty()) {
            player.displayClientMessage(Component.literal(
                    "No " + tier + " curse is authored; the roll was discarded."), false);
            return false;
        }
        Curse curse = candidates.get(level.getRandom().nextInt(candidates.size()));
        ResourceLocation id = registry.getKey(curse);
        if (id == null || !CurseEngine.takeCurse(player, id.toString())) {
            return false;
        }
        Payout payout = payout(tier);
        grantTicket(player, payout);
        player.displayClientMessage(Component.literal(
                "Curse roll " + roll + " (" + tier + "): " + curse.name()
                        + " — " + curse.description()
                        + " Resolve: " + resolveLabel(level, curse)
                        + ". Payout: " + payout.label() + "."), false);
        return true;
    }

    private record Payout(String band, String category, int advantage, int count, String label) {
    }

    private static Payout payout(String tier) {
        return switch (tier) {
            case "Minor" -> new Payout("gold", "random", 1, 1, "1 Gold ticket");
            case "Medium" -> new Payout("gold", "random", 2, 1, "1 Gold ticket with 2x Advantage");
            case "Major" -> new Payout("gold", "choice", 1, 1, "1 Gold choice ticket");
            case "Severe" -> new Payout("platinum", "random", 1, 1, "1 Platinum ticket");
            default -> new Payout("platinum", "choice", 1, 1, "1 Platinum choice ticket");
        };
    }

    private static String resolveLabel(ServerLevel level, Curse curse) {
        var resolve = curse.resolve();
        if (!"advancement".equals(resolve.get("type").asString(""))) {
            return resolve.get("type").asString("unknown");
        }
        ResourceLocation id = ResourceLocation.tryParse(resolve.get("advancement").asString(""));
        if (id == null) {
            return "unknown";
        }
        var holder = level.getServer().getAdvancements().get(id);
        if (holder != null && holder.value().display().isPresent()) {
            return holder.value().display().get().getTitle().getString();
        }
        return id.toString();
    }

    public static String tierFor(int roll) {
        if (roll <= 6) {
            return "Minor";
        }
        if (roll <= 13) {
            return "Medium";
        }
        if (roll <= 17) {
            return "Major";
        }
        if (roll <= 19) {
            return "Severe";
        }
        return "Ultimate";
    }

    private static void grantTicket(ServerPlayer player, Payout payout) {
        RollSpec roll = TicketPresets.BY_NAME.get(payout.band());
        if (roll == null) {
            return;
        }
        TicketData data = new TicketData(
                1, payout.category(), roll, payout.advantage(),
                Optional.empty(), Optional.empty(), Optional.of("curse"));
        for (int index = 0; index < payout.count(); index++) {
            ItemStack stack = new ItemStack(GachaItems.TICKET.get());
            stack.set(GachaComponents.TICKET.get(), data);
            if (!player.addItem(stack)) {
                player.drop(stack, false);
            }
        }
    }
}
