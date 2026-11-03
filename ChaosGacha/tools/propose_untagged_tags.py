#!/usr/bin/env python3
"""Propose tags for untagged entries (fork-only content the official list lacks).

The official import covers the original site's entries; anything added in this
fork afterwards has no tags. This script scans those and proposes tags using the
same taxonomy: category-aware rules, mostly name-based (names are short and
explicit: "Wado Ichimonji" is a katana, "Typhoon" is air), plus a small set of
identity-style description rules ("A ... hound", "you are a ...").

Every proposal is validated against the category's official tag dictionary, so
e.g. skills can only get the 18 skill tags even if an element word appears.

    python3 tools/propose_untagged_tags.py             # summary + samples
    python3 tools/propose_untagged_tags.py --all       # every proposal
    python3 tools/propose_untagged_tags.py --json out.json
    python3 tools/propose_untagged_tags.py --apply     # write into gachafiles
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_tree as gt          # noqa: E402
import import_official_tags as oi   # noqa: E402

ALL = ["ability", "item", "skill", "trait", "familiar"]
ELEM = ["ability", "item", "trait", "familiar"]      # skills have no element tags
FUNC = ["ability", "trait", "item"]
# curated fork tags kept alongside the official vocabulary
CURATED = {"beastkin", "blood", "construct", "eldritch", "fae", "healing",
           "teleport", "vampiric", "anti-draconic", "mechanical", "passive",
           "instance-familiar"}


# Compound-friendly name/description matching: a word may be preceded by a
# thematic prefix ("Hell"hound, "Snow"tiger) or carry suffixes ("Commander").
PREFIX = (r"(?:arch|alpha|beta|omega|prime|elder|ancient|greater|lesser|grand|"
          r"hell|hells|celestial|heavenly|infernal|demonic|eclipse|dawn|dusk|twilight|midnight|"
          r"gold|silver|copper|bronze|mythril|crystal|glass|rock|wave|tide|ember|blaze|magma|lava|"
          r"aqua|hydro|pyro|cryo|electro|geo|aero|necro|soul|spirit|ghost|skull|metal|robot|"
          r"mech|cyber|plasma|gloom|venom|poison|thunder|lightning|winter|summer|autumn|spring|"
          r"high|low|mini|lil|little|baby|young|old|blind|mad|crazy|king|queen|"
          r"lord|lady|master|big|small|dark|light|holy|dire|war|snow|shadow|"
          r"blood|moon|sun|sea|sky|storm|thunder|fire|ice|frost|stone|iron|"
          r"death|doom|night|demon|angel|dragon|steel|bone|flesh|vine|wood|"
          r"sand|dust|ash|flame|gloom|mist|star|void|chaos|order|grim|sludge|"
          r"toxic|acid|plague|mutant|cyber|nano|mega|ultra|super|swift|quick)"
          r"[- ']?")


def N(*stems):
    """Word matcher.

    Long stems (>=5 chars) allow a thematic prefix ("Hell"hound, "Thunder"bird)
    and any suffix. Short stems are matched as whole words only, so "imp",
    "ant", "ice" and friends cannot hide inside "important", "want" or "nice".
    """
    long_, short_ = [], []
    for s in stems:
        (short_ if len(s) <= 4 else long_).append(s)
    parts = []
    if long_:
        parts.append(r"\b(?:" + PREFIX + r")?(?:" + "|".join(long_) + r")\w*")
    if short_:
        parts.append(r"\b(?:" + "|".join(re.escape(s) for s in short_) + r")(?:s|es)?\b")
    return "(?:" + "|".join(parts) + ")"


# "…deals extra damage to holy beings", "vulnerable to fire" describe targets or
# weaknesses, not identity; strip those clauses before description matching.
NEG_STRIP = re.compile(
    r"\b(?:damage[sd]?|effective|strong against|lethal to|punish\w*|weak(?:ness)?|"
    r"vulnerab\w*|bonus against|extra damage|slay\w*|bane|counter\w*|"
    r"resistant to|protected against)\b[^.;]{0,70}", re.I)
# Clauses that talk about weakness/resistance/damage describe targets, not what
# an entry IS ("severe light and holy weakness", "immune to poison"); drop them.
NEG_CLAUSE = re.compile(r"\b(weak|resist|immune|vulnerab|damage|effective|slay|bane|lethal)", re.I)


def R(tag, cats, name=None, desc=None):
    return (tag, cats, name, desc)


RULES = [
    # ---------------- items: what the thing is ----------------
    R("blade", ["item"], N("sword","blade","katana","saber","sabre","rapier","cutlass","machete","dagger","knife","shiv","glaive","scimitar","claymore","falchion","kukri","wakizashi","tanto","sickle","khopesh","nodachi","kunai","dirk","stiletto"),
      N("sword","blade","katana","saber","rapier","cutlass","machete","dagger","knife","shiv","scimitar","claymore","kukri","wakizashi","tanto","kunai")),
    R("polearm", ["item"], N("spear","lance","halberd","naginata","pike","trident","bardiche","partisan","glaive","scythe","quarterstaff"),
      N("spear","lance","halberd","naginata","pike","trident","bardiche","partisan","glaive")),
    R("bludgeon", ["item"], N("hammer","maul","mace","cudgel","warhammer","morningstar","flail","sledge","club","baton","pipe"),
      N("hammer","maul","mace","cudgel","warhammer","morningstar","flail")),
    R("gun", ["item"], N("gun","rifle","pistol","revolver","shotgun","smg","carbine","musket","blaster","cannon","handgun","magnum","minigun","launcher","bazooka","sniper","artillery","railgun","derringer","flintlock"),
      N("gun","rifle","pistol","revolver","shotgun","carbine","musket","blaster","cannon","handgun","magnum","minigun","launcher","sniper","artillery","railgun")),
    R("bow", ["item"], N("bow","longbow","crossbow","recurve","arbalest","sling"),
      N("longbow","crossbow","recurve","arbalest","longbow")),
    R("shield", ["item"], N("shield","buckler","aegis","targe","pavise"),
      N("shield","buckler","aegis","targe")),
    R("weapon", ["item"], N("sword","blade","katana","spear","lance","axe","hammer","mace","dagger","knife","gun","rifle","pistol","bow","crossbow","scythe","whip","club","halberd","glaive","rapier","machete","shuriken","kusarigama","nunchaku","claw","gauntlet","arrow","javelin","bolas","boomerang"),
      N("sword","blade","katana","spear","axe","hammer","mace","dagger","gun","rifle","pistol","bow","crossbow","scythe","whip","shuriken","javelin","weapon")),
    R("dagger", ["item"], N("dagger","dirk","stiletto","shiv","kunai","tanto","kris"),
      N("dagger","shiv","kunai")),
    R("flexible", ["item"], N("whip","chain","rope","flail","kusarigama","nunchaku","scarf","ribbon","tendril"),
      N("whip","chain","rope","flail","tendril")),
    R("fist", ["item"], N("gauntlet","knuckle","brass knuckle","glove","claw","fist"),
      N("gauntlet","knuckle","claw","fist")),
    R("armor", ["item"], N("armor","armour","plate","mail","cuirass","helm","helmet","gauntlet","greaves","boots","cloak","robe","mantle","vest","suit","hazmat","garb","kimono","hood","barding","regalia"),
      N("armor","armour","plate","mail","cuirass","helm","helmet","greaves","cloak","robe","mantle","vest","suit")),
    R("accessory", ["item"], N("ring","amulet","necklace","bracelet","earring","charm","trinket","talisman","pendant","tiara","crown","mask","goggles","glasses","visor","scarf","belt","badge","brooch","hairpin","circlet","locket","cufflink"),
      N("ring","amulet","necklace","bracelet","earring","trinket","talisman","pendant","tiara","circlet","locket","brooch")),
    R("tool", ["item"], N("tool","kit","toolbox","wrench","screwdriver","drill","saw","pickaxe","shovel","lantern","torch","key","compass","rope","grapple","scanner","camera","detector","radio","beacon","clamp","welder","fabricator","gadget","multitool"),
      N("tool","toolbox","wrench","screwdriver","drill","lantern","torch","grapple","scanner","detector","fabricator","gadget")),
    R("consumable", ["item"], N("potion","elixir","serum","tonic","draught","pill","capsule","injection","syringe","snack","ration","food","meal","drink","beverage","salve","balm","antidote","grenade","bomb","dynamite","flare","stim","nectar","ambrosia","dew","cookie","cake","tea","coffee","beer","wine","sake","beans","jerky","hypo","vial"),
      N("potion","elixir","serum","tonic","draught","pill","capsule","injection","syringe","ration","antidote","grenade","bomb","dynamite","stim","nectar","ambrosia","vial")),
    R("elixir", ["item"], N("elixir","potion","tonic","draught","serum","nectar","ambrosia","ampule","vial"),
      N("elixir","potion","tonic","draught","serum","ampule","vial")),
    R("grimoire", ["item"], N("grimoire","tome","book","manual","codex","spellbook","scroll","ledger","journal","notebook","blueprint","handbook","scripture","inscription","tablet"),
      N("grimoire","tome","spellbook","codex","scroll","manual","blueprint","scripture","inscription")),
    R("resource", ["item"], N("ore","ingot","bar","gem","shard","essence","core","fuel","biomass","scrap","parts","coin","crystal","dust","powder","pelt","sap","resin","nugget","brick","battery","ammo","bullet","quill","feather","hide","leather"),
      N("ore","ingot","gem","shard","essence","biomass","scrap","nugget","bullet","pelt","hide","battery")),
    R("material", ["item"], N("leather","silk","cloth","thread","dye","bone","wood","log","steel","iron","copper","bronze","alloy","plating","sheet","wire","glass","clay","ceramic","polymer","nanotube","ingot"),
      N("alloy","plating","nanotube","polymer")),
    R("vehicle", ["item"], N("car","bike","motorcycle","truck","van","tank","jet","plane","ship","boat","submarine","mech","hovercraft","skateboard","train","chopper","starship","shuttle","strider","mount","wings","speeder","rover","fighter"),
      N("motorcycle","hovercraft","starship","submarine","speeder","rover","vehicle")),
    R("storage", ["item"], N("bag","satchel","backpack","pouch","chest","vault","inventory","warehouse","locker","container","hold","crate","box","case","sheath","holster","coffer"),
      N("satchel","backpack","pouch","vault","warehouse","locker","sheath","holster")),
    R("dimension", ["item"], N("dimension","domain","sanctuary","realm","plane","pocket"),
      N("dimension","sanctuary","pocket realm")),
    R("building", ["item"], N("house","home","base","fortress","castle","tower","shop","store","factory","farm","barracks","lab","laboratory","academy","temple","garden","mine","reactor","habitat","station","colony","pond","cauldron","foundry","forge","library","greenhouse","airport","arena","manor","estate","vault"),
      N("fortress","castle","laboratory","academy","habitat","colony","foundry","greenhouse","landmark")),
    R("implant", ["item"], N("implant","augment","cyberware","prosthetic","neural","interface","graft","biomod","exoplant"),
      N("implant","augment","cyberware","prosthetic","neural implant")),
    R("ticket", ["item"], r"\btickets?\b", r"\btickets?\b"),
    R("card", ["item"], N("card","deck","tarot","die","dice","token","chip","board game","chess","domino"),
      N("card","deck","tarot","dice","board game","chess","domino")),
    R("mundane", ["item"], N("laptop","phone","toaster","microwave","fridge","vacuum","stapler","pen","pencil","cup","mug","chair","table","bed","soap","shampoo","spray","febreze","wax","string","bottle","cushion","blanket","umbrella","towel","broom","gloves","calendar","clock","umbrella"),
      N("toaster","microwave","stapler","vacuum cleaner","soap","shampoo","hair dryer")),
    R("machine", ["item"], N("machine","engine","generator","robot","drone","computer","server","terminal","android","automaton","turret","sentry","replicator","printer","mill","pump","turbine","mainframe"),
      N("machine","engine","generator","robot","drone","computer","server","replicator","turbine","mainframe")),
    R("production", ["item"], N("factory","mill","farm","refinery","printer","forge","loom","assembl","replicator","generator","greenhouse","reactor","mine"),
      N("factory","refinery","forge","loom","replicator","greenhouse","reactor")),
    R("catalyst", ["item"], N("catalyst","focus","wand","staff","orb","focusing","scepter","rod"),
      N("catalyst","wand","orb","scepter","focusing")),
    R("fumo", ["item"], N("plush","plushie","fumo","doll","figurine","statuette","toy"),
      N("plush","plushie","fumo","doll","figurine")),
    R("divine", ["item"], N("god","goddess","divine","angel","holy","sacred","relic","grail","ark"),
      N("divine","relic","grail")),
    R("growing", ["item"], N("seed","sprout","sapling","egg","seedling"),
      N("seed","sprout","sapling","seedling")),
    # ---------------- elements & themes (no skill entries) ----------------
    R("fire", ELEM, N("fire","flame","blaze","ember","pyro","magma","lava","ashen","scorch","inferno","hellflame","hellfire","volcanic","sunburst","solar","bonfire","brazier","cinder","kiln"),
      r"\b(wield|conjure|emit|control|manipulate|generate|breathe|produce)\b[^.]{0,40}\b(fire|flames?)\b"),
    R("ice", ELEM, N("ice","frost","freeze","frozen","cryo","glacier","blizzard","snow","hail","chill","icicle","permafrost","winter"),
      r"\b(wield|conjure|emit|control|manipulate|generate|breathe|produce)\b[^.]{0,40}\b(ice|frost)\b"),
    R("water", ELEM, N("water","aqua","hydro","tide","ocean","sea","rain","steam","mist","bubble","flood","whirlpool","reef","drown","geyser"),
      r"\b(wield|conjure|emit|control|manipulate|generate|breathe|produce)\b[^.]{0,40}\b(water|tide|waves?)\b"),
    R("air", ELEM, N("air","wind","gale","tornado","cyclone","whirlwind","hurricane","vacuum","zephyr","typhoon","breeze","updraft","cloud","sky","gust"),
      r"\b(wield|conjure|emit|control|manipulate|generate|breathe|produce)\b[^.]{0,40}\b(wind|air|storms?)\b"),
    R("electric", ELEM, N("electric","lightning","thunder","volt","shock","plasma","emp","tesla","static","storm","arc","spark"),
      r"\b(wield|conjure|emit|control|manipulate|generate|breathe|produce)\b[^.]{0,40}\b(lightning|electricity|thunder)\b"),
    R("earth", ELEM, N("earth","stone","rock","sand","mud","metal","iron","steel","copper","gold","silver","quake","stalagmite","terra","geode","magnet","mineral","dirt","clay","obsidian","granite","quartz","crystal","gem"),
      r"\b(wield|conjure|emit|control|manipulate|generate|raise)\b[^.]{0,40}\b(earth|stone|rocks?|metal|sand)\b"),
    R("dark", ELEM, N("dark","shadow","void","abyss","umbra","gloom","eclipse","null","nightfall","nether","shade","twilight"),
      r"\b(wield|conjure|emit|control|manipulate|become|shroud)\b[^.]{0,40}\b(shadow|darkness|void|abyss)\b"),
    R("light", ELEM, N("light","radiant","laser","beam","prism","glow","sunlight","sunshine","lumen","photon","flash","flashlight","dawn","hologram"),
      r"\b(wield|conjure|emit|control|manipulate|generate)\b[^.]{0,40}\b(light|lasers?|beams?)\b"),
    R("holy", ELEM, N("holy","sacred","angel","seraph","blessed","sancti","divine","exorcism","paladin","celestial","heavenly","grace","relic"),
      r"\b(holy|sacred|blessed|sanctified|exorcism|divine)\b"),
    R("infernal", ELEM, N("demon","devil","infernal","hell","diabolic","fiend","imp","succubus","incubus","unholy","profane","brimstone","underworld","nether","oni"),
      r"\b(demonic|infernal|hellish|unholy|profane)\b"),
    R("necro", ELEM, N("necro","undead","zombie","skeleton","lich","wraith","ghoul","revenant","corpse","grave","death","reaper","dullahan","bone","tomb","mummy","banshee","crypt","skull"),
      r"\b(necro|undead|zombie|skeleton|lich|wraith|ghoul|corpse|reanimat|raise the dead)\w*\b"),
    R("nature", ELEM, N("nature","plant","flora","vine","thorn","wood","forest","grove","moss","bloom","leaf","root","seed","spore","mushroom","herb","druid","petal","tree","grass","flower","jungle","swamp","bark","bramble","blossom"),
      r"\b(plants?|vines?|forest|nature|flora|trees?|roots?)\b"),
    R("poison", ELEM, N("poison","venom","toxic","acid","corrosive","plague","fume","rot","blight","miasma","radiation","sewage","sludge","mold"),
      r"\b(poison|venom|toxic|acidic|corrosive|plague|blight|miasma)\w*\b"),
    R("bio", ELEM, N("flesh","bones","organs","muscle","genes","biolog","mutat","chimera","parasite","virus","cellular","dna","clon","fungal","splic","marrow","tendon","graft"),
      r"\b(flesh|organs?|graft|mutat|biolog|genes?|dna)\w*\b"),
    R("life", ELEM, N("life","lifeforce","vitality","heal","regenerat","revive","restore","resurrect","rebirth","fertility","vital","bloom"),
      r"\b(lifeforce|vitality|revive|resurrect|rebirth|rejuvenat)\w*\b"),
    R("spirit", ELEM, N("spirit","soul","ghost","spectral","phantom","ethereal","astral","possess","haunt","apparition","kami","revenant"),
      r"\b(spirits?|souls?|ghostly|spectral|astral|possess)\w*\b"),
    R("space", ELEM, N("space","spatial","dimension","portal","teleport","warp","rift","wormhole","blink","gate","singularity","fold","teleportation"),
      r"\b(portals?|teleport|dimension|warp|spatial|rift|wormhole)\w*\b"),
    R("time", ELEM, N("time","temporal","chrono","rewind","loop","haste","stasis","acceleration","prophecy","precognit","foresight","future","clock","hourglass","eternity"),
      r"\b(temporal|time|chrono|rewind|precognition|foresight|prophec)\w*\b"),
    R("gravity", ELEM, N("gravity","graviton","mass","weight","levitation","repuls","float","heavy","singularity"),
      r"\b(gravity|gravitational|levitat|float|weightlessness)\w*\b"),
    R("sound", ELEM, N("sound","sonic","voice","song","scream","roar","music","resonan","frequency","ultrasonic","siren","bell","drum","echo","whisper","radio","noise","shout","hum","sonar","chime"),
      r"\b(sound|sonic|resonance|frequency|ultrasound|music|song|roar|scream|voice)\w*\b"),
    R("kinetic", ELEM, N("kinetic","impact","momentum","inertia","concussi","shockwave","slam","bash","punch","strike","kick","blast","explosion","detonat","crush"),
      r"\b(kinetic|shockwave|impact|explosive|concussi)\w*\b"),
    R("mental", ELEM, N("mind","mental","psychic","psionic","telepath","telekinesis","memory","dream","illusion","charm","dominate","hypno","fear","willpower","empath","insanity","lucid","mesmer"),
      r"\b(mind|mental|psychic|telepathy|dreams?|memories|illusions?|hypno)\w*\b"),
    R("tech", ELEM, N("tech","cyber","nano","robot","drone","computer","software","hack","digital","virtual","android","machine","mech","laser","hologram","satellite","reactor","circuit","prosthetic","engine","data","code","server","signal"),
      r"\b(technolog|cyber|nano|robot|drone|computer|software|hack|digital|machine|mech|circuit|data|code)\w*\b"),
    R("magic", ELEM, N("magic","arcane","spell","mana","rune","enchant","ward","wizard","sorcer","witch","hex","ritual","sigil","grimoire","mage","spellcast","cantrip","alchem"),
      r"\b(magic|arcane|spells?|mana|rune|enchant|witchcraft|sorcer|ritual|alchem)\w*\b"),
    R("curse", ELEM, N("curse","hex","jinx","doom","maledict","blight","jinx"),
      r"\b(curses?|hex|jinx|doom|maledict)\w*\b"),
    R("command", ELEM, N("command","dominate","obey","order","leadership","authority","subjugat","enslave","puppet","rule","throne","crown","legion","army","swarm","warlord"),
      r"\b(command|dominate|obey|subjugat|enslave|puppet)\w*\b"),
    R("summon", ELEM, N("summon","conjure","familiar","minion","servant","construct","golem","skeleton","clone","spawn","portal","horde","legion"),
      r"\b(summon|conjure|spawn|familiar)\w*\b"),
    R("recovery", ELEM, N("heal","regen","recover","restore","revive","resurrect","rejuvenat","purif","cure","mend","nurse","salve"),
      r"\b(heal|regenerat|recover|restore|revive|resurrect|purif|cure)\w*\b"),
    R("transformation", ELEM, N("transform","shapeshift","morph","hybrid","becom","polymorph","physiolog","form","alter self","metamorph"),
      r"\b(transform|shapeshift|morph|polymorph|metamorph)\w*\b"),
    R("movement", ELEM, N("speed","dash","sprint","flight","teleport","blink","phase","dodge","evade","jump","levitat","hover","swim","climb","portal","warp","step","ride","travel","charge"),
      r"\b(teleport|dash|sprint|flight|levitat|hover|blink|warp)\w*\b"),
    R("stealth", ELEM, N("stealth","invisib","silence","silent","sneak","cloak","conceal","hide","assassin","prowl","camouflage","shadow","pickpocket","vanish","steal"),
      r"\b(stealth|invisib|sneak|conceal|camouflage|assassinat)\w*\b"),
    R("sense", ELEM, N("sense","sensor","detect","scan","perception","awareness","vision","sight","hearing","smell","radar","sonar","analysis","identify","observe","watch","eye","scan"),
      r"\b(senses?|detect|scans?|perception|awareness|radar|sonar|identif)\w*\b"),
    R("ocular", ELEM, N("eye","eyes","vision","sight","gaze","glare","stare","iris","pupil","optic","telescope","microscope"),
      r"\b(eyes?|eyesight|gaze|vision)\w*\b"),
    R("divination", ELEM, N("divination","prophecy","precognit","foresight","clairvoy","scry","oracle","fortune","omen","predict","augury","tarot"),
      r"\b(divination|prophec|precognit|foresight|clairvoy|scry|oracle|omen)\w*\b"),
    R("alter", ELEM, N("alter","modify","reality","rewrite","distort","convert","transmut","matter","transmigrat","transfigur","reshap"),
      r"\b(alter|modify|reality|rewrite|distort|transmut|transfigur)\w*\b"),
    R("growth", ELEM, N("growth","level","experience","evolut","upgrade","develop","train","improve","advance","evolve","mastery"),
      r"\b(growth|evolut|upgrade|develop|level up|experience|training)\w*\b"),
    R("meta", ELEM, N("gacha","ticket","meta","rarity","reroll","shuffle"),
      N("gacha","tickets?","rerolls?","shuffle")),
    R("ilusion", ["item", "familiar", "ability", "trait"], N("illusion","mirage","decoy","clone","disguise","figment","phantasm"),
      r"\b(illusion|mirage|decoy|disguise)\w*\b"),
    R("buff", ["ability", "trait", "item"], N("blessing","bless","empower","augment","enhance","fortify","inspire","haste","buff"),
      r"\b(blessing|augment|empower|fortify|enhance)\w*\b"),
    R("debuff", ["ability", "trait", "item"], N("curse","weaken","hex","slow","blind","stun","silence","drain","sap"),
      r"\b(weaken|curse|blind|stun|drain|sap|debilitat)\w*\b"),
    R("enhancer", ["ability", "trait"], N("strength","might","power","physique","durab","tough","endurance","vitality","agility","speed","reflex","enhanc","buff","boost","surge","rage","berserk","muscle","armor","armour","hardening","fortitude"),
      r"\b(empower|augment|boost|enhance|strengthen|fortif|toughen)\w*\b"),
    R("martial", ["ability", "trait"], N("martial","combat","fight","sword","blade","weapon","boxing","karate","kung fu","muay","wrestl","archery","gun","marksman","sharpshoot","melee","unarmed","stance"),
      r"\b(martial arts?|melee|weapon mastery|combat prowess)\w*\b"),
    R("kinesis", ["ability"], N("kinesis","telekinesis","manipulation","telekinetic"),
      r"\b(telekinetic|kinesis|manipulat)\w*\b"),
    R("neutral", ["ability", "trait"], N("neutral","raw energy","pure energy"),
      r"\b(raw energy|pure energy|neutral energy|energy beam|energy blast)\w*\b"),
    R("power", ["trait"], N("power","superpower","innate","awaken","apex","omnipot"),
      r"\b(powerful|superpower|innate power)\w*\b"),
    R("rule", ["trait"], N("law","rule","world","concept","domain","fundamental","absolute","immutable","axiom"),
      r"\b(law|rule|concept|domain|fundamental|absolute)\w*\b"),
    R("body", ["trait"], N("body","physique","anatomy","limb","organ","blood","skin","bone","size","shape","flesh","wing","tail","horn","claw"),
      r"\b(bodies|body|physique|anatomy|limbs?|organs?|flesh)\w*\b"),
    R("mind", ["trait"], N("mind","mental","psyche","sanity","memory","focus","will","intellect","brain","reason"),
      r"\b(mind|mental|psyche|sanity|memories|intellect|willpower)\w*\b"),
    R("social", ["trait"], N("charisma","social","persua","charm","befriend","flirt","romance","seduce","diplomac","reputation","fame","harem","rapport","loyalty","trust","command respect","allure"),
      r"\b(charisma|persua|charm|seduce|diplomac|loyalty|rapport|reputation)\w*\b"),
    R("talent", ["trait"], N("talent","prodig","genius","aptitude","knack","learn","mastery","potential","proficien","genius"),
      r"\b(talent|prodig|genius|aptitude|mastery|potential)\w*\b"),
    R("lifestyle", ["trait"], N("lifestyle","hygien","sleep","comfort","habit","hobby","entertain","quality of life","grooming","charm school"),
      r"\b(lifestyle|hygien|daily life|comfort|habit)\w*\b"),
    R("survival", ["trait"], N("surviv","endur","hardship","wilderness","forage","resilien","hardy","toughness"),
      r"\b(surviv|endur|resilien|hardy|wilderness)\w*\b"),
    R("bloodline", ["trait"], N("bloodline","lineage","descend","heritage","dynasty","inheritance","scion","ancestry"),
      r"\b(bloodline|lineage|descend|heritage|dynasty|ancestry)\w*\b"),
    R("race-change", ["trait"], r"^Race Change\b|^Race\b", r"\brace change\b"),
    R("health-recovery", ["trait"], N("health","wound","injur","heal","regenerat","vitality","recovery"),
      r"\b(health|wounds?|injur|heal|regenerat)\w*\b"),
    R("energy-recovery", ["trait"], N("energy","mana","stamina","reserve","regenerat"),
      r"\b(energy|mana|stamina|reserves?)\w*\b"),
    R("maximum-energy+", ["trait"], N("maximum energy","energy capacity","mana pool","reserve pool"),
      r"\b(maximum|reserve|capacity|pool|total)\b[^.]{0,20}\b(energy|mana|stamina)\b"),
    R("power+", ["trait"], None, r"\b(augment|amplif|increase)\b[^.]{0,30}\b(power|strength|ability)\b"),
    R("perception+", ["trait"], None, r"\b(augment|amplif|increase|sharpen)\b[^.]{0,30}\b(perception|senses|awareness)\b"),
    R("agility+", ["trait"], None, r"\b(augment|amplif|increase)\b[^.]{0,30}\b(agility|speed|reflex)\b"),
    R("strength+", ["trait"], None, r"\b(augment|amplif|increase)\b[^.]{0,30}\b(strength|might)\b"),
    R("defence+", ["trait"], None, r"\b(augment|amplif|increase)\b[^.]{0,30}\b(defence|defense|durability|resilience)\b"),
    R("recovery+", ["trait"], None, r"\b(augment|amplif|increase|boost)\b[^.]{0,30}\b(healing|recovery|regeneration)\b"),
    R("luck+", ["trait"], None, r"\b(augment|amplif|increase|boost)\b[^.]{0,30}\b(luck|fortune)\b"),
    # ---------------- familiars: kind, size, role ----------------
    # Draconic is the only creature-kind tag the official dictionaries also use
    # for abilities, items and traits (a "dragon form" ability, a dragon-scale
    # item); the rest are familiar-only.
    R("draconic", ELEM, N("dragon","drake","wyvern","wurm","wyrm","dragonoid","draconic","leviathan","serpent","hydra","basilisk","naga","bahamut","lindworm","wyrmling"),
      r"\b(dragons?|draconic|serpents?|wyverns?|drake)\w*\b"),
    R("reptilian", ["familiar"], N("lizard","reptile","snake","serpent","turtle","tortoise","crocodile","gecko","salamander","basilisk","skink","iguana","komodo","viper","cobra","python"),
      r"\b(lizard|reptile|serpent|snake|turtle|crocodile|gecko|salamander)\w*\b"),
    R("beast", ["familiar"], N("wolf","dog","hound","cat","tiger","lion","bear","fox","rabbit","boar","deer","horse","bull","cow","ape","monkey","gorilla","rat","mouse","squirrel","bat","beast","panther","leopard","rhino","hippo","elephant","sheep","goat","pig","sloth","otter","badger","weasel","yak","mammoth","chimera","griffon","manticore","warg","canine","feline","ursine","koala","panda","hamster","alpaca","llama","walrus","seal","dolphin","kangaroo","hedgehog","mole","hare","puppy","kitten","sabertooth","coyote","jackal","hyena","lynx","jaguar","cheetah","gazelle","antelope","bison","moose","elk","reindeer","capybara","squirrel"),
      r"\b(wolf|hound|canine|feline|beast|animal|mammal|paws?|furred|furry)\w*\b"),
    R("avian", ["familiar"], N("bird","hawk","eagle","owl","crow","raven","dove","swallow","falcon","phoenix","harpy","griffin","roc","thunderbird","peacock","penguin","duck","goose","chicken","chocobo","fowl","vulture","parrot","macaw","kiwi","ostrich","swan","heron","crane","stork","rooster","hen","chick","sparrow","finch","robin","jay","magpie","condor","kite"),
      r"\b(bird|avian|feathers?|wingspan|fowl|raptor)\w*\b"),
    R("aquatic", ["familiar"], N("fish","shark","whale","dolphin","octopus","squid","kraken","leviathan","crab","shrimp","jellyfish","eel","stingray","mermaid","fishman","naiad","koi","angler","turtle","tortoise","seal","walrus","lobster","clam","oyster","urchin","coral","anemone","manatee","narwhal","barracuda","piranha","carp","trout","salmon","tuna"),
      r"\b(aquatic|fish|marine|underwater|tentacles?|fins?|gills?)\w*\b"),
    R("insectoid", ["familiar"], N("insect","bug","ant","bee","wasp","moth","butterfly","beetle","spider","scorpion","centipede","mantis","cockroach","termite","larva","worm","leech","mite","tick","flea","hornet","dragonfly","firefly","weevil","arachnid"),
      r"\b(insect|arachnid|chitin|carapace|swarm of (bugs|insects)|spider|scorpion)\w*\b"),
    R("plant", ["familiar"], N("plant","flower","tree","vine","moss","mushroom","fungus","treant","dryad","alraune","seed","sprout","leaf","root","petal","lily","fern","cactus","bush","shrub","bonsai","pumpkin","mandrake","blossom"),
      r"\b(plant|flora|vine|tree|moss|fungus|mushroom|petals?|leaves|roots?)\w*\b"),
    R("golem", ["familiar"], N("golem","construct","automaton","android","robot","mech","machine","statue","elemental","drone","sentry","titan","homunculus","effigy"),
      r"\b(golem|construct|automaton|android|robot|machine|animated (armor|statue))\w*\b"),
    R("amorphous", ["familiar"], N("slime","ooze","goo","blob","gel","amorph","shoggoth","mimic","amoeba"),
      r"\b(slime|ooze|blob|amorphous|gelatinous)\w*\b"),
    R("incorporeal", ["familiar"], N("ghost","spirit","wraith","specter","spectre","phantom","shade","poltergeist","wisp","djinn","genie","apparition","banshee","revenant"),
      r"\b(ghost|spirit|wraith|specter|phantom|incorporeal|ethereal)\w*\b"),
    R("humanoid", ["familiar"], N("man","woman","girl","boy","lady","lord","knight","maid","butler","witch","wizard","sorcer","priest","monk","ninja","samurai","warrior","hunter","assassin","thief","merchant","smith","human","elf","dwarf","orc","goblin","troll","giant","ogre","demon","devil","angel","valkyrie","siren","vampire","noble","king","queen","princess","prince","empress","emperor","saint","ronin","berserker","nun","bishop","duelist","gladiator","oni"),
      r"\b(humanoid|human|person|woman|man|maiden|knight|warrior)\w*\b"),
    R("equine", ["familiar"], N("horse","pony","stallion","mare","pegasus","unicorn","centaur","nightmare","steed"),
      r"\b(horse|equine|stallion|mare|pegasus|unicorn|centaur)\w*\b"),
    R("alien", ["familiar"], N("alien","xeno","eldritch","cthulhu","tentacle","zerg","tyranid","protoss","neomorph","xenomorph","martian","kryptonian","ethereal","cosmic","extraterrestrial"),
      r"\b(alien|xeno|extraterrestrial|eldritch|otherworldly)\w*\b"),
    R("divine", ["familiar"], N("god","goddess","deity","divine","angel","seraph","valkyrie","titan","primordial","celestial","kami","nephilim"),
      r"\b(divine|god|goddess|deity|celestial|heavenly)\w*\b"),
    R("flying", ["familiar"], N("wing","feather","aerial","pegasus","wyvern","airy","hover","glide","soar"),
      r"\b(fly|flying|flight|wings?|soar|glide|hover)\w*\b"),
    R("evolving", ["familiar"], N("evolv","evolut","metamorph","larva","cocoon","pupa"),
      r"\b(evolv|evolut|metamorph|larva|cocoon|pupa)\w*\b"),
    R("breeding", ["familiar"], N("breed","egg","nest","spawn","mate","offspring","hatch","colony","hive","reproduc","clutch","litter"),
      r"\b(breed|eggs?|nest|hatch|litter|offspring|reproduc)\w*\b"),
    R("shapeshifter", ["familiar"], N("shapeshift","transform","morph","doppelganger","mimic","polymorph","were"),
      r"\b(shapeshift|transform|morph|polymorph|doppelganger)\w*\b"),
    R("immortal", ["familiar"], N("immortal","undying","eternal","deathless","unaging","respawn","phoenix","ageless"),
      r"\b(immortal|undying|deathless|respawn|ageless)\w*\b"),
    R("regenerator", ["familiar"], N("regenerat","respawn","revive","reassembl"),
      r"\b(regenerat|respawn|reassembl|rapid healing)\w*\b"),
    R("healer", ["familiar"], N("heal","medic","cleric","nurse","mender","apothecar","pharmac"),
      r"\b(heal|medic|cleric|nurse|mender|curative)\w*\b"),
    R("fighter", ["familiar"], N("fighter","brawler","bruiser","warrior","knight","berserker","brute","tank","guard","warden","champion","duelist","gladiat","axeman","swordsman","boxer","wrestler"),
      r"\b(fighter|brawler|warrior|duelist|combatant|melee)\w*\b"),
    R("blaster", ["familiar"], N("blaster","gunner","cannon","beam","blast","shooter","artillery","turret","ray","artillerist"),
      r"\b(blaster|gunner|artillery|energy beams?)\w*\b"),
    R("magician", ["familiar"], N("mage","magician","sorcer","wizard","warlock","shaman","druid","oracle","enchant","spellcast","spellcaster"),
      r"\b(mage|magician|sorcer|wizard|warlock|shaman|spellcast|enchant)\w*\b"),
    R("psychic", ["familiar"], N("psychic","psionic","telepath","esper","mesmer","hypno"),
      r"\b(psychic|psionic|telepath|esper|mesmer)\w*\b"),
    R("summoner", ["familiar"], N("summon","conjur","necromanc","tamer","beastmaster","shikigami"),
      r"\b(summon|conjur|necromanc|tamer|beastmaster|shikigami)\w*\b"),
    R("ranger", ["familiar"], N("ranger","archer","sniper","marksman","sharpshoot","scout","hunter"),
      r"\b(ranger|archer|sniper|marksman|scout|hunter)\w*\b"),
    R("mechanic", ["familiar"], N("mechanic","engineer","tinker","artificer","inventor","technician","machinist","sapper"),
      r"\b(mechanic|engineer|tinker|artificer|inventor|technician)\w*\b"),
    R("tactician", ["familiar"], N("tactic","strateg","commander","captain","general","planner","advisor","vizier","marshal","officer","admiral","warlord"),
      r"\b(tactic|strateg|command|marshal|admiral|warlord)\w*\b"),
    R("trickster", ["familiar"], N("trickster","thief","rogue","jester","prankster","swindler","illusionist","kitsune","tanuki"),
      r"\b(trickster|thief|rogue|jester|illusionist|prankster)\w*\b"),
    R("manipulator", ["familiar"], N("manipulat","puppet","domin","hypno","enslave","corrupt"),
      r"\b(manipulat|puppet|mind control|enslave|possess)\w*\b"),
    R("artisan", ["familiar"], N("artisan","craftsman","blacksmith","smith","artist","cook","chef","weaver","tailor","jeweler","potter","builder","architect","brewer"),
      r"\b(artisan|craftsman|blacksmith|weaver|tailor|chef|cook|builder)\w*\b"),
    R("worker", ["familiar"], N("worker","laborer","porter","servant","maid","butler","caretaker","farmer","miner","scribe","clerk","assistant"),
      r"\b(worker|laborer|porter|servant|maid|butler|caretaker|farmer|miner)\w*\b"),
    R("mentor", ["familiar"], N("mentor","teacher","sage","elder","tutor","sensei","guru","instructor","professor"),
      r"\b(mentor|teacher|sage|elder|tutor|sensei|instructor)\w*\b"),
    R("non-combatant", ["familiar"], N("civilian","merchant","vendor","shopkeeper","bureaucrat","mascot"),
      r"\b(civilian|non-combatant|merchant|shopkeeper)\w*\b"),
    R("resource", ["familiar"], N("cow","chicken","sheep","bee","farm","milk","wool","egg","honey","harvest","resource","producer"),
      r"\b(milk|wool|eggs?|honey|harvest|resource)\w*\b"),
    R("parasitic", ["familiar"], N("parasite","parasitic","infect","symbio","leech","virus","fungal"),
      r"\b(parasit|infect|symbio|leech|host body)\w*\b"),
    R("linked", ["familiar"], N("link","bond","contract","pact","servant","bound"),
      r"\b(soul ?link|bond|contract|pact|bound to)\w*\b"),
    R("character", ["familiar"], N("sentient","intelligent","character","speaks","talks","personality","opinionated"),
      r"\b(sentient|intelligent|speaks|talks|personality|opinionated)\w*\b"),
    R("informant", ["familiar"], N("informant","spy","detective","investigator","gossip"),
      r"\b(informant|spy|detective|investigator|intel)\w*\b"),
    R("biokinetic", ["familiar"], N("biokin","fleshcraft","biomass"),
      r"\b(biokin|fleshcraft|biomass|flesh|genes?|organs?|blood)\w*\b"),
    R("technopath", ["familiar"], N("technopath","hack","cyber","electronic","network","drone"),
      r"\b(technopath|hack|cyber|electronic|machine control)\w*\b"),
    R("teleporter", ["familiar"], N("teleport","portal","warp","blink","rift"),
      r"\b(teleport|portal|warp|rift)\w*\b"),
    R("reality-bender", ["familiar"], N("reality","wish","causality","probability","rewrite"),
      r"\b(reality|wish|casualit|probability|time stop)\w*\b"),
    R("martial-artist", ["familiar"], N("martial artist","monk","karate","kung fu","boxer","wrestler","swordsman","duelist","samurai","ninja"),
      r"\b(martial artist|monk|karate|kung fu|boxer|wrestler|swordsman|duelist)\w*\b"),
    R("small-size", ["familiar"], N("imp","pixie","fairy","sprite","homunculus","doll","puppet"),
      r"\b(dog cage|pocket|tiny|small|diminutive|pixie|fairy)\w*\b"),
    R("medium-size", ["familiar"], None, r"\b(human size|around human|dog size|child size|medium[- ]sized?)\b"),
    R("large-size", ["familiar"], N("colossus","behemoth","leviathan"),
      r"\b(buildings?|corridors?|horse[- ]sized?|car[- ]sized?|hulking|large|giant|enormous)\w*\b"),
    R("massive-size", ["familiar"], None, r"\b(street|skyscraper|massive|kaiju|elder dragon)\b"),
    R("titanic-size", ["familiar"], None, r"\b(titanic|colossal|godzilla|world serpent|continental|planet[- ]sized?)\b"),
    R("group", ["familiar"], N("swarm","horde","flock","pack","colony","legion","squad","army","cluster","collective"),
      r"\b(swarm|horde|flock|pack of|colony|legion|army|squad)\w*\b"),
    # ---------------- skills: only the 18 skill tags ----------------
    R("ranged", ["skill"], N("shooting","marksman","archery","sniper","gunslinger","firearms","throwing","bow","sling","gunnery"),
      r"\b(guns?|bows?|throwing|archery|marksman|sharpshoot|firearms)\w*\b"),
    R("weapon", ["skill"], N("sword","blade","spear","polearm","axe","hammer","mace","weapon","dagger","bow","glaive","halberd","scythe","whip","shield","crowbar"),
      r"\b(swords?|blades?|spears?|axes?|hammers?|weapons?|daggers?|shields?|crowbar)\w*\b"),
    R("motor", ["skill"], N("driving","piloting","riding","swimming","climbing","acrobat","parkour","balance","reflex","dance","athletic","sprinting","jumping"),
      r"\b(driving|piloting|riding|swimming|climbing|acrobat|parkour|athletic|balance|reflex)\w*\b"),
    R("social", ["skill"], N("charisma","persua","deception","diplomac","intimidat","negotiat","etiquette","leadership","performance","acting","lying","seduction","barter","haggl","courtly","oratory","command"),
      r"\b(charisma|persua|deception|diplomac|intimidat|negotiat|etiquette|leadership|acting|seduction|barter)\w*\b"),
    R("craft", ["skill"], N("craft","smith","weav","sewing","tailor","pottery","woodwork","construction","engineer","mechanic","repair","cook","brew","alchem","factory","planning","masonry","forging","carving","paint","sculpt","deckbuild"),
      r"\b(craft|smith|weav|tailor|pottery|construction|engineer|repair|cook|brew|alchem|mason|forg|carv|deckbuild)\w*\b"),
    R("science", ["skill"], N("science","biology","chemistry","physics","mathematic","research","survey","astronom","geolog","xenobiolog","logic","analysis","study","reasoning"),
      r"\b(science|biology|chemistry|physics|mathematic|research|astronom|geolog|logic|analysis|reasoning)\w*\b"),
    R("medical", ["skill"], N("medic","surgery","herbal","anatomy","doctor","nurse","pharmac","veterinar","bandage","treatment","first aid"),
      r"\b(medic|surgery|herbal|anatomy|doctor|nurse|pharmac|veterinar|treatment|first aid)\w*\b"),
    R("stealth", ["skill"], N("stealth","sneak","assassin","prowl","pickpocket","lockpick","infiltration","disguise","larceny","thievery","ambush","stealing"),
      r"\b(stealth|sneak|assassin|pickpocket|lockpick|infiltration|disguise|thievery|stealing|ambush)\w*\b"),
    R("movement", ["skill"], N("driving","piloting","riding","swimming","climbing","parkour","traversal","navigation","sailing","running","acrobat","hopping"),
      r"\b(driving|piloting|riding|swimming|climbing|parkour|navigation|sailing|running)\w*\b"),
    R("mental", ["skill"], N("meditation","focus","memory","mind","mental","concentration","willpower","awareness","discipline","logic","creativity"),
      r"\b(meditation|focus|memory|mental|concentration|willpower|awareness|discipline|creativity)\w*\b"),
    R("magic", ["skill"], N("magic","spell","arcane","rune","ritual","alchem","enchant","summon","conjur","divination","necromancy","wizardry"),
      r"\b(magic|spell|arcane|rune|ritual|enchant|summon|conjur|divination|necromancy)\w*\b"),
    R("technique", ["skill"], N("technique","style","kata","stance","breathing","flow","maneuver","footwork","arts","finesse"),
      r"\b(technique|style|kata|stance|breathing|maneuver|footwork|finesse)\w*\b"),
    R("tech", ["skill"], N("hacking","programming","cyber","computer","electronics","interface","robotics","engineering","machinery","machine override"),
      r"\b(hacking|programming|cyber|computer|electronics|robotics|machinery)\w*\b"),
    R("unarmed", ["skill"], N("unarmed","martial art","karate","kung fu","boxing","wrestl","grappl","muay","taekwondo","judo","hand-to-hand","jiu","aikido"),
      r"\b(unarmed|martial arts?|karate|kung fu|boxing|wrestl|grappl|muay|taekwondo|judo)\w*\b"),
    R("expertise", ["skill"], N("expertise","knowledge","theory","lore","academic","scholar"),
      r"\b(expertise|knowledge|theory|lore|academic|scholar)\w*\b"),
    R("unique", ["skill"], N("unique","otherworld","isekai","bloodline"),
      r"\b(unique|otherworld|isekai|not replicable|gacha-exclusive)\w*\b"),
]

# Families where a description mention is as good as a name mention (elements,
# creature kinds, roles). Everything else keeps its explicit description rule.
LOOSE = {
    "fire","ice","water","air","electric","earth","dark","light","holy","infernal",
    "necro","nature","poison","bio","life","spirit","space","time","gravity","sound",
    "kinetic","mental","tech","magic","curse","command","summon","recovery",
    "transformation","movement","stealth","sense","ocular","divination","alter","growth",
    "meta","blade","polearm","bludgeon","gun","bow","shield","weapon","dagger","flexible",
    "fist","armor","accessory","tool","consumable","elixir","grimoire","resource",
    "material","vehicle","storage","dimension","building","implant","card","mundane",
    "machine","production","catalyst","fumo","divine","growing","draconic","reptilian",
    "beast","avian","aquatic","insectoid","plant","golem","amorphous","incorporeal",
    "equine","alien","flying","evolving","breeding","shapeshifter","immortal",
    "regenerator","healer","fighter","blaster","magician","psychic","summoner","ranger",
    "mechanic","tactician","trickster","manipulator","artisan","worker","mentor",
    "non-combatant","resource","parasitic","linked","character","informant","biokinetic",
    "technopath","teleporter","reality-bender","martial-artist","small-size","large-size",
    "massive-size","titanic-size","group","ranged","weapon","motor","social","craft",
    "science","medical","stealth","movement","mental","magic","technique","tech",
    "unarmed","expertise","unique",
}
CLOSE = {"humanoid", "medium-size", "power", "rule", "body", "mind", "talent",
         "lifestyle", "race-change", "survival", "bloodline", "social", "command",
         "maximum-energy+", "health-recovery", "energy-recovery"}

COMPILED = []
for (t, cats, n, d) in RULES:
    rx_name = re.compile(n, re.I) if n else None
    if t in CLOSE:
        rx_desc = re.compile(d, re.I) if d else None       # explicit rule only
    elif t in LOOSE and n:
        rx_desc = rx_name                                  # same matcher
    else:
        rx_desc = re.compile(d, re.I) if d else None
    COMPILED.append((t, cats, rx_name, rx_desc))

# only tags the category actually uses (official dictionary + curated extras)
_VALID = None


def valid_tags():
    global _VALID
    if _VALID is None:
        with open(os.path.join(oi.DATA, "dicts.json"), encoding="utf-8") as fh:
            dicts = json.load(fh)
        _VALID = {cat: {gt.normalize_tag(t["name"]) for t in items} | CURATED
                  for cat, items in dicts.items()}
    return _VALID


# Hand-tagged untagged entries: rules missed them (prose-heavy text) or the
# right tag is not derivable from a keyword. Verified against each entry's text.
MANUAL = {
    ("familiar", "Solemn Simulacrum"): ["golem", "worker"],
    ("familiar", "Pocket Apocalypse"): ["draconic", "time", "small-size", "curse"],
    ("item", "Type-40 TARDIS"): ["time", "space", "vehicle", "storage"],
    ("item", "Maelstrom"): ["water", "summon", "command"],
    ("item", "Drakkar"): ["vehicle", "movement"],
    ("item", "Penny of the Ferryman"): ["necro", "magic"],
    ("ability", "Counterspell"): ["anti-magic", "magic"],
    # Palworld batch (fork-only): each from its own blurb.
    ("familiar", "Lamball"): ["beast", "resource", "medium-size"],
    ("familiar", "Chikipi"): ["avian", "breeding", "resource", "small-size"],
    ("familiar", "Lifmunk"): ["beast", "flying", "ranger"],
    ("familiar", "Foxparks"): ["beast", "fire", "shapeshifter"],
    ("familiar", "Pengullet"): ["avian"],
    ("familiar", "Tocotoco"): ["avian", "breeding", "resource", "kinetic"],
    ("familiar", "Tanzee"): ["beast", "ranger"],
    ("familiar", "Leezpunk"): ["reptilian", "stealth", "sense"],
    ("familiar", "Lunaris"): ["beast", "gravity"],
    ("familiar", "Bushi"): ["humanoid", "fighter", "martial-artist"],
    ("familiar", "Grizzbolt"): ["beast", "electric", "fighter", "blaster"],
    ("familiar", "Palworld Anubis"): ["beast", "fighter", "martial-artist"],
    ("skill", "Pal Training"): ["craft"],
}


def proposals_for(e):
    valid = valid_tags()[e["file"]]
    tags, why = set(), {}
    # Chaos-Tree meta nodes (Sight, Survey, Compass, Graft...) carry (Tree) and
    # (Meta:...) tokens; they are gacha/system mechanics by construction.
    if "meta" in valid and (e.get("meta") or e.get("tag") == "tree"):
        tags.add("meta"); why["meta"] = "tree"
    for t in MANUAL.get((e["file"], e["name"]), ()):
        if t in valid:
            tags.add(t); why[t] = "manual"
    raw = e["description"] or ""
    # "Race Change - ..." / "Race - ..." is our structural prefix for race
    # traits, so it counts as a name-level signal rather than prose.
    if "race-change" in valid and re.match(r"\s*Race(\s+Change)?\s*[-:]", raw):
        tags.add("race-change"); why["race-change"] = "structural"
    keep = [c for c in re.split(r"[.;]", raw) if not NEG_CLAUSE.search(c)]
    desc = NEG_STRIP.sub(" ", " . ".join(keep))
    for tag, cats, rx_name, rx_desc in COMPILED:
        if e["file"] not in cats or tag not in valid:
            continue
        if rx_name and rx_name.search(e["name"]):
            tags.add(tag); why.setdefault(tag, "name"); continue
        if rx_desc and (rx_desc.search(desc) or rx_desc.search(e["name"])):
            tags.add(tag); why.setdefault(tag, "desc")
    return tags, why


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="print every proposal")
    ap.add_argument("--apply", action="store_true", help="write tags into gachafiles")
    ap.add_argument("--with-desc", action="store_true",
                    help="also apply description-only proposals (review first)")
    ap.add_argument("--json", help="write proposals to a JSON file")
    args = ap.parse_args()

    entries = gt.load_entries(gt.ALL_FILES, None, None, set(), set(), True, True, True)
    untagged = [e for e in entries if not e["tags"]]
    out, dist, none = {}, Counter(), []
    for e in untagged:
        tags, why = proposals_for(e)
        out[f"{e['file']}:{e['number']}"] = {
            "file": e["file"], "name": e["name"], "rarity": e["rarity"],
            "tags": sorted(tags), "why": why}
        dist.update(tags)
        if not tags:
            none.append(e)

    tier_a = {k: v for k, v in out.items()
              if any(x in ("name", "tree", "manual", "structural") for x in v["why"].values())}
    tier_b = {k: v for k, v in out.items()
              if v["tags"] and k not in tier_a}
    def name_tags(v):
        return [t for t in v["tags"] if v["why"].get(t) in ("name", "tree", "manual", "structural")]
    print(f"untagged entries: {len(untagged)}")
    print(f"  A · name-driven proposals: {len(tier_a)} "
          f"({100 * len(tier_a) // max(1, len(untagged))}%)")
    print(f"  B · description-only proposals (review): {len(tier_b)}")
    print(f"  - no proposal: {len(none)}")
    print(f"distinct proposed tags: {len(dist)}")
    print("\nproposed tag counts (top 40):")
    for t, n in dist.most_common(40):
        print(f"  {t:20} {n}")

    def show(rows, limit, tags_of):
        for v in rows[:limit]:
            print(f"  [{v['file']:8}] {v['name'][:32]:32} -> {', '.join(tags_of(v))}")
    if not args.all:
        print("\n== A · name-driven samples (strongest signal) ==")
        show(list(tier_a.values()), 20, name_tags)
        print("\n== B · description-only samples (need an eye) ==")
        show(list(tier_b.values()), 12, lambda v: v["tags"])
    else:
        for cat in ALL:
            print(f"\n== {cat} ==")
            rows = [v for v in out.values() if v["file"] == cat and v["tags"]]
            show(rows, 10 ** 6, lambda v: v["tags"])

    if none:
        bycat = defaultdict(list)
        for e in none:
            bycat[e["file"]].append(e["name"])
        print(f"\n== no proposal ({len(none)}) ==")
        for cat in ALL:
            names = bycat.get(cat, [])
            if names:
                print(f"  {cat} ({len(names)}): {', '.join(names[:16])}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print(f"\nwrote {args.json}")

    if args.apply:
        by_file = defaultdict(list)
        for e in untagged:
            tags, why = proposals_for(e)
            if not args.with_desc:
                tags = {t for t in tags if why.get(t) in ("name", "tree", "manual", "structural")}
            if tags:
                by_file[e["file"]].append((e["number"], sorted(tags)))
        total = 0
        for fname in ALL:
            items = by_file.get(fname)
            if not items:
                continue
            path = os.path.join(oi.GACHA_DIR, fname + ".txt")
            lines = open(path, encoding="utf-8").read().splitlines()
            todo = dict(items)
            cur = None
            for idx, line in enumerate(lines):
                m = gt.HEADER_RE.match(line)
                if m:
                    cur = int(m.group(1)); continue
                if cur in todo and line.strip().startswith("#"):
                    toks, _ = gt.parse_description(line.strip())
                    have = set(gt.parse_tags(toks))
                    lines[idx] = oi.rewrite_line(line, have | set(todo.pop(cur)))
            open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            total += len(items) - len(todo)
            print(f"tagged {fname}: {len(items) - len(todo)} entries")
        print(f"total tagged: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
