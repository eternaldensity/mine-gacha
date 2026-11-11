package dev.eternaldensity.gacha.machine;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterMenuScreensEvent;

@EventBusSubscriber(modid = "gacha", value = Dist.CLIENT, bus = EventBusSubscriber.Bus.MOD)
public final class GachaClientEvents {
    private GachaClientEvents() {
    }

    @SubscribeEvent
    public static void onRegisterMenuScreens(RegisterMenuScreensEvent event) {
        event.register(GachaMenus.CHOICE.get(), GachaChoiceScreen::new);
    }
}
