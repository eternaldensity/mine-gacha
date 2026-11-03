"use strict";
/* Docs helper: CYOA "start here" buttons seed the gacha ticket wallet
 * (localStorage key shared with gacha.html). A Triple-Advantage ticket is
 * one ticket that rolls three wheels — you keep whichever you pick. */
(function () {
  var GLS = "chaosGacha.v1";
  function T(tier, cat, n) {
    var out = [];
    for (var i = 0; i < n; i++) out.push({ tier: tier, cat: cat });
    return out;
  }
  var STARTS = {
    transmigration: T("gold", "random", 3),
    native1: T("gold", "random", 1),
    native2: T("silver", "random", 2),
    native3: T("bronze", "random", 3),
    changed1: T("platinum", "random", 1).concat(T("gold", "random", 2)),
    changed2: [{ tier: "platinum", cat: "random", adv: 3 }]
  };
  function uid() {
    return Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
  }
  function award(list) {
    var db;
    try {
      db = JSON.parse(localStorage.getItem(GLS) || "null") ||
        { tickets: [], history: [], settings: { spin: "normal", filters: {} } };
    } catch (e) {
      db = { tickets: [], history: [], settings: { spin: "normal", filters: {} } };
    }
    db.tickets = db.tickets || [];
    for (var i = 0; i < list.length; i++) {
      var ticket = { id: uid(), tier: list[i].tier, cat: list[i].cat };
      if ((list[i].adv | 0) > 1) ticket.adv = list[i].adv;
      db.tickets.push(ticket);
    }
    try { localStorage.setItem(GLS, JSON.stringify(db)); } catch (e) {}
    return list.length;
  }
  var btns = document.querySelectorAll(".cyoa-start");
  for (var i = 0; i < btns.length; i++) {
    (function (b) {
      b.addEventListener("click", function () {
        var list = STARTS[b.getAttribute("data-start")] || [];
        if (!list.length) return;
        var n = award(list);
        var old = b.textContent;
        b.textContent = "Added " + n + " ticket" + (n === 1 ? "" : "s") + " ✓ (see ticket wallet)";
        b.disabled = true;
        setTimeout(function () { b.textContent = old; b.disabled = false; }, 2200);
      });
    })(btns[i]);
  }
  window.__docs = { award: award, STARTS: STARTS };
})();
