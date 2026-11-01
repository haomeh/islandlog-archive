#!/usr/bin/env python3
"""Run report of a topic run (R359.7: G4 renames, G7 off-topic checks).

Usage: python3 -m tools.newsfetch.run_report BASE_ROOT NEW_ROOT REPORT.json OUT_DIR [CORPUS.jsonl]

CORPUS.jsonl lets the candidate-attack check know the candidates of the corpus (as in the run).

Reads the archive tree before the run (BASE_ROOT, for example a git archive of the base commit) and after it (NEW_ROOT), and the report JSON of
topics_full. Writes OUT_DIR/new-topics.tsv, changed.tsv, regate.tsv and held-sensitive.tsv (R363.2). It reads files only and changes nothing in the two trees.
changed.tsv lists each event that changed: the title before and after with a rename flag, the members before and after, the added and
removed members with their titles, the latest news date before and after (a date that goes back is flagged), and a flag for each added
member that fails a check: no_key (the title lacks the event name), foreign_body (only a foreign body), candidate_attack, case (an arrest,
a search or a vote-buying title).
"""

import json
import re
import sys
from pathlib import Path

from tools.newsfetch import topics_full as tf

SRC_ID = re.compile(r"src-[A-Za-z0-9._-]+")
SEP = "｜"
CHANGED_COLUMNS = ["id", "title_before", "title_after", "renamed", "members_before", "members_after", "added", "removed", "latest_news_before",
                   "latest_news_after", "latest_moves_back", "added_flags", "added_titles", "removed_titles"]
NEW_COLUMNS = ["id", "name", "members", "news_publishers", "first_date", "last_date", "sample_titles", "flagged_titles"]
REGATE_COLUMNS = ["id", "gate", "title_before", "title_after", "members_before", "members_after", "removed", "capped"]


def _scalar(text, key):
    m = re.search(rf"^{key}: ?(.*)$", text, re.M)
    return m.group(1).strip().strip("'\"") if m else ""


def load_tree(root):
    """{"events": {id: {title, members}}, "sources": {id: {title, date, class, publisher}}}. A member is a source file that the event file cites."""
    root = Path(root)
    sources = {}
    for p in sorted((root / "sources").glob("*/*.yaml")):
        t = p.read_text(encoding="utf-8")
        sources[p.stem] = {"title": _scalar(t, "title"), "date": _scalar(t, "published_on"), "class": _scalar(t, "source_class"), "publisher": _scalar(t, "publisher")}
    events = {}
    for p in sorted((root / "events").glob("*/ev-*.md")):
        t = p.read_text(encoding="utf-8")
        members = sorted({i for i in SRC_ID.findall(t) if i in sources})
        events[p.stem] = {"title": _scalar(t.split("\n---", 1)[0], "title"), "members": members}
    return {"events": events, "sources": sources}


def latest_news(tree, members):
    return max([tree["sources"][i]["date"] for i in members if tree["sources"][i]["class"] == "news"], default="")


# R363.1: a title that may name a minor or a victim. A name before a family word, or a word for a student, a child or a victim.
VICTIM_TITLE = re.compile(r"[\u4e00-\u9fff]{2,4}(?:的)?(?:父親|母親|爸爸|媽媽|家屬|家長|遺族|家人|姊姊|姐姐|哥哥|弟弟|妹妹)|"
                          r"(?:國小|國中|高中|高職|大學)生|學童|男童|女童|少年|少女|未成年|被害人|受害(?:者|人|學生)|死者|遇害|命案|霸凌")


def victim_flag(title):
    """True if the title may name a minor or a victim. The writer reads every flag (R363.1)."""
    return bool(VICTIM_TITLE.search(title))


def member_flag(name, title):
    """The first failing check of an added member, as "label", or None. `name` is the event title without the place in front."""
    if victim_flag(title):
        return "minor_or_victim"
    if name and name not in title:
        return "no_key"
    if tf.foreign_body_only(title):
        return "foreign_body"
    if tf.candidate_talk(title):
        return "candidate_attack"
    if tf.CASE_TITLE.search(title):
        return "case"
    return None


