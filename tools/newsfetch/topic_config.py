"""R107a: every threshold of the topic tools in one place (topics.py and topics_full.py read it).

A value here controls one decision of the system. Each comment says what the value controls and where it
came from. "Case" means the real topic that the value was fit to. "Start" means the value of the first
implementation (R63, R68) that no case has tested. Change a value only with a precision sample (R107).
Pattern lists (ELECTION, CRIME, NATIONAL_SYSTEMS and others) stay in the module that uses them.
Display limits (MAX_STATIONS, MAX_GROUPS and others) stay in topics.py: they do not decide membership.
"""

# --- Key choice (topics.pick_key, topics.topic_keys, topics.display_name) ---
GENERIC_DF_SHARE = 0.02  # A phrase in more than this share of all items is generic and never a key. Start (R63).
GENERIC_DF_MIN = 50  # Floor of the generic limit in items, so a small corpus has no tiny limit. Start (R63).
KEY2_SHARE = 0.3  # A second key is added when this share of the seed titles lacks the first key. Start (R63).
KEY2_MIN_COVER_SHARE = 0.4  # The second key covers at least this share of the titles without the first key. Start (R63).
KEY2_MIN_COVER = 3  # ... and at least this many of them. Start (R63).
BAND = 25  # A key may appear in at most BAND x (seed titles it covers) items. Start (R63).
POOL_COVER_SHARE = 0.8  # A key that covers this share of the seed titles skips the BAND test. Start (R63).
TOP_COVER_SHARE = 0.9  # A key that covers this share of the seed titles ranks first. Start (R63).
EXTEND_DF_SHARE = 0.7  # A longer phrase with the same cover and this share of the key's frequency is the real name. Start (R63).
DOMINANT_SHARE = 0.6  # A longer form with a noun ending that covers this share of the key's titles names the topic (萬里溪 -> 萬里溪堰塞湖). Case (R69).

# --- Window and local keys (topics.members) ---
WINDOW_BEFORE, WINDOW_AFTER = 7, 30  # Days before the first seed and after the last seed that a member may fall in. Start (R63).
PLACE_FILTER_DF = 20  # A local key in more items than this, and used mostly outside the window, is generic. Start (R65).
GENERIC_BURST = 0.35  # "Used mostly outside the window" means less than this share of its uses inside it. Start (R65).
LOCAL_ANCHOR_SHARE = 0.3  # A local anchor is in this share of the seed titles ... Start (R65).
LOCAL_ANCHOR_MIN = 2  # ... and in at least this many of them. Start (R65).

# --- Anchors (topics.anchored: which titles with the key belong to the issue) ---
ANCHOR_MAX_DF = 50  # An anchor word is rare: in at most this many items of the corpus. Case: costco, cupp, fangyuan (T15).
ANCHOR_CORE_MIN = 2  # A rare word in this many core titles becomes a new anchor (A肝莓果). Case: costco (T15).
SPECIFIC_KEY_MIN = 15  # A key is specific to one issue when it has this many candidates ... Case: 統促黨, 薔琵 (T15).
SPECIFIC_KEY_SHARE = 0.7  # ... and they are this share of all its uses in the corpus. Case: 統促黨, 薔琵 (T15).
RARE_KEY_MIN_LEN = 5  # A key phrase of this length that is rare in the corpus is its own anchor. Case: 續放颱風假 (T15).
RARE_KEY_SHARE = 0.5  # ... when the candidates are this share of its uses. Case: 全民運動館 is also in other counties (T15).
COMPANION_MIN = 3  # A companion word is in at least this many core titles ... Case: 通車, 爆炸 (T15).
COMPANION_SHARE = 0.6  # ... and in this share of them. Case: 通車 in 26 of 33 core titles of 淡江大橋 (T15).
COMPANION_LIFT = 5  # ... and its share in the corpus is at most 1/COMPANION_LIFT of its share in the core. Case: T15.
ONE_ISSUE_MIN_CORE = 20  # A key with at least this many core titles ... Case: 淡江大橋 (T15).
ONE_ISSUE_SHARE = 0.6  # ... and a companion in this share of them names one story. Case: 通車 in 23 of 33 (T15).

