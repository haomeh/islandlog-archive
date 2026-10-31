#!/usr/bin/env python3
"""Merges new crawl rows into the news corpus (T79, R346).

Usage: python3 -m tools.newsfetch.merge_corpus --corpus CORPUS --new news-a.jsonl [news-b.jsonl ...] --out OUT

Rules:
- Every old row stays byte-equal: the old file is copied line by line and is a prefix of the new file.
- A new row joins only when its canonical URL is not in the corpus and not in an earlier new row.
- The tool writes OUT.tmp, checks it, then renames it onto OUT (atomic). When OUT is the corpus,
  the old corpus stays in place until the check passes. A failed check removes the temp file.
- The result JSON has the row counts, new rows per outlet and the sha256 of OUT.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

from tools.newsfetch.lists import canonical_url


class MergeError(Exception):
    pass


def _lines(path):
    try:
        data = Path(path).read_bytes()
    except OSError as err:
        raise MergeError(f"cannot read {path}: {err}") from err
    return [l for l in data.split(b"\n") if l.strip()]


def _key(row):
    return canonical_url(row["url"])


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _check(tmp, old_lines, new_rows):
    """The temp file must start with the old rows (byte-equal) and hold every new row once."""
    got = _lines(tmp)
    if got[:len(old_lines)] != old_lines:
        raise MergeError("old rows are not byte-equal in the merged file")
    if len(got) != len(old_lines) + len(new_rows):
        raise MergeError("row count of the merged file is wrong")
    for line in got[len(old_lines):]:
        json.loads(line)


def merge(corpus, new_paths, out):
    """Returns the result dict. Raises MergeError and leaves the corpus unchanged on any problem."""
    corpus, out = Path(corpus), Path(out)
    old_lines = _lines(corpus)
    seen = set()
    for line in old_lines:
        try:
            seen.add(_key(json.loads(line)))
        except (ValueError, KeyError, TypeError) as err:
            raise MergeError(f"bad row in the corpus: {err}") from err
    new_rows, crawled = [], Counter()
    for path in new_paths:
        for line in _lines(path):
            try:
                row = json.loads(line)
                key, publisher = _key(row), row["publisher"]
            except (ValueError, KeyError, TypeError, AttributeError) as err:
                raise MergeError(f"bad row in {path}: {err}") from err
            crawled[publisher] += 1
            if key not in seen:
                seen.add(key)
                new_rows.append(row)
    new_rows.sort(key=lambda r: (str(r.get("published_on", "")), r["url"]))
    tmp = out.with_name(out.name + ".tmp")
    try:
        with open(tmp, "wb") as f:
            for line in old_lines:
                f.write(line + b"\n")
            for row in new_rows:
                f.write(json.dumps(row, ensure_ascii=False).encode("utf-8") + b"\n")
            f.flush()
            os.fsync(f.fileno())
        _check(tmp, old_lines, new_rows)
        os.replace(tmp, out)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return {"rows_old": len(old_lines), "rows_new": len(new_rows), "rows_total": len(old_lines) + len(new_rows),
            "new_by_outlet": dict(Counter(r["publisher"] for r in new_rows)),
            "crawled_by_outlet": dict(crawled), "sha256": _sha256(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--new", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        print(json.dumps(merge(args.corpus, args.new, args.out), ensure_ascii=False))
    except MergeError as err:
        print(f"merge failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
