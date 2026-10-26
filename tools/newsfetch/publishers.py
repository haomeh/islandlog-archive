"""Publisher names and owner groups (R88).

Each feed has a `publisher` (the brand shown on the page) and a `publisher_group` (the owner group).
The 2-publisher rule counts groups. Aliases map the spellings that outlets use to the brand.
"""

import json
from pathlib import Path
from typing import Dict, List

FEEDS_PATH = Path(__file__).with_name("feeds.json")


class PublisherIndex:
    """Looks up the brand and the owner group of a publisher name."""

    def __init__(self, feeds: List[Dict]):
        self.brand_of: Dict[str, str] = {}
        self.group_of: Dict[str, str] = {}
        for feed in feeds:
            brand = feed["publisher"]
            group = feed.get("publisher_group") or brand
            for name in [brand] + list(feed.get("aliases", [])):
                self.brand_of[name] = brand
            self.group_of[brand] = group

    def brand(self, name: str) -> str:
        return self.brand_of.get(name, name)

    def group(self, name: str) -> str:
        brand = self.brand(name)
        return self.group_of.get(brand, brand)


def load_index(path: Path = FEEDS_PATH) -> PublisherIndex:
    with open(path, "r", encoding="utf-8") as f:
        return PublisherIndex(json.load(f))
