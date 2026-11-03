"use strict";
/* Curse Roulette pre-run gamble (Doc rules): d20 -> tier -> random curse of
 * that severity from CHAOS_CURSES. Parametric house-edge modifiers plus
 * ticket rewards. Reach depth 3 to resolve: penalties lift (soul damage, i.e.
 * max HP, stays), +1 gold each. Max 3 curses per run.
 * Depends on: config, dom, state (runtime G). */
(function (C) {
  C.curseTier = function (roll) {
    if (roll <= 6) return "Minor";
    if (roll <= 13) return "Medium";
    if (roll <= 17) return "Major";
    if (roll <= 19) return "Severe";
    return "Ultimate";
  };

  C.curseRewards = function (tier) {
    if (tier === "Minor") return ["gold"];
    if (tier === "Medium") return ["gold", "gold"];
    if (tier === "Major") return ["gold"];
    if (tier === "Severe") return ["platinum"];
    return ["platinum", "gold"]; // Ultimate
  };

  // Tier-scaled magnitudes for fitted effects.
  const MAG = {
    Minor:    { sight: 1.25, hp: -1, pull: 1.15, speed: 0.95, coins: -25, cost: 1.15, threat: 0, guards: 0, wave: 50, cdr: 1.25, heal: 0.8, taken: 1.2, dealt: 0.9, alert: 1.25 },
    Medium:   { sight: 1.4, hp: -1, pull: 1.25, speed: 0.9, coins: -40, cost: 1.25, threat: 1, guards: 1, wave: 40, cdr: 1.5, heal: 0.65, taken: 1.35, dealt: 0.8, alert: 1.5 },
    Major:    { sight: 1.5, hp: -1, pull: 1.3, speed: 0.9, coins: -60, cost: 1.35, threat: 1, guards: 1, wave: 35, cdr: 1.75, heal: 0.5, taken: 1.5, dealt: 0.7, alert: 1.75 },
    Severe:   { sight: 1.7, hp: -2, pull: 1.4, speed: 0.85, coins: -80, cost: 1.5, threat: 1, guards: 2, wave: 30, cdr: 2, heal: 0.5, taken: 1.75, dealt: 0.6, alert: 2 },
    Ultimate: { sight: 2, hp: -2, pull: 1.5, speed: 0.8, coins: -100, cost: 1.6, threat: 2, guards: 2, wave: 25, cdr: 2.5, heal: 0.4, taken: 2, dealt: 0.5, alert: 2.25 },
  };

  // Curse text -> fitting mechanic. First match wins; order matters
  // (pacifist phrases before anything containing "kill", hexes before light).
  const FIT = [
    [/unable to kill|will not kill|cannot kill|pacifist|merciful|mercy|surrender/i, "merciful", M => ({ pacifist: true })],
    [/disarm|unarmed|empty hands|curse of arms|no weapon|without weapon/i, "disarmed", M => ({ dmgDealtMult: M.dealt })],
    [/do not heal|does not (heal|mend|close)|won't mend|healing .* ineffective|refus\w* to close|not heal|healing is .* usel/i, "wounded", M => ({ healMult: M.heal })],
    [/milk|drink|alcohol|food|hunger|glutton|appetite|starv|thirst|famine|famish/i, "starved", M => ({ regenOff: true, healMult: 0.9 })],
    [/naked|clothes|exhibition|nudity|unclothed|undressed/i, "exposed", M => ({ armorLock: true })],
    [/elemental|exorcism|weakness|vulnerable|hex|warded against/i, "hexed", M => ({ dmgTakenMult: M.taken, elementalOnly: true })],
    [/conspicuous|celebrity|notice|attention|fame|visible|memetic|menacing|obvious|notoriety|infamous|recogniz/i, "noticed", M => ({ sightMult: M.sight })],
    [/wallet|coins|gold|poor|tax|tithe|greed|debt|bankrupt|toll|tariff|house cut/i, "bled dry", M => ({ coins: M.coins, costMult: M.cost })],
    [/wound|bleed|frail|sick|rot|decay|disease|infection|parasite|anemia|plague|illness|nausea/i, "afflicted", M => ({ maxHp: M.hp })],
    [/slow slots|cooldown|restock|process/i, "sluggish", M => ({ cdrMult: M.cdr })],
    [/slow|sleep|tired|exhaust|fatigue|sloth|letharg|drowsy|insomnia|out of shape|unfit|obes|flabby|sedentary|overweight|couch potato/i, "leaden", M => ({ speedMult: M.speed })],
    [/hunt|wanted|marked|target|stalk|chas|pursu|enemy|enmity|nemesis|slayer/i, "hunted", M => ({ guardBonus: M.guards, threat0: M.threat })],
    [/loud|scream|shout|noise|honk|goose|shriek|alarm/i, "loud", M => ({ alertMult: M.alert })],
    [/doom|climax|apocalypse|narrative|destined|prophecy/i, "doomed", M => ({ maxHp: M.hp, threat0: M.threat })],
    [/night|sun|sunlight|vampire/i, "light-touched", M => ({ sightMult: M.sight })],
  ];

  // Exported for tests: which mechanic does this curse text earn?
  C.curseModFor = function (curse, tier) {
    const M = MAG[tier] || MAG.Minor;
    const text = (curse.label || "") + " " + (curse.desc || "");
    for (const [re, label, build] of FIT) {
      if (re.test(text)) return { label, apply: build(M) };
    }
    return null; // caller falls back to the random pool
  };

  const MODS = {
    Minor: [
      { label: "Frail Start", apply: { maxHp: -1 } },
      { label: "Slow Pockets", apply: { pullMul: 1.2 } },
      { label: "Entry Fee", apply: { coins: -25 } },
    ],
    Medium: [
      { label: "Heavy Feet", apply: { speedMult: 0.9 } },
      { label: "House Cut", apply: { costMult: 1.25 } },
      { label: "Wanted", apply: { waveT: 40 } },
    ],
    Major: [
      { label: "Marked", apply: { threat0: 1 } },
      { label: "Glass Soul", apply: { maxHp: -1, pullMul: 1.15 } },
      { label: "Crowded", apply: { guardBonus: 1 } },
    ],
    Severe: [
      { label: "Doomed", apply: { maxHp: -2 } },
      { label: "Hunted", apply: { guardBonus: 1, threat0: 1 } },
    ],
    Ultimate: [
      { label: "Condemned", apply: { threat0: 2, maxHp: -1 } },
      { label: "Infested", apply: { guardBonus: 2 } },
    ],
  };

  // Rolls queued on the death screen for the NEXT run (title is gone then).
  C.pendingCurses = [];

  function pool() {
    return (window.CHAOS_CURSES || []).filter(c => !c.nsfw);
  }

  // Shared d20 roll: tier + curse flavor + house-edge modifier, no side effects.
  function pickCurse() {
    const list = pool();
    if (!list.length) return null;
    const roll = 1 + Math.floor(Math.random() * 20);
    const tier = C.curseTier(roll);
    let cands = list.filter(c => c.sev === roll);
    if (!cands.length) {
      let best = 99;
      for (const c of list) best = Math.min(best, Math.abs(c.sev - roll));
      cands = list.filter(c => Math.abs(c.sev - roll) === best);
    }
    const curse = cands[Math.floor(Math.random() * cands.length)];
    const fit = C.curseModFor(curse, tier);
    const mod = fit || MODS[tier][Math.floor(Math.random() * MODS[tier].length)];
    return { curse, tier, roll, mod };
  }

  // Apply a picked curse to a live run state (fresh or title).
  function applyPick(G, pick) {
    const p = G.p, A = pick.mod.apply, applied = {};
    if (A.maxHp) {
      p.curseHp = (p.curseHp || 0) + A.maxHp;
      p.maxHp = C.maxHp();
      p.hp = Math.min(p.maxHp, Math.max(1, p.hp));
      applied.maxHp = A.maxHp;
    }
    if (A.pullMul) { p.pullMul *= A.pullMul; applied.pullMul = A.pullMul; }
    if (A.speedMult) { p.moveMult *= A.speedMult; applied.speedMult = A.speedMult; }
    if (A.coins) p.coins = Math.max(0, p.coins + A.coins);
    if (A.costMult) { G.costMult = (G.costMult || 1) * A.costMult; applied.costMult = A.costMult; }
    if (A.threat0) G.threat = Math.max(G.threat, A.threat0);
    if (A.waveT) G.waveT = Math.min(G.waveT, A.waveT);
    if (A.guardBonus) G.guardBonus = (G.guardBonus || 0) + A.guardBonus;
    if (A.sightMult) { p.sightMult *= A.sightMult; applied.sightMult = A.sightMult; }
    if (A.cdrMult) { p.cdrMult *= A.cdrMult; applied.cdrMult = A.cdrMult; }
    if (A.healMult) { p.healMult *= A.healMult; applied.healMult = A.healMult; }
    if (A.dmgTakenMult) { p.dmgTakenMult *= A.dmgTakenMult; applied.dmgTakenMult = A.dmgTakenMult; }
    if (A.elementalOnly) { p.dmgTakenElementalOnly = true; applied.elementalOnly = true; }
    if (A.dmgDealtMult) { p.dmgDealtMult *= A.dmgDealtMult; applied.dmgDealtMult = A.dmgDealtMult; }
    if (A.alertMult) { G.alertMult = (G.alertMult || 1) * A.alertMult; applied.alertMult = A.alertMult; }
    if (A.regenOff) { p.regenOff = true; applied.regenOff = true; }
    if (A.armorLock) { p.armorLock = true; applied.armorLock = true; }
    if (A.pacifist) { p.pacifist = true; applied.pacifist = true; }
    for (const tk of C.curseRewards(pick.tier)) p.tickets[tk] = (p.tickets[tk] || 0) + 1;
    G.curses.push({ label: pick.curse.label, tier: pick.tier, roll: pick.roll,
      desc: pick.curse.desc, edge: pick.mod.label, applied, resolved: false });
  }

  C.applyPick = applyPick;

  function curseCard(pick) {
    const flav = C.flavorShort(pick.curse.desc);
    C.showCard("🎲 " + pick.curse.label + " (" + pick.tier + ", d20 " + pick.roll + ")",
      "House edge: " + pick.mod.label + ". Reward: " +
        C.curseRewards(pick.tier).join(" + ") + " tickets. Reach depth 3 to resolve (+1 gold).",
      flav ? "“" + flav + "”" : "", 5000);
  }

  // Title screen: applies to the run waiting behind it.
  C.rollCurse = function () {
    const G = C.G;
    if (!G || !G.title) return;
    if (G.curses.length >= 3) {
      C.showCard("Enough curses", "Three is plenty. The house admires restraint.", "", 2000);
      return;
    }
    const pick = pickCurse();
    if (!pick) {
      C.showCard("No curses", "Curse data missing.", "", 2000);
      return;
    }
    applyPick(G, pick);
    C.audio.curse();
    curseCard(pick);
    C.renderCurseList();
    C.updateHud();
  };

  // Death screen: queues for the NEXT run (applied on respawn).
  C.rollCurseNext = function () {
    const G = C.G;
    if (!G || !G.over) return;
    if (C.pendingCurses.length >= 3) return;
    const pick = pickCurse();
    if (!pick) return;
    C.pendingCurses.push(pick);
    C.audio.curse();
    C.renderPendingList();
  };

  C.renderPendingList = function () {
    const box = C.el("deathCurses");
    if (!box) return;
    box.innerHTML = C.pendingCurses.length
      ? "Next run: " + C.pendingCurses.map(c =>
        "🎲 " + esc(c.curse.label) + " (" + c.tier + ": " + esc(c.mod.label) + ")").join(" · ")
      : "No curses queued: clean soul (coward).";
    const btn = C.el("curseNextBtn");
    if (btn) btn.disabled = C.pendingCurses.length >= 3;
  };

  C.resolveCurses = function () {
    const G = C.G;
    let n = 0;
    for (const c of G.curses) {
      if (c.resolved) continue;
      c.resolved = true; n++;
      G.p.tickets.gold++;
      const a = c.applied || {};
      if (a.pullMul) G.p.pullMul /= a.pullMul;
      if (a.speedMult) G.p.moveMult /= a.speedMult;
      if (a.maxHp) {
        G.p.curseHp = (G.p.curseHp || 0) - a.maxHp;
        G.p.maxHp = C.maxHp();
        G.p.hp = Math.min(G.p.maxHp, Math.max(1, G.p.hp));
      }
      if (a.costMult) G.costMult = (G.costMult || 1) / a.costMult;
      if (a.sightMult) G.p.sightMult /= a.sightMult;
      if (a.cdrMult) G.p.cdrMult /= a.cdrMult;
      if (a.healMult) G.p.healMult /= a.healMult;
      if (a.dmgTakenMult) G.p.dmgTakenMult /= a.dmgTakenMult;
      if (a.elementalOnly || a.regenOff || a.armorLock || a.pacifist) {
        // Flags persist while ANY unresolved curse still holds them.
        const rest = G.curses.filter(o => o !== c && !o.resolved).map(o => o.applied || {});
        const kept = k => rest.some(x => x[k]);
        if (a.elementalOnly && !kept("elementalOnly")) G.p.dmgTakenElementalOnly = false;
        if (a.regenOff && !kept("regenOff")) G.p.regenOff = false;
        if (a.armorLock && !kept("armorLock")) G.p.armorLock = false;
        if (a.pacifist && !kept("pacifist")) G.p.pacifist = false;
      }
      C.floater(G.p.x, G.p.y - 30, "curse lifted: " + c.label.slice(0, 18), "#11d939");
    }
    if (n) {
      C.showCard("Curses resolved ×" + n,
        "Depth 3! The house acknowledges you: +1 gold each. Soul damage stays.", "", 3500);
      C.renderCurseList();
    }
  };

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  C.renderCurseList = function () {
    const box = C.el("curseList");
    if (box) {
      const cs = C.G ? C.G.curses : [];
      box.innerHTML = cs.length
        ? cs.map(c => "<span class='tick'>" + (c.resolved ? "✓ " : "🎲 ") +
          esc(c.label) + " (" + c.tier + (c.edge ? ": " + esc(c.edge) : "") + ")</span>").join("")
        : "<span class='tick'>No curses: clean soul (coward).</span>";
    }
    const btn = C.el("curseBtn");
    if (btn) btn.disabled = (C.G ? C.G.curses.length : 0) >= 3;
  };

  C.renderBest = function () {
    const box = C.el("bestLine");
    if (!box) return;
    const b = C.getBest();
    box.textContent = (b.depth || b.time)
      ? "Best run: depth " + b.depth + " · " + C.fmtTime(b.time) + " · " + b.kills + " kills"
      : "No runs on record. Make the house proud.";
  };
})(window.Casino);
