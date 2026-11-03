"use strict";
/* Tiny WebAudio bleeps: no assets, all oscillator. Everything is guarded so
 * the game runs silent when audio is unavailable or muted (M).
 * Depends on: config (namespace only). */
(function (C) {
  const KEY = "chaosCasinoMute";
  const audio = {
    ctx: null,
    muted: false,
    ensure() {
      if (this.ctx || this.muted) return;
      try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        this.ctx = new AC();
      } catch (e) { this.ctx = null; }
    },
    resume() {
      if (this.ctx && this.ctx.state === "suspended") {
        try { this.ctx.resume(); } catch (e) {}
      }
    },
    // freq slide f->f2 over dur seconds, starting `when` later.
    tone(f, f2, dur, type, vol, when) {
      if (this.muted || !this.ctx) return;
      try {
        const t0 = this.ctx.currentTime + (when || 0);
        const o = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        o.type = type || "square";
        o.frequency.setValueAtTime(f, t0);
        if (f2 && f2 !== f) o.frequency.exponentialRampToValueAtTime(Math.max(1, f2), t0 + dur);
        g.gain.setValueAtTime(vol || 0.06, t0);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
        o.connect(g).connect(this.ctx.destination);
        o.start(t0);
        o.stop(t0 + dur + 0.02);
      } catch (e) {}
    },
    toggle() {
      this.muted = !this.muted;
      try { localStorage.setItem(KEY, this.muted ? "1" : "0"); } catch (e) {}
      return this.muted;
    },
  };
  try { audio.muted = localStorage.getItem(KEY) === "1"; } catch (e) {}

  audio.click = () => audio.tone(660, 660, 0.06, "square", 0.05);
  audio.pullStart = () => audio.tone(220, 660, 0.18, "sawtooth", 0.05);
  audio.dry = () => audio.tone(140, 90, 0.07, "square", 0.05);
  audio.lock = () => audio.tone(880, 880, 0.05, "square", 0.05);
  audio.jackpot = () => {
    [523, 659, 784, 1047].forEach((f, i) => audio.tone(f, f, 0.12, "square", 0.06, i * 0.09));
  };
  audio.coins = () => audio.tone(990, 1320, 0.08, "square", 0.05);
  audio.ticket = () => { audio.tone(740, 740, 0.07, "square", 0.05); audio.tone(1108, 1108, 0.09, "square", 0.05, 0.07); };
  audio.build = () => { audio.tone(392, 392, 0.1, "triangle", 0.07); audio.tone(523, 523, 0.1, "triangle", 0.07, 0.09); audio.tone(659, 659, 0.14, "triangle", 0.07, 0.18); };
  audio.hurt = () => audio.tone(160, 70, 0.18, "sawtooth", 0.08);
  audio.kill = () => audio.tone(440, 110, 0.12, "square", 0.06);
  audio.wave = () => { audio.tone(233, 233, 0.15, "sawtooth", 0.06); audio.tone(233, 233, 0.15, "sawtooth", 0.06, 0.18); };
  audio.curse = () => { audio.tone(311, 311, 0.12, "triangle", 0.07); audio.tone(208, 208, 0.2, "triangle", 0.07, 0.12); };
  audio.death = () => { [392, 330, 262, 196].forEach((f, i) => audio.tone(f, f * 0.97, 0.22, "sawtooth", 0.06, i * 0.16)); };

  C.audio = audio;
})(window.Casino);
