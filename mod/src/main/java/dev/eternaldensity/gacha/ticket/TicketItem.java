package dev.eternaldensity.gacha.ticket;

import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.roll.Tiers;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;
import java.util.Locale;

/**
 * The ticket item (PROJECT_PLAN.md sections 6.3 and 6.4). Tickets are inert
 * until the Gacha Machine consumes them; no auto-opening, no sealed state.
 */
public class TicketItem extends Item {
    public TicketItem(Properties properties) {
        super(properties);
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        TicketData data = stack.get(GachaComponents.TICKET.get());
        if (data == null) {
            tooltip.add(Component.translatable("tooltip.gacha.ticket.blank").withStyle(ChatFormatting.GRAY));
            return;
        }
        String tier = Tiers.forRarity(data.roll().avg());
        tooltip.add(Component.literal(capitalise(data.category()) + " - " + tier)
                .withStyle(ChatFormatting.GOLD));
        tooltip.add(Component.translatable(
                        "tooltip.gacha.ticket.roll",
                        format(data.roll().min()), format(data.roll().max()), format(data.roll().avg()))
                .withStyle(ChatFormatting.GRAY));
        if (data.roll().flat()) {
            tooltip.add(Component.translatable("tooltip.gacha.ticket.flat").withStyle(ChatFormatting.GRAY));
        }
        if (data.advantage() > 1) {
            tooltip.add(Component.translatable("tooltip.gacha.ticket.advantage", data.advantage())
                    .withStyle(ChatFormatting.AQUA));
        }
        data.depth().ifPresent(depth -> tooltip.add(
                Component.translatable("tooltip.gacha.ticket.depth", depth).withStyle(ChatFormatting.DARK_GRAY)));
        tooltip.add(Component.translatable("tooltip.gacha.ticket.open").withStyle(ChatFormatting.DARK_GRAY));
    }

    private static String format(double value) {
        return String.format(Locale.ROOT, "%.1f", value);
    }

    private static String capitalise(String value) {
        if (value.isEmpty()) {
            return value;
        }
        return Character.toUpperCase(value.charAt(0)) + value.substring(1);
    }
}
