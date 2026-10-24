"""Polite HTTP crawler obeying robots.txt, rate limits, caching, and retry.

Standard library only.
"""

import gzip
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Dict, Optional

USER_AGENT = "islandlog-newsfetch/0.1 (+https://github.com/haomeh/islandlog-archive)"
DEFAULT_CACHE_DIR = Path(__file__).parent / ".cache"
MAX_HOST_FAILURES = 5

logger = logging.getLogger("newsfetch.crawler")


class HostRobots:
    """Manages robots.txt rules for a host."""

    def __init__(self, content: Optional[str] = None):
        self.parser = urllib.robotparser.RobotFileParser()
        self.is_missing = (content is None)
        if content:
            self.parser.parse(content.splitlines())

    def parse(self, content: str) -> None:
        self.is_missing = False
        self.parser.parse(content.splitlines())

    def can_fetch(self, user_agent: str, url: str) -> bool:
        if self.is_missing:
            # Per RFC 9309, missing robots.txt allows access
            return True
        return self.parser.can_fetch(user_agent, url)


class RateLimiter:
    """Limits requests to maximum 1 request per second per host."""

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self._last_request_time: Dict[str, float] = {}

    def wait(self, host: str) -> None:
        now = time.time()
        last = self._last_request_time.get(host, 0.0)
        elapsed = now - last
        if elapsed < self.min_interval:
            sleep_needed = self.min_interval - elapsed
            time.sleep(sleep_needed)
        self._last_request_time[host] = time.time()


class FileCache:
    """Disk cache for fetched responses."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, url: str) -> Path:
        hashed = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}.cache"

    def get(self, url: str) -> Optional[bytes]:
        path = self._get_path(url)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    return f.read()
            except OSError as err:
                logger.warning("Cache read error for %s: %s", url, err)
        return None

    def set(self, url: str, data: bytes) -> None:
        path = self._get_path(url)
        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError as err:
            logger.warning("Cache write error for %s: %s", url, err)


class PoliteCrawler:
    """Polite web crawler adhering to robots.txt, host rate limits, and caching."""

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        cache_dir: Optional[Path] = None,
        rate_limit_interval: float = 1.0,
    ):
        self.user_agent = user_agent
        self.cache = FileCache(cache_dir or DEFAULT_CACHE_DIR)
        self.rate_limiter = RateLimiter(min_interval=rate_limit_interval)
        self.robots_map: Dict[str, HostRobots] = {}
        self.host_failures: Dict[str, int] = {}
        self.stopped_hosts: set = set()

    def get_host(self, url: str) -> str:
        parts = urllib.parse.urlsplit(url)
        return parts.netloc.lower()

    def load_robots(self, host: str, scheme: str = "https") -> HostRobots:
        if host in self.robots_map:
            return self.robots_map[host]

        robots_url = f"{scheme}://{host}/robots.txt"
        content_bytes = self.fetch_raw(robots_url, check_robots=False)
        content_str = None
        if content_bytes is not None:
            content_str = content_bytes.decode("utf-8", errors="ignore")

        hr = HostRobots(content_str)
        self.robots_map[host] = hr
        return hr

    def fetch_raw(
        self, url: str, check_robots: bool = True, force_refresh: bool = False
    ) -> Optional[bytes]:
        host = self.get_host(url)
        if host in self.stopped_hosts:
            logger.warning("Skipping %s: host %s reached maximum failure count", url, host)
            return None

        # Check cache first
        if not force_refresh:
            cached = self.cache.get(url)
            if cached is not None:
                return cached

        # Check robots.txt
        if check_robots:
            scheme = urllib.parse.urlsplit(url).scheme or "https"
            hr = self.load_robots(host, scheme=scheme)
            if not hr.can_fetch(self.user_agent, url):
                logger.info("Blocked by robots.txt: %s", url)
                return None

        # Rate limit per host
        self.rate_limiter.wait(host)

        # Retry with back-off
        retries = 3
        backoff = 1.0
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})

        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    # Decompress gzip if applicable
                    if resp.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                        data = gzip.decompress(data)

                    # Reset failure count on success
                    self.host_failures[host] = 0
                    self.cache.set(url, data)
                    return data
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    logger.info("URL returned 404 (Not Found): %s", url)
                    return None
                logger.warning(
                    "Fetch attempt %d failed for %s: %s", attempt + 1, url, err
                )
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    failures = self.host_failures.get(host, 0) + 1
                    self.host_failures[host] = failures
                    if failures >= MAX_HOST_FAILURES:
                        logger.error(
                            "Host %s failed %d times. Stopping host.", host, failures
                        )
                        self.stopped_hosts.add(host)
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                logger.warning(
                    "Fetch attempt %d failed for %s: %s", attempt + 1, url, err
                )
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    failures = self.host_failures.get(host, 0) + 1
                    self.host_failures[host] = failures
                    if failures >= MAX_HOST_FAILURES:
                        logger.error(
                            "Host %s failed %d times. Stopping host.", host, failures
                        )
                        self.stopped_hosts.add(host)

        return None
