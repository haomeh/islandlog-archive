#!/usr/bin/env python3
"""System topics (R63, R64, R65): form, name and group a topic from crawled items.

Rules:
- The topic key is picked from the seed titles, not written by hand. Candidates are
  CJK n-grams of 3 to 8 characters. The key covers the most seed titles. On a tie it has
  the larger document frequency (more recall), then the longer text. A phrase in more than
  GENERIC_DF_SHARE of all items is generic and never a key. A second key is added when
  KEY2_SHARE or more of the seed titles do not contain the first key.
- The topic title is the key. The jurisdiction name goes in front when the key has no
  place name and the topic has exactly one local jurisdiction.
- Members: items whose title has a key and whose date is in [first seed - WINDOW_BEFORE,
  last seed + WINDOW_AFTER].
- Kinds: official_statement and official_record are "official" (timeline only, CI-25).
  fact_check is "clarification". A news title with a clarification word is "clarification".
  A news title or quote that cites a social post is "post". Other news is "report".
- Same content (cluster.same_content) of the same kind joins one group. A newspaper copy
  (/paper/ URL) joins an earlier group of the same kind within PAPER_DAYS when its bigrams
  overlap PAPER_OVERLAP of its own set.
- Stations: the first day, each day with a clarification, post or official item, then the
  busiest report days, up to MAX_STATIONS. A station title is a neutral count.
"""

import hashlib
import json
import math
import re
import sys
import unicodedata
import urllib.parse
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from tools.newsfetch.article import LTN_SECTIONS
from tools.newsfetch.cluster import bigrams, normalize_title, same_content
from tools.newsfetch.topic_config import (
    ANCHOR_CORE_MIN, ANCHOR_MAX_DF, BAND, COMPANION_LIFT, COMPANION_MIN, COMPANION_SHARE, DOMINANT_SHARE, EXTEND_DF_SHARE,
    GENERIC_BURST, GENERIC_DF_MIN, GENERIC_DF_SHARE, KEY2_MIN_COVER, KEY2_MIN_COVER_SHARE, KEY2_SHARE, LOCAL_ANCHOR_MIN,
    CONTROVERSY_MIN_ACTORS, DISPLAY_FORM_MIN_COUNT, LOCAL_ANCHOR_SHARE, ONE_ISSUE_MIN_CORE, ONE_ISSUE_SHARE, PLACE_FILTER_DF,
    POOL_COVER_SHARE, RARE_KEY_MIN_LEN, SHORT_KEY_LEN,
    PAPER_DAYS, PAPER_OVERLAP, RARE_KEY_SHARE, SECOND_ANCHOR_MAX_DF, SECOND_ANCHOR_MAX_LEN, SECOND_ANCHOR_MIN, SECOND_ANCHOR_MIN_LEN,
    SECOND_ANCHOR_MIN_SEEDS,
    SECOND_ANCHOR_SHARE, SPECIFIC_KEY_MIN, SPECIFIC_KEY_SHARE, TOP_COVER_SHARE, WINDOW_AFTER, WINDOW_BEFORE)

CAPTION = re.compile(r"圖擷自|擷取自|（圖|\(圖|圖／|翻攝|資料照|提供）|攝）|攝影）")

