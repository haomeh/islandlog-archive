#!/usr/bin/env python3
"""Resumable back-fill of news metadata per outlet and per date window (T16-C, R91).

Usage:
    python3 -m tools.newsfetch.backfill --out-dir DIR --log-dir DIR --since 2026-04-24 --until 2026-10-25 [--source ID ...]

Each unit (one 7-day window of a dated list, or the whole run of other routes) writes
DIR/parts/<id>/<unit>.jsonl and then a line in DIR/state/<id>.done. A second run skips done units.
Run one process per outlet: outlets on different hosts can run in parallel (1 request per second per host).
The record format is the same as fetch.py writes (all2.jsonl), so cluster.py and topics_full.py work unchanged.
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.newsfetch.classify import Classifier
from tools.newsfetch.crawler import PoliteCrawler
from tools.newsfetch.fetch import (
    DEFAULT_FEEDS_PATH,
    build_record,
    fetch_source_items,
    generate_weekly_windows,
    load_feeds,
)
from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.lists import canonical_url
from tools.newsfetch.parser import is_date_in_range
from tools.newsfetch.publishers import PublisherIndex

logger = logging.getLogger("newsfetch.backfill")


def units_for(feed: Dict, since: str, until: str, route_mode: str = "auto") -> List[Dict]:
    """Splits one outlet into resumable units."""
    if route_mode == "click":
        # One click run per outlet: the browser walks the whole list in one go (R179).
        return [{"name": "click", "since": since, "until": until}]
    if feed.get("type") == "dated_list":
        return [
            {"name": f"{a}_{b}", "since": f"{a[:4]}-{a[4:6]}-{a[6:]}", "until": f"{b[:4]}-{b[4:6]}-{b[6:]}"}
            for a, b in generate_weekly_windows(since, until)
        ]
    return [{"name": "all", "since": since, "until": until}]


def done_units(state_file: Path) -> set:
    if not state_file.exists():
        return set()
    return {line.strip() for line in state_file.read_text(encoding="utf-8").splitlines() if line.strip()}


def run_unit(feed: Dict, unit: Dict, crawler, news_filter, classifier, index, parts_dir: Path, route_mode: str = "auto") -> int:
    items = fetch_source_items(feed, crawler, since=unit["since"], until=unit["until"], route_mode=route_mode)
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = set()
    count = 0
    parts_dir.mkdir(parents=True, exist_ok=True)
    tmp = parts_dir / (unit["name"] + ".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as out:
        for item in items:
            if not is_date_in_range(item["published_on"], unit["since"], unit["until"]):
                continue
            keep, matched = news_filter.should_keep(item["title"], item.get("summary", ""))
            if not keep:
                continue
            url = canonical_url(item["url"])
            if url in seen:
                continue
            seen.add(url)
            item = dict(item, url=url)
            record = build_record(item, index.brand(feed["publisher"]), now_iso, matched, classifier,
                                  index.group(feed["publisher"]))
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    tmp.rename(parts_dir / (unit["name"] + ".jsonl"))
    return count


def merge_source(out_dir: Path, source_id: str) -> Dict:
    """Merges the parts of one outlet into news-<id>.jsonl and returns count and reach."""
    seen = {}
    for part in sorted((out_dir / "parts" / source_id).glob("*.jsonl")):
        for line in part.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                seen.setdefault(record["url"], record)
    records = sorted(seen.values(), key=lambda r: (r["published_on"], r["url"]))
    with open(out_dir / f"news-{source_id}.jsonl", "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    dates = [r["published_on"] for r in records]
    return {"id": source_id, "items": len(records), "oldest": min(dates) if dates else None,
            "newest": max(dates) if dates else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default="2026-04-24")
    ap.add_argument("--until", default=datetime.date.today().isoformat())
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--log-dir", type=Path, required=True)
    ap.add_argument("--source", action="append", help="outlet id; repeat for several")
    ap.add_argument("--feeds", type=Path, default=DEFAULT_FEEDS_PATH)
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--route", choices=("auto", "click"), default="auto",
                    help="click: run the browser click route of each outlet only (R179); auto: the earlier routes")
    ap.add_argument("--no-resume", action="store_true", help="ignore the done list (daily timer runs)")
    args = ap.parse_args(argv)

    feeds = load_feeds(args.feeds)
    index = PublisherIndex(feeds)
    wanted = args.source or [f["id"] for f in feeds]
    args.log_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "state").mkdir(parents=True, exist_ok=True)
    news_filter, classifier = NewsFilter(), Classifier()

    logging.basicConfig(force=True, level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S",
                        handlers=[logging.FileHandler(args.log_dir / f"backfill-{'+'.join(wanted)}.log", encoding="utf-8")])
    summary = []
    for feed in feeds:
        if feed["id"] not in wanted:
            continue
        crawler = PoliteCrawler(cache_dir=args.cache_dir or args.out_dir / "cache" / feed["id"])
        crawler.use_browser_robots([feed])
        state_file = args.out_dir / "state" / f"{feed['id']}.done"
        finished = set() if args.no_resume else done_units(state_file)
        for unit in units_for(feed, args.since, args.until, args.route):
            if unit["name"] in finished:
                logger.info("%s %s already done", feed["id"], unit["name"])
                continue
            count = run_unit(feed, unit, crawler, news_filter, classifier, index, args.out_dir / "parts" / feed["id"], args.route)
            with open(state_file, "a", encoding="utf-8") as f:
                f.write(unit["name"] + "\n")
            logger.info("%s %s done: %d records", feed["id"], unit["name"], count)
        reports = getattr(crawler, "click_reports", None)
        if reports:
            (args.out_dir / "state" / f"{feed['id']}.click-report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")
        result = merge_source(args.out_dir, feed["id"])
        summary.append(result)
        logger.info("%s merged: %s", feed["id"], result)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
