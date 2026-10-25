#!/usr/bin/env python3
"""Full topic run (R68): form topics from all clusters and write only those that meet PRD 4.4.

Usage: python3 -m tools.newsfetch.topics_full corpus.jsonl clusters.json topic_seeds.json archive_root report.json

Steps:
1. Seeds: clusters with 2 or more items, or with an official or fact-check item. One-item news
   clusters stay candidates in the crawler output.
2. Each seed gets a key (topics.pick_key) with a month-bucket window frequency. Seeds with the
   same key and overlapping windows merge into one topic.
3. A topic that shares SAME_EVENT_SHARE of its members with a published event is skipped.
4. Jurisdictions come from place names in the member titles. Government actors come from agency
   names in the titles and from official sources (PRD 4.4 item 1).
5. Publish only when PRD 4.4 item 2 holds (1 grade A source, or grade C sources from 2 or more
   publishers) and no PRD 4.5 exclusion applies (sensitive, criminal case, election campaign,
   entertainment). Every published topic has review.status draft-review (R64).
"""

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools.newsfetch import topics as tp
from tools.newsfetch.topic_config import (
    BOUNDARY_SHARE, CLASSIFY_SHARE, CONCENTRATION, CONTINUATION_SHARE, EXCLUDE_SHARE, JURISDICTION_SHARE,
    CONTINUATION_MIN_USES, DISEASE_NAME_MAX_LEN, FOREIGN_NAMED_SHARE, GENERIC_NAME_MAX_LEN, GOV_NAME_SHARE, MERGE_OVERLAP, MIN_KEY_LEN, NEWS_RULE_MIN_ITEMS, NEWS_RULE_MIN_PUBLISHERS, QUOTED_SLOGAN_SHARE,
    RELEVANCE_SHARE, SAME_EVENT_SHARE, SEED_MIN_ITEMS, SOURCE_RULE_MIN_PUBLISHERS, SPLIT_MIN_TITLES, SUBTOPIC_SHARE,
    WITHDRAW_AFTER_FAILS)

TOPIC_FILE = re.compile(r"^ev-\d{8}-topic-[0-9a-f]{8}\.md$")
ELECTION = re.compile(r"參選|選情|民調|競選|拜票|提名|初選|選戰|輔選|候選人|號次|造勢|催票|對手陣營|競辦|競總")  # R106: the last 3 name a campaign without an election word
CRIME = re.compile(r"起訴|判刑|聲押|收押|交保|嫌犯|涉嫌|偵辦|逮捕|送辦|殺人|命案|毒品|詐團|車手|性侵|猥褻|竊盜|酒駕|弊案|收賄|貪污|貪瀆|行賄|賄賂|洩題")  # R112.3: the last 7 name a corruption case
ENTERTAINMENT = re.compile(r"演唱會|歌手|藝人|女星|男星|偶像|專輯|戲劇|影集|綜藝|中職|球隊|選手|奪冠|賽事|電影")
ELECTION_LEGAL = re.compile(r"駁回|裁定|判決|高行|行政法院|法院|當選無效|選舉訴訟")  # R112.4: a court ruling on a candidacy is not campaign content
LAW_PASSED = re.compile(r"三讀|條例》|修正草案|修法")  # R112.4: a law passed by the legislature is not sensitive by its subject alone
CONSUMER = re.compile(r"優惠|折扣|現省|省[\d百千萬]|半價|折抵|票價|抵用|買一送一")  # R112.5: a discount is a consumer title, not entertainment news
FOREIGN_ONLY = re.compile(r"美國|川普|中國|大陸|日本|南韓|北韓|俄羅斯|烏克蘭|伊朗|以色列|歐盟|英國|德國|法國|印度|菲律賓|越南|泰國|馬來西亞")

JURS = [  # id, government actor id, actor name, place terms
    ("jur-63000000", "ac-taipei-city-government", "臺北市政府", ["臺北市", "台北市", "北市", "臺北", "台北"]),
    ("jur-65000000", "ac-new-taipei-city-government", "新北市政府", ["新北"]),
    ("jur-68000000", "ac-taoyuan-city-government", "桃園市政府", ["桃園", "桃市"]),
    ("jur-66000000", "ac-taichung-city-government", "臺中市政府", ["臺中", "台中", "中市"]),
    ("jur-67000000", "ac-tainan-city-government", "臺南市政府", ["臺南", "台南", "南市"]),
    ("jur-64000000", "ac-kaohsiung-city-government", "高雄市政府", ["高雄", "高市"]),
    ("jur-10017000", "ac-keelung-city-government", "基隆市政府", ["基隆"]),
    ("jur-10018000", "ac-hsinchu-city-government", "新竹市政府", ["新竹市", "竹市"]),
    ("jur-10004000", "ac-hsinchu-county-government", "新竹縣政府", ["新竹縣", "竹縣", "竹北"]),
    ("jur-10005000", "ac-miaoli-county-government", "苗栗縣政府", ["苗栗"]),
    ("jur-10007000", "ac-changhua-county-government", "彰化縣政府", ["彰化"]),
    ("jur-10008000", "ac-nantou-county-government", "南投縣政府", ["南投"]),
    ("jur-10009000", "ac-yunlin-county-government", "雲林縣政府", ["雲林"]),
    ("jur-10020000", "ac-chiayi-city-government", "嘉義市政府", ["嘉義市", "嘉市"]),
    ("jur-10010000", "ac-chiayi-county-government", "嘉義縣政府", ["嘉義縣", "嘉縣"]),
    ("jur-10013000", "ac-pingtung-county-government", "屏東縣政府", ["屏東", "恆春"]),
    ("jur-10002000", "ac-yilan-county-government", "宜蘭縣政府", ["宜蘭"]),
    ("jur-10015000", "ac-hualien-county-government", "花蓮縣政府", ["花蓮"]),
    ("jur-10014000", "ac-taitung-county-government", "臺東縣政府", ["臺東", "台東"]),
    ("jur-10016000", "ac-penghu-county-government", "澎湖縣政府", ["澎湖"]),
    ("jur-09020000", "ac-kinmen-county-government", "金門縣政府", ["金門"]),
    ("jur-09007000", "ac-lienchiang-county-government", "連江縣政府", ["連江", "馬祖"]),
]
LOCAL_GOV = tp.LOCAL_GOV  # R112.1: the actor lists live in topics.py, where the topic members use them
CENTRAL = tp.CENTRAL
CTYPES = [
    (r"預算|補助|統籌|刪減|凍結", "budget"), (r"修法|三讀|草案|條例|立法", "legislation"),
    (r"環評|污染|汙染|焚化|廢棄物|空污|排放|砍樹|路樹|行道樹", "environment"),
    (r"假訊息|謠言|【錯誤】|【誤導】|不實|造謠|詐騙", "information"),
    (r"中國|共諜|統戰|國台辦|共軍|中共", "cross_strait_foreign"),
    (r"工程|道路|橋|捷運|施工|天坑", "public_works"), (r"都更|徵收|土地|開發案", "land_development"),
    (r"食安|致癌|中毒|火災|火警|颱風|地震|事故|爆炸|堰塞|豪雨|淹水|停電", "public_safety"),
]
DOMAINS = [
    (r"衛福|食藥|醫|食安|油品|中毒|疫苗|健保|長照", "health_welfare"), (r"環境部|環評|污染|空污|廢棄物|焚化|路樹|行道樹", "environment"),
    (r"交通|公路|捷運|台鐵|高鐵|航班|機場|橋", "transport"), (r"勞動|勞工|移工|工資", "labor"),
    (r"教育|學校|國中|國小|高中|大學|午餐", "education"), (r"國防|國軍|共軍|軍購", "defense"),
    (r"陸委|國台辦|兩岸", "mainland_affairs"), (r"外交", "foreign_affairs"), (r"電價|能源|光電|風電|台電|經濟部", "economy_energy"),
    (r"農業|農民|漁", "agriculture"), (r"財政|稅|統籌", "finance"), (r"文化|藝文", "culture"),
]


