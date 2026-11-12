package dev.eternaldensity.gacha;

import com.mojang.logging.LogUtils;
import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaBlocks;
import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.loot.GachaLootModifiers;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.curse.CurseEngine;
import dev.eternaldensity.gacha.feat.FeatEngine;
import dev.eternaldensity.gacha.machine.GachaMenus;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;

@Mod(GachaMod.MOD_ID)
public final class GachaMod {
    public static final String MOD_ID = "gacha";
    public static final Logger LOGGER = LogUtils.getLogger();

    public GachaMod(IEventBus modBus, ModContainer container) {
        GachaComponents.register(modBus);
        GachaItems.register(modBus);
        GachaBlocks.register(modBus);
        GachaRegistries.register(modBus);
        GachaAttachments.register(modBus);
        GachaLootModifiers.register(modBus);
        GachaCommands.register();
        GachaMenus.MENUS.register(modBus);
        FeatEngine.register();
        CurseEngine.register();
        dev.eternaldensity.gacha.social.SocialEngine.register();
        dev.eternaldensity.gacha.gate.RecipeGatingEngine.register();
        dev.eternaldensity.gacha.smith.SmithingEngine.register();
        dev.eternaldensity.gacha.medical.MedicalEngine.register();
        dev.eternaldensity.gacha.combat.CombatEngine.register();
        dev.eternaldensity.gacha.stealth.StealthEngine.register();
        dev.eternaldensity.gacha.motor.MotorEngine.register();
        dev.eternaldensity.gacha.healing.HealingEngine.register();
        dev.eternaldensity.gacha.science.ScienceEngine.register();
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(
                (net.neoforged.neoforge.event.entity.player.PlayerEvent.PlayerLoggedInEvent event) -> {
                    if (event.getEntity() instanceof net.minecraft.server.level.ServerPlayer player) {
                        dev.eternaldensity.gacha.machine.MachineService.reapplyOwnedTraits(player);
                        CurseEngine.reapplyCurseHooks(player);
                    }
                });
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(
                (net.neoforged.neoforge.event.entity.player.PlayerEvent.PlayerRespawnEvent event) -> {
                    if (event.getEntity() instanceof net.minecraft.server.level.ServerPlayer player) {
                        dev.eternaldensity.gacha.machine.MachineService.reapplyOwnedTraits(player);
                        CurseEngine.reapplyCurseHooks(player);
                        CurseEngine.triggerEvent(player, "on_respawn");
                    }
                });
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(
                (net.neoforged.neoforge.event.entity.player.PlayerEvent.PlayerLoggedOutEvent event) -> {
                    if (event.getEntity() instanceof net.minecraft.server.level.ServerPlayer player) {
                        dev.eternaldensity.gacha.machine.ChoiceService.onLogout(player);
                    }
                });
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(
                (net.neoforged.neoforge.event.tick.ServerTickEvent.Post event) -> {
                    if (event.getServer().getTickCount() % 20 == 0) {
                        dev.eternaldensity.gacha.machine.ChoiceService.tick(event.getServer().overworld());
                    }
                });
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(
                (net.neoforged.neoforge.event.server.ServerStoppingEvent event) -> {
                    dev.eternaldensity.gacha.machine.ChoiceService.refundAll(event.getServer());
                });
        LOGGER.info("Chaos Gacha initialising");
    }
}
