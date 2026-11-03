"use strict";
/* Active ability ops: compile keyword-matched ability prizes into runnable,
 * cooldown-gated powers bound to slot keys (J/K/L). Unmatched abilities fall
 * back to the legacy essence path in prizes.js — never a dead pull.
 * Depends on: config, state (runtime). Execution lives in combat.js. */
(function (C) {
  C.SLOT_KEYS = ["J", "K", "L"];

  // Doc rule, run-scaled: 1 slot, +1 per 5 abilities owned, cap 3.
  C.maxSlots = function () {
    return Math.min(3, 1 + Math.floor((C.G.p.abilitiesOwned || 0) / 5));
  };

  C.slotCd = function (base, rarity) {
    return base / (1 + 0.06 * rarity);
  };

  // Casino elements differ in name from gacha tags in four places:
  // ice->frost, electric->bolt, poison->venom, holy->light, air->wind.
  C.TAG_TO_ELEMENT = { fire: "fire", water: "water", ice: "frost",
    electric: "bolt", earth: "earth", air: "wind", dark: "shadow",
    nature: "nature", poison: "venom", holy: "light" };

  C.elementOf = function (nm, tags) {
    const tg = (tags || []).map(t => String(t).toLowerCase());
    // Explicit theme tags beat name-guessing (same priority as below).
    for (const t of ["fire", "dark", "holy", "electric", "ice",
                     "poison", "water", "earth", "air", "nature"]) {
      if (tg.includes(t) && C.TAG_TO_ELEMENT[t]) return C.TAG_TO_ELEMENT[t];
    }
    const s = String(nm).toLowerCase();
    // Thematic elements (shadow/light) win over delivery words ("bolt").
    if (/fire|flame|blast|explos|plasma|inferno|cinder|magma|lava|scorch|pyre|\bash\b|smolder|\bmeteor\b|comet/i.test(s)) return "fire";
    if (/shadow|darkness|umbral|void|abyss|\bnight\b|eclipse|gloom|obscur/i.test(s)) return "shadow";
    if (/\blight\b|holy|radiant|\bdawn\b|sacred|prism|seraph|lum/i.test(s)) return "light";
    if (/lightning|bolt|storm|thunder|electric/i.test(s)) return "bolt";
    if (/frost|ice|freeze|cold|blizzard/i.test(s)) return "frost";
    if (/poison|acid|venom|toxic/i.test(s)) return "venom";
    if (/water|aqua|\btide\b|tidal|rain|mist|steam|bubble|flood/i.test(s)) return "water";
    if (/earth|stone|\brock\b|sand|mud|mountain|clay|crystal|gem/i.test(s)) return "earth";
    if (/\bwind\b|gale|tornado|zephyr|tempest/i.test(s)) return "wind";
    if (/nature|plant|wood|vine|forest|bloom|thorn|\broot\b|leaf|swamp|jungle/i.test(s)) return "nature";
    if (/shadow|darkness|umbral|void|abyss|\bnight\b|eclipse|gloom|obscur/i.test(s)) return "shadow";
    if (/\blight\b|holy|radiant|\bdawn\b|sacred|prism|seraph|lum/i.test(s)) return "light";
    return "arcane";
  };

  // Familiar role from its name (phase 3); the healing tag catches
  // themed medics whose names carry no heal-word (tags beat names).
  // Wealth-themed money pets (gold slimes, treasure fairies) haul loot as
  // mules; description-aware so "Spelunker Fairy" still counts. Bare
  // "gold"/"coin" excluded (golden retrievers, sport coins stay ordinary).
  C.petRole = function (name, tags, desc) {
    if ((tags || []).map(t => String(t).toLowerCase()).includes("healing")) return "medic";
    const nm = String(name).toLowerCase();
    if (/guard|bully|brawler|tank|defend|protector|bodyguard/i.test(nm)) return "bully";
    if (/heal|medic|cleric|nurse|doctor|mend/i.test(nm)) return "medic";
    if (/mule|pack|merchant|greed|luck|hoard|storage|gathering swarm|lizard doggo|simulacrum|\bcrow\b|\bwisp\b|\bpeon\b|\bharvest\b/i.test(nm)) return "mule";
    if (desc && /wealth|treasures?|newbucks|plorts?.*gold|solid-gold egg|gold bars?|free market|stock speculation|money|payday|gather(?! information)|fetch|lifted wallets|stripped corpses|digs up surprises/i.test(String(desc).toLowerCase())) return "mule";
    if (/scout|eye|watcher|guide|spy|sensor/i.test(nm)) return "scout";
    if (/spelunker fairy|gold slime/i.test(nm)) return "mule";
    return "gunner";
  };

  C.ARMORY_WORDS = ["sword", "blade", "knife", "axe", "hammer", "mace",
    "dagger", "spear", "baton", "club", "scythe", "cleaver"];

  // The Pocket Armory draws a fresh melee weapon: roll the item gacha through
  // weapon-ish queries at roughly the bag's rarity. Standby blade on failure.
  C.rollArmoryWeapon = function (r) {
    const pool = C.entries();
    const words = C.ARMORY_WORDS.slice();
    for (let i = words.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = words[i]; words[i] = words[j]; words[j] = tmp;
    }
    if (pool.length && window.ChaosGacha) {
      for (const w of words) {
        try {
          return window.ChaosGacha.roll(pool, null, "item",
            Math.max(0.1, r - 1), r, r + 1,
            { hideNsfw: true, hideNoncon: true, q: w }, Math.random);
        } catch (e) { /* word matched nothing: try the next */ }
      }
    }
    return { category: "item", name: "Armory Standby Blade", rarity: r,
      source: "Casino", description: "A plain but honest blade.", odds: 0, meta: [] };
  };

  // Weapon pattern from its name (phase 3).
  C.weaponPattern = function (name) {
    const nm = String(name).toLowerCase();
    if (/shotgun|spread|blunderbuss|scatter/i.test(nm)) return "spread";
    if (/rapid|chaingun|repeater|smg|auto/i.test(nm)) return "rapid";
    if (/heavy|hammer|maul|great|massive|wreck/i.test(nm)) return "heavy";
    return "single";
  };

  C.activeRole = function (role) {
    return C.G.p.pets.some(q => (q.role || "gunner") === role);
  };

  C.ticketDropChance = function () {
    return C.activeRole("scout") ? 0.45 : 0.3;
  };

  // Piercing weapons ignore shields (armor-piercing rounds, phase edges...).
  C.weaponPierce = function (name, desc) {
    return /pierc|lance|phase|railgun|armor piercing/i.test(String(name) + " " + String(desc || ""));
  };

  // Weapon element from its name (phase 2: melee/ranged apply statuses);
  // tags first so themed prizes (holy swords, hellflame hammers) type
  // correctly even with plain names.
  C.weaponElement = function (name, tags) {
    const e = C.elementOf(String(name).toLowerCase(), tags);
    return e === "arcane" ? null : e;
  };

  // Full branch order: mobility > nova > wall > summon > beam > lobbed >
  // wave > bolt > dash-lite > surge > chrono > heal. Earlier wins on overlap
  // ("Nova Blast" novas, "Frost Beam" stays a bolt, "Lightning Dash" zaps).
  // Returns {name, rarity, op, ...} or null (→ essence fallback, never dead).
  C.compileAbility = function (res) {
    const nm = (res.name + " " + (res.description || "")).toLowerCase(), r = res.rarity;
    const tags = (res.tags || []).map(t => String(t).toLowerCase());
    const has = t => tags.includes(t);
    const el = C.elementOf(nm, tags);
    if (/teleport|blink|\bphase\b|portal|\brift\b/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "dash", power: 340,
        cd: C.slotCd(6, r), cdLeft: 0, blurb: "blink-dash, i-frames",
      };
    }
    if (/nova|shockwave|detonat|implosion|eruption|burst of|cataclysm/i.test(nm)) {
      const power = 2 + Math.floor(r / 2);
      return {
        name: res.name, rarity: r, op: "nova", element: el, power,
        cd: C.slotCd(9, r), cdLeft: 0,
        blurb: "nova: " + power + " dmg around you",
      };
    }
    if (/\bwall\b|barrier|rampart|bulwark|fortress|force.?field|\bcover\b|bastion/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "wall", power: 8 + r * 0.5,
        cd: C.slotCd(12, r), cdLeft: 0,
        blurb: "conjure a " + Math.round(8 + r * 0.5) + "s guard-blocking wall",
      };
    }
    if (/summon|skeleton|zombie|golem|homunculus|\bclone\b|swarm|stampede|raise (the )?dead|animate|conjure.*(creature|beast|being|soldier|warrior|servant|ally|minion)|turret|deploy|sentry|automaton|\btrap\b|\bmine\b|construct/i.test(nm)) {
      const stationary = /turret|deploy|sentry|\btrap\b|\bmine\b|construct/i.test(nm);
      return {
        name: res.name, rarity: r, op: "summon",
        role: C.petRole(res.name, res.tags), element: el === "arcane" ? null : el,
        power: Math.max(1, Math.round(r / 2)), dur: 20 + r * 2, stationary,
        cd: C.slotCd(15, r), cdLeft: 0,
        blurb: "summon " + (stationary ? "turret" : "ally") + " for " + Math.round(20 + r * 2) + "s",
      };
    }
    if (/salvage|scrap|dismantle|recycle|strip for parts|chop shop/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "salvage",
        cd: C.slotCd(6, r), cdLeft: 0,
        blurb: "scrap nearest machine into bonus parts",
      };
    }
    if (/tinker|engineer|\bbuild\b|craft|gadget|contraption|workshop|blueprint|repair|invention|\bdevice\b|machinist/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "tinker", power: C.rigTierFor(r),
        cd: C.slotCd(3, r), cdLeft: 0,
        blurb: "build rigs up to " + C.rigTierFor(r) + " from parts",
      };
    }
    if (/survey|reveal|expose|clairvoy|farsight|scry|precog|foresight|danger sense|sixth sense|\bdetect\b|oversight|all-seeing/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "survey",
        cd: C.slotCd(25, r), cdLeft: 0,
        blurb: "reveal nearby rooms (" + Math.round(20 + r * 2) + "s intel)",
      };
    }
    if (/laser|disintegrat|annihilat|death.?ray|solar.?ray|lunar.?ray|heat.?vision|\bray\b|lightlance/i.test(nm)) {
      const power = 2 + Math.floor(r / 2);
      return {
        name: res.name, rarity: r, op: "beam", element: el, power,
        cd: C.slotCd(4, r), cdLeft: 0,
        blurb: "piercing beam (" + power + " dmg in a line)",
      };
    }
    if (/mortar|grenade|bombard|catapult|trebuchet|artillery|airstrike|meteor|comet|boulder|landslide|avalanche|siege|orbital/i.test(nm)) {
      const power = 2 + Math.floor(r / 2);
      return {
        name: res.name, rarity: r, op: "lobbed", element: el, power,
        cd: C.slotCd(8, r), cdLeft: 0,
        blurb: "delayed blast (" + power + " dmg, lands late)",
      };
    }
    if (/dominate|possess|mind control|betray|\bcharm\b|confuse|beguile|enthrall/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "betray",
        cd: C.slotCd(18, r), cdLeft: 0,
        blurb: "turn a guard for " + Math.round(8 + r * 0.5) + "s",
      };
    }
    if (/wave|tide|tsunami|kinesis|telekinesis|gravity|graviton|gust|vortex|maelstrom|\bwind\b|gale|tornado|repuls/i.test(nm)) {
      const power = 1 + Math.floor(r / 2);
      return {
        name: res.name, rarity: r, op: "wave", element: el, power,
        cd: C.slotCd(5, r), cdLeft: 0,
        blurb: "force wave (" + power + " dmg + shove)",
      };
    }
    const stanceKind = (() => {
      if (/claw|fang|talon|\brend\b|beast|feral|\bwere\b|werewolf|lycan|dragon|transform|shapeshift|alternate form/i.test(nm)) return "claws";
      if (/\bwing|angel|harpy|glide|to fly|can fly|fly at will|take flight|takes flight/i.test(nm)) return "wings";
      if (/carapace|shell|exoskeleton|\bskin\b|barkskin|diamond skin|armor skin|scales|scaled hide/i.test(nm)) return "carapace";
      return null;
    })();
    if (stanceKind) {
      return {
        name: res.name, rarity: r, op: "stance", kind: stanceKind,
        cd: C.slotCd(16, r), cdLeft: 0,
        blurb: stanceKind + " stance (" +
          (stanceKind === "claws" ? "fast +dmg melee, kills heal" :
           stanceKind === "wings" ? "fly over walls, +speed" : "+block, thorns, slow") + ")",
      };
    }
    if (/taunt|provoke|\bchallenge\b|mock|jeer|trash talk|come at me/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "taunt",
        cd: C.slotCd(12, r), cdLeft: 0, blurb: "taunt: every guard comes to you",
      };
    }
    if (/pacif|soothe|serene|befriend|lullaby|calm emotions|tranquil/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "pacify",
        cd: C.slotCd(15, r), cdLeft: 0, blurb: "pacify a guard for good",
      };
    }
    if (/fire|flame|lightning|bolt|projectile|emit|blast|breath|plasma|frost|ice|freeze|shadow.?bolt|holy.?light|acid|poison.?spit|energy.?blast|bullet|spike|shard|lance|arrow|dart|missile|cannon|volley|javelin|spear/i.test(nm)) {
      const power = Math.max(1, Math.round(r / 2));
      const element = el;
      return {
        name: res.name, rarity: r, op: "bolt", element, power,
        // Venom fires a 3-way spread: longer cooldown to pay for it.
        cd: C.slotCd(element === "venom" ? 0.8 : 0.55, r), cdLeft: 0,
        blurb: element + (element === "venom" ? " spread" : " bolt") +
          " (" + power + " dmg" + (C.G.p.weapon ? ", +1 armed" : "") + ")",
      };
    }
    if (/invisib|stealth|unseen|vanish|shadowmeld|chameleon|thermoptic|camouflage|shadow cloak|shade cloak|invisibility cloak|cloak of|fade from sight|undetect/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "veil",
        cd: C.slotCd(22, r), cdLeft: 0,
        blurb: "veil " + Math.round(3 + r * 0.2) + "s: unseen + quiet pulls",
      };
    }
    if (/\bdash\b|flicker|afterimage/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "dash", power: 340,
        cd: C.slotCd(6, r), cdLeft: 0, blurb: "blink-dash, i-frames",
      };
    }
    if (/strength|muscle|physique|durability|stamina|athletic|enrage|\brage\b|frenzy|berserk|bloodlust|overdrive/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "surge",
        dur: 10, dmgMult: 1 + 0.1 * r, spdMult: 1 + 0.05 * r,
        cd: C.slotCd(20, r), cdLeft: 0,
        blurb: "surge 10s: +" + Math.round(10 * r) + "% dmg, +" + Math.round(5 * r) + "% speed",
      };
    }
    if (/\btime\b|temporal|rewind|\bloop\b|accelerat|time.?stop|time.?skip/i.test(nm)) {
      return {
        name: res.name, rarity: r, op: "chrono", power: 5,
        cd: C.slotCd(14, r), cdLeft: 0,
        blurb: "time bubble: slows all nearby guards 5s",
      };
    }
    if (/heal|regen|restor|purif|cure|second.?wind|mend|rejuvenat/i.test(nm)) {
      const power = 1 + Math.floor(r / 3);
      return {
        name: res.name, rarity: r, op: "heal", power,
        cd: C.slotCd(25, r), cdLeft: 0, blurb: "restore " + power + " HP",
      };
    }
    // Tag fallbacks: name regex above wins; tags catch themed entries with
    // non-obvious names (Velkhana Form has no "dragon" in its name, Seize
    // has no "mind control", Grave Buster has no "skeleton").
    if (has("teleport")) {
      return {
        name: res.name, rarity: r, op: "dash", power: 340,
        cd: C.slotCd(6, r), cdLeft: 0, blurb: "blink-dash, i-frames",
      };
    }
    if (has("undead") || has("construct")) {
      const stationary = has("construct");
      return {
        name: res.name, rarity: r, op: "summon",
        role: C.petRole(res.name, res.tags), element: el === "arcane" ? null : el,
        power: Math.max(1, Math.round(r / 2)), dur: 20 + r * 2, stationary,
        cd: C.slotCd(15, r), cdLeft: 0,
        blurb: "summon " + (stationary ? "turret" : "ally") + " for " + Math.round(20 + r * 2) + "s",
      };
    }
    if (has("psychic")) {
      return {
        name: res.name, rarity: r, op: "betray",
        cd: C.slotCd(18, r), cdLeft: 0,
        blurb: "turn a guard for " + Math.round(8 + r * 0.5) + "s",
      };
    }
    if (has("healing")) {
      const power = 1 + Math.floor(r / 3);
      return {
        name: res.name, rarity: r, op: "heal", power,
        cd: C.slotCd(25, r), cdLeft: 0, blurb: "restore " + power + " HP",
      };
    }
    return null;
  };

  // Equip into the first free slot; overflow goes to the stash.
  // Returns the bound key ("J"/"K"/"L") or null when stashed.
  C.equipAbility = function (ab) {
    const p = C.G.p;
    if (p.slots.length < C.maxSlots()) {
      p.slots.push(ab);
      return C.SLOT_KEYS[p.slots.length - 1];
    }
    p.stash.push(ab);
    return null;
  };

  // Newly opened slots auto-fill from the stash. Returns count moved.
  C.fillSlots = function () {
    const p = C.G.p;
    let moved = 0;
    while (p.slots.length < C.maxSlots() && p.stash.length) {
      p.slots.push(p.stash.shift());
      moved++;
    }
    return moved;
  };
})(window.Casino);
