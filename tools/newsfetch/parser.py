"""Parsers for date, text, privacy masking, sitemaps, and RSS feeds.

Standard library only.
"""

import email.utils
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

TZ_TW = timezone(timedelta(hours=8))
TAG_RE = re.compile(r"<[^>]+>")

# Common Taiwanese surnames
SURNAMES = (
    "黃李王張劉陳楊趙周吳徐孫胡朱高林何郭馬羅梁宋鄭謝韓唐馮于董蕭程曹袁鄧許傅沈曾彭"
    "呂蘇盧蔣蔡賈丁魏薛葉閻余潘杜戴夏鍾汪田任姜范方石姚譚廖鄒熊金陸郝孔白崔康毛邱秦"
    "江史顧侯邵孟龍萬段雷錢湯尹黎易常武喬賀賴龔文"
)

# Civilian identity suffix patterns
PATTERN_CIVILIAN = re.compile(
    rf"[{SURNAMES}]姓?(?:男子|女子|婦人|老翁|老婦|少女|少年|男童|女童|民眾|運將|嫌犯|嫌疑人|被害人|駕駛|騎士|乘客|移工|死者|傷者|病患|工程師|工人)"
)

# Shorthand 2-character civilian references e.g. 陳男, 林女, 張婦
PATTERN_SHORT = re.compile(
    rf"[{SURNAMES}][男女婦翁孩](?=[與向至在和涉遭由被已因，、。 　\s]|$)"
)


def _find_elements(root: ET.Element, local_name: str) -> List[ET.Element]:
    """Finds all descendant elements matching local_name with or without namespace."""
    res = []
    for el in root.iter():
        tag = el.tag
        if tag == local_name or (tag.startswith("{") and tag.endswith("}" + local_name)):
            res.append(el)
    return res


def _find_child(parent: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Finds direct child matching local_name with or without namespace."""
    for child in parent:
        tag = child.tag
        if tag == local_name or (tag.startswith("{") and tag.endswith("}" + local_name)):
            return child
    return None


def mask_private_person(text: str) -> str:
    """Replaces private person names/references with [當事人]. Preserves public titles."""
    if not text:
        return ""
    masked = PATTERN_CIVILIAN.sub("[當事人]", text)
    masked = PATTERN_SHORT.sub("[當事人]", masked)
    return masked


def make_snippet(text: str, max_chars: int = 150) -> str:
    """Cuts snippet from title or feed summary up to max_chars, removing HTML tags."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = TAG_RE.sub("", text)
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    # Apply privacy filter
    cleaned = mask_private_person(cleaned)
    # Normalize whitespaces
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def parse_date(date_str: str) -> str:
    """Normalizes an ISO 8601 or RFC 2822 date string into YYYY-MM-DD (UTC+8)."""
    if not date_str:
        raise ValueError("Empty date string")
    s = date_str.strip()

    # Match RFC 2822 (e.g. 'Sat, 24 Oct 2026 09:00:00 +0800' or '... GMT')
    if re.search(r"[A-Za-z]{3},", s) or "GMT" in s or "UTC" in s:
        dt = email.utils.parsedate_to_datetime(s)
        dt_tw = dt.astimezone(TZ_TW)
        return dt_tw.strftime("%Y-%m-%d")

    # Plain date YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    # Space separated YYYY-MM-DD HH:MM:SS
    if " " in s and "T" not in s:
        parts = s.split(" ")
        s = parts[0] + "T" + parts[1]

    # ISO 8601
    dt = datetime.fromisoformat(s)
    if dt.tzinfo:
        dt = dt.astimezone(TZ_TW)
    return dt.strftime("%Y-%m-%d")


def is_date_in_range(pub_date: str, since: str, until: str) -> bool:
    """Checks if pub_date (YYYY-MM-DD) falls between since and until (inclusive)."""
    return since <= pub_date <= until


def parse_news_sitemap_xml(xml_bytes: bytes, publisher: str) -> List[Dict]:
    """Parses Google News sitemap XML bytes into a list of news items."""
    items: List[Dict] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    for url_el in _find_elements(root, "url"):
        loc_el = _find_child(url_el, "loc")
        if loc_el is None or not loc_el.text:
            continue
        url = loc_el.text.strip()

        news_el = _find_child(url_el, "news")
        title = ""
        date_raw = ""
        if news_el is not None:
            title_el = _find_child(news_el, "title")
            if title_el is not None and title_el.text:
                title = title_el.text.strip()
            date_el = _find_child(news_el, "publication_date")
            if date_el is not None and date_el.text:
                date_raw = date_el.text.strip()

        # Fallback to lastmod if date_raw missing
        if not date_raw:
            lastmod_el = _find_child(url_el, "lastmod")
            if lastmod_el is not None and lastmod_el.text:
                date_raw = lastmod_el.text.strip()

        if not date_raw or not title:
            continue

        try:
            published_on = parse_date(date_raw)
        except Exception:
            continue

        masked_title = mask_private_person(title)
        snippet = make_snippet(masked_title)

        items.append(
            {
                "url": url,
                "title": masked_title,
                "publisher": publisher,
                "published_on": published_on,
                "snippet": snippet,
                "summary": "",
            }
        )

    return items


def parse_rss_xml(xml_bytes: bytes, publisher: str) -> List[Dict]:
    """Parses RSS or Atom feed XML bytes into a list of news items."""
    items: List[Dict] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    # Check for RSS item elements
    rss_items = _find_elements(root, "item")
    if rss_items:
        for it in rss_items:
            link_el = _find_child(it, "link")
            title_el = _find_child(it, "title")
            pub_date_el = _find_child(it, "pubDate")
            desc_el = _find_child(it, "description")

            if link_el is None or not link_el.text:
                continue
            if title_el is None or not title_el.text:
                continue
            if pub_date_el is None or not pub_date_el.text:
                continue

            url = link_el.text.strip()
            title = title_el.text.strip()
            raw_desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            try:
                published_on = parse_date(pub_date_el.text.strip())
            except Exception:
                continue

            masked_title = mask_private_person(title)
            snippet_source = raw_desc if raw_desc else masked_title
            snippet = make_snippet(snippet_source)

            items.append(
                {
                    "url": url,
                    "title": masked_title,
                    "publisher": publisher,
                    "published_on": published_on,
                    "snippet": snippet,
                    "summary": raw_desc,
                }
            )
        return items

    # Check for Atom entry elements
    atom_entries = _find_elements(root, "entry")
    if atom_entries:
        for en in atom_entries:
            link_el = _find_child(en, "link")
            title_el = _find_child(en, "title")
            pub_date_el = _find_child(en, "published")
            if pub_date_el is None:
                pub_date_el = _find_child(en, "updated")
            summary_el = _find_child(en, "summary")
            if summary_el is None:
                summary_el = _find_child(en, "content")

            url = ""
            if link_el is not None:
                url = link_el.get("href", "") or (link_el.text or "")
                url = url.strip()
            if not url or title_el is None or not title_el.text:
                continue
            if pub_date_el is None or not pub_date_el.text:
                continue

            title = title_el.text.strip()
            raw_desc = summary_el.text.strip() if summary_el is not None and summary_el.text else ""

            try:
                published_on = parse_date(pub_date_el.text.strip())
            except Exception:
                continue

            masked_title = mask_private_person(title)
            snippet_source = raw_desc if raw_desc else masked_title
            snippet = make_snippet(snippet_source)

            items.append(
                {
                    "url": url,
                    "title": masked_title,
                    "publisher": publisher,
                    "published_on": published_on,
                    "snippet": snippet,
                    "summary": raw_desc,
                }
            )

    return items
