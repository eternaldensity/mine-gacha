package dev.eternaldensity.gacha.gate;

import dev.eternaldensity.gacha.GachaMod;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.event.server.ServerAboutToStartEvent;

import java.lang.reflect.Field;
import java.util.List;

/**
 * Removes a small allowlist of crafting recipes after datapack load. Used to
 * take backpack crafting off the table when those items are meant to come from
 * gacha entries instead.
 */
public final class RecipeDisabler {
    private static final List<String> DISABLED = List.of(
            "sophisticatedbackpacks:backpack",
            "sophisticatedbackpacks:copper_backpack",
            "sophisticatedbackpacks:iron_backpack",
            "sophisticatedbackpacks:iron_backpack_from_copper",
            "sophisticatedbackpacks:gold_backpack",
            "sophisticatedbackpacks:gold_backpack_from_iron",
            "sophisticatedbackpacks:diamond_backpack",
            "sophisticatedbackpacks:diamond_backpack_from_gold",
            "sophisticatedbackpacks:netherite_backpack"
    );

    private RecipeDisabler() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(RecipeDisabler::onServerAboutToStart);
    }

    private static void onServerAboutToStart(ServerAboutToStartEvent event) {
        var manager = event.getServer().getRecipeManager();
        try {
            Field byNameField = manager.getClass().getDeclaredField("byName");
            byNameField.setAccessible(true);
            @SuppressWarnings("unchecked")
            java.util.Map<ResourceLocation, Object> byName =
                    (java.util.Map<ResourceLocation, Object>) byNameField.get(manager);
            Field byTypeField = manager.getClass().getDeclaredField("byType");
            byTypeField.setAccessible(true);
            @SuppressWarnings("unchecked")
            com.google.common.collect.Multimap<Object, Object> byType =
                    (com.google.common.collect.Multimap<Object, Object>) byTypeField.get(manager);
            for (String id : DISABLED) {
                ResourceLocation key = ResourceLocation.tryParse(id);
                if (key == null) continue;
                Object holder = byName.remove(key);
                if (holder != null) {
                    byType.values().remove(holder);
                    GachaMod.LOGGER.info("Disabled recipe {}", id);
                }
            }
        } catch (ReflectiveOperationException | RuntimeException exception) {
            GachaMod.LOGGER.warn("Could not disable backpack recipes: {}", exception.toString());
        }
    }
}
