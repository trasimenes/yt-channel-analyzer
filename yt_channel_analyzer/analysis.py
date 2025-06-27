from datetime import date, datetime
from typing import Dict, Tuple


def hero_hub_help_matrix(competitor: Dict, start: date | None = None, end: date | None = None) -> Tuple[Dict[str, int], Dict[str, int]]:
    counts = {"hero": 0, "hub": 0, "help": 0}
    views = {"hero": 0, "hub": 0, "help": 0}
    for video in competitor.get("videos", []):
        published = datetime.fromisoformat(video["published_at"]).date()
        if start and published < start:
            continue
        if end and published > end:
            continue
        category = video.get("category")
        if category not in counts:
            continue
        counts[category] += 1
        views[category] += video.get("view_count", 0)
    return counts, views
