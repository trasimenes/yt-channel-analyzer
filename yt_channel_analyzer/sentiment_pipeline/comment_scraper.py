"""
YouTube Comment Scraper
Scrapes 1000 comments per video for 8,800 videos = 8.8M comments total
Based on youtube_emotion_analysis_pipeline.md
"""
import time
import random
import sqlite3
from typing import List, Dict, Optional
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from pathlib import Path

class YouTubeCommentScraper:
    """Scraper pour extraire massivement les commentaires YouTube"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key is required")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting settings
        self.min_delay = 0.5
        self.max_delay = 1.5
        self.video_delay_min = 1.0
        self.video_delay_max = 3.0
        
        # Database setup
        self.db_path = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_massive.db'
        self.setup_database()
    
    def setup_database(self):
        """Setup database for massive comment storage (8.8M records)"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Main comments table - 8.8M records
            conn.execute('''
                CREATE TABLE IF NOT EXISTS comments_raw (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    comment_id TEXT UNIQUE,
                    comment_text TEXT NOT NULL,
                    like_count INTEGER DEFAULT 0,
                    published_at TEXT,
                    author_name TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON comments_raw(video_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_processed ON comments_raw(processed)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON comments_raw(scraped_at)')
            
            # Progress tracking table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scraping_progress (
                    video_id TEXT PRIMARY KEY,
                    comments_scraped INTEGER DEFAULT 0,
                    target_comments INTEGER DEFAULT 1000,
                    status TEXT DEFAULT 'pending',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            conn.commit()
            self.logger.info("✅ Database setup completed for sentiment analysis")
    
    def scrape_video_comments(self, video_id: str, max_comments: int = 1000) -> List[Dict]:
        """Scrape up to 1000 comments per video with rate limiting"""
        comments = []
        next_page_token = None
        
        self.logger.info(f"🎯 Scraping video {video_id} (target: {max_comments} comments)")
        
        # Update progress - started
        self._update_progress(video_id, 0, max_comments, 'in_progress')
        
        while len(comments) < max_comments:
            try:
                response = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),
                    pageToken=next_page_token,
                    order='relevance',  # Most relevant comments first
                    textFormat='plainText'
                ).execute()
                
                for item in response['items']:
                    comment_data = item['snippet']['topLevelComment']['snippet']
                    
                    comment = {
                        'video_id': video_id,
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'text': comment_data['textDisplay'],
                        'like_count': comment_data.get('likeCount', 0),
                        'published_at': comment_data['publishedAt'],
                        'author_name': comment_data.get('authorDisplayName', 'Unknown')
                    }
                    comments.append(comment)
                    
                    # Include replies if they exist
                    if 'replies' in item:
                        for reply in item['replies']['comments']:
                            reply_data = reply['snippet']
                            reply_comment = {
                                'video_id': video_id,
                                'comment_id': reply['id'],
                                'text': reply_data['textDisplay'],
                                'like_count': reply_data.get('likeCount', 0),
                                'published_at': reply_data['publishedAt'],
                                'author_name': reply_data.get('authorDisplayName', 'Unknown')
                            }
                            comments.append(reply_comment)
                            
                            if len(comments) >= max_comments:
                                break
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                
                # Rate limiting between API calls
                delay = random.uniform(self.min_delay, self.max_delay)
                time.sleep(delay)
                
                # Update progress
                self._update_progress(video_id, len(comments), max_comments, 'in_progress')
                
            except HttpError as e:
                error_msg = f"YouTube API error for {video_id}: {e}"
                self.logger.error(error_msg)
                self._update_progress(video_id, len(comments), max_comments, 'error', error_msg)
                break
            
            except Exception as e:
                error_msg = f"Unexpected error scraping {video_id}: {e}"
                self.logger.error(error_msg)
                self._update_progress(video_id, len(comments), max_comments, 'error', error_msg)
                break
        
        # Final comments (limit to max_comments)
        final_comments = comments[:max_comments]
        
        # Update progress - completed
        status = 'completed' if len(final_comments) > 0 else 'failed'
        self._update_progress(video_id, len(final_comments), max_comments, status)
        
        self.logger.info(f"✅ Scraped {len(final_comments)} comments for video {video_id}")
        return final_comments
    
    def _update_progress(self, video_id: str, scraped: int, target: int, status: str, error: str = None):
        """Update scraping progress in database"""
        with sqlite3.connect(str(self.db_path)) as conn:
            if status == 'in_progress' and scraped == 0:
                # First update - insert
                conn.execute('''
                    INSERT OR REPLACE INTO scraping_progress 
                    (video_id, comments_scraped, target_comments, status, started_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                ''', (video_id, scraped, target, status))
            else:
                # Update existing
                update_fields = ['comments_scraped = ?', 'status = ?']
                values = [scraped, status]
                
                if status in ('completed', 'failed', 'error'):
                    update_fields.append('completed_at = datetime("now")')
                
                if error:
                    update_fields.append('error_message = ?')
                    values.append(error)
                
                values.append(video_id)  # WHERE clause
                
                conn.execute(f'''
                    UPDATE scraping_progress 
                    SET {", ".join(update_fields)}
                    WHERE video_id = ?
                ''', values)
            
            conn.commit()
    
    def save_comments_batch(self, comments: List[Dict]):
        """Save batch of comments to database"""
        if not comments:
            return
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executemany('''
                INSERT OR IGNORE INTO comments_raw 
                (video_id, comment_id, comment_text, like_count, published_at, author_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                (c['video_id'], c['comment_id'], c['text'], c['like_count'], c['published_at'], c['author_name'])
                for c in comments
            ])
            
            conn.commit()
            self.logger.info(f"💾 Saved {len(comments)} comments to database")
    
    def get_all_video_ids(self) -> List[str]:
        """Get all video IDs from the main database"""
        main_db_path = Path(__file__).parent.parent.parent / 'instance' / 'database.db'
        
        with sqlite3.connect(str(main_db_path)) as conn:
            cursor = conn.execute('SELECT DISTINCT video_id FROM video WHERE video_id IS NOT NULL')
            video_ids = [row[0] for row in cursor.fetchall()]
        
        self.logger.info(f"🎯 Found {len(video_ids)} videos to scrape")
        return video_ids
    
    def scrape_all_videos(self, batch_size: int = 100):
        """Main function: Scrape all 8,800 videos × 1000 comments = 8.8M comments"""
        video_ids = self.get_all_video_ids()
        total_videos = len(video_ids)
        
        self.logger.info(f"🚀 Starting massive scraping: {total_videos} videos × 1000 comments = {total_videos * 1000:,} target comments")
        
        total_processed = 0
        total_comments_scraped = 0
        
        for i, video_id in enumerate(video_ids):
            self.logger.info(f"📹 Processing video {i+1}/{total_videos}: {video_id}")
            
            # Check if already processed
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    'SELECT status, comments_scraped FROM scraping_progress WHERE video_id = ?',
                    (video_id,)
                )
                result = cursor.fetchone()
                
                if result and result[0] == 'completed':
                    total_comments_scraped += result[1]
                    self.logger.info(f"⏭️ Skipping {video_id} (already completed: {result[1]} comments)")
                    continue
            
            # Scrape comments
            comments = self.scrape_video_comments(video_id, 1000)
            
            # Save to database
            if comments:
                self.save_comments_batch(comments)
                total_comments_scraped += len(comments)
            
            total_processed += 1
            
            # Progress reporting
            if total_processed % batch_size == 0:
                progress_pct = (total_processed / total_videos) * 100
                avg_comments = total_comments_scraped / total_processed if total_processed > 0 else 0
                
                self.logger.info(f"""
                📊 PROGRESS REPORT:
                ├── Videos processed: {total_processed:,}/{total_videos:,} ({progress_pct:.1f}%)
                ├── Comments scraped: {total_comments_scraped:,}
                ├── Average per video: {avg_comments:.0f}
                └── Estimated total: {(avg_comments * total_videos):,.0f} comments
                """)
            
            # Rate limiting between videos
            delay = random.uniform(self.video_delay_min, self.video_delay_max)
            time.sleep(delay)
        
        self.logger.info(f"""
        🎉 SCRAPING COMPLETED!
        ├── Total videos processed: {total_processed:,}
        ├── Total comments scraped: {total_comments_scraped:,}
        └── Database: {self.db_path}
        """)
        
        return {
            'videos_processed': total_processed,
            'comments_scraped': total_comments_scraped,
            'database_path': str(self.db_path)
        }
    
    def get_scraping_stats(self) -> Dict:
        """Get current scraping statistics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute('''
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(comments_scraped) as total_comments,
                    AVG(comments_scraped) as avg_comments
                FROM scraping_progress 
                GROUP BY status
            ''')
            
            stats = {
                'by_status': {},
                'total_videos': 0,
                'total_comments': 0
            }
            
            for row in cursor.fetchall():
                status, count, total_comments, avg_comments = row
                stats['by_status'][status] = {
                    'videos': count,
                    'total_comments': total_comments or 0,
                    'avg_comments': avg_comments or 0
                }
                stats['total_videos'] += count
                stats['total_comments'] += total_comments or 0
            
            return stats