MAX_STATIONS, MAX_REPORT_MEMBERS, MAX_GROUPS, MAX_OFFICIAL = 10, 8, 40, 15
CLAR = re.compile(r"澄清|駁斥|更正|嚴正|假訊息|不實|闢謠|否認|回應|說明|【錯誤】|【誤導】|【詐騙】")
POST = re.compile(r"臉書|PO文|PO出|發文|貼文|FB|IG|Threads|社群平台|直播|YouTube|曬出|曬")
PLACE = re.compile(r"[臺台]北|新北|桃園|[臺台]中|[臺台]南|高雄|基隆|新竹|苗栗|彰化|南投|雲林|嘉義|屏東|宜蘭|花蓮|[臺台]東|澎湖|金門|馬祖|連江|北市|中市|南市|高市|竹市|竹縣")
CJK_RUN = re.compile(r"[一-鿿]+")
# Government actors named in a title: local offices (LOCAL_GOV) and central bodies (CENTRAL: regex, actor id, name, type).
LOCAL_GOV = re.compile(r"市府|縣府|市政府|縣政府|市長|縣長|議會|議員|局長|衛生局|教育局|環保局|消防局|交通局|社會局|工務局|公園處|鄉公所|鎮公所|區公所")
CENTRAL = [  # regex, actor id, name, actor type
    (r"行政院|政院|卓揆", "ac-executive-yuan", "行政院", "gov_agency"),
    (r"立法院|立院|立委", "ac-legislative-yuan", "立法院", "legislature"),
    (r"總統府", "ac-office-of-the-president", "總統府", "gov_agency"),
    (r"監察院|監委", "ac-control-yuan", "監察院", "control_body"),
    (r"司法院", "ac-judicial-yuan", "司法院", "court"),
    (r"憲法法庭|大法官", "ac-constitutional-court", "憲法法庭", "court"),  # R141.5: the justices sit in the court
    (r"內政部|國土署", "ac-ministry-of-the-interior", "內政部", "gov_agency"),
    (r"警政署", "ac-national-police-agency", "內政部警政署", "gov_agency"),
    (r"消防署", "ac-national-fire-agency", "內政部消防署", "gov_agency"),
    (r"外交部", "ac-ministry-of-foreign-affairs", "外交部", "gov_agency"),
    (r"國防部|(?<![中美韓日俄英合])國軍", "ac-ministry-of-national-defense", "國防部", "gov_agency"),
    (r"財政部|國稅局", "ac-ministry-of-finance", "財政部", "gov_agency"),
    (r"教育部", "ac-ministry-of-education", "教育部", "gov_agency"),
    (r"法務部", "ac-ministry-of-justice", "法務部", "gov_agency"),
    (r"經濟部|能源署", "ac-ministry-of-economic-affairs", "經濟部", "gov_agency"),
    (r"交通部|公路局|觀光署|氣象署", "ac-ministry-of-transportation", "交通部", "gov_agency"),
    (r"勞動部|勞保|勞退", "ac-ministry-of-labor", "勞動部", "gov_agency"),
    (r"農業部|林保署|防檢署", "ac-ministry-of-agriculture", "農業部", "gov_agency"),
    (r"衛福部|衛生福利部|健保|國民年金|疾管署", "ac-ministry-of-health-and-welfare", "衛生福利部", "gov_agency"),
    (r"食藥署", "ac-taiwan-fda", "衛生福利部食品藥物管理署", "gov_agency"),
    (r"環境部", "ac-ministry-of-environment", "環境部", "gov_agency"),
    (r"文化部", "ac-ministry-of-culture", "文化部", "gov_agency"),
    (r"數發部|數位發展部", "ac-ministry-of-digital-affairs", "數位發展部", "gov_agency"),
    (r"陸委會", "ac-mainland-affairs-council", "大陸委員會", "gov_agency"),
    (r"海巡署|海委會", "ac-ocean-affairs-council", "海洋委員會", "gov_agency"),
    (r"中選會", "ac-central-election-commission", "中央選舉委員會", "gov_agency"),
    (r"金管會", "ac-financial-supervisory-commission", "金融監督管理委員會", "gov_agency"),
    (r"通傳會|NCC", "ac-national-communications-commission", "國家通訊傳播委員會", "gov_agency"),
    (r"國安局|國安會", "ac-national-security-bureau", "國家安全局", "gov_agency"),  # R112.4: 國安局 case
    (r"央行|中央銀行", "ac-central-bank", "中央銀行", "gov_agency"),
    (r"國科會", "ac-national-science-and-technology-council", "國家科學及技術委員會", "gov_agency"),
    (r"國發會", "ac-national-development-council", "國家發展委員會", "gov_agency"),
    (r"原民會", "ac-council-of-indigenous-peoples", "原住民族委員會", "gov_agency"),
    (r"客委會", "ac-hakka-affairs-council", "客家委員會", "gov_agency"),
    (r"公平會", "ac-fair-trade-commission", "公平交易委員會", "gov_agency"),
    (r"主計總處", "ac-dgbas", "行政院主計總處", "gov_agency"),
    (r"人事行政總處|人事總處", "ac-dgpa", "行政院人事行政總處", "gov_agency"),
]
REVIEW_REASON = "draft-review: 系統依爬取資料自動形成與命名，編輯尚未審閱。"
PUB_SLUG = {"自由時報": "ltn", "中央通訊社": "cna", "公視新聞網": "pts", "TVBS": "tvbs", "Newtalk": "newtalk",
            "風傳媒": "storm", "聯合新聞網": "udn", "MyGoPen": "mygopen", "台灣事實查核中心": "tfc",
            "ETtoday新聞雲": "ettoday", "中時新聞網": "chinatimes", "三立新聞網": "setn", "東森新聞": "ebc",
            "華視新聞": "cts", "鏡週刊": "mirrormedia"}
HOSTS = {
    "www.ey.gov.tw": ("行政院", "ac-executive-yuan", "ey"),
    "www.moi.gov.tw": ("內政部", "ac-ministry-of-the-interior", "moi"),
    "www.moea.gov.tw": ("經濟部", "ac-ministry-of-economic-affairs", "moea"),
    "www.moa.gov.tw": ("農業部", "ac-ministry-of-agriculture", "moa"),
    "www.mohw.gov.tw": ("衛生福利部", "ac-ministry-of-health-and-welfare", "mohw"),
    "www.fda.gov.tw": ("衛生福利部食品藥物管理署", "ac-taiwan-fda", "fda"),
    "www.mol.gov.tw": ("勞動部", "ac-ministry-of-labor", "mol"),
    "www.mof.gov.tw": ("財政部", "ac-ministry-of-finance", "mof"),
    "enews.moenv.gov.tw": ("環境部", "ac-ministry-of-environment", "moenv"),
    "www.mnd.gov.tw": ("國防部", "ac-ministry-of-national-defense", "mnd"),
    "www.edu.tw": ("教育部", "ac-ministry-of-education", "edu"),
    "www.tainan.gov.tw": ("臺南市政府", "ac-tainan-city-government", "tainan"),
    "www.kcg.gov.tw": ("高雄市政府", "ac-kaohsiung-city-government", "kcg"),
    "www.oac.gov.tw": ("海洋委員會", "ac-ocean-affairs-council", "oac"),
    "www.judicial.gov.tw": ("司法院", "ac-judicial-yuan", "judicial"),
}
# Titles with masked names, opinion columns and listicles are never used.
DROP = re.compile(r"\[[^\]]*\]|自由開講|自由廣場|自由日日shoot|社論|漫畫|黑熊學院|筆記本|觀點》|國際視野|一次看|懶人包|健康網》")