# --- Second anchor (R112.1: a member has a key and one more anchor of the seed titles) ---
SECOND_ANCHOR_SHARE = 0.3  # A word is a second key word when this share of the seed titles has it ... Sample T18-AP (R112.1): 焚化爐 titles about a zoo or Taichung had none.
SECOND_ANCHOR_MIN_SEEDS = 4  # With fewer seed titles than this no word can be shared, so a word of any one seed title counts. Start (R112.1).
SECOND_ANCHOR_MIN = 2  # ... and in at least this many of them. A place or a government actor in this many seed titles is an anchor too. Sample T18-AP (R112.1).
SECOND_ANCHOR_MAX_DF = 400  # A second key word is in at most this many items of the corpus. 回應 (1117) and 民眾 (858) are generic; 內政部 (288) and 縣府 (308) are not. Sample T18-AP (R112.1).
SECOND_ANCHOR_MIN_LEN, SECOND_ANCHOR_MAX_LEN = 2, 4  # A second key word has 2 to 4 characters (環評, 憲法法庭). Sample T18-AP (R112.1).

# --- Gates of the full run (topics_full.run) ---
SAME_EVENT_SHARE = 0.3  # A topic that shares this share of its members with a published event is skipped. Start (R68).
EXCLUDE_SHARE = {  # PRD 4.5: a topic is excluded when this share of its titles has the exclusion pattern. Start (R68).
    "sensitive": 0.3, "election_campaign": 0.3, "criminal_case": 0.5, "entertainment": 0.3}
CONCENTRATION = 4.0  # A key may have at most this many times more uses in the corpus than in the topic window. Start (R85).
BOUNDARY_SHARE = 0.8  # A neighbor character is added to a key when this share of its uses has it (脫大稽查). Case (R85).
CONTINUATION_SHARE = 0.8  # A key is a fragment when at most 3 characters follow it in this share of its uses. Case: 降速演 (R85).
QUOTED_SLOGAN_SHARE = 0.5  # A key inside 「」 in this share of its uses is a quote or slogan. Case (R85).
RELEVANCE_SHARE = 0.5  # A topic is about Taiwan when this share of its titles has a Taiwan term. Start (R68, R84).
JURISDICTION_SHARE = 0.3  # A place is a jurisdiction of the topic when this share of its titles names it. Start (R68).
CLASSIFY_SHARE = 0.2  # A controversy type or policy domain is set when this share of the titles matches it. Start (R68).
MERGE_OVERLAP = 0.5  # Two topics or a topic and a published one are the same when they share this share of sources. Start (R68, R82).
SUBTOPIC_SHARE = 0.1  # A child topic needs this share of its titles to have the older topic key (R72). Start (R72).

# --- Counts of the full-run gates (topics_full: PRD 4.4, R68, R73) and low limits (R117) ---
SEED_MIN_ITEMS = 2  # A cluster with fewer items than this and no official or fact-check item is no seed. Start (R68).
SOURCE_RULE_MIN_PUBLISHERS = 2  # PRD 4.4 item 2: grade C sources from at least this many publishers (or 1 grade A source). Start (R68).
NEWS_RULE_MIN_ITEMS = 2  # R73: at least this many news items ... Start (R73).
NEWS_RULE_MIN_PUBLISHERS = 2  # ... from at least this many news publishers. Start (R73).
CONTINUATION_MIN_USES = 2  # A key with fewer uses than this is a fragment: the next-character test needs 2 uses. Start (R85).
MIN_KEY_LEN = 3  # A key shorter than this many characters is not a topic name. Start (R68, R85).
PAPER_DAYS = 2  # A newspaper copy joins a group of an earlier item at most this many days older. Start (R63).
PAPER_OVERLAP = 0.5  # ... when its bigrams overlap this share of the smaller set. Start (R63).
SHORT_KEY_LEN = 2  # A key of this length or less takes a longer display form from the seed titles (移工 -> 移工懷孕). Case (R69).
DISPLAY_FORM_MIN_COUNT = 2  # A common 4-character form needs this many titles (薔琵 -> 薔琵颱風). Case (R69).
CONTROVERSY_MIN_ACTORS = 2  # PRD 4.4 item 3, R73: a controversy needs real stances from this many actors. Start (R73).

# --- Name and gate fixes of the precision sample (T22, R112) ---
GENERIC_NAME_MAX_LEN = 3  # A name of this length or less that is a generic object (巡視船, 豎孤棚), or that is a few characters after a jurisdiction, is not a topic name. Sample T18-AP: 巡視船, 屏東縣豎孤棚 (R112.2).
DISEASE_NAME_MAX_LEN = 6  # A name of this length or less that ends with a disease word and has no policy noun is only a disease (惡性腫瘤). Sample T18-AP: 惡性腫瘤 (R112.2).
GOV_NAME_SHARE = 0.5  # A noun phrase is a policy name when this share of its titles names a government body: the quote and word-start tests are skipped. Sample T18-AP: 廚餘給弱勢 (教育局, 3 of 4), 不只高德地圖 (數發部, 3 of 3) (R112.4).
FOREIGN_NAMED_SHARE = 0.3  # A topic outside Taiwan is foreign only when this share of its titles names a foreign country or leader. Sample T18-AP: 清潔公司掛羊頭賣狗肉 was labeled foreign with none (R112.5).

