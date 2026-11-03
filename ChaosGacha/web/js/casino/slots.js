"use strict";
/* Payout tables: slot odds/symbols + gacha rolls via the shared engine.
 * Depends on: config, state (runtime G). */
(function (C) {
  C.slotCost = function (t) {
    return Math.max(1, Math.round(t.cost * (1 - C.G.p.discount) * (C.G.costMult || 1)));
  };

  C.rollSlotPayout = function (t) {
    const luck = (C.G && C.luck && C.luck()) || 0;
    const cm = (C.coinMult && C.coinMult()) || 1;
    const r = Math.random();
    const idx = C.TIERS.indexOf(t);
    const up = C.TIERS[Math.min(C.TIERS.length - 1, idx + 1)];
    const ticketFor = (rr) => {
      if (rr < 0.7) return t.id;
      if (rr < 0.9 && idx > 0) return C.TIERS[idx - 1].id;
      return up.id;
    };
    if (r < 0.01 + 0.005 * luck) return { kind: "jackpot", coins: Math.round(t.cost * 10 * cm), ticket: t.id };
    if (r < 0.31) {
      let tk = ticketFor(Math.random());
      // Luck can bump the ticket up one tier.
      if (luck > 0 && Math.random() < 0.05 * luck) {
        const i = C.TIERS.findIndex(x => x.id === tk);
        tk = C.TIERS[Math.min(C.TIERS.length - 1, i + 1)].id;
      }
      return { kind: "ticket", ticket: tk };
    }
    if (r < 0.86) return { kind: "coins", coins: Math.round(t.cost * (0.6 + Math.random() * 1.6) * cm) };
    return { kind: "nothing" };
  };

  // Rigged display symbols for a predetermined payout.
  C.symbolsFor = function (pay) {
    const S = C.SYMS;
    if (pay.kind === "jackpot") return ["7", "7", "7"];
    if (pay.kind === "ticket") {
      const s = S[1 + Math.floor(Math.random() * 4)];
      return [s, s, s];
    }
    if (pay.kind === "coins") {
      const a = S[Math.floor(Math.random() * S.length)];
      let b = S[Math.floor(Math.random() * S.length)];
      if (b === a) b = S[(S.indexOf(a) + 2) % S.length];
      return Math.random() < 0.4 ? [a, a, b] : [a, b, "🪙"];
    }
    const a = S[Math.floor(Math.random() * S.length)];
    const b = S[Math.floor(Math.random() * S.length)];
    let c = S[Math.floor(Math.random() * S.length)];
    if (a === b && b === c) c = S[(S.indexOf(c) + 1) % S.length];
    return [a, b, c];
  };

  C.gachaRoll = function (tierId, cat) {
    const t = C.tierById(tierId);
    try {
      const pool = C.entries();
      if (!pool.length || !window.ChaosGacha) throw new Error("no data");
      const res = window.ChaosGacha.roll(pool, null, cat, t.min, t.avg, t.max,
        { hideNsfw: true, hideNoncon: true }, Math.random);
      let strip = [];
      try {
        strip = window.ChaosGacha.drawStrip(pool, cat, t.min, t.avg, t.max,
          { hideNsfw: true, hideNoncon: true }, 14, Math.random);
      } catch (e) { strip = []; }
      return { res, strip };
    } catch (e) {
      const stub = {
        category: cat === "random" ? "item" : cat, name: tierId + " trinket",
        rarity: t.avg, source: "Casino", description: "Fallback prize (data missing).", odds: 0,
      };
      return { res: stub, strip: [] };
    }
  };
})(window.Casino);