def _day(d):
    return date.fromisoformat(str(d))


def _grams(title):
    text = unicodedata.normalize("NFKC", title or "")
    out = set()
    for run in CJK_RUN.findall(text):
        for n in range(2, 9):
            for i in range(len(run) - n + 1):
                out.add(run[i:i + n])
    return out


def document_frequency(corpus):
    df = Counter()
    for it in corpus:
        df.update(_grams(it["title"]))
    return df


ALIASES = {"臺北市": ["北市"], "新北市": [], "桃園市": ["桃市"], "臺中市": ["中市"], "臺南市": ["南市"], "高雄市": ["高市"],
           "新竹市": ["竹市"], "新竹縣": ["竹縣"]}


NOUN_END = re.compile(r"(館|橋|湖|溪|案|場|爐|國中|國小|高中|大學|圓環|颱風|油|黨|粉|包|款|旗|風機|火災|工地|園區|設備|中毒|塵爆|堰塞湖|法|條例|計畫|預算)$")
VERB_END = re.compile(r"(質疑|閃過|閃|回應|轟|嗆|批|揭|喊|說|稱|放|指|籲|怒|痛斥|表示|曝|挨)$")
VERB_START = re.compile(r"^(放|揭|批|轟|嗆|喊|爆|曝|驚|遭|被|稱|指|要)")
SPEECH_AFTER = r"(?:[：:]|質疑|轟|批|表示|嗆|揭|喊|回應|稱|說|痛斥|怒|籲|指|示警|酸|曝|道歉)"
_FIGURES_PATH = Path(__file__).with_name("public_figures.json")
try:
    PUBLIC_FIGURES = tuple(json.load(open(_FIGURES_PATH, encoding="utf-8")).get("names", []))
except (OSError, ValueError):
    PUBLIC_FIGURES = ()


def _is_person_or_speaker(g, titles):
    """A phrase that names a person (public figure list) or a speaker in the seed titles is not a topic name."""
    if any(name in g for name in PUBLIC_FIGURES if len(name) >= 2):
        return True
    if 2 <= len(g) <= 3 and not NOUN_END.search(g):
        pattern = re.compile(re.escape(g) + SPEECH_AFTER)
        return sum(1 for t in titles if pattern.search(t)) >= 1
    return False


def _is_place(g):
    return bool(PLACE.fullmatch(g)) or bool(re.fullmatch(r"(?:" + PLACE.pattern + r")[市縣]?", g))


def window_frequency(corpus, lo, hi):
    """Document frequency of each n-gram among items dated in [lo, hi]."""
    dfw = Counter()
    for it in corpus:
        if lo <= _day(it["published_on"]) <= hi:
            dfw.update(_grams(it["title"]))
    return dfw


def pick_key(titles, df, total, exclude=(), min_cover=1, dfw=None):
    cover = Counter()
    for t in titles:
        cover.update(_grams(t))
    generic = max(GENERIC_DF_MIN, GENERIC_DF_SHARE * total)
    cands = [(g, c) for g, c in cover.items()
             if c >= min_cover and df.get(g, 0) <= generic and not any(g in e or e in g for e in exclude)
             and not _is_place(g) and not VERB_END.search(g) and not VERB_START.search(g)
             and not _is_person_or_speaker(g, titles)]
    n_titles = max(1, len(titles))
    pool = [(g, c) for g, c in cands if df.get(g, 0) <= BAND * c or c >= POOL_COVER_SHARE * n_titles]
    if not pool and not exclude:
        pool = cands
    if not pool:
        return ""
    dfw = dfw if dfw is not None else df

    def score(gc):
        g, c = gc
        burst = dfw.get(g, 0) / max(1, df.get(g, 0))  # share of all uses that fall in the topic window
        noun = 2.0 if NOUN_END.search(g) else 1.0
        return (c >= TOP_COVER_SHARE * n_titles, round(c * burst * noun, 6), dfw.get(g, 0), len(g))

    best = max(pool, key=score)[0]
    # A longer phrase that covers the same seeds and has a similar frequency is the real name.
    longer = [g for g, c in pool if best in g and g != best and c == cover[best]
              and df.get(g, 0) >= EXTEND_DF_SHARE * df.get(best, 0)]
    return max(longer, key=len) if longer else best



def display_name(key, titles):
    """The shown name of a topic. `titles` are the seed titles, oldest first (R69).

    A. A longer form with a noun ending that covers DOMINANT_SHARE of the key's titles (萬里溪 -> 萬里溪堰塞湖).
    B. A 2-character key takes a 4-character form from the oldest seed title, the topic origin (移工 -> 移工懷孕).
    C. A 2-character key takes its most common 4-character form (薔琵 -> 薔琵颱風).
    """
    with_key = [t for t in titles if key in t]
    cover = Counter()
    for t in with_key:
        cover.update(g for g in _grams(t) if key in g and g != key)
    # Rule A grows to the right only: a left extension can cut a place name (名間 -> 間焚化爐).
    noun = [(g, c) for g, c in cover.items() if g.startswith(key) and NOUN_END.search(g) and not VERB_START.search(g)
            and c >= DOMINANT_SHARE * max(1, len(with_key))]
    if noun:
        return max(noun, key=lambda gc: (gc[1], -len(gc[0])))[0]
    if len(key) > SHORT_KEY_LEN:
        return key
    ok = lambda g: len(g) == 4 and not VERB_END.search(g) and not VERB_START.search(g)
    for t in with_key[:1]:
        origin = [g for g in _grams(t) if key in g and ok(g)]
        if origin:
            return max(origin, key=lambda g: (cover[g], g.endswith(key), g.startswith(key)))
    forms = [(g, c) for g, c in cover.items() if ok(g) and c >= DISPLAY_FORM_MIN_COUNT]
    return max(forms, key=lambda gc: gc[1])[0] if forms else key


