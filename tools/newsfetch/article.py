"""Article step: open a news article in a real browser and keep only a few fields (R60, R61).

The browser extracts byline, section, publish time and a short quote inside the page.
This module keeps only those fields, cuts the quote to 150 characters and never stores,
caches or logs the article body.

CLI: python3 -m tools.newsfetch.article in.jsonl out.jsonl
The browser helper is article_browser.mjs. It needs Node and the playwright package
(set NEWSFETCH_NODE_PATH to a node_modules folder that has it).
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from tools.newsfetch.crawler import USER_AGENT, PoliteCrawler, RateLimiter

ROBOTS_TOKEN = "islandlog-newsfetch"
QUOTE_MAX = 150
BYLINE_MAX = 80
SECTION_MAX = 40
KEPT_FIELDS = ("byline", "section", "published_at", "quote")
# R61: hosts or paths that the article step must never open, whatever robots.txt says.
DENIED_PATHS = {"udn.com": re.compile(r"^/news/", re.I)}
LTN_SECTIONS = {"politics": "政治", "life": "生活", "society": "社會", "world": "國際", "local": "地方",
                "business": "財經", "entertainment": "娛樂", "sports": "體育", "Taipei": "臺北", "art": "藝文"}
BROWSER_SCRIPT = Path(__file__).with_name("article_browser.mjs")

logger = logging.getLogger("newsfetch.article")


def clean_byline(text):
    """Returns "記者王小明" from forms like "〔記者王小明／台北報導〕". Returns "" when it does not look like a byline."""
    t = (text or "").strip().strip("〔〕[]()（）")
    head = re.split(r"[／/]", t)[0].strip()
    if head.startswith("記者"):
        t = head  # drop the place: 記者王小明／台北報導 -> 記者王小明
    if not t or len(t) > BYLINE_MAX or "\n" in t:
        return ""
    return t


def section_from_url(url):
    parts = urllib.parse.urlparse(url)
    if parts.hostname and parts.hostname.endswith("ltn.com.tw"):
        segs = parts.path.strip("/").split("/")
        if len(segs) >= 2 and segs[0] == "news":
            return LTN_SECTIONS.get(segs[1], "")
    return ""


def node_browser(url, user_agent, timeout=45):
    """Runs the browser helper. It prints one JSON object with the kept fields only."""
    env = dict(os.environ)
    if os.environ.get("NEWSFETCH_NODE_PATH"):
        env["NODE_PATH"] = os.environ["NEWSFETCH_NODE_PATH"]
    proc = subprocess.run(["node", str(BROWSER_SCRIPT), url, user_agent], capture_output=True, text=True,
                          timeout=timeout, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"browser exit {proc.returncode}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class ArticleStep:
    def __init__(self, crawler, browser=node_browser, limiter=None, clock=time):
        self.crawler = crawler
        self.browser = browser
        self.min_interval = (limiter or RateLimiter()).min_interval
        self.clock = clock
        self._last = {}

    def _wait(self, host):
        last = self._last.get(host)
        if last is not None:
            gap = self.clock.time() - last
            if gap < self.min_interval:
                self.clock.sleep(self.min_interval - gap)
        self._last[host] = self.clock.time()

    def extract(self, url):
        parts = urllib.parse.urlparse(url)
        host = (parts.hostname or "").lower()
        for denied_host, pattern in DENIED_PATHS.items():
            if (host == denied_host or host.endswith("." + denied_host)) and pattern.search(parts.path):
                return {"url": url, "status": "host_rule_denied"}
        robots = self.crawler.load_robots(host, parts.scheme or "https")
        if not robots.can_fetch(ROBOTS_TOKEN, url):
            return {"url": url, "status": "robots_denied"}
        self._wait(host)
        try:
            raw = self.browser(url, USER_AGENT)
        except Exception as err:  # the message can hold page text: log the type only
            logger.warning("browser error for %s: %s", url, type(err).__name__)
            return {"url": url, "status": "browser_error"}
        out = {"url": url, "status": "ok"}
        byline = clean_byline(str(raw.get("byline") or ""))
        section = str(raw.get("section") or "").strip()
        section = LTN_SECTIONS.get(section, section)[:SECTION_MAX] or section_from_url(url)
        published = str(raw.get("published_at") or "").strip()[:40]
        quote = re.sub(r"\s+", " ", str(raw.get("quote") or "")).strip()[:QUOTE_MAX]
        for key, value in (("byline", byline), ("section", section), ("published_at", published), ("quote", quote)):
            if value:
                out[key] = value
        return out


def main(argv):
    if len(argv) != 3:
        print("usage: python3 -m tools.newsfetch.article in.jsonl out.jsonl", file=sys.stderr)
        return 2
    step = ArticleStep(PoliteCrawler())
    with open(argv[1], encoding="utf-8") as src, open(argv[2], "w", encoding="utf-8") as dst:
        for line in src:
            item = json.loads(line)
            result = step.extract(item["url"])
            dst.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
