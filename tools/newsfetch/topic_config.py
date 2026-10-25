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

# --- Hysteresis (R107b) ---
WITHDRAW_AFTER_FAILS = 2  # A published topic is withdrawn after this many failing runs in a row. Ruling R107.
