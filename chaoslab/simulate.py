"""Reproduce the gacha and curse rollers over the snapshotted data.

The gacha path mirrors ``Gacha.py`` / ``web/js/gacha.js``: draw a target
rarity from the preset window with weight ``1/4**|avg - rarity|``, then pick
among entries within +/-0.2 of it. Flat (wild) tickets widen that window to
+/-1.0 and drop the exponent to 1. The curse path mirrors the roulette: a d20
sets the severity tier, then a curse carrying that roll is chosen (falling
back to the nearest severity when a bucket is empty).
"""

from __future__ import annotations

import bisect
import random
from collections import Counter
from pathlib import Path

from . import curses as curses_mod
from .fetch import FetchError
from .util import TIER_NAMES, read_jsonl, tier_for

CATEGORIES = ("ability", "familiar", "item", "skill", "trait")

# (minimum, average, maximum, flat) mirrored from Gacha.py presets and the
# web exporter's extended ticket list (trash/aluminium/wild/transcendent).
PRESETS = {
    "trash": (0.1, 0.5, 1.5, False),
    "bronze": (0.1, 1.3, 3.3, False),
    "silver": (0.5, 2.3, 4.3, False),
    "gold": (1.5, 3.3, 5.3, False),
    "aluminium": (1.0, 4.0, 6.0, False),
    "platinum": (2.5, 4.3, 6.3, False),
    "diamond": (3.5, 5.3, 7.3, False),
    "legendary": (4.5, 6.3, 8.3, False),
    "mythical": (5.5, 7.3, 9.3, False),
    "wild": (1.0, 5.0, 10.0, True),
    "divine": (6.5, 8.3, 10.0, False),
    "transcendent": (7.5, 9.3, 10.0, False),
}

CURSE_TIERS = ("Minor", "Medium", "Major", "Severe", "Ultimate")
CURSE_REWARDS = {
    "Minor": "gold random",
    "Medium": "gold random (2x Advantage)",
    "Major": "gold choice",
    "Severe": "platinum random",
    "Ultimate": "platinum choice",
}


def _build_pool(entries: list[dict]) -> dict[str, tuple[list[float], list[dict]]]:
    pool: dict[str, tuple[list[float], list[dict]]] = {}
    for category in CATEGORIES:
        rows = sorted(
            (entry for entry in entries if entry.get("category") == category),
            key=lambda entry: float(entry.get("rarity") or 0.0),
        )
        pool[category] = ([float(entry.get("rarity") or 0.0) for entry in rows], rows)
    missing = [category for category, (rarities, _) in pool.items() if not rarities]
    if missing:
        raise FetchError(
            f"corpus has no entries for: {', '.join(missing)}; run `chaoslab parse` first"
        )
    return pool


def _rarity_pull(
    rng: random.Random, minimum: float, average: float, maximum: float, flat: bool
) -> float:
    """Weighted draw over the 0.1 rarity grid, exactly as Gacha.py builds it."""
    exponent = 1 if flat else 4
    values: list[float] = []
    weights: list[float] = []
    x = float(minimum)
    while x < float(maximum):
        values.append(x)
        weights.append(1.0 / (exponent ** abs(average - x)))
        x += 0.1
    if not values:
        raise ValueError(f"empty rarity window {minimum}..{maximum}")
    return rng.choices(values, weights=weights, k=1)[0] + 0.1


def _draw(
    pool: dict[str, tuple[list[float], list[dict]]],
    rng: random.Random,
    minimum: float,
    average: float,
    maximum: float,
    flat: bool,
) -> dict:
    exponent = 1 if flat else 4
    window = 1.0 if flat else 0.2
    # Upstream picks the category once per pull, then retries rarity draws
    # inside it; a new category is only chosen if that one cannot resolve.
    for _ in range(len(CATEGORIES) * 2):
        category = rng.choice(CATEGORIES)
        rarities, rows = pool[category]
        for _ in range(200):
            pull = _rarity_pull(rng, minimum, average, maximum, flat)
            lo = bisect.bisect_left(rarities, pull - window)
            hi = bisect.bisect_right(rarities, pull + window)
            candidates = rows[lo:hi]
            if not candidates:
                continue
            weights = [
                1.0 / (exponent ** abs(average - float(entry.get("rarity") or 0.0)))
                for entry in candidates
            ]
            return rng.choices(candidates, weights=weights, k=1)[0]
    raise ValueError("no entry matched the preset after 200 attempts; widen the rarity window")


def _run_gacha(root: Path, preset: str, draws: int, seed: int) -> dict:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; choose from {', '.join(sorted(PRESETS))}")
    corpus_path = Path(root) / "data" / "corpus.jsonl"
    entries = [entry for entry in read_jsonl(corpus_path) if not entry.get("excluded")]
    if not entries:
        raise FileNotFoundError(f"no parsed corpus at {corpus_path}; run `chaoslab parse` first")
    pool = _build_pool(entries)
    minimum, average, maximum, flat = PRESETS[preset]
    rng = random.Random(seed)
    counts = {name: 0 for name in TIER_NAMES}
    total_rarity = 0.0
    for _ in range(draws):
        entry = _draw(pool, rng, minimum, average, maximum, flat)
        rarity = float(entry.get("rarity") or 0.0)
        counts[tier_for(rarity)] += 1
        total_rarity += rarity
    return {
        "roller": "gacha",
        "preset": preset,
        "draws": draws,
        "seed": seed,
        "average_rarity": total_rarity / draws,
        "tiers": {name: counts[name] / draws for name in TIER_NAMES},
    }


def _curse_pool(root: Path) -> list[dict]:
    source = curses_mod.find_source(Path(root))
    parsed = curses_mod.parse_text(source.read_text(encoding="utf-8"))
    # The roulette hides mature curses by default; keep simulate consistent.
    pool = [curse for curse in parsed if not curse.get("nsfw")]
    if not pool:
        raise FetchError("curse list is empty after hiding mature entries")
    return pool


def _pick_curse(rng: random.Random, pool: list[dict], roll: int) -> dict:
    candidates = [curse for curse in pool if curse["severity"] == roll]
    if not candidates:
        nearest = min(abs(curse["severity"] - roll) for curse in pool)
        candidates = [curse for curse in pool if abs(curse["severity"] - roll) == nearest]
    return rng.choice(candidates)


def _run_curses(root: Path, draws: int, seed: int) -> dict:
    pool = _curse_pool(root)
    rng = random.Random(seed)
    counts = {name: 0 for name in CURSE_TIERS}
    rewards = {CURSE_REWARDS[name]: 0 for name in CURSE_TIERS}
    for _ in range(draws):
        roll = rng.randint(1, 20)
        tier = curses_mod.tier_of(roll)
        _pick_curse(rng, pool, roll)
        counts[tier] += 1
        rewards[CURSE_REWARDS[tier]] += 1
    return {
        "roller": "curses",
        "preset": None,
        "draws": draws,
        "seed": seed,
        "curses": len(pool),
        "tiers": {name: counts[name] / draws for name in CURSE_TIERS},
        "rewards": rewards,
    }


def run(
    root: Path,
    roller: str = "gacha",
    preset: str = "gold",
    draws: int = 100000,
    seed: int = 1,
) -> dict:
    if draws <= 0:
        raise ValueError("draws must be a positive integer")
    if roller == "gacha":
        return _run_gacha(root, preset, draws, seed)
    if roller == "curses":
        return _run_curses(root, draws, seed)
    raise ValueError(f"unknown roller {roller!r}; choose gacha or curses")