def topic_keys(seed_titles, df, total, dfw=None):
    k1 = pick_key(seed_titles, df, total, dfw=dfw)
    keys = [k1] if k1 else []
    rest = [t for t in seed_titles if k1 and k1 not in t]
    if rest and len(rest) >= KEY2_SHARE * len(seed_titles):
        k2 = pick_key(rest, df, total, exclude=keys, min_cover=max(KEY2_MIN_COVER, int(KEY2_MIN_COVER_SHARE * len(rest))), dfw=dfw)
        if k2:
            keys.append(k2)
    return keys


def _place_terms(names):
    out = []
    for n in names:
        base = n[:-1] if n[-1] in "市縣" else n
        out += [base, base.replace("臺", "台"), n, n.replace("臺", "台")] + ALIASES.get(n, [])
    return [t for t in dict.fromkeys(out) if t]


def topic_title(key, jurisdiction_names, national=False, generic=False):
    if len(jurisdiction_names) == 1 and not PLACE.search(key) and (generic or not national):
        return jurisdiction_names[0] + key
    return key


def members(seed, corpus, df):
    by_url = {it["url"]: it for it in corpus}
    seeds = [by_url[u] for u in seed["seed_urls"] if u in by_url]
    titles = [s["title"] for s in seeds]
    lo = min(_day(s["published_on"]) for s in seeds) - timedelta(days=WINDOW_BEFORE)
    hi = max(_day(s["published_on"]) for s in seeds) + timedelta(days=WINDOW_AFTER)
    keys = topic_keys(titles, df, len(corpus), dfw=window_frequency(corpus, lo, hi))
    seed["_keys"] = keys
    by_date = [s["title"] for s in sorted(seeds, key=lambda j: (j["published_on"], j["url"]))]
    seed["_name"] = display_name(keys[0], by_date) if keys else ""
    names = seed.get("jurisdiction_names", [])
    national = "jur-tw" in seed.get("jurisdiction_ids", [])
    dfw = window_frequency(corpus, lo, hi)
    burst = dfw.get(keys[0], 0) / max(1, df.get(keys[0], 0)) if keys else 1.0
    generic = (not national and len(names) == 1 and bool(keys) and df.get(keys[0], 0) > PLACE_FILTER_DF
               and burst < GENERIC_BURST and not PLACE.search(keys[0]))
    seed["_generic"] = generic
    places = _place_terms(names) if generic else []
    if generic:
        # Local anchors: short phrases in many seed titles that are rare in the corpus (for example 名間).
        cover = Counter()
        for t in titles:
            cover.update(g for g in _grams2(t))
        places += [g for g, c in cover.items() if c >= max(LOCAL_ANCHOR_MIN, LOCAL_ANCHOR_SHARE * len(titles)) and df.get(g, 0) <= PLACE_FILTER_DF
                   and not any(g in k for k in keys)]
    out, seen = [], set()
    for it in sorted(corpus, key=lambda j: (j["published_on"], j["url"])):
        if DROP.search(it["title"]) or not (lo <= _day(it["published_on"]) <= hi):
            continue
        if not any(k in it["title"] for k in keys):
            continue
        if places and not any(p in it["title"] for p in places):
            continue
        norm = normalize_title(it["title"])
        if norm in seen:
            continue
        seen.add(norm)
        out.append(it)
    return anchored(out, titles, keys, df, len(corpus))  # same key, other issue (好市多 opening vs fine appeal)


def _grams2(title):
    text = unicodedata.normalize("NFKC", title or "")
    return {run[i:i + 2] for run in CJK_RUN.findall(text) for i in range(len(run) - 1)}




def _stripped(title, keys):
    for k in keys:
        title = title.replace(k, " ")
    return title


def _rare_grams(title, keys, df):
    return {g for g in _grams(_stripped(title, keys)) if len(g) >= 2 and df.get(g, 0) <= ANCHOR_MAX_DF}


def anchor_terms(seed_titles, keys, df, total=0):
    """Words of the seed titles that tell the issue apart from other news with the same key (R63).
    An anchor has 2 or more characters, is not part of a key, and is rare in the corpus (at most
    ANCHOR_MAX_DF items). A common word such as 衛生局 or 出包 joins two issues; a rare word does not."""
    out = set()
    for t in seed_titles:
        out |= _rare_grams(t, keys, df)
    return out


RESPONSE_CLASSES = ("official_statement", "official_record", "fact_check")