SPLIT_MIN_TITLES = 2  # A jurisdiction splits a topic off when this many titles name it alone and another jurisdiction of the same level has as many. Sample T18-AP: 臺中市續放颱風假 holds 北市 (2 titles) and 台中 (4) (R112.3).

# --- Re-gate of old topics and gate fixes of the second precision sample (T22 round 3, R126 to R130) ---
BODY_VERB_NAME_MAX_LEN = 6  # A name of this length or less that is a body short name and a verb (北高行駁回, 5 characters) is not a topic name. Sample T22-P: e142b3a9 (R128).
ELECTION_DAY = "2026-11-28"  # Day of the 2026 local elections. The campaign period ends the day before it. Ruling R136 final.
CAMPAIGN_DAYS = 10  # Legal campaign activity period of the 公職人員選舉罷免法: the widest local period (縣市長, 縣市議員) is 10 days, 2026-11-18 to 2026-11-27. Before it, an election dispute with grade C sources passes. Ruling R136 final (user answer 2026-10-25), replaces the provisional 90 days (R130).
ELECTION_DISPUTE_MIN_GRADE_A = 1  # An election dispute inside the campaign period needs this many grade A sources, else it is rejected_election_campaign. PRD R-10. Sample T22-P: e142b3a9 had 3 grade C sources (R130).

# --- Hysteresis (R107b) ---
WITHDRAW_AFTER_FAILS = 2  # A published topic is withdrawn after this many failing runs in a row. Ruling R107.

# --- Safety stop for withdrawals (R133) ---
WITHDRAW_MAX_COUNT = 3  # A run that would withdraw more topics than this withdraws none and writes withdraw_blocked. Ruling R133.
WITHDRAW_MAX_SHARE = 0.1  # ... also when it would withdraw more than this share of the published system topics (at least 1 topic is always allowed). Ruling R133.

# --- Follow-up gate fixes after T22 (T24, R141) ---
TAIWAN_MIN_TITLES = 2  # A topic is about Taiwan also when this many of its titles name Taiwan (a place, a body, a figure, a national road) and they are TAIWAN_MIN_SHARE of the titles. A typhoon forecast needs this many titles that name Taiwan. Sample T22-P2: 事後避孕藥 (4 of 9 titles), 米克拉 typhoon (4 of 8 name Taiwan) were rejected as not_taiwan (R141.4).
TAIWAN_MIN_SHARE = 0.25  # ... and they are at least this share of the titles; below it a foreign story that names Taiwan once or twice still fails. Sample T22-P2: the lowest of the 9 not_taiwan rejects is 事後避孕藥 with 44% (R141.4). Start for the margin below 44%.
OFFICIAL_MIN_TITLES = 3  # A name that follows an office word (部長, 署長, 主委, 次長) in this many titles of the corpus is the name of an office holder (石崇良), so a title that names the holder names a minister. Sample T22-P2: 5 of the 17 name_quality rejects were 石崇良 stories (R141.5).
BARE_PERSON_MIN_LEN = 2  # A name of at least this many characters can be a bare person name (R147.3).
BARE_PERSON_MAX_LEN = 4  # ... and of at most this many characters (a Chinese name with a title word before it). Case: 薛楷莉, 朱安雄 (R147.3).
BARE_PERSON_SHARE = 0.5  # A name that follows a role word (前主播, 議長) in this share of its uses names only a person. Case: 薛楷莉, 朱安雄 (R147.3).

