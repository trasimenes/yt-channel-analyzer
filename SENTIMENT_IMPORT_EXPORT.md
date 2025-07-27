# Sentiment Analysis Import/Export Documentation

## Overview
The sentiment analysis feature now includes import/export functionality to backup and transfer sentiment data between environments.

## Features

### Export
- Export all sentiment analysis data as JSON
- Includes video metadata, engagement metrics, and sentiment classifications
- Exports up to 1000 videos with highest view counts
- Available via UI button or API endpoint

### Import
- Import previously exported sentiment data
- Updates existing videos or creates new ones
- Validates data format before import
- Shows import statistics (imported/skipped/total)

## Usage

### Web UI
1. Navigate to http://localhost:8082/sentiment-analysis
2. Click "Exporter" button to download sentiment data as JSON
3. Click "Importer" button to upload a JSON file

### API Endpoints

#### Export
```bash
GET /api/sentiment-analysis/export
```

Response format:
```json
{
  "success": true,
  "data": {
    "export_date": "2025-07-25T19:20:23.158563",
    "stats": {
      "total_videos_analyzed": 1000,
      "positive_count": 28,
      "negative_count": 1,
      "neutral_count": 971
    },
    "videos": [
      {
        "id": 3353,
        "video_id": "laBjQ9uJDg8",
        "title": "Video Title",
        "view_count": 119294592,
        "like_count": 1975,
        "comment_count": 124,
        "published_at": "2025-07-05 16:37:48.903590",
        "duration_seconds": 31,
        "category": "hub",
        "competitor_id": 8,
        "competitor_name": "Booking.com",
        "channel_url": "https://www.youtube.com/channel/...",
        "sentiment": "neutral",
        "engagement_rate": 0.0
      }
    ]
  }
}
```

#### Import
```bash
POST /api/sentiment-analysis/import
Content-Type: application/json

{
  "videos": [/* array of video objects */]
}
```

### Command Line Scripts

#### Export
```bash
python export_sentiment_data.py
```

#### Import
```bash
python import_sentiment_data.py sentiment_analysis_export_20250725_192023.json
```

## Data Format

### Video Object
- `id`: Internal database ID
- `video_id`: YouTube video ID
- `title`: Video title
- `view_count`: Number of views
- `like_count`: Number of likes
- `comment_count`: Number of comments
- `published_at`: Publication date
- `duration_seconds`: Video duration
- `category`: Video category (hero/hub/help)
- `competitor_id`: Internal competitor ID
- `competitor_name`: Competitor name
- `channel_url`: YouTube channel URL
- `sentiment`: Classified sentiment (positive/negative/neutral)
- `engagement_rate`: Engagement percentage

## Notes
- Import requires existing competitors in database (matched by channel_url)
- Sentiment classification uses keyword-based analysis
- Export limited to 1000 videos to keep file size manageable
- Import updates existing videos based on video_id