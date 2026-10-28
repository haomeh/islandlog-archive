#!/usr/bin/env python3
"""Full topic run (R68): form topics from all clusters and write only those that meet PRD 4.4.

Usage: python3 -m tools.newsfetch.topics_full corpus.jsonl clusters.json topic_seeds.json archive_root report.json [--today YYYY-MM-DD] [--approve-withdraw approve.txt]

Steps:
1. Seeds: clusters with 2 or more items, or with an official or fact-check item. One-item news
   clusters stay candidates in the crawler output.
2. Each seed gets a key (topics.pick_key) with a month-bucket window frequency. Seeds with the
   same key and overlapping windows merge into one topic.
3. A topic that shares SAME_EVENT_SHARE of its members with a published event is skipped.
4. Jurisdictions come from place names in the member titles. Government actors come from agency
   names in the titles and from official sources (PRD 4.4 item 1).
   R154 to R157 (T26): a new topic also needs an issue name (a law, a budget, a case, a dispute, a disaster, a drill), no cut
   edge, no foreign body as its only body, and none of these: a candidate attack, a single accident, the health of an official,
   a private matter. Two new topics on one issue give one topic. Precision comes before recall: a class that no general rule stops
   is rejected. An old topic keeps the structural name test of R134.
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
    BODY_VERB_NAME_MAX_LEN, BOUNDARY_SHARE, CAMPAIGN_DAYS, CLASSIFY_SHARE, ELECTION_DAY, ELECTION_DISPUTE_MIN_GRADE_A, CONCENTRATION, CONTINUATION_SHARE, EXCLUDE_SHARE, JURISDICTION_SHARE,
    CONTINUATION_MIN_USES, DISEASE_NAME_MAX_LEN, FOREIGN_NAMED_SHARE, GENERIC_NAME_MAX_LEN, GOV_NAME_SHARE, MERGE_OVERLAP, MIN_KEY_LEN, NEWS_RULE_MIN_ITEMS, NEWS_RULE_MIN_PUBLISHERS, QUOTED_SLOGAN_SHARE,
    BARE_PERSON_MAX_LEN, BARE_PERSON_MIN_LEN, BARE_PERSON_SHARE, OFFICIAL_MIN_TITLES, RELEVANCE_SHARE, SAME_EVENT_SHARE, SEED_MIN_ITEMS, SOURCE_RULE_MIN_PUBLISHERS, SPLIT_MIN_TITLES, SUBTOPIC_SHARE,
    TAIWAN_MIN_SHARE, TAIWAN_MIN_TITLES, WITHDRAW_AFTER_FAILS, WITHDRAW_MAX_COUNT, WITHDRAW_MAX_SHARE,
    ACCIDENT_POLICY_SHARE, ACCIDENT_SHARE, CANDIDATE_MIN_TITLES, CANDIDATE_SHARE, DUPLICATE_GAP_DAYS, DUPLICATE_MIN_TITLES,
    DUPLICATE_TERM_LEN, DUPLICATE_TERM_MAX_DF, GOV_ACT_SHARE,
    NUMBER_CUT_SHARE, OFFICIAL_HEALTH_SHARE, QUOTE_COLON_SHARE, SLOGAN_MAX_LEN, THEME_MAX_MONTH_SHARE, THEME_MIN_MONTHS, THEME_MIN_USES,
    DUPLICATE_NEAR_DAYS, DUPLICATE_NEAR_TERM_LEN,
    ACT_MATCH_LEN, ACTOR_SHARE, SCOPE_MIN_SHARE, SCOPE_MIN_TITLES, TITLE_TERM_MIN_TITLES, TITLE_TERM_SHARE,
    MINISTRY_MAX_SHARE, MINISTRY_MIN_COUNT, MINISTRY_MIN_TITLES,
    ACT_MIN_TITLES, PHENOMENON_SHARE, PUBLIC_WORKS_ACT, AD_HOC_ACT, PUBLIC_BODY, NATIONAL_BODY)

TOPIC_FILE = re.compile(r"^ev-\d{8}-topic-[0-9a-f]{8}\.md$")
ELECTION = re.compile(r"參選|選情|民調|競選|拜票|提名|初選|選戰|輔選|候選人|號次|造勢|催票|對手陣營|競辦|競總")  # R106: the last 3 name a campaign without an election word
CRIME = re.compile(r"起訴|判刑|聲押|收押|交保|嫌犯|涉嫌|偵辦|逮捕|送辦|殺人|命案|毒品|詐團|車手|性侵|猥褻|竊盜|酒駕|弊案|收賄|貪污|貪瀆|行賄|賄賂|洩題")  # R112.3: the last 7 name a corruption case
CRIME_NEW = re.compile(CRIME.pattern + r"|緩刑|壓制帶回|虐殺|虐待|縱火|放火|砍殺|持刀|持槍|持球棒|鬥毆|拘提|拘留|重判|輕判")  # R154: the last 14 name a single case or a sentence; R162 (N1): only a new topic reads them
ENTERTAINMENT = re.compile(r"演唱會|歌手|藝人|女星|男星|偶像|專輯|戲劇|影集|綜藝|中職|球隊|選手|奪冠|賽事|電影")
ELECTION_LEGAL = re.compile(r"駁回|裁定|判決|高行|行政法院|法院|當選無效|選舉訴訟")  # R112.4: a court ruling on a candidacy is not campaign content
LAW_PASSED = re.compile(r"三讀|條例》|修正草案|修法")  # R112.4: a law passed by the legislature is not sensitive by its subject alone
CONSUMER = re.compile(r"優惠|折扣|現省|省[\d百千萬]|半價|折抵|票價|抵用|買一送一")  # R112.5: a discount is a consumer title, not entertainment news
CASE_TITLE = re.compile(CRIME.pattern + r"|賄選|涉賄|羈押|追捕|查獲|查緝|查抄|落網|通緝|逃竄")  # R141.3: a title of an arrest, a search or a vote-buying case is another case than the issue of the topic
FOREIGN_ONLY = re.compile(r"美國|川普|中國|大陸|日本|南韓|北韓|俄羅斯|烏克蘭|伊朗|以色列|歐盟|英國|德國|法國|印度|菲律賓|越南|泰國|馬來西亞")
FOREIGN_NEW = re.compile(FOREIGN_ONLY.pattern
                         + r"|萬那杜|索羅門|斐濟|印尼|土耳其|沙烏地|埃及|巴西|阿根廷|加拿大|澳洲|紐西蘭|新加坡|巴基斯坦|阿富汗|敘利亞|黎巴嫩|古巴|墨西哥|委內瑞拉|智利|秘魯|肯亞|奈及利亞|南非|蘇丹|葉門|伊拉克|緬甸|柬埔寨|寮國|尼泊爾|孟加拉|斯里蘭卡")  # R154: a country list, so a foreign quake or a foreign bank has a foreign label; R162 (N1): only a new topic reads it

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
COURT = re.compile(r"北高行|中高行|高高行|最高行政法院|高等行政法院|行政法院|高等法院|最高法院|地方法院|地院|高分院|法院")  # R129: a court name is no place
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


def has_word_boundary(key, titles, df=None, new=False):
    """A key is a fragment when its next (or previous) character is one of at most 3 characters in
    CONTINUATION_SHARE of its uses (降速演 -> 習 or 練; 辦理退 -> 稅 or 費). A noun head ends a whole word.
    R154, R162 (N1): for a new topic a digit or a letter continues the word too (EEZ + 劃界談判)."""
    def continues(c):
        return bool(tp.CJK_RUN.fullmatch(c) or (new and re.fullmatch(r"[0-9A-Za-z]", c)))

    noun = bool(NOUN_HEAD.search(key))
    left, right, n = Counter(), Counter(), 0
    for t in titles:
        i = t.find(key)
        while i >= 0:
            n += 1
            if i > 0 and continues(t[i - 1]):
                left[t[i - 1]] += 1
            j = i + len(key)
            if j < len(t) and continues(t[j]):
                right[t[j]] += 1
            i = t.find(key, i + 1)
    if n < CONTINUATION_MIN_USES:
        return False  # R147.3: one use cannot show where the word ends
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


ROLE_BEFORE = re.compile(r"(?:議長|議員|市長|縣長|立委|部長|署長|局長|院長|校長|主委|委員|主播|記者|總統|董事長|教授|老師|醫師|律師|檢察官|法官|歌手|演員|導演|網紅|[前現])$")


def bare_person(key, titles):
    """R147.3: a name of 2 to 4 characters that follows a role word (前主播薛楷莉, 議長朱安雄) in half of its uses names only a person."""
    if not BARE_PERSON_MIN_LEN <= len(key) <= BARE_PERSON_MAX_LEN or tp.NOUN_END.search(key):
        return False
    uses = after_role = 0
    for t in titles:
        i = t.find(key)
        while i >= 0:
            uses += 1
            after_role += bool(ROLE_BEFORE.search(t[:i]))
            i = t.find(key, i + 1)
    return uses > 0 and after_role >= BARE_PERSON_SHARE * uses


def is_person_or_party(key, titles):
    return bool(PARTIES.search(key)) or tp._is_person_or_speaker(key, titles) or bare_person(key, titles) or bool(re.search(r"議長|議員|市長|縣長|立委|部長", key))


POLICY_NOUN = re.compile(r"平台|補助|獎助|津貼|警示|示警|預算|條例|辦法|方案|計畫|政策|草案|新制|制度|專案|給付|基金|原住民族")  # R112.4; R141.5: 原住民族 names a national status and policy
PLACE_PREFIX = re.compile(r"^(?:" + tp.PLACE.pattern + r")[市縣]?")
PLACE_ONLY = re.compile(PLACE_PREFIX.pattern + r"(?:[\u4e00-\u9fff]{1,3}[區鄉鎮里村市])?")
DISEASE_END = re.compile(r"(癌|腫瘤|症|病|炎|瘟|流感|感染)$")
OBJECT_HEAD = re.compile(r"(船|艦|車|機|棚|袋|箱)$")  # a bare object type: 巡視船, 豎孤棚


BODY_NAME = "|".join([p for p, _, _, _ in CENTRAL] + [LOCAL_GOV.pattern, COURT.pattern])
BODY_VERB = re.compile(r"(?:" + BODY_NAME + r")(?:駁回|裁定|判決|回應|說明|表示|宣布|拍板|喊停|開罰|道歉|聲明|澄清|否認|證實|通過|同意|撤銷|退回|決議)")  # R128


def body_verb_name(name):
    """R128: a body short name and a verb (北高行駁回) names an act of the body, not an issue."""
    return len(name) <= BODY_VERB_NAME_MAX_LEN and bool(BODY_VERB.fullmatch(name))


def generic_name(name):
    """R112.2: a name that is only a place, only a disease or only a generic object. A named facility (淡江大橋,
    金華國中) has a proper name before its head and is not generic. The schema has no place event kind, so the
    named facility is the exception for a place."""
    if PLACE_ONLY.fullmatch(name) or body_verb_name(name):
        return True
    rest = PLACE_PREFIX.sub("", name, count=1)
    if rest != name and len(rest) <= GENERIC_NAME_MAX_LEN:
        return True  # a jurisdiction and a few characters (屏東縣豎孤棚)
    if DISEASE_END.search(name) and len(name) <= DISEASE_NAME_MAX_LEN and not POLICY_NOUN.search(name):
        return True
    return len(name) <= GENERIC_NAME_MAX_LEN and bool(OBJECT_HEAD.search(name))


OFFICE_HOLDER = re.compile(r"(?:部長|署長|主委|次長)([\u4e00-\u9fff]{3})(?![\u4e00-\u9fff]{0,1}(?:部|署|會|院|局))")  # R141.5: 衛福部長石崇良
OFFICE_WORD = re.compile(r"部長|署長|閣揆|總長|次長")
_OFFICIALS = frozenset()


def office_holders(corpus):
    """R141.5: the names that follow an office word (部長, 署長, 主委) in at least OFFICIAL_MIN_TITLES titles of the corpus."""
    count = Counter()
    for it in corpus:
        count.update(set(OFFICE_HOLDER.findall(it["title"])))
    return {name for name, n in count.items() if n >= OFFICIAL_MIN_TITLES}


def set_officials(names):
    """The run sets the office holders of its corpus once; names_central reads them."""
    global _OFFICIALS
    _OFFICIALS = frozenset(names)


FOREIGN_NAME = (r"(?:美國|美方|美|中國|中共|北京|大陸|日本|日方|南韓|韓國(?!瑜)|北韓|俄羅斯|俄方|俄|烏克蘭|烏國|烏|伊朗|以色列|埃及|印度|英國|德國|法國|歐盟|越南|菲律賓|泰國|土耳其|巴西|加拿大|澳洲|紐西蘭|新加坡|馬來西亞|印尼|巴基斯坦|阿富汗|沙烏地|敘利亞|黎巴嫩|古巴|墨西哥|委內瑞拉|聯合國)")
FOREIGN_OFFICE = re.compile(FOREIGN_NAME + r"(?:外交部|國防部|防部|財政部|國安局|國安會|央行|中央銀行|教育部|內政部|司法部|衛生部|總統|總理|首相|部長|議員|議會|市長|國會|政府|軍方|法院|最高法院|國務院|白宮|軍司令部)|聯合國軍|[參眾]議員")


def home_text(title):
    """R154 (PRD 4.5 item 6): the title without the bodies and officials of a foreign country (伊朗外交部, 美國防部, 南韓議員, 聯合國軍),
    so a foreign office does not count as a body of Taiwan."""
    return FOREIGN_OFFICE.sub(" ", title)


def names_central(title, new=False):
    """R141.5: a title names a central body (大法官 and 憲法法庭 belong to it), a minister title or a minister by name.
    R162 (N1): for a new topic the foreign bodies are taken out first."""
    title = (home_text(title) if new else title).replace("氣象署", "")  # a weather or quake report cites the agency as its source: a foreign quake is no central act
    return bool(any(re.search(p, title) for p, _, _, _ in CENTRAL) or OFFICE_WORD.search(title) or any(n in title for n in _OFFICIALS))


def names_government(title, new=False):
    return bool(LOCAL_GOV.search(home_text(title) if new else title) or names_central(title, new))


def names_public_body(title):
    """R247.3, R251.1: a body by kind (PUBLIC_BODY) or a national body by name. Only the act gate reads it (public_act_title)."""
    text = home_text(title)
    return bool(PUBLIC_BODY.search(text) or NATIONAL_BODY.search(text))


def names_foreign(titles, new=False):
    """R112.5: a topic is foreign when FOREIGN_NAMED_SHARE of its titles names a foreign country or leader."""
    foreign = FOREIGN_NEW if new else FOREIGN_ONLY
    return sum(1 for t in titles if foreign.search(t)) >= FOREIGN_NAMED_SHARE * max(1, len(titles))


ISSUE_HEAD = re.compile(
    r"(?:(?<![非違合犯說想方手用看寫算無依做作])法|(?<![提個文答檔圖])案|法案|條例|草案|修法|立法|新制|新規|制度|辦法|規定|標準|機制|政策|計畫|方案|專案|預算|決算|經費|補助|津貼|補貼|獎勵|減免|優惠|基金|年金|保險|稅|稅制|關稅|費|費率|電價|票價|房價|物價|利率|匯率|工資|薪資|護病比"  # a law, a rule, a budget or a price
    r"|事件|事故|意外|爭議|風波|風暴|危機|疫情|災情|災害|淹水|地震|颱風|豪雨|堰塞湖|土石流|火災|爆炸|停電|斷水|缺水|缺電|污染|汙染|空污|淤積|問題|超標|不實|謠言"  # a case, a dispute or a disaster
    r"|演習|演練|會談|談判|協商|出訪|訪問|之旅|審查|調查|稽查|查核|檢驗|招標|採購|軍購|徵收|拆遷|通車|啟用|開工|動工|選舉|罷免|連署|公投|釋憲|抗議|罷工|遊行|集會|審議|質詢"  # a public act
    r"|召回|下架|停業|停課|停班|放假|禁令|管制|制裁|免簽|降速|改革|轉型|重建|重啟|復原|擴建|改建|遷移|搬遷|地下化|共識)$")  # R154, R155.3: a new topic names an issue, not a bare place, organization, object or person
VERB_LEAD = re.compile(
    r"^(?:要求|研擬|擬|將|協商|舉辦|取消|關閉|持有|撥補|拋|推動|提出|提高|調整|修正|修訂|制定|訂定|實施|施行|強化|加強|落實|啟動|宣布|公布|公開|發布|回應|否認|反擊|批評|質疑|呼籲|籲|促|主張|反對|支持|同意|拒絕|通過|退回|駁回|凍結|刪除|刪減|撤銷|取締|禁止|限制|開放|放寬|解除|延長|縮短|增加|減少|降低|擴大|縮小|避免|防止|預防|面對|確認|認定|讓|使|被|遭|為|給|在|對|向|從|把|以|由|因|應|須|需|已|仍|還|又|也|都|就|才|僅|只|並|及|與|和|的|了|不|沒|未|別|勿|是|恐|疑|欲|直接|立即|馬上|盡快|儘速|全面|持續|繼續|正式|即將|預計|可望|課|砍|擋|漲|砸|加重|加徵|減徵|免徵|開徵)")  # R154: a name that starts with a verb, an adverb or a function word has no subject; R162: the last 9 are tax and price verbs (課重稅)
SENTENCE_WORD = re.compile(r"有.+就|也|才會|不會|不能|不是|不要|不再|不得|無法|沒有|沒辦法|怎麼|為何|什麼|一直|我們|你們|他們|自己|你|我")  # R154: a sentence of a speaker, not a noun phrase


GENERIC_ACT = re.compile(r"(?:修法|立法|修正|會議|大會|協商|說明|記者會|座談會|公聽會|討論|檢討|溝通|表態|回應|聲明)$")  # R162: an act that every law and every issue has
FACILITY_EVENT = re.compile(r"(?:中心|診所|醫院|學校|工廠|公司|餐廳|飯店|旅館|商場|市場|夜市|公園|車站|機場|大樓|宿舍|園區|幼兒園|安養院|養護中心|護理之家|店|館)(?:颱風|地震|豪雨|大雨|火災|爆炸|停電|淹水|寒流|強風|水災)$")  # R162: an object and a weather or disaster noun, with no relation between them (月子中心颱風)
NEGATED_PREDICATE = re.compile(r"(?<=[\u4e00-\u9fff])不(?:放|給|發|做|管|讓|用|准|開|停|補|提|說|理|應|辦|救|查|認|交|還|到|去|來|能|會|要|想|該|得|肯|敢|願|買|賣|道歉|承認|回應|處理)")  # R162: a negated verb in the middle of a name is a clause or a slogan (白海豚不放假)


def strip_generic_act(name):
    """R162: the name without the generic act nouns at its end (食安法修法會議 -> 食安法, 修法會議 -> empty)."""
    while True:
        m = GENERIC_ACT.search(name)
        if not m:
            return name
        name = name[:m.start()]


def issue_name(name):
    """R154, R155.3, R162: a name of a new topic ends with an issue noun (law, budget, case, dispute, disaster, drill, recall) and does not
    start with a verb or a function word. A bare place, organization, object or person, a verb phrase and a quote fail.
    R162: a generic act noun (修法, 會議, 協商) at the end needs a law or an issue before it; an object and a weather noun
    (月子中心颱風) and a negated verb (白海豚不放假) fail. A clause with a subject and a verb that ends with no issue noun
    is a known miss (R156)."""
    core = strip_generic_act(name)
    return bool(ISSUE_HEAD.search(core)) and not VERB_LEAD.search(name) and not SENTENCE_WORD.search(name) \
        and not FACILITY_EVENT.search(name) and not NEGATED_PREDICATE.search(name)


SPEECH_BEFORE = re.compile(r"(?:喊|高喊|喊出|主張|倡議|倡導|提倡|倡|直呼|宣稱|標榜)[「『]?$")  # R162: a verb that brings a slogan


def copied_quote(key, titles):
    """R162: the key sits inside 「」 or follows a slogan verb (喊, 主張, 倡) in QUOTED_SLOGAN_SHARE of its uses. A short name that
    a title only quotes is a slogan, not the name of an issue (零軍購)."""
    inside = n = 0
    for t in titles:
        for m in re.finditer(re.escape(key), t):
            n += 1
            before = t[:m.start()]
            if before.count("「") > before.count("」") or SPEECH_BEFORE.search(before):
                inside += 1
    return n >= CONTINUATION_MIN_USES and len(key) <= SLOGAN_MAX_LEN and inside >= QUOTED_SLOGAN_SHARE * n


def theme_word(key, months):
    """R162: a keyword bundle. The key is in use in THEME_MIN_MONTHS months or more (2 titles or more in each) and no month holds
    THEME_MAX_MONTH_SHARE of its uses. A theme word (政治獻金) joins many cases. A case or an issue has a burst. `months` is the
    month counters of MonthFrequency."""
    counts = [c.get(key, 0) for c in months.values()]
    total = sum(counts)
    return total > 0 and sum(1 for c in counts if c >= THEME_MIN_USES) >= THEME_MIN_MONTHS and max(counts) < THEME_MAX_MONTH_SHARE * total


def _neighbors(key, titles):
    """The characters before and after every use of the key in the titles. A title edge gives an empty string."""
    before, after = [], []
    for t in titles:
        i = t.find(key)
        while i >= 0:
            before.append(t[i - 1] if i > 0 else "")
            j = i + len(key)
            after.append(t[j] if j < len(t) else "")
            i = t.find(key, i + 1)
    return before, after


def cut_edge(key, titles):
    """R154: the key follows a digit, a Latin letter, a percent sign or a list comma in NUMBER_CUT_SHARE of its uses (42號演習 -> 號演習,
    C肝群聚 -> 肝群聚, 海嘯、堰塞湖列災害 -> 堰塞湖列災害), or a digit follows a key that ends with no noun head (利率連10凍).
    The first or last part of the name is lost."""
    before, after = _neighbors(key, titles)
    if not before:
        return False
    left = sum(1 for c in before if re.fullmatch(r"[0-9A-Za-z%％、]", c))
    right = sum(1 for c in after if re.fullmatch(r"[0-9]", c))
    return left >= NUMBER_CUT_SHARE * len(before) or (right >= NUMBER_CUT_SHARE * len(after) and not NOUN_HEAD.search(key))


def spoken_after_colon(key, titles):
    """R154: the key follows a colon in QUOTE_COLON_SHARE of its uses. It is what a speaker said (沈伯洋：底線一直被踩)."""
    before, _ = _neighbors(key, titles)
    return bool(before) and sum(1 for c in before if c and c in "：:") >= QUOTE_COLON_SHARE * len(before)


def new_name_ok(key, titles):
    """R154, R162: the name tests that only a new topic must pass: the key has no cut edge and is no words of a speaker or a slogan."""
    return not cut_edge(key, titles) and not spoken_after_colon(key, titles) and not copied_quote(key, titles)


ACT_VERB_LEAD = re.compile(r"^(?:免(?![費簽])|提|刪|砍|減|增(?!值)|追加|聲請|申請|修|補發|撤換|降|擴(?!建)|縮)")  # R196.1: a name that starts with an act verb has no subject (免健保費, 提追加預算, 聲請釋憲)
ENTITY_END = re.compile(r"(?:基金會?|公司|集團|企業|銀行|協會|公會|學會|財團|工會|聯盟|商會)$")  # R196.3: the end of a bare organization, fund or company
ACT_ISSUE = re.compile(r"採購|預算|決算|條例|修法|立法|草案|彈劾|人事|同意|提名|任命|徵收|釋憲|補助|稅|費|審查|調查|招標|仲裁|訴訟|選舉|罷免|公投|協議|協商|改革|爭議|弊|軍購|招商|拆遷|都更|違建|貸款|薪資|工資|延役|除役|修憲|開放|管制|放寬")  # R196.3: a word that names the act or the issue of a case (炸藥採購案), not only an entity
GENERIC_OBJECT = r"(?:追加|總|年度|特別)?(?:預算|經費|法案|款項|條例|草案|法律|政策|計畫|方案|補助)"
GENERIC_CLAUSE = re.compile(r"^.{1,6}?(?:通過|凍結|刪減|撤回|退回|刪|砍|凍|減|增|提|退|擋|撤|撥|砸)" + GENERIC_OBJECT + "$")  # R196.8: a subject, an act verb and a generic object (立院刪預算)
SPOKEN_FROM = re.compile(r"[：:]|稱(?![號霸呼讚])")


def act_verb_lead(name):
    """R196.1: the first word of the name is a verb or an act verb, and no subject comes before it. Only a new topic must pass."""
    return bool(ACT_VERB_LEAD.search(name))


ACT_HEAD = re.compile(r"(?:法案|草案|條例|政策|制度|新制|辦法|規定|機制|方案|計畫|專案|改革|案)$")  # R215.2: a noun that names the thing, not a payment (修憲案, 減碳政策)
MONEY_END = re.compile(r"(?:費|預算|決算|經費|補助|津貼|補貼|款|稅|金)$")  # R215.2: a money object stays a bare verb phrase (免健保費, 刪預算案)


def act_verb_lead_fails(name):
    """R206, R215.2: the name starts with an act verb and no head noun saves it. A head noun (案, 政策, 條例) at the end, with an object
    between the verb and the head that is no money noun, names the thing (修憲案, 提名案, 減碳政策). A money noun (免健保費, 提追加預算),
    a bare head (提案) and a name with no head (聲請釋憲) have no subject and no issue."""
    m = ACT_VERB_LEAD.search(name)
    if not m:
        return False
    head = ACT_HEAD.search(name)
    if not head:
        return True
    obj = name[m.end():head.start()]
    return not obj or bool(MONEY_END.search(obj))


def title_term(key, titles):
    """R196.2: the key sits inside a quote (「」), or after a colon or 稱, in TITLE_TERM_MIN_TITLES titles or more and in
    TITLE_TERM_SHARE of the titles that hold it. A name that a source quotes is words of a speaker (大不過憲法), not an issue."""
    holding = [t for t in titles if key in t]
    spoken = 0
    for t in holding:
        parts = re.findall(r"[「『]([^」』]*)", t)
        m = SPOKEN_FROM.search(t)
        if m:
            parts.append(t[m.end():])
        if any(key in p for p in parts):
            spoken += 1
    return spoken >= TITLE_TERM_MIN_TITLES and spoken >= TITLE_TERM_SHARE * max(1, len(holding))


def bare_entity(name):
    """R196.3: a bare organization, fund or company name, or <entity>案 with no word of an act or an issue before 案 (兆基案)."""
    m = ENTITY_END.search(name)
    if m:
        rest = name[:m.start()]
        return not (ACT_ISSUE.search(rest) or ISSUE_HEAD.search(rest))
    if name.endswith("案") and len(name) > 1:
        rest = name[:-1]
        return not (ACT_ISSUE.search(rest) or ISSUE_HEAD.search(rest))
    return False


def generic_clause(name):
    """R196.8: a clause of a subject, an act verb and a generic object (預算, 法案) with no named item (立院刪預算)."""
    return bool(GENERIC_CLAUSE.search(name))


def title_level(title):
    """R196.6: "local" when the title names a local government and no central body, "central" for the reverse, else None."""
    local = bool(LOCAL_GOV.search(home_text(title)))
    central = names_central(title, True)
    return "local" if local and not central else "central" if central and not local else None


def scope_levels(titles, national):
    """R196.4, R196.6: returns (the indexes of the titles that name another government level than the topic, mixed). A title of the other
    level fails (b). `mixed` is true when two levels each have SCOPE_MIN_TITLES titles or more and SCOPE_MIN_SHARE of the titles: the
    cluster joins two issues that share a keyword."""
    levels = [title_level(t) for t in titles]
    own = "central" if national else "local"
    off = [i for i, lv in enumerate(levels) if lv and lv != own]
    big = max(SCOPE_MIN_TITLES, SCOPE_MIN_SHARE * len(titles))
    mixed = levels.count("local") >= big and levels.count("central") >= big
    return off, mixed


def place_scope(titles, jids):
    """R196.5: a place stays in the name of the topic only when every title names it. The other places go out of the name. The topic keeps
    its jurisdictions and its actors."""
    kept = [j for j in jids if j != "jur-tw" and all(j in _title_jurisdictions(t) for t in titles)]
    return kept or ["jur-tw"]


FEE_NAME = re.compile(r"(?:費|預算|經費|補助|補貼|津貼|款)$")
MINISTRY_ACTORS = [(p, aid) for p, aid, _, kind in CENTRAL if kind == "gov_agency" and aid != "ac-executive-yuan"]  # R215.3: the ministries and agencies; the Executive Yuan, the legislature and the courts sit above or beside them


def mixed_ministry(name, titles):
    """R207, R215.3: a fee or budget name whose titles name MINISTRY_MIN_TITLES titles each of MINISTRY_MIN_COUNT central ministries or more, with no
    ministry in MINISTRY_MAX_SHARE of the titles, joins one fee name over several ministries (媒宣費). Such a cluster is no one issue."""
    if not FEE_NAME.search(name):
        return False
    homes = [home_text(t) for t in titles]
    counts = [sum(1 for h in homes if re.search(p, h)) for p, _ in MINISTRY_ACTORS]
    big = [c for c in counts if c >= MINISTRY_MIN_TITLES]
    return len(big) >= MINISTRY_MIN_COUNT and max(counts) < MINISTRY_MAX_SHARE * max(1, len(titles))


def t32_name_ok(key, name, titles):
    """R196.1, R196.2, R196.3, R196.8, R206: the name tests that only a new topic must pass."""
    return not (act_verb_lead_fails(name) or generic_clause(name) or bare_entity(name) or any(title_term(k, titles) for k in {key, name}))


def name_quality_ok(key, titles, total_df, window_df, df=None, new=False):
    """The name gates of the full run. R112.2: only a place, a disease or a generic object fails. R112.4: a key with a policy
    noun, or a key whose titles name a government body in GOV_NAME_SHARE, skips the word-start and word-end tests of name_ok.
    R147.1: no name skips the word-boundary test or the quote test."""
    if not noun_phrase_name(key) or generic_name(key) or is_person_or_party(key, titles) or is_place_name(key):
        return False
    policy_key = bool(POLICY_NOUN.search(key))
    policy_titles = sum(1 for t in titles if names_government(t, new)) >= GOV_NAME_SHARE * max(1, len(titles))
    if not name_ok(key, total_df, window_df, loose=policy_key or policy_titles):
        return False
    return has_word_boundary(key, titles, df, new) and not is_quoted_slogan(key, titles)


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


TW_POLITICS = re.compile(r"國民黨|民進黨|民眾黨|時代力量|時力|台灣基進|親民黨|新黨|藍營|綠營|藍白|在野|朝野|藍委|綠委|白委|立委|部長|閣揆|院長")  # R127: Taiwan parties, legislators, ministers
NATIONAL_LAW = re.compile(r"修法|入法|立法|專法|子法|法案|草案|條例|三讀|預算|軍購|國防|護病比|公股|釋憲|修憲|公投|(?:食安|空污|勞基|道交|刑|民|憲)法")  # R127: national law or policy nouns


FOREIGN_FIGURE = re.compile(r"川普|拜登|普丁|習近平|王毅|王滬寧|范斯|盧比歐|馬可仕|歐巴馬|趙小蘭|黎智英|戴恩斯|詹姆士|古天樂|郭文貴|澤倫斯基")  # names of public_figures.json that are not Taiwan officials
TAIWAN_FIGURE_NAMES = frozenset(n for n in tp.PUBLIC_FIGURES if len(n) >= 2 and not FOREIGN_FIGURE.search(n))
TAIWAN_FIGURE = re.compile("|".join(re.escape(n) for n in tp.PUBLIC_FIGURES if len(n) >= 2 and not FOREIGN_FIGURE.search(n)) or r"(?!)")  # R141.4: a mayor, legislator or minister of Taiwan
TYPHOON = re.compile(r"颱風|颱|熱帶低壓|熱帶性低氣壓")
TAIWAN_WORD = re.compile(r"台灣|臺灣|全台|[對近襲侵離登赴朝向]台")  # R141.4: a forecast that names Taiwan
NATIONAL_ROAD = re.compile(r"台\d{1,2}線|國道\d|省道")


def taiwan_relevant(titles, new=False):
    """R84, R127: a title is about Taiwan when it names a place, a government body, a national system, a Taiwan party,
    legislator or minister, or (with no foreign country named) a national law or policy noun. R141.4: a Taiwan public figure
    (a mayor) and a national road count too. A topic passes with RELEVANCE_SHARE of such titles, or with TAIWAN_MIN_TITLES of them
    that are TAIWAN_MIN_SHARE of the titles when the topic names no foreign country. A typhoon forecast passes when
    RELEVANCE_SHARE of its titles name a typhoon and TAIWAN_MIN_TITLES of them name Taiwan.
    R154, R162 (N1): for a new topic a foreign body or official is no Taiwan body and a longer country list is read."""
    n = max(1, len(titles))
    hits = storm = named = 0
    for t in titles:
        foreign = bool((FOREIGN_NEW if new else FOREIGN_ONLY).search(t))
        if new:
            t = home_text(t)
            if foreign:
                t = t.replace("氣象署", "")  # a report of a foreign quake cites the Taiwan agency as its source
        if any(term in (place_text(t) if new else t) for _, _, _, terms in JURS for term in terms) or (LOCAL_GOV.search(t) and not (new and foreign)) \
                or any(re.search(p, t) for p, _, _, _ in CENTRAL) or NATIONAL_SYSTEMS.search(t) or re.search(r"台灣|臺灣|全台|國人", t) \
                or TW_POLITICS.search(t) or (NATIONAL_LAW.search(t) and not foreign) \
                or (TAIWAN_FIGURE.search(t) and not foreign) or NATIONAL_ROAD.search(t):
            hits += 1
        if TYPHOON.search(t):
            storm += 1
            named += bool(TAIWAN_WORD.search(t))
    if hits >= RELEVANCE_SHARE * n or (storm >= RELEVANCE_SHARE * n and named >= TAIWAN_MIN_TITLES):
        return True
    return hits >= TAIWAN_MIN_TITLES and hits >= TAIWAN_MIN_SHARE * n and not names_foreign(titles, new)


def name_ok(key, total_df, window_df, loose=False):
    """`loose` (R112.4) skips the word-start and word-end tests for a policy name."""
    if len(key) < MIN_KEY_LEN or BAD_WORDS.search(key) or (not loose and (key[0] in BAD_START or key[-1] in BAD_END)):
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
    return len(pubs) >= SOURCE_RULE_MIN_PUBLISHERS


PLACE_FIXES = (("台北港", "新北港"), ("臺北港", "新北港"), ("竹北", "竹縣"), ("南韓", "韓國"))  # 台北港 is in 新北市; 竹北市 is in 新竹縣 and holds 北市 (R129)


def meets_news_rule(items):
    """R73: 2 or more news items from 2 or more news publishers (fact checks and official releases do not count)."""
    news = [it for it in items if it.get("source_class") == "news"]
    return len(news) >= NEWS_RULE_MIN_ITEMS and len({owner(it) for it in news}) >= NEWS_RULE_MIN_PUBLISHERS



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


def place_text(title):
    """R129: the title with the place fixes applied and the court names taken out, so a court name names no place."""
    for wrong, right in PLACE_FIXES:
        title = title.replace(wrong, right)
    return COURT.sub(" ", title)


def _title_jurisdictions(title):
    """The ids of the jurisdictions that a title names. 新北 is taken out first, so 新北市 does not name 北市."""
    title = place_text(title)
    plain = title.replace("新北", "\0")
    found = {jid for jid, _, _, terms in JURS if any(term in (title if jid == "jur-65000000" else plain) for term in terms)}
    return found


def _same_level(jid):
    return "special" if jid in SPECIAL_MUNICIPALITIES else "county_city"


SPECIAL_MUNICIPALITIES = ("jur-63000000", "jur-64000000", "jur-65000000", "jur-66000000", "jur-67000000", "jur-68000000")


def split_cases(members):
    """R112.3: the member lists of the topics that one candidate holds. A criminal-case title is another case than the
    other titles of the topic (PRD 4.5 excludes it; R141.3: an arrest, a search or a vote-buying title is one too); it leaves as its own list. Then titles that name two jurisdictions
    of the same level, each alone in SPLIT_MIN_TITLES titles or more, split by jurisdiction. A title with no
    jurisdiction stays with the biggest list. A topic of one case and one jurisdiction returns [members]."""
    crime = [m for m in members if CASE_TITLE.search(m["title"])]
    rest = [m for m in members if not CASE_TITLE.search(m["title"])]
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
        t = place_text(t)
        for jid, _, _, terms in JURS:
            if any(term in t for term in terms):
                counts[jid] += 1
    local = [j for j, c in counts.most_common() if c >= max(1, JURISDICTION_SHARE * len(titles))]
    return local[:3] or ["jur-tw"]


PROGRAM_NOUN = re.compile(r"地圖|計畫|方案|專案|補助|津貼|新制|專線|平台")  # R141.6: a city names its own program with one of these nouns (新北涼適地圖)


def detect_gov_actors(titles, jurisdiction_ids, new=False):
    found = []
    for t in titles:
        if new:
            t = home_text(t)  # R154, R162 (N1): for a new topic a foreign body is no actor of Taiwan
        for pattern, aid, _, _ in CENTRAL:
            if re.search(pattern, t) and aid not in found:
                found.append(aid)
        if LOCAL_GOV.search(t):
            for jid, aid, _, terms in JURS:
                if jid in jurisdiction_ids and aid not in found:
                    found.append(aid)
        elif PROGRAM_NOUN.search(t):  # R141.6: a city name and a program noun name an act of the city government
            named = _title_jurisdictions(t)
            for jid, aid, _, terms in JURS:
                if jid in jurisdiction_ids and jid in named and aid not in found:
                    found.append(aid)
    return found


def election_dispute_without_grade_a(items):
    """R130 (PRD R-10): EXCLUDE_SHARE of the titles is an election dispute (a court ruling on a candidacy), the topic ends inside the
    campaign period, and it has fewer than ELECTION_DISPUTE_MIN_GRADE_A grade A sources."""
    dispute = sum(1 for it in items if ELECTION.search(it["title"]) and ELECTION_LEGAL.search(it["title"]))
    if not items or dispute < EXCLUDE_SHARE["election_campaign"] * len(items):
        return False
    last = max(_day(it["published_on"]) for it in items)
    if not 1 <= (_day(ELECTION_DAY) - last).days <= CAMPAIGN_DAYS:
        return False
    return sum(1 for it in items if it.get("source_class") == "official_record") < ELECTION_DISPUTE_MIN_GRADE_A


SCHOOL_NAME = re.compile(r"([\u4e00-\u9fff]{2,3})(?:高中|國中|國小|高職|中學|小學|大學)")
try:
    SENSITIVE_TITLE_TERMS = tuple(json.loads((Path(__file__).with_name("sensitive_terms.json")).read_text(encoding="utf-8"))["terms"])
except (OSError, ValueError, KeyError):
    SENSITIVE_TITLE_TERMS = ()


def school_name_only(title):
    """R141.6: the crawler flag of a title is sensitive only by the school name (竹南高中生 holds 高中生). True when the title names a
    school and no sensitive term is left after the school names are taken out. A place word before 國中 (台北市國中生) is no school name."""
    names = [m for m in SCHOOL_NAME.finditer(title) if m.group(1)[-1] not in "市縣區鄉鎮的各"]
    if not names:
        return False
    masked = title
    for m in names:
        masked = masked.replace(m.group(0), " ")
    return not any(term in masked for term in SENSITIVE_TITLE_TERMS)


CAMPAIGN_ACT = re.compile(r"站台|助選|後援會|辯論會|電視辯論|選市長|選縣長|選議員|競選看板|競選總部")  # R154 (PRD 4.5 item 5): an act of a campaign
ATTACK = re.compile(r"酸|嗆|轟|開砲|反擊|回擊|槓|打臉|嘲|諷|反酸|批|指控|抹黑|攻擊|霸凌")  # R154: a candidate attacks or answers another
CANDIDATE_NAME = re.compile(r"([\u4e00-\u9fff]{3})(?:宣布|表態|確定|登記|成立競辦|爭取|角逐)?(?:參選|競選|連任|角逐|出線|選市長|選縣長)|(?:提名|候選人|參選人)([\u4e00-\u9fff]{3})")
_CANDIDATES = frozenset()


def candidate_names(corpus):
    """R154: the public figures of Taiwan that stand next to a campaign word (參選, 提名, 候選人) in at least CANDIDATE_MIN_TITLES titles of the corpus."""
    count = Counter()
    for it in corpus:
        count.update({a or b for a, b in CANDIDATE_NAME.findall(it["title"])})
    return {name for name, n in count.items() if n >= CANDIDATE_MIN_TITLES and name in TAIWAN_FIGURE_NAMES}


def set_candidates(names):
    """The run sets the candidates of its corpus once; candidate_talk reads them."""
    global _CANDIDATES
    _CANDIDATES = frozenset(names)


def candidate_talk(title):
    """R154 (PRD 4.5 item 5): a title with a campaign act, or with two candidates and an attack word, judges candidates."""
    named = sum(1 for n in _CANDIDATES if n in title)
    return bool(CAMPAIGN_ACT.search(title)) or (named > 1 and bool(ATTACK.search(title)))


ACCIDENT = re.compile(r"車禍|肇事|撞(?!臉|期|名|衫)|[輾碾]|無呼吸心跳|捲入|墜樓|墜落|墜海|溺水|溺斃|落水|身亡|喪命|不治|命危|重傷|罹難|意外|工安|氣爆|爆炸|火警|火災|起火|落石|翻覆|翻車|倒塌|崩塌")  # R154 (PRD 4.5 item 2): the words of one accident
ACCIDENT_POLICY = re.compile(r"規定|修法|條例|法規|制度|檢討|改善|預算|機制|政策|新制|辦法|草案|強化|加強|通報|補償|賠償")  # R154: a rule after an accident is a policy topic
PUBLIC_ACT = re.compile(r"三讀|修法|條例|草案|預算|立法|法案|釋憲|公告|裁罰|罰款|罰鍰|開罰|補助|公投|官員|公所|稽查|函釋|核定|核准|核釋|審查|質詢|提案|朝野|藍白|在野|綠營|藍營|立院|議會|政府|主管機關|檢調|警方|海巡|消防|部會|法規|法令|規定|新制|政策|公務|公共|監察"
                        r"|颱風|地震|豪雨|大雨|警報|停班|停課|放假|氣象|海嘯|磁暴|雨量|梅雨|防災|災害|疫情|疫苗|病毒|食安|捷運|鐵路|高鐵|道路|橋梁|機場|港口|電價|水庫|缺水|停電|學校|國小|國中|高中|醫院|診所")  # R154: a title that names a public act, a public body or a public service
OFFICIAL_PERSON = re.compile(r"市長|縣長|部長|署長|局長|院長|主委|總統|立委|議員|首長|閣揆|總長|議長")
HEALTH = re.compile(r"住院|住進|開刀|手術|動刀|病倒|病情|罹癌|心臟病|中風|請假休養|確診")


def private_health_of_official(title):
    """R154 (rule 4): the title gives the health of a named official or public figure."""
    return bool(HEALTH.search(title)) and bool(OFFICIAL_PERSON.search(title) or TAIWAN_FIGURE.search(title) or any(n in title for n in _CANDIDATES))


NATURAL_PHENOMENON = re.compile(r"地震|餘震|震度|海嘯|颱風|豪雨|大雨|暴雨|寒流|低溫|高溫|熱浪|降雪|下雪|霧霾|日蝕|月蝕|日食|月食|流星|彗星|極光|天象|超級月亮|彩虹|候鳥|黑面琵鷺|賞鳥|賞花|花季|櫻花|螢火蟲|蝴蝶|鯨豚|白海豚|鯨魚|鯊魚|野生動物")  # R229.2a: the words of an earthquake, weather, astronomy, animal or plant record
CEREMONY = re.compile(r"剪綵|剪彩|啟用|通車|揭牌|動土|開幕|閉幕|典禮|儀式|遊行|遶境|繞境|嘉年華|慶典|燈會|煙火|跨年|音樂節|藝術節|文化節|花火|園遊會")  # R229.2b: the words of a ribbon-cutting, an opening, a parade or a festival
PUBLIC_POWER_ACT = re.compile(r"停班|停課|放假|颱風假|應變中心|疏散|撤離|避難|救助|救災|慰助|履勘|驗收|勘查|查驗|環評|下令|搶修|搶通|搶險|賑災|罰單|處罰|開鍘|懲處|預算|經費|補助|補貼|津貼|三讀|修法|立法|條例|草案|法案|法規|新制|新規|規定|辦法|政策|函釋|裁罰|罰鍰|罰款|開罰|處分|稽查|查核|核定|核准|判決|裁定|釋憲|公告|決議|決定|禁令|管制|禁止|徵收|招標|採購|補償|賠償")  # R229.2c: a decision, a budget, a law or rule change, a ruling, a penalty, a subsidy or an emergency order; a remark (表示, 說明, 呼籲) is not an act

def public_act_title(text):
    """R229.2c, R234.3: a title names a public-power act. The works and ad hoc words need a public body, so a private firm does not count (R234.5)."""
    if PUBLIC_POWER_ACT.search(text):
        return True
    return bool((PUBLIC_WORKS_ACT.search(text) or AD_HOC_ACT.search(text)) and (names_government(text, True) or names_public_body(text)))


def no_public_act(titles):
    """R225.1, R229.2: a cluster of natural phenomena (earthquake, weather, astronomy, animal or plant records) or of ceremonies
    (ribbon-cutting, opening, parade, festival) with no title that names a public-power act. The cluster is a record or an event, not an issue."""
    n = max(1, len(titles))
    texts = [home_text(t) for t in titles]
    if sum(1 for t in texts if NATURAL_PHENOMENON.search(t) or CEREMONY.search(t)) < PHENOMENON_SHARE * n:
        return False
    return sum(1 for t in texts if public_act_title(t)) < ACT_MIN_TITLES


NEW_TOPIC_ONLY = ("rejected_issue_name", "rejected_keyword_bundle", "rejected_candidate_attack", "rejected_single_accident", "rejected_official_health", "rejected_private_matter", "rejected_mixed_cluster", "rejected_government_scope", "rejected_mixed_ministry", "rejected_no_public_act")  # R154, R196, R215.3, R229: the labels of the rules that only a new topic must pass


def new_topic_reason(items):
    """R154: the exclusions that only a new topic must pass. Returns a rejected_* label without the prefix, or None.
    candidate_attack: PRD 4.5 item 5. single_accident: PRD 4.5 item 2. official_health: rule 4. private_matter: PRD 4.5 item 1."""
    n = max(1, len(items))
    titles = [it["title"] for it in items]
    if sum(1 for t in titles if candidate_talk(t)) >= CANDIDATE_SHARE * n:
        return "candidate_attack"
    if sum(1 for t in titles if ACCIDENT.search(t)) >= ACCIDENT_SHARE * n \
            and sum(1 for t in titles if ACCIDENT_POLICY.search(t)) < ACCIDENT_POLICY_SHARE * n:
        return "single_accident"
    if sum(1 for t in titles if private_health_of_official(t)) >= OFFICIAL_HEALTH_SHARE * n:
        return "official_health"
    if sum(1 for t in titles if names_government(t, True) or PUBLIC_ACT.search(home_text(t))) < GOV_ACT_SHARE * n:
        return "private_matter"
    if no_public_act(titles):  # R229.2
        return "no_public_act"
    return None


def exclusion_reason(items, skip=(), new=False):
    n = max(1, len(items))
    crime = CRIME_NEW if new else CRIME
    shares = {
        "sensitive": sum(1 for it in items if it.get("sensitive") and not LAW_PASSED.search(it["title"]) and not school_name_only(it["title"])) / n,
        "election_campaign": sum(1 for it in items if ELECTION.search(it["title"]) and not ELECTION_LEGAL.search(it["title"])) / n,
        "criminal_case": sum(1 for it in items if crime.search(it["title"])) / n,
        "entertainment": sum(1 for it in items if ENTERTAINMENT.search(it["title"]) and not CONSUMER.search(it["title"])) / n,
    }
    has_official = any(it.get("source_class") in ("official_statement", "official_record") for it in items)
    for reason in ("sensitive", "criminal_case", "election_campaign", "entertainment"):
        if reason in skip:
            continue
        if reason == "criminal_case" and has_official:
            continue
        if reason == "election_campaign" and election_dispute_without_grade_a(items):
            return reason
        if shares[reason] >= EXCLUDE_SHARE[reason]:
            return reason
    return None


def issue_profile(key, members):
    """R154, R162: what the duplicate-issue test compares: the key, the first and last day of the members, and for each term of
    DUPLICATE_NEAR_TERM_LEN characters or more the number of member titles that hold it."""
    days = [_day(m["published_on"]) for m in members]
    terms = Counter()
    for m in members:
        terms.update(g for g in tp._grams(m["title"]) if len(g) >= DUPLICATE_NEAR_TERM_LEN)
    return {"key": key, "first": min(days), "last": max(days), "terms": terms, "actors": profile_actors(members), "act": act_part(key)}


ACTOR_WORDS = re.compile("|".join([p for p, _, _, _ in CENTRAL] + [tp.PLACE.pattern, LOCAL_GOV.pattern]))
GENERIC_END = re.compile(r"(?:案|法|事件|爭議|問題)$")


def profile_actors(members):
    """R196.7: the central bodies that ACTOR_SHARE of the member titles names."""
    n = max(1, len(members))
    return {aid for pattern, aid, _, _ in CENTRAL if sum(1 for m in members if re.search(pattern, home_text(m["title"]))) >= ACTOR_SHARE * n}


def act_part(key):
    """R196.7: the key without its bodies, places and generic end (監察院人事同意權案 -> 人事同意權, 監委人事案 -> 人事)."""
    return GENERIC_END.sub("", ACTOR_WORDS.sub("", key))


def same_actor_act(a, b):
    """R196.7: the topics name one body in most titles, and the act parts of the keys share ACT_MATCH_LEN characters or more."""
    if not (a.get("actors", set()) & b.get("actors", set())):
        return False
    x, y = a.get("act", ""), b.get("act", "")
    return len(x) >= ACT_MATCH_LEN and len(y) >= ACT_MATCH_LEN and any(x[i:i + ACT_MATCH_LEN] in y for i in range(len(x) - ACT_MATCH_LEN + 1))


def key_bodies(key):
    """R203, R215.1: the central bodies (one actor id per body: 監委 and 監察院 are one) and the places that a key names."""
    return {aid for pattern, aid, _, _ in CENTRAL if re.search(pattern, key)} | _title_jurisdictions(key)


def same_issue(a, b, df):
    """R154, R162: two topics (new or old) are one issue when their days are at most DUPLICATE_GAP_DAYS apart and one key holds the
    other (兄弟姊妹 and 兄弟姊妹特留分), or they share a rare term that DUPLICATE_MIN_TITLES titles of each hold: a term of
    DUPLICATE_TERM_LEN characters (玄濟宮, 副署無人載具條例), or of DUPLICATE_NEAR_TERM_LEN characters that both keys hold when the
    topics are at most DUPLICATE_NEAR_DAYS days apart (立院三讀免健保費 and 長者有條件免健保費)."""
    gap = max((a["first"] - b["last"]).days, (b["first"] - a["last"]).days)
    if gap > DUPLICATE_GAP_DAYS:
        return False
    bodies_a, bodies_b = key_bodies(a["key"]), key_bodies(b["key"])
    if bodies_a and bodies_b and not bodies_a & bodies_b:  # R203, R215.1: two government bodies are two issues, also when the keys share a term (部人事案)
        return False
    if a["key"] in b["key"] or b["key"] in a["key"]:
        return True
    near = gap <= DUPLICATE_NEAR_DAYS
    if near and same_actor_act(a, b):  # R196.7: 監察院人事同意權案 and 監委人事案
        return True
    return any((len(g) >= DUPLICATE_TERM_LEN or (near and g in a["key"] and g in b["key"]))
               and c >= DUPLICATE_MIN_TITLES and b["terms"].get(g, 0) >= DUPLICATE_MIN_TITLES and df.get(g, 0) <= DUPLICATE_TERM_MAX_DF
               for g, c in a["terms"].items())


def is_duplicate_issue(profile, issues, df):
    """R162: the profile is one issue with a profile in `issues` (old topics, published topics and skipped duplicates). The caller adds the
    profile of a skipped duplicate to `issues`, so a third topic that links to the duplicate only is a duplicate too: the test works
    across 3 topics or more."""
    return any(same_issue(profile, other, df) for other in issues)


def topic_id(key, first_day, first_url):
    h = hashlib.sha1(f"{key}|{first_url}".encode()).hexdigest()[:8]
    return f"ev-{first_day.replace('-', '')}-topic-{h}"


def _editor_approved(text):
    """R141.1: the front matter of the event has review.status editor-approved."""
    return bool(re.search(r"^review:\n(?:[ \t]+\S.*\n)*?[ \t]+status: ['\"]?editor-approved", text, re.M))


def published_topics(root, ref="HEAD"):
    """System topics that a commit already publishes: id, title, the first and last date, the cited source ids and the editor-approved flag (R141.1).
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
                        "src_ids": set(re.findall(r"src-[0-9a-z-]+", t)), "approved": _editor_approved(t)})
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
    git ref first. A topic that is withdrawn already stays as it is and writes no new record (R105). An editor-approved topic stays as it is too (R141.1).
    Returns the file path."""
    root = Path(root)
    year = event_id.split("-")[1][:4]
    path = root / "events" / year / f"{event_id}.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_event_text(root, event_id, ref), encoding="utf-8")
    doc, body = _read_event(path)
    if doc.get("status") == "withdrawn" or (doc.get("review") or {}).get("status") == "editor-approved":  # R141.1: an editor decides on an approved topic
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


def limit_withdrawals(due, published_total):
    """R133: (allowed, blocked). A run that would withdraw more than WITHDRAW_MAX_COUNT topics, or more than
    WITHDRAW_MAX_SHARE of the published system topics (one topic is always allowed), withdraws none."""
    if len(due) > WITHDRAW_MAX_COUNT or len(due) > max(1, WITHDRAW_MAX_SHARE * published_total):
        return {}, dict(due)
    return dict(due), {}


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


def recorded_name_passes(name, titles):
    """R134, R141.2: the structural name tests for the recorded name of an old topic. The key statistics test a key that was just
    picked, so they do not apply to a name that an editor or an earlier run published."""
    return noun_phrase_name(name) and not generic_name(name) and not is_person_or_party(name, titles) and not is_place_name(name)


def gate_topic(key, members, seeds, df, corpus, existing_keys=(), window=None, known=None, mf=None, rebuilds_old=False):
    """The gates of one member list, in order: name quality, foreign, existing event, exclusion, government actor, Taiwan,
    name. Returns (outcome, found). The outcome is "ok", "skipped_existing_event" or a rejected_* label. `found` holds the
    jurisdictions, the actors and the name of a topic that passes. `existing_keys` and `window` (lo, hi) are for a new candidate only.
    `known` (R134, R135) is an old topic: its recorded name, jurisdictions, actors and sensitive flag. Its name gets the structural
    name tests only, because the key statistics test a key that was just picked. Its recorded jurisdictions, actors and flag count
    when the titles name none. `rebuilds_old` (R155.4, R168) marks a candidate that rebuilds a published old topic: the rules of a new
    topic do not apply to it, as they do not apply to `known`."""
    titles = [m["title"] for m in members]
    if known:
        if not recorded_name_passes(known["name"], titles):
            return "rejected_name_quality", None
    elif not name_quality_ok(key, titles, df.get(key, 0) or sum(1 for it in corpus if key in it["title"]), len(members), df, new=not rebuilds_old):
        return "rejected_name_quality", None
    local_known = [j for j in (known or {}).get("jids", []) if j != "jur-tw"]
    new = not known and not rebuilds_old  # R155.4, R162 (N1), R168: the rules of a new topic do not change the result for an old topic
    irrelevant = not taiwan_relevant(titles, new) and not local_known
    if irrelevant and names_foreign(titles, new):  # R112.5: only a title that names a foreign country gets the foreign label
        return "rejected_foreign", None
    if window and (any((k in key or key in k) and s_lo <= window[1] and window[0] <= s_hi for k, s_lo, s_hi in existing_keys) or any(
            s_lo <= window[1] and window[0] <= s_hi and sum(1 for t in titles if k in t) >= SAME_EVENT_SHARE * len(titles)
            for k, s_lo, s_hi in existing_keys)):
        return "skipped_existing_event", None
    reason = exclusion_reason(members, skip=("sensitive",) if known and known.get("sensitive") else (), new=new) or (new_topic_reason(members) if new else None)
    if reason:
        return "rejected_" + reason, None
    jids = detect_jurisdictions(titles)
    if jids == ["jur-tw"] and local_known:
        jids = local_known
    actors = detect_gov_actors(titles, jids, new)
    if not actors and known:
        actors = list(known.get("actors", []))
    for m in members:
        host = (m["url"].split("/")[2] if "//" in m["url"] else "")
        if m.get("source_class") == "official_statement" and host in tp.HOSTS and tp.HOSTS[host][1] not in actors:
            actors.append(tp.HOSTS[host][1])
    if not actors:
        return "rejected_no_gov_actor", None
    if irrelevant:  # the gate still rejects a topic with no Taiwan term; a later gate above gave the label first
        return "rejected_not_taiwan", None
    off = []
    if new:
        off, mixed = scope_levels(titles, jids == ["jur-tw"])  # R196.4, R196.6
        if mixed:
            return "rejected_mixed_cluster", None
        if len(titles) - len(off) < SEED_MIN_ITEMS:
            return "rejected_government_scope", None
    name = known["name"] if known else tp.display_name(key, [s["title"] for s in seeds])
    if not noun_phrase_name(name) or generic_name(name):
        return "rejected_name_quality", None
    if not known and not (issue_name(name) and new_name_ok(key, titles)):
        return "rejected_issue_name", None
    if not known and mf is not None and theme_word(key, mf.months):
        return "rejected_keyword_bundle", None  # R162: the key is a theme word that joins many cases
    if new and mixed_ministry(name, titles):  # R207, R215.3
        return "rejected_mixed_ministry", None
    if not known and not t32_name_ok(key, name, titles):  # R196.1, R196.2, R196.3, R196.8: a rebuild of an old topic gets a new name from its key, so the name tests apply to it too
        return "rejected_issue_name", None
    return "ok", {"jids": jids, "actors": actors, "name": name, "name_jids": place_scope(titles, jids) if new else jids, "off_level": {members[i]["url"] for i in off}}


def build_checked(seed, corpus, df, members):
    """Builds the topic and applies the source gates of PRD 4.4. Returns (event, rejected_* label or None)."""
    ev = tp.build_event(seed, corpus, df, items=members)
    used = list(ev["used"].values())
    if not meets_source_rule(used):
        return ev, "rejected_source_rule"
    if not meets_news_rule(used):
        return ev, "rejected_news_rule"
    return ev, None


def write_topic(root, ev, seed, today):
    """Writes a topic that passed. Restores its correction ids (R105). Returns the republication record id or None."""
    used = list(ev["used"].values())
    ev["review"]["sensitive"] = "misconduct" in seed["controversy_types"] or has_sensitive_term([it["title"] for it in used])
    ensure_actor_files(root, [a for a, _ in ev["actors"]])
    prior = prior_event(root, ev["id"])
    tp.write_event(ev, seed, root, {}, actors_by_host=tp.HOSTS, overwrite_sources=False)
    return republish_topic(root, ev["id"], prior, today)


JUR_NAME = {jid: name[:-2] for jid, _, name, _ in JURS}


def old_system_topics(root):
    """R126: (path, front matter, text) of each published system topic with review.status draft-review. A topic with
    another review status (editor-approved) is not in the list."""
    out = []
    for p in sorted((Path(root) / "events").glob("*/ev-*.md")):
        text = p.read_text(encoding="utf-8")
        doc, _ = _read_event(p)
        review = doc.get("review") or {}
        if doc.get("status") == "published" and review.get("status") == "draft-review" and str(review.get("reason", "")).startswith(SYSTEM_REASON):
            out.append((p, doc, text))
    return out


def regate_seed(doc, text, seed, urls_by_id, by_url):
    """The seed of an old topic: its entry in the seed file, or the sources that its file cites."""
    cited = list(dict.fromkeys(re.findall(r"src-[0-9a-z-]+", text)))
    if seed:
        seed = dict(seed, actors=[tuple(a) for a in seed["actors"]])
    else:
        jids = doc.get("jurisdiction_ids", [])
        seed = {"event_id": doc["id"], "seed_urls": [urls_by_id[c] for c in cited if c in urls_by_id],
                "jurisdiction_ids": jids, "jurisdiction_names": [JUR_NAME[j] for j in jids if j in JUR_NAME],
                "gov_levels": doc.get("gov_levels", []), "controversy_types": doc.get("controversy_types", []),
                "policy_domains": doc.get("policy_domains", []), "sensitive": bool((doc.get("review") or {}).get("sensitive")),
                "actors": [(a["actor_id"], a["role"]) for a in doc.get("actors", [])]}
    seed["seed_urls"] = [u for u in seed["seed_urls"] if u in by_url]
    return seed, set(cited)


def file_items(root, ids):
    """R132: the items that the source files of a topic record (url, title, date, publisher, class)."""
    import yaml
    out = []
    for p in sorted((Path(root) / "sources").glob("*/*.yaml")):
        if p.stem in ids:
            d = yaml.safe_load(p.read_text(encoding="utf-8"))
            out.append({"url": d["url"], "title": d["title"], "published_on": str(d["published_on"]), "publisher": d["publisher"],
                        "source_class": d["source_class"], "quote": d.get("quote")})
    return out


GENRE_WORD = re.compile(tp.CLAR.pattern + r"|錯誤|誤導|謠言|網傳|資訊")  # R141.3: a word that names the kind of title (a clarification), not its issue


def second_anchor_members(members, core, keys, df, total):
    """R141.3: the members whose title has a second anchor of the on-topic titles (`core`: the members that the corpus confirms,
    after the case split). The key is in every member already. A seed title has no right of its own: the seeds of an old topic can
    hold an off-topic story, and a response (a clarification or a release) answers one issue only when it holds the anchor too.
    A word that names the kind of title (錯誤, 澄清) is no anchor. The members stay as they are when the core shares no anchor."""
    second = {a for a in tp.second_anchors([m["title"] for m in core], keys, df, total) if not GENRE_WORD.search(a)}
    return [m for m in members if not second or tp.has_anchor(m["title"], second)]


def regate_topic(root, doc, text, seed, corpus, df, by_url, urls_by_id, today):
    """R126: checks one old topic with the current gates. The members are built again (R112.1) and the ID stays.
    Returns the record of the check: id, gate (None when it passes), the source ids before and after, the titles."""
    seed, before = regate_seed(doc, text, seed, urls_by_id, by_url)
    record = {"id": doc["id"], "gate": None, "title_before": doc["title"], "title_after": doc["title"], "removed": [], "before": len(before), "after": len(before)}
    if not seed["seed_urls"]:
        record["gate"] = "no_corpus_items"  # the corpus holds none of its sources: nothing to check
        return record
    members = tp.members(seed, corpus, df)
    keys = seed["_keys"]
    if not keys or not any(m.get("source_class") in ("news", "fact_check") for m in members):
        record["gate"] = "rejected_no_key" if not keys else "rejected_no_news"
        return record
    # R132: a source of the file stays when the corpus lacks it, unless its own title fails the membership rule (R112.1, R141.3).
    # R141.2: a recorded name that passes the structural tests replaces the new key; the boundary extension of the key does not cut the members.
    name = PLACE_PREFIX.sub("", doc["title"], count=1)
    have = {m["url"] for m in members}
    extras = [it for it in file_items(root, before) if it["url"] not in have and it["url"] not in by_url]
    recorded = recorded_name_passes(name, [m["title"] for m in members + extras if name in m["title"] or any(k in m["title"] for k in keys)])
    matchers = [name] + keys if recorded else keys
    members = members + [it for it in extras if any(k in it["title"] for k in matchers)]
    members.sort(key=lambda m: (m["published_on"], m["url"]))
    key = keys[0]
    if recorded and any(name in m["title"] for m in members):
        key = name
    else:
        full = extend_to_boundary(key, [m["title"] for m in members])
        if full != key:
            members, key = [m for m in members if full in m["title"]], full
    seed_urls = set(seed["seed_urls"])
    members = max(split_cases(members), key=lambda g: (sum(1 for m in g if m["url"] in seed_urls), len(g)))  # R112.3
    members = second_anchor_members(members, [m for m in members if m["url"] in by_url] or members, keys, df, len(corpus))  # R141.3
    record["dropped"] = sorted(before - {tp.src_id(m, tp.HOSTS) for m in members})  # the file sources that the membership rule does not keep
    seeds = [by_url[u] for u in sorted(seed_urls, key=lambda u: (by_url[u]["published_on"], u))]
    known = {"name": name, "jids": doc.get("jurisdiction_ids", []),
             "actors": [a["actor_id"] for a in doc.get("actors", [])], "sensitive": bool((doc.get("review") or {}).get("sensitive"))}
    outcome, found = gate_topic(key, members, seeds, df, corpus, known=known)  # R134: the name of an old topic changes only by rule (R69)
    if outcome != "ok":
        record["gate"] = outcome
        return record
    seed["_keys"], seed["_name"] = [key], found["name"]
    ev, gate = build_checked(seed, corpus, df, members)
    if gate:
        record["gate"] = gate
        return record
    ev["title"] = doc["title"]  # the recorded name stays, so the title stays
    relations = doc.get("relations")
    write_topic(root, ev, seed, today)
    if relations:
        path = Path(root) / "events" / doc["id"].split("-")[1][:4] / f"{doc['id']}.md"
        new, body = _read_event(path)
        out = {}
        for k, v in new.items():
            if k == "privacy":
                out["relations"] = relations
            out[k] = v
        _write_event(path, out, body)
    after = {tp.src_id(it, tp.HOSTS) for it in ev["used"].values()}
    record.update(title_after=ev["title"], removed=sorted(before - after), after=len(after), key=key)
    return record


def source_urls_by_id(root):
    """{source id: url} of the source files in the archive."""
    urls = {}
    for p in (Path(root) / "sources").glob("*/*.yaml"):
        m = re.search(r'^url: "?([^"\n]+)"?$', p.read_text(encoding="utf-8"), re.M)
        if m:
            urls[p.stem] = m.group(1)
    return urls


def run(corpus, clusters, existing_seeds, root, report_path, today=None, approve_withdraw=None):
    set_officials(office_holders(corpus))  # R141.5
    set_candidates(candidate_names(corpus))  # R154
    df = tp.document_frequency(corpus)
    mf = MonthFrequency(corpus)
    by_url = {it["url"]: it for it in corpus}
    stats = Counter()
    published_ids = published_topics(root)
    failed, covered = {}, set()  # R82: published topic id -> first failed gate; ids that another candidate keeps
    deferred = set()  # R202, R205: old topics that a rebuild left to the re-gate because the rebuild got a name reject for a new topic

    def src_ids_of(urls):
        return {tp.src_id(by_url[u], tp.HOSTS) for u in urls if u in by_url}

    approved = {p["id"] for p in published_ids if p.get("approved")}  # R141.1: an editor-approved topic never fails a run

    def fail(gate, urls):
        for pid in matching_published(published_ids, src_ids_of(urls)):
            if pid not in approved:
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
    existing_keys, existing_key_by_id, old_issues = [], [], []
    for s in existing_seeds:
        taken.update(s["seed_urls"])
        seed_items = [by_url[u] for u in s["seed_urls"] if u in by_url]
        if seed_items:
            probe = dict(s)
            old_members = tp.members(probe, corpus, df)  # the same key that the event was built with
            ks = probe["_keys"]
            if ks and old_members:
                old_issues.append((issue_profile(ks[0], old_members), {m["url"] for m in old_members}))  # R162: a new topic on the issue of an old topic is not published
            if ks:
                existing_key_by_id.append((s["event_id"], ks[0]))
            days = sorted(_day(i["published_on"]) for i in seed_items)
            existing_keys += [(k, days[0] - timedelta(days=tp.WINDOW_BEFORE), days[-1] + timedelta(days=tp.WINDOW_AFTER)) for k in ks]
    urls_by_id = source_urls_by_id(root)
    for _, doc, text in old_system_topics(root):  # R162: the old system topics count for the duplicate test too
        cited = [by_url[urls_by_id[c]] for c in dict.fromkeys(re.findall(r"src-[0-9a-z-]+", text)) if c in urls_by_id and urls_by_id[c] in by_url]
        if cited:
            old_issues.append((issue_profile(PLACE_PREFIX.sub("", doc["title"], count=1), cited), {it["url"] for it in cited}))
    # Bigger topics first, so a duplicate keeps the larger one.
    ordered = sorted(merged.items(), key=lambda kv: (-len(kv[1]), kv[0][1], kv[0][0]))
    window_items = sorted(corpus, key=lambda j: j["published_on"])
    out_seeds, published, published_sets, published_issues = [], [], [], []
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
            member_urls = {m["url"] for m in members}
            rebuilds_old = any(len(member_urls & old_urls) >= MERGE_OVERLAP * min(len(member_urls), len(old_urls)) for _, old_urls in old_issues)
            outcome, found = gate_topic(key, members, seeds, df, corpus, existing_keys, (lo, hi), mf=mf, rebuilds_old=rebuilds_old)
            if outcome == "skipped_existing_event":
                stats[outcome] += 1
                keep([m["url"] for m in members])
                continue
            if outcome != "ok":
                stats[outcome] += 1
                if outcome not in NEW_TOPIC_ONLY:  # R155.4: the rules of a new topic do not fail an old topic; its re-gate decides
                    fail(outcome, [m["url"] for m in members])
                elif rebuilds_old:  # R205: no other candidate may fail this old topic either
                    deferred.update(matching_published(published_ids, src_ids_of([m["url"] for m in members])))
                continue
            jids, actors, name = found["jids"], found["actors"], found["name"]
            if found["off_level"]:  # R196.6: a title of another government level fails (b)
                members = [m for m in members if m["url"] not in found["off_level"]]
                stats["scope_titles_removed"] += len(found["off_level"])
            local = [j for j in found["name_jids"] if j != "jur-tw"]  # R196.5: a place that not every title names stays out of the name
            names = [next(n for jid, _, n, _ in JURS if jid == j)[:-2] for j in local]
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
            profile = issue_profile(key, members)
            other_old_issues = [p for p, old_urls in old_issues if len(urls & old_urls) < MERGE_OVERLAP * min(len(urls), len(old_urls))]  # a candidate that rebuilds an old topic is no duplicate of it
            if is_duplicate_issue(profile, published_issues + other_old_issues, df):  # R154, R162: one issue gives one topic, old topics and skipped duplicates included
                stats["skipped_duplicate_issue"] += 1
                published_issues.append(profile)
                keep(urls)
                continue
            ev, gate = build_checked(seed, corpus, df, members)
            if gate:
                stats[gate] += 1
                fail(gate, urls)
                continue
            used = list(ev["used"].values())
            if write_topic(root, ev, seed, today or date.today().isoformat()):
                stats["republished"] += 1
            published.append({"id": ev["id"], "title": ev["title"], "sources": len(used), "key": key})
            published_sets.append(urls)
            published_issues.append(profile)
            out_seeds.append({k: v for k, v in seed.items() if not k.startswith("_")})
    stats["published"] = len(published)
    covered.update(p["id"] for p in published)
    # R126: every other published system topic with review.status draft-review is checked again with the current gates.
    for pid in deferred:  # R205: the re-gate decides for a deferred old topic
        failed.pop(pid, None)
    done = {p["id"] for p in published} | {pid for pid in failed if pid not in covered}  # a topic that a candidate rebuilt or failed has its result
    seed_by_id = {s["event_id"]: s for s in existing_seeds}
    regated, regate_keys = [], {}
    for path, doc, text in old_system_topics(root):
        if doc["id"] in done:
            continue
        rec = regate_topic(root, doc, text, seed_by_id.get(doc["id"]), corpus, df, by_url, urls_by_id, today or date.today().isoformat())
        regated.append(rec)
        stats["regate_checked"] += 1
        if rec["gate"] == "no_corpus_items":
            stats["regate_no_corpus_items"] += 1
        elif rec["gate"]:
            stats["regate_failed"] += 1
            stats["regate_" + rec["gate"]] += 1
            failed[doc["id"]] = rec["gate"]
            covered.discard(doc["id"])
        else:
            stats["regate_passed"] += 1
            stats["regate_members_removed"] += len(rec["removed"])
            stats["regate_renamed"] += rec["title_after"] != rec["title_before"]
            covered.add(doc["id"])
            regate_keys[doc["id"]] = rec["key"]
    failing = {pid: gate for pid, gate in failed.items() if pid not in covered}
    kept_withdrawn = {pid: gate for pid, gate in failing.items() if prior_event(root, pid)[0] == "withdrawn"}
    day = today or taipei_day()
    old_state = read_topic_state(root)
    state, withdrawn, pending = apply_hysteresis(old_state, {p: g for p, g in failing.items() if p not in kept_withdrawn}, day)
    allowed_ids = set(approve_withdraw or ())  # R218, R221: a due topic is withdrawn only when its id is in the approval list
    approval_ignored = sorted(allowed_ids - set(withdrawn))
    unapproved = {p: g for p, g in withdrawn.items() if p not in allowed_ids}
    withdrawn, limited = limit_withdrawals({p: g for p, g in withdrawn.items() if p in allowed_ids}, len(old_system_topics(root)))  # R133
    blocked = {**unapproved, **limited}
    blocked_reason = {**{p: "needs_user_approval" for p in unapproved}, **{p: "withdraw_limit" for p in limited}}
    for pid, gate in blocked.items():  # the fail count stays; the PM decides
        prior = old_state.get(pid, {})
        state[pid] = {"fails": prior.get("fails", 0) + (0 if prior.get("day") == day else 1), "gate": gate, "day": day}
    for pid, gate in sorted({**kept_withdrawn, **withdrawn}.items()):
        withdraw_topic(root, pid, gate, today=today)  # a withdrawn topic gets its file back and no new record
    write_topic_state(root, state)
    stats["withdrawn"] = len(withdrawn)
    stats["withdraw_blocked"] = len(blocked)
    stats["withdraw_pending"] = len(pending)
    stats["withdrawn_kept"] = len(kept_withdrawn)
    keys = {k[0]: k[1] for k in existing_key_by_id}
    keys.update({p["id"]: p["key"] for p in published})
    keys.update(regate_keys)
    links = apply_subtopic_links(root, keys)
    stats["part_of_links"] = len(links)
    stats["sensitive_from_sources"] = len(refresh_sensitive(root))
    Path(report_path).write_text(json.dumps({"stats": stats, "published": published, "part_of": links, "withdrawn": withdrawn, "withdraw_blocked": blocked, "regate": regated,
                                "withdraw_blocked_reason": blocked_reason, "approval_ignored": approval_ignored}, ensure_ascii=False, indent=1),
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


def parse_today(args):
    """R141.7: (args without the option, the day). The day is None without the option. Raises ValueError for a missing or bad day."""
    if "--today" not in args:
        return args, None
    i = args.index("--today")
    if i + 1 >= len(args):
        raise ValueError("--today needs a day")
    day = args[i + 1]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("--today needs YYYY-MM-DD")
    date.fromisoformat(day)
    return args[:i] + args[i + 2:], day


def parse_approve_withdraw(args):
    """R221: (args without the option, the approval file). The file is None without the option. Raises ValueError for a missing file name."""
    if "--approve-withdraw" not in args:
        return args, None
    i = args.index("--approve-withdraw")
    if i + 1 >= len(args):
        raise ValueError("--approve-withdraw needs a file")
    return args[:i] + args[i + 2:], args[i + 1]


def read_approval_file(path):
    """R221: the set of event ids in the file, one id per line. Empty lines are ignored."""
    return {line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()}


def main(argv):
    try:
        args, today = parse_today(list(argv[1:]))
        args, approve_file = parse_approve_withdraw(args)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 2
    if len(args) != 5:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    corpus = tp.read_jsonl(args[0])
    clusters = json.load(open(args[1], encoding="utf-8"))
    existing = json.load(open(args[2], encoding="utf-8"))
    stats, published, _ = run(corpus, clusters, existing, args[3], args[4], today=today,
                              approve_withdraw=read_approval_file(approve_file) if approve_file else None)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