# --- Gate round T26 (R154 to R157): precision over recall. A class that no general rule can stop is rejected. ---
NUMBER_CUT_SHARE = 0.5  # A key that follows a digit, a Latin letter or a percent sign in this share of its uses lost its first part (42號演習 -> 號演習, C肝群聚 -> 肝群聚), or lost its last part when a digit follows it. Sample T25-P: 42號演習, 60天免簽, C肝群聚 (R154).
QUOTE_COLON_SHARE = 0.5  # A key that follows a colon in this share of its uses is the words of a speaker (沈伯洋：底線一直被踩), not a name. Sample T25-P: 不因威脅放棄民主, 底線一直被踩 (R154).
GOV_ACT_SHARE = 0.1  # A topic needs this share of its titles to name a government body of Taiwan or a public act: a topic with none is a private matter (PRD 4.5 item 1). Sample T25-P: 鍘美藝術節, 台商捐款, 美光回應工會訴求 (R154).
ACCIDENT_SHARE = 0.5  # A topic is a single accident when this share of its titles has an accident word ... Sample T25-P: 新加坡婦 (R154).
ACCIDENT_POLICY_SHARE = 0.3  # ... and fewer than this share of its titles has a policy word (rules, review, law). A road-safety rule topic names an accident too (R154).
CANDIDATE_SHARE = 0.3  # A topic is a candidate attack or election banter when this share of its titles names two figures and an attack word, or names a campaign act (PRD 4.5 item 5). Sample T25-P: 往臉上貼金, 東泉辣椒醬, 臺北市電視辯論 (R154).
OFFICIAL_HEALTH_SHARE = 0.3  # A topic is the health of a named official when this share of its titles has an official and a health word (rule 4). Sample T25-P: 基隆市住進北榮 (R154).
DUPLICATE_GAP_DAYS = 60  # Two new topics are one issue only when their days are at most this many days apart. Sample T25-P: 兄弟姊妹 and 兄弟姊妹特留分 are 46 days apart (R154).
DUPLICATE_TERM_LEN = 5  # ... and they share a term (a character n-gram) of at least this many characters, or one key holds the other. A 4-character term (藍白立委, 立院三讀) is common in many stories. Sample T25-P: 賴清德出訪, 副署無人載具條例, 行動網路降速演練 (R154).
DUPLICATE_TERM_MAX_DF = 60  # ... and the term is in at most this many items of the corpus: a rare term names one story. Start (R154); the dry run measures it.
DUPLICATE_MIN_TITLES = 2  # ... and each topic has the term in at least this many titles. One title can quote another story. Start (R154).
CANDIDATE_MIN_TITLES = 5  # A name that follows or precedes a campaign word (參選, 候選人, 提名, 競選) in this many titles of the corpus is a candidate of the election. Start (R154); the dry run measures it.

# --- Gate round T26-W2 (R160 to R163): the name classes of the second precision round. ---
SLOGAN_MAX_LEN = 6  # A key of this length or less that a title only quotes or brings with a slogan verb is a slogan. Sample T26-P: 零軍購 (R162).
THEME_MIN_USES = 2  # A month counts for the theme test when the key has this many uses in it. One title can be an accident. Start (R162).
THEME_MIN_MONTHS = 6  # A key is a theme word when it has 2 uses or more in this many months of the corpus ... Sample T26-P: 政治獻金 is in 7 of 7 months; the next key (追加預算) is in 5 (R162).
THEME_MAX_MONTH_SHARE = 0.5  # ... and no month holds this share of its uses: a case or an issue has a burst. Sample T26-P: 政治獻金 top month 38%, 追加預算 46% (R162).
DUPLICATE_NEAR_DAYS = 7  # Two new topics, or a new topic and an old one, that are at most this many days apart are one issue when they share a rare term of DUPLICATE_NEAR_TERM_LEN characters. Sample T26-P: 立院三讀免健保費 and 長者有條件免健保費 are 1 day apart (R162).
DUPLICATE_NEAR_TERM_LEN = 4  # ... which is shorter than DUPLICATE_TERM_LEN because the topics are close in time. Sample T26-P: 免健保費 (R162).

# --- Gate round T32 (R194 to R199): the general rules after the day-2 precision fail. ---
TITLE_TERM_MIN_TITLES = 2  # A key that sits inside a quote, or after a colon or 稱, in this many titles is words of a speaker (R196.2). Sample T31-P: 大不過憲法 (8 of 10 titles), 立院刪預算 (3 of 3).
TITLE_TERM_SHARE = 0.4  # ... and in this share of the titles that hold the key. An issue that a few titles quote (卓榮泰：無人機條例需修正) stays a name. Start (R196.2); the dry run measures it.
SCOPE_MIN_TITLES = 2  # A government level is a big group of a topic when this many titles name it alone ... Sample T31-P: 提追加預算 has 2 city titles and 2 central titles (R196.4).
SCOPE_MIN_SHARE = 0.25  # ... and they are this share of the titles. Two big groups of two levels are a mixed cluster. A smaller group is off topic title by title: 媒宣費 has 2 city titles in 34 (R196.4, R196.6).
ACTOR_SHARE = 0.5  # A body is the actor of a topic when this share of its titles names it. The duplicate test compares the actors (R196.7).
ACT_MATCH_LEN = 2  # Two names have the same act when their act parts share this many characters (人事同意權 and 人事) (R196.7).
