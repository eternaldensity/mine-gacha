"use strict";
/* Seeded RNG (mulberry32) + helpers. Web-app-local seeds; trees generated
 * here are reproducible inside the app but intentionally not bit-identical
 * to the Python generator's output for the same seed. */
window.ChaosRng = (function () {
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function make(seed) {
    const rand = mulberry32(Number(seed) || 0);
    let spare = null;
    return {
      random() { return rand(); },
      int(n) { return Math.floor(rand() * n); },
      range(lo, hi) { return lo + rand() * (hi - lo); },
      pick(arr) { return arr[Math.floor(rand() * arr.length)]; },
      shuffle(arr) {
        for (let i = arr.length - 1; i > 0; i--) {
          const j = Math.floor(rand() * (i + 1));
          const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
        }
        return arr;
      },
      sample(arr, k) {
        const c = arr.slice();
        this.shuffle(c);
        return c.slice(0, k);
      },
      weighted(arr, weights) {
        let total = 0;
        for (const w of weights) total += w;
        let pick = rand() * total, acc = 0;
        for (let i = 0; i < arr.length; i++) {
          acc += weights[i];
          if (acc >= pick) return arr[i];
        }
        return arr[arr.length - 1];
      },
      gauss() {
        // Box-Muller with cached spare.
        if (spare !== null) { const v = spare; spare = null; return v; }
        let u = 0, v = 0;
        while (u === 0) u = rand();
        while (v === 0) v = rand();
        const m = Math.sqrt(-2.0 * Math.log(u));
        spare = m * Math.sin(2.0 * Math.PI * v);
        return m * Math.cos(2.0 * Math.PI * v);
      }
    };
  }

  // Knuth poisson sampler.
  function poisson(rng, mean) {
    const limit = Math.exp(-mean);
    let k = 0, p = 1.0;
    for (;;) {
      k += 1; p *= rng.random();
      if (p <= limit) return k - 1;
    }
  }

  return { make, poisson };
})();
