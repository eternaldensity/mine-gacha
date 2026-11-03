package dev.eternaldensity.gacha.loot;

import com.mojang.serialization.MapCodec;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

/**
 * Registers the {@code gacha:add_ticket} and {@code gacha:remove_items} global
 * loot modifier serializers (PROJECT_PLAN.md section 6.12).
 */
public final class GachaLootModifiers {
    public static final DeferredRegister<MapCodec<? extends net.neoforged.neoforge.common.loot.IGlobalLootModifier>> SERIALIZERS =
            DeferredRegister.create(NeoForgeRegistries.GLOBAL_LOOT_MODIFIER_SERIALIZERS, dev.eternaldensity.gacha.GachaMod.MOD_ID);

    public static final DeferredHolder<MapCodec<? extends net.neoforged.neoforge.common.loot.IGlobalLootModifier>, MapCodec<AddTicketModifier>> ADD_TICKET =
            SERIALIZERS.register("add_ticket", () -> AddTicketModifier.CODEC);

    public static final DeferredHolder<MapCodec<? extends net.neoforged.neoforge.common.loot.IGlobalLootModifier>, MapCodec<RemoveItemsModifier>> REMOVE_ITEMS =
            SERIALIZERS.register("remove_items", () -> RemoveItemsModifier.CODEC);

    private GachaLootModifiers() {
    }

    public static void register(IEventBus modBus) {
        SERIALIZERS.register(modBus);
    }
}
