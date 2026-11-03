package dev.eternaldensity.gacha;

import com.mojang.logging.LogUtils;
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
        GachaCommands.register();
        LOGGER.info("Chaos Gacha initialising");
    }
}
