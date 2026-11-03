"use strict";
/* Boot: input wiring + title screen + first run. Depends on: all modules. */
(function (C) {
  C.audio.ensure();
  addEventListener("keydown", e => {
    C.audio.ensure(); C.audio.resume();
    if (e.key.toLowerCase() === "m" && C.G && !C.G.title) {
      const muted = C.audio.toggle();
      C.showCard(muted ? "🔇 Muted (M)" : "🔊 Sound on (M)", "", "", 1200);
      return;
    }
    if ((e.key === "b" || e.key === "B") && C.G && C.G.over) { C.toggleSummary(); return; }
    if (e.key === "Escape" && C.G && C.G.draft) { C.closeDraft(); return; }
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) e.preventDefault();
    C.keys[e.key.toLowerCase()] = true;
    const k = e.key.toLowerCase();
    if (k === "enter" && C.G && C.G.title) C.startGame();
    else if ((k === "enter" || k === " ") && C.G && C.G.over) {
      if (!C.spinDeath()) { C.resolveDeathRest(); C.newRun(false); }
    }
    else if (k === "r" && C.G && C.G.over) { C.resolveDeathRest(); C.newRun(false); }
    else if (k === "t" && C.G && C.G.over) { C.banked = null; C.pendingCurses = []; C.newRun(false, false); }
  });
  addEventListener("keyup", e => { C.keys[e.key.toLowerCase()] = false; });
  C.ui.canvas.addEventListener("mousedown", e => {
    if (e.button === 2) C.queueWeapon();
    else C.queueAttack();
  });
  C.ui.canvas.addEventListener("contextmenu", e => e.preventDefault());
  C.audio.ensure();
  C.el("againBtn").addEventListener("click", () => { C.audio.ensure(); C.audio.click(); C.resolveDeathRest(); C.newRun(false); });
  C.el("curseBtn").addEventListener("click", () => C.rollCurse());
  C.el("curseNextBtn").addEventListener("click", () => C.rollCurseNext());
  C.ui.freshBtn.addEventListener("click", () => { C.audio.ensure(); C.audio.click(); C.banked = null; C.pendingCurses = []; C.newRun(false, false); });
  C.ui.spinBtn.addEventListener("click", () => { C.audio.ensure(); C.spinDeath(); });
  C.el("summaryBtn").addEventListener("click", () => C.toggleSummary());
  C.ui.sumCopyAll.addEventListener("click", () => C.copyText(C.allEntriesText(), C.ui.sumCopyAll));
  C.ui.sumClose.addEventListener("click", () => C.toggleSummary(false));
  C.ui.startBtn.addEventListener("click", () => { C.audio.ensure(); C.audio.click(); C.startGame(); });

  C.newRun(true);
  requestAnimationFrame(C.frame);
})(window.Casino);
