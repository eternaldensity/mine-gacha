package dev.eternaldensity.gacha.machine;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;

public class MachineBlock extends Block {
    public MachineBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected ItemInteractionResult useItemOn(
            ItemStack stack,
            BlockState state,
            Level level,
            BlockPos pos,
            Player player,
            InteractionHand hand,
            BlockHitResult hitResult) {
        if (!(stack.getItem() instanceof dev.eternaldensity.gacha.ticket.TicketItem)) {
            return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }
        if (level.isClientSide()) {
            return ItemInteractionResult.SUCCESS;
        }
        MachineService.open((net.minecraft.server.level.ServerLevel) level, player, stack);
        return ItemInteractionResult.CONSUME;
    }
}
