"use strict";
/* Chaos Casino: shared config + pure helpers. No dependencies. */
window.Casino = window.Casino || {};
(function (C) {
  C.W = 960; C.H = 540; C.WALL = 46;

  // Machine footprint + interaction/pickup radii.
  C.MW = 96; C.MH = 84;
  C.INTERACT_R = 100;
  C.PICKUP_R = 26;
  // Reel geometry: symbol row heights for the in-place spin animation.
  C.REEL_H = 30;   // slot reel window row
  C.GREEL_H = 28;  // gacha reel window row

  C.pmod = function (n, m) { return ((n % m) + m) % m; };

  // Tiny seeded PRNG so room layouts are stable across revisits.
  C.rng = function (seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  // Tiers mirror the desktop presets (Gacha.py min/avg/max).
  C.TIERS = [
    { id: "bronze",    label: "Bronze",    cost: 5,    pull: 2.5, color: "#9c7e5a", min: 0.1, avg: 1.3, max: 3.3,  minDepth: 0 },
    { id: "silver",    label: "Silver",    cost: 12,   pull: 3.0, color: "#aed1d1", min: 0.5, avg: 2.3, max: 4.3,  minDepth: 0 },
    { id: "gold",      label: "Gold",      cost: 30,   pull: 3.8, color: "#11d939", min: 1.5, avg: 3.3, max: 5.3,  minDepth: 2 },
    { id: "platinum",  label: "Platinum",  cost: 70,   pull: 4.5, color: "#1172d9", min: 2.5, avg: 4.3, max: 6.3,  minDepth: 4 },
    { id: "diamond",   label: "Diamond",   cost: 150,  pull: 5.2, color: "#6811d9", min: 3.5, avg: 5.3, max: 7.3,  minDepth: 6 },
    { id: "legendary", label: "Legendary", cost: 300,  pull: 6.0, color: "#f7d40a", min: 4.5, avg: 6.3, max: 8.3,  minDepth: 8 },
    { id: "mythical",  label: "Mythical",  cost: 600,  pull: 6.5, color: "#fc61ff", min: 5.5, avg: 7.3, max: 9.3,  minDepth: 11 },
    { id: "divine",    label: "Divine",    cost: 1200, pull: 7.5, color: "#ff8c00", min: 6.5, avg: 8.3, max: 10.0, minDepth: 14 },
  ];
  C.CATS = ["ability", "item", "skill", "trait", "familiar"];
  C.SYMS = ["7", "BAR", "★", "♦", "♥", "🪙"];

  C.tierById = id => C.TIERS.find(t => t.id === id);
  C.tierIdx = id => Math.max(0, C.TIERS.findIndex(t => t.id === id));
  // Highest rig tier a tinker rarity can build (house doesn't sell mythic+).
  C.rigTierFor = function (r) {
    if (r < 2) return "bronze";
    if (r < 3) return "silver";
    if (r < 4) return "gold";
    if (r < 5) return "platinum";
    if (r < 6) return "diamond";
    return "legendary";
  };
  C.allowedTiers = depth => C.TIERS.filter(t => depth >= t.minDepth);

  // Rarity colors/names match the desktop app tiers.
  C.rarityColor = function (r) {
    if (r < 1) return "#878d96"; if (r < 2) return "#9c7e5a"; if (r < 3) return "#aed1d1";
    if (r < 4) return "#11d939"; if (r < 5) return "#1172d9"; if (r < 6) return "#6811d9";
    if (r < 7) return "#f7d40a"; if (r < 8) return "#fc61ff"; if (r < 9) return "#ff8c00";
    return "#ff0000";
  };
  C.rarityName = function (r) {
    if (r < 1) return "Trash"; if (r < 2) return "Common"; if (r < 3) return "Uncommon";
    if (r < 4) return "Rare"; if (r < 5) return "Elite"; if (r < 6) return "Epic";
    if (r < 7) return "Legendary"; if (r < 8) return "Mythical"; if (r < 9) return "Divine";
    return "Transcendent";
  };

  C.fmtTime = function (s) {
    const m = Math.floor(s / 60), ss = Math.floor(s % 60);
    return m + ":" + String(ss).padStart(2, "0");
  };

  // Gacha pool, read lazily so load order with data/entries.js is forgiving.
  C.entries = function () {
    return (window.CHAOS_DATA && window.CHAOS_DATA.entries) || [];
  };
})(window.Casino);
