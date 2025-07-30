#!/usr/bin/env python3
"""
🔄 Create Sentiment Analysis Backup
Saves the current sentiment analysis data as a backup for production fallback
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(__file__))

def create_sentiment_backup():
    """Create a backup of current sentiment analysis data"""
    
    print("🔄 CREATING SENTIMENT ANALYSIS BACKUP")
    print("=" * 60)
    
    # Try to get data from existing sources
    backup_created = False
    
    # 1. Try to copy from production JSON if it exists
    prod_json = Path('static/sentiment_analysis_production.json')
    if prod_json.exists():
        print("✅ Found production JSON, creating backup...")
        
        try:
            with open(prod_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update metadata
            if 'export_info' not in data:
                data['export_info'] = {}
            
            data['export_info']['backup_date'] = datetime.now().isoformat()
            data['export_info']['backup_source'] = 'production_json'
            
            # Save as backup
            backup_path = Path('static/sentiment_analysis_last_backup.json')
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Backup saved: {backup_path}")
            print(f"📊 Contains: {data['stats']['total_videos_analyzed']} videos, {data['stats']['total_comments_analyzed']} comments")
            backup_created = True
            
        except Exception as e:
            print(f"❌ Error creating backup from production JSON: {e}")
    
    # 2. If no production JSON, try to export from database
    if not backup_created:
        print("📊 No production JSON found, trying to export from database...")
        
        try:
            # Import and run the export script
            from export_sentiment_production import export_sentiment_for_production
            
            if export_sentiment_for_production():
                # Now copy the newly created file as backup
                if prod_json.exists():
                    with open(prod_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    data['export_info']['backup_date'] = datetime.now().isoformat()
                    data['export_info']['backup_source'] = 'fresh_export'
                    
                    backup_path = Path('static/sentiment_analysis_last_backup.json')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Backup created from fresh export: {backup_path}")
                    backup_created = True
                    
        except Exception as e:
            print(f"❌ Error creating backup from database: {e}")
    
    # 3. If still no backup, create a minimal sample
    if not backup_created:
        print("⚠️  Creating minimal sample backup...")
        
        sample_data = {
            "export_info": {
                "export_date": datetime.now().isoformat(),
                "source": "sample_fallback",
                "version": "1.0",
                "total_videos": 3,
                "backup_date": datetime.now().isoformat(),
                "backup_source": "minimal_sample"
            },
            "stats": {
                "total_videos_analyzed": 3,
                "total_comments_analyzed": 60,
                "positive_count": 40,
                "negative_count": 10,
                "neutral_count": 10,
                "positive_percentage": 66.67,
                "negative_percentage": 16.67,
                "neutral_percentage": 16.67,
                "avg_confidence": 0.85,
                "engagement_correlation": 0.42
            },
            "videos": [
                {
                    "video_id": "sample1",
                    "total_comments": 30,
                    "positive_count": 25,
                    "negative_count": 3,
                    "neutral_count": 2,
                    "avg_confidence": 90,
                    "dominant_sentiment": "positive",
                    "positive_percentage": 83.3,
                    "title": "Sample Video - Positive Reception",
                    "thumbnail_url": "",
                    "competitor_name": "Sample Competitor",
                    "view_count": 50000,
                    "like_count": 2500,
                    "original_comment_count": 300,
                    "published_at": "2025-01-15T00:00:00",
                    "rank": 1
                },
                {
                    "video_id": "sample2",
                    "total_comments": 20,
                    "positive_count": 10,
                    "negative_count": 5,
                    "neutral_count": 5,
                    "avg_confidence": 75,
                    "dominant_sentiment": "positive",
                    "positive_percentage": 50.0,
                    "title": "Sample Video - Mixed Reception",
                    "thumbnail_url": "",
                    "competitor_name": "Sample Competitor",
                    "view_count": 25000,
                    "like_count": 1000,
                    "original_comment_count": 150,
                    "published_at": "2025-01-10T00:00:00",
                    "rank": 2
                },
                {
                    "video_id": "sample3",
                    "total_comments": 10,
                    "positive_count": 5,
                    "negative_count": 2,
                    "neutral_count": 3,
                    "avg_confidence": 80,
                    "dominant_sentiment": "positive",
                    "positive_percentage": 50.0,
                    "title": "Sample Video - Neutral Reception",
                    "thumbnail_url": "",
                    "competitor_name": "Sample Competitor",
                    "view_count": 10000,
                    "like_count": 500,
                    "original_comment_count": 75,
                    "published_at": "2025-01-05T00:00:00",
                    "rank": 3
                }
            ],
            "charts_data": {
                "global_distribution": {
                    "positive": 40,
                    "negative": 10,
                    "neutral": 10
                },
                "country_sentiment_data": {},
                "competitor_sentiment_data": [],
                "temporal_sentiment_data": []
            }
        }
        
        backup_path = Path('static/sentiment_analysis_last_backup.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Minimal sample backup created: {backup_path}")
        backup_created = True
    
    print("\n" + "=" * 60)
    print("✅ BACKUP PROCESS COMPLETE")
    
    return backup_created


if __name__ == '__main__':
    create_sentiment_backup()