BAD_START = set("的了在要是將再也與和及自幫今明昨業生發釀拚遠臨被遭讓把對向從為就都還又才更最很不沒")
BAD_END = set("的了在要是將再也與和及來去停買說稱指喊轟嗆批揭爆曝挨全不能會讓把被遭向從為到等")
BAD_WORDS = re.compile(r"不能|不會|今晚|今天|明天|昨天|這樣|那樣|如何|為何|什麼|怎麼|市長|縣長|議員|闢謠|論壇|會議紀錄|警戒")


def extend_to_boundary(key, titles):
    """Adds a neighbor character while BOUNDARY_SHARE of the uses share it (脫大稽查 -> 密室逃脫大稽查)."""
    for _ in range(6):
        left, right, n = Counter(), Counter(), 0
        for t in titles:
            i = t.find(key)
            while i >= 0:
                n += 1
                if i > 0:
                    left[t[i - 1]] += 1
                if i + len(key) < len(t):
                    right[t[i + len(key)]] += 1
                i = t.find(key, i + 1)
        grown = False
        for side, counter in (("l", left), ("r", right)):
            if not counter or n == 0:
                continue
            ch, c = counter.most_common(1)[0]
            if c >= BOUNDARY_SHARE * n and tp.CJK_RUN.fullmatch(ch):
                key = ch + key if side == "l" else key + ch
                grown = True
                break
        if not grown:
            break
    return key


PARTIES = re.compile(r"國民黨|民進黨|民眾黨|時代力量|時力|台灣基進|親民黨|新黨|綠黨|民主黨|共和黨|共產黨")

NOUN_HEAD = re.compile(tp.NOUN_END.pattern[:-2] + r"|卡|船|節|假|課|宅|站|區|鎮|鄉|港|島|祭|價|費|稅|證|照|險|車|機|路|樹|所|室|廠|署|局|院|會|商場|中心)$")


def has_word_boundary(key, titles, df=None):
    """A key is a fragment when its next (or previous) character is one of at most 3 characters in
    CONTINUATION_SHARE of its uses (降速演 -> 習 or 練; 辦理退 -> 稅 or 費). A noun head ends a whole word."""
    noun = bool(NOUN_HEAD.search(key))
    left, right, n = Counter(), Counter(), 0
    for t in titles:
        i = t.find(key)
        while i >= 0:
            n += 1
            if i > 0 and tp.CJK_RUN.fullmatch(t[i - 1]):
                left[t[i - 1]] += 1
            j = i + len(key)
            if j < len(t) and tp.CJK_RUN.fullmatch(t[j]):
                right[t[j]] += 1
            i = t.find(key, i + 1)
    if n < CONTINUATION_MIN_USES:
        return True
    sides = (left,) if noun else (left, right)  # a noun head ends the word on the right side only
    for side in sides:
        if sum(c for _, c in side.most_common(3)) >= CONTINUATION_SHARE * n:
            return False
    return True


def is_quoted_slogan(key, titles):
    """A key that sits inside 「」 in half of its uses is a quote or a slogan, not a name."""
    inside = n = 0
    for t in titles:
        for m in re.finditer(re.escape(key), t):
            n += 1
            before = t[:m.start()]
            if before.count("「") > before.count("」"):
                inside += 1
    return n > 0 and inside >= QUOTED_SLOGAN_SHARE * n


def is_place_name(key):
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{1,3}[鄉鎮區里村]", key)) or tp._is_place(key)


def is_person_or_party(key, titles):
    return bool(PARTIES.search(key)) or tp._is_person_or_speaker(key, titles) or bool(re.search(r"議長|議員|市長|縣長|立委|部長", key))


