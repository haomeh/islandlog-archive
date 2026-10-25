"""List-page routes (T16-C, R87, R93): dated list pages, paged lists and browser scrolling.

A route reads list pages only. It keeps URL, title and date. It never keeps an article body.
Standard library only. The browser route calls list_browser.mjs.
"""

import datetime
import html
import json
import logging
import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from tools.newsfetch.crawler import USER_AGENT, PoliteCrawler
from tools.newsfetch.parser import make_snippet, mask_title

logger = logging.getLogger("newsfetch.lists")

ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)
HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
TITLE_ATTR_RE = re.compile(r"""title\s*=\s*["']([^"']+)["']""", re.I)
TAG_RE = re.compile(r"<[^>]+>")
MONTH_LETTERS = {"A": 10, "B": 11, "C": 12}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "chdtv", "from", "ref"}
BROWSER_SCRIPT = Path(__file__).with_name("list_browser.mjs")
MIN_TITLE_CHARS = 6


def canonical_url(url: str) -> str:
    """Drops the fragment, tracking parameters and a trailing slash, so one article has one URL."""
    parts = urllib.parse.urlsplit(url.strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    path = parts.path.rstrip("/") or "/"
    scheme = "https" if parts.scheme == "http" else parts.scheme
    return urllib.parse.urlunsplit((scheme, parts.netloc.lower(), path, urllib.parse.urlencode(query), ""))


def _plain(text: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", text)).split())


def date_from_match(m: "re.Match", today: str) -> Optional[str]:
    """Builds YYYY-MM-DD from the groups y (optional), m and d. m can be a month letter A to C."""
    groups = m.groupdict()
    month_raw, day_raw = groups.get("m"), groups.get("d")
    if not month_raw or not day_raw:
        return None
    month = MONTH_LETTERS.get(month_raw.upper()) if month_raw.upper() in MONTH_LETTERS else int(month_raw)
    day = int(day_raw)
    if groups.get("y"):
        year = int(groups["y"])
    else:
        # A date without a year is never in the future: the list is newest first.
        t = datetime.date.fromisoformat(today)
        year = t.year if (month, day) <= (t.month, t.day) else t.year - 1
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_anchor_list(html_text: str, route: Dict, base_url: str, today: str, publisher: str) -> List[Dict]:
    """Reads the article links of one list page.

    route: link (regex on the absolute href), date_where (url, before, after, inner or time_attr),
    date_regex (groups y, m, d), title_min, title_strip and anchor_before (optional; anchor_before is a regex for the markup right before the link).
    """
    link_re = re.compile(route["link"])
    date_re = re.compile(route["date_regex"])
    where = route.get("date_where", "url")
    title_min = route.get("title_min", MIN_TITLE_CHARS)
    items: List[Dict] = []
    seen = set()
    for m in ANCHOR_RE.finditer(html_text):
        attrs, inner = m.group(1), m.group(2)
        href_m = HREF_RE.search(attrs)
        if not href_m:
            continue
        href = urllib.parse.urljoin(base_url, html.unescape(href_m.group(1)))
        if not link_re.search(href):
            continue
        if route.get("anchor_before") and not re.search(route["anchor_before"], html_text[max(0, m.start() - 300): m.start()]):
            continue
        url = canonical_url(href)
        if url in seen:
            continue
        title_m = TITLE_ATTR_RE.search(attrs)
        title = _plain(title_m.group(1)) if title_m else _plain(inner)
        published = None
        if where == "inner":
            # The date label sits inside the link text: read it, then cut it from the title.
            dm = date_re.search(title)
            if dm:
                published = date_from_match(dm, today)
                title = " ".join((title[: dm.start()] + " " + title[dm.end():]).split())
        if route.get("title_strip"):
            title = re.sub(route["title_strip"], "", title).strip()
        if len(title) < title_min:
            continue
        if where == "url":
            dm = date_re.search(href)
            published = date_from_match(dm, today) if dm else None
        elif where == "before":
            text = _plain(html_text[max(0, m.start() - 250): m.start()])
            found = list(date_re.finditer(text))
            published = date_from_match(found[-1], today) if found else None
        elif where == "after":
            text = _plain(html_text[m.end(): m.end() + 400])
            dm = date_re.search(text)
            published = date_from_match(dm, today) if dm else None
        elif where == "time_attr":
            text = html_text[m.end(): m.end() + 800]
            dm = date_re.search(text)
            published = date_from_match(dm, today) if dm else None
        if not published:
            continue
        seen.add(url)
        items.append(make_item(url, title, published, publisher))
    return items


def make_item(url: str, title: str, published: str, publisher: str) -> Dict:
    masked = mask_title(title)
    return {
        "url": url,
        "title": masked,
        "publisher": publisher,
        "published_on": published,
        "snippet": make_snippet(masked),
        "summary": "",
    }


RELATIVE_RE = re.compile(r"(?:(?P<n>\d+)\s*(?P<unit>分鐘|小時|天)前|(?P<yesterday>昨天)|(?P<clock>\d{1,2}:\d{2})\s*$)")


def relative_date(row: str, now: datetime.datetime) -> Optional[str]:
    """Reads a label such as 3小時前 or 2天前 and returns the date (Asia/Taipei). Used where a list shows no date."""
    m = RELATIVE_RE.search(row)
    if not m:
        return None
    if m.group("n"):
        n = int(m.group("n"))
        if m.group("unit") == "天":
            return (now.date() - datetime.timedelta(days=n)).isoformat()
        delta = datetime.timedelta(minutes=n) if m.group("unit") == "分鐘" else datetime.timedelta(hours=n)
        return (now - delta).date().isoformat()
    if m.group("yesterday"):
        return (now.date() - datetime.timedelta(days=1)).isoformat()
    return now.date().isoformat()


def date_range(since: str, until: str) -> Iterator[datetime.date]:
    cur = datetime.date.fromisoformat(since)
    end = datetime.date.fromisoformat(until)
    while cur <= end:
        yield cur
        cur += datetime.timedelta(days=1)


def fetch_dated_list(route: Dict, crawler: PoliteCrawler, publisher: str, since: str, until: str,
                     today: str) -> List[Dict]:
    """One list page per day (and per category). url holds {date}, {category} and {page}."""
    found: List[Dict] = []
    date_fmt = route.get("date_format", "%Y-%m-%d")
    for day in date_range(since, until):
        for category in route.get("categories", [""]):
            seen_day = set()
            for page in range(1, route.get("max_pages", 1) + 1):
                url = route["url"].format(date=day.strftime(date_fmt), category=category, page=page)
                content = crawler.fetch_raw(url)
                if not content:
                    break
                page_items = parse_anchor_list(content.decode("utf-8", errors="ignore"), route, url, today, publisher)
                new_items = [i for i in page_items if i["url"] not in seen_day]
                if not new_items:
                    break
                seen_day.update(i["url"] for i in new_items)
                found.extend(new_items)
    return found


def fetch_paged_list(route: Dict, crawler: PoliteCrawler, publisher: str, since: str, today: str) -> List[Dict]:
    """Pages of a newest-first list. Stops when a page is older than since, empty or repeated."""
    found: List[Dict] = []
    seen = set()
    for page in range(route.get("first_page", 1), route.get("max_pages", 200) + 1):
        url = route["url"].format(page=page)
        content = crawler.fetch_raw(url)
        if not content:
            break
        page_items = parse_anchor_list(content.decode("utf-8", errors="ignore"), route, url, today, publisher)
        new_items = [i for i in page_items if i["url"] not in seen]
        if not new_items:
            break
        seen.update(i["url"] for i in new_items)
        found.extend(new_items)
        if all(i["published_on"] < since for i in new_items):
            break
    return found


def robots_deny_patterns(crawler: PoliteCrawler, url: str) -> List[str]:
    """Regexes of the paths that robots.txt denies to our token, for the browser to abort."""
    parts = urllib.parse.urlsplit(url)
    hr = crawler.load_robots(parts.netloc.lower(), scheme=parts.scheme)
    patterns: List[str] = []
    parser = hr.parser
    entries = list(parser.entries) + ([parser.default_entry] if parser.default_entry else [])
    token = crawler.user_agent.split("/")[0].lower()
    # A group that names our token wins over the * group (RFC 9309).
    named = [e for e in entries if any(u.lower() == token for u in e.useragents)]
    for entry in named or [e for e in entries if "*" in e.useragents]:
        for rule in entry.rulelines:
            if not rule.allowance and rule.path:
                patterns.append("^" + re.escape(urllib.parse.unquote(rule.path)).replace(r"\*", ".*"))
    return patterns


def node_list_browser(url: str, user_agent: str, config: Dict, timeout: int = 900) -> Dict:
    env = dict(os.environ)
    if os.environ.get("NEWSFETCH_NODE_PATH"):
        env["NODE_PATH"] = os.environ["NEWSFETCH_NODE_PATH"]
    proc = subprocess.run(["node", str(BROWSER_SCRIPT), url, user_agent, json.dumps(config)],
                          capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"list browser exit {proc.returncode}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def fetch_browser_list(route: Dict, crawler: PoliteCrawler, publisher: str, since: str, today: str,
                       browser=node_list_browser) -> List[Dict]:
    """Scrolls one list page slowly in a real browser. Robots is checked first and fails closed."""
    url = route["url"]
    parts = urllib.parse.urlsplit(url)
    hr = crawler.load_robots(parts.netloc.lower(), scheme=parts.scheme)
    if not hr.can_fetch(crawler.user_agent, url):
        logger.info("Blocked by robots.txt: %s", url)
        return []
    config = {
        "link": route["link"],
        "more": route.get("more", ""),
        "max_steps": route.get("max_steps", 80),
        "delay_ms": max(1000, route.get("delay_ms", 1200)),
        "stop_before": since,
        "deny": robots_deny_patterns(crawler, url),
        "row_selector": route.get("row_selector", ""),
        "page_template": route.get("page_template", ""),
        "last_page": route.get("last_page", 9000),
        "light": bool(route.get("page_template")),
        "stop_probe": route.get("stop_probe", ""),
    }
    if route.get("partial"):
        config["partial"] = route["partial"]
    result = browser(url, crawler.user_agent, config)
    if result.get("denied"):
        logger.warning("Browser aborted %d robots-denied requests: %s", len(result["denied"]), result["denied"][:3])
    items: List[Dict] = []
    seen = set()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    for row in result.get("items", []):
        text = (row.get("row", "") + " " + row.get("hint", "")).strip()
        where = route.get("date_where", "url")
        if where == "relative":
            published = relative_date(row.get("row", ""), now)
            parsed = [make_item(canonical_url(row["href"]), row["title"], published, publisher)] if published else []
        else:
            anchor = f'<a href="{html.escape(row["href"])}" title="{html.escape(row["title"])}">x</a>'
            if where != "url":
                anchor = anchor + " " + html.escape(text)
            probe = {"link": route["link"], "date_regex": route["date_regex"], "date_where": where}
            for key in ("title_strip", "title_min"):
                if key in route:
                    probe[key] = route[key]
            parsed = parse_anchor_list(anchor, probe, url, today, publisher)
        for item in parsed:
            if item["url"] not in seen:
                seen.add(item["url"])
                items.append(item)
    return items
