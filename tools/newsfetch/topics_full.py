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
from datetime import date, timedelta
from pathlib import Path

from tools.newsfetch import topics as tp

SAME_EVENT_SHARE = 0.3
EXCLUDE_SHARE = {"sensitive": 0.3, "election_campaign": 0.3, "criminal_case": 0.5, "entertainment": 0.3}
ELECTION = re.compile(r"參選|選情|民調|競選|拜票|提名|初選|選戰|輔選|候選人|號次|造勢|催票")
CRIME = re.compile(r"起訴|判刑|聲押|收押|交保|嫌犯|涉嫌|偵辦|逮捕|送辦|殺人|命案|毒品|詐團|車手|性侵|猥褻|竊盜|酒駕")
ENTERTAINMENT = re.compile(r"演唱會|歌手|藝人|女星|男星|偶像|專輯|戲劇|影集|綜藝|中職|球隊|選手|奪冠|賽事|電影")
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
LOCAL_GOV = re.compile(r"市府|縣府|市政府|縣政府|市長|縣長|議會|議員|局長|衛生局|教育局|環保局|消防局|交通局|社會局|工務局|公園處|鄉公所|鎮公所|區公所")
CENTRAL = [  # regex, actor id, name, actor type
    (r"行政院|政院|卓揆", "ac-executive-yuan", "行政院", "gov_agency"),
    (r"立法院|立院|立委", "ac-legislative-yuan", "立法院", "legislature"),
    (r"總統府", "ac-office-of-the-president", "總統府", "gov_agency"),
    (r"監察院|監委", "ac-control-yuan", "監察院", "control_body"),
    (r"司法院", "ac-judicial-yuan", "司法院", "court"),
    (r"憲法法庭", "ac-constitutional-court", "憲法法庭", "court"),
    (r"內政部|國土署", "ac-ministry-of-the-interior", "內政部", "gov_agency"),
    (r"警政署", "ac-national-police-agency", "內政部警政署", "gov_agency"),
    (r"消防署", "ac-national-fire-agency", "內政部消防署", "gov_agency"),
    (r"外交部", "ac-ministry-of-foreign-affairs", "外交部", "gov_agency"),
    (r"國防部|國軍", "ac-ministry-of-national-defense", "國防部", "gov_agency"),
    (r"財政部|國稅局", "ac-ministry-of-finance", "財政部", "gov_agency"),
    (r"教育部", "ac-ministry-of-education", "教育部", "gov_agency"),
    (r"法務部", "ac-ministry-of-justice", "法務部", "gov_agency"),
    (r"經濟部|能源署", "ac-ministry-of-economic-affairs", "經濟部", "gov_agency"),
    (r"交通部|公路局|觀光署|氣象署", "ac-ministry-of-transportation", "交通部", "gov_agency"),
    (r"勞動部", "ac-ministry-of-labor", "勞動部", "gov_agency"),
    (r"農業部|林保署|防檢署", "ac-ministry-of-agriculture", "農業部", "gov_agency"),
    (r"衛福部|衛生福利部|健保署|疾管署", "ac-ministry-of-health-and-welfare", "衛生福利部", "gov_agency"),
    (r"食藥署", "ac-taiwan-fda", "衛生福利部食品藥物管理署", "gov_agency"),
    (r"環境部", "ac-ministry-of-environment", "環境部", "gov_agency"),
    (r"文化部", "ac-ministry-of-culture", "文化部", "gov_agency"),
    (r"數發部|數位發展部", "ac-ministry-of-digital-affairs", "數位發展部", "gov_agency"),
    (r"陸委會", "ac-mainland-affairs-council", "大陸委員會", "gov_agency"),
    (r"海巡署|海委會", "ac-ocean-affairs-council", "海洋委員會", "gov_agency"),
    (r"中選會", "ac-central-election-commission", "中央選舉委員會", "gov_agency"),
    (r"金管會", "ac-financial-supervisory-commission", "金融監督管理委員會", "gov_agency"),
    (r"通傳會|NCC", "ac-national-communications-commission", "國家通訊傳播委員會", "gov_agency"),
]
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
CONCENTRATION = 4.0
BOUNDARY_SHARE = 0.8


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
BOUNDARY_MIN_SHARE = 0.3
RELEVANCE_SHARE = 0.5
MERGE_OVERLAP = 0.5


