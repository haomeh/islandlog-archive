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

import listing  # noqa: E402
import textutil  # noqa: E402
from crawler import PoliteCrawler  # noqa: E402

DEFAULT_OUT = HERE / "out" / "official.jsonl"
DEFAULT_SOURCES = HERE / "sources.json"
DEFAULT_TERMS = HERE / "terms.json"

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


def match_terms(title: str, summary: str, terms: Dict) -> Tuple[List[str], bool]:
    """Return (matched include terms, is_excluded). Same rules as F6 filter.py."""
    text = f"{title} {summary}"
    matched = [t for t in terms.get("include_terms", []) if t in text]
    broad = terms.get("broad_terms", [])
    if broad and not any(t in text for t in terms.get("taiwan_public_body_terms", [])):
        matched = [t for t in matched if t not in broad]
    excluded = any(w in text for words in terms.get("exclude_categories", {}).values() for w in words)
    if not excluded and any(t in text for t in terms.get("foreign_soft_terms", [])):
        excluded = not any(t in text for t in terms.get("taiwan_government_terms", []))
    return matched, excluded


def build_record(source: Dict, item: Dict, fetched_on: str, matched: List[str]) -> Dict:
    title = item["title"]
    return {
        "url": item["url"],
        "publisher": source["publisher"],
        "published_on": item["published_on"],
        "title": textutil.mask_title(title),
        "snippet": textutil.make_snippet(item.get("summary") or title),
        "fetched_on": fetched_on,
        "matched_terms": matched,
        "routine": is_routine(title),
        "source_class": assign_source_class(source, title),
        "publisher_actor_hint": source.get("actor_hint", ""),
    }


def fetch_feed(feed: Dict, crawler: PoliteCrawler, since: str) -> List[Dict]:
    """Fetch one feed definition. Return raw items (all dates)."""
    kind = feed["type"]
    if kind == "rss":
        data = crawler.fetch_raw(feed["url"])
        return listing.parse_rss(data) if data else []
    if kind == "html_list":
        items: List[Dict] = []
        seen_first: Optional[str] = None
        for page in range(1, feed.get("max_pages", 60) + 1):
            url = feed["url"].format(page=page)
            data = crawler.fetch_raw(url)
            if not data:
                break
            html_str = data.decode(feed.get("encoding", "utf-8"), errors="ignore")
            page_items = listing.parse_html_list(html_str, url, feed.get("date_before", False))
            if not page_items or page_items[0]["url"] == seen_first:
                break
            seen_first = page_items[0]["url"]
            items.extend(page_items)
            if min(i["published_on"] for i in page_items) < since:
                break
        return items
    raise ValueError(f"unknown feed type: {kind}")


def run(sources: List[Dict], terms: Dict, crawler: PoliteCrawler, since: str, until: str):
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records: List[Dict] = []
    seen = set()
    stats: Dict[str, Dict] = {}
    for src in sources:
        st = stats.setdefault(src["id"], {"count": 0, "oldest": None, "newest": None, "feeds": 0, "non_routine": 0, "matched_non_routine": 0})
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
                matched, excluded = match_terms(it["title"], it.get("summary", ""), terms)
                if excluded:
                    continue
                seen.add(it["url"])
                rec = build_record({**src, **{k: v for k, v in feed.items() if k == "source_class"}}, it, now_iso, matched)
                records.append(rec)
                st["count"] += 1
                if not rec["routine"]:
                    st["non_routine"] += 1
                    st["matched_non_routine"] += 1 if matched else 0
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
    ap.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    ap.add_argument("--cache-dir", type=Path, default=HERE / ".cache")
    args = ap.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    terms = json.loads(args.terms.read_text(encoding="utf-8"))
    if args.source != "all":
        sources = [s for s in sources if s["id"] == args.source]
        if not sources:
            logger.error("source '%s' not found", args.source)
            sys.exit(1)

    crawler = PoliteCrawler(cache_dir=args.cache_dir)
    records, stats = run(sources, terms, crawler, args.since, args.until)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Window {args.since} to {args.until}; {len(records)} records -> {args.out}")
    for sid, st in stats.items():
        print(f"  {sid}: kept={st['count']} non_routine={st['non_routine']} matched_non_routine={st['matched_non_routine']} oldest={st['oldest']} newest={st['newest']} {st.get('note', '')}")
    stopped = sorted(crawler.stopped_hosts)
    if stopped:
        print("Stopped hosts (5 failures):", ", ".join(stopped))


if __name__ == "__main__":
    main()