POLICY_NOUN = re.compile(r"平台|補助|獎助|津貼|警示|示警|預算|條例|辦法|方案|計畫|政策|草案|新制|制度|專案|給付|基金")  # R112.4
PLACE_PREFIX = re.compile(r"^(?:" + tp.PLACE.pattern + r")[市縣]?")
PLACE_ONLY = re.compile(PLACE_PREFIX.pattern + r"(?:[\u4e00-\u9fff]{1,3}[區鄉鎮里村市])?")
DISEASE_END = re.compile(r"(癌|腫瘤|症|病|炎|瘟|流感|感染)$")
OBJECT_HEAD = re.compile(r"(船|艦|車|機|棚|袋|箱)$")  # a bare object type: 巡視船, 豎孤棚


def generic_name(name):
    """R112.2: a name that is only a place, only a disease or only a generic object. A named facility (淡江大橋,
    金華國中) has a proper name before its head and is not generic. The schema has no place event kind, so the
    named facility is the exception for a place."""
    if PLACE_ONLY.fullmatch(name):
        return True
    rest = PLACE_PREFIX.sub("", name, count=1)
    if rest != name and len(rest) <= GENERIC_NAME_MAX_LEN:
        return True  # a jurisdiction and a few characters (屏東縣豎孤棚)
    if DISEASE_END.search(name) and len(name) <= DISEASE_NAME_MAX_LEN and not POLICY_NOUN.search(name):
        return True
    return len(name) <= GENERIC_NAME_MAX_LEN and bool(OBJECT_HEAD.search(name))


def names_government(title):
    return bool(LOCAL_GOV.search(title) or any(re.search(p, title) for p, _, _, _ in CENTRAL))


def names_foreign(titles):
    """R112.5: a topic is foreign when FOREIGN_NAMED_SHARE of its titles names a foreign country or leader."""
    return sum(1 for t in titles if FOREIGN_ONLY.search(t)) >= FOREIGN_NAMED_SHARE * max(1, len(titles))


def name_quality_ok(key, titles, total_df, window_df, df=None):
    """The name gates of the full run. R112.2: only a place, a disease or a generic object fails. R112.4: a key with
    a policy noun, or a key whose titles name a government body in GOV_NAME_SHARE, skips the quote and word-start tests;
    a key with a policy noun skips the word-boundary test too."""
    if not noun_phrase_name(key) or generic_name(key) or is_person_or_party(key, titles) or is_place_name(key):
        return False
    policy_key = bool(POLICY_NOUN.search(key))
    policy_titles = sum(1 for t in titles if names_government(t)) >= GOV_NAME_SHARE * max(1, len(titles))
    if not name_ok(key, total_df, window_df, loose=policy_key or policy_titles):
        return False
    if policy_key:
        return True
    if not has_word_boundary(key, titles, df):
        return False
    return policy_titles or not is_quoted_slogan(key, titles)


NATIONAL_SYSTEMS = re.compile(r"健保|勞保|勞退|國民年金|國保|公保|軍保|長照|衛福部|衛生福利部|健保署|勞保局|勞動部|國人")  # R84
SPEECH_END = re.compile(r"(表示|指出|在場|回應|強調|認為|透露|坦言|[說稱])$")  # R85
ROLE_FRAGMENT = re.compile(r"(高層|高官|幕僚|官員|人士|發言人)$")


def noun_phrase_name(name):
    """R85: a topic name is a noun phrase. A speech or sentence predicate at the end, or a person-role fragment, fails."""
    return not (SPEECH_END.search(name) or ROLE_FRAGMENT.search(name))


def pick_noun_key(titles, df, total, dfw=None):
    """The best key whose name is a noun phrase (R85). A rejected candidate and its overlaps are left out and the next
    candidate is tried. Returns an empty string when no candidate passes."""
    tried = []
    while True:
        key = tp.pick_key(titles, df, total, exclude=tuple(tried), dfw=dfw)
        if not key or noun_phrase_name(key):
            return key
        tried.append(key)


def taiwan_relevant(titles):
    n = max(1, len(titles))
    hits = 0
    for t in titles:
        if any(term in t for _, _, _, terms in JURS for term in terms) or LOCAL_GOV.search(t) \
                or any(re.search(p, t) for p, _, _, _ in CENTRAL) or NATIONAL_SYSTEMS.search(t) or re.search(r"台灣|臺灣|全台|國人", t):
            hits += 1
    return hits >= RELEVANCE_SHARE * n


def name_ok(key, total_df, window_df, loose=False):
    """`loose` (R112.4) skips the word-start and word-end tests for a policy name."""
    if len(key) < MIN_KEY_LEN or BAD_WORDS.search(key) or (not loose and (key[0] in BAD_START or key[-1] in BAD_END)):
        return False
    return total_df <= CONCENTRATION * max(1, window_df)


has_sensitive_term = tp.has_sensitive_term


def _day(d):
    return date.fromisoformat(str(d))


def meets_source_rule(items):
    """PRD 4.4 item 2: 1 grade A source, or grade C sources from 2 or more publishers."""
    if any(it.get("source_class") in ("official_record",) for it in items):
        return True
    pubs = {it["publisher"] for it in items if it.get("source_class") in ("news", "fact_check")}
    return len(pubs) >= SOURCE_RULE_MIN_PUBLISHERS


PLACE_FIXES = (("台北港", "新北港"), ("臺北港", "新北港"))  # 台北港 is in 新北市


def meets_news_rule(items):
    """R73: 2 or more news items from 2 or more news publishers (fact checks and official releases do not count)."""
    news = [it for it in items if it.get("source_class") == "news"]
    return len(news) >= NEWS_RULE_MIN_ITEMS and len({it["publisher"] for it in news}) >= NEWS_RULE_MIN_PUBLISHERS



