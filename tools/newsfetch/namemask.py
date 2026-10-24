"""Masks private person names in titles and snippets. Standard library only.

A name candidate is a surname plus 1 or 2 given-name characters (2-4 characters).
A candidate is masked only in one of three contexts:
  1. after an action or role word (載, 帶, 男子, 警員 ...),
  2. before a verdict or action word (涉, 遭, 被, 起訴, 落網 ...),
  3. before an age in brackets (張三（35歲）).
A name on the public-figure allowlist is never masked. Place and organisation
words in GUARD_WORDS are never masked. An editor maintains GUARD_WORDS.
"""

import re
from typing import Iterable, List, Set, Tuple

MASK = "[當事人]"

# About 100 common Taiwanese surnames. Single characters that are also common words
# (金, 龍, 萬, 文, 武, 常, 易, 白, 方, 田, 石, 任) are left out to avoid false masks.
SINGLE_SURNAMES = (
    "陳林黃張李王吳劉蔡楊許鄭謝郭洪曾邱廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾彭游詹胡施沈余趙盧梁"
    "顏柯孫魏翁戴范宋方鄧杜傅侯曹薛丁卓馬阮董唐温溫藍蔣石古紀姚連馮歐程湯田康姜汪白鄒尤巫鐘黎涂龔嚴韓袁金"
)
# Drop the words-too-common ones from the single list.
_DROP = set("金方田石白")
SINGLE_SURNAMES = "".join(c for c in SINGLE_SURNAMES if c not in _DROP)
COMPOUND_SURNAMES = ("歐陽", "司馬", "諸葛", "上官", "范姜", "張簡", "夏侯", "皇甫", "令狐", "東方", "司徒", "公孫")

_SURNAME_ALT = "|".join(list(COMPOUND_SURNAMES) + list(SINGLE_SURNAMES))
_HAN = r"[一-鿿]"

# Words that come before a person name.
ACTION_WORDS = (
    "帶回|逮捕|拘提|傳喚|約談|逮獲|通緝|指控|控告|載|帶|找|幫|助|邀|控|告|偕|與|和|同|陪|跟|替|供稱|指稱|表示|"
    "男子|女子|少年|少女|嫌犯|嫌疑人|嫌|被告|原告|被害人|受害人|死者|傷者|乘客|駕駛|司機|運將|"
    "警員|員警|警官|醫師|護理師|老師|教練|店員|學生|同學|房東|鄰居|業者|"
    "兒子|女兒|母親|父親|妻子|丈夫|前夫|前妻|男友|女友|友人"
)
# Words that come after a person name.
VERDICT_WORDS = (
    "涉|遭|被|嫌|判|獲判|起訴|不起訴|羈押|收押|聲押|交保|落網|肇事|死亡|罹難|喪生|身亡|不治|送醫|受傷|失聯|失蹤|"
    "遇害|輕生|墜海|墜樓|落海|溺水|猝死|認罪|否認|自首|投案|求刑|宣判|約談|逮捕|被捕|酒駕|毒駕|詐|偷|搶|殺|砍|"
    "無罪|定讞|重判|逃逸|持刀|"
    r"[(（]\s*(?:年約|約|年僅|未滿)?\d{1,3}(?:多|出頭)?歲?\s*[)）]"
)

