package dev.eternaldensity.gacha.roll;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Port of the source roller, mirrored from {@code chaoslab/simulate.py}.
 *
 * <p>A ticket window is {@code (min, avg, max, flat)}. A rarity target is drawn
 * from the 0.1 grid inside the window with weight {@code 1 / 4^|avg - x|}
 * (exponent 1 and a wider entry window for flat tickets), then an entry within
 * {@code +/-0.2} of the target is chosen with the same bell weight. Draws are
 * bounded: 200 rarity attempts per category, 10 category attempts for a random
 * ticket, exactly as upstream.
 *
 * <p>Keeping this in step with the Python roller is part of the gate: the sweep
 * report and the game must not disagree about the odds.
 */
public final class RollEngine {
    public static final double STEP = 0.1;
    public static final double WINDOW = 0.2;
    public static final double FLAT_WINDOW = 1.0;
    public static final int RARITY_ATTEMPTS = 200;
    public static final int CATEGORY_ATTEMPTS = 10;

    private RollEngine() {
    }

    public record Candidate<T>(double rarity, T value) {
    }

    public record Draw<T>(double target, double rarity, T value) {
    }

    /** Draw a rarity target from the ticket window, mirroring {@code _rarity_pull}. */
    public static double sampleRarity(Rng rng, double min, double avg, double max, boolean flat) {
        if (!(max > min)) {
            throw new IllegalArgumentException("empty rarity window " + min + ".." + max);
        }
        int exponent = flat ? 1 : 4;
        List<Double> values = new ArrayList<>();
        List<Double> weights = new ArrayList<>();
        for (double x = min; x < max; x += STEP) {
            values.add(x);
            weights.add(bellWeight(exponent, avg, x));
        }
        double total = 0.0;
        for (double weight : weights) {
            total += weight;
        }
        double roll = rng.nextDouble() * total;
        for (int index = 0; index < values.size(); index++) {
            roll -= weights.get(index);
            if (roll <= 0.0) {
                return values.get(index) + STEP;
            }
        }
        return values.get(values.size() - 1) + STEP;
    }

    /**
     * Draw one entry from a rarity-sorted pool. Empty when no entry sits inside
     * the window after {@value RARITY_ATTEMPTS} attempts.
     */
    public static <T> Optional<Draw<T>> draw(
            Rng rng, double min, double avg, double max, boolean flat, List<Candidate<T>> pool) {
        if (pool.isEmpty()) {
            return Optional.empty();
        }
        int exponent = flat ? 1 : 4;
        double window = flat ? FLAT_WINDOW : WINDOW;
        for (int attempt = 0; attempt < RARITY_ATTEMPTS; attempt++) {
            double target = sampleRarity(rng, min, avg, max, flat);
            int low = lowerBound(pool, target - window);
            int high = upperBound(pool, target + window);
            if (low >= high) {
                continue;
            }
            Candidate<T> chosen = pick(rng, exponent, avg, pool.subList(low, high));
            return Optional.of(new Draw<>(target, chosen.rarity(), chosen.value()));
        }
        return Optional.empty();
    }

    /**
     * Draw across categories like a Random ticket: pick a category uniformly,
     * try it, and repeat for up to {@value CATEGORY_ATTEMPTS} category picks.
     */
    public static <T> Optional<Draw<T>> drawRandomCategory(
            Rng rng,
            double min,
            double avg,
            double max,
            boolean flat,
            Map<String, List<Candidate<T>>> pools,
            List<String> categories) {
        if (categories.isEmpty()) {
            return Optional.empty();
        }
        for (int attempt = 0; attempt < CATEGORY_ATTEMPTS; attempt++) {
            String category = categories.get(rng.nextInt(categories.size()));
            List<Candidate<T>> pool = pools.getOrDefault(category, List.of());
            Optional<Draw<T>> draw = draw(rng, min, avg, max, flat, pool);
            if (draw.isPresent()) {
                return draw;
            }
        }
        return Optional.empty();
    }

    private static double bellWeight(int exponent, double avg, double rarity) {
        return 1.0 / Math.pow(exponent, Math.abs(avg - rarity));
    }

    private static <T> Candidate<T> pick(
            Rng rng, int exponent, double avg, List<Candidate<T>> candidates) {
        double total = 0.0;
        for (Candidate<T> candidate : candidates) {
            total += bellWeight(exponent, avg, candidate.rarity());
        }
        double roll = rng.nextDouble() * total;
        for (Candidate<T> candidate : candidates) {
            roll -= bellWeight(exponent, avg, candidate.rarity());
            if (roll <= 0.0) {
                return candidate;
            }
        }
        return candidates.get(candidates.size() - 1);
    }

    /** First index whose rarity is >= value; the pool is sorted ascending. */
    private static <T> int lowerBound(List<Candidate<T>> pool, double value) {
        int low = 0;
        int high = pool.size();
        while (low < high) {
            int mid = (low + high) >>> 1;
            if (pool.get(mid).rarity() < value) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return low;
    }

    /** First index whose rarity is > value; the pool is sorted ascending. */
    private static <T> int upperBound(List<Candidate<T>> pool, double value) {
        int low = 0;
        int high = pool.size();
        while (low < high) {
            int mid = (low + high) >>> 1;
            if (pool.get(mid).rarity() <= value) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return low;
    }
}
