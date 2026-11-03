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
        FeatEngine.register();
        CurseEngine.register();
        LOGGER.info("Chaos Gacha initialising");
    }
}