def link_subtopics(entries):
    """R72: {child id: parent id}. The child window lies inside an older topic window, the child is in the same
    jurisdiction or a child of it (every county is a child of jur-tw), and SUBTOPIC_SHARE of its titles have the
    older topic key."""
    links = {}
    for c in entries:
        best = None
        for p in entries:
            if p["id"] == c["id"] or not (p["start"] <= c["start"] and c["end"] <= p["end"]):
                continue
            if (p["start"], p["end"]) == (c["start"], c["end"]):
                continue
            if not (set(c["jurisdictions"]) <= set(p["jurisdictions"]) or "jur-tw" in p["jurisdictions"]):
                continue
            share = sum(1 for t in c["titles"] if p["key"] in t) / max(1, len(c["titles"]))
            if share >= SUBTOPIC_SHARE and (best is None or share > best[0]):
                best = (share, p["id"])
        if best:
            links[c["id"]] = best[1]
    return links


def _read_event(path):
    import yaml
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front), body


def _write_event(path, doc, body):
    import yaml
    path.write_text("---\n" + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000) + "---\n" + body,
                    encoding="utf-8")


def apply_subtopic_links(root, keys):
    """Builds the entries from the event files and writes relations: part_of into each child file."""
    root = Path(root)
    titles_by_src = {}
    for p in (root / "sources").glob("2026/*.yaml"):
        m = re.search(r'^title: "?(.+?)"?$', p.read_text(encoding="utf-8"), re.M)
        if m:
            titles_by_src[p.stem] = m.group(1)
    entries, files = [], {}
    for p in (root / "events" / "2026").glob("*.md"):
        doc, body = _read_event(p)
        if doc["id"] not in keys:
            continue
        dates = sorted(t["date"] for t in doc["timeline"])
        srcs = {s for g in doc.get("news_groups", []) for s in g["source_ids"]}
        entries.append({"id": doc["id"], "start": str(dates[0]), "end": str(dates[-1]), "jurisdictions": doc["jurisdiction_ids"],
                        "key": keys[doc["id"]], "titles": [titles_by_src[s] for s in srcs if s in titles_by_src]})
        files[doc["id"]] = (p, doc, body)
    links = link_subtopics(entries)
    for child, parent in links.items():
        p, doc, body = files[child]
        rels = [r for r in doc.get("relations", []) if r.get("type") != "part_of"]
        rels.append({"type": "part_of", "target_id": parent})
        new = {}
        for k, v in doc.items():
            if k == "privacy":
                new["relations"] = rels
            if k != "relations":
                new[k] = v
        _write_event(p, new, body)
    return links


def _title_jurisdictions(title):
    """The ids of the jurisdictions that a title names. 新北 is taken out first, so 新北市 does not name 北市."""
    for wrong, right in PLACE_FIXES:
        title = title.replace(wrong, right)
    plain = title.replace("新北", "\0")
    found = {jid for jid, _, _, terms in JURS if any(term in (title if jid == "jur-65000000" else plain) for term in terms)}
    return found


def _same_level(jid):
    return "special" if jid in SPECIAL_MUNICIPALITIES else "county_city"


SPECIAL_MUNICIPALITIES = ("jur-63000000", "jur-64000000", "jur-65000000", "jur-66000000", "jur-67000000", "jur-68000000")


def split_cases(members):
    """R112.3: the member lists of the topics that one candidate holds. A criminal-case title is another case than the
    other titles of the topic (PRD 4.5 excludes it); it leaves as its own list. Then titles that name two jurisdictions
    of the same level, each alone in SPLIT_MIN_TITLES titles or more, split by jurisdiction. A title with no
    jurisdiction stays with the biggest list. A topic of one case and one jurisdiction returns [members]."""
    crime = [m for m in members if CRIME.search(m["title"])]
    rest = [m for m in members if not CRIME.search(m["title"])]
    lists = [rest, crime] if crime and rest else [members]
    out = []
    for lst in lists:
        alone = {id(m): next(iter(j)) for m in lst for j in [_title_jurisdictions(m["title"])] if len(j) == 1}
        counts = Counter(alone.values())
        by_level = defaultdict(list)
        for jid, n in counts.most_common():
            if n >= SPLIT_MIN_TITLES:
                by_level[_same_level(jid)].append(jid)
        sides = next((js for js in by_level.values() if len(js) > 1), [])
        if not sides:
            out.append(lst)
            continue
        groups = {jid: [m for m in lst if alone.get(id(m)) == jid] for jid in sides}
        biggest = sides[0]
        groups[biggest] += [m for m in lst if alone.get(id(m)) not in sides]
        order = {id(m): i for i, m in enumerate(lst)}
        out += [sorted(g, key=lambda m: order[id(m)]) for g in groups.values()]
    return out


def detect_jurisdictions(titles):
    counts = Counter()
    for t in titles:
        for wrong, right in PLACE_FIXES:
            t = t.replace(wrong, right)
        for jid, _, _, terms in JURS:
            if any(term in t for term in terms):
                counts[jid] += 1
    local = [j for j, c in counts.most_common() if c >= max(1, JURISDICTION_SHARE * len(titles))]
    return local[:3] or ["jur-tw"]


def detect_gov_actors(titles, jurisdiction_ids):
    found = []
    for t in titles:
        for pattern, aid, _, _ in CENTRAL:
            if re.search(pattern, t) and aid not in found:
                found.append(aid)
        if LOCAL_GOV.search(t):
            for jid, aid, _, terms in JURS:
                if jid in jurisdiction_ids and aid not in found:
                    found.append(aid)
    return found


def exclusion_reason(items):
    n = max(1, len(items))
    shares = {
        "sensitive": sum(1 for it in items if it.get("sensitive") and not LAW_PASSED.search(it["title"])) / n,
        "election_campaign": sum(1 for it in items if ELECTION.search(it["title"]) and not ELECTION_LEGAL.search(it["title"])) / n,
        "criminal_case": sum(1 for it in items if CRIME.search(it["title"])) / n,
        "entertainment": sum(1 for it in items if ENTERTAINMENT.search(it["title"]) and not CONSUMER.search(it["title"])) / n,
    }
    has_official = any(it.get("source_class") in ("official_statement", "official_record") for it in items)
    for reason in ("sensitive", "criminal_case", "election_campaign", "entertainment"):
        if reason == "criminal_case" and has_official:
            continue
        if shares[reason] >= EXCLUDE_SHARE[reason]:
            return reason
    return None


