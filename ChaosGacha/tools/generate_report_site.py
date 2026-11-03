#!/usr/bin/env python3
"""Generate a navigable report site from the gacha files and reports.

Output (all under reports/generated/):
  entries/<file>.md          one page per gacha file, one section per entry (anchored)
  index.md                   top-level navigation
  <file>-clarity-report.md   copies of the 8 reports with linked entry names
  <file>-scaling-report.md     (rarity/tier/source shown inline in each link)
  responses.tsv              response workbook (existing answers are preserved/merged)
  README.md                  usage + workflow

Usage:
  python3 tools/generate_report_site.py [--html]

  --html also writes self-contained HTML copies of the linked reports
  (requires the optional 'markdown' package; GitHub renders the .md files
  natively, so HTML is only for local convenience).
"""
import argparse
import csv
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GACHA_DIR = os.path.join(ROOT, "gachafiles")
REPORT_DIR = os.path.join(ROOT, "reports")
OUT = os.path.join(REPORT_DIR, "generated")
ENTRIES_OUT = os.path.join(OUT, "entries")

FILES = ["skill", "trait", "familiar", "item", "ability"]
REPORTS = [f"{f}-clarity-report.md" for f in FILES] + \
          [f"{f}-scaling-report.md" for f in FILES]

TIERS = [
    (0.0, 1.0, "Trash"), (1.0, 2.0, "Common"), (2.0, 3.0, "Uncommon"),
    (3.0, 4.0, "Rare"), (4.0, 5.0, "Elite"), (5.0, 6.0, "Epic"),
    (6.0, 7.0, "Legendary"), (7.0, 8.0, "Mythical"), (8.0, 9.0, "Divine"),
    (9.0, 10.0, "Transcendent"),
]


def tier(rarity: float) -> str:
    for lo, hi, name in TIERS:
        if lo <= rarity < hi:
            return name
    return "Transcendent"


def slugify(text: str) -> str:
    """GitHub-style heading slug: lowercase, drop punctuation, spaces->-."""
    out = []
    for ch in text.lower():
        if ch.isalnum() or ch in "_-":
            out.append(ch)
        elif ch == " ":
            out.append("-")
    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    return slug


def load_entries(file: str):
    """Return {key: entry} where key is int, or 'N-2' for duplicate numbers."""
    entries = {}
    path = os.path.join(GACHA_DIR, file + ".txt")
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    seen = {}
    cur = None
    desc = []
    for line in lines:
        m = re.match(r"^(\d+)\.\s*(.*),\s*(\d+\.\d+)(?:,\s*(.*))?\s*$", line)
        if m:
            if cur is not None:
                cur["description"] = _clean_desc(desc)
            num = int(m.group(1))
            occ = seen.get(num, 0) + 1
            seen[num] = occ
            key = num if occ == 1 else f"{num}-{occ}"
            cur = {
                "num": num,
                "occ": occ,
                "key": key,
                "name": m.group(2).strip(),
                "rarity": float(m.group(3)),
                "source": (m.group(4) or "").strip(),
            }
            desc = []
            entries[key] = cur
        else:
            desc.append(line)
    if cur is not None:
        cur["description"] = _clean_desc(desc)
    return entries


def _clean_desc(lines):
    text = " ".join(l.strip() for l in lines if l.strip())
    text = text.strip()
    text = re.sub(r"^#+", "", text).strip()
    return text


def anchor(entry) -> str:
    if entry.get("occ", 1) > 1:
        return f"{entry['num']}-{entry['occ']}-{slugify(entry['name'])}"
    return f"{entry['num']}-{slugify(entry['name'])}"


def entry_link(entry, relative_to_entries_root=True) -> str:
    """Relative markdown link to the entry's anchor."""
    return f"entries/{entry_file_of(entry)}.md#{anchor(entry)}"


def entry_file_of(entry) -> str:
    return entry["_file"]


