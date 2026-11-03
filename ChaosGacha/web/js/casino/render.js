"use strict";
/* Canvas renderer: maze walls, big machines with in-place reels,
 * floor pickups, floaters. Depends on: config, dom, state, slots. */
(function (C) {
  function rr(x, y, w, h, r) {
    const ctx = C.ctx;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
    else ctx.rect(x, y, w, h);
  }

  function drawWalls(room) {
    const ctx = C.ctx;
    for (const wl of (room.tempWalls || [])) {
      if (wl.barricade) {
        ctx.fillStyle = "#3a3a10";
        ctx.fillRect(wl.x + wl.w / 2 - 8, wl.y + wl.h / 2 - 8, 16, 16);
        ctx.fillStyle = "#ffe066"; ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
        ctx.fillText("🚧", wl.x + wl.w / 2, wl.y + wl.h / 2 + 4);
        continue;
      }
      ctx.globalAlpha = Math.min(1, 0.35 + wl.t * 0.15);
      ctx.fillStyle = "#2e6b5e";
      ctx.fillRect(wl.x, wl.y, wl.w, wl.h);
      ctx.fillStyle = "#7df9ff";
      if (wl.h < wl.w) ctx.fillRect(wl.x, wl.y, wl.w, 3);
      else ctx.fillRect(wl.x, wl.y, 3, wl.h);
      ctx.globalAlpha = 1;
    }
    for (const wl of room.walls) {
      ctx.fillStyle = "#2e2342";
      ctx.fillRect(wl.x, wl.y, wl.w, wl.h);
      ctx.fillStyle = "#4a3a6b"; // lit top edge
      ctx.fillRect(wl.x, wl.y, wl.w, 3);
      ctx.strokeStyle = "#a58fe0"; ctx.lineWidth = 3; // outline lifts it off the carpet
      ctx.strokeRect(wl.x - 1.5, wl.y - 1.5, wl.w + 3, wl.h + 3);
      ctx.strokeStyle = "#171021"; ctx.lineWidth = 1;
      ctx.strokeRect(wl.x + 3.5, wl.y + 3.5, wl.w - 7, wl.h - 7);
    }
  }

  // Vertical fade so the tape reads as a wheel seen edge-on.
  // edge = "dark" (gacha strip) or "paper" (slot windows).
  function reelFade(ctx, x, y, w, h, edge) {
    const c = edge === "paper" ? "232,228,218" : "8,10,14";
    const gr = ctx.createLinearGradient(0, y, 0, y + h);
    gr.addColorStop(0, "rgba(" + c + ",.8)");
    gr.addColorStop(0.3, "rgba(" + c + ",0)");
    gr.addColorStop(0.7, "rgba(" + c + ",0)");
    gr.addColorStop(1, "rgba(" + c + ",.8)");
    ctx.fillStyle = gr;
    ctx.fillRect(x, y, w, h);
  }

  // Classic slot ink on paper. BAR gets its own plaque.
  function reelSymbol(ctx, s, x, yc, locked, tierColor) {
    if (s === "BAR") {
      ctx.fillStyle = locked ? tierColor : "#1a1a22";
      const w = 22;
      ctx.fillRect(x - w / 2, yc - 9, w, 18);
      ctx.fillStyle = "#f5f1e6";
      ctx.font = "bold 9px monospace";
      ctx.fillText("BAR", x, yc + 1);
      return;
    }
    ctx.fillStyle = s === "7" ? "#c02020"
      : s === "★" ? "#b8860b"
      : s === "♦" || s === "♥" ? "#c02020"
      : s === "🪙" ? "#8a6d1c"
      : locked ? tierColor : "#555566";
    ctx.font = symFont(s);
    ctx.fillText(s.length > 3 ? s.slice(0, 3) : s, x, yc);
  }

  function symFont(s) {
    return s.length > 1 ? "bold 10px monospace" : "bold 15px monospace";
  }

  // One spinning slot window: a wrapping symbol tape scrolling downward,
  // easing onto the target symbol with the tier color on lock.
  function drawSlotReelWindow(m, t, i) {
    const ctx = C.ctx;
    const reel = m.pull.reels[i];
    const x = m.x - 39 + i * 27, y = m.y - 16, w = 25, h = 30;
    const H = C.REEL_H, N = C.SYMS.length;
    ctx.save();
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
    ctx.fillStyle = "#e8e4da";
    ctx.fillRect(x, y, w, h);
    // Tape index q drifts with pos; rows tile around the window center and
    // move downward as pos grows (screenY rises with q for fixed k).
    const q = reel.pos / H, k0 = Math.floor(q);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (let j = -1; j <= 2; j++) {
      const k = k0 + j;
      const s = C.SYMS[C.pmod(k, N)];
      const yc = y + h / 2 + (q - k) * H;
      const edge = Math.abs(yc - (y + h / 2)) / (h / 2); // 0 center, 1+ edge
      ctx.globalAlpha = Math.max(0.35, 1 - edge * 0.5);
      reelSymbol(ctx, s, x + w / 2, yc, reel.state === "locked", t.color);
    }
    ctx.globalAlpha = 1;
    reelFade(ctx, x, y, w, h, "paper");
    ctx.restore();
    ctx.strokeStyle = reel.state === "locked" ? t.color : "#333a47";
    ctx.lineWidth = reel.state === "locked" ? 2 : 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  }

  function slotWindows(m, t) {
    const ctx = C.ctx;
    if (m.pull) {
      for (let i = 0; i < 3; i++) drawSlotReelWindow(m, t, i);
      return;
    }
    // Idle: show the last result dimmed on paper.
    const labels = m.idleSyms || ["◈", "◈", "◈"];
    for (let i = 0; i < 3; i++) {
      const x = m.x - 39 + i * 27, y = m.y - 16;
      ctx.fillStyle = "#e8e4da";
      ctx.fillRect(x, y, 25, 30);
      ctx.strokeStyle = "#333a47"; ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, 24, 29);
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      reelSymbol(ctx, String(labels[i]), x + 12.5, y + 15, false, m.color);
      ctx.textBaseline = "alphabetic";
    }
  }



  // Chasing marquee bulbs across a machine header.
  function marquee(m, t, y, w) {
    const ctx = C.ctx;
    const fast = !!m.pull;
    const tick = Math.floor(C.G.t * (fast ? 10 : 2.5));
    for (let i = 0; i < 8; i++) {
      const on = ((i - tick) % 4 + 4) % 4 < 2;
      ctx.fillStyle = on ? "#ffe066" : "#4a4430";
      const bx = m.x - w / 2 + 6 + i * ((w - 12) / 7);
      ctx.fillRect(bx - 2, y, 4, 4);
    }
  }

  // Slot cabinet: marquee, reel glass, coin tray, side lever, damage cracks.
  function drawSlotCabinet(m, t, near, hw, hh) {
    const ctx = C.ctx;
    // Marquee band with tier label.
    ctx.fillStyle = "#1a1e28";
    ctx.fillRect(m.x - hw + 4, m.y - hh + 4, C.MW - 8, 15);
    marquee(m, t, m.y - hh + 6, C.MW - 8);
    ctx.fillStyle = m.color; ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
    ctx.fillText(t.label.toUpperCase().slice(0, 9) + (m.playerMade ? " ★" : ""),
      m.x, m.y - hh + 16);
    slotWindows(m, t);
    // Coin tray.
    ctx.fillStyle = "#05060a";
    ctx.fillRect(m.x - 30, m.y + hh - 13, 60, 8);
    ctx.strokeStyle = m.color; ctx.lineWidth = 1;
    ctx.strokeRect(m.x - 30, m.y + hh - 13, 60, 8);
    ctx.fillStyle = m.pull ? "#ffe066" : "#c7ccd6";
    ctx.font = "9px monospace";
    const cost = C.slotCost(t) + "c";
    ctx.fillText(m.pull ? "RUNNING…" : cost, m.x, m.y + hh - 17);
    // Side lever follows pull progress.
    const frac = m.pull ? Math.min(1, m.pull.t / m.pull.dur) : 0;
    const px = m.x + hw + 5, py = m.y - 6;
    ctx.strokeStyle = "#8b93a3"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px + 4, py - 2); ctx.stroke();
    ctx.fillStyle = "#ff4444";
    const kx = px + 4 + 3, ky = py - 2 - 12 + frac * 22;
    ctx.beginPath(); ctx.arc(kx, ky, 4, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "#8b93a3"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(px + 4, py - 2); ctx.lineTo(kx, ky); ctx.stroke();
    // Battle damage.
    if (m.maxHp && m.hp <= m.maxHp / 2) {
      ctx.strokeStyle = "rgba(0,0,0,.8)"; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(m.x - hw + 8, m.y - hh + 22);
      ctx.lineTo(m.x - hw + 22, m.y - 2);
      ctx.lineTo(m.x - hw + 14, m.y + 12);
      ctx.stroke();
    }
  }

  // Gacha globe: glass ball with bouncing capsules + crank base + name strip.
  function drawGachaCabinet(m, t, near, hw, hh) {
    const ctx = C.ctx;
    ctx.fillStyle = m.color; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
    ctx.fillText("🎲 " + t.label.toUpperCase().slice(0, 9) + (m.playerMade ? " ★" : ""),
      m.x, m.y - hh + 13);
    // Globe.
    const gx = m.x - 24, gy = m.y + 2, gr = 14;
    ctx.fillStyle = "#101c30";
    ctx.beginPath(); ctx.arc(gx, gy, gr, 0, Math.PI * 2); ctx.fill();
    if (m.pull) {
      for (let i = 0; i < 3; i++) {
        const a = C.G.t * 5 + i * 2.1;
        ctx.fillStyle = t.color;
        ctx.fillRect(gx + Math.cos(a) * 7 - 2, gy + Math.sin(a) * 7 - 2, 4, 4);
      }
    } else {
      ctx.fillStyle = t.color;
      ctx.fillRect(gx - 8, gy + 2, 4, 4);
      ctx.fillRect(gx - 1, gy - 6, 4, 4);
      ctx.fillRect(gx + 4, gy + 4, 4, 4);
    }
    ctx.strokeStyle = m.color; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(gx, gy, gr, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,.35)";
    ctx.fillRect(gx - 9, gy - 11, 7, 3);
    // Crank + category + cost, right column.
    ctx.strokeStyle = "#8b93a3"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(m.x + 22, m.y - 2, 5, 0, Math.PI * 2); ctx.stroke();
    if (m.pull) {
      const a = C.G.t * 9;
      ctx.fillStyle = "#ffe066";
      ctx.fillRect(m.x + 22 + Math.cos(a) * 5 - 1, m.y - 2 + Math.sin(a) * 5 - 1, 3, 3);
    }
    ctx.fillStyle = "#fff"; ctx.font = "bold 10px monospace";
    ctx.fillText((m.cat || "?").toUpperCase().slice(0, 8), m.x + 22, m.y + 8);
    ctx.fillStyle = m.pull ? "#ffe066" : t.color; ctx.font = "10px monospace";
    ctx.fillText(m.pull ? "WORKING" : "1×" + t.label.slice(0, 5), m.x + 22, m.y + 19);
    gachaStrip(m, t);
  }

  // Bottom name strip: scrolling decoys, winner on lock, category when idle.
  function gachaStrip(m, t) {
    const ctx = C.ctx;
    const x = m.x - 42, y = m.y + 24, w = 84, h = 14;
    ctx.fillStyle = "#10131a";
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = m.pull ? t.color : "#333a47"; ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "9px monospace";
    if (m.pull) {
      const pull = m.pull, reel = pull.reel;
      const strip = pull.gacha.strip.length ? pull.gacha.strip
        : [{ name: pull.gacha.res.name, rarity: pull.gacha.res.rarity }];
      const H = C.GREEL_H, L = strip.length;
      ctx.save();
      ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
      const q = reel.pos / H, k0 = Math.floor(q);
      for (let j = -1; j <= 2; j++) {
        const k = k0 + j;
        const e = strip[C.pmod(k, L)];
        const yc = y + h / 2 + (q - k) * H;
        const edge = Math.abs(yc - (y + h / 2)) / (h / 2);
        ctx.globalAlpha = Math.max(0.3, 1 - edge * 0.55);
        ctx.fillStyle = C.rarityColor(e.rarity);
        ctx.fillText(String(e.name).slice(0, 20), m.x, yc);
      }
      if (reel.state !== "spin") {
        const a = reel.state === "locked" ? 1 : Math.min(1, reel.landT / 0.45);
        ctx.globalAlpha = a;
        ctx.fillStyle = "#10131a";
        ctx.fillRect(x, y, w, h);
        ctx.fillStyle = C.rarityColor(pull.gacha.res.rarity);
        ctx.fillText("▶ " + String(pull.gacha.res.name).slice(0, 14) + " ◀", m.x, y + h / 2);
      }
      ctx.globalAlpha = 1;
      ctx.restore();
    } else if (m.lastPrize) {
      ctx.fillStyle = C.rarityColor(m.lastPrize.rarity);
      ctx.fillText(String(m.lastPrize.name).slice(0, 15), m.x, y + h / 2);
    } else {
      ctx.fillStyle = "#8b93a3";
      ctx.fillText("◈ TICKETS ◈", m.x, y + h / 2);
    }
    ctx.textBaseline = "alphabetic";
  }

  function drawMachines(room, near) {
    const ctx = C.ctx;
    const hw = C.MW / 2, hh = C.MH / 2;
    for (const m of room.machines) {
      const t = C.tierById(m.tier);
      // Drop shadow + body + tier trim.
      ctx.fillStyle = "rgba(0,0,0,.4)";
      rr(m.x - hw + 3, m.y - hh + 5, C.MW, C.MH, 8); ctx.fill();
      ctx.fillStyle = m.pull ? "#141824" : "#0d0f15";
      rr(m.x - hw, m.y - hh, C.MW, C.MH, 8); ctx.fill();
      ctx.lineWidth = near === m ? 3 : 2;
      ctx.strokeStyle = near === m ? "#fff" : m.color;
      ctx.stroke();
      if (m.kind === "slot") drawSlotCabinet(m, t, near, hw, hh);
      else drawGachaCabinet(m, t, near, hw, hh);
      if (near === m) {
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 1;
        ctx.strokeRect(m.x - hw, m.y - hh, C.MW, C.MH);
        // Channel bar above machine.
        if (m.pull) {
          const f = Math.min(1, m.pull.t / m.pull.dur);
          ctx.fillStyle = "#000"; ctx.fillRect(m.x - hw + 6, m.y - hh - 11, C.MW - 12, 7);
          ctx.fillStyle = m.pull.fin != null ? "#11d939" : t.color;
          ctx.fillRect(m.x - hw + 7, m.y - hh - 10, (C.MW - 14) * f, 5);
        }
      }
    }
  }

  function drawPickups(room) {
    const ctx = C.ctx;
    ctx.textAlign = "center";
    for (const pk of room.pickups) {
      const bobY = pk.y + Math.sin(pk.bob * 4) * 3;
      // Expanding gold ring so finished loot calls you back.
      const rs = ((pk.age || 0) * 26) % 22;
      ctx.globalAlpha = Math.max(0, 0.8 - rs / 22 * 0.8);
      ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 2;
      ctx.strokeRect(pk.x - 8 - rs / 2, bobY - 8 - rs / 2, 16 + rs, 16 + rs);
      ctx.globalAlpha = 1;
      if (pk.kind === "ammo") {
        ctx.fillStyle = "#3a3a3a";
        ctx.fillRect(pk.x - 8, bobY - 8, 16, 16);
        ctx.fillStyle = "#ffd166";
        ctx.fillRect(pk.x - 3, bobY - 6, 6, 12);
        ctx.fillStyle = "#fff"; ctx.font = "10px monospace";
        ctx.fillText("+" + pk.amount, pk.x, bobY + 22);
      } else if (pk.kind === "parts") {
        ctx.fillStyle = "#5a4a1a";
        ctx.fillRect(pk.x - 8, bobY - 8, 16, 16);
        ctx.fillStyle = "#ffe066"; ctx.font = "bold 11px monospace";
        ctx.fillText("⚙", pk.x, bobY + 4);
        ctx.fillStyle = "#ffe066"; ctx.font = "10px monospace";
        ctx.fillText("+" + pk.amount, pk.x, bobY + 22);
      } else if (pk.kind === "coins") {
        ctx.fillStyle = "#8a6d1c";
        ctx.fillRect(pk.x - 8, bobY - 8, 16, 16);
        ctx.fillStyle = "#ffe066";
        ctx.fillRect(pk.x - 6, bobY - 6, 12, 12);
        ctx.fillStyle = "#8a6d1c"; ctx.font = "bold 10px monospace";
        ctx.fillText("c", pk.x, bobY + 4);
        ctx.fillStyle = "#ffe066"; ctx.font = "10px monospace";
        ctx.fillText("+" + pk.amount, pk.x, bobY + 22);
      } else if (pk.kind === "ticket") {
        const t = C.tierById(pk.tier);
        ctx.fillStyle = "#e8e4da";
        ctx.fillRect(pk.x - 10, bobY - 7, 20, 14);
        ctx.strokeStyle = t.color; ctx.lineWidth = 2;
        ctx.strokeRect(pk.x - 10, bobY - 7, 20, 14);
        ctx.fillStyle = "#111"; ctx.font = "bold 10px monospace";
        ctx.fillText("T", pk.x, bobY + 4);
        ctx.fillStyle = t.color; ctx.font = "10px monospace";
        ctx.fillText(pk.tier.slice(0, 5), pk.x, bobY + 22);
      } else if (pk.kind === "prize") {
        const col = C.rarityColor(pk.res.rarity);
        ctx.fillStyle = col;
        ctx.fillRect(pk.x - 9, bobY - 9, 18, 18);
        ctx.fillStyle = "#fff"; ctx.font = "bold 12px monospace";
        ctx.fillText("★", pk.x, bobY + 5);
        ctx.fillStyle = col; ctx.font = "bold 10px monospace";
        ctx.fillText(String(pk.res.name).slice(0, 22), pk.x, bobY + 24);
      }
    }
  }

  function drawGuards(room) {
    const ctx = C.ctx;
    const BODY = { guard: "#111", pitboss: "#3a2a5a", enforcer: "#5a1a1a",
      bruiser: "#4a2a12", stalker: "#1a3a3a", hexer: "#2a1a4a", medic: "#1a3a1a",
      captain: "#4a3a0a", handler: "#3a2a1a", hound: "#222",
      warlord: "#4a0a0a", collector: "#3a0a0a", roller: "#3a2f0a" };
    for (const gd of room.guards) {
      const sc = gd.size || 1; // bosses (and hounds) break the mold
      const flash = gd.flashT > 0;
      if (gd.type === "hound") {
        const hf = gd.chase ? Math.floor(C.G.t * 10) % 2 : 0;
        C.drawSprite("hound_" + hf, gd.x, gd.y - 4, {
          scale: 2 * sc, flip: Math.cos(gd.facing || 0) < 0, flash });
      } else {
        const gf = gd.chase ? Math.floor(C.G.t * 8 + ((gd.phase || 0) * 2)) % 2 : 0;
        const gd2 = C.spriteDir(gd.facing);
        C.drawSprite("guard_" + gf, gd.x, gd.y - 2, {
          scale: 2 * sc, flip: gd2.flip,
          palette: C.RANK_PAL[gd.type] || C.RANK_PAL.guard, flash });
      }
      if (gd.type === "collector") {
        ctx.fillStyle = "#ffe066"; ctx.font = "bold 14px monospace"; ctx.textAlign = "center";
        ctx.fillText("💀", gd.x, gd.y - 24 * sc);
      } else if (gd.type === "roller") {
        ctx.fillStyle = "#ffe066"; ctx.font = "bold 14px monospace"; ctx.textAlign = "center";
        ctx.fillText("🎲", gd.x, gd.y - 24 * sc);
      }
      if (gd.chase) {
        ctx.fillStyle = "#ff2222"; ctx.font = "bold 14px monospace"; ctx.textAlign = "center";
        ctx.fillText("!", gd.x, gd.y - 24);
      }
      // Pacified guards are friends (dim ♪, never re-acquire).
      if (gd.pacified) {
        ctx.fillStyle = "#11d939"; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText("♪", gd.x, gd.y - 32);
      }
      // Possessed guards answer to you now (purple ⁉).
      if (gd.possessed && gd.possessed > 0) {
        ctx.strokeStyle = "#c77dff"; ctx.lineWidth = 2;
        ctx.strokeRect(gd.x - 12, gd.y - 21, 24, 30);
        ctx.fillStyle = "#c77dff"; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText("⁉", gd.x, gd.y - 32);
      }
      // Rank glyphs: bruiser B, medic +, captain ★, handler ?, warlord ♛.
      const GLYPH = { bruiser: ["B", "#c98a4a"], medic: ["+", "#11d939"],
        captain: ["★", "#ffe066"], handler: ["?", "#ff9c41"], warlord: ["♛", "#ff5555"] }[gd.type];
      if (GLYPH) {
        ctx.fillStyle = GLYPH[1]; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText(GLYPH[0], gd.x, gd.y - 32);
      }
      // Elite affix glyph: shielded ◈, elemental ✦ (element color), charger ».
      if (gd.affix === "shielded") {
        ctx.fillStyle = "#8b93a3"; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText("◈", gd.x, gd.y - 32);
      } else if (gd.affix === "elemental") {
        ctx.fillStyle = gd.element === "fire" ? "#ff8c00" : "#aed1d1";
        ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText("✦", gd.x, gd.y - 32);
      } else if (gd.affix === "charger" && gd.type !== "warlord") {
        ctx.fillStyle = gd.teleT > 0 && Math.floor(C.G.t * 10) % 2 === 0 ? "#ff2222" : "#f7d40a";
        ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
        ctx.fillText("»", gd.x, gd.y - 32);
      }
      // Second affix (threat 4+ combos) rides below the first.
      if (gd.affix2 === "shielded") {
        ctx.fillStyle = "#8b93a3"; ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
        ctx.fillText("◈", gd.x, gd.y - 41);
      } else if (gd.affix2 === "elemental") {
        ctx.fillStyle = gd.element === "fire" ? "#ff8c00" : "#aed1d1";
        ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
        ctx.fillText("✦", gd.x, gd.y - 41);
      } else if (gd.affix2 === "charger") {
        ctx.fillStyle = "#f7d40a"; ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
        ctx.fillText("»", gd.x, gd.y - 41);
      }
      // Charger telegraph: flashing outline while winding up.
      if (gd.teleT > 0 && Math.floor(C.G.t * 10) % 2 === 0) {
        ctx.strokeStyle = "#ff2222"; ctx.lineWidth = 2;
        ctx.strokeRect(gd.x - 12, gd.y - 21, 24, 30);
      }
      // Burning guards flicker orange.
      if (gd.statuses.burn && gd.statuses.burn.t > 0 && Math.floor(C.G.t * 8) % 2 === 0) {
        ctx.fillStyle = "rgba(255,140,0,.45)";
        ctx.fillRect(gd.x - 9, gd.y - 12, 18, 24);
      }
      if (gd.shield > 0) {
        ctx.fillStyle = "#400"; ctx.fillRect(gd.x - 10, gd.y - 32, 20, 3);
        ctx.fillStyle = "#7df9ff";
        ctx.fillRect(gd.x - 10, gd.y - 32, 20 * Math.max(0, gd.shield) / 10, 3);
      }
      ctx.fillStyle = "#400"; ctx.fillRect(gd.x - 10, gd.y - 28, 20, 3);
      ctx.fillStyle = "#f66";
      ctx.fillRect(gd.x - 10, gd.y - 28, 20 * Math.max(0, gd.hp) / 6, 3);
    }
  }

  function dangerColor(d) {
    if (d < 2.5) return "#11d939";
    if (d < 4.5) return "#f7d40a";
    return "#ff8c00";
  }

  // Dark pill so depth/danger always reads against the carpet.
  function drawDepthPill(room) {
    const ctx = C.ctx;
    ctx.font = "bold 12px monospace";
    const label = "DEPTH " + room.depth + " · DANGER " + room.danger.toFixed(1);
    const w = ctx.measureText(label).width + 20;
    const x = C.WALL + 8, y = 8;
    ctx.fillStyle = "rgba(5,6,10,.88)";
    rr(x, y, w, 24, 12); ctx.fill();
    ctx.strokeStyle = dangerColor(room.danger); ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = "#fff"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    ctx.fillText("DEPTH " + room.depth + " · ", x + 10, y + 13);
    const pre = ctx.measureText("DEPTH " + room.depth + " · ").width;
    ctx.fillStyle = dangerColor(room.danger);
    ctx.fillText("DANGER " + room.danger.toFixed(1), x + 10 + pre, y + 13);
    ctx.textBaseline = "alphabetic";
  }

  // Gold EXIT doorways with pulsing outward chevrons.
  function drawDoors() {
    const ctx = C.ctx, cx = C.W / 2, cy = C.H / 2, W2 = C.WALL;
    const surveyed = !!(C.G.p.survey || C.G.p.surveyT > 0);
    const intel = surveyed ? {
      N: C.neighborInfo(0, -1), S: C.neighborInfo(0, 1),
      W: C.neighborInfo(-1, 0), E: C.neighborInfo(1, 0),
    } : null;
    const postColor = (k) => (intel && intel[k].best) ? intel[k].best.color : "#ffe066";
    const bob = (Math.sin(C.G.t * 4) + 1) / 2; // 0..1 pulse
    const gold = "rgba(255,224,102," + (0.55 + 0.45 * bob).toFixed(2) + ")";
    // Mats inside the wall gaps.
    ctx.fillStyle = "#3a2f10";
    ctx.fillRect(cx - 34, 0, 68, W2);
    ctx.fillRect(cx - 34, C.H - W2, 68, W2);
    ctx.fillRect(0, cy - 34, W2, 68);
    ctx.fillRect(C.W - W2, cy - 34, W2, 68);
    // Side posts: gold, or best-machine color when surveyed.
    ctx.fillStyle = postColor("N");
    ctx.fillRect(cx - 36, 0, 3, W2); ctx.fillRect(cx + 33, 0, 3, W2);
    ctx.fillStyle = postColor("S");
    ctx.fillRect(cx - 36, C.H - W2, 3, W2); ctx.fillRect(cx + 33, C.H - W2, 3, W2);
    ctx.fillStyle = postColor("W");
    ctx.fillRect(0, cy - 36, W2, 3); ctx.fillRect(0, cy + 33, W2, 3);
    ctx.fillStyle = postColor("E");
    ctx.fillRect(C.W - W2, cy - 36, W2, 3); ctx.fillRect(C.W - W2, cy + 33, W2, 3);
    // EXIT labels inside the mats, each tagged with the depth beyond:
    // red = deadlier, green = safer, gray = same. Walk in to go through.
    const here = Math.abs(C.G.roomX) + Math.abs(C.G.roomY);
    const depths = {
      N: Math.abs(C.G.roomX) + Math.abs(C.G.roomY - 1),
      S: Math.abs(C.G.roomX) + Math.abs(C.G.roomY + 1),
      W: Math.abs(C.G.roomX - 1) + Math.abs(C.G.roomY),
      E: Math.abs(C.G.roomX + 1) + Math.abs(C.G.roomY),
    };
    function depthTag(d) {
      if (d > here) return { txt: "D" + d + " ▲", col: "#ff8888" };
      if (d < here) return { txt: "D" + d + " ▼", col: "#11d939" };
      return { txt: "D" + d + " ＝", col: "#c7ccd6" };
    }
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillStyle = "#ffe066"; ctx.font = "bold 11px monospace";
    ctx.fillText("EXIT", cx, W2 / 2 - 8);
    ctx.fillText("EXIT", cx, C.H - W2 / 2 - 8);
    ctx.fillText("EXIT", W2 / 2, cy - 8);
    ctx.fillText("EXIT", C.W - W2 / 2, cy - 8);
    ctx.font = "bold 10px monospace";
    const tags = { N: [cx, W2 / 2 + 9], S: [cx, C.H - W2 / 2 + 9],
      W: [W2 / 2, cy + 9], E: [C.W - W2 / 2, cy + 9] };
    for (const k of ["N", "S", "W", "E"]) {
      if (intel) {
        // Surveyed: depth + guard count; posts already show best machine.
        const inf = intel[k];
        const arrow = inf.depth > here ? "▲" : inf.depth < here ? "▼" : "＝";
        ctx.fillStyle = inf.depth > here ? "#ff8888" : inf.depth < here ? "#11d939" : "#c7ccd6";
        ctx.fillText("D" + inf.depth + arrow + "·" + inf.guards + "g", tags[k][0], tags[k][1]);
      } else {
        const tag = depthTag(depths[k]);
        ctx.fillStyle = tag.col;
        ctx.fillText(tag.txt, tags[k][0], tags[k][1]);
      }
    }
    // Outward chevrons just inside the room (door corridors stay clear).
    const off = 4 + bob * 7;
    ctx.strokeStyle = gold; ctx.lineWidth = 3; ctx.lineCap = "round";
    function chev(x, y, dx, dy) {
      // double chevron pointing along (dx, dy)
      for (let k = 0; k < 2; k++) {
        const bx = x + dx * k * 9, by = y + dy * k * 9;
        ctx.beginPath();
        ctx.moveTo(bx - dy * 8 - dx * 5, by - dx * 8 - dy * 5);
        ctx.lineTo(bx, by);
        ctx.lineTo(bx + dy * 8 - dx * 5, by + dx * 8 - dy * 5);
        ctx.stroke();
      }
    }
    chev(cx, W2 + 16 + off, 0, -1);
    chev(cx, C.H - W2 - 16 - off, 0, 1);
    chev(W2 + 16 + off, cy, -1, 0);
    chev(C.W - W2 - 16 - off, cy, 1, 0);
    ctx.textBaseline = "alphabetic";
  }

  // Player-built sentries (turrets aim at the nearest guard).
  function drawPlaced(room) {
    const ctx = C.ctx;
    for (const pl of room.placed) {
      if (pl.kind !== "turret") continue;
      ctx.fillStyle = "#2a2f3a";
      ctx.fillRect(pl.x - 11, pl.y - 11, 22, 22);
      ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 2;
      ctx.strokeRect(pl.x - 11, pl.y - 11, 22, 22);
      const g = C.nearestGuard(9999);
      const a = g ? Math.atan2(g.y - pl.y, g.x - pl.x) : 0;
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(pl.x, pl.y);
      ctx.lineTo(pl.x + Math.cos(a) * 16, pl.y + Math.sin(a) * 16); ctx.stroke();
      ctx.fillStyle = "#ffe066"; ctx.font = "9px monospace"; ctx.textAlign = "center";
      ctx.fillText(Math.ceil(pl.t) + "s", pl.x, pl.y + 24);
    }
  }

  // Expanding nova rings (gold) and lobbed telegraphs (red, pending).
  function drawRings() {
    const ctx = C.ctx;
    for (const rg of C.rings) {
      const f = rg.age / rg.max;
      ctx.globalAlpha = Math.max(0, 0.8 - f * 0.8);
      ctx.strokeStyle = rg.col || "#ffe066"; ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(rg.x, rg.y, Math.max(1, rg.r * f), 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (const d of C.delayed) {
      const pulse = 0.5 + 0.5 * Math.sin(C.G.t * 10);
      ctx.globalAlpha = 0.4 + 0.4 * pulse;
      ctx.strokeStyle = "#ff4444"; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = "#ff4444";
      ctx.font = "bold 12px monospace"; ctx.textAlign = "center";
      ctx.fillText("!", d.x, d.y - d.r - 6);
    }
    ctx.globalAlpha = 1;
    for (const b of C.beams) {
      const f = 1 - b.age / b.max;
      ctx.globalAlpha = Math.max(0, f);
      ctx.strokeStyle = "#fff2b0"; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.moveTo(b.x1, b.y1); ctx.lineTo(b.x2, b.y2); ctx.stroke();
      ctx.strokeStyle = "#ff8c00"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(b.x1, b.y1); ctx.lineTo(b.x2, b.y2); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  C.render = function () {
    const ctx = C.ctx, room = C.curRoom(), p = C.G.p;
    ctx.save();
    if (C.G.shake > 0) ctx.translate((Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6);
    // Floor carpet (vaults gild it).
    ctx.fillStyle = room.vault ? "#221a10" : "#191423";
    ctx.fillRect(0, 0, C.W, C.H);
    ctx.fillStyle = room.vault ? "#2e2413" : "#1e1830";
    for (let y = 0; y < C.H; y += 24) {
      for (let x = 0; x < C.W; x += 24) {
        if ((x + y) % 48 === 0) ctx.fillRect(x, y, 12, 12);
        // Deterministic speckle (stable per tile, no flicker).
        const h = ((x * 73856093) ^ (y * 19349663)) >>> 0;
        if (h % 7 === 0) {
          ctx.fillStyle = room.vault ? "#241b0e" : "#151020";
          ctx.fillRect(x + 5, y + 15, 2, 2);
          ctx.fillStyle = room.vault ? "#2e2413" : "#1e1830";
        }
      }
    }
    // Gold trim where carpet meets the walls + soft inner shadow.
    ctx.strokeStyle = "rgba(255,224,102,.16)"; ctx.lineWidth = 2;
    ctx.strokeRect(C.WALL + 2, C.WALL + 2, C.W - (C.WALL + 2) * 2, C.H - (C.WALL + 2) * 2);
    ctx.fillStyle = "rgba(0,0,0,.3)";
    ctx.fillRect(C.WALL, C.WALL, C.W - C.WALL * 2, 7);
    ctx.fillRect(C.WALL, C.H - C.WALL - 7, C.W - C.WALL * 2, 7);
    ctx.fillRect(C.WALL, C.WALL, 7, C.H - C.WALL * 2);
    ctx.fillRect(C.W - C.WALL - 7, C.WALL, 7, C.H - C.WALL * 2);
    if (room.vault) {
      ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 3;
      ctx.strokeRect(C.WALL + 6, C.WALL + 6, C.W - C.WALL * 2 - 12, C.H - C.WALL * 2 - 12);
    }
    // Walls + door gaps.
    ctx.fillStyle = "#2b2137";
    ctx.fillRect(0, 0, C.W, C.WALL); ctx.fillRect(0, C.H - C.WALL, C.W, C.WALL);
    ctx.fillRect(0, 0, C.WALL, C.H); ctx.fillRect(C.W - C.WALL, 0, C.WALL, C.H);
    drawDoors();
    drawDepthPill(room);

    drawWalls(room);
    // Scorch marks where machines died.
    for (const s of (room.scorch || [])) {
      ctx.globalAlpha = Math.max(0, 0.5 - (s.age || 0) * 0.025);
      ctx.fillStyle = "#050505";
      ctx.beginPath();
      ctx.ellipse(s.x, s.y, 34, 22, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    drawMachines(room, C.nearestMachine(false));
    drawPickups(room);
    drawPlaced(room);
    drawGuards(room);
    drawRings();

    for (const pr of C.projs) {
      const col = pr.foe ? "#ff5555" : "#ffe066";
      ctx.globalAlpha = 0.35;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(pr.x, pr.y, 7, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(pr.x, pr.y, 3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(pr.x, pr.y, 1.5, 0, Math.PI * 2); ctx.fill();
    }
    // Particles.
    for (const q of C.particles) {
      ctx.globalAlpha = Math.max(0, q.life / q.max);
      ctx.fillStyle = q.col;
      ctx.fillRect(q.x - q.size / 2, q.y - q.size / 2, q.size, q.size);
    }
    ctx.globalAlpha = 1;
    const PET_COLORS = { gunner: "#7df9ff", bully: "#ff9c41", medic: "#11d939",
      mule: "#ffe066", scout: "#c77dff" };
    C.G.p.pets.forEach((pet, i) => {
      // Positions come from updatePets; fall back to the orbit formula.
      let px = pet.x, py = pet.y;
      if (px == null) {
        const a = C.G.t * 2 + i * 2.1;
        px = p.x + Math.cos(a) * 26; py = p.y + Math.sin(a) * 26;
      }
      const bobY = py + Math.sin(C.G.t * 5 + i * 1.7) * 2;
      C.drawSprite("wisp", px, bobY, { scale: 1.5,
        palette: { w: PET_COLORS[pet.role || "gunner"] || "#7df9ff" } });
      if ((pet.role || "gunner") !== "gunner") {
        ctx.fillStyle = "#111"; ctx.font = "bold 8px monospace"; ctx.textAlign = "center";
        ctx.fillText((pet.role || "?")[0].toUpperCase(), px, bobY + 3);
      }
    });
    // Mount: ride box under the player.
    if (p.mount) {
      ctx.fillStyle = "#3a2f10";
      ctx.fillRect(p.x - 13, p.y - 8, 26, 20);
      ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 2;
      ctx.strokeRect(p.x - 13, p.y - 8, 26, 20);
      ctx.fillStyle = "#fff"; ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
      ctx.fillText(p.mount.glyph || "?", p.x, p.y + 7);
    }
    // Player (blinks while invulnerable; soul glow dims with HP; cloaked = ghost).
    const cloakA = p.cloakT > 0 ? 0.45 : 1;
    if (p.surge && p.surge.t > 0) {
      ctx.strokeStyle = "#ff5555"; ctx.lineWidth = 2;
      ctx.strokeRect(p.x - 12, p.y - 21, 24, 30);
    }
    if (p.stance && p.stance.t > 0) {
      ctx.strokeStyle = p.stance.kind === "claws" ? "#ff9c41"
        : p.stance.kind === "wings" ? "#ffffff" : "#8b93a3";
      ctx.lineWidth = 2;
      ctx.strokeRect(p.x - 13, p.y - 22, 26, 32);
    }
    // Player sprite (walk cycle when moving) + soul glow + status outlines.
    const pdir = C.spriteDir(p.facing);
    const pframe = p.moving ? Math.floor(C.G.t * 8) % 2 : 0;
    if (p.inv <= 0 || Math.floor(C.G.t * 12) % 2 === 0) {
      ctx.globalAlpha = cloakA;
      C.drawSprite("player_" + pdir.dir + pframe, p.x, p.y - 2,
        { scale: 2, flip: pdir.flip, flash: p.flashT > 0 });
      ctx.fillStyle = "#7CFC00";
      ctx.globalAlpha = cloakA * (0.3 + 0.7 * (p.hp / p.maxHp));
      ctx.fillRect(p.x - 9, p.y + 12, 18, 3);
      ctx.globalAlpha = 1;
    }
    // Floaters (pickup feedback).
    ctx.textAlign = "center";
    for (const f of C.floaters) {
      ctx.globalAlpha = Math.min(1, f.t);
      ctx.fillStyle = f.color; ctx.font = "bold 12px monospace";
      ctx.fillText(f.txt, f.x, f.y - (1.5 - f.t) * 30);
    }
    ctx.globalAlpha = 1;
    ctx.restore();
    drawMinimap(room);
    drawVignette();
  };

  let vigCache = null;
  function drawVignette() {
    try {
      if (vigCache === null) {
        const c = document.createElement("canvas");
        c.width = C.W; c.height = C.H;
        const g = c.getContext("2d");
        const gr = g.createRadialGradient(C.W / 2, C.H / 2, C.H * 0.35,
          C.W / 2, C.H / 2, C.H * 0.75);
        gr.addColorStop(0, "rgba(0,0,0,0)");
        gr.addColorStop(1, "rgba(0,0,0,.38)");
        g.fillStyle = gr;
        g.fillRect(0, 0, C.W, C.H);
        vigCache = c;
      }
      if (vigCache) C.ctx.drawImage(vigCache, 0, 0);
    } catch (e) { vigCache = false; }
  }

  // 7x7 visited-room grid: brightness by depth, gold = vault, white = you.
  function drawMinimap(room) {
    const ctx = C.ctx, cell = 11, R = 3;
    const size = (R * 2 + 1) * cell;
    const ox = C.W - size - 10, oy = 30;
    ctx.fillStyle = "rgba(5,6,10,.8)";
    ctx.fillRect(ox - 5, oy - 5, size + 10, size + 10);
    ctx.strokeStyle = "#333a47"; ctx.lineWidth = 1;
    ctx.strokeRect(ox - 5, oy - 5, size + 10, size + 10);
    for (let dy = -R; dy <= R; dy++) {
      for (let dx = -R; dx <= R; dx++) {
        const r = C.rooms.get(C.roomKey(C.G.roomX + dx, C.G.roomY + dy));
        if (!r) continue;
        const x = ox + (dx + R) * cell, y = oy + (dy + R) * cell;
        const d = Math.abs(C.G.roomX + dx) + Math.abs(C.G.roomY + dy);
        ctx.globalAlpha = r._seen ? 1 : 0.35;
        ctx.fillStyle = d >= 6 ? "#5a2a2a" : d >= 3 ? "#3a2a4d" : "#2a3342";
        ctx.fillRect(x + 1, y + 1, cell - 2, cell - 2);
        if (r.vault) {
          ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 1;
          ctx.strokeRect(x + 1.5, y + 1.5, cell - 3, cell - 3);
        }
        if (dx === 0 && dy === 0) {
          ctx.strokeStyle = "#fff"; ctx.lineWidth = 2;
          ctx.strokeRect(x + 0.5, y + 0.5, cell - 1, cell - 1);
          ctx.fillStyle = "#fff";
          ctx.fillRect(x + cell / 2 - 1, y + cell / 2 - 1, 2, 2);
        }
      }
    }
    ctx.globalAlpha = 1;
  }
})(window.Casino);
