package dev.eternaldensity.gacha;

import dev.eternaldensity.gacha.machine.MachineBlock;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

/**
 * Block registry. The machine is the only place a ticket resolves.
 */
public final class GachaBlocks {
    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(GachaMod.MOD_ID);

    public static final DeferredBlock<MachineBlock> MACHINE = BLOCKS.registerBlock(
            "machine",
            MachineBlock::new,
            BlockBehaviour.Properties.of().strength(3.5F).requiresCorrectToolForDrops());

    public static final DeferredItem<BlockItem> MACHINE_ITEM =
            GachaItems.ITEMS.registerSimpleBlockItem("machine", MACHINE);

    private GachaBlocks() {
    }

    public static void register(net.neoforged.bus.api.IEventBus modBus) {
        BLOCKS.register(modBus);
    }
}
