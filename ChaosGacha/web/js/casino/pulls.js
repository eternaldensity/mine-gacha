"use strict";
/* Pull lifecycle: E starts a machine pull, you walk away, loot drops on the
 * floor when done. Pulls tick even while you kite guards or visit rooms.
 * Depends on: config, dom, state, slots, prizes, hud (all runtime). */
(function (C) {
  C.nearestMachine = function (freeOnly) {
    const room = C.curRoom();
    let best = null, bd = C.INTERACT_R;
    for (const m of room.machines) {
      if (freeOnly && m.pull) continue;
      const d = Math.hypot(m.x - C.G.p.x, m.y - C.G.p.y);
      if (d < bd) { bd = d; best = m; }
    }
    return best;
  };

  C.tryStartPull = function () {
    if (C.G.over || C.G.title) return;
    const m = C.nearestMachine(true);
    if (!m) return;
    const t = C.tierById(m.tier);
    if (m.kind === "slot") {
      const c = C.slotCost(t);
      if (C.G.p.coins < c) {
        C.showCard("Not enough coins", t.label + " slot costs " + c + ".", "", 1800);
        return;
      }
      C.G.p.coins -= c;
      const pay = C.rollSlotPayout(t);
      const syms = C.symbolsFor(pay);
      const total = C.SYMS.length * C.REEL_H;
      m.pull = {
        t: 0, dur: t.pull * C.pullMul() * (C.G.p.pullMul || 1), pay, syms, fin: null,
        // Each reel scrolls a wrapping symbol tape, then lands on its target.
        reels: syms.map((s, i) => ({
          pos: Math.random() * total, vel: 300 + i * 40,
          state: "spin", target: C.SYMS.indexOf(s),
          landFrom: 0, landTo: 0, landT: 0,
        })),
      };
    } else {
      if ((C.G.p.tickets[m.tier] || 0) < 1) {
        C.showCard("Need 1× " + t.label + " ticket",
          "Win it from " + t.label + " slots first (depth " + t.minDepth + "+).", "", 2200);
        return;
      }
      C.G.p.tickets[m.tier]--;
      m.pull = {
        t: 0, dur: 3.0 * C.pullMul() * (C.G.p.pullMul || 1), gacha: C.gachaRoll(m.tier, m.cat), fin: null,
        reel: { pos: Math.random() * 280, vel: 300, state: "spin", landT: 0 },
      };
    }
    C.audio.pullStart();
    // Noise: alert nearby guards (unless cloaked). Ghosts run quiet.
    const room = C.curRoom();
    if (!C.G.p.cloakT) {
      room.alert = 5;
      const noise = C.noiseRadius();
      for (const gd of room.guards) {
        if (!gd.pacified && Math.hypot(gd.x - C.G.p.x, gd.y - C.G.p.y) < noise) gd.chase = true;
      }
    }
    C.updateHud();
  };

  function dropSpot(room, m) {
    const front = m.y < C.H / 2 ? 1 : -1;
    return {
      x: Math.max(60, Math.min(C.W - 60, m.x + (Math.random() * 30 - 15))),
      y: m.y + front * (C.MH / 2 + 18),
    };
  }

  function spawnPickup(room, m, data) {
    const s = dropSpot(room, m);
    room.pickups.push(Object.assign({ x: s.x, y: s.y, bob: Math.random() * 6, age: 0 }, data));
  }

  function completePull(room, m) {
    const pull = m.pull, t = C.tierById(m.tier);
    m.pull = null;
    C.floater(m.x, m.y - C.MH / 2 - 22, "✔ READY", "#ffe066");
    if (m.kind === "slot") m.idleSyms = pull.syms.slice();
    else m.lastPrize = { name: pull.gacha.res.name, rarity: pull.gacha.res.rarity };
    C.G.pulls++;
    if (m.kind === "slot") {
      const pay = pull.pay, at = { x: m.x, y: m.y };
      if (pay.kind === "jackpot") {
        C.audio.jackpot();
        C.spawnP(m.x, m.y - 20, 50,
          { col: ["#f7d40a", "#ffe066", "#ff8c00", "#ffffff"], spd: 260, life: 0.9, size: 3, grav: 300 });
        spawnPickup(room, m, { kind: "coins", amount: pay.coins });
        spawnPickup(room, m, { kind: "ticket", tier: pay.ticket });
        C.floater(at.x, at.y - 50, "JACKPOT 7-7-7!", "#f7d40a");
        C.showCard("JACKPOT 7-7-7! +" + pay.coins + " coins + 1× " + pay.ticket,
          t.label + " slot screams. Every guard heard that. Grab the loot.", "", 3500);
        for (const gd of room.guards) if (!gd.pacified) gd.chase = true;
      } else if (pay.kind === "ticket") {
        spawnPickup(room, m, { kind: "ticket", tier: pay.ticket });
        C.floater(at.x, at.y - 50, "🎟 " + pay.ticket, t.color);
      } else if (pay.kind === "coins") {
        spawnPickup(room, m, { kind: "coins", amount: pay.coins });
        C.floater(at.x, at.y - 50, "+" + pay.coins + " 🪙", "#ffe066");
      } else {
        C.floater(at.x, at.y - 50, "house wins", "#878d96");
      }
    } else {
      spawnPickup(room, m, { kind: "prize", res: pull.gacha.res, tier: m.tier, src: m });
      C.floater(m.x, m.y - 50, "🎲 " + pull.gacha.res.name.slice(0, 24), C.rarityColor(pull.gacha.res.rarity));
    }
    C.checkFeats();
    C.updateHud();
  }

  var REEL_LOCKS = [0.55, 0.75, 0.95]; // reels land left-to-right
  var LAND_DUR = 0.34;   // slot reel landing (ease + bounce)
  var GREEL_LAND = 0.45; // gacha reel slow-down

  function easeOutBack(p) {
    var c1 = 1.70158, c3 = c1 + 1;
    return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2);
  }

  // Scroll one slot reel; when lockNow, ease onto the target symbol.
  // pullT ramps the speed so the spin visibly accelerates like a real reel.
  function tickSlotReel(reel, dt, lockNow, pullT) {
    var H = C.REEL_H, total = C.SYMS.length * H;
    if (reel.state === "locked") return;
    if (reel.state === "spin") {
      reel.pos += reel.vel * Math.min(1, 0.25 + pullT / 0.5) * dt;
      if (!lockNow) return;
      // Land on the next offset at/after pos+90px that centers the target.
      var targetPos = C.pmod(reel.target * H, total);
      reel.landFrom = reel.pos;
      reel.landTo = reel.pos + 90 + C.pmod(targetPos - (reel.pos + 90), total);
      reel.landT = 0;
      reel.state = "land";
      return;
    }
    reel.landT += dt;
    var p = Math.min(1, reel.landT / LAND_DUR);
    reel.pos = reel.landFrom + (reel.landTo - reel.landFrom) * easeOutBack(p);
    if (p >= 1) { reel.state = "locked"; reel.pos = reel.landTo; C.audio.lock(); }
  }

  // Scroll the gacha reel; landing is a slow-down while the winner fades in.
  function tickGachaReel(pull, dt, frac) {
    var reel = pull.reel;
    if (reel.state === "locked") return;
    if (reel.state === "spin") {
      reel.pos += reel.vel * Math.min(1, 0.25 + pull.t / 0.5) * dt;
      if (frac >= 0.8) { reel.state = "land"; reel.landT = 0; }
      return;
    }
    reel.landT += dt;
    var p = Math.min(1, reel.landT / GREEL_LAND);
    reel.vel = 300 * (1 - p) * (1 - p);
    reel.pos += reel.vel * dt;
    if (p >= 1) { reel.state = "locked"; C.audio.lock(); }
  }

  // Animate one machine pull; payout waits for locked reels, then holds briefly.
  function tickMachinePull(room, m, dt) {
    const pull = m.pull;
    if (!pull) return;
    if (pull.fin != null) {
      pull.fin -= dt;
      if (pull.fin <= 0) completePull(room, m);
      return;
    }
    pull.t += dt;
    const frac = Math.min(1, pull.t / pull.dur);
    var settled;
    if (m.kind === "slot") {
      pull.reels.forEach((reel, i) => tickSlotReel(reel, dt, frac >= REEL_LOCKS[i], pull.t));
      settled = pull.reels.every(r => r.state === "locked");
    } else {
      tickGachaReel(pull, dt, frac);
      settled = pull.reel.state === "locked";
    }
    // Pay out once the reels show the result (with a hard cap as fallback).
    if ((pull.t >= pull.dur && settled) || pull.t >= pull.dur + 0.8) pull.fin = 0.42;
  }

  // Tick every known room's pulls so loot is waiting when you circle back.
  C.updatePulls = function (dt) {
    for (const room of C.rooms.values()) {
      for (const m of room.machines) tickMachinePull(room, m, dt);
    }
  };

  C.updatePickups = function (dt) {
    const p = C.G.p, room = C.curRoom();
    for (const pk of room.pickups) { pk.bob += dt; pk.age += dt; }
    const magnet = C.pickupRadius ? C.pickupRadius()
      : (C.PICKUP_R + (C.activeRole("mule") ? 40 : 0));
    for (const pk of [...room.pickups]) {
      if (Math.hypot(pk.x - p.x, pk.y - p.y) > magnet) continue;
      room.pickups.splice(room.pickups.indexOf(pk), 1);
      if (pk.kind === "coins") {
        C.audio.coins();
        C.spawnP(pk.x, pk.y, 3, { col: "#ffe066", spd: 80, life: 0.3, size: 2 });
        p.coins += pk.amount;
        C.floater(p.x, p.y - 24, "+" + pk.amount + " 🪙", "#ffe066");
      } else if (pk.kind === "ticket") {
        C.audio.ticket();
        p.tickets[pk.tier] = (p.tickets[pk.tier] || 0) + 1;
        const t = C.tierById(pk.tier);
        C.floater(p.x, p.y - 24, "+1 🎟 " + pk.tier, t.color);
      } else if (pk.kind === "ammo") {
        C.audio.coins();
        const space = Math.max(0, C.ammoMax() - (p.ammo || 0));
        const take = Math.min(space, pk.amount);
        p.ammo = (p.ammo || 0) + take;
        C.floater(p.x, p.y - 24, "+" + take + " ammo", "#ffd166");
        if (take < pk.amount) {
          pk.amount -= take; // leave the rest on the floor (spliced above)
          room.pickups.push(pk);
          C.updateHud();
          continue;
        }
      } else if (pk.kind === "parts") {
        C.audio.coins();
        p.parts += pk.amount;
        C.floater(p.x, p.y - 24, "+" + pk.amount + " 🧩 parts", "#ffe066");
      } else if (pk.kind === "prize") {
        C.audio.build();
        if (pk.src) pk.src.lastPrize = null; // window back to category
        const res = pk.res;
        const tags = (res.tags || []).slice();
        C.G.prizeLog.push({ name: res.name, rarity: res.rarity, category: res.category,
          source: res.source || "", description: res.description || "", odds: res.odds || 0, tags });
        const note = C.applyPrize(res);
        C.checkTagSets();
        const flav = C.flavorShort(res.description);
        C.showCard("[" + C.rarityName(res.rarity) + " " + res.category + "] " + res.name +
          " (" + res.rarity.toFixed(1) + ")" + (tags.length ? " #" + tags.join(" #") : ""),
          note,
          "Ticket: " + pk.tier + " · odds " + (res.odds || 0).toFixed(2) + "%" +
            (flav ? " · “" + flav + "”" : ""), 6000);
      }
      C.updateHud();
    }
  };
})(window.Casino);
