"""Re-applies the privacy mask to a JSONL file of news items.

Usage: python3 -m tools.newsfetch.remask --in a.jsonl --out b.jsonl [--since D --until D]

The tool masks the title and the snippet. A name that the mask removes from the title
is also removed from the snippet. A snippet that equals the title is rebuilt from the
masked title. The tool drops noise items (columns, commentary, life tips) and, when
--since and --until are set, items published outside the window. A second run on the
output changes nothing. Standard library only.
"""

import argparse
import html
import json
import sys
from typing import Dict, Optional, Set

from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.namemask import MASK
from tools.newsfetch.parser import make_snippet, mask_title_collect

_FILTER: Optional[NewsFilter] = None


def _filter() -> NewsFilter:
    global _FILTER
    if _FILTER is None:
        _FILTER = NewsFilter()
    return _FILTER


MIN_PROPAGATE_CHARS = 3


def _replace_names(text: str, names) -> str:
    for name in sorted(names, key=len, reverse=True):
        text = text.replace(name, MASK)
    return text


def collect_names(items) -> Set[str]:
    """Names that the context rules mask in any title. Names of 3 or more characters only."""
    found: Set[str] = set()
    for item in items:
        found.update(n for n in mask_title_collect(item.get("title", ""))[1] if len(n) >= MIN_PROPAGATE_CHARS)
    return found


def remask_item(item: Dict, since: str = "", until: str = "", known_names=()) -> Optional[Dict]:
    """Returns the masked copy of an item, or None when the item must be dropped.

    known_names are names that the rules masked in other titles. The tool removes them here too.
    """
    day = item.get("published_on", "")
    if since and until and not (since <= day <= until):
        return None
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    if _filter().check_match(title, snippet)[1]:
        return None
    masked_title, names = mask_title_collect(title)
    masked_title = _replace_names(masked_title, known_names)
    names = list(names) + list(known_names)
    out = dict(item)
    out["title"] = masked_title
    if not snippet or snippet == title:
        out["snippet"] = make_snippet(masked_title)
    else:
        cleaned = html.unescape(snippet)
        cleaned = _replace_names(cleaned, names)
        out["snippet"] = make_snippet(cleaned)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Re-apply the privacy mask to a JSONL file.")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="")
    args = ap.parse_args(argv)
    with open(args.src, "r", encoding="utf-8") as fin:
        items = [json.loads(line) for line in fin if line.strip()]
    known = collect_names(items)
    kept = dropped = changed = 0
    with open(args.dst, "w", encoding="utf-8") as fout:
        for item in items:
            new = remask_item(item, args.since, args.until, known)
            if new is None:
                dropped += 1
                continue
            if new["title"] != item.get("title") or new["snippet"] != item.get("snippet"):
                changed += 1
            kept += 1
            fout.write(json.dumps(new, ensure_ascii=False) + "\n")
    print(f"kept={kept} dropped={dropped} changed={changed} propagated_names={len(known)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
