package dev.eternaldensity.gacha;

import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

import dev.eternaldensity.gacha.ticket.TicketData;

/**
 * The mod's data components (PROJECT_PLAN.md section 6.3).
 */
public final class GachaComponents {
    public static final DeferredRegister<DataComponentType<?>> COMPONENTS =
            DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, GachaMod.MOD_ID);

    public static final DeferredHolder<DataComponentType<?>, DataComponentType<TicketData>> TICKET =
            COMPONENTS.register("ticket", () -> DataComponentType.<TicketData>builder()
                    .persistent(TicketData.CODEC)
                    .networkSynchronized(TicketData.STREAM_CODEC)
                    .cacheEncoding()
                    .build());

    private GachaComponents() {
    }

    public static void register(net.neoforged.bus.api.IEventBus modBus) {
        COMPONENTS.register(modBus);
    }
}
