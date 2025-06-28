from dataclasses import dataclass
from datetime import date
from typing import List, Optional


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
    region: Optional[str] = "Europe"  # Par défaut Europe
    industry: Optional[str] = None  # Optionnelle, peut être None
    custom_tags: Optional[List[str]] = None  # Tags personnalisés additionnels
