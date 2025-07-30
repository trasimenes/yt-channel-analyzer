"""
Cache utilities for backward compatibility
Provides cache functions that were previously in app.py
"""
import os
import json
from typing import Dict, Any


def ensure_cache_dir():
    """Ensure cache directory exists"""
    cache_dir = "cache_recherches"
    os.makedirs(cache_dir, exist_ok=True)


def load_cache() -> Dict[str, Any]:
    """Load cache data from file or return empty dict"""
    cache_file = "cache_recherches/recherches.json"
    
    if not os.path.exists(cache_file):
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[CACHE] Error loading cache: {e}")
        return {}


def save_cache(cache_data: Dict[str, Any]) -> bool:
    """Save cache data to file"""
    ensure_cache_dir()
    cache_file = "cache_recherches/recherches.json"
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[CACHE] Error saving cache: {e}")
        return False


def get_channel_key(channel_url: str) -> str:
    """Generate unique key for a YouTube channel URL"""
    if "@" in channel_url:
        # Format @username
        return channel_url.split("@")[-1].split("/")[0].lower()
    elif "/c/" in channel_url:
        # Format /c/channelname
        return channel_url.split("/c/")[-1].split("/")[0].lower()
    elif "/channel/" in channel_url:
        # Format /channel/UC...
        return channel_url.split("/channel/")[-1].split("/")[0]
    elif "/user/" in channel_url:
        # Format /user/username
        return channel_url.split("/user/")[-1].split("/")[0].lower()
    else:
        # Fallback: normalize URL for unique key
        return channel_url.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_')


def save_competitor_data(channel_url: str, videos: list) -> int:
    """Save competitor data using database functions"""
    try:
        from .database import refresh_competitor_data
        from .youtube_api_client import create_youtube_client
        
        print(f"[SAVE] 💾 Saving {len(videos)} videos for {channel_url}")
        
        # Get channel info to enrich data
        channel_info = None
        try:
            youtube_client = create_youtube_client()
            channel_info = youtube_client.get_channel_info(channel_url)
            print(f"[SAVE] 📊 Channel info: {channel_info.get('title', 'N/A')}")
        except Exception as e:
            print(f"[SAVE] ⚠️ Could not get channel info: {e}")
        
        # Use intelligent refresh (creation + automatic enrichment)
        result = refresh_competitor_data(channel_url, videos, channel_info)
        
        if result['success']:
            action = result['action']
            competitor_name = result.get('competitor_name', 'Competitor')
            competitor_id = result['competitor_id']
            
            if action == 'created':
                print(f"[SAVE] ✅ NEW competitor created: {competitor_name} (ID: {competitor_id})")
            else:  # refreshed
                print(f"[SAVE] 🔄 ENRICHED: {competitor_name} (ID: {competitor_id})")
                print(f"[SAVE] 📈 New: {result['new_videos']}, Enriched: {result['enriched_videos']}")
            
            return competitor_id
            
        else:
            print(f"[SAVE] ❌ Error saving: {result.get('error', 'Unknown error')}")
            return 0
            
    except Exception as e:
        print(f"[SAVE] ❌ Exception in save_competitor_data: {e}")
        import traceback
        traceback.print_exc()
        return 0