CONTINUATION_SHARE = 0.8
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
    if n < 2:
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
    return n > 0 and inside >= 0.5 * n


def is_place_name(key):
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{1,3}[鄉鎮區里村]", key)) or tp._is_place(key)


def is_person_or_party(key, titles):
    return bool(PARTIES.search(key)) or tp._is_person_or_speaker(key, titles) or bool(re.search(r"議長|議員|市長|縣長|立委|部長", key))


def taiwan_relevant(titles):
    n = max(1, len(titles))
    hits = 0
    for t in titles:
        if any(term in t for _, _, _, terms in JURS for term in terms) or LOCAL_GOV.search(t) \
                or any(re.search(p, t) for p, _, _, _ in CENTRAL) or re.search(r"台灣|臺灣|全台|國人", t):
            hits += 1
    return hits >= RELEVANCE_SHARE * n


def name_ok(key, total_df, window_df):
    if len(key) < 3 or key[0] in BAD_START or key[-1] in BAD_END or BAD_WORDS.search(key):
        return False
    return total_df <= CONCENTRATION * max(1, window_df)


has_sensitive_term = tp.has_sensitive_term


def _day(d):
    return date.fromisoformat(str(d))


def owner(item):
    """R88: one media group counts as one publisher. Items without a group count by publisher."""
    return item.get("publisher_group") or item["publisher"]


def meets_source_rule(items):
    """PRD 4.4 item 2: 1 grade A source, or grade C sources from 2 or more publishers."""
    if any(it.get("source_class") in ("official_record",) for it in items):
        return True
    pubs = {owner(it) for it in items if it.get("source_class") in ("news", "fact_check")}
    return len(pubs) >= 2


PLACE_FIXES = (("台北港", "新北港"), ("臺北港", "新北港"))  # 台北港 is in 新北市


def meets_news_rule(items):
    """R73: 2 or more news items from 2 or more news publishers (fact checks and official releases do not count)."""
    news = [it for it in items if it.get("source_class") == "news"]
    return len(news) >= 2 and len({owner(it) for it in news}) >= 2


SUBTOPIC_SHARE = 0.1


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


def detect_jurisdictions(titles):
    counts = Counter()
    for t in titles:
        for wrong, right in PLACE_FIXES:
            t = t.replace(wrong, right)
        for jid, _, _, terms in JURS:
            if any(term in t for term in terms):
                counts[jid] += 1
    local = [j for j, c in counts.most_common() if c >= max(1, 0.3 * len(titles))]
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
        "sensitive": sum(1 for it in items if it.get("sensitive")) / n,
        "election_campaign": sum(1 for it in items if ELECTION.search(it["title"])) / n,
        "criminal_case": sum(1 for it in items if CRIME.search(it["title"])) / n,
        "entertainment": sum(1 for it in items if ENTERTAINMENT.search(it["title"])) / n,
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
    picked = [s for s, c in counts.most_common(2) if c >= max(1, 0.2 * len(titles))]
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
    """URLs of every source that an event in events/ cites (the published membership)."""
    root = Path(root)
    urls = {}
    for p in (root / "sources").glob("*/*.yaml"):
        m = re.search(r'^url: "?([^"\n]+)"?$', p.read_text(encoding="utf-8"), re.M)
        if m:
            urls[p.stem] = m.group(1)
    cited = set()
    for p in (root / "events").glob("*/*.md"):
        cited.update(urls[s] for s in re.findall(r"src-[0-9a-z-]+", p.read_text(encoding="utf-8")) if s in urls)
    return cited


