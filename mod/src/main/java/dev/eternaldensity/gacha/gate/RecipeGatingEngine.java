package dev.eternaldensity.gacha.gate;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.Entry;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

public final class RecipeGatingEngine {
    private static final Map<String, String> GATES = new HashMap<>();
    private static boolean loaded = false;

    private RecipeGatingEngine() {
    }

    public static void register() {
        loadConfig();
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(RecipeGatingEngine::onRightClickBlock);
    }

    private static void loadConfig() {
        if (loaded) return;
        loaded = true;
        try {
            Path config = Path.of("config", "gacha", "recipe_gating.json");
            if (Files.isRegularFile(config)) {
                String text = Files.readString(config);
                com.google.gson.JsonObject obj = com.google.gson.JsonParser.parseString(text).getAsJsonObject();
                if (obj.has("gates") && obj.get("gates").isJsonObject()) {
                    com.google.gson.JsonObject gates = obj.getAsJsonObject("gates");
                    for (var e : gates.entrySet()) {
                        GATES.put(e.getKey(), e.getValue().getAsString());
                    }
                }
            }
        } catch (Exception ignored) {
        }
    }

    private static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        BlockPos pos = event.getPos();
        ResourceLocation blockId = BuiltInRegistries.BLOCK.getKey(player.level().getBlockState(pos).getBlock());
        if (blockId == null) return;
        String required = GATES.get(blockId.toString());
        if (required == null) return;
        if (!hasCluster(player, required)) {
            event.setCanceled(true);
            player.displayClientMessage(Component.literal(
                    "You need a " + required.replace('_', ' ') + " ability to use this."), true);
        }
    }

    private static boolean hasCluster(ServerPlayer player, String cluster) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.ownedEntries().isEmpty()) return false;
        var registry = player.level().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        for (String id : state.ownedEntries()) {
            ResourceLocation rl = ResourceLocation.tryParse(id);
            if (rl == null) continue;
            Entry entry = registry.get(rl);
            if (entry != null && entry.tags().contains(cluster)) {
                return true;
            }
        }
        return false;
    }
}
