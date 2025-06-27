from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Video:
    title: str
    category: str  # hero, hub, help
    view_count: int
    published_at: date


@dataclass
class Competitor:
    name: str
    videos: List[Video]
