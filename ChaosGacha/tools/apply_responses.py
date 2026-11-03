#!/usr/bin/env python3
"""Apply responses entered in reports/generated/responses.tsv.

Supported decisions (applied to header lines only, never descriptions):
  Adjust / Change / Raise / Lower / Set value  -> new rarity in proposed_value
  Set source / Resourcerelabel / Source        -> new source in proposed_source
Everything else (Reword, Remove, Merge, Split, Other, questions) is listed in
the preview for manual or agent follow-up.

Usage:
  python3 tools/apply_responses.py            # dry-run: preview only
  python3 tools/apply_responses.py --apply    # write changes to gachafiles

After --apply, run tools/generate_report_site.py to refresh the site.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GACHA_DIR = os.path.join(ROOT, "gachafiles")
RESP = os.path.join(ROOT, "reports", "generated", "responses.tsv")
PREVIEW = os.path.join(ROOT, "reports", "generated", "apply-preview.md")

VALUE_DECISIONS = {"adjust", "change", "raise", "lower", "set value", "set"}
SOURCE_DECISIONS = {"set source", "source", "resourcerelabel"}
KEEP = {"no change", "keep", "keep as is", "", None}

HEADER_RE = re.compile(r"^(\d+)\.\s*(.*),\s*(\d+\.\d+)(?:,\s*(.*))?\s*$")


def load_rows():
    if not os.path.exists(RESP):
        print("responses.tsv not found. Run tools/generate_report_site.py first.")
        sys.exit(1)
    with open(RESP, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh, delimiter="\t")]


def build_changes(rows):
    """Return {file: {entry: change}} where change holds new rarity/source."""
    changes = {}
    manual = []
    for r in rows:
        decision = (r.get("decision") or "").strip().lower()
        if decision in KEEP:
            continue
        file = (r.get("file") or "").strip()
        m = re.match(r"^(\d+)", (r.get("entry") or "").strip())
        if not m:
            continue
        entry = int(m.group(1))
        ch = changes.setdefault(file, {})[entry] = {}
        if decision in VALUE_DECISIONS:
            val = (r.get("proposed_value") or "").strip().replace(",", ".")
            try:
                fval = float(val)
            except ValueError:
                manual.append((file, entry, "bad value", r.get("proposed_value")))
            else:
                if 0.0 <= fval <= 9.9:
                    ch["rarity"] = fval
                else:
                    manual.append((file, entry, "out of range", val))
        elif decision in SOURCE_DECISIONS:
            src = (r.get("proposed_source") or "").strip()
            if src and "," not in src:
                ch["source"] = src
            else:
                manual.append((file, entry, "bad source", src))
        else:
            notes = (r.get("notes") or "").strip()
            manual.append((file, entry, decision, notes))
    return changes, manual


def apply_to_file(file, ch):
    path = os.path.join(GACHA_DIR, file + ".txt")
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    out = []
    applied = 0
    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            num = int(m.group(1))
            if num in ch:
                name, rarity, source = m.group(2).strip(), m.group(3), m.group(4)
                new = ch[num]
                if "rarity" in new:
                    rarity = f"{new['rarity']:.1f}"
                if "source" in new:
                    source = new["source"]
                line = f"{num}. {name}, {rarity}, {source}"
                applied += 1
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes to gachafiles (default: preview only)")
    args = ap.parse_args()

    rows = load_rows()
    changes, manual = build_changes(rows)

    preview = []
    preview.append("# Response apply preview")
    preview.append("")
    if not changes and not manual:
        preview.append("No actionable responses found.")
        print("No actionable responses found.")
    for file, ch in changes.items():
        preview.append(f"## {file}")
        preview.append("")
        preview.append("| Entry | Name | Change |")
        preview.append("|---|---|---|")
        # re-read file headers for names
        path = os.path.join(GACHA_DIR, file + ".txt")
        with open(path, encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                m = HEADER_RE.match(line)
                if m and int(m.group(1)) in ch:
                    num = int(m.group(1))
                    parts = []
                    if "rarity" in ch[num]:
                        parts.append(f"rarity -> {ch[num]['rarity']:.1f}")
                    if "source" in ch[num]:
                        parts.append(f"source -> {ch[num]['source']}")
                    preview.append(f"| {num} | {m.group(2).strip()} | {', '.join(parts)} |")
        preview.append("")
    if manual:
        preview.append("## Needs manual follow-up")
        preview.append("")
        preview.append("| File | Entry | Type | Detail |")
        preview.append("|---|---|---|---|")
        for file, entry, typ, detail in manual:
            preview.append(f"| {file} | {entry} | {typ} | {detail} |")
        preview.append("")

    with open(PREVIEW, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(preview) + "\n")
    print(f"Preview written to {PREVIEW}")

    total = sum(len(c) for c in changes.values())
    print(f"{total} entry updates planned, {len(manual)} manual items.")

    if args.apply:
        for file, ch in changes.items():
            n = apply_to_file(file, ch)
            print(f"{file}: applied {n} header updates")
        print("Run tools/generate_report_site.py to refresh the site.")
    else:
        print("Dry-run only. Re-run with --apply to write changes.")


if __name__ == "__main__":
    sys.exit(main())
