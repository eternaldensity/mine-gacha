"use strict";
/* Combat: player attacks, guards, pets, projectiles, death/legacy.
 * Depends on: config, dom, state, legacy, prizes (runtime). */
(function (C) {
  C.tryAttack = function () {
    const p = C.G.p;
    if (!p.weapon || p.atkCd > 0 || C.G.over) return;
    p.atkCd = 0.45 * (p.weapon.rate || 1);
    if (p.weapon.ranged) {
      if ((p.ammo || 0) <= 0) {
        C.floater(p.x, p.y - 24, "out of ammo!", "#ff5555");
        C.audio.dry();
        p.atkCd = 0.3;
        return;
      }
      p.ammo -= 1;
      const g = C.nearestGuard(420);
      const a = g ? Math.atan2(g.y - p.y, g.x - p.x) : (p.facing || 0);
      const angs = p.weapon.pattern === "spread" ? [-0.16, 0, 0.16] : [0];
      for (const off of angs) {
        C.projs.push({
          x: p.x, y: p.y, vx: Math.cos(a + off) * 520, vy: Math.sin(a + off) * 520,
          dmg: (C.playerDmg(p.dmg, p.weapon.element) + (p.rangedBonus || 0)) * (p.weapon.bane || 1), foe: false, life: 0.8, element: p.weapon.element, pierce: !!p.weapon.pierce,
        });
      }
    } else {
      const claws = p.stance && p.stance.kind === "claws";
      const dmg = C.playerDmg(p.dmg + (claws ? 2 : 0), p.weapon.element) *
        (p.weapon.bane || 1) + (p.meleeBonus || 0);
      let fed = false;
      for (const gd of [...C.curRoom().guards]) {
        if (Math.hypot(gd.x - p.x, gd.y - p.y) < p.range + 14) {
          if (p.weapon.knockback) {
            const a = Math.atan2(gd.y - p.y, gd.x - p.x) || 0;
            const room = C.curRoom();
            const fx = C.collideCircle(gd.x + Math.cos(a) * p.weapon.knockback,
              gd.y + Math.sin(a) * p.weapon.knockback, 9, C.solids(room));
            gd.x = fx[0]; gd.y = fx[1];
          }
          const mopts = {};
          if (p.weapon.pierce) mopts.pierce = true;
          if (p.wrecker) mopts.wrecker = p.wrecker;
          if (C.damageGuard(gd, dmg, p.weapon.element, false, mopts)) fed = true;
        }
      }
      if (claws) {
        p.atkCd *= 0.5; // flurry rate
        if (fed && p.hp < p.maxHp) {
          p.hp += 1;
          C.floater(p.x, p.y - 24, "+1 feed", "#ff9c41");
        }
      }
      C.G.shake = 0.12;
    }
  };

  // Fire a slotted active power. Cooldown-gated; heal won't waste on full HP.
  // Point-segment distance for beam hits.
  function segDist(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const l2 = dx * dx + dy * dy;
    let t = l2 ? ((px - x1) * dx + (py - y1) * dy) / l2 : 0;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  C.runActive = function (i) {
    const p = C.G.p, ab = p.slots[i];
    if (!ab || ab.cdLeft > 0 || C.G.over || C.G.title) return false;
    const cost = C.MANA_COSTS[ab.op] || 0;
    if (p.mana < cost) {
      C.floater(p.x, p.y - 24, "drained!", "#7df9ff");
      C.audio.dry();
      return false;
    }
    p.mana -= cost;
    const armed = p.weapon ? 1 : 0;
    if (ab.op === "bolt") {
      const g = C.nearestGuard(460);
      const a = g ? Math.atan2(g.y - p.y, g.x - p.x) : p.facing;
      const dmg = C.playerDmg(ab.power + armed, ab.element);
      const angs = ab.element === "venom" ? [-0.18, 0, 0.18] : [0];
      for (const off of angs) {
        C.projs.push({
          x: p.x, y: p.y, vx: Math.cos(a + off) * 560, vy: Math.sin(a + off) * 560,
          dmg, foe: false, life: 0.9, element: ab.element,
        });
      }
    } else if (ab.op === "nova") {
      C.detonate(p.x, p.y, 135, C.playerDmg(ab.power + armed, ab.element), ab.element);
    } else if (ab.op === "wave") {
      // Cone shove: damage + radial knockback + element in front of you.
      const g = C.nearestGuard(460);
      const a = g ? Math.atan2(g.y - p.y, g.x - p.x) : p.facing;
      const dmg = C.playerDmg(ab.power + armed, ab.element);
      const room = C.curRoom();
      for (const gd of [...room.guards]) {
        const d = Math.hypot(gd.x - p.x, gd.y - p.y);
        if (d > 175) continue;
        let da = Math.atan2(gd.y - p.y, gd.x - p.x) - a;
        while (da > Math.PI) da -= Math.PI * 2;
        while (da < -Math.PI) da += Math.PI * 2;
        if (Math.abs(da) > 0.5) continue;
        const pa = Math.atan2(gd.y - p.y, gd.x - p.x) || 0;
        const fx = C.collideCircle(gd.x + Math.cos(pa) * 70, gd.y + Math.sin(pa) * 70,
          9, C.solids(room));
        gd.x = fx[0]; gd.y = fx[1];
        C.damageGuard(gd, dmg, ab.element);
      }
      C.rings.push({ x: p.x, y: p.y, age: 0, max: 0.25, r: 70 });
    } else if (ab.op === "beam") {
      const g = C.nearestGuard(460);
      const a = g ? Math.atan2(g.y - p.y, g.x - p.x) : p.facing;
      const x2 = p.x + Math.cos(a) * 340, y2 = p.y + Math.sin(a) * 340;
      C.beams.push({ x1: p.x, y1: p.y, x2, y2, age: 0, max: 0.25 });
      const dmg = C.playerDmg(ab.power + armed, ab.element);
      for (const gd of [...C.curRoom().guards]) {
        if (segDist(gd.x, gd.y, p.x, p.y, x2, y2) < 16) {
          C.damageGuard(gd, dmg, ab.element);
        }
      }
      C.G.shake = 0.1;
    } else if (ab.op === "lobbed") {
      // Shell lands late: red telegraph now, boom in 0.6s.
      const g = C.nearestGuard(520);
      const tx = g ? g.x : p.x + Math.cos(p.facing) * 200;
      const ty = g ? g.y : p.y + Math.sin(p.facing) * 200;
      C.delayed.push({
        x: tx, y: ty, t: 0.6, r: 95,
        dmg: C.playerDmg(ab.power + armed, ab.element), element: ab.element,
      });
    } else if (ab.op === "wall") {
      // Conjured cover perpendicular to facing; blocks guards + foe shots.
      const horiz = Math.abs(Math.cos(p.facing)) > Math.abs(Math.sin(p.facing));
      const w = horiz ? 16 : 110, h = horiz ? 110 : 16;
      const room = C.curRoom();
      room.tempWalls.push({
        x: p.x + Math.cos(p.facing) * 52 - w / 2,
        y: p.y + Math.sin(p.facing) * 52 - h / 2,
        w, h, t: ab.power,
      });
      C.floater(p.x, p.y - 30, "wall up!", "#7df9ff");
    } else if (ab.op === "summon") {
      p.pets.push({
        name: ab.name, role: ab.role, element: ab.element,
        dmg: ab.power, cd: 0, cdMax: 1.1,
        temp: true, dur: ab.dur, stationary: !!ab.stationary,
        x: p.x, y: p.y,
      });
      C.floater(p.x, p.y - 30, "summoned!", "#c77dff");
      C.updateHud();
    } else if (ab.op === "surge") {
      p.surge = { t: ab.dur, dmgMult: ab.dmgMult, spdMult: ab.spdMult };
      C.floater(p.x, p.y - 30, "SURGING", "#ff5555");
    } else if (ab.op === "chrono") {
      // Time bubble: everything nearby slows to a crawl.
      const room = C.curRoom();
      for (const gd of [...room.guards]) {
        if (Math.hypot(gd.x - p.x, gd.y - p.y) < 230) {
          C.applyStatus(gd, "slow", ab.power, 0.35);
        }
      }
      C.rings.push({ x: p.x, y: p.y, age: 0, max: 0.4, r: 230 });
      C.G.shake = 0.12;
    } else if (ab.op === "salvage") {
      const room = C.curRoom();
      let best = null, bd = 115;
      for (const m of room.machines) {
        const d = Math.hypot(m.x - p.x, m.y - p.y);
        if (d < bd) { bd = d; best = m; }
      }
      if (!best) return false; // nothing in reach: don't burn the cooldown
      const wasPull = !!best.pull;
      const parts = (C.tierIdx(best.tier) + 1) + 2;
      // Remove first so damageMachine's own drop doesn't double-pay.
      room.machines.splice(room.machines.indexOf(best), 1);
      room.pickups.push({ kind: "parts", amount: parts, x: best.x, y: best.y, bob: 0, age: 0 });
      room.scorch.push({ x: best.x, y: best.y, age: 0 });
      C.floater(best.x, best.y - 50, "🔧 +" + parts + "🧩" + (wasPull ? " (pull lost)" : ""), "#ffe066");
      C.G.shake = Math.max(C.G.shake, 0.1);
    } else if (ab.op === "tinker") {
      C.openDraft({ kind: "build", ab });
      return true; // menu handles the cooldown on build, not on open
    } else if (ab.op === "survey") {
      p.surveyT = 20 + ab.rarity * 2;
      const dirs = [["N", 0, -1], ["S", 0, 1], ["W", -1, 0], ["E", 1, 0]];
      const lines = dirs.map(([k, dx, dy]) => {
        const info = C.neighborInfo(dx, dy);
        return k + ": depth " + info.depth + ", " + info.guards + " guards" +
          (info.best ? ", best " + info.best.label : "");
      });
      C.showCard("🔭 " + ab.name + " (" + Math.round(p.surveyT) + "s intel)",
        lines.join(" · "), "Doors now tag guards + best machine.", 5000);
    } else if (ab.op === "betray") {
      const room = C.curRoom();
      let best = null, bd = 220;
      for (const gd of room.guards) {
        const d = Math.hypot(gd.x - p.x, gd.y - p.y);
        if (d < bd) { bd = d; best = gd; }
      }
      if (!best) return false; // no mark in reach: don't burn the cooldown
      best.possessed = (8 + ab.rarity * 0.5) * C.chaMult();
      best.chase = true;
      C.floater(best.x, best.y - 30, "⁉ turned!", "#c77dff");
    } else if (ab.op === "stance") {
      const dur = (ab.kind === "wings" ? 8 : 12) + (p.stanceBonus || 0);
      p.stance = { kind: ab.kind, t: dur, dur };
      C.floater(p.x, p.y - 30,
        ab.kind === "claws" ? "CLAWS OUT" : ab.kind === "wings" ? "WINGS" : "CARAPACE", "#ff9c41");
    } else if (ab.op === "taunt") {
      const room = C.curRoom();
      room.alert = 5;
      for (const gd of room.guards) {
        if (!gd.pacified && Math.hypot(gd.x - p.x, gd.y - p.y) < C.tauntRange()) gd.chase = true;
      }
      C.floater(p.x, p.y - 30, "COME AT ME", "#ff5555");
    } else if (ab.op === "pacify") {
      const room = C.curRoom();
      let best = null, bd = C.pacifyRange();
      for (const gd of room.guards) {
        if (gd.pacified) continue;
        const d = Math.hypot(gd.x - p.x, gd.y - p.y);
        if (d < bd) { bd = d; best = gd; }
      }
      if (!best) return false; // no mark in reach: don't burn the cooldown
      best.pacified = true;
      best.chase = false;
      C.floater(best.x, best.y - 30, "♪", "#11d939");
    } else if (ab.op === "veil") {
      p.cloakT = 3 + ab.rarity * 0.2;
      C.floater(p.x, p.y - 30, "👻 veiled", "#c77dff");
    } else if (ab.op === "dash") {
      p.dashDx = Math.cos(p.facing); p.dashDy = Math.sin(p.facing);
      p.dashSpd = ab.power;
      p.rollT = 0.3;
    } else if (ab.op === "heal") {
      if (p.hp >= p.maxHp) return false;
      const amt = (ab.power + (p.healBonus || 0)) * (p.healMult || 1);
      p.hp = Math.min(p.maxHp, p.hp + amt);
      C.floater(p.x, p.y - 24, "+" + amt + " HP", "#11d939");
    } else {
      return false;
    }
    ab.cdLeft = ab.cd * (1 - C.cdr()) * (p.cdrMult || 1);
    C.updateHud();
    return true;
  };

  // Statuses: burn/poison dps, slow mult, brief stun. Refresh on reapply.
  C.applyStatus = function (ent, id, dur, power) {
    ent.statuses = ent.statuses || {};
    ent.statuses[id] = { t: dur, power };
  };

  C.statusForElement = function (element) {
    if (element === "fire") return ["burn", 3, 0.9];
    if (element === "frost" || element === "water") return ["slow", 2, 0.5];
    if (element === "bolt") return ["stun", 0.45, 0];
    if (element === "earth") return ["stun", 0.6, 0];
    if (element === "venom" || element === "nature") return ["poison", 4, 0.6];
    if (element === "shadow") return ["weaken", 4, 1.25];
    // wind shoves (wave op); light breaks shields (damageGuard). No status.
    return null;
  };

  // Outgoing player damage: surge steroid x element affinity bonus.
  C.playerDmg = function (base, element) {
    const p = C.G.p;
    const s = p.surge;
    let m = (s && s.t > 0) ? s.dmgMult : 1;
    if (element && p.elemBonus[element]) m *= 1 + p.elemBonus[element];
    if (p.dmgDealtMult) m *= p.dmgDealtMult;
    return base * m;
  };

  // Single choke point for guard damage: shields soak direct hits (dots seep
  // through), numbers pop, elements apply, death routes to killGuard.
  C.damageGuard = function (gd, amt, element, isDot, opts) {
    if (opts && opts.wrecker) amt += opts.wrecker;
    if (gd.hp <= 0) return true;
    gd.statuses = gd.statuses || {};
    // Round only display-facing hits: per-frame DoT slices are fractional.
    if (!isDot) amt = Math.round(amt * 10) / 10;
    if (gd.statuses.weaken && gd.statuses.weaken.t > 0) amt *= 1.25;
    if (!isDot && gd.shield > 0 && !(opts && opts.pierce)) {
      // Holy/light is shieldbreaking: double soak rate. Wreckers chew it down.
      const soak = element === "light" || element === "holy" ? amt * 2 : amt;
      const effShield = Math.max(0, gd.shield - ((opts && opts.wrecker) || 0));
      const absorbed = Math.min(effShield, soak);
      gd.shield -= absorbed;
      amt -= (element === "light" || element === "holy") ? absorbed / 2 : absorbed;
      C.floater(gd.x, gd.y - 30, "🛡" + absorbed, "#8b93a3");
      if (amt <= 0) { C.updateHud(); return false; }
    }
    // The Merciful cannot kill: victims are spared at 1 HP instead.
    if (C.G.p.pacifist && !isDot && gd.hp - amt <= 0 && gd.type !== "collector" && gd.type !== "roller") {
      gd.hp = 1;
      C.floater(gd.x, gd.y - 30, "spared", "#11d939");
      C.updateHud();
      return false;
    }
    gd.hp -= amt;
    if (!isDot) {
      C.floater(gd.x, gd.y - 30, "-" + amt, element ? "#ffd166" : "#fff");
      gd.flashT = 0.09;
      C.spawnP(gd.x, gd.y - 6, 4, { col: element ? "#ffd166" : "#ffffff", spd: 130, life: 0.25, size: 2 });
    }
    if (element && !isDot) {
      const st = C.statusForElement(element);
      if (st) C.applyStatus(gd, st[0], st[1], st[2]);
    }
    if (gd.hp <= 0) { C.killGuard(gd); return true; }
    C.updateHud();
    return false;
  };

  // Guard DoTs + slow/stun. Returns {mult, stunned, died}.
  C.tickGuardStatuses = function (gd, dt) {
    gd.statuses = gd.statuses || {};
    for (const id of ["burn", "poison"]) {
      const s = gd.statuses[id];
      if (s && s.t > 0) {
        s.t -= dt;
        if (C.damageGuard(gd, s.power * dt, null, true)) return { mult: 1, stunned: false, died: true };
      }
    }
    let mult = 1, stunned = false;
    const slow = gd.statuses.slow;
    if (slow && slow.t > 0) { mult = slow.power; slow.t -= dt; }
    const stun = gd.statuses.stun;
    if (stun && stun.t > 0) { stunned = true; stun.t -= dt; }
    const weak = gd.statuses.weaken;
    if (weak && weak.t > 0) weak.t -= dt;
    return { mult, stunned, died: false };
  };

  // Satchel: bombs / potions / decoys. Q uses the selected stack, C cycles.
  // The selected stack restocks +1 per 25s up to 3 while equipped.
  C.SAT_ORDER = ["bomb", "potion", "decoy"];
  C.satAdd = function (kind, power) {
    const p = C.G.p;
    const st = p.satchel[kind];
    if (st) {
      st.qty = Math.min(C.satCap() + 2, st.qty + 1);
      if (power > st.power) st.power = power;
    } else {
      p.satchel[kind] = { kind, qty: 1, power };
    }
    C.updateHud();
  };
  C.cycleSatchel = function () {
    const p = C.G.p;
    const have = C.SAT_ORDER.filter(k => p.satchel[k]);
    if (!have.length) {
      C.floater(p.x, p.y - 24, "satchel empty", "#8b93a3");
      return;
    }
    const i = have.indexOf(p.satSel);
    p.satSel = have[(i + 1) % have.length];
    C.floater(p.x, p.y - 24, "selected: " + p.satSel, "#ffe066");
    C.updateHud();
  };
  C.useConsumable = function () {
    const p = C.G.p;
    if (C.G.over || C.G.title || C.G.draft) return false;
    let st = p.satchel[p.satSel];
    if (!st) { C.cycleSatchel(); st = p.satchel[p.satSel]; }
    if (!st) { C.floater(p.x, p.y - 24, "satchel empty", "#8b93a3"); return false; }
    if (st.qty <= 0) { C.floater(p.x, p.y - 24, st.kind + " restocking…", "#8b93a3"); return false; }
    if (st.kind === "bomb") {
      const g = C.nearestGuard(520);
      const tx = g ? g.x : p.x + Math.cos(p.facing) * 200;
      const ty = g ? g.y : p.y + Math.sin(p.facing) * 200;
      C.delayed.push({ x: tx, y: ty, t: 0.6, r: 95,
        dmg: C.playerDmg(st.power, "fire"), element: "fire" });
      C.floater(p.x, p.y - 30, "🧨 out!", "#ff8c00");
    } else if (st.kind === "potion") {
      if (p.hp >= p.maxHp) return false;
      const amt = (st.power + (p.healBonus || 0)) * (p.healMult || 1);
      p.hp = Math.min(p.maxHp, p.hp + amt);
      C.floater(p.x, p.y - 24, "+" + amt + " HP", "#11d939");
    } else if (st.kind === "decoy") {
      p.cloakT = st.power;
      C.floater(p.x, p.y - 24, "👻 " + st.power.toFixed(0) + "s", "#c77dff");
    }
    st.qty -= 1;
    C.updateHud();
    return true;
  };
  C.tickRestock = function (dt) {
    const p = C.G.p;
    const st = p.satchel[p.satSel];
    if (st && st.qty < C.satCap()) {
      p.restockT += dt;
      if (p.restockT >= 25) {
        p.restockT = 0;
        st.qty += 1;
        C.floater(p.x, p.y - 24, "+1 " + st.kind + " restocked", "#ffe066");
        C.updateHud();
      }
    } else {
      p.restockT = 0;
    }
  };

  C.updateRam = function (dt) {
    const p = C.G.p;
    if (!p.mount) return;
    if (p.mount.ramCd > 0) { p.mount.ramCd -= dt; return; }
    const room = C.curRoom();
    for (const gd of [...room.guards]) {
      if (Math.hypot(gd.x - p.x, gd.y - p.y) < 26) {
        const a = Math.atan2(gd.y - p.y, gd.x - p.x) || 0;
        const fx = C.collideCircle(gd.x + Math.cos(a) * 40, gd.y + Math.sin(a) * 40,
          9, C.solids(room));
        gd.x = fx[0]; gd.y = fx[1];
        C.damageGuard(gd, p.mount.ram, null);
        p.mount.ramCd = 0.5;
        break;
      }
    }
  };

  // Juice: capped particle pool. {x,y,vx,vy,life,max,size,col,grav}
  C.particles = [];
  C.spawnP = function (x, y, n, o) {
    o = o || {};
    const cols = Array.isArray(o.col) ? o.col : [o.col || "#ffffff"];
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = (o.spd ?? 120) * (0.4 + Math.random() * 0.8);
      C.particles.push({
        x, y,
        vx: Math.cos(a) * sp + (o.vx || 0),
        vy: Math.sin(a) * sp + (o.vy || 0),
        life: (o.life || 0.4) * (0.7 + Math.random() * 0.6), max: o.life || 0.4,
        size: o.size || 3, col: cols[Math.floor(Math.random() * cols.length)],
        grav: o.grav || 0,
      });
    }
    if (C.particles.length > 300) C.particles.splice(0, C.particles.length - 300);
  };
  C.updateParticles = function (dt) {
    for (const q of C.particles) {
      q.x += q.vx * dt; q.y += q.vy * dt;
      q.vy += (q.grav || 0) * dt;
      q.vx *= 1 - 1.8 * dt; q.vy *= 1 - 1.8 * dt;
      q.life -= dt;
    }
    C.particles = C.particles.filter(q => q.life > 0);
  };

  C.updateFx = function (dt) {
    for (const rg of C.rings) rg.age += dt;
    C.rings = C.rings.filter(rg => rg.age < rg.max);
    for (const rm of C.rooms.values()) {
      if (!rm.scorch) continue;
      for (const s of rm.scorch) s.age += dt;
      rm.scorch = rm.scorch.filter(s => s.age < 20);
    }
    for (const b of C.beams) b.age += dt;
    C.beams = C.beams.filter(b => b.age < b.max);
    C.updateParticles(dt);
    for (const d of C.delayed) {
      d.t -= dt;
      if (d.t <= 0) {
        C.rings.push({ x: d.x, y: d.y, age: 0, max: 0.3, r: d.r, col: "#ff8c00" });
        C.detonate(d.x, d.y, d.r, d.dmg, d.element);
      }
    }
    C.delayed = C.delayed.filter(d => d.t > 0);
  };
  C.updateRings = C.updateFx;

  // Player-placed constructs: turrets shoot, everything wears out.
  C.updatePlaced = function (dt) {
    const p = C.G.p, room = C.curRoom();
    for (const pl of [...room.placed]) {
      pl.t -= dt;
      if (pl.t <= 0) {
        room.placed.splice(room.placed.indexOf(pl), 1);
        C.floater(pl.x, pl.y - 20, pl.kind + " wears out", "#8b93a3");
        continue;
      }
      if (pl.kind === "turret") {
        pl.cd -= dt;
        const g = C.nearestGuard(380);
        if (g && pl.cd <= 0) {
          const a = Math.atan2(g.y - pl.y, g.x - pl.x);
          C.projs.push({
            x: pl.x, y: pl.y, vx: Math.cos(a) * 500, vy: Math.sin(a) * 500,
            dmg: pl.dmg, foe: false, life: 0.8, element: null,
          });
          pl.cd = 0.8;
        }
      }
    }
  };

  C.updateTempWalls = function (dt) {
    for (const room of C.rooms.values()) {
      if (!room.tempWalls) continue;
      for (const w of room.tempWalls) w.t -= dt;
      room.tempWalls = room.tempWalls.filter(w => w.t > 0);
    }
  };

  // Machines have hull by tier. AoE and stray shots wreck them into parts.
  C.damageMachine = function (room, m, amt) {
    if (!room.machines.includes(m)) return;
    m.hp -= amt + (C.G.p.wrecker || 0);
    if (m.hp > 0) {
      C.floater(m.x, m.y - C.MH / 2 - 10, "crack", "#8b93a3");
      return;
    }
    room.machines.splice(room.machines.indexOf(m), 1);
    const parts = C.tierIdx(m.tier) + 1;
    room.pickups.push({ kind: "parts", amount: parts,
      x: m.x, y: m.y, bob: 0, age: 0 });
    room.scorch.push({ x: m.x, y: m.y, age: 0 });
    if (m.pull) C.floater(m.x, m.y - 50, "pull lost!", "#ff5555");
    C.floater(m.x, m.y - 50, "💥 " + m.tier + " " + m.kind + " → +" + parts + "🧩", "#ffe066");
    C.G.shake = Math.max(C.G.shake, 0.15);
    C.updateHud();
  };

  // Shared AoE: nova powers and volatile pickups both go through here.
  C.detonate = function (x, y, radius, dmg, element) {
    C.rings.push({ x, y, age: 0, max: 0.35, r: radius });
    C.spawnP(x, y, 14, { col: ["#ff8c00", "#ffe066", "#ff5555"], spd: 220, life: 0.45, size: 3 });
    C.spawnP(x, y, 6, { col: "#555566", spd: 60, life: 0.8, size: 4 });
    const room = C.curRoom();
    for (const m of [...room.machines]) {
      if (Math.hypot(m.x - x, m.y - y) < radius + 40) C.damageMachine(room, m, dmg);
    }
    for (const gd of [...room.guards]) {
      const d = Math.hypot(gd.x - x, gd.y - y);
      if (d > radius + 14) continue;
      const a = Math.atan2(gd.y - y, gd.x - x) || 0;
      const fx = C.collideCircle(gd.x + Math.cos(a) * 52, gd.y + Math.sin(a) * 52, 9, C.solids(room));
      gd.x = fx[0]; gd.y = fx[1];
      C.damageGuard(gd, dmg, element);
    }
    C.G.shake = 0.15;
  };

  C.nearestGuard = function (maxD) {
    let best = null, bd = maxD || 1e9;
    for (const gd of C.curRoom().guards) {
      const d = Math.hypot(gd.x - C.G.p.x, gd.y - C.G.p.y);
      if (d < bd) { bd = d; best = gd; }
    }
    return best;
  };

  C.killGuard = function (gd) {
    C.audio.kill();
    C.spawnP(gd.x, gd.y - 6, 10, { col: ["#8b93a3", "#555566", "#777788"], spd: 130, life: 0.4, size: 3 });
    const room = C.curRoom();
    room.guards = room.guards.filter(g => g !== gd);
    C.G.kills++;
    if (gd.type === "warlord") {
      const mk = (data) => room.pickups.push(Object.assign(
        { x: gd.x, y: gd.y, bob: Math.random() * 6, age: 0 }, data));
      const wamt = Math.round((50 + room.depth * 8) * (C.coinMult ? C.coinMult() : 1));
      mk({ kind: "coins", amount: wamt });
      mk({ kind: "ticket", tier: "gold" });
      mk({ kind: "parts", amount: 3 });
      C.showCard("♛ WARLORD DOWN",
        "The pack scatters: +" + wamt + " coins, gold ticket, parts.",
        "", 4000);
    }
    if (gd.type === "roller") {      const mk = (data) => room.pickups.push(Object.assign(
        { x: gd.x, y: gd.y, bob: Math.random() * 6, age: 0 }, data));
      const ramt = Math.round((40 + room.depth * 8) * (C.coinMult ? C.coinMult() : 1));
      mk({ kind: "coins", amount: ramt });
      mk({ kind: "ticket", tier: "gold" });
      mk({ kind: "parts", amount: 2 + Math.floor(room.depth / 2) });
      C.showCard("🎲 HIGH ROLLER DOWN",
        "Chips everywhere: +" + ramt + " coins, gold ticket, parts. Grab them.",
        "", 4000);
    }
    if (gd.type === "collector") {
      // The Collector drops what it was carrying: a payout on the floor.
      const mk = (data) => room.pickups.push(Object.assign(
        { x: gd.x, y: gd.y, bob: Math.random() * 6, age: 0 }, data));
      const camt = Math.round((60 + room.depth * 10) * (C.coinMult ? C.coinMult() : 1));
      mk({ kind: "coins", amount: camt });
      mk({ kind: "ticket", tier: "gold" });
      mk({ kind: "ticket", tier: "silver" });
      C.showCard("💀 DEBT COLLECTOR DOWN",
        "It dropped +" + camt + " coins, gold + silver tickets. Grab them.",
        "Threat remains ★" + C.G.threat + ", the house has more.", 4000);
    }
    const nt = Math.min(5, Math.floor(C.G.kills / 2));
    if (nt > C.G.threat) {
      C.G.threat = nt;
      C.showCard("Threat ★" + nt,
        "You fought back. Future waves get faster, tougher, ranged.", "", 3000);
    }
    if (!C.G.feats.firstBlood) {
      C.G.feats.firstBlood = 1;
      C.G.p.tickets.silver++;
      C.showCard("Feat: First blood",
        "+1× Silver Ability ticket. Threat ★" + C.G.threat + ".", "", 3000);
    }
    if (Math.random() < C.ticketDropChance()) {
      const spont = ["bronze", "silver", "gold"][Math.floor(Math.random() * 3)];
      C.G.p.tickets[spont]++;
    }
    // Gunmen drop ammo instead of coins; everyone else pays bounties.
    // (Bosses keep their showers.)
    if (gd.ranged && gd.type !== "collector" && gd.type !== "roller") {
      const amt = 2 + Math.floor(Math.random() * 3);
      room.pickups.push({ kind: "ammo", amount: amt, x: gd.x, y: gd.y, bob: 0, age: 0 });
      C.updateHud();
      return;
    }
    // The house pays bounties: rank + danger scale the drop.
    const bounty = { guard: [2, 5], pitboss: [4, 8], enforcer: [6, 11],
      bruiser: [5, 9], stalker: [3, 6], hexer: [5, 9], medic: [4, 7],
      captain: [8, 13], handler: [6, 10], hound: [1, 3] }[gd.type];
    if (bounty) {
      const base = bounty[0] + Math.floor(Math.random() * (bounty[1] - bounty[0] + 1)) +
        Math.floor(room.danger / 3);
      const amt = Math.max(1, Math.round(base * (C.coinMult ? C.coinMult() : 1)));
      room.pickups.push({ kind: "coins", amount: amt, x: gd.x, y: gd.y, bob: 0, age: 0 });
    }
    C.updateHud();
  };

  C.hurtPlayer = function (n, element) {
    const p = C.G.p;
    if (p.inv > 0 || p.rollT > 0 || C.G.over) return;
    if (p.mount) {
      p.mount.hp -= 1;
      C.floater(p.x, p.y - 24, p.mount.name.slice(0, 14) + " -1", "#ffe066");
      p.inv = Math.max(p.inv, 0.4);
      if (p.mount.hp <= 0) {
        C.floater(p.x, p.y - 30, p.mount.name.slice(0, 16) + " wrecked!", "#ff5555");
        p.mount = null;
      }
      C.updateHud();
      return;
    }
    // Armor: flat chance to fully block a hit (carapace stacks, cap 65%).
    const block = p.armorLock ? 0 : Math.min(0.65, (p.armorPct || 0) +
      ((p.stance && p.stance.kind === "carapace") ? 0.25 : 0));
    if (block > 0 && Math.random() < block) {
      C.floater(p.x, p.y - 24, "blocked", "#7df9ff");
      p.inv = Math.max(p.inv, 0.4);
      C.G.shake = 0.1;
      C.updateHud();
      return;
    }
    if (element && p.resist[element]) n *= 1 - Math.min(0.5, p.resist[element]);
    if (p.dmgTakenMult && p.dmgTakenMult !== 1 &&
        (!p.dmgTakenElementalOnly || element)) n *= p.dmgTakenMult;
    p.hp -= n; p.inv = 0.9; p.flashT = 0.12; C.G.shake = 0.2; C.audio.hurt();
    C.spawnP(p.x, p.y - 6, 6, { col: ["#ff5555", "#ff8888"], spd: 150, life: 0.3, size: 3 });
    if (p.hp <= 0) C.die();
    C.updateHud();
  };

  C.die = function () {
    C.G.over = true;
    C.audio.death();
    C.spawnP(C.G.p.x, C.G.p.y - 6, 30, { col: ["#7CFC00", "#2ecc71", "#ffffff"], spd: 200, life: 0.7, size: 3 });
    C.ui.card.classList.remove("show");
    const dreRoom = C.curRoom();
    const best = C.saveBest(dreRoom.depth, C.G.t, C.G.kills);
    const bestTag = best ? " ★ NEW BEST" : "";
    // Too fast to impress the house: no legacy pull under 10 seconds.
    if (C.G.t < 10) {
      const room = C.curRoom();
      C.ui.deathStats.textContent = "Survived " + C.fmtTime(C.G.t) + " · depth " + room.depth +
        " · " + C.G.kills + " kills · " + C.G.pulls + " pulls." + bestTag;
      C.ui.deathLegacy.textContent = "Gone in " + Math.floor(C.G.t) +
        "s: too fast for a legacy pull. Survive 10s+ to earn one.";
      C.ui.deathLegacy.style.color = "#878d96";
      C.renderPendingList();
      C.ui.deathBox.classList.add("show");
      return;
    }
    C.armDeathMachine();
    const room = C.curRoom();
    C.ui.deathStats.textContent = "Survived " + C.fmtTime(C.G.t) + " · depth " + room.depth +
      " · " + C.G.kills + " kills · " + C.G.pulls + " pulls · Threat ★" + C.G.threat + "." + bestTag;
    C.ui.deathLegacy.textContent = "";
    C.renderPendingList();
    C.ui.deathBox.classList.add("show");
  };

  function hurtTouch(gd, p, d) {
    if (d < 26 && gd.atkCd <= 0) {
      C.hurtPlayer(gd.touchDmg || 1, C.hasAffix(gd, "elemental") ? gd.element : null);
      if (p.stance && p.stance.kind === "carapace") C.damageGuard(gd, 2, null);
      if (gd.affix === "elemental" && gd.element) {
        const st = C.statusForElement(gd.element);
        if (st) C.applyStatus(p, st[0], st[1], st[2]);
      }
      gd.atkCd = 0.9;
    }
  }

  function foeShot(gd, a) {
    C.projs.push({
      x: gd.x, y: gd.y, vx: Math.cos(a) * 300, vy: Math.sin(a) * 300,
      dmg: 1, foe: true, life: 1.6,
      element: C.hasAffix(gd, "elemental") ? gd.element : null,
    });
    gd.atkCd = 1.6;
  }

  function chaseMove(gd, p, room, dt, mult) {
    const a = Math.atan2(p.y - gd.y, p.x - gd.x);
    gd.facing = a;
    gd.x += Math.cos(a) * gd.speed * mult * dt;
    gd.y += Math.sin(a) * gd.speed * mult * dt;
    const fixed = C.collideCircle(gd.x, gd.y, 9, C.solids(room));
    gd.x = fixed[0]; gd.y = fixed[1];
    return a;
  }

  C.updateGuards = function (dt) {
    const p = C.G.p, room = C.curRoom();
    for (const gd of [...room.guards]) {
      const d = Math.hypot(gd.x - p.x, gd.y - p.y);
      if (gd.flashT > 0) gd.flashT -= dt;
      // Possessed: it hunts its own coworkers for a while.
      if (gd.possessed && gd.possessed > 0) {
        gd.possessed -= dt;
        let mark = null, md = 1e9;
        for (const o of room.guards) {
          if (o === gd || (o.possessed && o.possessed > 0)) continue;
          const d = Math.hypot(o.x - gd.x, o.y - gd.y);
          if (d < md) { md = d; mark = o; }
        }
        if (mark) {
          const a = Math.atan2(mark.y - gd.y, mark.x - gd.x);
          gd.facing = a;
          gd.x += Math.cos(a) * gd.speed * dt;
          gd.y += Math.sin(a) * gd.speed * dt;
          const fixed = C.collideCircle(gd.x, gd.y, 9, C.solids(room));
          gd.x = fixed[0]; gd.y = fixed[1];
          if (md < 22 && gd.atkCd <= 0) {
            C.damageGuard(mark, 2, null);
            gd.atkCd = 1.0;
          }
        }
        if (gd.atkCd > 0) gd.atkCd -= dt;
        continue;
      }
      // Pacified: a friend for life. Stands around, takes dots like anyone.
      if (gd.pacified) {
        const pc = C.tickGuardStatuses(gd, dt);
        if (pc.died) continue;
        if (gd.atkCd > 0) gd.atkCd -= dt;
        continue;
      }
      // Cloaked: the trail goes cold, chasers give up.
      if (C.G.p.cloakT > 0) {
        gd.chase = false;
        const cl = C.tickGuardStatuses(gd, dt);
        if (cl.died) continue;
        if (gd.atkCd > 0) gd.atkCd -= dt;
        continue;
      }
      // DoTs tick even on unaware guards; slow/stun matter once chasing.
      const st = C.tickGuardStatuses(gd, dt);
      if (st.died) continue;
      if (!gd.pacified && !gd.chase &&
          (d < gd.sight * (1 - (C.G.p.presence || 0)) * (C.G.p.sightMult || 1) * C.noticeMult() || room.alert > 0)) gd.chase = true;
      if (!gd.chase) { if (gd.atkCd > 0) gd.atkCd -= dt; continue; }
      // No body-stacking, no standing inside the player: hard shove out to
      // arm's length, and guard pairs slide around each other tangentially
      // so piles flow apart instead of grinding one HP bar.
      {
        const px = p.x - gd.x, py = p.y - gd.y;
        const pd = Math.hypot(px, py);
        if (pd > 0.01 && pd < 26) {
          gd.x -= (px / pd) * (26 - pd) * 0.85;
          gd.y -= (py / pd) * (26 - pd) * 0.85;
        }
        for (const o of room.guards) {
          if (o === gd) continue;
          const ox = gd.x - o.x, oy = gd.y - o.y;
          const od = Math.hypot(ox, oy);
          if (od > 0.01 && od < 24) {
            const push = (24 - od) * 0.5;
            gd.x += (ox / od) * push + (-oy / od) * push * 0.4;
            gd.y += (oy / od) * push + (ox / od) * push * 0.4;
          }
        }
      }
      // Captain's rally aura: nearby coworkers hustle (+25% speed).
      let aura = 1;
      if (gd.type !== "captain") {
        for (const c of room.guards) {
          if (c.type !== "captain" || (c.possessed && c.possessed > 0)) continue;
          if (Math.hypot(c.x - gd.x, c.y - gd.y) < 220) { aura = 1.25; break; }
        }
      }
      const mult = (p.rollT > 0 ? 0.7 : 1) * st.mult * aura *
        (C.enemySlowMult ? C.enemySlowMult() : 1);
      if (st.stunned) { if (gd.atkCd > 0) gd.atkCd -= dt; continue; }
      // Medics cower and mend: flee the player, patch up the pack.
      if (gd.type === "medic") {
        if (d < 170) {
          const ma = Math.atan2(gd.y - p.y, gd.x - p.x);
          gd.facing = ma + Math.PI;
          gd.x += Math.cos(ma) * gd.speed * mult * dt;
          gd.y += Math.sin(ma) * gd.speed * mult * dt;
          const fixed = C.collideCircle(gd.x, gd.y, 9, C.solids(room));
          gd.x = fixed[0]; gd.y = fixed[1];
        }
        gd.healCd -= dt;
        if (gd.healCd <= 0) {
          let healed = false;
          for (const o of room.guards) {
            if (o === gd || o.hp >= (o.maxHp || o.hp)) continue;
            if (Math.hypot(o.x - gd.x, o.y - gd.y) > 220) continue;
            o.hp = Math.min(o.maxHp || o.hp, o.hp + 2);
            healed = true;
          }
          if (healed) C.floater(gd.x, gd.y - 30, "+2", "#11d939");
          gd.healCd = 3;
        }
        hurtTouch(gd, p, d);
        if (gd.atkCd > 0) gd.atkCd -= dt;
        continue;
      }
      // Handlers skirmish at range and whistle up hounds (max 2 live).
      if (gd.type === "handler") {
        const ha = Math.atan2(gd.y - p.y, gd.x - p.x);
        if (d < 160 || d > 380) {
          const dir = d < 160 ? 1 : -0.6;
          gd.facing = dir > 0 ? ha + Math.PI : ha;
          gd.x += Math.cos(ha) * gd.speed * dir * mult * dt;
          gd.y += Math.sin(ha) * gd.speed * dir * mult * dt;
          const fixed = C.collideCircle(gd.x, gd.y, 9, C.solids(room));
          gd.x = fixed[0]; gd.y = fixed[1];
        }
        gd.sumCd -= dt;
        if (gd.sumCd <= 0) {
          const hounds = room.guards.filter(o => o.type === "hound").length;
          if (hounds < 2) {
            room.guards.push({ x: gd.x, y: gd.y, hp: 2, maxHp: 2, speed: 190,
              sight: 240, atkCd: 0, chase: true, ranged: false, type: "hound",
              touchDmg: 1, size: 0.7, statuses: {}, affix: null, affix2: null,
              shield: 0, element: null, teleT: 0, dashT: 0, dashCd: 9, dashDx: 0, dashDy: 0,
              healCd: 0, sumCd: 0, rallyCd: 0, phase: Math.random(), facing: 0 });
            C.floater(gd.x, gd.y - 30, "yelp!", "#ff9c41");
          }
          gd.sumCd = 8;
        }
        hurtTouch(gd, p, d);
        if (gd.atkCd > 0) gd.atkCd -= dt;
        continue;
      }
      // Warlords bellow rally: patch up the pack every few seconds.
      if (gd.type === "warlord") {
        gd.rallyCd -= dt;
        if (gd.rallyCd <= 0) {
          gd.rallyCd = 6;
          for (const o of room.guards) {
            if (o === gd || Math.hypot(o.x - gd.x, o.y - gd.y) > 230) continue;
            if (o.hp < (o.maxHp || o.hp)) o.hp = Math.min(o.maxHp || o.hp, o.hp + 3);
          }
          C.floater(gd.x, gd.y - 36, "RALLY!", "#ff5555");
        }
      }
      if (C.hasAffix(gd, "charger")) {
        gd.dashCd -= dt;
        if (gd.dashT > 0) {
          // Committed dash along the locked direction.
          gd.dashT -= dt;
          gd.x += gd.dashDx * 340 * dt;
          gd.y += gd.dashDy * 340 * dt;
          const fixed = C.collideCircle(gd.x, gd.y, 9, C.solids(room));
          gd.x = fixed[0]; gd.y = fixed[1];
          hurtTouch(gd, p, Math.hypot(gd.x - p.x, gd.y - p.y));
        } else if (gd.teleT > 0) {
          // Telegraph: hold still, then go.
          gd.teleT -= dt;
          if (gd.teleT <= 0) {
            const a = Math.atan2(p.y - gd.y, p.x - gd.x);
            gd.facing = a;
            gd.dashDx = Math.cos(a); gd.dashDy = Math.sin(a);
            gd.dashT = 0.28;
          }
        } else {
          const a = chaseMove(gd, p, room, dt, mult);
          if (gd.dashCd <= 0 && d < 280 && d > 70) {
            gd.teleT = 0.5; gd.dashCd = 3.2;
          }
          hurtTouch(gd, p, Math.hypot(gd.x - p.x, gd.y - p.y));
          if (gd.ranged && d < 380 && d > 120 && gd.atkCd <= 0) foeShot(gd, a);
        }
      } else {
        const a = chaseMove(gd, p, room, dt, mult);
        hurtTouch(gd, p, Math.hypot(gd.x - p.x, gd.y - p.y));
        if (gd.ranged && d < 380 && d > 120 && gd.atkCd <= 0) foeShot(gd, a);
      }
      if (gd.atkCd > 0) gd.atkCd -= dt;
    }
  };

  // Familiar storage (Doc rule, run-scaled): 2 active, rest stabled. P rotates.
  // Summoned temps stay pinned and are never stabled.
  C.rotatePets = function () {
    const p = C.G.p;
    const act = () => p.pets.filter(q => !q.temp);
    if (!p.stable.length) {
      const a = act();
      if (a.length > 1) {
        p.pets.splice(p.pets.indexOf(a[0]), 1);
        p.pets.push(a[0]);
        C.showCard("Familiars reordered",
          "Lead: " + act()[0].name + ".", "", 1800);
      }
      return;
    }
    const incoming = p.stable.shift();
    const a = act();
    if (a.length >= 2) {
      p.pets.splice(p.pets.indexOf(a[0]), 1);
      p.stable.push(a[0]);
    }
    p.pets.push(incoming);
    C.showCard("Familiars rotated",
      "Active: " + p.pets.map(q => q.name + " (" + (q.role || "gunner") + ")").join(", ") + ".",
      p.stable.length + " stabled.", 2200);
    C.updateHud();
  };

  C.updatePets = function (dt) {
    const p = C.G.p, room = C.curRoom();
    for (const pet of p.pets) {
      const i = p.pets.indexOf(pet);
      if (pet.stationary) {
        if (pet.x == null) { pet.x = p.x; pet.y = p.y; }
        continue;
      }
      const radius = (pet.role || "gunner") === "bully" ? 42 : 26;
      const spin = (pet.role || "gunner") === "bully" ? 3.2 : 2;
      const a = C.G.t * spin + i * 2.1;
      pet.x = p.x + Math.cos(a) * radius;
      pet.y = p.y + Math.sin(a) * radius;
    }
    for (const pet of [...p.pets]) {
      if (pet.temp) {
        pet.dur -= dt;
        if (pet.dur <= 0) {
          p.pets.splice(p.pets.indexOf(pet), 1);
          C.floater(p.x, p.y - 30, pet.name.slice(0, 16) + " fades", "#8b93a3");
          continue;
        }
      }
      const role = pet.role || "gunner";
      if (role === "gunner") {
        pet.cd -= dt;
        const g = C.nearestGuard(360);
        if (g && pet.cd <= 0) {
          const a = Math.atan2(g.y - p.y, g.x - p.x);
          C.projs.push({
            x: pet.stationary ? pet.x : p.x, y: pet.stationary ? pet.y : p.y,
            vx: Math.cos(a) * 460, vy: Math.sin(a) * 460,
            dmg: pet.dmg * C.petMult(), foe: false, life: 0.7, element: pet.element || null,
          });
          pet.cd = pet.cdMax || 1.1;
        }
      } else if (role === "bully") {
        // Brawling orbiter: body-slams guards it touches.
        pet.cd -= dt;
        if (pet.cd <= 0) {
          let hit = false;
          for (const gd of [...room.guards]) {
            if (Math.hypot(gd.x - pet.x, gd.y - pet.y) < 20) {
              const a = Math.atan2(gd.y - p.y, gd.x - p.x) || 0;
              const fx = C.collideCircle(gd.x + Math.cos(a) * 30, gd.y + Math.sin(a) * 30,
                9, C.solids(room));
              gd.x = fx[0]; gd.y = fx[1];
              C.damageGuard(gd, pet.dmg * C.petMult(), null);
              hit = true;
            }
          }
          pet.cd = hit ? 0.5 : 0.1;
        }
      } else if (role === "medic") {
        pet.cd -= dt;
        if (pet.cd <= 0) {
          if (p.hp < p.maxHp) {
            const amt = (1 + (p.healBonus || 0)) * (p.healMult || 1);
            p.hp = Math.min(p.maxHp, p.hp + amt);
            C.floater(p.x, p.y - 24, "+" + amt + " HP (" + pet.name.slice(0, 14) + ")", "#11d939");
            C.updateHud();
            pet.cd = pet.cdMax || 18;
          } else {
            pet.cd = 1;
          }
        }
      }
      // mule (loot magnet) and scout (ticket luck) are passive auras.
    }
  };

  C.updateProjectiles = function (dt) {
    const p = C.G.p, room = C.curRoom();
    for (const pr of [...C.projs]) {
      pr.x += pr.vx * dt; pr.y += pr.vy * dt; pr.life -= dt;
      if (pr.life <= 0 || C.pointBlocked(room, pr.x, pr.y) ||
          (pr.foe && C.pointBlockedTemp(room, pr.x, pr.y))) {
        C.projs.splice(C.projs.indexOf(pr), 1);
        continue;
      }
      if (!pr.muzzled) {
        pr.muzzled = true;
        C.spawnP(pr.x, pr.y, 3, { col: pr.foe ? "#ff5555" : "#ffe066", spd: 60, life: 0.12, size: 3 });
      }
      let hit = false;
      if (pr.foe) {
        if (Math.hypot(pr.x - p.x, pr.y - p.y) < 12) {
          C.hurtPlayer(pr.dmg, pr.element);
          if (pr.element) {
            const pst = C.statusForElement(pr.element);
            if (pst) C.applyStatus(p, pst[0], pst[1], pst[2]);
          }
          hit = true;
        }
      } else {
        for (const gd of [...room.guards]) {
          if (Math.hypot(pr.x - gd.x, pr.y - gd.y) < 14) {
            C.damageGuard(gd, pr.dmg, pr.element, false, pr.pierce ? { pierce: true } : null);
            hit = true;
            break;
          }
        }
      }
      // Missed shots (both sides) slam into machines and wreck them.
      if (!hit) {
        for (const m of [...room.machines]) {
          if (Math.abs(pr.x - m.x) < C.MW / 2 && Math.abs(pr.y - m.y) < C.MH / 2) {
            C.damageMachine(room, m, pr.dmg);
            hit = true;
            break;
          }
        }
      }
      if (hit) C.projs.splice(C.projs.indexOf(pr), 1);
    }
  };
})(window.Casino);
