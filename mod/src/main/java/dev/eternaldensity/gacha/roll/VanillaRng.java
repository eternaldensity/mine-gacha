package dev.eternaldensity.gacha.roll;

import net.minecraft.util.RandomSource;

/** Delegates the engine's randomness to the level's {@link RandomSource}. */
public final class VanillaRng implements Rng {
    private final RandomSource source;

    public VanillaRng(RandomSource source) {
        this.source = source;
    }

    @Override
    public double nextDouble() {
        return source.nextDouble();
    }

    @Override
    public int nextInt(int bound) {
        return source.nextInt(bound);
    }
}
