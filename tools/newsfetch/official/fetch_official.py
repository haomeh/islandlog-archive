#!/usr/bin/env python3
"""Collect metadata of official statements and public records (grade A or B).

Usage:
    python3 tools/newsfetch/official/fetch_official.py --since 2026-04-24 --until 2026-10-24 \
        --out tools/newsfetch/official/out/official.jsonl [--source ey]

Reads sources.json. Keeps URL, title, date, publisher and a snippet of 150 characters or fewer.
"""

import argparse
import datetime
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import classify  # noqa: E402
import listing  # noqa: E402
import textutil  # noqa: E402
from crawler import PoliteCrawler  # noqa: E402

DEFAULT_OUT = HERE / "out" / "official.jsonl"
DEFAULT_SOURCES = HERE / "sources.json"

RECORD_RE = re.compile(r"判決|裁定|裁判書|憲法判決|公報|會議紀錄|議事錄|議事日程|會議記錄|解釋文")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("official")


def assign_source_class(source: Dict, title: str) -> str:
    """official_record for judgments, gazettes and minutes; else the source default."""
    if source.get("source_class") == "official_record" or RECORD_RE.search(title or ""):
        return "official_record"
    return "official_statement"


ROUTINE_WORDS = ("活動", "開幕", "表揚", "補助", "招募", "比賽", "市集", "展覽", "報名", "慶典")


def is_routine(title: str) -> bool:
    """A title with a routine word (event, award, subsidy, contest) is routine."""
    return any(w in title for w in ROUTINE_WORDS)


def build_record(source: Dict, item: Dict, fetched_on: str, lex: Dict, feed: Dict) -> Dict:
    """Build one output record. Title and snippet pass the privacy mask and victim redaction."""
    raw_title = item["title"]
    summary = item.get("summary") or ""
    flags = classify.classify(raw_title, summary, lex, force_clarification=bool(feed.get("clarification")))
    title = textutil.redact_victim(textutil.mask_title(raw_title)).strip()
    # Title-only snippet: requested by the feed (fact-check bodies) or needed for a sensitive item.
    use_title = feed.get("snippet") == "title" or flags["sensitive"] or not summary
    rec = {
        "url": item["url"],
        "title": title,
        "publisher": source["publisher"],
        "published_on": item["published_on"],
        "snippet": textutil.make_snippet(raw_title if use_title else summary),
        "fetched_on": fetched_on,
        **flags,
        "source_class": "fact_check" if source.get("source_class") == "fact_check"
        else assign_source_class({**source, **{k: v for k, v in feed.items() if k == "source_class"}}, raw_title),
    }
    if rec["source_class"] != "fact_check":
        rec["routine"] = is_routine(raw_title)
    return rec


def fetch_feed(feed: Dict, crawler: PoliteCrawler, since: str) -> List[Dict]:
    """Fetch one feed definition. Return raw items (all dates)."""
    kind = feed["type"]
    if kind == "rss":
        if "{page}" not in feed["url"] and "{start_index}" not in feed["url"]:
            data = crawler.fetch_raw(feed["url"])
            return listing.parse_rss(data) if data else []
        items = []
        seen_first = None
        for page in range(1, feed.get("max_pages", 60) + 1):
            # start_index is for Blogger feeds, page for WordPress feeds.
            url = feed["url"].format(page=page, start_index=1 + (page - 1) * feed.get("page_size", 100))
            data = crawler.fetch_raw(url)
            page_items = listing.parse_rss(data) if data else []
            if not page_items or page_items[0]["url"] == seen_first:
                break
            seen_first = page_items[0]["url"]
            items.extend(page_items)
            if min(i["published_on"] for i in page_items) < since:
                break
        return items
    if kind in ("html_list", "titleattr_list"):
        items: List[Dict] = []
        seen_first: Optional[str] = None
        for page in range(1, feed.get("max_pages", 60) + 1):
            url = feed["url"].format(page=page)
            data = crawler.fetch_raw(url)
            if not data:
                break
            html_str = data.decode(feed.get("encoding", "utf-8"), errors="ignore")
            if kind == "titleattr_list":
                page_items = listing.parse_titleattr_list(html_str, url)
            else:
                page_items = listing.parse_html_list(html_str, url, feed.get("date_before", False))
            if not page_items or page_items[0]["url"] == seen_first:
                break
            seen_first = page_items[0]["url"]
            items.extend(page_items)
            if min(i["published_on"] for i in page_items) < since:
                break
        return items
    raise ValueError(f"unknown feed type: {kind}")


def run(sources: List[Dict], lex: Dict, crawler: PoliteCrawler, since: str, until: str):
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records: List[Dict] = []
    seen = set()
    stats: Dict[str, Dict] = {}
    for src in sources:
        st = stats.setdefault(src["id"], {"count": 0, "clarification": 0, "oldest": None, "newest": None, "feeds": 0})
        if not src.get("feeds"):
            st["note"] = src.get("note", "no feed configured")
            continue
        for feed in src["feeds"]:
            items = fetch_feed(feed, crawler, since)
            st["feeds"] += 1
            for it in items:
                d = it["published_on"]
                st["oldest"] = d if st["oldest"] is None else min(st["oldest"], d)
                st["newest"] = d if st["newest"] is None else max(st["newest"], d)
                if not textutil.is_date_in_range(d, since, until) or it["url"] in seen:
                    continue
                seen.add(it["url"])
                rec = build_record(src, it, now_iso, lex, feed)
                records.append(rec)
                st["count"] += 1
                st["clarification"] += 1 if rec["clarification"] else 0
        if not st["count"] and not st["oldest"]:
            st["note"] = "feeds returned no dated items (blocked, empty or unparsable)"
    return records, stats


def main():
    ap = argparse.ArgumentParser(description="Fetch official statements and public records metadata.")
    ap.add_argument("--since", default="2026-04-24")
    ap.add_argument("--until", default="2026-10-24")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--source", default="all", help="source id (for example ey) or all")
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--cache-dir", type=Path, default=HERE / ".cache")
    args = ap.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    lex = classify.load_lexicons(HERE)
    if args.source != "all":
        sources = [s for s in sources if s["id"] == args.source]
        if not sources:
            logger.error("source '%s' not found", args.source)
            sys.exit(1)

    crawler = PoliteCrawler(cache_dir=args.cache_dir)
    records, stats = run(sources, lex, crawler, args.since, args.until)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Window {args.since} to {args.until}; {len(records)} records -> {args.out}")
    for sid, st in stats.items():
        print(f"  {sid}: kept={st['count']} clarification={st['clarification']} oldest={st['oldest']} newest={st['newest']} {st.get('note', '')}")
    stopped = sorted(crawler.stopped_hosts)
    if stopped:
        print("Stopped hosts (5 failures):", ", ".join(stopped))


if __name__ == "__main__":
    main()
