# Web apps (static, no server needed)

Two single-purpose pages sharing `css/app.css` (mobile-first layout):

- `tree.html` — Chaos Tree: generate and play multiple named trees.
  The New-tree form covers all generator options (hover any label for an
  explanation); Preview renders the current settings into the 3D view with
  summary stats so parameters can be tuned live before generating.
  Node colour encodes rarity tier (see the legend under the 3D view).
  Play aids: unlockable-now list, bulk ticket awards, node finder, sortable
  owned-nodes table, progress snapshot, first-run guide.
  Progress is saved per tree in `localStorage`; export/import moves a tree
  plus its progress as one JSON file (Python `chaos-tree` JSONs import too).
  Includes a canvas 3D view of visible nodes/connections, an SVG
  neighbour view for the selected node, and a sortable/filterable table
  of owned nodes. Trees are generated in-browser from
  `data/entries.js` (deterministic per seed; seeds are app-local, not
  identical to the Python generator's output for the same seed).
  The Trees tab offers copy (with progress) and fresh-clone (same
  parameters, new progress). Each tree records the data version it was
  generated with; a mismatch warns that regeneration may differ.
  A tree's current view can be shared as a read-only link (`tree.html?share=…`):
  the snapshot uploads to an anonymous paste host and carries only what the
  owner can currently see — never the seed, generation settings, or hidden
  nodes. Loaded under `js/share.js` (snapshot/validation) and `js/paste.js`
  (paste-host adapters).
- `gacha.html` — Chaos Gacha roller with the same presets/odds as the
  desktop app, a ticket wallet (tickets may carry a theme tag or an
  Advantage count that rolls several wheels at once and lets you pick
  which to keep), roll history, spin-wheel animation with adjustable
  slowdown, filters, ×10 multi-pull, result sharing, history stats, and
  history import/export.
- `curse.html` — Curse Roulette port: d20 spin with the original severity
  bands, resolve conditions, per-tier ticket rewards paid into the shared
  wallet, and a resolvable curse history. List source: the original
  site's curse list, vendored under `web/data/curses.txt`.
- `docs.html` — tabbed documentation; the Story Start tab can seed the
  ticket wallet with the CYOA opening tickets.

Serve the `web/` directory over HTTP (e.g. `python3 -m http.server` inside
`web/`) and open `tree.html` / `gacha.html`. `entries.js` is loaded with a
plain `<script>` tag so the pages also work from `file://`.

## Tags

Entries carry the tag taxonomy of the original Chaos Gacha index
(`chaosgacha.com`, by BronzDeck), vendored under `tools/tagdata/` and written
into `gachafiles/*.txt` as `(Tag:…)` tokens by
`tools/import_official_tags.py` (`tools/fetch_official_tags.py` refreshes the
snapshot). The per-category dictionaries are exported to `data/tags.js` so tag
pills can explain themselves on hover. Tag names are lowercase with `+` kept
significant (`fire` vs `fire+`).

## Refreshing the data bundle

After editing `gachafiles/*.txt`:

    python3 tools/export_web_data.py

## Deploys and caching

`sw.js` precaches the app shell and serves it cache-first, but serves
generated data (`data/*.js`) **network-first** — so a fresh export is picked up
on the next reload without touching the worker. Bump the `CACHE` version in
`sw.js` whenever shell files (html/css/js/icons) change, otherwise returning
players keep the old shell.

## Tests

- `node tools/web_parity.cjs` — checks the JS engine against the Python
  engine (visibility, costs, meta derive, jump order, echo) and that the
  JS generator is deterministic and connected.
- `node tools/web_tags_test.cjs` — boots the real pages in jsdom (needs
  `npm install --no-save jsdom`) and drives the tag UI: entries chips,
  tag search, pill tooltips, the gacha tag filter, tagged tickets, the
  no-match error path, and the tree tag pickers.
- `python3 tools/test_chaos_tree.py` — generator/engine self-test, plus tag
  parsing/normalization invariants (`test_tags`).
- `node tools/sw_behavior_test.cjs` — checks the service worker's caching
  rules: data bundles are revalidated against the network (with an offline
  fallback), the shell stays cache-first, and `data/tags.js` is precached.
- The app shells boot headlessly under the DOM stub used during
  development (not committed); rerun `node --check web/js/*.js` after edits.
