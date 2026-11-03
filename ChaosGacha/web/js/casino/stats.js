"use strict";
/* Coherent character stats: every prize/curse hooks into named numeric
 * stats; derived values (move, pull time, HP, cooldowns, mana...) come from
 * one formula each. Bases are tuned so a fresh run matches old tuning.
 * Depends on: config (namespace only). */
(function (C) {
  // Base 10 each. SPD move · DEX pull speed · STR inventory · END health ·
  // FOC cooldowns + mana · LCK luck · PWR damage.
  C.BASE_STATS = { SPD: 10, DEX: 10, STR: 10, END: 10, FOC: 10, LCK: 10, PWR: 10, CHA: 10 };
  C.STAT_NAMES = ["SPD", "DEX", "STR", "END", "FOC", "LCK", "PWR", "CHA"];

  C.STAT_BLURB = {
    SPD: "move speed", DEX: "pull speed", STR: "inventory size",
    END: "extra health", FOC: "cooldowns + mana", LCK: "luck", PWR: "damage",
    CHA: "charm: longer dominates, wider talks, friendlier pets",
  };

  const S = () => (C.G && C.G.p.stats) || C.BASE_STATS;
  const get = k => S()[k] || 10;

  C.moveSpeed = () => 100 + 6.5 * get("SPD"); // SPD 10 -> 165
  C.pullMul = () => 1 / (1 + 0.08 * (get("DEX") - 10)); // DEX 11 -> x0.93
  C.maxHp = () => Math.max(1,
    3 + Math.floor((get("END") - 10) / 2) + ((C.G && C.G.p.curseHp) || 0));
  C.cdr = () => Math.min(0.35, 0.02 * (get("FOC") - 10));
  C.luck = () => get("LCK") - 10;
  C.coinMult = () => 1 + ((C.G && C.G.p.coinBonus) || 0);
  // Temporal drag: time-affinity prizes slow all guards by a fraction.
  // Unlike SPD/DEX/FOC/roll (which speed YOU up), this slows THEM down.
  C.enemySlowMult = function () {
    return 1 - Math.min(0.30, ((C.G && C.G.p.timeBonus) || 0));
  };
  // Loot-grab radius: base + mule aura (+40 while a mule is active) +
  // stacking pickupBonus from magnet/fetch prizes (cap applied on grant).
  C.pickupRadius = function () {
    const base = C.PICKUP_R || 26;
    const mule = (typeof C.activeRole === "function" && C.activeRole("mule")) ? 40 : 0;
    return base + mule + (((C.G && C.G.p.pickupBonus) || 0));
  };
  C.satCap = () => 3 + Math.floor((get("STR") - 10) / 2);
  C.ammoMax = () => 20 + 2 * (get("STR") - 10);
  C.manaMax = () => 60 + 5 * (get("FOC") - 10);
  C.manaRegen = () => 5 + 0.5 * (get("FOC") - 10);

  C.chaMult = () => 1 + 0.06 * (((C.G && C.G.p.stats.CHA) || 10) - 10);
  C.petMult = () => 1 + 0.03 * (((C.G && C.G.p.stats.CHA) || 10) - 10);
  C.pacifyRange = () => 200 + 12 * (((C.G && C.G.p.stats.CHA) || 10) - 10);
  C.tauntRange = () => 420 + 15 * (((C.G && C.G.p.stats.CHA) || 10) - 10);

  C.MANA_COSTS = {
    bolt: 6, dash: 8, heal: 14, wave: 12, beam: 14, nova: 20, lobbed: 18,
    wall: 16, summon: 22, survey: 8, betray: 14, taunt: 4, pacify: 10,
    salvage: 4, tinker: 0, surge: 18, chrono: 26,
  };

  // Sync effective damage from weapon + PWR (call on equip or PWR change).
  C.syncDmg = function () {
    const p = C.G.p;
    p.dmg = (p.weapon ? p.weapon.dmg : 1) + 0.25 * (get("PWR") - 10);
  };

  // Bump a stat (floor 1) with END/STR side effects. Central choke point.
  C.modStat = function (stat, delta) {
    const p = C.G.p;
    const oldMax = C.maxHp();
    p.stats[stat] = Math.max(1, (p.stats[stat] || 10) + delta);
    if (stat === "END") {
      p.maxHp = C.maxHp();
      p.hp = Math.min(p.maxHp, Math.max(1, p.hp + (p.maxHp - oldMax)));
    }
    if (stat === "PWR") C.syncDmg();
    C.updateHud();
  };
})(window.Casino);
