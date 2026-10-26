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
from typing import Dict, Optional, Tuple

USER_AGENT = "islandlog-newsfetch/0.1 (+https://github.com/haomeh/islandlog-archive)"
DEFAULT_CACHE_DIR = Path(__file__).parent / ".cache"
MAX_HOST_FAILURES = 5
MAX_REDIRECTS = 3
CACHE_TTL_SECONDS = 24 * 3600
ROBOTS_TTL_SECONDS = 3600
REQUEST_TIMEOUT = 15
# Markers of error or captcha pages that must never enter the cache.
ERROR_PAGE_MARKERS = (
    "captcha",
    "access denied",
    "just a moment",
    "attention required",
    "are you a robot",
    "403 forbidden",
    "too many requests",
    "驗證碼",
    "人機驗證",
    "請證明您不是機器人",
)

logger = logging.getLogger("newsfetch.crawler")


class HostRobots:
    """robots.txt rules for one host.

    Modes: "rules" (parsed content), "allow_all" (robots.txt is 404/410),
    "disallow_all" (robots.txt could not be read: fail closed).
    """

    def __init__(self, content: Optional[str] = None, mode: Optional[str] = None):
        self.parser = urllib.robotparser.RobotFileParser()
        self.loaded_at = time.time()
        if mode is not None:
            self.mode = mode
        elif content is None:
            self.mode = "allow_all"
        else:
            self.mode = "rules"
        if content and self.mode == "rules":
            self.parser.parse(content.splitlines())

    @property
    def is_missing(self) -> bool:
        return self.mode == "allow_all"

    def can_fetch(self, user_agent: str, url: str) -> bool:
        if self.mode == "allow_all":
            # RFC 9309: a missing robots.txt (404/410) allows access
            return True
        if self.mode == "disallow_all":
            return False
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
    """Disk cache for fetched 200 responses, with a time to live."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, url: str) -> Path:
        hashed = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}.cache"

    def get(self, url: str, ttl: float = CACHE_TTL_SECONDS) -> Optional[bytes]:
        path = self._get_path(url)
        try:
            if not path.exists():
                return None
            if time.time() - path.stat().st_mtime > ttl:
                return None
            return path.read_bytes()
        except OSError as err:
            logger.warning("Cache read error for %s: %s", url, err)
        return None

    def set(self, url: str, data: bytes) -> None:
        path = self._get_path(url)
        try:
            path.write_bytes(data)
        except OSError as err:
            logger.warning("Cache write error for %s: %s", url, err)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stops urllib from following redirects. The crawler follows them by hand."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def looks_like_error_page(data: bytes) -> bool:
    """Returns True if a 200 body looks like an error or captcha page."""
    if not data:
        return True
    head = data[:4096].decode("utf-8", errors="ignore").lower()
    return any(marker in head for marker in ERROR_PAGE_MARKERS)


class PoliteCrawler:
    """Polite web crawler: robots.txt (fail closed), host rate limit, manual redirects, cache."""

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        cache_dir: Optional[Path] = None,
        rate_limit_interval: float = 1.0,
        use_cache: bool = True,
    ):
        self.user_agent = user_agent
        self.use_cache = use_cache
        self.cache = FileCache(cache_dir or DEFAULT_CACHE_DIR)
        self.rate_limiter = RateLimiter(min_interval=rate_limit_interval)
        self.robots_map: Dict[str, HostRobots] = {}
        self.host_failures: Dict[str, int] = {}
        self.stopped_hosts: set = set()
        self._opener = urllib.request.build_opener(_NoRedirect)

    def get_host(self, url: str) -> str:
        parts = urllib.parse.urlsplit(url)
        return parts.netloc.lower()

    def _http_get(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
        """One HTTP GET without redirect following. Returns (status, headers, body).

        Raises URLError, TimeoutError or OSError on network failure.
        """
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with self._opener.open(req, timeout=REQUEST_TIMEOUT) as resp:
                data = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
                status = resp.status
        except urllib.error.HTTPError as err:
            headers = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
            return err.code, headers, b""
        if headers.get("content-encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return status, headers, data

    def _record_failure(self, host: str) -> None:
        failures = self.host_failures.get(host, 0) + 1
        self.host_failures[host] = failures
        if failures >= MAX_HOST_FAILURES:
            logger.error("Host %s failed %d times. Stopping host.", host, failures)
            self.stopped_hosts.add(host)

    def load_robots(self, host: str, scheme: str = "https") -> HostRobots:
        cached = self.robots_map.get(host)
        if cached is not None and time.time() - cached.loaded_at <= ROBOTS_TTL_SECONDS:
            return cached

        robots_url = f"{scheme}://{host}/robots.txt"
        status, data = self._fetch(robots_url, check_robots=False, ttl=ROBOTS_TTL_SECONDS)
        if status == 200 and data is not None:
            hr = HostRobots(data.decode("utf-8", errors="ignore"), mode="rules")
        elif status in (404, 410):
            hr = HostRobots(mode="allow_all")
        else:
            # 5xx, timeout, blocked host, redirect loop, other: fail closed
            logger.warning("robots.txt unreadable for %s (status %s): disallow all", host, status)
            hr = HostRobots(mode="disallow_all")
        self.robots_map[host] = hr
        return hr

    def fetch_raw(
        self, url: str, check_robots: bool = True, force_refresh: bool = False
    ) -> Optional[bytes]:
        _, data = self._fetch(url, check_robots=check_robots, force_refresh=force_refresh)
        return data

    def _fetch(
        self,
        url: str,
        check_robots: bool = True,
        force_refresh: bool = False,
        ttl: float = CACHE_TTL_SECONDS,
    ) -> Tuple[Optional[int], Optional[bytes]]:
        """Fetches url, following up to MAX_REDIRECTS redirects by hand.

        Returns (status, body). status is None for a local refusal or network failure.
        body is set only for a usable 200 response.
        """
        for _hop in range(MAX_REDIRECTS + 1):
            parts = urllib.parse.urlsplit(url)
            if parts.scheme not in ("http", "https"):
                logger.warning("Refusing non-HTTP URL: %s", url)
                return None, None
            host = parts.netloc.lower()
            if host in self.stopped_hosts:
                logger.warning("Skipping %s: host %s reached maximum failure count", url, host)
                return None, None

            if self.use_cache and not force_refresh:
                cached = self.cache.get(url, ttl=ttl)
                if cached is not None:
                    return 200, cached

            if check_robots:
                hr = self.load_robots(host, scheme=parts.scheme)
                if not hr.can_fetch(self.user_agent, url):
                    logger.info("Blocked by robots.txt: %s", url)
                    return None, None

            status, headers, data = self._request_with_retry(url, host)
            if status is not None and 300 <= status < 400 and status != 304:
                location = headers.get("location")
                if not location:
                    return status, None
                url = urllib.parse.urljoin(url, location)
                continue
            if status == 200:
                if looks_like_error_page(data):
                    logger.warning("Error or captcha page, not cached: %s", url)
                    return status, None
                if self.use_cache:
                    self.cache.set(url, data)
                return status, data
            return status, None

        logger.warning("Too many redirects (max %d) from %s", MAX_REDIRECTS, url)
        return None, None

    def _request_with_retry(
        self, url: str, host: str
    ) -> Tuple[Optional[int], Dict[str, str], bytes]:
        retries = 3
        backoff = 1.0
        status: Optional[int] = None
        for attempt in range(retries):
            # Rate limit before every request to this host
            self.rate_limiter.wait(host)
            logger.info("GET %s %s", host, url)
            try:
                status, headers, data = self._http_get(url)
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                logger.warning("Fetch attempt %d failed for %s: %s", attempt + 1, url, err)
                status = None
            else:
                if status < 500 and status != 429:
                    if status == 200:
                        self.host_failures[host] = 0
                    elif status in (404, 410):
                        logger.info("URL returned %d: %s", status, url)
                    return status, headers, data
                logger.warning("Fetch attempt %d got HTTP %d for %s", attempt + 1, status, url)
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2.0
        self._record_failure(host)
        return status, {}, b""
