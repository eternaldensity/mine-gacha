"use strict";
/* Advantage-style draft: when slots are full (or via B), pick which power
 * holds each slot instead of silently stashing. Game sim pauses while open.
 * Depends on: config, dom, state, effects (runtime). */
(function (C) {
  function slotLine(ab, i) {
    return "[" + C.SLOT_KEYS[i] + "] " + ab.name + ": " + ab.op +
      (ab.element ? "/" + ab.element : "") +
      (ab.cdLeft > 0 ? " (" + ab.cdLeft.toFixed(0) + "s cd)" : "");
  }

  function abLine(ab) {
    return ab.name + ": " + ab.op +
      (ab.element ? "/" + ab.element : "") + ": " + ab.blurb +
      " (" + (C.MANA_COSTS[ab.op] || 0) + "⚡)";
  }

  C.openDraft = function (mode) {
    if (C.G.draft) return;
    C.G.draft = mode;
    render();
    C.ui.draftBox.classList.remove("hide");
  };

  C.closeDraft = function () {
    if (!C.G || !C.G.draft) return;
    C.G.draft = null;
    C.ui.draftBox.classList.add("hide");
  };

  // Swap a stashed ability into slot i (attuning: 8s cooldown, Doc rule).
  C.draftSwap = function (slotIdx) {
    const G = C.G, mode = G.draft;
    if (!mode) return;
    const from = mode.kind === "new"
      ? G.p.stash.indexOf(mode.ab)
      : G.p.stash.indexOf(mode.pick);
    const ab = mode.kind === "new" ? mode.ab : mode.pick;
    if (!ab || from < 0) { C.closeDraft(); return; }
    G.p.stash.splice(from, 1);
    const old = G.p.slots[slotIdx];
    G.p.slots[slotIdx] = ab;
    if (old) G.p.stash.push(old);
    ab.cdLeft = Math.max(ab.cdLeft || 0, 8);
    C.showCard("Slotted [" + C.SLOT_KEYS[slotIdx] + "]: " + ab.name,
      ab.blurb + " (attuning 8s).", old ? "Swapped out: " + old.name + " (stashed)." : "", 3000);
    C.closeDraft();
    C.updateHud();
  };

  // Tinker build menu: spend parts on a rig placed in front of you.
  C.buildOptions = function (ab) {
    const p = C.G.p;
    const maxTier = ab.power; // tier id, e.g. "gold"
    const maxIdx = C.tierIdx(maxTier);
    const opts = [];
    for (let i = 0; i <= Math.min(maxIdx, 5); i++) {
      const t = C.TIERS[i];
      opts.push({ kind: "slot", tier: t.id, label: t.label + " Slot Rig",
        cost: (i + 1) * 2, ok: p.parts >= (i + 1) * 2 });
      opts.push({ kind: "gacha", tier: t.id, label: t.label + " Gacha Rig",
        cost: (i + 1) * 2, ok: p.parts >= (i + 1) * 2 });
    }
    opts.push({ kind: "turret", label: "Sentry Turret (60s)", cost: 5, ok: p.parts >= 5 });
    opts.push({ kind: "barricade", label: "Barricade (45s)", cost: 4, ok: p.parts >= 4 });
    return opts;
  };

  C.buildPick = function (idx) {
    const G = C.G, mode = G.draft;
    if (!mode || mode.kind !== "build") return;
    const opt = C.buildOptions(mode.ab)[idx];
    if (!opt || !opt.ok) return;
    const p = G.p;
    p.parts -= opt.cost;
    const room = C.curRoom();
    const px = Math.max(70, Math.min(C.W - 70, p.x + Math.cos(p.facing) * 64));
    const py = Math.max(70, Math.min(C.H - 70, p.y + Math.sin(p.facing) * 64));
    if (opt.kind === "slot" || opt.kind === "gacha") {
      const t = C.tierById(opt.tier);
      room.machines.push({
        id: 900 + room.machines.length, kind: opt.kind, tier: t.id, color: t.color,
        pull: null, hp: 3 + C.tierIdx(t.id), maxHp: 3 + C.tierIdx(t.id), playerMade: true,
        idleSyms: ["◈", "◈", "◈"], lastPrize: null,
        cat: opt.kind === "gacha" ? "random" : null,
        x: px, y: py,
      });
    } else if (opt.kind === "turret") {
      room.placed.push({ kind: "turret", x: px, y: py, t: 60, cd: 0,
        dmg: Math.max(2, Math.round(mode.ab.rarity)) });
    } else if (opt.kind === "barricade") {
      const horiz = Math.abs(Math.cos(p.facing)) <= Math.abs(Math.sin(p.facing));
      const w = horiz ? 110 : 16, h = horiz ? 16 : 110;
      room.tempWalls.push({ x: px - w / 2, y: py - h / 2, w, h, t: 45, barricade: true });
    }
    mode.ab.cdLeft = mode.ab.cd;
    C.floater(px, py - 44, "🔧 " + opt.label, "#ffe066");
    C.closeDraft();
    C.updateHud();
  };

  // Manage mode: choose a stashed ability first, then a slot.
  C.draftPickStash = function (idx) {
    const G = C.G;
    if (!G.draft || G.draft.kind !== "manage") return;
    G.draft.pick = G.p.stash[idx];
    render();
  };

  function render() {
    const G = C.G, mode = G.draft;
    const box = C.ui.draftList;
    box.innerHTML = "";
    const el = (tag, txt, cls) => {
      const d = document.createElement(tag);
      if (txt) d.textContent = txt;
      if (cls) d.className = cls;
      return d;
    };
    if (mode.kind === "build") {
      box.appendChild(el("p", "🔧 " + mode.ab.name + ": parts: " + C.G.p.parts +
        "🧩. Builds up to " + mode.ab.power + ". Placed in front of you."));
      C.buildOptions(mode.ab).forEach((o, i) => {
        const b = el("button", (o.ok ? "Build " : "Need " + o.cost + "🧩: ") +
          o.label + " (" + o.cost + "🧩)", "draftBtn" + (o.ok ? "" : " dim"));
        if (o.ok) b.addEventListener("click", () => C.buildPick(i));
        box.appendChild(b);
      });
      const done = el("button", "Done (Esc)", "draftBtn dim");
      done.addEventListener("click", () => C.closeDraft());
      box.appendChild(done);
    } else if (mode.kind === "new") {
      box.appendChild(el("p", "Slots full! New pull: " + abLine(mode.ab)));
      box.appendChild(el("p", "Take it into a slot (old power stashes), or keep your loadout:", "small"));
      G.p.slots.forEach((s, i) => {
        const b = el("button", "[" + C.SLOT_KEYS[i] + "] " + abLine(mode.ab) +
          "  ⇄  " + abLine(s), "draftBtn");
        b.addEventListener("click", () => C.draftSwap(i));
        box.appendChild(b);
      });
      const keep = el("button", "Keep loadout (stash " + mode.ab.name + ")", "draftBtn dim");
      keep.addEventListener("click", () => C.closeDraft());
      box.appendChild(keep);
    } else {
      if (!G.p.stash.length) {
        box.appendChild(el("p", "Stash is empty. New powers land here when slots are full."));
      } else {
        box.appendChild(el("p", "1) pick a stashed power" +
          (mode.pick ? ": " + mode.pick.name + ": 2) pick a slot:" : ""), "small"));
        G.p.stash.forEach((s, i) => {
          const b = el("button", (mode.pick === s ? "▶ " : "") + abLine(s),
            "draftBtn" + (mode.pick === s ? " sel" : ""));
          b.addEventListener("click", () => C.draftPickStash(i));
          box.appendChild(b);
        });
        if (mode.pick) {
          G.p.slots.forEach((s, i) => {
            const b = el("button", "[" + C.SLOT_KEYS[i] + "] " + abLine(mode.pick) +
              "  ⇄  " + abLine(s), "draftBtn");
            b.addEventListener("click", () => C.draftSwap(i));
            box.appendChild(b);
          });
        }
      }
      const done = el("button", "Done (Esc)", "draftBtn dim");
      done.addEventListener("click", () => C.closeDraft());
      box.appendChild(done);
    }
    C.ui.draftTitle.textContent = mode.kind === "build" ? "🔧 Tinker bench"
      : mode.kind === "new" ? "🎰 Slots full: draft!" : "🎒 Stash manager";
  }
})(window.Casino);
