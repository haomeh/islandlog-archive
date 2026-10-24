#!/usr/bin/env python3
"""CLI entrypoint for newsfetch.

Usage:
    python3 tools/newsfetch/fetch.py --since 2026-04-24 --until 2026-10-24 --out tools/newsfetch/out/news.jsonl [--source pts]
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path

# Ensure repo root is on sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Dict, List, Set

from tools.newsfetch.crawler import PoliteCrawler
from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.parser import (
    is_date_in_range,
    parse_news_sitemap_xml,
    parse_rss_xml,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FEEDS_PATH = BASE_DIR / "feeds.json"
DEFAULT_TERMS_PATH = BASE_DIR / "terms.json"
DEFAULT_OUT_PATH = BASE_DIR / "out" / "news.jsonl"
DEFAULT_CACHE_DIR = BASE_DIR / ".cache"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("newsfetch")


def load_feeds(feeds_path: Path) -> List[Dict]:
    with open(feeds_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_source_items(
    feed_cfg: Dict,
    crawler: PoliteCrawler,
) -> List[Dict]:
    url = feed_cfg["url"]
    publisher = feed_cfg["publisher"]
    feed_type = feed_cfg.get("type", "sitemap")

    logger.info("Fetching %s from %s ...", publisher, url)
    content = crawler.fetch_raw(url)
    if not content:
        logger.warning("No content retrieved for %s (%s)", publisher, url)
        return []

    if feed_type == "rss":
        items = parse_rss_xml(content, publisher=publisher)
    else:
        items = parse_news_sitemap_xml(content, publisher=publisher)

    logger.info("Parsed %d items from %s", len(items), publisher)
    return items


def main():
    parser = argparse.ArgumentParser(description="Fetch and filter Taiwan news metadata.")
    parser.add_argument(
        "--since",
        type=str,
        default="2026-04-24",
        help="Start date in YYYY-MM-DD (inclusive)",
    )
    parser.add_argument(
        "--until",
        type=str,
        default="2026-10-24",
        help="End date in YYYY-MM-DD (inclusive)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help="Output path for JSONL file",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        help="Optional publisher source ID (e.g. pts, cna, tvbs, or all)",
    )
    parser.add_argument(
        "--feeds",
        type=Path,
        default=DEFAULT_FEEDS_PATH,
        help="Path to feeds.json configuration",
    )
    parser.add_argument(
        "--terms",
        type=Path,
        default=DEFAULT_TERMS_PATH,
        help="Path to terms.json configuration",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Path to response cache directory",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass cache and re-download feeds",
    )

    args = parser.parse_args()

    # Load configurations
    if not args.feeds.exists():
        logger.error("Feeds config not found at %s", args.feeds)
        sys.exit(1)

    feeds = load_feeds(args.feeds)
    news_filter = NewsFilter()

    # Filter feeds by source if requested
    if args.source and args.source != "all":
        feeds = [f for f in feeds if f.get("id") == args.source]
        if not feeds:
            logger.error("Source ID '%s' not found in feeds config", args.source)
            sys.exit(1)

    crawler = PoliteCrawler(cache_dir=args.cache_dir)
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    output_records: List[Dict] = []
    seen_urls: Set[str] = set()
    publisher_counts: Dict[str, int] = {}
    publisher_dates: Dict[str, List[str]] = {}

    for feed_cfg in feeds:
        pub_name = feed_cfg["publisher"]
        publisher_counts.setdefault(pub_name, 0)
        publisher_dates.setdefault(pub_name, [])

        raw_items = fetch_source_items(feed_cfg, crawler)

        for item in raw_items:
            pub_date = item["published_on"]
            publisher_dates[pub_name].append(pub_date)

            # Date range filter
            if not is_date_in_range(pub_date, args.since, args.until):
                continue

            # Topic / Term filter
            keep, matched = news_filter.should_keep(item["title"], item.get("summary", ""))
            if not keep:
                continue

            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            record = {
                "url": url,
                "title": item["title"],
                "publisher": pub_name,
                "published_on": pub_date,
                "snippet": item["snippet"],
                "fetched_on": now_iso,
                "matched_terms": matched,
            }
            output_records.append(record)
            publisher_counts[pub_name] += 1

    # Ensure output directory exists
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as out_f:
        for rec in output_records:
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info("Finished. Saved %d records to %s", len(output_records), args.out)

    # Print summary statistics
    print("\n--- Newsfetch Summary ---")
    print(f"Date Window: {args.since} to {args.until}")
    print(f"Output File: {args.out}")
    print(f"Total Matched Records: {len(output_records)}")
    print("\nPublisher Reach and Matched Counts:")
    for pub, count in publisher_counts.items():
        dates = publisher_dates.get(pub, [])
        oldest = min(dates) if dates else "N/A"
        newest = max(dates) if dates else "N/A"
        print(f"  - {pub}: {count} matched items (Reach: {oldest} to {newest})")


if __name__ == "__main__":
    main()