def run(corpus, clusters, existing_seeds, root, report_path):
    df = tp.document_frequency(corpus)
    mf = MonthFrequency(corpus)
    by_url = {it["url"]: it for it in corpus}
    stats = Counter()
    # 1. seeds
    raw = []
    for c in clusters:
        urls = [u for g in c.get("news_groups", []) for u in g.get("source_ids", []) if u in by_url]
        has_official = any(by_url[u].get("source_class") != "news" for u in urls)
        if len(urls) < 2 and not has_official:
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
        key = tp.pick_key([i["title"] for i in its], df, len(corpus), dfw=mf.window(lo, hi)) if len(its) > 1 else ""
        if not key:
            stats["rejected_no_key"] += 1
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
        if not any(m.get("source_class") in ("news", "fact_check") for m in members):
            stats["rejected_no_news"] += 1
            continue
        if sum(1 for m in members if m["url"] in taken) >= SAME_EVENT_SHARE * len(members):
            stats["skipped_existing_event"] += 1
            continue
        titles = [m["title"] for m in members]
        full = extend_to_boundary(key, titles)
        if full != key:
            members = [m for m in members if full in m["title"]]
            titles = [m["title"] for m in members]
            key = full
        if not name_ok(key, df.get(key, 0) or sum(1 for it in corpus if key in it["title"]), len(members)) \
                or not has_word_boundary(key, titles, df) or is_person_or_party(key, titles) \
                or is_quoted_slogan(key, titles) or is_place_name(key):
            stats["rejected_name_quality"] += 1
            continue
        if not taiwan_relevant(titles):
            stats["rejected_foreign"] += 1
            continue
        if any((k in key or key in k) and s_lo <= hi and lo <= s_hi for k, s_lo, s_hi in existing_keys) or any(
                s_lo <= hi and lo <= s_hi and sum(1 for t in titles if k in t) >= SAME_EVENT_SHARE * len(titles)
                for k, s_lo, s_hi in existing_keys):
            stats["skipped_existing_event"] += 1
            continue
        reason = exclusion_reason(members)
        if reason:
            stats["rejected_" + reason] += 1
            continue
        jids = detect_jurisdictions(titles)
        actors = detect_gov_actors(titles, jids)
        for m in members:
            host = (m["url"].split("/")[2] if "//" in m["url"] else "")
            if m.get("source_class") == "official_statement" and host in tp.HOSTS and tp.HOSTS[host][1] not in actors:
                actors.append(tp.HOSTS[host][1])
        if not actors:
            stats["rejected_no_gov_actor"] += 1
            continue
        local = [j for j in jids if j != "jur-tw"]
        names = [next(n for jid, _, n, _ in JURS if jid == j)[:-2] for j in local]
        seed = {"event_id": topic_id(key, members[0]["published_on"], members[0]["url"]),
                "seed_urls": [s["url"] for s in seeds], "jurisdiction_ids": jids, "jurisdiction_names": names,
                "gov_levels": _levels(jids), "controversy_types": _classify(titles, CTYPES, "governance_procedure"),
                "policy_domains": _classify(titles, DOMAINS, "interior"), "actors": [(a, "other") for a in actors[:6]],
                "sensitive": False, "_keys": [key],
                "_name": tp.display_name(key, [s["title"] for s in seeds]), "_generic": False}
        urls = {m["url"] for m in members}
        if any(len(urls & other) >= MERGE_OVERLAP * min(len(urls), len(other)) for other in published_sets):
            stats["skipped_duplicate_topic"] += 1
            continue
        ev = tp.build_event(seed, corpus, df, items=members)
        used = list(ev["used"].values())
        if not meets_source_rule(used):
            stats["rejected_source_rule"] += 1
            continue
        if not meets_news_rule(used):
            stats["rejected_news_rule"] += 1
            continue
        ev["review"]["sensitive"] = "misconduct" in seed["controversy_types"] or has_sensitive_term(
            [it["title"] for it in used])
        ensure_actor_files(root, [a for a, _ in ev["actors"]])
        tp.write_event(ev, seed, root, {}, actors_by_host=tp.HOSTS, overwrite_sources=False)
        published.append({"id": ev["id"], "title": ev["title"], "sources": len(used), "key": key})
        published_sets.append(urls)
        out_seeds.append({k: v for k, v in seed.items() if not k.startswith("_")})
    stats["published"] = len(published)
    keys = {k[0]: k[1] for k in existing_key_by_id}
    keys.update({p["id"]: p["key"] for p in published})
    links = apply_subtopic_links(root, keys)
    stats["part_of_links"] = len(links)
    stats["sensitive_from_sources"] = len(refresh_sensitive(root))
    Path(report_path).write_text(json.dumps({"stats": stats, "published": published, "part_of": links}, ensure_ascii=False, indent=1),
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