def changed_rows(before, after):
    rows = []
    for eid, new in after["events"].items():
        old = before["events"].get(eid)
        if old is None:
            continue
        added = sorted(set(new["members"]) - set(old["members"]))
        removed = sorted(set(old["members"]) - set(new["members"]))
        if not added and not removed and old["title"] == new["title"]:
            continue
        name = tf.PLACE_PREFIX.sub("", new["title"], count=1)
        flags = []
        for i in added:
            title = after["sources"][i]["title"]
            label = member_flag(name, title)
            if label:
                flags.append(f"{label}:{title}")
        lo, hi = latest_news(before, old["members"]), latest_news(after, new["members"])
        rows.append({"id": eid, "title_before": old["title"], "title_after": new["title"], "renamed": "yes" if old["title"] != new["title"] else "no",
                     "members_before": len(old["members"]), "members_after": len(new["members"]), "added": len(added), "removed": len(removed),
                     "latest_news_before": lo, "latest_news_after": hi, "latest_moves_back": "yes" if hi < lo else "no",
                     "added_flags": SEP.join(flags), "added_titles": SEP.join(after["sources"][i]["title"] for i in added),
                     "removed_titles": SEP.join(before["sources"][i]["title"] for i in removed)})
    return rows


def new_rows(before, after):
    rows = []
    for eid, ev in after["events"].items():
        if eid in before["events"]:
            continue
        src = [after["sources"][i] for i in ev["members"]]
        news = [s for s in src if s["class"] == "news"]
        dates = sorted(s["date"] for s in src)
        rows.append({"id": eid, "name": ev["title"], "members": len(src), "news_publishers": len({s["publisher"] for s in news}),
                     "first_date": dates[0] if dates else "", "last_date": dates[-1] if dates else "",
                     "sample_titles": SEP.join(s["title"] for s in sorted(src, key=lambda s: s["date"])[:3]),
                     "flagged_titles": SEP.join(s["title"] for s in src if victim_flag(s["title"]))})
    return rows


def regate_rows(report):
    return [{"id": r["id"], "gate": r.get("gate"), "title_before": r.get("title_before"), "title_after": r.get("title_after"),
             "members_before": r.get("before"), "members_after": r.get("after"), "removed": len(r.get("removed") or []), "capped": r.get("capped", 0)} for r in report.get("regate", [])]


HELD_COLUMNS = ["id", "title", "gate", "members_in_file", "candidates", "candidate_id", "in_file", "candidate_title"]


def held_rows(report):
    """R363.2: one row for each candidate member of an event with review.sensitive true that the run left as it is."""
    rows = []
    for h in report.get("held_sensitive", []):
        base = {"id": h["id"], "title": h.get("title", ""), "gate": h.get("gate") or "", "members_in_file": len(h.get("in_file", [])) if isinstance(h.get("in_file"), list) else h.get("in_file", 0),
                "candidates": len(h.get("candidates", []))}
        for c in h.get("candidates") or [{}]:
            rows.append(dict(base, candidate_id=c.get("id", ""), in_file="yes" if c.get("in_file") else ("no" if c else ""), candidate_title=c.get("title", "")))
    return rows


def write_tsv(path, columns, rows):
    def cell(v):
        return str(v).replace("\t", " ").replace("\n", " ")
    lines = ["\t".join(columns)] + ["\t".join(cell(r.get(c, "")) for c in columns) for r in rows]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv):
    if len(argv) not in (5, 6):
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    base, new, report, out = Path(argv[1]), Path(argv[2]), json.load(open(argv[3], encoding="utf-8")), Path(argv[4])
    out.mkdir(parents=True, exist_ok=True)
    tf.set_candidates(tf.candidate_names(__import__("tools.newsfetch.topics", fromlist=["x"]).read_jsonl(argv[5])) if len(argv) > 5 else frozenset())
    before, after = load_tree(base), load_tree(new)
    write_tsv(out / "changed.tsv", CHANGED_COLUMNS, changed_rows(before, after))
    write_tsv(out / "new-topics.tsv", NEW_COLUMNS, new_rows(before, after))
    write_tsv(out / "regate.tsv", REGATE_COLUMNS, regate_rows(report))
    write_tsv(out / "held-sensitive.tsv", HELD_COLUMNS, held_rows(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