def fmt_entry(entry, link=True) -> str:
    base = f"{entry['num']}. {entry['name']}"
    if not link:
        return base
    return f"[{base}](entries/{entry['_file']}.md#{anchor(entry)}) — {entry['rarity']:.1f} {tier(entry['rarity'])} ({entry['source'] or 'Generic'})"


# ----------------------------------------------------------------------------
# Entry pages (one page per gacha file, anchored sections)
# ----------------------------------------------------------------------------

def build_entries_pages(entries_by_file):
    os.makedirs(ENTRIES_OUT, exist_ok=True)
    for file, entries in entries_by_file.items():
        ordered = sorted(entries.values(), key=lambda e: (e["num"], e["occ"]))
        # tier groups for a mini navigation
        groups = {}
        for e in ordered:
            groups.setdefault(tier(e["rarity"]), []).append(e)
        lines = []
        lines.append(f"# {file} — Entry Reference")
        lines.append("")
        lines.append(f"{len(ordered)} entries. Sorted by rarity, then number.")
        lines.append("")
        lines.append("| Tier | Count |")
        lines.append("|---|---|")
        for t in TIERS:
            name = t[2]
            n = len(groups.get(name, []))
            if n:
                lines.append(f"| {name} | {n} |")
        lines.append("")
        lines.append("## Index by tier")
        lines.append("")
        for name, tup in [(t[2], t) for t in TIERS]:
            grp = groups.get(name, [])
            if not grp:
                continue
            lines.append(f"### {name} ({len(grp)})")
            lines.append("")
            lines.append("| # | Name | Rarity | Source |")
            lines.append("|---|---|---|---|")
            for e in sorted(grp, key=lambda x: x["rarity"]):
                lines.append(
                    f"| {e['num']} | [{e['name']}](#{anchor(e)}) | "
                    f"{e['rarity']:.1f} | {e['source'] or 'Generic'} |"
                )
            lines.append("")
        # full detail sections
        lines.append("## Entries")
        lines.append("")
        for e in ordered:
            lines.append(f"## {e['num']}. {e['name']}")
            lines.append("")
            lines.append(f"| Rarity | Tier | Source |")
            lines.append(f"|---|---|---|")
            lines.append(
                f"| {e['rarity']:.1f} | {tier(e['rarity'])} | "
                f"{e['source'] or 'Generic'} |"
            )
            lines.append("")
            lines.append("**Description**")
            lines.append("")
            for para in e["description"].split("\n"):
                lines.append(f"> {para}" if para.strip() else ">")
            lines.append("")
            refs = e.get("_refs", [])
            if refs:
                lines.append("**Flagged in reports**")
                lines.append("")
                for ref in refs:
                    lines.append(f"- {ref}")
                lines.append("")
            lines.append("**Decision**")
            lines.append("")
            lines.append("- [ ] No change")
            lines.append("- [ ] Adjust rarity  (see **Proposed value** in responses.tsv)")
            lines.append("- [ ] Set source     (see **Proposed source** in responses.tsv)")
            lines.append("- [ ] Reword / Remove / Other (see **Notes** in responses.tsv)")
            lines.append("")
        path = os.path.join(ENTRIES_OUT, f"{file}.md")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------
# Report linkification
# ----------------------------------------------------------------------------

NAME_RE = re.compile(r"\b(\d{1,4})\.")
CELL_RE = re.compile(r"(\|\s*)(\d{1,4})(\s*\|)")
SEVERITY_RE = re.compile(r"(BLOCKER|MAJOR|MINOR|blocker|major|minor)")


def _next_char_ok(line, idx):
    if idx >= len(line):
        return True
    c = line[idx]
    return not (c.isalnum() or c in "._-") or c in " "