def companion_terms(core, keys, df, total):
    """Round 3: {word: share of the core titles} for the words that the core titles share as a group. A common
    word such as 出包 is in a few core titles; a companion such as 通車 is in most of them and is rare in the
    corpus as a whole. A title with the key and a companion is on topic, even when it shares no rare word with a
    seed (淡江大橋5/12通車 卓揆：...)."""
    if not total or len(core) < COMPANION_MIN:
        return {}
    cover = Counter()
    for c in core:
        cover.update(g for g in _grams(_stripped(c["title"], keys)) if len(g) <= 4)
    need = max(COMPANION_MIN, COMPANION_SHARE * len(core))
    return {g: n / len(core) for g, n in cover.items() if n >= need and df.get(g, 0) / total * COMPANION_LIFT <= n / len(core)}


def is_response(item):
    """An official or fact-check title with a clarification word answers an issue (勞動部回應, 【錯誤】). It is not a new issue."""
    return item.get("source_class") in RESPONSE_CLASSES and bool(CLAR.search(item["title"]))


def is_place_key(key):
    return bool(re.fullmatch(r"[一-鿿]{1,3}[鄉鎮區里村]", key)) or _is_place(key)


def has_anchor(title, anchors):
    return any(a in title for a in anchors)


def second_anchors(seed_titles, keys, df, total=0):
    """R112.1: the words, places and government actors that the seed titles share besides the key. A member of the
    topic has a key and one of these. A word is in SECOND_ANCHOR_SHARE of the seed titles and is not generic; a
    place or an actor is in SECOND_ANCHOR_MIN seed titles. Empty when the seeds share nothing (then the key rules alone)."""
    stripped = [_stripped(t, keys) for t in seed_titles]
    shared = len(stripped) >= SECOND_ANCHOR_MIN_SEEDS  # a few seed titles show no shared word
    need = max(SECOND_ANCHOR_MIN, SECOND_ANCHOR_SHARE * len(stripped)) if shared else 1
    need_entity = SECOND_ANCHOR_MIN if shared else 1
    words, entities = Counter(), Counter()
    for t in stripped:
        words.update(g for g in _grams(t) if SECOND_ANCHOR_MIN_LEN <= len(g) <= SECOND_ANCHOR_MAX_LEN
                     and 0 < df.get(g, 0) <= SECOND_ANCHOR_MAX_DF)
        found = set(PLACE.findall(t)) | {m.group(0) for m in LOCAL_GOV.finditer(t)}
        found |= {m.group(0) for pattern, _, _, _ in CENTRAL for m in re.finditer(pattern, t)}
        entities.update(found)
    return {g for g, c in words.items() if c >= need} | {e for e, c in entities.items() if c >= need_entity}


def anchored(cands, seed_titles, keys, df, total=0):
    """The candidates (items with a key) that belong to the issue of the seeds.
    A key that is specific to one issue needs no rare anchor. A long key that is as rare as an anchor is specific too.
    Round 1: a candidate with a seed anchor is core. Round 2: a rare word in 2 or more core titles is a new
    anchor (A肝莓果 is in no seed title, but in two core titles). Round 3: a companion word of the core (see
    companion_terms) is an anchor too, and an official or fact-check response with the key answers the same issue.
    A seed title always stays. R112.1: every other member also has a second anchor of the seeds (second_anchors),
    a core word of round 2 or a companion word. The key alone never makes a member."""
    seeds = set(seed_titles)
    second = second_anchors(seed_titles, keys, df, total)

    def on_issue(found, extra=()):
        out = []
        for c in found:
            if c["title"] in seeds or is_response(c) or not second or has_anchor(c["title"], second) or has_anchor(c["title"], extra):
                out.append(c)
        return out

    if keys and df.get(keys[0], 0) and len(cands) >= SPECIFIC_KEY_MIN and len(cands) >= SPECIFIC_KEY_SHARE * df.get(keys[0], 0):
        return on_issue(cands, companion_terms(cands, keys, df, total))  # the key is not shared with other issues
    if keys and len(keys[0]) >= RARE_KEY_MIN_LEN and 0 < df.get(keys[0], 0) <= ANCHOR_MAX_DF \
            and len(cands) >= RARE_KEY_SHARE * df[keys[0]]:
        return on_issue(cands, companion_terms(cands, keys, df, total))
    first = anchor_terms(seed_titles, keys, df, total)
    if not first:
        return list(cands)
    core = [c for c in on_issue(cands) if c["title"] in seeds or has_anchor(c["title"], first)]
    cover = Counter()
    for c in core:
        cover.update(_rare_grams(c["title"], keys, df))
    anchors = first | {g for g, n in cover.items() if n >= ANCHOR_CORE_MIN}
    kept = [c for c in cands if c["title"] in seeds or has_anchor(c["title"], anchors)]
    companions = companion_terms(kept, keys, df, total)
    if len(kept) >= ONE_ISSUE_MIN_CORE and companions and max(companions.values()) >= ONE_ISSUE_SHARE and not is_place_key(keys[0]):
        return list(cands)  # the key names one story: every title with it is on topic (淡江大橋 + 通車). R112.1 does not apply: the companion word is the second anchor of the whole core
    return on_issue([c for c in cands if c["title"] in seeds
                     or is_response(c) or has_anchor(c["title"], anchors) or has_anchor(c["title"], companions)], companions)


def kind_of(it):
    cls = it.get("source_class", "news")
    if cls in ("official_statement", "official_record"):
        return "official"
    if cls == "fact_check" or CLAR.search(it["title"]):
        return "clarification"
    if POST.search(it["title"]) or POST.search(it.get("quote") or ""):
        return "post"
    return "report"


