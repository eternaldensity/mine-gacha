"use strict";
/* HUD. Depends on: config, dom, state (runtime). */
(function (C) {
  C.updateHud = function () {
    const p = C.G.p, room = C.curRoom();
    C.el("hCoins").textContent = "🪙 " + p.coins;
    C.el("hParts").textContent = "🧩 " + (p.parts || 0);
    C.el("hHp").textContent = "❤ " + Math.max(0, p.hp) + "/" + p.maxHp;
    C.el("hThreat").textContent = "★ Threat " + C.G.threat;
    C.el("hDepth").textContent = "🚪 Depth " + room.depth + " · Danger " + room.danger.toFixed(1);
    C.el("hTime").textContent = "⏱ " + C.fmtTime(C.G.t) + " · ☠" + C.G.kills + " · 🎰" + C.G.pulls;
    const prim = p.slots[0] ? "[" + C.SLOT_KEYS[0] + "] " + p.slots[0].name : null;
    const ammoTxt = (p.weapon && p.weapon.ranged) ? " [" + (p.ammo || 0) + "💥]" : "";
    C.el("hWeapon").textContent = prim || (p.weapon
      ? "🔫 " + p.weapon.name.slice(0, 22) + ammoTxt
      : "🥊 Unarmed (J does nothing)");
    const satBits = [];
    for (const k of C.SAT_ORDER) {
      const st = p.satchel[k];
      if (!st) continue;
      const sel = (p.satSel === k) ? "▶" : "";
      satBits.push("<span class='bchip" + (p.satSel === k ? " sel" : "") + "'>" + sel +
        (k === "bomb" ? "🧨" : k === "potion" ? "🧪" : "👻") + " " + k + "×" + st.qty +
        (st.qty < 3 && p.satSel === k ? " (+)" : "") + "</span>");
    }
    C.el("satchel").innerHTML = "[Q] use · [C] cycle · " + (satBits.join("") || "empty: prizes stock it");
    const st = p.stats || {};
    const statChip = k => "<span class='tick' title='" + (C.STAT_BLURB[k] || k) + "'>" +
      k + " " + (st[k] || 10) + "</span>";
    C.el("stats").innerHTML = C.STAT_NAMES.map(statChip).join("") +
      "<span class='tick' title='mana pool'>⚡" + Math.floor(p.mana) + "/" + C.manaMax() + "</span>" +
      "<span class='tick'>move " + Math.round(C.moveSpeed()) + " · pull ×" +
      C.pullMul().toFixed(2) + " · sat " + C.satCap() + "</span>";
    const mf = Math.max(0, Math.min(1, p.mana / C.manaMax()));
    const mb = C.el("manabar").firstChild;
    if (mb) mb.style.width = (mf * 100).toFixed(1) + "%";
    const n = C.maxSlots();
    let abits = "";
    for (let i = 0; i < n; i++) {
      const ab = p.slots[i];
      if (!ab) {
        abits += "<span class='tick'>[" + C.SLOT_KEYS[i] + "], </span>";
        continue;
      }
      const cost = C.MANA_COSTS[ab.op] || 0;
      const cooling = ab.cdLeft > 0;
      const broke = p.mana < cost;
      abits += "<span class='tick" + (cooling ? " cool" : "") + "'>[" + C.SLOT_KEYS[i] + "] " +
        esc(ab.name) + " (" + ab.op + (ab.element ? "/" + ab.element : "") + ") " +
        (cooling ? ab.cdLeft.toFixed(1) + "s · " : "") + (broke ? "drained" : cost + "⚡") + "</span>";
    }
    C.el("actives").innerHTML = abits;
    C.el("tickets").innerHTML = C.TIERS.map(t =>
      "<span class='tick' style='border-color:" + t.color + "'>" +
      t.label.slice(0, 4) + "×" + (p.tickets[t.id] || 0) + "</span>").join("");
    const bits = [];
    if (p.weapon) bits.push("<span class='bchip'>🔫 " + esc(p.weapon.name) + " " + p.dmg + "dmg</span>");
    p.slots.forEach((s, i) => bits.push("<span class='bchip'>[" + C.SLOT_KEYS[i] + "] " +
      esc(s.name) + " (" + s.op + (s.element ? "/" + s.element : "") + ")</span>"));
    if (p.stash.length) bits.push("<span class='bchip'>+" + p.stash.length + " stashed</span>");
    p.pets.forEach(pt => bits.push("<span class='bchip pet'>🐾 " + esc(pt.name) +
      " (" + (pt.role || "gunner") + ")</span>"));
    if (p.stable.length) bits.push("<span class='bchip pet'>+" + p.stable.length + " stabled (P)</span>");
    if (p.armorPct > 0) bits.push("<span class='bchip'>🛡 block " + Math.round(p.armorPct * 100) + "%</span>");
    if ((p.coinBonus || 0) > 0) bits.push("<span class='bchip'>🪙 coins +" + Math.round(p.coinBonus * 100) + "%</span>");
    if ((p.pickupBonus || 0) > 0) bits.push("<span class='bchip'>🧲 pickup +" + p.pickupBonus + "</span>");
    if ((p.timeBonus || 0) > 0) bits.push("<span class='bchip'>⏳ foe slow " + Math.round(p.timeBonus * 100) + "%</span>");
    if (p.cloakT > 0) bits.push("<span class='bchip'>👻 cloak " + p.cloakT.toFixed(0) + "s</span>");
    if (p.mount) bits.push("<span class='bchip'>" + p.mount.glyph + " " + esc(p.mount.name) + " (" + p.mount.hp + ")</span>");
    if (p.presence > 0) bits.push("<span class='bchip'>🎭 presence " + Math.round(p.presence * 100) + "%</span>");
    (C.G.curses || []).forEach(c => bits.push("<span class='bchip'>🎲 " +
      esc(c.label) + " (" + c.tier + (c.edge ? ": " + esc(c.edge) : "") + (c.resolved ? ", ✓" : "") + ")</span>"));
    p.buildLog.forEach(b => bits.push("<span class='bchip " + b.cls + "'>" + esc(b.txt) + "</span>"));
    C.el("build").innerHTML = bits.join("") || "<span class='bchip'>No prizes yet: pull a gacha.</span>";

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  };
})(window.Casino);
