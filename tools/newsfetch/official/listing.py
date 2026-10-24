"""Parsers for dated listings: RSS feeds and HTML list pages.

Standard library only. No body text is read or kept.
"""

import re
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from typing import Dict, List

import textutil

ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)
HREF_RE = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.I)
TITLE_ATTR_RE = re.compile(r'title\s*=\s*["\']([^"\']+)["\']', re.I)
# Text after an anchor that may hold its date (stop at the next anchor).
WINDOW = 700


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(parent: ET.Element, name: str) -> str:
    for ch in parent:
        if _local(ch.tag) == name and ch.text:
            return ch.text.strip()
    return ""


def parse_rss(xml_bytes: bytes) -> List[Dict]:
    """Parse RSS 2.0 items into dicts with url, title, published_on, summary."""
    try:
        root = ET.fromstring(xml_bytes.lstrip(b"\xef\xbb\xbf"))
    except ET.ParseError:
        return []
    items = []
    for it in root.iter():
        if _local(it.tag) != "item":
            continue
        url = _child_text(it, "link")
        title = _child_text(it, "title")
        raw_date = _child_text(it, "pubDate") or _child_text(it, "date")
        if not (url and title and raw_date):
            continue
        try:
            published_on = textutil.parse_date(raw_date)
        except ValueError:
            continue
        items.append(
            {
                "url": url,
                "title": title,
                "published_on": published_on,
                "summary": _child_text(it, "description"),
            }
        )
    return items


def parse_html_list(html_str: str, base_url: str, date_before: bool = False) -> List[Dict]:
    """Find anchors that sit next to a date. Return url, title, published_on.

    The date follows the anchor, or precedes it if date_before is true.
    Anchors with no date in the window, and script links, are skipped.
    """
    items = []
    matches = list(ANCHOR_RE.finditer(html_str))
    for idx, m in enumerate(matches):
        attrs, inner = m.group(1), m.group(2)
        href_m = HREF_RE.search(attrs)
        if not href_m:
            continue
        href = unescape(href_m.group(1)).strip()
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        title = " ".join(unescape(textutil.TAG_RE.sub("", inner)).split())
        if not title:
            t = TITLE_ATTR_RE.search(attrs)
            title = unescape(t.group(1)).strip() if t else ""
        if len(title) < 4:
            continue
        if date_before:
            prev_end = matches[idx - 1].end() if idx else 0
            near = html_str[max(prev_end, m.start() - WINDOW): m.start()]
        else:
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(html_str)
            near = html_str[m.end(): min(end, m.end() + WINDOW)]
        date = textutil.find_date(textutil.TAG_RE.sub(" ", near))
        if date is None:
            continue
        items.append(
            {
                "url": urllib.parse.urljoin(base_url, href),
                "title": title,
                "published_on": date,
                "summary": "",
            }
        )
    return items


def parse_titleattr_list(html_str: str, base_url: str) -> List[Dict]:
    """Parse anchors that hold a title attribute and a date inside the anchor (ey.gov.tw).

    The teaser paragraph is not kept.
    """
    items = []
    for m in ANCHOR_RE.finditer(html_str):
        attrs, inner = m.group(1), m.group(2)
        href_m, title_m = HREF_RE.search(attrs), TITLE_ATTR_RE.search(attrs)
        if not (href_m and title_m):
            continue
        date = textutil.find_date(textutil.TAG_RE.sub(" ", inner))
        title = " ".join(unescape(title_m.group(1)).split())
        if date is None or len(title) < 4:
            continue
        items.append(
            {
                "url": urllib.parse.urljoin(base_url, unescape(href_m.group(1)).strip()),
                "title": title,
                "published_on": date,
                "summary": "",
            }
        )
    return items
