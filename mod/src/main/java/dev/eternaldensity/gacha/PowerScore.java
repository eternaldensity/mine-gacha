package dev.eternaldensity.gacha;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;

import dev.eternaldensity.gacha.entry.Entry;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Config-driven Power Score (PROJECT_PLAN.md sections 6.9 and 7 row 26, D3).
 *
 * <p>The config is read from {@code config/gacha/power_score.json} in the instance
 * working directory, falling back to the jar-embedded default and writing it out
 * on first use. The default is the D3-answered vector.
 */
public final class PowerScore {
    public record Config(
            double gearWeight, double entriesWeight, double stageWeight,
            double weightRange,
            double weightMin, double weightMax,
            double gearRef, int entriesRef,
            double scoreMin, double scoreMax) {
    }

    private PowerScore() {
    }

    public static Config load() {
        Path file = Paths.get("config", "gacha", "power_score.json");
        if (Files.exists(file)) {
            try {
                return parse(Files.readString(file));
            } catch (Exception e) {
                GachaMod.LOGGER.warn("Failed to read power score config from {}; using default", file, e);
            }
        }
        Config cfg = loadDefault();
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, toJson(cfg));
        } catch (IOException e) {
            GachaMod.LOGGER.warn("Could not write default power score config to {}", file, e);
        }
        return cfg;
    }

    public static Config loadDefault() {
        String json = readResource("/gacha/power_score.json");
        if (json == null) {
            return new Config(0.36, 0.36, 0.28, 0.10, 0.05, 0.80, 538.4, 667, 0.0, 1.0);
        }
        return parse(json);
    }

    private static Config parse(String json) {
        JsonObject obj = JsonParser.parseString(json).getAsJsonObject();
        JsonObject w = obj.getAsJsonObject("weights");
        JsonArray bounds = obj.getAsJsonArray("weight_bounds");
        JsonObject ref = obj.getAsJsonObject("reference");
        JsonArray clamp = obj.getAsJsonArray("score_clamp");
        return new Config(
                w.get("gear").getAsDouble(),
                w.get("entries").getAsDouble(),
                w.get("stage").getAsDouble(),
                obj.get("weight_range").getAsDouble(),
                bounds.get(0).getAsDouble(),
                bounds.get(1).getAsDouble(),
                ref.get("gear").getAsDouble(),
                ref.get("entries").getAsInt(),
                clamp.get(0).getAsDouble(),
                clamp.get(1).getAsDouble()
        );
    }

    private static String toJson(Config cfg) {
        return "{\n"
                + "  \"weights\": {\"gear\": " + cfg.gearWeight + ", \"entries\": " + cfg.entriesWeight
                + ", \"stage\": " + cfg.stageWeight + "},\n"
                + "  \"weight_range\": " + cfg.weightRange + ",\n"
                + "  \"weight_bounds\": [" + cfg.weightMin + ", " + cfg.weightMax + "],\n"
                + "  \"reference\": {\"gear\": " + cfg.gearRef + ", \"entries\": " + cfg.entriesRef + "},\n"
                + "  \"score_clamp\": [" + cfg.scoreMin + ", " + cfg.scoreMax + "]\n"
                + "}\n";
    }

    private static String readResource(String path) {
        try (var in = PowerScore.class.getResourceAsStream(path)) {
            if (in == null) return null;
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Compute the score from the owned entry set. Gear is the summed rarity of
     * owned item-kind entries; entries is the owned count; stage is a proxy
     * fraction (owned / reference) until feats drive real progression.
     */
    public static double compute(Config cfg, Registry<Entry> registry, PlayerData data) {
        double gear = 0.0;
        for (String id : data.ownedEntries()) {
            ResourceLocation rl = ResourceLocation.tryParse(id);
            if (rl == null) continue;
            Entry entry = registry.getOptional(rl).orElse(null);
            if (entry != null && "item".equals(entry.kind())) {
                gear += entry.rarity();
            }
        }
        double gearNorm = Math.min(1.0, gear / cfg.gearRef());
        double entriesNorm = Math.min(1.0, (double) data.ownedEntries().size() / cfg.entriesRef());
        double stageNorm = Math.min(1.0, (double) data.ownedEntries().size() / cfg.entriesRef());
        double score = cfg.gearWeight() * gearNorm
                + cfg.entriesWeight() * entriesNorm
                + cfg.stageWeight() * stageNorm;
        return Math.max(cfg.scoreMin(), Math.min(cfg.scoreMax(), score));
    }
}
