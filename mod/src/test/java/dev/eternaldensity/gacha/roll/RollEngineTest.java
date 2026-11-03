package dev.eternaldensity.gacha.roll;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RollEngineTest {
    private static Rng rng(long seed) {
        Random random = new Random(seed);
        return new Rng() {
            @Override
            public double nextDouble() {
                return random.nextDouble();
            }

            @Override
            public int nextInt(int bound) {
                return random.nextInt(bound);
            }
        };
    }

    @Test
    void rarityStaysInsideTheWindow() {
        int total = 20000;
        int inside = 0;
        for (int i = 0; i < total; i++) {
            double rarity = RollEngine.sampleRarity(rng(i), 0.1, 1.3, 3.3, false);
            if (rarity >= 0.1 && rarity <= 3.3 + 1e-6) {
                inside++;
            }
        }
        assertEquals(total, inside, "every draw must stay on the 0.1 grid inside the window");
    }

    @Test
    void rarityAveragesNearTheWindowCentre() {
        int total = 20000;
        double sum = 0.0;
        for (int i = 0; i < total; i++) {
            sum += RollEngine.sampleRarity(rng(i), 0.1, 1.3, 3.3, false);
        }
        double mean = sum / total;
        assertTrue(mean > 1.0 && mean < 1.9, "mean was " + mean);
    }

    @Test
    void flatRollsAreWider() {
        int total = 5000;
        double bronzeVariance = 0.0;
        double wildVariance = 0.0;
        for (int i = 0; i < total; i++) {
            double bronze = RollEngine.sampleRarity(rng(i), 0.1, 1.3, 3.3, false);
            double wild = RollEngine.sampleRarity(rng(i + 100000), 1.0, 5.0, 10.0, true);
            bronzeVariance += Math.pow(bronze - 1.3, 2);
            wildVariance += Math.pow(wild - 5.0, 2);
        }
        assertTrue(wildVariance / total > bronzeVariance / total, "wild must be wider than bronze");
    }

    @Test
    void drawRespectsTheEntryWindow() {
        List<RollEngine.Candidate<String>> pool = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            pool.add(new RollEngine.Candidate<>(i * 0.1, "entry-" + i));
        }
        pool.sort(Comparator.comparingDouble(RollEngine.Candidate::rarity));
        for (int i = 0; i < 1000; i++) {
            java.util.Optional<RollEngine.Draw<String>> draw = RollEngine.draw(rng(i), 0.1, 1.3, 3.3, false, pool);
            if (draw.isPresent()) {
                assertTrue(Math.abs(draw.get().target() - draw.get().rarity()) <= 0.2 + 1e-9,
                        "draw target and entry rarity must be within the 0.2 window");
            }
        }
    }

    @Test
    void tierBoundariesMatchTheSourceBands() {
        assertEquals("Trash", Tiers.forRarity(0.5));
        assertEquals("Common", Tiers.forRarity(1.0));
        assertEquals("Uncommon", Tiers.forRarity(2.0));
        assertEquals("Rare", Tiers.forRarity(3.0));
        assertEquals("Elite", Tiers.forRarity(4.0));
        assertEquals("Epic", Tiers.forRarity(5.0));
        assertEquals("Legendary", Tiers.forRarity(6.0));
        assertEquals("Mythical", Tiers.forRarity(7.0));
        assertEquals("Divine", Tiers.forRarity(8.0));
        assertEquals("Transcendent", Tiers.forRarity(9.9));
    }

    @Test
    void drawsAreDeterministicForTheSameSeed() {
        Random left = new Random(42);
        Random right = new Random(42);
        Rng rngLeft = new Rng() {
            @Override
            public double nextDouble() {
                return left.nextDouble();
            }

            @Override
            public int nextInt(int bound) {
                return left.nextInt(bound);
            }
        };
        Rng rngRight = new Rng() {
            @Override
            public double nextDouble() {
                return right.nextDouble();
            }

            @Override
            public int nextInt(int bound) {
                return right.nextInt(bound);
            }
        };
        for (int i = 0; i < 50; i++) {
            assertEquals(RollEngine.sampleRarity(rngLeft, 0.1, 1.3, 3.3, false),
                    RollEngine.sampleRarity(rngRight, 0.1, 1.3, 3.3, false));
        }
    }
}
