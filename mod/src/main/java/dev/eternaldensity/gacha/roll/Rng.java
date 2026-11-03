package dev.eternaldensity.gacha.roll;

/**
 * The randomness surface the roll engine needs.
 *
 * <p>Deliberately not Minecraft's {@code RandomSource}: the engine stays plain
 * Java so its behaviour is unit-testable without a game. In game the adapter
 * delegates straight to {@code RandomSource}.
 */
public interface Rng {
    double nextDouble();

    int nextInt(int bound);
}