def topic_id(key, first_day, first_url):
    h = hashlib.sha1(f"{key}|{first_url}".encode()).hexdigest()[:8]
    return f"ev-{first_day.replace('-', '')}-topic-{h}"


def published_topics(root, ref="HEAD"):
    """System topics that a commit already publishes: id, title, the first and last date and the cited source ids.
    The ids come from the git ref, so a rebuild can reuse them after the files are removed.
    Without git, the files in events/ are read."""
    import subprocess
    root = Path(root)
    texts = []
    try:
        names = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", ref, "events/"],
                               capture_output=True, text=True, check=True).stdout.split()
        for n in names:
            if re.search(r"/ev-\d{8}-topic-[0-9a-f]{8}\.md$", n):
                texts.append(subprocess.run(["git", "-C", str(root), "show", f"{ref}:{n}"],
                                            capture_output=True, text=True, check=True).stdout)
    except (OSError, subprocess.CalledProcessError):
        texts = [p.read_text(encoding="utf-8") for p in sorted((root / "events").glob("*/ev-*-topic-*.md"))]
    out = []
    for t in texts:
        i = re.search(r"^id: (\S+)$", t, re.M)
        title = re.search(r"^title: (.+)$", t, re.M)
        days = re.findall(r"^\s*(?:-\s+)?(?:date|start_date): '?(\d{4}-\d{2}-\d{2})", t, re.M)
        if i and title and days:
            out.append({"id": i.group(1), "title": title.group(1).strip("'\""), "first": min(days), "last": max(days),
                        "src_ids": set(re.findall(r"src-[0-9a-z-]+", t))})
    return out


def matching_published(published, src_ids):
    """Ids of the published system topics that keep at least MERGE_OVERLAP of their sources in src_ids."""
    return [p["id"] for p in published
            if p.get("src_ids") and len(src_ids & p["src_ids"]) >= MERGE_OVERLAP * len(p["src_ids"])]


WITHDRAW_RULE = "R82"
REPUBLISH_RULE = "R105"


def _correction_records(root):
    import yaml
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((Path(root) / "corrections").glob("*/cr-*.yaml"))]


def write_status_record(root, event_id, rtype, summary, rule_id, today, gate=None):
    """R86, R105: a status change of a published id writes a correction record made by the tool: the event, the
    date, the type (withdrawal or republication) and the rule. Every change writes a new record. Returns the id."""
    import yaml
    root = Path(root)
    records = _correction_records(root)
    stamp = today.replace("-", "")
    used = [int(r["id"][-2:]) for r in records if r["id"].startswith(f"cr-{stamp}-")]
    cid = f"cr-{stamp}-{max(used, default=0) + 1:02d}"
    doc = {"schema_version": 1, "id": cid, "target_ids": [event_id], "date": today, "type": rtype,
           "summary": summary, "made_by": "tool"}
    if gate:
        doc["gate"] = gate
    doc["rule_id"] = rule_id
    path = root / "corrections" / today[:4] / f"{cid}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    return cid


def write_withdrawal_record(root, event_id, gate, today):
    return write_status_record(root, event_id, "withdrawal", f"系統撤回事件：未通過 {gate}（{WITHDRAW_RULE}）。",
                               WITHDRAW_RULE, today, gate=gate)


def write_republication_record(root, event_id, today):
    return write_status_record(root, event_id, "republication", f"系統重新發布事件：已通過所有檢查（{REPUBLISH_RULE}）。",
                               REPUBLISH_RULE, today)


