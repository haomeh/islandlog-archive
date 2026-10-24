"""Flag a title and summary: negative, topics, clarification, sensitive. Standard library only.

Lexicons are JSON files (editable):
  negative_terms.json      {"topics": {topic_key: [terms]}}
  clarification_terms.json {"terms": [...]}
  sensitive_terms.json     {"terms": [...]}
"""

import json
from pathlib import Path
from typing import Dict, List


def load_lexicons(directory: Path) -> Dict:
    directory = Path(directory)

    def load(name: str) -> Dict:
        return json.loads((directory / name).read_text(encoding="utf-8"))

    return {
        "topics": load("negative_terms.json")["topics"],
        "clarification": load("clarification_terms.json")["terms"],
        "sensitive": load("sensitive_terms.json")["terms"],
    }


def classify(title: str, summary: str, lex: Dict, force_clarification: bool = False) -> Dict:
    text = f"{title} {summary or ''}"
    topics: List[str] = [k for k, terms in lex["topics"].items() if any(t in text for t in terms)]
    return {
        "negative": bool(topics),
        "topics": topics,
        "clarification": force_clarification or any(t in text for t in lex["clarification"]),
        "sensitive": any(t in text for t in lex["sensitive"]),
    }
