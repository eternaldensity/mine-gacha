"use strict";
/* DOM refs + card/title UI. Depends on: config (namespace only). */
(function (C) {
  function el(id) { return document.getElementById(id); }
  C.el = el;

  C.ui = {
    card: el("card"),
    cardTitle: el("cardTitle"),
    cardBody: el("cardBody"),
    cardSub: el("cardSub"),
    deathBox: el("death"),
    deathMachine: el("deathMachine"),
    dmTitle: el("dmTitle"),
    dmReels: [...el("dmReels").querySelectorAll(".dmreel")],
    spinBtn: el("spinBtn"),
    summaryBox: el("summaryBox"),
    sumStats: el("sumStats"),
    sumList: el("sumList"),
    sumCard: el("sumCard"),
    sumCardTitle: el("sumCardTitle"),
    sumCardBody: el("sumCardBody"),
    sumCardSub: el("sumCardSub"),
    sumCopyOne: el("sumCopyOne"),
    sumCopyAll: el("sumCopyAll"),
    sumClose: el("sumClose"),
    dmResults: el("dmResults"),
    dmBanked: el("dmBanked"),
    draftBox: el("draft"),
    draftTitle: el("draftTitle"),
    draftList: el("draftList"),
    deathStats: el("deathStats"),
    deathLegacy: el("deathLegacy"),
    titleBox: el("title"),
    startBtn: el("startBtn"),
    freshBtn: el("freshBtn"),
    canvas: el("game"),
  };
  C.ctx = C.ui.canvas.getContext("2d");
  C.ctx.imageSmoothingEnabled = false;

  C.showCard = function (t, b, s, ms) {
    C.ui.cardTitle.textContent = t;
    C.ui.cardBody.textContent = b || "";
    C.ui.cardSub.textContent = s || "";
    C.ui.card.classList.add("show");
    if (C.G) C.G.cardT = (ms || 3500) / 1000;
  };

  C.hideDeath = function () { C.ui.deathBox.classList.remove("show"); };
  C.showTitle = function () { C.ui.titleBox.classList.remove("hide"); };
  C.hideTitle = function () { C.ui.titleBox.classList.add("hide"); };

  C.floater = function (x, y, txt, color) {
    C.floaters.push({ x, y, txt, color: color || "#fff", t: 1.5 });
  };

  // Flavor snippet: first sentence (or clean word-cut) with ellipsis.
  // Mechanics always lead; flavor follows quoted and short.
  C.flavorShort = function (desc, max) {
    const s = String(desc || "").replace(/\s+/g, " ").trim();
    if (!s) return "";
    max = max || 90;
    if (s.length <= max) return s;
    const cut = s.lastIndexOf(". ", max);
    if (cut > 8) return s.slice(0, cut + 1) + " …";
    return s.slice(0, max).replace(/\s+\S*$/, "") + " …";
  };
})(window.Casino);
