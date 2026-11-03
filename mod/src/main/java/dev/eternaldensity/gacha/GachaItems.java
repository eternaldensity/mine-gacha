package dev.eternaldensity.gacha;

import dev.eternaldensity.gacha.ticket.TicketItem;
import net.minecraft.world.item.Item;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

/**
 * Item registry.
 */
public final class GachaItems {
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(GachaMod.MOD_ID);

    public static final DeferredItem<TicketItem> TICKET =
            ITEMS.registerItem("ticket", TicketItem::new, new Item.Properties().stacksTo(16));

    private GachaItems() {
    }

    public static void register(net.neoforged.bus.api.IEventBus modBus) {
        ITEMS.register(modBus);
    }
}