def linkify_report(text: str, file: str, entries) -> tuple[str, dict, dict]:
    """Return (linked_text, flags_by_entry, refs_by_entry)."""
    flags = {}
    refs = {}
    out_lines = []
    for line in text.splitlines():
        new_line = ""
        pos = 0
        for m in NAME_RE.finditer(line):
            num = int(m.group(1))
            entry = entries.get(num)
            if entry is None:
                continue
            # anchored name match: text after 'N. ' must equal the entry name
            cand = m.end()
            if cand < len(line) and line[cand] == " ":
                cand += 1
            else:
                continue
            name = entry["name"]
            if line[cand:cand + len(name)] != name:
                continue
            if not _next_char_ok(line, cand + len(name)):
                continue
            if pos <= m.start() and "](" in new_line[-6:]:
                continue
            new_line += line[pos:m.start()]
            new_line += fmt_entry(entry)
            pos = cand + len(name)
            sev = SEVERITY_RE.search(line[cand + len(name):cand + len(name) + 60])
            flags.setdefault(num, set()).add(sev.group(1).upper() if sev else "REF")
            refs.setdefault(num, []).append(line.strip()[:180])
        new_line += line[pos:]
        new_line = CELL_RE.sub(
            lambda mm: f"{mm.group(1)}[{mm.group(2)}](entries/{file}.md"
            f"#{entries.get(int(mm.group(2)), {}).get('num', 0)}-"
            f"{slugify(entries.get(int(mm.group(2)), {}).get('name', ''))})"
            f"{mm.group(3)}" if int(mm.group(2)) in entries else mm.group(0),
            new_line,
        )
        out_lines.append(new_line)
    return "\n".join(out_lines), flags, refs


def build_linked_reports(entries_by_file, linked):
    for report in REPORTS:
        m = re.match(r"^(.+)-(clarity|scaling)-report\.md$", report)
        file = m.group(1)
        header = (f"# {file} {m.group(2)} report (linked)\n\n"
                  f"Auto-generated from `{report}`. Entry names link to "
                  f"[entries/{file}.md](entries/{file}.md). Responses: "
                  f"[responses.tsv](responses.tsv).\n\n---\n\n")
        path = os.path.join(OUT, report)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(header + linked[report] + "\n")


# ----------------------------------------------------------------------------
# Index + README + responses
# ----------------------------------------------------------------------------

def linkify_reports(entries_by_file):
    """Link every report; attach flags + refs to entries; return linked texts."""
    linked = {}
    refs_by_file = {}
    for report in REPORTS:
        m = re.match(r"^(.+)-(clarity|scaling)-report\.md$", report)
        file = m.group(1)
        src = os.path.join(REPORT_DIR, report)
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
        linked[report], flags, refs = linkify_report(text, file,
                                                     entries_by_file[file])
        for num, sevs in flags.items():
            e = entries_by_file[file].get(num)
            if e is not None:
                e.setdefault("_flags", set()).update(sevs)
        for num, lines in refs.items():
            e = entries_by_file[file].get(num)
            if e is not None:
                e.setdefault("_refs", []).extend(
                    f"[{m.group(2)}] {l}" for l in lines)
    return linked, refs_by_file