def _event_text(root, event_id, ref):
    """The event file text from the working tree, or from the git ref when the file is missing. None if neither exists."""
    import subprocess
    root = Path(root)
    year = event_id.split("-")[1][:4]
    path = root / "events" / year / f"{event_id}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    try:
        return subprocess.run(["git", "-C", str(root), "show", f"{ref}:events/{year}/{event_id}.md"],
                              capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def prior_event(root, event_id, ref="HEAD"):
    """R105: the status and correction ids of an event before a run rewrites it. (None, []) for a new event."""
    import yaml
    text = _event_text(root, event_id, ref)
    if text is None:
        return None, []
    front = yaml.safe_load(text.split("---\n", 2)[1])
    return front.get("status"), list(front.get("correction_ids", []))


def republish_topic(root, event_id, prior, today):
    """R105: after a full run rewrites an event, restore its correction ids. A topic that was withdrawn and is
    published again gets a republication record and a link to it. Returns the new record id or None."""
    root = Path(root)
    status, ids = prior
    path = root / "events" / event_id.split("-")[1][:4] / f"{event_id}.md"
    doc, body = _read_event(path)
    cid = None
    if status == "withdrawn":
        cid = write_republication_record(root, event_id, today)
        ids = ids + [cid]
    if ids:
        doc = _with_correction_ids(doc, ids)
        _write_event(path, doc, body)
    return cid


def _with_correction_ids(doc, ids):
    """The doc with correction_ids before `review` (the key order of the event files)."""
    new = {}
    for k, v in doc.items():
        if k == "review":
            new["correction_ids"] = ids
        if k != "correction_ids":
            new[k] = v
    new.setdefault("correction_ids", ids)
    return new


def withdraw_topic(root, event_id, gate, ref="HEAD", today=None):
    """R82: a published system topic that fails a gate keeps its file and id. It gets status withdrawn, the
    failed gate in review.reason and a link to its correction record (R86). A missing file is restored from the
    git ref first. A topic that is withdrawn already stays as it is and writes no new record (R105).
    Returns the file path."""
    root = Path(root)
    year = event_id.split("-")[1][:4]
    path = root / "events" / year / f"{event_id}.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_event_text(root, event_id, ref), encoding="utf-8")
    doc, body = _read_event(path)
    if doc.get("status") == "withdrawn":
        return path
    doc["status"] = "withdrawn"
    doc["review"]["reason"] = f"withdrawn: {gate}"
    cid = write_withdrawal_record(root, event_id, gate, today or date.today().isoformat())
    if cid not in doc.get("correction_ids", []):
        doc["correction_ids"] = doc.get("correction_ids", []) + [cid]
    _write_event(path, doc, body)
    return path


STATE_FILE = Path("tools") / "newsfetch" / "topic_state.json"


def read_topic_state(root):
    """R107b, R116: {event id: {"fails": consecutive failing days, "gate": the last failed gate, "day": the last counted day}}. Empty when no file exists."""
    path = Path(root) / STATE_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def write_topic_state(root, state):
    path = Path(root) / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


TAIPEI = timezone(timedelta(hours=8))  # Taiwan has no daylight saving time


def taipei_day(now=None):
    """R116: the calendar day in Asia/Taipei, as YYYY-MM-DD."""
    return (now or datetime.now(timezone.utc)).astimezone(TAIPEI).date().isoformat()


def apply_hysteresis(state, failed, day):
    """R107b, R116: adds 1 to the fail count of each failed topic and clears the count of every other topic. A topic
    gets at most one count per calendar day (`day`), so a second run on the same day adds none.
    Returns (new state, {id: gate} to withdraw now, ids still pending)."""
    new, due, pending = {}, {}, []
    for pid, gate in sorted(failed.items()):
        prior = state.get(pid, {})
        fails = prior.get("fails", 0) + (0 if prior.get("day") == day else 1)
        if fails >= WITHDRAW_AFTER_FAILS:
            due[pid] = gate
        else:
            new[pid] = {"fails": fails, "gate": gate, "day": day}
            pending.append(pid)
    return new, due, pending


def stable_id(published, title, first_day, last_day, new_id):
    """A rebuilt topic keeps the id of a published topic with the same title and an overlapping window."""
    for p in sorted(published, key=lambda p: p["first"]):
        if p["title"] == title and p["first"] <= last_day and first_day <= p["last"]:
            return p["id"]
    return new_id


class MonthFrequency:
    """Window document frequency from month buckets. A window counts every month it touches."""

    def __init__(self, corpus):
        self.months = defaultdict(Counter)
        for it in corpus:
            self.months[it["published_on"][:7]].update(tp._grams(it["title"]))

    def window(self, lo, hi):
        keys = []
        d = date(lo.year, lo.month, 1)
        while d <= hi:
            keys.append(d.strftime("%Y-%m"))
            d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return _WindowView([self.months[k] for k in keys if k in self.months])


class _WindowView:
    """Sums the month counters only for the n-grams that a caller asks for."""

    def __init__(self, counters):
        self.counters = counters

    def get(self, gram, default=0):
        return sum(c.get(gram, 0) for c in self.counters) or default

    def __getitem__(self, gram):
        return self.get(gram, 0)


def _classify(titles, table, default):
    counts = Counter()
    for t in titles:
        for pattern, slug in table:
            if re.search(pattern, t):
                counts[slug] += 1
    picked = [s for s, c in counts.most_common(2) if c >= max(1, CLASSIFY_SHARE * len(titles))]
    return picked or [default]


def _levels(jids):
    levels = []
    if "jur-tw" in jids:
        levels.append("central")
    if any(j in jids for j in ("jur-63000000", "jur-64000000", "jur-65000000", "jur-66000000", "jur-67000000", "jur-68000000")):
        levels.append("special_municipality")
    if any(j.startswith(("jur-10", "jur-09")) for j in jids):
        levels.append("county_city")
    return levels


def published_source_urls(root):
    """URLs of every source that an event in events/ cites (the published membership).
    System topics do not count: the full run builds them again and each run decides their members."""
    root = Path(root)
    urls = {}
    for p in (root / "sources").glob("*/*.yaml"):
        m = re.search(r'^url: "?([^"\n]+)"?$', p.read_text(encoding="utf-8"), re.M)
        if m:
            urls[p.stem] = m.group(1)
    cited = set()
    for p in (root / "events").glob("*/*.md"):
        if TOPIC_FILE.search(p.name):
            continue
        cited.update(urls[s] for s in re.findall(r"src-[0-9a-z-]+", p.read_text(encoding="utf-8")) if s in urls)
    return cited


def run(corpus, clusters, existing_seeds, root, report_path, today=None):
    df = tp.document_frequency(corpus)
    mf = MonthFrequency(corpus)
    by_url = {it["url"]: it for it in corpus}
    stats = Counter()
    published_ids = published_topics(root)
    failed, covered = {}, set()  # R82: published topic id -> first failed gate; ids that another candidate keeps

    def src_ids_of(urls):
        return {tp.src_id(by_url[u], tp.HOSTS) for u in urls if u in by_url}

    def fail(gate, urls):
        for pid in matching_published(published_ids, src_ids_of(urls)):
            failed.setdefault(pid, gate)

    def keep(urls):
        covered.update(matching_published(published_ids, src_ids_of(urls)))

    # 1. seeds
    raw = []
    for c in clusters:
        urls = [u for g in c.get("news_groups", []) for u in g.get("source_ids", []) if u in by_url]
        has_official = any(by_url[u].get("source_class") != "news" for u in urls)
        if len(urls) < SEED_MIN_ITEMS and not has_official:
            stats["candidate_single_item"] += 1
            continue
        raw.append(urls)
    stats["seed_clusters"] = len(raw)
    # 2. keys and merge
    merged = {}
    for urls in raw:
        its = sorted((by_url[u] for u in urls), key=lambda j: (j["published_on"], j["url"]))
        lo = _day(its[0]["published_on"]) - timedelta(days=tp.WINDOW_BEFORE)
        hi = _day(its[-1]["published_on"]) + timedelta(days=tp.WINDOW_AFTER)
        key = pick_noun_key([i["title"] for i in its], df, len(corpus), dfw=mf.window(lo, hi)) if len(its) > 1 else ""
        if not key:
            stats["rejected_no_key"] += 1
            fail("rejected_no_key", urls)
            continue
        slot = None
        for (k, a, b), v in merged.items():
            if k == key and a <= hi and lo <= b:
                slot = (k, a, b)
                break
        if slot:
            v = merged.pop(slot)
            merged[(key, min(lo, slot[1]), max(hi, slot[2]))] = v + its
        else:
            merged[(key, lo, hi)] = its
    stats["merged_topics"] = len(merged)
    # 3. existing events
    taken = published_source_urls(root)
    existing_keys, existing_key_by_id = [], []
    for s in existing_seeds:
        taken.update(s["seed_urls"])
        seed_items = [by_url[u] for u in s["seed_urls"] if u in by_url]
        if seed_items:
            probe = dict(s)
            tp.members(probe, corpus, df)  # the same key that the event was built with
            ks = probe["_keys"]
            if ks:
                existing_key_by_id.append((s["event_id"], ks[0]))
            days = sorted(_day(i["published_on"]) for i in seed_items)
            existing_keys += [(k, days[0] - timedelta(days=tp.WINDOW_BEFORE), days[-1] + timedelta(days=tp.WINDOW_AFTER)) for k in ks]
    # Bigger topics first, so a duplicate keeps the larger one.
    ordered = sorted(merged.items(), key=lambda kv: (-len(kv[1]), kv[0][1], kv[0][0]))
    window_items = sorted(corpus, key=lambda j: j["published_on"])
    out_seeds, published, published_sets = [], [], []
    for (key, lo, hi), seeds in ordered:
        members, seen_titles = [], set()
        for it in window_items:
            if lo <= _day(it["published_on"]) <= hi and key in it["title"] and not tp.DROP.search(it["title"]):
                norm = tp.normalize_title(it["title"])
                if norm not in seen_titles:
                    seen_titles.add(norm)
                    members.append(it)
        members = tp.anchored(members, [s["title"] for s in seeds], [key], df, len(corpus))
        if not any(m.get("source_class") in ("news", "fact_check") for m in members):
            stats["rejected_no_news"] += 1
            fail("rejected_no_news", [m["url"] for m in members])
            continue
        if sum(1 for m in members if m["url"] in taken) >= SAME_EVENT_SHARE * len(members):
            stats["skipped_existing_event"] += 1
            keep([m["url"] for m in members])
            continue
        titles = [m["title"] for m in members]
        full = extend_to_boundary(key, titles)
        if full != key:
            members = [m for m in members if full in m["title"]]
            titles = [m["title"] for m in members]
            key = full
        groups = split_cases(members)  # R112.3
        all_seeds = seeds
        for members in groups:
            titles = [m["title"] for m in members]
            seeds = all_seeds if len(groups) == 1 else ([s for s in all_seeds if s["url"] in {m["url"] for m in members}] or members[:1])
            if not name_quality_ok(key, titles, df.get(key, 0) or sum(1 for it in corpus if key in it["title"]), len(members), df):
                stats["rejected_name_quality"] += 1
                fail("rejected_name_quality", [m["url"] for m in members])
                continue
            irrelevant = not taiwan_relevant(titles)
            if irrelevant and names_foreign(titles):  # R112.5: only a title that names a foreign country gets the foreign label
                stats["rejected_foreign"] += 1
                fail("rejected_foreign", [m["url"] for m in members])
                continue
            if any((k in key or key in k) and s_lo <= hi and lo <= s_hi for k, s_lo, s_hi in existing_keys) or any(
                    s_lo <= hi and lo <= s_hi and sum(1 for t in titles if k in t) >= SAME_EVENT_SHARE * len(titles)
                    for k, s_lo, s_hi in existing_keys):
                stats["skipped_existing_event"] += 1
                keep([m["url"] for m in members])
                continue
            reason = exclusion_reason(members)
            if reason:
                stats["rejected_" + reason] += 1
                fail("rejected_" + reason, [m["url"] for m in members])
                continue
            jids = detect_jurisdictions(titles)
            actors = detect_gov_actors(titles, jids)
            for m in members:
                host = (m["url"].split("/")[2] if "//" in m["url"] else "")
                if m.get("source_class") == "official_statement" and host in tp.HOSTS and tp.HOSTS[host][1] not in actors:
                    actors.append(tp.HOSTS[host][1])
            if not actors:
                stats["rejected_no_gov_actor"] += 1
                fail("rejected_no_gov_actor", [m["url"] for m in members])
                continue
            if irrelevant:  # the gate still rejects a topic with no Taiwan term; a later gate above gave the label first
                stats["rejected_not_taiwan"] += 1
                fail("rejected_not_taiwan", [m["url"] for m in members])
                continue
            local = [j for j in jids if j != "jur-tw"]
            names = [next(n for jid, _, n, _ in JURS if jid == j)[:-2] for j in local]
            name = tp.display_name(key, [s["title"] for s in seeds])
            if not noun_phrase_name(name) or generic_name(name):
                stats["rejected_name_quality"] += 1
                fail("rejected_name_quality", [m["url"] for m in members])
                continue
            title = tp.topic_title(name, names, national="jur-tw" in jids)
            event_id = stable_id(published_ids, title, members[0]["published_on"], members[-1]["published_on"],
                                 topic_id(key, members[0]["published_on"], members[0]["url"]))
            seed = {"event_id": event_id,
                    "seed_urls": [s["url"] for s in seeds], "jurisdiction_ids": jids, "jurisdiction_names": names,
                    "gov_levels": _levels(jids), "controversy_types": _classify(titles, CTYPES, "governance_procedure"),
                    "policy_domains": _classify(titles, DOMAINS, "interior"), "actors": [(a, "other") for a in actors[:6]],
                    "sensitive": False, "_keys": [key],
                    "_name": name, "_generic": False}
            urls = {m["url"] for m in members}
            if any(len(urls & other) >= MERGE_OVERLAP * min(len(urls), len(other)) for other in published_sets):
                stats["skipped_duplicate_topic"] += 1
                keep(urls)
                continue
            ev = tp.build_event(seed, corpus, df, items=members)
            used = list(ev["used"].values())
            if not meets_source_rule(used):
                stats["rejected_source_rule"] += 1
                fail("rejected_source_rule", urls)
                continue
            if not meets_news_rule(used):
                stats["rejected_news_rule"] += 1
                fail("rejected_news_rule", urls)
                continue
            ev["review"]["sensitive"] = "misconduct" in seed["controversy_types"] or has_sensitive_term(
                [it["title"] for it in used])
            ensure_actor_files(root, [a for a, _ in ev["actors"]])
            prior = prior_event(root, ev["id"])
            tp.write_event(ev, seed, root, {}, actors_by_host=tp.HOSTS, overwrite_sources=False)
            republished = republish_topic(root, ev["id"], prior, today or date.today().isoformat())
            if republished:
                stats["republished"] += 1
            published.append({"id": ev["id"], "title": ev["title"], "sources": len(used), "key": key})
            published_sets.append(urls)
            out_seeds.append({k: v for k, v in seed.items() if not k.startswith("_")})
    stats["published"] = len(published)
    covered.update(p["id"] for p in published)
    failing = {pid: gate for pid, gate in failed.items() if pid not in covered}
    kept_withdrawn = {pid: gate for pid, gate in failing.items() if prior_event(root, pid)[0] == "withdrawn"}
    state, withdrawn, pending = apply_hysteresis(read_topic_state(root), {p: g for p, g in failing.items() if p not in kept_withdrawn},
                                                  today or taipei_day())
    for pid, gate in sorted({**kept_withdrawn, **withdrawn}.items()):
        withdraw_topic(root, pid, gate, today=today)  # a withdrawn topic gets its file back and no new record
    write_topic_state(root, state)
    stats["withdrawn"] = len(withdrawn)
    stats["withdraw_pending"] = len(pending)
    stats["withdrawn_kept"] = len(kept_withdrawn)
    keys = {k[0]: k[1] for k in existing_key_by_id}
    keys.update({p["id"]: p["key"] for p in published})
    links = apply_subtopic_links(root, keys)
    stats["part_of_links"] = len(links)
    stats["sensitive_from_sources"] = len(refresh_sensitive(root))
    Path(report_path).write_text(json.dumps({"stats": stats, "published": published, "part_of": links, "withdrawn": withdrawn}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    return stats, published, out_seeds


def ensure_actor_files(root, ids):
    import yaml
    root = Path(root)
    defs = {aid: (name, "gov_agency", jid) for jid, aid, name, _ in JURS}
    defs.update({aid: (name, atype, "jur-tw") for _, aid, name, atype in CENTRAL})
    made = []
    for aid in ids:
        if aid not in defs:
            continue
        name, atype, jid = defs[aid]
        p = root / "actors" / f"{aid}.md"
        if p.exists():
            continue
        doc = {"schema_version": 1, "id": aid, "name": name, "actor_type": atype, "jurisdiction_id": jid}
        p.write_text("---\n" + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False) + "---\n", encoding="utf-8")
        made.append(aid)
    return made


SYSTEM_REASON = "draft-review: 系統"


def refresh_sensitive(root, seeds_path=None):
    """R76 after the fact: recompute review.sensitive of each system topic from the cited source files
    (title and quote), the seed flag and the misconduct type. Returns the ids that changed."""
    root = Path(root)
    texts = {}
    for p in (root / "sources").glob("*/*.yaml"):
        raw = p.read_text(encoding="utf-8")
        texts[p.stem] = [m.group(1) for m in re.finditer(r'^(?:title|quote): "?(.+?)"?$', raw, re.M)]
    seeds_path = Path(seeds_path) if seeds_path else Path(__file__).with_name("topic_seeds.json")
    try:
        seed_flags = {s["event_id"]: bool(s.get("sensitive")) for s in json.load(open(seeds_path, encoding="utf-8"))}
    except OSError:
        seed_flags = {}
    changed = []
    for p in (root / "events" / "2026").glob("*.md"):
        doc, body = _read_event(p)
        review = doc.get("review", {})
        if not str(review.get("reason", "")).startswith(SYSTEM_REASON):
            continue
        cited = set(re.findall(r"src-[0-9a-z-]+", p.read_text(encoding="utf-8")))
        want = (seed_flags.get(doc["id"], False) or "misconduct" in doc.get("controversy_types", [])
                or tp.has_sensitive_term([t for s in cited for t in texts.get(s, [])]))
        if bool(review.get("sensitive")) != want:
            review["sensitive"] = want
            _write_event(p, doc, body)
            changed.append(doc["id"])
    return changed


def enrich_sources(root, corpus, enrich_path):
    """R75: add byline, section and the body quote from an article step output to existing source files."""
    enrich = {e["url"]: e for e in tp.read_jsonl(enrich_path) if e.get("status") == "ok"}
    by_url = {it["url"]: it for it in corpus}
    done = 0
    for p in (Path(root) / "sources" / "2026").glob("*.yaml"):
        m = re.search(r'^url: "?([^"\n]+)"?$', p.read_text(encoding="utf-8"), re.M)
        if not m or m.group(1) not in enrich or m.group(1) not in by_url:
            continue
        doc = tp._source_doc(by_url[m.group(1)], enrich, tp.HOSTS)
        if doc["id"] != p.stem:
            continue
        p.write_text(tp._dump(doc), encoding="utf-8")
        done += 1
    return done


def main(argv):
    if len(argv) != 6:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    corpus = tp.read_jsonl(argv[1])
    clusters = json.load(open(argv[2], encoding="utf-8"))
    existing = json.load(open(argv[3], encoding="utf-8"))
    stats, published, _ = run(corpus, clusters, existing, argv[4], argv[5])
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
