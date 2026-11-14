package dev.eternaldensity.gacha.gate;

import dev.eternaldensity.gacha.GachaMod;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.neoforged.neoforge.event.server.ServerAboutToStartEvent;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Removes a small allowlist of crafting recipes after datapack load. Used to
 * take backpack crafting off the table when those items are meant to come from
 * gacha entries instead.
 *
 * <p>The live recipe maps are immutable, so the disabler builds replacement
 * maps and swaps the fields.
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
            Map<ResourceLocation, RecipeHolder<?>> original =
                    (Map<ResourceLocation, RecipeHolder<?>>) byNameField.get(manager);

            Map<ResourceLocation, RecipeHolder<?>> replacement = new HashMap<>(original);
            int removed = 0;
            for (String id : DISABLED) {
                ResourceLocation key = ResourceLocation.tryParse(id);
                if (key == null) continue;
                if (replacement.remove(key) != null) {
                    removed++;
                    GachaMod.LOGGER.info("Disabled recipe {}", id);
                }
            }
            if (removed == 0) {
                return;
            }

            com.google.common.collect.Multimap<Object, RecipeHolder<?>> rebuilt =
                    com.google.common.collect.ArrayListMultimap.create();
            for (RecipeHolder<?> holder : replacement.values()) {
                rebuilt.put(holder.value().getType(), holder);
            }
            byNameField.set(manager, replacement);
            Field byTypeField = manager.getClass().getDeclaredField("byType");
            byTypeField.setAccessible(true);
            byTypeField.set(manager, rebuilt);
        } catch (ReflectiveOperationException | RuntimeException exception) {
            GachaMod.LOGGER.warn("Could not disable backpack recipes: {}", exception.toString());
        }
    }
}
