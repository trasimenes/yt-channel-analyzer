import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import datetime
from yt_channel_analyzer.analysis import hero_hub_help_matrix


def test_hero_hub_help_matrix_counts_and_views():
    comp = {
        "name": "Test Channel",
        "videos": [
            {"title": "Hero video", "category": "hero", "view_count": 100, "published_at": "2023-01-01"},
            {"title": "Hub video", "category": "hub", "view_count": 50, "published_at": "2023-01-02"},
            {"title": "Help video", "category": "help", "view_count": 30, "published_at": "2023-01-03"},
            {"title": "Another hero", "category": "hero", "view_count": 20, "published_at": "2023-01-04"}
        ]
    }
    counts, views = hero_hub_help_matrix(comp)
    assert counts == {"hero": 2, "hub": 1, "help": 1}
    assert views == {"hero": 120, "hub": 50, "help": 30}

    start_date = datetime.date(2023, 1, 2)
    end_date = datetime.date(2023, 1, 3)
    counts, views = hero_hub_help_matrix(comp, start_date, end_date)
    assert counts == {"hero": 0, "hub": 1, "help": 1}
    assert views == {"hero": 0, "hub": 50, "help": 30}