def _overlap(a, b):
    small = a if len(a) <= len(b) else b
    return len(a & b) / len(small) if small else 0.0


def group_items(items):
    groups = []
    for it in sorted(items, key=lambda j: (j["published_on"], "/paper/" in j["url"], j["url"])):
        kind = kind_of(it)
        target = None
        if kind != "official":
            for g in groups:
                if g["kind"] != kind:
                    continue
                rep = g["items"][0]
                if same_content(rep, it):
                    target = g
                    break
                if ("/paper/" in it["url"] and 0 <= (_day(it["published_on"]) - _day(rep["published_on"])).days <= PAPER_DAYS
                        and _overlap(bigrams(it["title"]), bigrams(rep["title"])) >= PAPER_OVERLAP
                        and len(bigrams(it["title"]) & bigrams(rep["title"])) / max(1, len(bigrams(it["title"]))) >= PAPER_OVERLAP):
                    target = g
                    break
        if target is None:
            target = {"kind": kind, "items": [], "urls": []}
            groups.append(target)
        target["items"].append(it)
        target["urls"].append(it["url"])
    return groups


def src_slug(it, actors_by_host):
    host = urllib.parse.urlparse(it["url"]).hostname or ""
    if it.get("source_class") in ("official_statement", "official_record") and host in actors_by_host:
        return actors_by_host[host][2]
    slug = PUB_SLUG.get(it.get("publisher"), "")
    if slug:
        return slug
    labels = [x for x in host.split(".") if x not in ("www", "m", "news", "com", "tw", "net", "org", "co", "gov")]
    return re.sub(r"[^a-z0-9]", "", labels[-1].lower()) if labels else "unknown"


def src_id(it, actors_by_host):
    h = hashlib.sha1(it["url"].encode()).hexdigest()[:8]
    return f"src-{it['published_on'].replace('-', '')}-{src_slug(it, actors_by_host)}-{h}"


def _stations(groups):
    days = sorted({g["items"][0]["published_on"] for g in groups})
    special = [d for d in days if any(g["items"][0]["published_on"] == d and g["kind"] != "report" for g in groups)]
    volume = Counter()
    for g in groups:
        if g["kind"] == "report":
            volume[g["items"][0]["published_on"]] += len(g["items"])
    chosen = [days[0]]
    for d in special + [d for d, _ in volume.most_common()]:
        if d not in chosen and len(chosen) < MAX_STATIONS:
            chosen.append(d)
    return sorted(chosen)


def _station_title(gs):
    c = Counter()
    for g in gs:
        c[g["kind"]] += len(g["items"])
    parts = []
    for kind, label in (("report", "則報導"), ("clarification", "則回應或澄清"), ("post", "則引述貼文"), ("official", "則官方發布")):
        if c[kind]:
            parts.append(f"{c[kind]} {label}")
    return "、".join(parts)


