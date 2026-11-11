package dev.eternaldensity.gacha.machine;

import net.minecraft.core.registries.Registries;
import net.minecraft.world.inventory.MenuType;
import net.neoforged.neoforge.registries.DeferredRegister;

public final class GachaMenus {
    public static final DeferredRegister<MenuType<?>> MENUS =
            DeferredRegister.create(Registries.MENU, "gacha");

    public static final net.neoforged.neoforge.registries.DeferredHolder<MenuType<?>, MenuType<GachaChoiceMenu>> CHOICE =
            MENUS.register("choice", () -> net.neoforged.neoforge.common.extensions.IMenuTypeExtension.create(GachaChoiceMenu::new));

    private GachaMenus() {
    }
}
