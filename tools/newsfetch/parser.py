"""Parsers for date, text, privacy masking, sitemaps, and RSS feeds.

Standard library only.
"""

import email.utils
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from tools.newsfetch.namemask import mask_names

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


# Public figures (officials, legislators, mayors) whose names stay visible.
# An editor maintains tools/newsfetch/public_figures.json.
PUBLIC_FIGURES_PATH = Path(__file__).parent / "public_figures.json"

# 2-4 character name (surname + 1 to 3 characters) right before a verdict/action word.
VICTIM_WORDS = (
    "失聯|失蹤|身亡|死亡|送醫|不治|受傷|罹難|喪生|遇害|輕生|墜海|墜樓|落海|溺水|猝死|[(（]\\d{1,3}歲"
)
PATTERN_NAME_BEFORE_VERDICT = re.compile(
    rf"(?<![{SURNAMES}])([{SURNAMES}][\u4e00-\u9fff]{{1,3}})(?=[涉遭被]|{VICTIM_WORDS})"
)
# A personal name does not contain these characters (organizations, places, phrases).
NON_NAME_CHARS = set("的之與及和或市縣鄉鎮區部會院署局處長案委員黨團府校所館站隊組社業費款國中生元戰方陸門船機車輛廠港島山海河湖路街橋道線艦艇客貨班列")
# A surname that is also a verb: skip when the previous character shows a word such as 照顧.
VERB_SURNAME_PREFIX = {"顧": set("照關愛看兼眷光"), "白": set("明告坦"), "易": set("交貿輕容")}


