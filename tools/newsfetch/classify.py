"""Flags for news items: negative topics, clarification, sensitive.

The three lexicon files are JSON and an editor maintains them. Standard library only.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
NEGATIVE_PATH = BASE_DIR / "negative_terms.json"
CLARIFICATION_PATH = BASE_DIR / "clarification_terms.json"
SENSITIVE_PATH = BASE_DIR / "sensitive_terms.json"


def _load(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Classifier:
    """Sets negative, topics, clarification and sensitive from the three lexicon files."""

    def __init__(
        self,
        negative: Optional[Dict[str, List[str]]] = None,
        clarification: Optional[List[str]] = None,
        sensitive: Optional[List[str]] = None,
    ):
        self.negative = negative if negative is not None else _load(NEGATIVE_PATH)["topics"]
        self.clarification = (
            clarification if clarification is not None else _load(CLARIFICATION_PATH)["terms"]
        )
        self.sensitive = sensitive if sensitive is not None else _load(SENSITIVE_PATH)["terms"]

    def classify(self, title: str, summary: str = "") -> Dict:
        text = f"{title} {summary}"
        topics = [
            topic for topic, terms in self.negative.items() if any(t in text for t in terms)
        ]
        return {
            "negative": bool(topics),
            "topics": topics,
            "clarification": any(t in text for t in self.clarification),
            "sensitive": any(t in text for t in self.sensitive),
        }