def build_event(seed, corpus, df, actors_by_host=HOSTS, items=None):
    """Builds one topic. `items` skips the member search when the caller already has the members
    (the full run); then `seed` must already hold `_keys` and `_name`."""
    if items is None:
        items = members(seed, corpus, df)
    groups = group_items([it for it in items
                          if it.get("source_class") not in ("official_statement", "official_record")
                          or (urllib.parse.urlparse(it["url"]).hostname or "") in actors_by_host])
    official = [g for g in groups if g["kind"] == "official"][:MAX_OFFICIAL]
    keep = [g for g in groups if g["kind"] in ("clarification", "post")][:MAX_GROUPS]
    reports = sorted([g for g in groups if g["kind"] == "report"], key=lambda g: -len(g["items"]))
    keep += reports[:max(0, MAX_GROUPS - len(keep))]
    groups = sorted(keep + official, key=lambda g: (g["items"][0]["published_on"], g["kind"]))
    for g in groups:
        g["items"] = g["items"][:MAX_REPORT_MEMBERS]
        g["urls"] = [it["url"] for it in g["items"]]
    stations = _stations(groups)
    by_station = {d: [] for d in stations}
    for g in groups:
        d = max(s for s in stations if s <= g["items"][0]["published_on"])
        by_station[d].append(g)
    used, timeline, news_groups, body = {}, [], [], []
    extra_actors = []
    for n, d in enumerate(stations, 1):
        gs = by_station[d]
        tl_id = f"tl-{n:02d}"
        official = [g["items"][0] for g in gs if g["kind"] == "official"]
        actor = None
        if official:
            actor = actors_by_host[urllib.parse.urlparse(official[0]["url"]).hostname][1]
            if actor not in [a for a, _ in seed.get("actors", [])] + extra_actors:
                extra_actors.append(actor)
        news = [g for g in gs if g["kind"] != "official"]
        tl_items = [g["items"][0] for g in news][:3]
        tl_items += [it for it in official if actors_by_host[urllib.parse.urlparse(it["url"]).hostname][1] == actor][:3]
        t = {"id": tl_id, "date": d, "date_precision": "day", "title": _station_title(gs)}
        if actor:
            t["attributed_to"] = actor
        # No lifecycle_stage: a stage needs an editor and a source (a vote, a ruling). Title words do not prove it.
        t["source_urls"] = [it["url"] for it in tl_items]
        timeline.append(t)
        for g in news:
            ng = {"timeline_id": tl_id, "kind": g["kind"], "title": g["items"][0]["title"],
                  "representative_url": g["urls"][0], "source_urls": list(g["urls"])}
            if g["kind"] == "clarification":
                rep = g["items"][0]
                ng["note"] = f"{rep['publisher']}的查核" if rep.get("source_class") == "fact_check" else "報導中的回應或澄清"
            news_groups.append(ng)
        for g in gs:
            for it in g["items"]:
                used[it["url"]] = it
        lines = []
        for g in gs:
            it = g["items"][0]
            if g["kind"] == "official":
                lines.append(f"{it['publisher']}發布「{it['title']}」 [@{src_id(it, actors_by_host)}]。")
            elif it.get("source_class") == "fact_check":
                lines.append(f"{it['publisher']}發布查核報告「{it['title']}」 [@{src_id(it, actors_by_host)}]。")
            else:
                lines.append(f"{it['publisher']}以「{it['title']}」為題報導 [@{src_id(it, actors_by_host)}]。")
        body.append(f"## {d}　{t['title']}\n\n" + "\n\n".join(lines))
    for n, g in enumerate(news_groups, 1):
        g["id"] = f"ng-{n:02d}"
    keys = seed["_keys"]
    news_items = [it for it in used.values() if it.get("source_class") == "news"]
    pubs = list(dict.fromkeys(it["publisher"] for it in news_items))
    first_rep = timeline[0]["source_urls"][0]
    span = stations[0] if stations[0] == stations[-1] else f"{stations[0]}至{stations[-1]}"
    summary = (f"{span}，{'、'.join(pubs[:3])}{'等' if len(pubs) > 3 else ''}共 {len(news_items)} 則報導"
               f"提及{seed['_name']} [@{src_id(used[first_rep], actors_by_host)}]。")
    offs = [it for it in used.values() if it.get("source_class") in ("official_statement", "official_record")]
    if offs:
        summary += f"{offs[0]['publisher']}等機關發布 {len(offs)} 則相關說明 [@{src_id(offs[0], actors_by_host)}]。"
    actors = list(seed.get("actors", [])) + [(a, "other") for a in extra_actors]
    positions = [{"id": f"pos-{i:02d}", "question_id": "q-01", "actor_id": a, "stance": "not_found"}
                 for i, (a, r) in enumerate([x for x in actors if x[1] in ("decision_maker", "proposer", "opponent", "supporter")], 1)]
    return {
        "id": seed["event_id"],
        "title": topic_title(seed["_name"], seed.get("jurisdiction_names", []), national="jur-tw" in seed.get("jurisdiction_ids", []),
                             generic=seed.get("_generic", False)),
        "summary": summary, "start_date": stations[0], "keys": keys,
        "actors": actors, "question": f"{seed['_name']}的經過與各方說明為何？", "positions": positions,
        "timeline": timeline, "news_groups": news_groups, "body": body, "used": used,
        "review": {"sensitive": bool(seed.get("sensitive")), "reason": REVIEW_REASON, "status": "draft-review"},
    }


_TERMS_PATH = Path(__file__).resolve().parents[2] / "taxonomy" / "sensitive_terms.yaml"
try:
    SENSITIVE_TERMS = tuple(t.strip() for t in re.findall(r"term: ([^,}]+)", _TERMS_PATH.read_text(encoding="utf-8")))
except OSError:
    SENSITIVE_TERMS = ()


# The same benign phrases as the server CI-15 rule (server pkg/archive/rules.go, benignSensitiveRe).
BENIGN_SENSITIVE = re.compile(r"(?:全面|徹底|重新|通盤)體檢|就醫(?:需求|不便|便利|時間|管道|資訊)")


def has_sensitive_term(texts):
    """R76: a sensitive term in a source title or a source quote makes the event sensitive (CI-15).
    A benign phrase (全面體檢, 就醫需求) is removed first, as the server does."""
    return any(term in BENIGN_SENSITIVE.sub("", t) for t in texts if t for term in SENSITIVE_TERMS)


def event_kind(positions):
    """R73: controversy needs real stances from 2 or more actors (PRD 4.4 item 3). Else historical_event."""
    actors = {p["actor_id"] for p in positions if p.get("stance") not in (None, "not_found")}
    return "controversy" if len(actors) >= CONTROVERSY_MIN_ACTORS else "historical_event"


def _dump(doc):
    import yaml  # the writer needs PyYAML; the topic rules above do not
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000, default_flow_style=False)


def _source_doc(it, enrich, actors_by_host):
    cls = it.get("source_class", "news")
    d = {"schema_version": 1, "id": src_id(it, actors_by_host), "source_class": cls,
         "grade": "B" if cls == "official_statement" else "C", "title": it["title"]}
    host = urllib.parse.urlparse(it["url"]).hostname or ""
    if cls == "official_statement":
        d["publisher"], d["publisher_actor_id"] = actors_by_host[host][0], actors_by_host[host][1]
    else:
        d["publisher"] = it["publisher"]
    e = enrich.get(it["url"], {})
    quote = e.get("quote") or ""
    if not quote or CAPTION.search(quote):
        quote = it["title"]
    d.update({"url": it["url"], "published_on": it["published_on"], "accessed_on": "2026-10-25",
              "has_archive_url": False, "quote": quote[:150]})
    section = LTN_SECTIONS.get(e.get("section", ""), e.get("section", ""))
    if section and not re.fullmatch(r"[A-Za-z]+", section):
        d["section"] = section[:40]
    if e.get("byline"):
        d["byline"] = e["byline"][:80]
    d["license"] = "unknown"
    return d