def build_index(entries_by_file):
    lines = []
    lines.append("# Chaos Gacha — Report Site")
    lines.append("")
    lines.append("Navigable view of the gacha data and the review reports.")
    lines.append("")
    lines.append("## Browse the data")
    lines.append("")
    lines.append("| File | Entries | Page |")
    lines.append("|---|---|---|")
    for file in FILES:
        n = len(entries_by_file[file])
        lines.append(f"| {file} | {n} | [entries/{file}.md](entries/{file}.md) |")
    lines.append("")
    lines.append("## Reports")
    lines.append("")
    lines.append("| Report | Linked copy |")
    lines.append("|---|---|")
    for report in REPORTS:
        lines.append(f"| {report} | [{report}]({report}) |")
    lines.append("")
    lines.append("## Respond")
    lines.append("")
    lines.append("Open [responses.tsv](responses.tsv) in a spreadsheet or "
                 "editor and fill the Decision / Proposed value / Proposed "
                 "source / Notes columns. Then run "
                 "`python3 tools/apply_responses.py`.")
    lines.append("")
    path = os.path.join(OUT, "index.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def build_responses(entries_by_file, merged):
    rows = []
    for file in FILES:
        for e in sorted(entries_by_file[file].values(),
                        key=lambda x: (x["num"], x["occ"])):
            key = (file, e["num"])
            old = merged.get(key, {})
            flags = " ".join(sorted(e.get("_flags", [])))
            entry_label = str(e["num"]) if e["occ"] == 1 else f"{e['num']} (2)"
            rows.append({
                "file": file,
                "entry": entry_label,
                "name": e["name"],
                "rarity": f"{e['rarity']:.1f}",
                "tier": tier(e["rarity"]),
                "source": e["source"] or "Generic",
                "flags": flags,
                "decision": old.get("decision", ""),
                "proposed_value": old.get("proposed_value", ""),
                "proposed_source": old.get("proposed_source", ""),
                "notes": old.get("notes", ""),
            })
    cols = ["file", "entry", "name", "rarity", "tier", "source", "flags",
            "decision", "proposed_value", "proposed_source", "notes"]
    path = os.path.join(OUT, "responses.tsv")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t",
                           lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def read_existing_responses():
    path = os.path.join(OUT, "responses.tsv")
    merged = {}
    if not os.path.exists(path):
        return merged
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            entry_raw = (row.get("entry") or "").strip()
            m = re.match(r"^(\d+)", entry_raw)
            if not m:
                continue
            key = (row.get("file", "").strip(), int(m.group(1)))
            merged[key] = {
                "decision": row.get("decision", "").strip(),
                "proposed_value": row.get("proposed_value", "").strip(),
                "proposed_source": row.get("proposed_source", "").strip(),
                "notes": row.get("notes", "").strip(),
            }
    return merged


README = """# reports/generated

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
"""


def build_html():
    try:
        import markdown  # type: ignore
    except ImportError:
        print("--html requested but 'markdown' is not installed. "
              "Skipping HTML. (pip install markdown)")
        return
    html_dir = os.path.join(OUT, "html")
    os.makedirs(html_dir, exist_ok=True)
    for report in REPORTS:
        src = os.path.join(OUT, report)
        with open(src, encoding="utf-8") as fh:
            body = markdown.markdown(fh.read(), extensions=["tables", "fenced_code"])
        page = ("<!doctype html><html><head><meta charset='utf-8'>"
                f"<title>{report}</title><style>body{{max-width:960px;margin:2em "
                "auto;font:16px/1.5 system-ui;}}table{border-collapse:collapse;}"
                "th,td{border:1px solid #ccc;padding:4px 8px;}}</style></head>"
                f"<body><h1><a href='index.html'>← index</a></h1>{body}</body></html>")
        with open(os.path.join(html_dir, report.replace(".md", ".html")),
                  "w", encoding="utf-8") as fh:
            fh.write(page)
    idx = ["<!doctype html><html><head><meta charset='utf-8'><title>Reports</title>"
           "</head><body><h1>Report Site</h1><ul>"]
    for report in REPORTS:
        idx.append(f"<li><a href='{report.replace('.md', '.html')}'>{report}</a></li>")
    idx.append("</ul></body></html>")
    with open(os.path.join(html_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(idx))
    print("HTML written under reports/generated/html/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true", help="also emit HTML copies")
    args = ap.parse_args()

    os.makedirs(ENTRIES_OUT, exist_ok=True)
    entries_by_file = {}
    for file in FILES:
        entries = load_entries(file)
        for e in entries.values():
            e["_file"] = file
        entries_by_file[file] = entries
        print(f"{file}: {len(entries)} entries")

    linked, _ = linkify_reports(entries_by_file)
    build_entries_pages(entries_by_file)
    build_linked_reports(entries_by_file, linked)
    build_index(entries_by_file)
    merged = read_existing_responses()
    n = build_responses(entries_by_file, merged)
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(README)
    print(f"responses.tsv: {n} rows (preserved {len(merged)} existing answers)")
    if args.html:
        build_html()
    print("Done. Start at reports/generated/index.md")


if __name__ == "__main__":
    sys.exit(main())