# Place, organisation and word guards: a candidate that starts with one of these is skipped.
GUARD_WORDS = (
    "高雄", "高鐵", "高速", "高中", "高層", "高齡", "高溫", "高壓", "高等", "高端", "高階", "高額", "高度",
    "高峰", "高價", "高職", "高工", "高市", "高風險", "高科", "高教", "高低", "高空", "高空", "高處", "高灘",
    "林口", "林園", "林內", "林務", "林業", "林地", "林場", "林森", "林肯", "林相",
    "張家界", "李先", "周邊", "周遭", "周圍", "周全", "周知", "周年", "周休", "周刊",
    "馬祖", "馬公", "馬來", "馬達", "馬路", "馬拉", "馬斯克",
    "王品", "王國", "王者", "王道", "王牌", "王朝",
    "古蹟", "古坑", "古早", "古物", "古都", "古道",
    "江山", "江湖", "江南", "江蘇", "江西",
    "康復", "康健", "康樂", "康寧", "康軒",
    "施工", "施政", "施作", "施放", "施壓", "施打", "施行", "施予", "施測",
    "連線", "連結", "連續", "連假", "連日", "連江", "連署", "連動", "連任", "連同", "連環", "連帶", "連夜",
    "游泳", "游說", "游客", "游擊",
    "湯圓", "沈默", "孫子",
    "紀錄", "紀念", "紀律", "紀要", "紀事", "紀實",
    "藍綠", "藍白", "藍營", "藍天", "藍鵲", "藍色",
    "嚴重", "嚴格", "嚴正", "嚴禁", "嚴查", "嚴懲", "嚴防", "嚴肅", "嚴厲", "嚴峻", "嚴選", "嚴辦", "嚴管", "嚴審",
    "程序", "程度", "程式", "程式",
    "傅統", "程小", "簡訊", "簡易", "簡化", "簡報", "簡單", "簡介", "簡稱", "簡直", "簡併", "簡政",
    "戴上", "戴口罩",
    "洪水", "洪災", "洪峰",
    "曾經", "曾任", "曾表示", "曾說", "曾指",
    "何時", "何謂", "何況", "何不", "何以", "何必", "何在", "何處",
    "朱古", "高志", "卓越", "卓著", "卓見", "卓然",
    "黎明", "黎巴嫩", "鄭重", "鄭成功", "劉海", "楊柳",
    "潘朵", "余額", "余裕", "余震", "梁柱", "蘇花", "蘇澳", "蘇丹", "蘇俄", "蘇聯", "蘇打", "蘇格蘭",
    "賴皮", "莊園", "莊稼", "葉片", "葉菜", "謝絕", "謝謝", "謝罪", "謝票", "謝神", "魏晉", "薛丁格",
    "盧森堡", "呂宋", "尤其", "尤指", "吳郭魚", "徐州", "徐徐", "施耐德", "鍾點", "鐘點", "鐘擺", "鐘錶",
    "古巴", "古埃及", "歐盟", "歐洲", "歐美", "歐元", "歐債", "歐式", "歐系", "歐陽修",
)
# A candidate whose given part starts with a title word is a title, not a name.
TITLE_AFTER_SURNAME = ("先生", "小姐", "女士", "太太", "大哥", "大姐", "老師", "教授", "醫師", "律師", "董事", "總", "局長",
                       "市長", "縣長", "部長", "署長", "處長", "院長", "主任", "委員", "議員", "立委", "姓", "媽", "爸")
# A personal name does not contain these characters (organisations, places, phrases).
NON_NAME_CHARS = set(
    "的之與及和或市縣鄉鎮區部會院署局處長案委員黨團府校所館站隊組社業費款國中生元戰方陸門船機車輛廠港島山海河湖路街橋道線艦艇客貨班列"
    "年月日時分秒號萬億個人次起件名位項筆場期屆週度級場區帶圈型式制法"
    "與及並但而且卻均皆將已仍再又更最很都就也還只"
)
VERB_SURNAME_PREFIX = {"顧": set("照關愛看兼眷光"), "白": set("明告坦"), "易": set("交貿輕容")}

_NAME = rf"(?:{_SURNAME_ALT}){_HAN}{{1,2}}"
PATTERN_AFTER_ACTION = re.compile(rf"(?P<pre>{ACTION_WORDS})(?P<name>{_NAME})")
PATTERN_BEFORE_VERDICT = re.compile(rf"(?P<name>(?:{_SURNAME_ALT}){_HAN}{{1,2}})(?=(?:{VERDICT_WORDS}))")


def _trim(name: str) -> str:
    """Returns the part of name that is a plausible private name, or '' if none."""
    if any(name.startswith(g) for g in GUARD_WORDS):
        return ""
    surname_len = 2 if name[:2] in COMPOUND_SURNAMES else 1
    given = name[surname_len:]
    if any(given.startswith(t) for t in TITLE_AFTER_SURNAME):
        return ""
    # Cut the given part at the first character that is not part of a personal name.
    for i, ch in enumerate(given):
        if ch in NON_NAME_CHARS:
            given = given[:i]
            break
    if not given:
        return ""
    return name[:surname_len] + given


def _is_figure(text: str, start: int, figures: Set[str]) -> bool:
    for fig in figures:
        if text.startswith(fig, start):
            return True
    return False


def mask_names(text: str, figures: Iterable[str] = ()) -> Tuple[str, List[str]]:
    """Returns (masked text, names removed). Public figures in figures stay visible."""
    if not text:
        return "", []
    figs = set(figures)
    found: List[str] = []

    def candidate(s: str, m: "re.Match") -> str:
        """Returns the name to mask, or '' when the match must stay."""
        name = m.group("name")
        start = m.start("name")
        if _is_figure(s, start, figs):
            return ""
        if any(name in f or f in s[max(0, start - 4): m.end("name")] for f in figs):
            return ""
        if start > 0 and s[start - 1].isdigit():
            return ""
        prefixes = VERB_SURNAME_PREFIX.get(name[0])
        if prefixes and start > 0 and s[start - 1] in prefixes:
            return ""
        return _trim(name)

    def apply(pattern: "re.Pattern", s: str) -> str:
        out: List[str] = []
        pos = 0
        for m in pattern.finditer(s):
            kept = candidate(s, m)
            if not kept:
                continue
            start = m.start("name")
            out.append(s[pos:start])
            out.append(MASK)
            found.append(kept)
            pos = start + len(kept)
        out.append(s[pos:])
        return "".join(out)

    s = apply(PATTERN_AFTER_ACTION, text)
    s = apply(PATTERN_BEFORE_VERDICT, s)
    return s, found