REMOVED_SOURCES = Path(__file__).with_name("removed_sources.json")


def load_removed_sources(path=None):
    """{source id: entry} of the sources that a ruling removed (R256). Each entry has id, ruling and reason.
    Every path that reads or writes sources/ uses this loader (R261.2c)."""
    entries = {}
    for e in json.loads(Path(path or REMOVED_SOURCES).read_text(encoding="utf-8"))["sources"]:
        if not all(str(e.get(k, "")).strip() for k in ("id", "ruling", "reason")):
            raise ValueError(f"removed source entry needs id, ruling and reason: {e}")
        if e["id"] in entries:
            raise ValueError(f"removed source id is listed twice: {e['id']}")
        entries[e["id"]] = e
    return entries


def write_event(ev, seed, root, enrich, actors_by_host=HOSTS, overwrite_sources=True):
    removed = load_removed_sources()  # R261.2b: a removed source gets no file and no link
    cited = sorted(i for i in (src_id(it, actors_by_host) for it in ev["used"].values()) if i in removed)
    if cited:
        raise ValueError(f"the event cites a source that a ruling removed (R256): {cited}")
    sid = lambda u: src_id(ev["used"][u], actors_by_host)
    timeline = []
    for t in ev["timeline"]:
        t = dict(t)
        t["source_ids"] = [sid(u) for u in t.pop("source_urls")]
        timeline.append(t)
    groups = []
    for g in ev["news_groups"]:
        out = {"id": g["id"], "timeline_id": g["timeline_id"], "kind": g["kind"], "title": g["title"],
               "representative_source_id": sid(g["representative_url"]), "source_ids": [sid(u) for u in g["source_urls"]]}
        if g.get("note"):
            out["note"] = g["note"]
        groups.append(out)
    source_docs = [_source_doc(it, enrich, actors_by_host) for it in ev["used"].values()]
    review = dict(ev["review"])
    if has_sensitive_term([d["title"] for d in source_docs] + [d["quote"] for d in source_docs]):
        review["sensitive"] = True
    doc = {"schema_version": 1, "id": ev["id"], "kind": event_kind(ev["positions"]), "status": "published", "title": ev["title"],
           "summary": ev["summary"], "start_date": ev["start_date"], "start_date_precision": "day",
           "gov_levels": seed["gov_levels"], "jurisdiction_ids": seed["jurisdiction_ids"],
           "controversy_types": seed["controversy_types"], "policy_domains": seed["policy_domains"],
           "actors": [{"actor_id": a, "role": r} for a, r in ev["actors"]],
           "questions": [{"id": "q-01", "text": ev["question"]}], "positions": ev["positions"],
           "timeline": timeline, "news_groups": groups,
           "privacy": {"contains_private_persons": False, "basis_source_ids": []}, "review": review}
    root = Path(root)
    (root / "events/2026" / f"{ev['id']}.md").write_text("---\n" + _dump(doc) + "---\n\n" + "\n\n".join(ev["body"]) + "\n", encoding="utf-8")
    for it in ev["used"].values():
        target = root / "sources/2026" / f"{src_id(it, actors_by_host)}.yaml"
        if target.exists() and not overwrite_sources:
            continue  # keep the enriched copy that another event already cites
        target.write_text(_dump(_source_doc(it, enrich, actors_by_host)), encoding="utf-8")
    for a, _ in ev["actors"]:
        p = root / "actors" / f"{a}.md"
        if p.exists():
            continue
        name = next((v[0] for v in actors_by_host.values() if v[1] == a), None)
        if not name:
            raise SystemExit(f"missing actor file and definition: {a}")
        jur = {"ac-tainan-city-government": "jur-67000000", "ac-kaohsiung-city-government": "jur-64000000"}.get(a, "jur-tw")
        p.write_text("---\n" + _dump({"schema_version": 1, "id": a, "name": name, "actor_type": "gov_agency", "jurisdiction_id": jur}) + "---\n", encoding="utf-8")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv):
    if len(argv) not in (4, 5):
        print("usage: python3 -m tools.newsfetch.topics corpus.jsonl topic_seeds.json archive_root [enrich.jsonl]", file=sys.stderr)
        return 2
    removed = load_removed_sources()
    corpus = [it for it in read_jsonl(argv[1]) if src_id(it, HOSTS) not in removed]  # R256: a removed source never comes back
    seeds = json.load(open(argv[2], encoding="utf-8"))
    enrich = {e["url"]: e for e in read_jsonl(argv[4]) if e.get("status") == "ok"} if len(argv) == 5 else {}
    df = document_frequency(corpus)
    for seed in seeds:
        seed["actors"] = [tuple(a) for a in seed["actors"]]
        ev = build_event(seed, corpus, df)
        write_event(ev, seed, argv[3], enrich)
        kinds = Counter(g["kind"] for g in ev["news_groups"])
        print(f"{ev['id']}: {ev['title']} keys={ev['keys']} sources={len(ev['used'])} stations={len(ev['timeline'])} groups={dict(kinds)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
