#!/usr/bin/env python3
"""Cluster fetched news items by title similarity and publication date."""

import hashlib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

SAME_CONTENT_THRESHOLD = 0.55
TOPIC_THRESHOLD = 0.25
SAME_CONTENT_DAYS = 3
TOPIC_DAYS = 30
CLARIFICATION_WORDS = ("澄清", "更正", "回應", "否認", "道歉", "說明", "駁斥", "表示將")
PREFERRED_PUBLISHERS = ("公視新聞網", "中央通訊社")
BRACKET_TAG = re.compile(r"【[^】]*】|\[[^\]]*\]|（[^）]*）")
PUBLISHER_SUFFIXES = ("公視新聞網", "中央通訊社", "中央社", "自由時報", "聯合新聞網", "TVBS新聞網")


def normalize_title(title):
    """Remove publisher suffixes, bracket tags, spaces, and punctuation."""
    text = BRACKET_TAG.sub("", title or "")
    text = text.strip()
    for suffix in PUBLISHER_SUFFIXES:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
            break
    return "".join(
        char for char in text
        if not char.isspace() and not unicodedata.category(char).startswith(("P", "Z"))
    )


def bigrams(text):
    normalized = normalize_title(text)
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[i:i + 2] for i in range(len(normalized) - 1)}


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


def _similarity(left, right):
    return jaccard(bigrams(left["title"]), bigrams(right["title"]))


def same_content(left, right):
    """Return whether two items meet the report title and date rules."""
    return abs((_day(left) - _day(right)).days) <= SAME_CONTENT_DAYS and _similarity(left, right) >= SAME_CONTENT_THRESHOLD


def _components(nodes, linked):
    parents = list(range(len(nodes)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for left in range(len(nodes)):
        for right in range(left + 1, len(nodes)):
            if linked(nodes[left], nodes[right]):
                a, b = root(left), root(right)
                if a != b:
                    parents[b] = a
    groups = {}
    for index, node in enumerate(nodes):
        groups.setdefault(root(index), []).append(node)
    return list(groups.values())


def cluster_items(items):
    """Return topic clusters with report and clarification groups."""
    items = sorted(items, key=_order_key)
    same_content_groups = _components(
        items,
        same_content,
    )
    topic_nodes = []
    for members in same_content_groups:
        representative = min(members, key=_order_key)
        topic_nodes.append({"members": members, "representative": representative})

    topic_components = _components(
        topic_nodes,
        lambda left, right: abs((_day(left["representative"]) - _day(right["representative"])).days) <= TOPIC_DAYS
        and _similarity(left["representative"], right["representative"]) >= TOPIC_THRESHOLD,
    )

    output = []
    for topic in topic_components:
        topic_items = sorted(
            (item for node in topic for item in node["members"]), key=_order_key
        )
        groups = []
        for node in sorted(topic, key=lambda value: _order_key(value["representative"])):
            members = sorted(node["members"], key=_order_key)
            representative = members[0]
            title_bigrams = bigrams(representative["title"])
            kind = "report"
            if groups and any(word in representative["title"] for word in CLARIFICATION_WORDS):
                kind = "clarification"
            group = {
                "kind": kind,
                "title": representative["title"],
                "representative_url": representative["url"],
                "member_urls": [item["url"] for item in members],
                "_bigrams": title_bigrams,
                "_date": _day(representative),
            }
            if kind == "clarification":
                groups.append(group)
            else:
                nearest = max(
                    groups,
                    key=lambda existing: jaccard(title_bigrams, existing["_bigrams"]),
                    default=None,
                )
                # A non-clarification content group joins its nearest topic group as a repeat.
                if nearest:
                    nearest["member_urls"].extend(group["member_urls"])
                else:
                    groups.append(group)

        earliest = topic_items[0]
        cluster_id = "cluster-" + hashlib.sha256(earliest["url"].encode("utf-8")).hexdigest()[:16]
        clean_groups = []
        for group in groups:
            clean_groups.append({key: group[key] for key in ("kind", "title", "representative_url", "member_urls")})
        output.append({
            "cluster_id": cluster_id,
            "title": earliest["title"],
            "first_date": str(_day(topic_items[0])),
            "last_date": str(_day(topic_items[-1])),
            "groups": clean_groups,
        })
    return sorted(output, key=lambda cluster: (cluster["first_date"], cluster["cluster_id"]))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        raise SystemExit("usage: python3 tools/newsfetch/cluster.py in.jsonl out.json")
    clusters = cluster_items(read_jsonl(args[0]))
    Path(args[1]).write_text(json.dumps(clusters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
