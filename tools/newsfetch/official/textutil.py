"""Text helpers for official sources. Copied from newsfetch/parser.py (branch m1/news-fetch), plus ROC dates.

Standard library only.
"""

import email.utils
import html
import re
from datetime import datetime, timedelta, timezone

TZ_TW = timezone(timedelta(hours=8))
TAG_RE = re.compile(r"<[^>]+>")

SURNAMES = (
    "黃李王張劉陳楊趙周吳徐孫胡朱高林何郭馬羅梁宋鄭謝韓唐馮于董蕭程曹袁鄧許傅沈曾彭"
    "呂蘇盧蔣蔡賈丁魏薛葉閻余潘杜戴夏鍾汪田任姜范方石姚譚廖鄒熊金陸郝孔白崔康毛邱秦"
    "江史顧侯邵孟龍萬段雷錢湯尹黎易常武喬賀賴龔文"
)

PATTERN_CIVILIAN = re.compile(
    rf"[{SURNAMES}]姓?(?:男子|女子|婦人|老翁|老婦|少女|少年|男童|女童|民眾|運將|嫌犯|嫌疑人|被害人|駕駛|騎士|乘客|移工|死者|傷者|病患|工程師|工人)"
)
PATTERN_SHORT = re.compile(
    rf"[{SURNAMES}][男女婦翁孩](?=[與向至在和涉遭由被已因，、。 　\s]|$)"
)

ROC_RE = re.compile(r"^(\d{2,3})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*日?$")
# Date search inside longer text (used by list pages).
DATE_FIND_RE = re.compile(
    r"(?<!\d)(?:(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})|(1\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?)(?!\d)"
)


def mask_private_person(text: str) -> str:
    """Replace private person references with [當事人]. Public titles stay."""
    if not text:
        return ""
    masked = PATTERN_CIVILIAN.sub("[當事人]", text)
    return PATTERN_SHORT.sub("[當事人]", masked)


def make_snippet(text: str, max_chars: int = 150) -> str:
    """Strip tags, mask private names and cut to max_chars."""
    if not text:
        return ""
    cleaned = html.unescape(TAG_RE.sub("", text))
    cleaned = mask_private_person(cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def _ymd(y: int, m: int, d: int) -> str:
    return datetime(y, m, d).strftime("%Y-%m-%d")


def find_date(text: str):
    """Return the first date in text as YYYY-MM-DD, or None."""
    m = DATE_FIND_RE.search(text or "")
    if not m:
        return None
    try:
        if m.group(1):
            return _ymd(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return _ymd(int(m.group(4)) + 1911, int(m.group(5)), int(m.group(6)))
    except ValueError:
        return None


def parse_date(date_str: str) -> str:
    """Normalize RFC 2822, ISO 8601, Gregorian or ROC dates to YYYY-MM-DD (UTC+8)."""
    if not date_str or not date_str.strip():
        raise ValueError("Empty date string")
    s = date_str.strip()

    if re.search(r"[A-Za-z]{3},", s) or "GMT" in s or "UTC" in s:
        dt = email.utils.parsedate_to_datetime(s)
        return dt.astimezone(TZ_TW).strftime("%Y-%m-%d")

    m = ROC_RE.match(s)
    if m:
        y = int(m.group(1))
        if y < 1900:
            y += 1911
        return _ymd(y, int(m.group(2)), int(m.group(3)))

    s_norm = s.replace("/", "-")
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s_norm):
        y, mo, d = (int(x) for x in s_norm.split("-"))
        return _ymd(y, mo, d)
    if " " in s_norm and "T" not in s_norm:
        a, b = s_norm.split(" ", 1)
        s_norm = a + "T" + b
    dt = datetime.fromisoformat(s_norm)
    if dt.tzinfo:
        dt = dt.astimezone(TZ_TW)
    return dt.strftime("%Y-%m-%d")


def is_date_in_range(pub_date: str, since: str, until: str) -> bool:
    return since <= pub_date <= until