def load_public_figures(path: Path = PUBLIC_FIGURES_PATH) -> Set[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return set()
    return set(data.get("names", []))


_PUBLIC_FIGURES: Optional[Set[str]] = None


def _public_figures() -> Set[str]:
    global _PUBLIC_FIGURES
    if _PUBLIC_FIGURES is None:
        _PUBLIC_FIGURES = load_public_figures()
    return _PUBLIC_FIGURES


def _is_civilian_false_positive(text: str, m: "re.Match") -> bool:
    surname = m.group(0)[0]
    prefixes = VERB_SURNAME_PREFIX.get(surname)
    return bool(prefixes and m.start() > 0 and text[m.start() - 1] in prefixes)


def _mask_name_before_verdict(text: str) -> str:
    figures = _public_figures()

    def repl(m: "re.Match") -> str:
        name = m.group(1)
        if any(ch in NON_NAME_CHARS for ch in name[1:]):
            return name
        if m.start() > 0 and text[m.start() - 1].isdigit():
            return name
        # Keep the name when it overlaps a listed public figure.
        if any(name in fig or fig in text[max(0, m.start() - 4): m.end()] for fig in figures):
            return name
        return "[當事人]"

    return PATTERN_NAME_BEFORE_VERDICT.sub(repl, text)


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
    masked = PATTERN_CIVILIAN.sub(
        lambda m: m.group(0) if _is_civilian_false_positive(text, m) else "[當事人]", text
    )
    masked = PATTERN_SHORT.sub("[當事人]", masked)
    return masked


# Victim details: age, street address, workplace, medical information.
PATTERN_AGE = re.compile(
    r"[(（]\s*(?:年約|約|年僅|未滿)?\d{1,3}(?:多|出頭)?歲\s*[)）]"
    r"|(?:年約|約|年僅|未滿|年滿)?\d{1,3}(?:多|出頭)?歲(?:的)?"
)
PATTERN_ADDRESS = re.compile(
    r"(?:[\u4e00-\u9fff]{1,6}[縣市])?(?:[\u4e00-\u9fff]{1,4}[鄉鎮市區])?"
    r"[\u4e00-\u9fff]{1,8}(?:路|街|大道)(?:[一二三四五六七八九十]+段)?"
    r"(?:\d+巷)?(?:\d+弄)?\d+(?:之\d+)?號(?:\d+樓|[一二三四五六七八九十]+樓)?"
)
PATTERN_WORKPLACE = re.compile(
    r"(?:任職|服務|就讀|任教|受僱|受雇|上班)(?:於|在)[^，,。；;、\s]{1,20}"
)
PATTERN_MEDICAL = re.compile(
    r"(?:罹患|患有|診斷出|病歷|病史|就醫紀錄)[^，,。；;、\s]{0,12}"
)


def strip_victim_details(text: str) -> str:
    """Removes age, address, workplace and medical details from a title or snippet."""
    if not text:
        return ""
    out = PATTERN_ADDRESS.sub("[地址]", text)
    out = PATTERN_WORKPLACE.sub("[單位]", out)
    out = PATTERN_MEDICAL.sub("[醫療資訊]", out)
    out = PATTERN_AGE.sub("", out)
    return out


def mask_title_collect(text: str):
    """Masks a title. Returns (masked text, private names removed by the context rules)."""
    base = _mask_name_before_verdict(mask_private_person(text))
    masked, names = mask_names(base, _public_figures())
    return strip_victim_details(masked), names


def mask_title(text: str) -> str:
    """Masks a title: names, civilian references and victim details."""
    return mask_title_collect(text)[0]


def make_snippet(text: str, max_chars: int = 150) -> str:
    """Cuts snippet from title or feed summary up to max_chars, removing HTML tags."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = TAG_RE.sub("", text)
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    # Apply privacy filter
    cleaned = mask_title(cleaned)
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
        if dt.tzinfo is None:
            # Zone-less dates are Asia/Taipei, never the machine zone
            dt = dt.replace(tzinfo=TZ_TW)
        dt_tw = dt.astimezone(TZ_TW)
        return dt_tw.strftime("%Y-%m-%d")

    # Normalize slashes to dashes
    s_norm = s.replace("/", "-")

    # Plain date YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s_norm):
        return s_norm

    # Space separated YYYY-MM-DD HH:MM:SS
    if " " in s_norm and "T" not in s_norm:
        parts = s_norm.split(" ")
        s_norm = parts[0] + "T" + parts[1]

    # ISO 8601
    dt = datetime.fromisoformat(s_norm)
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

        masked_title = mask_title(title)
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

            masked_title = mask_title(title)
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

            masked_title = mask_title(title)
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


def _balanced_div_blocks(html_str: str, css_class: str) -> List[str]:
    """Returns inner HTML of each <div class="css_class"> with nested divs balanced."""
    blocks: List[str] = []
    start_re = re.compile(rf'<div\s+class="{re.escape(css_class)}"[^>]*>')
    tag_re = re.compile(r"<(/?)div\b[^>]*>")
    pos = 0
    while True:
        m = start_re.search(html_str, pos)
        if not m:
            break
        depth = 1
        end = None
        for t in tag_re.finditer(html_str, m.end()):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = t.start()
                break
        if end is None:
            blocks.append(html_str[m.end():])
            break
        blocks.append(html_str[m.end():end])
        pos = end
    return blocks


def parse_ltn_search_html(html_str: str, publisher: str = "自由時報") -> List[Dict]:
    """Parses HTML search results from search.ltn.com.tw into news items."""
    items: List[Dict] = []
    if not html_str:
        return items

    cont_blocks = _balanced_div_blocks(html_str, "cont")
    for block in cont_blocks:
        link_m = re.search(r'<a\s+[^>]*?class="tit"[^>]*href="([^"]+)"', block)
        if not link_m:
            link_m = re.search(r'<a\s+[^>]*?href="([^"]+)"[^>]*class="tit"', block)
        if not link_m:
            continue
        url = link_m.group(1).strip()

        title_m = re.search(r'<a\s+[^>]*?class="tit"[^>]*>([\s\S]*?)</a>', block)
        if not title_m:
            title_m = re.search(r'<a\s+[^>]*?class="[^"]*tit[^"]*"[^>]*>([\s\S]*?)</a>', block)
        if not title_m:
            continue
        raw_title = TAG_RE.sub("", title_m.group(1)).strip()

        time_m = re.search(r'<span class="time">([\s\S]*?)</span>', block)
        if not time_m:
            continue
        time_raw = time_m.group(1).strip()

        p_m = re.search(r'<p>([\s\S]*?)</p>', block)
        summary_raw = TAG_RE.sub("", p_m.group(1)).strip() if p_m else ""

        try:
            published_on = parse_date(time_raw)
        except Exception:
            continue

        masked_title = mask_title(raw_title)
        snippet_source = summary_raw if summary_raw else masked_title
        snippet = make_snippet(snippet_source)

        items.append(
            {
                "url": url,
                "title": masked_title,
                "publisher": publisher,
                "published_on": published_on,
                "snippet": snippet,
                "summary": summary_raw,
            }
        )

    return items


def parse_ltn_ajax_json(data: bytes, today: str, publisher: str = "自由時報") -> List[Dict]:
    """Parses one page of the LTN breaking-news list (ajax JSON) into news items.

    Page 1 lists the items of today by clock time only. Those items get the date `today`.
    Image fields are not kept.
    """
    try:
        doc = json.loads(data)
    except (ValueError, TypeError):
        return []
    entries = doc.get("data") if isinstance(doc, dict) else None
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        return []

    items: List[Dict] = []
    for en in entries:
        if not isinstance(en, dict):
            continue
        url = (en.get("url") or "").strip()
        title = (en.get("title") or "").strip()
        time_raw = (en.get("time") or "").strip()
        if not url or not title or not time_raw:
            continue
        try:
            published_on = today if re.fullmatch(r"\d{1,2}:\d{2}", time_raw) else parse_date(time_raw)
        except Exception:
            continue
        summary_raw = (en.get("summary") or "").strip()
        masked_title = mask_title(title)
        items.append(
            {
                "url": url,
                "title": masked_title,
                "publisher": publisher,
                "published_on": published_on,
                "snippet": make_snippet(summary_raw if summary_raw else masked_title),
                "summary": summary_raw,
            }
        )
    return items
