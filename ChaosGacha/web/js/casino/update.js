"use strict";
/* Main loop: timers, movement, doors, pulls, waves.
 * Depends on: everything above (runtime). */
(function (C) {
  let last = 0;
  let prevE = false;
  let prevP = false;
  let prevB = false;
  let prevQ = false;
  let prevC = false;

  C.frame = function (ts) {
    requestAnimationFrame(C.frame);
    const dt = Math.min(0.05, (ts - last) / 1000 || 0.016);
    last = ts;
    if (!C.G) return;
    C.update(dt);
    C.render(dt);
  };

  function moveInput() {
    const k = C.keys;
    const mx = (k["d"] || k["arrowright"] ? 1 : 0) - (k["a"] || k["arrowleft"] ? 1 : 0);
    const my = (k["s"] || k["arrowdown"] ? 1 : 0) - (k["w"] || k["arrowup"] ? 1 : 0);
    return [mx, my];
  }

  function updateDoors(p) {
    // Thresholds sit just inside the clamp bounds so plain walking (no dash)
    // reaches them: pressing into a doorway is enough to go through.
    const doorR = 34;
    let entered = null;
    if (p.y < C.WALL + 4 && Math.abs(p.x - C.W / 2) < doorR) entered = "N";
    else if (p.y > C.H - C.WALL - 4 && Math.abs(p.x - C.W / 2) < doorR) entered = "S";
    else if (p.x < C.WALL + 4 && Math.abs(p.y - C.H / 2) < doorR) entered = "W";
    else if (p.x > C.W - C.WALL - 4 && Math.abs(p.y - C.H / 2) < doorR) entered = "E";
    if (entered) {
      if (entered === "N") { C.G.roomY--; p.y = C.H - C.WALL - 20; p.x = C.W / 2; }
      if (entered === "S") { C.G.roomY++; p.y = C.WALL + 20; p.x = C.W / 2; }
      if (entered === "W") { C.G.roomX--; p.x = C.W - C.WALL - 20; p.y = C.H / 2; }
      if (entered === "E") { C.G.roomX++; p.x = C.WALL + 20; p.y = C.H / 2; }
      C.onEnterRoom();
    }
    p.x = Math.max(C.WALL - 2, Math.min(C.W - C.WALL + 2, p.x));
    p.y = Math.max(C.WALL - 2, Math.min(C.H - C.WALL + 2, p.y));
  }

  function updateWaves(dt, room) {
    C.G.waveT -= dt;
    if (C.G.waveT > 0) return;
    C.G.waveT = Math.max(25, 60 - C.G.threat * 5 - room.danger * 2);
    // Threat 4+: the Collector may come instead of a pack (one at a time).
    if (C.G.threat >= 4 && !room.guards.some(g => g.type === "collector") && Math.random() < 0.3) {
      room.guards.push(C.makeBoss(room, room.danger, room.depth));
      C.showCard("💀 DEBT COLLECTOR", "It has come to collect. Kill it for a payout.", "", 3000);
      C.updateHud();
      return;
    }
    const n = 1 + Math.floor(C.G.threat / 2) + (room.danger > 4 ? 1 : 0);
    for (let i = 0; i < n; i++) {
      // Threat 3+: first responder is always an elite.
      const gd = C.makeGuard(room, room.danger, i === 0 && C.G.threat >= 3);
      gd.x = C.WALL + 30;
      gd.y = C.WALL + 80 + Math.random() * 100;
      gd.chase = true;
      room.guards.push(gd);
    }
    C.audio.wave();
    C.showCard("Security wave ★" + C.G.threat,
      n + " guard(s) converge. Pulls are loud, keep moving.", "", 2200);
  }

  C.update = function (dt) {
    if (C.G.title) return; // title screen: frozen room behind the intro
    if (C.G.draft) return; // draft modal pauses the sim
    const p = C.G.p, room = C.curRoom();
    if (C.G.cardT > 0) {
      C.G.cardT -= dt;
      if (C.G.cardT <= 0) C.ui.card.classList.remove("show");
    }
    if (C.G.over) return;
    C.G.t += dt;
    if (p.atkCd > 0) p.atkCd -= dt;
    if (p.inv > 0) p.inv -= dt;
    if (p.flashT > 0) p.flashT -= dt;
    if (p.rollCd > 0) p.rollCd -= dt;
    if (p.cloakT > 0) p.cloakT -= dt;
    if (p.surveyT > 0) p.surveyT -= dt;
    // Pocket Armory: a fresh draw every 18s while it's in hand.
    if (p.weapon && p.weapon.armory) {
      p.armoryT = (p.armoryT == null ? 18 : p.armoryT) - dt;
      if (p.armoryT <= 0) {
        p.armoryT = 18;
        const res = C.rollArmoryWeapon(p.weapon.armory);
        p.weapon.name = res.name;
        p.weapon.dmg = Math.max(1, Math.round(res.rarity / 2)) + 1;
        p.weapon.element = C.weaponElement(res.name);
        p.weapon.pierce = C.weaponPierce(res.name, res.description);
        C.syncDmg();
        C.floater(p.x, p.y - 30, "🔄 " + res.name.slice(0, 20), "#ffe066");
        C.updateHud();
      }
    }
    if (p.rollT > 0) {
      p.rollT -= dt;
      if (p.rollT <= 0) { p.dashDx = null; p.dashDy = null; p.dashSpd = 0; }
    }
    for (const s of p.slots) if (s.cdLeft > 0) s.cdLeft -= dt;
    if (C.G.shake > 0) C.G.shake -= dt;
    room.alert = Math.max(0, room.alert - dt);

    // Player statuses: burn seeps through invulnerability, slow drags movement.
    const ps = p.statuses;
    if (ps.burn && ps.burn.t > 0) {
      ps.burn.t -= dt;
      p.hp -= ps.burn.power * dt;
      if (p.hp <= 0) { C.die(); C.updateHud(); return; }
    }
    let spd = C.moveSpeed() * (p.moveMult || 1) * (p.mount ? p.mount.speedMult : 1);
    p.mana = Math.min(C.manaMax(), p.mana + C.manaRegen() * dt);
    if (ps.slow && ps.slow.t > 0) { spd *= ps.slow.power; ps.slow.t -= dt; }
    if (p.surge && p.surge.t > 0) {
      p.surge.t -= dt;
      spd *= p.surge.spdMult;
      if (p.surge.t <= 0) p.surge = null;
    }
    const stance = (p.stance && p.stance.t > 0) ? p.stance.kind : null;
    if (p.stance && p.stance.t > 0) {
      p.stance.t -= dt;
      if (p.stance.t <= 0) { p.stance = null; C.floater(p.x, p.y - 30, "stance fades", "#8b93a3"); }
    }
    if (stance === "carapace") spd *= 0.9;
    if (stance === "wings") spd *= 1.3;

    // Timed feats.
    if (!C.G.feats.pacifist && C.G.t > 300 && C.G.kills === 0) {
      C.G.feats.pacifist = 1;
      p.tickets.gold++;
      C.showCard("Feat: Ghost (5:00 pacifist)", "+1× Gold Trait ticket.", "", 3000);
    }
    if (!C.G.feats.deep && room.depth >= 3) {
      C.G.feats.deep = 1;
      p.tickets.gold++;
      C.showCard("Feat: High roller (depth 3)", "+1× Gold Random ticket.", "", 3000);
      C.resolveCurses();
    }

    // Movement: free to roam mid-pull, maze walls block.
    let [mx, my] = moveInput();
    p.moving = !!(mx || my);
    if (p.moving) {
      p.dustT = (p.dustT || 0) + dt;
      if (p.dustT > 0.14) {
        p.dustT = 0;
        C.spawnP(p.x + (Math.random() * 10 - 5), p.y + 10, 1,
          { col: "#3a3344", spd: 25, life: 0.35, size: 2 });
      }
    }
    if (mx || my) {
      const l = Math.hypot(mx, my); mx /= l; my /= l;
      p.x += mx * spd * dt;
      p.y += my * spd * dt;
      p.facing = Math.atan2(my, mx);
    }
    if (C.keys[" "] && p.rollCd <= 0 && (mx || my)) { p.rollT = 0.32; p.rollCd = p.rollCdMax || 5; }
    if (p.regen && !p.regenOff && p.hp < p.maxHp) {
      p.regenT += dt;
      if (p.regenT >= 30) {
        p.regenT = 0; p.hp += 1;
        C.floater(p.x, p.y - 24, "+1 HP", "#11d939");
        C.updateHud();
      }
    }
    if (p.threatDecayT && C.G.threat > 0) {
      p.threatDecayT += dt;
      if (p.threatDecayT >= 60) {
        p.threatDecayT = 0; C.G.threat -= 1;
        C.showCard("Threat cools to ★" + C.G.threat, "You lay low. Security forgets... a little.", "", 2200);
      }
    }
    if (p.rollT > 0) {
      const dx = p.dashDx != null ? p.dashDx : mx;
      const dy = p.dashDy != null ? p.dashDy : my;
      const sp = p.dashSpd || 260;
      p.x += dx * sp * dt;
      p.y += dy * sp * dt;
    }
    // Wings fly over maze walls and machines (outer walls still hold).
    if (stance !== "wings") {
      const fixed = C.collideCircle(p.x, p.y, p.r, C.solids(room));
      p.x = fixed[0]; p.y = fixed[1];
    }

    updateDoors(p);

    // Edge-triggered E: one press starts one pull, then walk away.
    const eDown = !!C.keys["e"];
    if (eDown && !prevE) C.tryStartPull();
    prevE = eDown;
    const pDown = !!C.keys["p"];
    if (pDown && !prevP) C.rotatePets();
    prevP = pDown;
    const bDown = !!C.keys["b"];
    if (bDown && !prevB) C.openDraft({ kind: "manage" });
    prevB = bDown;
    C.updatePulls(dt);
    C.updatePickups(dt);

    // J/click: slot-1 power, else legacy weapon attack. K/L: slots 2-3.
    if (C.takeAttack()) {
      if (p.slots[0]) C.runActive(0);
      else if (p.weapon) C.tryAttack();
    }
    if (C.keys["k"]) C.runActive(1);
    if (C.keys["l"]) C.runActive(2);
    // F always fires the weapon. Q uses satchel, C cycles it.
    if (C.takeWeapon() && p.weapon) C.tryAttack();
    if (C.keys["q"] && !prevQ) C.useConsumable();
    prevQ = !!C.keys["q"];
    if (C.keys["c"] && !prevC) C.cycleSatchel();
    prevC = !!C.keys["c"];
    C.tickRestock(dt);

    C.updateGuards(dt);
    C.updateRam(dt);
    C.updatePets(dt);
    C.updateProjectiles(dt);
    C.updateFx(dt);
    C.updateTempWalls(dt);
    C.updatePlaced(dt);
    updateWaves(dt, room);
    for (const f of C.floaters) f.t -= dt;
    C.floaters = C.floaters.filter(f => f.t > 0);
    C.updateHud();
  };
})(window.Casino);
