"""
Settings management module for YT Channel Analyzer
Handles loading and saving application settings to/from the database
"""
import json
from datetime import datetime
from .database import get_db_connection


def load_settings():
    """
    Load application settings from the database
    Returns a dictionary with all settings and their values
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Load all settings
        cursor.execute("SELECT key, value, value_type FROM app_settings")
        settings_rows = cursor.fetchall()
        
        settings = {}
        for row in settings_rows:
            key, value, value_type = row
            
            # Convert value based on type
            if value_type == 'boolean':
                settings[key] = value.lower() == 'true'
            elif value_type == 'integer':
                settings[key] = int(value) if value else 0
            elif value_type == 'float':
                settings[key] = float(value) if value else 0.0
            elif value_type == 'json':
                settings[key] = json.loads(value) if value else {}
            else:  # string
                settings[key] = value or ''
        
        # Set default values for missing settings
        default_settings = {
            'youtube_api_key': '',
            'paid_threshold': 10000,
            'auto_classify': True,
            'semantic_analysis': True,
            'debug_mode': False,
            'cache_enabled': True,
            'max_videos_per_channel': 1000,
            'classification_confidence_threshold': 0.7,
            'update_frequency_hours': 24,
            'enable_thumbnails': True,
            'enable_notifications': True,
            'default_sort_order': 'desc',
            'items_per_page': 50,
            'enable_advanced_analytics': True
        }
        
        # Merge defaults with loaded settings
        for key, default_value in default_settings.items():
            if key not in settings:
                settings[key] = default_value
        
        conn.close()
        return settings
        
    except Exception as e:
        print(f"[SETTINGS] Error loading settings: {e}")
        # Return minimal default settings on error
        return {
            'youtube_api_key': '',
            'paid_threshold': 10000,
            'auto_classify': True,
            'semantic_analysis': True,
            'debug_mode': False,
            'cache_enabled': True,
            'max_videos_per_channel': 1000,
            'classification_confidence_threshold': 0.7,
            'update_frequency_hours': 24,
            'enable_thumbnails': True,
            'enable_notifications': True,
            'default_sort_order': 'desc',
            'items_per_page': 50,
            'enable_advanced_analytics': True
        }


def save_settings(settings_dict):
    """
    Save application settings to the database
    
    Args:
        settings_dict (dict): Dictionary of settings to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Save each setting
        for key, value in settings_dict.items():
            # Determine value type
            if isinstance(value, bool):
                value_str = 'true' if value else 'false'
                value_type = 'boolean'
            elif isinstance(value, int):
                value_str = str(value)
                value_type = 'integer'
            elif isinstance(value, float):
                value_str = str(value)
                value_type = 'float'
            elif isinstance(value, (dict, list)):
                value_str = json.dumps(value)
                value_type = 'json'
            else:
                value_str = str(value)
                value_type = 'string'
            
            # Insert or update setting
            cursor.execute('''
                INSERT OR REPLACE INTO app_settings (key, value, value_type, updated_at)
                VALUES (?, ?, ?, datetime('now'))
            ''', (key, value_str, value_type))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[SETTINGS] Error saving settings: {e}")
        return False


def get_setting(key, default=None):
    """
    Get a single setting value
    
    Args:
        key (str): Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value or default
    """
    try:
        settings = load_settings()
        return settings.get(key, default)
    except Exception:
        return default


def set_setting(key, value):
    """
    Set a single setting value
    
    Args:
        key (str): Setting key
        value: Setting value
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        current_settings = load_settings()
        current_settings[key] = value
        return save_settings(current_settings)
    except Exception:
        return False


def get_youtube_api_key():
    """
    Get the YouTube API key from settings
    
    Returns:
        str: API key or empty string if not set
    """
    return get_setting('youtube_api_key', '')


def set_youtube_api_key(api_key):
    """
    Set the YouTube API key in settings
    
    Args:
        api_key (str): YouTube API key
        
    Returns:
        bool: True if successful, False otherwise
    """
    return set_setting('youtube_api_key', api_key)