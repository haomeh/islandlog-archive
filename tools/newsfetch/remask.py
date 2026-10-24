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
from typing import Dict, Optional

from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.namemask import MASK
from tools.newsfetch.parser import make_snippet, mask_title_collect

_FILTER: Optional[NewsFilter] = None


def _filter() -> NewsFilter:
    global _FILTER
    if _FILTER is None:
        _FILTER = NewsFilter()
    return _FILTER


def remask_item(item: Dict, since: str = "", until: str = "") -> Optional[Dict]:
    """Returns the masked copy of an item, or None when the item must be dropped."""
    day = item.get("published_on", "")
    if since and until and not (since <= day <= until):
        return None
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    if _filter().check_match(title, snippet)[1]:
        return None
    masked_title, names = mask_title_collect(title)
    out = dict(item)
    out["title"] = masked_title
    if not snippet or snippet == title:
        out["snippet"] = make_snippet(masked_title)
    else:
        cleaned = html.unescape(snippet)
        for name in names:
            cleaned = cleaned.replace(name, MASK)
        out["snippet"] = make_snippet(cleaned)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Re-apply the privacy mask to a JSONL file.")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="")
    args = ap.parse_args(argv)
    kept = dropped = changed = 0
    with open(args.src, "r", encoding="utf-8") as fin, open(args.dst, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            item = json.loads(line)
            new = remask_item(item, args.since, args.until)
            if new is None:
                dropped += 1
                continue
            if new["title"] != item.get("title") or new["snippet"] != item.get("snippet"):
                changed += 1
            kept += 1
            fout.write(json.dumps(new, ensure_ascii=False) + "\n")
    print(f"kept={kept} dropped={dropped} changed={changed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
