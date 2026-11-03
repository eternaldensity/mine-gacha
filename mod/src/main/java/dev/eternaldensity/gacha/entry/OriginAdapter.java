package dev.eternaldensity.gacha.entry;

import com.mojang.serialization.Dynamic;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.neoforged.fml.ModList;

import java.lang.reflect.Method;

/**
 * Optional bridge to Neo Origins. The adapter is intentionally reflective: the
 * pack ships Neo Origins, but the mod's GameTest classpath and a pack without
 * the mod must still load and simply keep the ticket rather than crash.
 *
 * <p>The adapter payload is {@code {"type":"gacha:origin","origin":"neoorigins:merling",
 * "layer":"neoorigins:origin"}}.
 */
public final class OriginAdapter {
    private static final String SERVICE = "com.cyberday1.neoorigins.service.OriginChangeService";
    private static final String MOD_ID = "neoorigins";

    private OriginAdapter() {
    }

    public static boolean available() {
        try {
            return ModList.get() != null && ModList.get().isLoaded(MOD_ID);
        } catch (Throwable ignored) {
            return false;
        }
    }

    /** The origin layer named by an entry's adapter, or null for non-origin entries. */
    public static String layer(Entry entry) {
        return entry.adapter()
                .filter(adapter -> "gacha:origin".equals(adapter.get("type").asString("")))
                .map(adapter -> adapter.get("layer").asString(""))
                .orElse(null);
    }

    public static boolean apply(Player player, Dynamic<?> adapter) {
        if (!(player instanceof ServerPlayer serverPlayer) || !available()) {
            return false;
        }
        ResourceLocation origin = ResourceLocation.tryParse(adapter.get("origin").asString(""));
        ResourceLocation layer = ResourceLocation.tryParse(adapter.get("layer").asString(""));
        if (origin == null || layer == null) {
            return false;
        }
        try {
            Class<?> service = Class.forName(SERVICE);
            Class<?> modeClass = Class.forName(SERVICE + "$Mode");
            Object admin = null;
            for (Object constant : modeClass.getEnumConstants()) {
                if ("ADMIN".equals(constant.toString())) {
                    admin = constant;
                    break;
                }
            }
            if (admin == null) {
                return false;
            }
            Method set = service.getMethod(
                    "set", ServerPlayer.class, ResourceLocation.class, ResourceLocation.class, modeClass);
            Object result = set.invoke(null, serverPlayer, layer, origin, admin);
            String name = String.valueOf(result);
            if ("SUCCESS".equals(name) || "UNCHANGED".equals(name)) {
                return true;
            }
            dev.eternaldensity.gacha.GachaMod.LOGGER.warn(
                    "Neo Origins refused {} in {}: {}", origin, layer, name);
            return false;
        } catch (ReflectiveOperationException | RuntimeException exception) {
            dev.eternaldensity.gacha.GachaMod.LOGGER.warn(
                    "Neo Origins adapter could not set {} in {}; the ticket was kept",
                    origin, layer, exception);
            return false;
        }
    }
}
