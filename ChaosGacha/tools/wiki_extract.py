#!/usr/bin/env python3
"""Fetch a MediaWiki page (Fandom, Wikipedia, Paradox wikis, ...) as clean
markdown for gacha-entry research.

The MediaWiki API returns raw wikitext without any site skin/JS, which this
tool converts to readable markdown (infobox facts, sections, lists).

Usage:
    python3 tools/wiki_extract.py palworld.fandom.com Lamball
    python3 tools/wiki_extract.py --wiki https://stellaris.paradoxwikis.com/api.php \\
        --page Psionic --chars 4000 --out /tmp/opencode/psionic.md
    python3 tools/wiki_extract.py palworld.fandom.com --search "fire pal"

Output goes to stdout unless --out is given.
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "ChaosGacha-research/1.0 (gacha entry research)"}


def api_get(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SystemExit(
            f"error: {base} did not return API data (some wikis, e.g. "
            f"Paradox wikis, block scripted access). Research those in a "
            f"browser instead.")


def resolve_api(wiki):
    wiki = wiki.strip()
    if "api.php" in wiki:
        return wiki if wiki.startswith("http") else "https://" + wiki
    wiki = wiki.replace("https://", "").replace("http://", "").rstrip("/")
    return f"https://{wiki}/api.php"


def fetch_wikitext(base, title):
    data = api_get(base, {"action": "parse", "page": title, "prop": "wikitext",
                          "redirects": 1, "format": "json"})
    if "error" in data:
        raise SystemExit(f"API error: {data['error'].get('info', data['error'])}")
    return data["parse"]["title"], data["parse"]["wikitext"]["*"]


def search_titles(base, query, limit=10):
    data = api_get(base, {"action": "query", "list": "search",
                          "srsearch": query, "srlimit": limit, "format": "json"})
    return [r["title"] for r in data.get("query", {}).get("search", [])]


def strip_markup(s):
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S | re.I)
    s = re.sub(r"<ref[^>]*/>", "", s, flags=re.I)
    s = re.sub(r"\{\{[^\{\}]*\}\}", "", s)  # simple templates
    s = re.sub(r"\[\[([^|\]]*)\|([^\]]*)\]\]", r"\2", s)  # [[a|b]] -> b
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)  # [[a]] -> a
    s = re.sub(r"\[https?://[^\s\]]+\s+([^\]]*)\]", r"\1", s)  # [url text]
    s = re.sub(r"\[https?://[^\s\]]+\]", "", s)
    s = re.sub(r"'''''(.+?)'''''", r"***\1***", s)
    s = re.sub(r"'''(.+?)'''", r"**\1**", s)
    s = re.sub(r"''(.+?)''", r"*\1*", s)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</?(div|span|small|sup|sub|center)[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return s.strip()


def top_blocks(wt):
    """Yield each top-level {{...}} block."""
    i, n = 0, len(wt)
    while i < n - 1:
        m = re.search(r"\{\{", wt[i:])
        if not m:
            return
        i += m.start()
        depth, start = 0, i
        while i < n - 1:
            if wt[i:i + 2] == "{{":
                depth += 1
                i += 2
            elif wt[i:i + 2] == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    break
            else:
                i += 1
        yield wt[start:i]


def block_facts(box):
    facts = []
    for line in box.split("\n"):
        mm = re.match(r"\|\s*([^=|<>]+?)\s*=\s*(.+)", line.strip())
        if mm:
            k, v = mm.group(1).strip(), strip_markup(mm.group(2).strip())
            v = re.sub(r"\s+", " ", v)
            if k.lower() not in ("image", "caption") and v and len(v) < 300:
                facts.append((k, v))
    return facts


def extract_infobox(wt):
    """Pull | key = value pairs from the richest template block
    (usually the infobox, whatever its name)."""
    best = []
    for box in top_blocks(wt):
        facts = block_facts(box)
        if len(facts) > len(best):
            best = facts
    return best[:25]


def drop_templates(wt):
    """Remove all balanced {{...}} blocks (infoboxes, navboxes, ...)."""
    for _ in range(50):
        new = re.sub(r"\{\{[^{}]*\}\}", "", wt)
        if new == wt:
            break
        wt = new
    return wt


def to_markdown(title, wt, chars):
    facts = extract_infobox(wt)
    wt = drop_templates(wt)
    # drop tables, files/categories
    wt = re.sub(r"\{\|.*?\|\}", "", wt, flags=re.S)
    wt = re.sub(r"\[\[(File|Image|Category):[^\]]*\]\]", "", wt)
    out = [f"# {title}", ""]
    if facts:
        out.append("## Facts")
        out += [f"- **{k}:** {v}" for k, v in facts]
        out.append("")
    for line in wt.split("\n"):
        s = line.strip()
        if not s or s.startswith("__") or re.match(r"\{\{.*\}\}$", s):
            continue
        m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", s)
        if m:
            lvl = min(4, len(m.group(1)))
            out.append("#" * lvl + " " + strip_markup(m.group(2)))
            continue
        if s[0] in ("*", "#", ":", ";"):
            out.append(s[0] + " " + strip_markup(s.lstrip("*#:; ")))
            continue
        out.append(strip_markup(s))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    if len(text) > chars:
        text = text[:chars].rsplit("\n", 1)[0] + "\n\n…(truncated)"
    return text + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wiki", help="wiki host (e.g. palworld.fandom.com) or api.php URL")
    ap.add_argument("page", nargs="?", help="page title to fetch")
    ap.add_argument("--wiki-base", dest="wiki_base", default=None)
    ap.add_argument("--search", default=None, help="search titles instead of fetching")
    ap.add_argument("--chars", type=int, default=6000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    base = resolve_api(args.wiki_base or args.wiki)
    if args.search or not args.page:
        for t in search_titles(base, args.search or args.page or ""):
            print(t)
        return 0
    title, wt = fetch_wikitext(base, args.page)
    md = to_markdown(title, wt, args.chars)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"wrote {args.out} ({len(md)} chars)")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
