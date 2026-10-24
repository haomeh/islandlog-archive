#!/usr/bin/env python3
"""Cluster fetched news items by title similarity and publication date.

Rules:
- Items are processed in order (date, preferred publisher, URL). Input order does not matter.
- Report groups use an anchor rule. An item joins a group only if its title is similar
  (bigram Jaccard >= SAME_CONTENT_THRESHOLD) to the group's REPRESENTATIVE and its date
  is within SAME_CONTENT_DAYS of the representative. Otherwise it starts a new group.
  An item with a clarification word does not join a group whose representative has none.
- Topic clusters link groups when the Jaccard of their union-of-bigrams is
  >= TOPIC_THRESHOLD and the representatives are within TOPIC_DAYS.
- Inside a topic cluster the first group is a report. A later group is a clarification
  only if its representative title has a clarification word. Other groups are reports.
- cluster_id is "cluster-" + the first 16 hex digits of SHA-256 of the earliest item URL
  of the cluster. It does not depend on input order. It changes only if an earlier item
  joins the cluster.
- Each item has a source_group, "news" or "official". The input field source_group wins.
  Else it is "official" for source_class official_statement or official_record, else "news".
  Official items form groups of kind "official". They never merge with news groups,
  but they can share a topic cluster. Only news groups can be clarifications.
- fact_check counts as official for grouping. Its source_class stays in the output.
- A clarification item has clarification:true, and for a news item also a clarification word
  in the title. It never joins a group of other items. Its group has kind "clarification".
  An item without the clarification field keeps the old rule (title word, later news group).
- A clarification group links to a group in a topic cluster when the shared bigrams cover
  MIN_CLARIFICATION_OVERLAP of the smaller set (and at least MIN_CLARIFICATION_SHARED).
- negative, clarification and sensitive are true on a group or cluster if any item is true.
  topics is the sorted union. has_negative_and_clarification is true when a negative group
  and a different clarification group are in the same cluster.
- A group where every item has routine:true gets routine:true.
- An item with a bad or missing published_on, title or url is skipped with a warning.
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

LOGGER = logging.getLogger(__name__)

SAME_CONTENT_THRESHOLD = 0.55
TOPIC_THRESHOLD = 0.25
SAME_CONTENT_DAYS = 3
TOPIC_DAYS = 30
CLARIFICATION_WORDS = ("澄清", "更正", "回應", "否認", "道歉", "說明", "駁斥", "表示將")
OFFICIAL_CLASSES = ("official_statement", "official_record", "fact_check")
MIN_CLARIFICATION_OVERLAP = 0.5
MIN_CLARIFICATION_SHARED = 4
PREFERRED_PUBLISHERS = ("公視新聞網", "中央通訊社")
LEADING_TAG = re.compile(r"^\s*(?:【[^】]*】|\[[^\]]*\])")
PUBLISHER_SUFFIXES = ("公視新聞網", "中央通訊社", "中央社", "自由時報", "聯合新聞網", "TVBS新聞網")
SEPARATED_PUBLISHER = re.compile(
    r"\s*[|\-–—]\s*(?:公視新聞網|公視|中央通訊社|中央社|自由時報|聯合新聞網|風傳媒|"
    r"newtalk新聞|newtalk|tvbs新聞網|tvbs新聞|tvbs)\s*$",
    re.IGNORECASE,
)


def normalize_title(title):
    """Apply NFKC, drop leading tags and publisher suffixes, then drop spaces and punctuation."""
    text = unicodedata.normalize("NFKC", title or "").strip()
    while True:
        stripped = LEADING_TAG.sub("", text, count=1).strip()
        if stripped == text:
            break
        text = stripped
    while True:
        stripped = SEPARATED_PUBLISHER.sub("", text, count=1).strip()
        if stripped == text:
            break
        text = stripped
    for suffix in PUBLISHER_SUFFIXES:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
            break
    return "".join(
        char for char in text
        if not char.isspace() and not unicodedata.category(char).startswith(("P", "Z"))
    )


def _bigrams_of(normalized):
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[i:i + 2] for i in range(len(normalized) - 1)}


def bigrams(text):
    return _bigrams_of(normalize_title(text))


def jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _day(item):
    return date.fromisoformat(str(item["published_on"]))


def _publisher_rank(item):
    try:
        return PREFERRED_PUBLISHERS.index(item.get("publisher"))
    except ValueError:
        return len(PREFERRED_PUBLISHERS)


def _order_key(item):
    return (_day(item), _publisher_rank(item), item.get("url", ""))


def same_content(left, right):
    """Return whether two items meet the report title and date rules."""
    return (abs((_day(left) - _day(right)).days) <= SAME_CONTENT_DAYS
            and jaccard(bigrams(left["title"]), bigrams(right["title"])) >= SAME_CONTENT_THRESHOLD)


def _source_group(item):
    value = item.get("source_group")
    if value in ("news", "official"):
        return value
    return "official" if item.get("source_class") in OFFICIAL_CLASSES else "news"


class _Prepared:
    """An item with its day, bigrams and clarification flag computed once."""
    __slots__ = ("item", "day", "bigrams", "order", "has_word",
                 "source_group", "routine", "is_clar", "legacy", "negative",
                 "clarification", "sensitive", "topics")

    def __init__(self, item):
        self.item = item
        self.day = _day(item)
        self.bigrams = _bigrams_of(normalize_title(item["title"]))
        self.order = (self.day, _publisher_rank(item), item["url"])
        self.has_word = any(word in item["title"] for word in CLARIFICATION_WORDS)
        self.source_group = _source_group(item)
        self.routine = item.get("routine") is True
        self.negative = item.get("negative") is True
        self.clarification = item.get("clarification") is True
        self.sensitive = item.get("sensitive") is True
        topics = item.get("topics")
        self.topics = {t for t in topics if isinstance(t, str)} if isinstance(topics, list) else set()
        self.legacy = "clarification" not in item
        self.is_clar = self.clarification and (self.source_group == "official" or self.has_word)


class _Index:
    """Inverted index from bigram to node ids, to find nodes that share bigrams."""

    def __init__(self):
        self.postings = {}

    def add(self, node_id, grams):
        for gram in grams:
            self.postings.setdefault(gram, []).append(node_id)

    def shared(self, grams):
        counts = Counter()
        for gram in grams:
            counts.update(self.postings.get(gram, ()))
        return counts


def _prepare(items):
    prepared = []
    for item in items:
        try:
            if not item.get("url") or not item.get("title"):
                raise ValueError("missing url or title")
            prepared.append(_Prepared(item))
        except (ValueError, TypeError, KeyError) as error:
            LOGGER.warning("skip item %s: %s", item.get("url"), error)
    prepared.sort(key=lambda value: value.order)
    return prepared


def _report_groups(prepared):
    groups = []  # each: {"rep": _Prepared, "members": [_Prepared]}
    indexes = {}
    for entry in prepared:
        index = indexes.setdefault((entry.source_group, entry.is_clar), _Index())
        best, best_score = None, 0.0
        for group_id, shared in index.shared(entry.bigrams).items():
            rep = groups[group_id]["rep"]
            if abs((entry.day - rep.day).days) > SAME_CONTENT_DAYS:
                continue
            if (entry.source_group == "news" and entry.legacy and entry.has_word
                    and not rep.has_word):
                continue
            score = shared / (len(entry.bigrams) + len(rep.bigrams) - shared)
            if score >= SAME_CONTENT_THRESHOLD and (score > best_score or (
                    score == best_score and group_id < best)):
                best, best_score = group_id, score
        if best is None:
            index.add(len(groups), entry.bigrams)
            groups.append({"rep": entry, "members": [entry]})
        else:
            groups[best]["members"].append(entry)
    for group in groups:
        group["clar"] = group["rep"].is_clar
        group["bigrams"] = set().union(*(member.bigrams for member in group["members"]))
    return groups


def _topic_components(groups):
    parents = list(range(len(groups)))

    def root(node):
        while parents[node] != node:
            parents[node] = parents[parents[node]]
            node = parents[node]
        return node

    index = _Index()
    for current, group in enumerate(groups):
        for other, shared in index.shared(group["bigrams"]).items():
            rep = groups[other]["rep"]
            if abs((group["rep"].day - rep.day).days) > TOPIC_DAYS:
                continue
            union = len(group["bigrams"]) + len(groups[other]["bigrams"]) - shared
            smaller = min(len(group["bigrams"]), len(groups[other]["bigrams"]))
            clarifies = ((group["clar"] != groups[other]["clar"])
                         and shared >= MIN_CLARIFICATION_SHARED
                         and shared / smaller >= MIN_CLARIFICATION_OVERLAP)
            if shared / union >= TOPIC_THRESHOLD or clarifies:
                parents[root(current)] = root(other)
        index.add(current, group["bigrams"])
    topics = {}
    for node, group in enumerate(groups):
        topics.setdefault(root(node), []).append(group)
    return list(topics.values())


def _flags(members):
    return {
        "negative": any(m.negative for m in members),
        "clarification": any(m.clarification for m in members),
        "sensitive": any(m.sensitive for m in members),
        "topics": sorted(set().union(*(m.topics for m in members))),
    }


def cluster_items(items):
    """Return topic clusters with report and clarification groups."""
    groups = _report_groups(_prepare(items))
    output = []
    for topic in _topic_components(groups):
        topic.sort(key=lambda group: group["rep"].order)
        members = sorted((m for g in topic for m in g["members"]), key=lambda value: value.order)
        earliest = members[0]
        clean_groups = []
        seen_news = False
        for group in topic:
            rep = group["rep"]
            if rep.source_group == "official":
                kind = "official"
            else:
                if rep.is_clar or (rep.legacy and seen_news and rep.has_word):
                    kind = "clarification"
                else:
                    kind = "report"
                seen_news = True
            if rep.is_clar:
                kind = "clarification"
            clean = {
                "kind": kind,
                "source_group": rep.source_group,
                "title": rep.item["title"],
                "representative_url": rep.item["url"],
                "member_urls": [member.item["url"] for member in group["members"]],
                "source_class": rep.item.get("source_class"),
                **_flags(group["members"]),
            }
            if all(member.routine for member in group["members"]):
                clean["routine"] = True
            clean_groups.append(clean)
        has_pair = any(g["negative"] and h["kind"] == "clarification" and g is not h
                       for g in clean_groups for h in clean_groups)
        output.append({
            "cluster_id": "cluster-" + hashlib.sha256(earliest.item["url"].encode("utf-8")).hexdigest()[:16],
            "title": earliest.item["title"],
            "first_date": str(earliest.day),
            "last_date": str(members[-1].day),
            "groups": clean_groups,
            **_flags(members),
            "has_negative_and_clarification": has_pair,
        })
    return sorted(output, key=lambda cluster: (cluster["first_date"], cluster["cluster_id"]))


def _proposed_source_id(url, published_on):
    host = urlsplit(url).hostname or "news"
    labels = [label for label in host.split(".") if label not in ("www", "com", "tw", "org", "gov", "net")]
    label = re.sub(r"[^a-z0-9]+", "", (labels[-1] if labels else "news").lower()) or "news"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"src-{str(published_on).replace('-', '')}-{label}-{digest}"


def as_news_groups(clusters, items):
    """Return (news_groups per cluster, url -> proposed source id).

    source_ids and representative_source_id hold URLs as placeholders. The Archive
    Editor replaces them with the mapped IDs after creating the source files.
    """
    days = {entry["url"]: str(entry["published_on"]) for entry in items if entry.get("url")}
    mapping = {}
    result = []
    for cluster in clusters:
        news_groups = []
        for number, group in enumerate(cluster["groups"], start=1):
            for url in group["member_urls"]:
                mapping[url] = _proposed_source_id(url, days[url])
            entry = {
                "id": f"ng-{number:02d}",
                "kind": group["kind"],
                "source_group": group["source_group"],
                "title": group["title"],
                "representative_source_id": group["representative_url"],
                "source_ids": list(group["member_urls"]),
            }
            for key in ("source_class", "negative", "clarification", "sensitive", "topics"):
                entry[key] = group[key]
            if group.get("routine"):
                entry["routine"] = True
            news_groups.append(entry)
        result.append({"cluster_id": cluster["cluster_id"], "title": cluster["title"],
                       "negative": cluster["negative"], "clarification": cluster["clarification"],
                       "sensitive": cluster["sensitive"], "topics": cluster["topics"],
                       "has_negative_and_clarification": cluster["has_negative_and_clarification"],
                       "news_groups": news_groups})
    return result, mapping


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cluster fetched news items.")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--as-news-groups", action="store_true",
                        help="write news_groups entries and <output>.sources.json")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    items = read_jsonl(args.input)
    clusters = cluster_items(items)
    out = Path(args.output)
    if args.as_news_groups:
        clusters, mapping = as_news_groups(clusters, [i for i in items if _valid_day(i)])
        Path(str(out) + ".sources.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out.write_text(json.dumps(clusters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _valid_day(item):
    try:
        _day(item)
        return True
    except (ValueError, TypeError, KeyError):
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
