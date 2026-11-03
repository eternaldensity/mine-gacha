# reports/generated

This directory is **script-generated**. Do not edit it by hand — run
`python3 tools/generate_report_site.py` after any change to `gachafiles/*.txt`
or the reports in `reports/`. Re-running merges and preserves any responses
you entered in `responses.tsv`.

## Consuming

- GitHub renders `.md` files natively, and the entry links work there.
  Start at `index.md`.
- Report pages link every entry name to its reference page
  (`entries/<file>.md#<anchor>`), with rarity/tier/source shown right in the
  link text, so you no longer need to guess what the numbers refer to.
- Locally, open the same files in any Markdown editor. The `#anchor` in the
  link text tells you which section to jump to even when links don't render.

## Responding

1. Open `responses.tsv` in a spreadsheet (LibreOffice, Excel, Google Sheets)
   or a plain-text editor.
2. For each row you care about, fill:
   - `decision`: `No change` / `Adjust` / `Set source` / `Reword` / `Remove`
     / `Other`
   - `proposed_value`: new rarity (0.1–9.9) when adjusting
   - `proposed_source`: new source label when setting a source
   - `notes`: anything else (reword text, merge/split intent, questions)
3. Preview: `python3 tools/apply_responses.py` (dry-run, writes
   `apply-preview.md`).
4. Apply: `python3 tools/apply_responses.py --apply` (modifies the gacha
   files' header lines only).
5. Refresh: `python3 tools/generate_report_site.py` to rebuild pages,
   linked reports, and the index with your answers preserved.

## HTML (optional)

`python3 tools/generate_report_site.py --html` writes HTML copies of the
linked reports under `reports/generated/html/` for local browsing. Requires
the `markdown` package (`pip install markdown`). GitHub renders the `.md`
files natively, so this is only for offline convenience.
