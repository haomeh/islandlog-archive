"""Exclusion filter for news items: drops sports results and entertainment gossip.

Public-body terms only fill matched_terms. They are not required.

Standard library only.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_TERMS_PATH = Path(__file__).parent / "terms.json"


class NewsFilter:
    """Filters news items based on required terms and excluded categories."""

    def __init__(self, terms_data: Optional[Dict] = None):
        if terms_data is None:
            if DEFAULT_TERMS_PATH.exists():
                with open(DEFAULT_TERMS_PATH, "r", encoding="utf-8") as f:
                    terms_data = json.load(f)
            else:
                terms_data = {"include_terms": [], "exclude_categories": {}}

        self.include_terms: List[str] = terms_data.get("include_terms", [])
        self.exclude_categories: Dict[str, List[str]] = terms_data.get(
            "exclude_categories", {}
        )
        # Columns, commentary and life tips: matched in the title only.
        self.noise_title_terms: List[str] = terms_data.get("noise_title_terms", [])

    def check_match(self, title: str, summary: str = "") -> Tuple[List[str], bool]:
        """Checks text for positive include terms and negative exclusions.

        Returns (matched_terms, is_excluded).
        """
        text = f"{title} {summary}"

        # Check positive matches
        matched: List[str] = []
        for term in self.include_terms:
            # A term counts only as a whole name: hide longer listed terms that contain it
            # (法院 inside 立法院, 議會 inside 縣議會) before testing.
            masked = text
            for longer in sorted(self.include_terms, key=len, reverse=True):
                if longer != term and term in longer:
                    masked = masked.replace(longer, "\x00" * len(longer))
            if term in masked:
                matched.append(term)

        # Check exclusions (sports, entertainment)
        is_excluded = any(word in title for word in self.noise_title_terms)
        for category, words in self.exclude_categories.items():
            for word in words:
                if word in text:
                    is_excluded = True
                    break
            if is_excluded:
                break

        return matched, is_excluded

    def should_keep(self, title: str, summary: str = "") -> Tuple[bool, List[str]]:
        """Determines whether an item should be kept.

        Returns (should_keep, matched_terms).
        """
        matched, is_excluded = self.check_match(title, summary)
        if is_excluded:
            return False, []
        return True, matched
