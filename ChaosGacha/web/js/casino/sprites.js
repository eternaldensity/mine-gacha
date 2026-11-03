"use strict";
/* Pixel sprites: hand-authored maps + palettes. Characters are 16x16 drawn
 * at 2x; irregular glyphs stay procedural. Rank recoloring works by passing
 * a palette override (uniform U/u) so one guard body serves every rank.
 * Depends on: config (namespace only). */
(function (C) {
  // '.' = transparent. Shared ink; U/u are uniform slots for rank palettes.
  C.PAL = {
    k: "#14101c", s: "#e8c39e", S: "#c99a76", h: "#2a1e16",
    e: "#ffffff", E: "#0a0a12", p: "#23232e", b: "#0d0d12",
    j: "#2ecc71", J: "#1f9d55", g: "#ffe066", r: "#ff4444",
    c: "#7df9ff", o: "#ff9c41", w: "#ffffff", d: "#4a3018",
    B: "#6b4a2a", W: "#e8e4da",
  };

  // 16x16 gambler, facing down, walk frame 0 (legs apart).
  const PLAYER_D0 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....ksssssk.....",
    "....ksesesk.....",
    "....ksssssk.....",
    ".....sssss......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjejjejjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    "....pp...pp.....",
    "...bbb...bbb....",
  ];
  // Facing down, frame 1 (legs together).
  const PLAYER_D1 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....ksssssk.....",
    "....ksesesk.....",
    "....ksssssk.....",
    ".....sssss......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjejjejjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    ".....pp.pp......",
    ".....bbb.bbb....",
  ];
  // Facing up (back of head), frames 0/1 differ only in legs.
  const PLAYER_U0 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....khhhhhk.....",
    "....khhhhhk.....",
    "....khhhhhk.....",
    ".....kkkkk......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjjjjjjjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    "....pp...pp.....",
    "...bbb...bbb....",
  ];
  const PLAYER_U1 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....khhhhhk.....",
    "....khhhhhk.....",
    "....khhhhhk.....",
    ".....kkkkk......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjjjjjjjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    ".....pp.pp......",
    ".....bbb.bbb....",
  ];
  // Facing right (flip for left); torso shared with front view.
  const PLAYER_S0 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....khhksss.....",
    "....khhkses.....",
    "....khhksss.....",
    ".....kksss......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjejjejjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    "....pp...pp.....",
    "...bbb...bbb....",
  ];
  const PLAYER_S1 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....khhksss.....",
    "....khhkses.....",
    "....khhksss.....",
    ".....kksss......",
    "....jjjjjjj.....",
    "...jjjjjjjjj....",
    "...jjejjejjj....",
    "...jjjjjjjjj....",
    "...jjjJJJjjj....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    ".....pp.pp......",
    ".....bbb.bbb....",
  ];
  // Security suit, walk frames (U/u = rank uniform).
  const GUARD_0 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....kEEEEEk.....",
    "....ksssssk.....",
    ".....sssss......",
    "....UUUUUUU.....",
    "...gUUUUUUUg....",
    "...UUeUUUeUU....",
    "...UUUUUUUUU....",
    "...UUuUUUuUU....",
    "...UUUUUUUUU....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    "....pp...pp.....",
    "...bbb...bbb....",
  ];
  const GUARD_1 = [
    "................",
    ".....kkkkk......",
    "....kkkkkkk.....",
    "....kEEEEEk.....",
    "....ksssssk.....",
    ".....sssss......",
    "....UUUUUUU.....",
    "...gUUUUUUUg....",
    "...UUeUUUeUU....",
    "...UUUUUUUUU....",
    "...UUuUUUuUU....",
    "...UUUUUUUUU....",
    "....ppppppp.....",
    "....ppp.ppp.....",
    ".....pp.pp......",
    ".....bbb.bbb....",
  ];
  // Kennel hound, quadruped facing right (flip for left).
  const HOUND_0 = [
    "................",
    "................",
    "................",
    "...........kkk..",
    "..........khsek.",
    "..bb......khsk..",
    "....bbbbbbbbbb..",
    "...bbbbbbbbbbb..",
    "...bbbddbbbbbb..",
    "....bbbbbbbbbb..",
    "...bb..bb..bb...",
    "................",
    "................",
    "................",
    "................",
    "................",
  ];
  const HOUND_1 = [
    "................",
    "................",
    "................",
    "...........kkk..",
    "..........khsek.",
    "..bb......khsk..",
    "....bbbbbbbbbb..",
    "...bbbbbbbbbbb..",
    "...bbbddbbbbbb..",
    "....bbbbbbbbbb..",
    "...bbb..bbb.....",
    "................",
    "................",
    "................",
    "................",
    "................",
  ];
  // Familiar wisp 8x8 (w = role color).
  const WISP = [
    "..wwww..",
    ".wwwwww.",
    "wwweewww",
    "wweeeeww",
    "wweeeeww",
    "wwweewww",
    ".wwwwww.",
    "..wwww..",
  ];

  C.SPRITES = {
    player_d0: { rows: PLAYER_D0 }, player_d1: { rows: PLAYER_D1 },
    player_u0: { rows: PLAYER_U0 }, player_u1: { rows: PLAYER_U1 },
    player_s0: { rows: PLAYER_S0 }, player_s1: { rows: PLAYER_S1 },
    guard_0: { rows: GUARD_0 }, guard_1: { rows: GUARD_1 },
    hound_0: { rows: HOUND_0 }, hound_1: { rows: HOUND_1 },
    wisp: { rows: WISP },
  };

  // Rank uniform palettes for the guard body (U = cloth, u = shade).
  C.RANK_PAL = {
    guard: { U: "#23232e", u: "#14141c" },
    pitboss: { U: "#3a2a5a", u: "#241a38" },
    enforcer: { U: "#5a1a1a", u: "#381010" },
    bruiser: { U: "#4a2a12", u: "#2e1a0c" },
    stalker: { U: "#1a3a3a", u: "#102626" },
    hexer: { U: "#2a1a4a", u: "#1a1030" },
    medic: { U: "#1a3a1a", u: "#102610" },
    captain: { U: "#4a3a0a", u: "#2e2506" },
    handler: { U: "#3a2a1a", u: "#251c10" },
    hound: { U: "#6b4a2a", u: "#4a3018" },
    warlord: { U: "#6b1010", u: "#420a0a" },
    collector: { U: "#3a0a0a", u: "#240606" },
    roller: { U: "#4a3a0a", u: "#2e2506" },
  };

  // Facing angle (0=east, y-down) -> sprite direction + horizontal flip.
  C.spriteDir = function (facing) {
    if (facing == null || isNaN(facing)) return { dir: "d", flip: false };
    const a = ((facing % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    if (a >= Math.PI * 0.25 && a < Math.PI * 0.75) return { dir: "d", flip: false };
    if (a >= Math.PI * 1.25 && a < Math.PI * 1.75) return { dir: "u", flip: false };
    return { dir: "s", flip: Math.cos(a) < 0 };
  };

  // Draw a sprite centered at (cx, cy). flash remaps all ink to white.
  C.drawSprite = function (name, cx, cy, o) {
    const spr = C.SPRITES[name];
    if (!spr) return;
    o = o || {};
    const ctx = C.ctx;
    const px = o.scale || 2;
    const rows = spr.rows, h = rows.length, w = rows[0].length;
    const x0 = Math.round(cx - (w * px) / 2), y0 = Math.round(cy - (h * px) / 2);
    const pal = o.palette;
    for (let y = 0; y < h; y++) {
      const row = rows[y];
      for (let x = 0; x < w; x++) {
        const ch = row[o.flip ? w - 1 - x : x];
        if (ch === "." || ch === " ") continue;
        let col = (pal && pal[ch]) || C.PAL[ch];
        if (!col) continue;
        if (o.flash) col = "#ffffff";
        ctx.fillStyle = col;
        ctx.fillRect(x0 + x * px, y0 + y * px, px, px);
      }
    }
  };
})(window.Casino);
