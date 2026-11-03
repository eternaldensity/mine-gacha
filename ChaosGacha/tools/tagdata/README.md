# Official tag data (vendored snapshot)

These files mirror the tag taxonomy published by the **original Chaos Gacha
site** (`chaosgacha.com`, by BronzDeck). The GitHub repo we forked only ships
the entry text; the site additionally publishes per-category tag dictionaries
and per-entry tags, which we import here so the web apps can filter like the
original index page does.

## Files

- `dicts.json` — the five per-category tag dictionaries, straight from
  `https://www.chaosgacha.com/<category>_tags.txt`:
  `{"ability": [{"name": "Fire", "desc": "An ability that utilizes the power of Fire or Heat"}, ...], ...}`
- `entry_tags.json` — per-entry tags parsed from
  `https://www.chaosgacha.com/gachalist.txt`:
  `[["ability", "Hellflames", ["Fire"]], ...]`

## Provenance / regeneration

Snapshot taken **2026-10-18** from the URLs above. Re-fetch with:

    python3 tools/fetch_official_tags.py

Parsing notes (why the snapshot is not a verbatim copy of `gachalist.txt`):

- `gachalist.txt` encodes tags as leading `|Tag|` slots followed by the
  description, e.g. `|Fire|My Hero Academia - Allows the user ...`. Slots are
  kept only when they match the category's dictionary (case-insensitively),
  otherwise the source text would be misread as a tag. The site's own file has
  two malformed lines where a source sentence ended up in a tag slot; both are
  dropped here.
- A few tags are used on entries but missing from the dictionaries
  (`Large Size` (cased `Large size` in the dictionary), `Mechanical`,
  `Machine`, `Passive`, `Anti Draconic`, `Instance Familiar`). They are kept.
- Entries are merged by `(category, name)`; the one duplicate
  (`ability: Explosion`) has its tags unioned.

Attribution: tags and dictionary text are BronzDeck's; see the site footer and
repo README. Entry text in `gachafiles/` already carries the same attribution.
