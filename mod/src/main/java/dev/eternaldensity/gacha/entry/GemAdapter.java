package dev.eternaldensity.gacha.entry;

import com.mojang.serialization.Dynamic;
import dev.eternaldensity.gacha.GachaMod;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.fml.ModList;

import java.lang.reflect.Method;

/**
 * Optional bridge to Apotheosis gems. Gems are one item with a data component,
 * so the generic item adapter cannot grant them; this reflective adapter asks
 * Apotheosis for a random gem stack instead.
 */
public final class GemAdapter {
    private static final String GEN_CONTEXT = "dev.shadowsoffire.apotheosis.tiers.GenContext";
    private static final String REGISTRY = "dev.shadowsoffire.apotheosis.socket.gem.GemRegistry";
    private static final String MOD_ID = "apotheosis";

    private GemAdapter() {
    }

    public static boolean available() {
        try {
            return ModList.get() != null && ModList.get().isLoaded(MOD_ID);
        } catch (Throwable ignored) {
            return false;
        }
    }

    public static boolean apply(Player player, Dynamic<?> adapter) {
        if (!available()) {
            return false;
        }
        try {
            Class<?> genContext = Class.forName(GEN_CONTEXT);
            Method dummy = genContext.getMethod("dummy", net.minecraft.util.RandomSource.class);
            Object context = dummy.invoke(null, player.getRandom());

            Class<?> registry = Class.forName(REGISTRY);
            Object instance = registry.getField("INSTANCE").get(null);
            Method create = registry.getMethod("createRandomGemStack", genContext);
            ItemStack stack = (ItemStack) create.invoke(instance, context);
            if (stack == null || stack.isEmpty()) {
                return false;
            }
            if (!player.addItem(stack)) {
                player.drop(stack, false);
            }
            return true;
        } catch (ReflectiveOperationException | RuntimeException exception) {
            GachaMod.LOGGER.warn("Apotheosis gem adapter could not grant a gem: {}", exception.toString());
            return false;
        }
    }
}
