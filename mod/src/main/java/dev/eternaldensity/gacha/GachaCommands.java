package dev.eternaldensity.gacha;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import dev.eternaldensity.gacha.ticket.TicketData;
import dev.eternaldensity.gacha.ticket.TicketItem;
import dev.eternaldensity.gacha.ticket.TicketPresets;
import dev.eternaldensity.gacha.curse.CurseService;
import net.minecraft.server.level.ServerLevel;

import java.util.Locale;

public final class GachaCommands {
    private GachaCommands() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(GachaCommands::onRegisterCommands);
    }

    private static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<net.minecraft.commands.CommandSourceStack> dispatcher = event.getDispatcher();
        var root = Commands.literal("gacha")
                .then(Commands.literal("choose")
                        .then(Commands.argument("index", com.mojang.brigadier.arguments.IntegerArgumentType.integer(1))
                                .executes(GachaCommands::chooseResult)))
                .then(Commands.literal("category")
                        .then(Commands.argument("category", StringArgumentType.word())
                                .suggests((context, builder) -> {
                                    for (String name : dev.eternaldensity.gacha.machine.MachineService.CATEGORIES) {
                                        builder.suggest(name);
                                    }
                                    builder.suggest("random");
                                    return builder.buildFuture();
                                })
                                .executes(GachaCommands::chooseCategory)))
                .then(Commands.literal("curse")
                        .requires(source -> source.hasPermission(Commands.LEVEL_GAMEMASTERS))
                        .executes(GachaCommands::takeCurse))
                .then(Commands.literal("ticket")
                        .requires(source -> source.hasPermission(Commands.LEVEL_GAMEMASTERS))
                        .then(Commands.literal("give")
                                .then(Commands.argument("targets", EntityArgument.players())
                                        .then(Commands.argument("preset", StringArgumentType.word())
                                                .suggests((context, builder) -> {
                                                    for (String name : TicketPresets.BY_NAME.keySet()) {
                                                        builder.suggest(name);
                                                    }
                                                    return builder.buildFuture();
                                                })
                                                .executes(GachaCommands::giveTicket)))))
                .then(Commands.literal("machine")
                        .requires(source -> source.hasPermission(Commands.LEVEL_GAMEMASTERS))
                        .then(Commands.literal("give")
                                .then(Commands.argument("targets", EntityArgument.players())
                                        .executes(GachaCommands::giveMachine))));
        dispatcher.register(root);
    }

    private static int chooseResult(CommandContext<net.minecraft.commands.CommandSourceStack> context) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = context.getSource().getPlayerOrException();
        int index = com.mojang.brigadier.arguments.IntegerArgumentType.getInteger(context, "index");
        return dev.eternaldensity.gacha.machine.ChoiceService.chooseResult(player, index) ? 1 : 0;
    }

    private static int chooseCategory(CommandContext<net.minecraft.commands.CommandSourceStack> context) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = context.getSource().getPlayerOrException();
        String category = StringArgumentType.getString(context, "category").toLowerCase(Locale.ROOT);
        return dev.eternaldensity.gacha.machine.ChoiceService.chooseCategory(player, category) ? 1 : 0;
    }

    private static int takeCurse(CommandContext<net.minecraft.commands.CommandSourceStack> context) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = context.getSource().getPlayerOrException();
        return CurseService.takeRandomCurse((ServerLevel) player.level(), player) ? 1 : 0;
    }

    private static int giveTicket(CommandContext<net.minecraft.commands.CommandSourceStack> context) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        String presetName = StringArgumentType.getString(context, "preset").toLowerCase(Locale.ROOT);
        dev.eternaldensity.gacha.ticket.RollSpec roll = TicketPresets.BY_NAME.get(presetName);
        if (roll == null) {
            context.getSource().sendFailure(Component.literal("Unknown preset '" + presetName
                    + "'. Known: " + String.join(", ", TicketPresets.BY_NAME.keySet())));
            return 0;
        }
        TicketData data = new TicketData(1, "random", roll, 1, java.util.Optional.empty(),
                java.util.Optional.empty(), java.util.Optional.of(presetName));
        int count = 0;
        for (ServerPlayer target : EntityArgument.getPlayers(context, "targets")) {
            ItemStack stack = new ItemStack(GachaItems.TICKET.get());
            stack.set(GachaComponents.TICKET.get(), data);
            if (!target.addItem(stack)) {
                target.drop(stack, false);
            }
            count++;
        }
        final int granted = count;
        context.getSource().sendSuccess(() -> Component.literal("Granted a " + presetName
                + " ticket to " + granted + " player(s)"), true);
        return count;
    }

    private static int giveMachine(CommandContext<net.minecraft.commands.CommandSourceStack> context) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        int count = 0;
        for (ServerPlayer target : EntityArgument.getPlayers(context, "targets")) {
            ItemStack stack = new ItemStack(GachaBlocks.MACHINE_ITEM.get());
            if (!target.addItem(stack)) {
                target.drop(stack, false);
            }
            count++;
        }
        final int grantedMachine = count;
        context.getSource().sendSuccess(() -> Component.literal("Granted the Gacha Machine to " + grantedMachine + " player(s)"), true);
        return count;
    }
}
