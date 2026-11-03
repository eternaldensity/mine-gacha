"use strict";
/* Best-run records (localStorage). Death spoils are per-next-run only. */
(function (C) {
  const BEST_KEY = "chaosCasinoBest";
  C.getBest = function () {
    try { return JSON.parse(localStorage.getItem(BEST_KEY) || "{}"); }
    catch (e) { return {}; }
  };
  // Returns true if any record fell.
  C.saveBest = function (depth, time, kills) {
    const b = C.getBest();
    let best = false;
    if (depth > (b.depth || 0)) { b.depth = depth; best = true; }
    if (time > (b.time || 0)) { b.time = Math.round(time); best = true; }
    if (kills > (b.kills || 0)) { b.kills = kills; best = true; }
    try { localStorage.setItem(BEST_KEY, JSON.stringify(b)); } catch (e) {}
    return best;
  };
})(window.Casino);
