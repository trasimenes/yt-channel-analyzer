"""
Fast YouTube Comment Scraper - Optimized Version
Scrapes only top 20 comments per video for quality analysis
8,800 videos × 20 comments = 176,000 high-quality comments
"""
import time
import sqlite3
from typing import List, Dict, Optional
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

class FastYouTubeScraper:
    """Optimized scraper for top 20 comments per video"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key is required")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.db_path = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_fast.db'
        self.setup_database()
    
    def setup_database(self):
        """Setup optimized database for 176K comments"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Fast comments table - 176K records
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fast_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    comment_id TEXT UNIQUE,
                    comment_text TEXT NOT NULL,
                    author_name TEXT,
                    like_count INTEGER DEFAULT 0,
                    published_at TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_fast_video_id ON fast_comments(video_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_fast_processed ON fast_comments(processed)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_fast_like_count ON fast_comments(like_count)')
            
            # Progress tracking table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fast_scraping_progress (
                    video_id TEXT PRIMARY KEY,
                    comments_scraped INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    scraped_at TIMESTAMP,
                    error_message TEXT,
                    quota_used INTEGER DEFAULT 1
                )
            ''')
            
            conn.commit()
            self.logger.info("✅ Fast database setup completed")
    
    def get_top_20_comments(self, video_id: str) -> Dict:
        """Récupérer top 20 commentaires (1 seule requête API)"""
        try:
            request = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=20,
                order='relevance',
                textFormat='plainText'
            )
            
            response = request.execute()
            comments = []
            
            for item in response['items']:
                comment_data = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'video_id': video_id,
                    'comment_id': item['snippet']['topLevelComment']['id'],
                    'text': comment_data['textDisplay'],
                    'author': comment_data['authorDisplayName'],
                    'like_count': comment_data.get('likeCount', 0),
                    'published_at': comment_data['publishedAt']
                })
            
            return {
                'video_id': video_id,
                'comments': comments,
                'success': True,
                'quota_used': 1  # Une seule requête !
            }
            
        except HttpError as e:
            if 'commentsDisabled' in str(e) or 'disabled comments' in str(e):
                # Comments disabled on this video
                return {
                    'video_id': video_id,
                    'comments': [],
                    'success': True,  # Not an error, just no comments
                    'quota_used': 1,
                    'note': 'Comments disabled'
                }
            else:
                return {
                    'video_id': video_id,
                    'comments': [],
                    'success': False,
                    'quota_used': 1,
                    'error': str(e)
                }
        except Exception as e:
            return {
                'video_id': video_id,
                'comments': [],
                'success': False,
                'quota_used': 1,
                'error': str(e)
            }
    
    def save_video_comments(self, result: Dict):
        """Save comments for one video to database"""
        if not result['comments']:
            # Still record the attempt
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO fast_scraping_progress 
                    (video_id, comments_scraped, status, scraped_at, error_message, quota_used)
                    VALUES (?, ?, ?, datetime('now'), ?, ?)
                ''', (
                    result['video_id'], 
                    0, 
                    'completed' if result['success'] else 'failed',
                    result.get('error') or result.get('note'),
                    result['quota_used']
                ))
                conn.commit()
            return
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Save comments
            conn.executemany('''
                INSERT OR IGNORE INTO fast_comments 
                (video_id, comment_id, comment_text, author_name, like_count, published_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                (c['video_id'], c['comment_id'], c['text'], c['author'], c['like_count'], c['published_at'])
                for c in result['comments']
            ])
            
            # Update progress
            conn.execute('''
                INSERT OR REPLACE INTO fast_scraping_progress 
                (video_id, comments_scraped, status, scraped_at, quota_used)
                VALUES (?, ?, 'completed', datetime('now'), ?)
            ''', (result['video_id'], len(result['comments']), result['quota_used']))
            
            conn.commit()
    
    def get_all_video_ids(self) -> List[str]:
        """Get all video IDs from the main database"""
        main_db_path = Path(__file__).parent.parent.parent / 'instance' / 'database.db'
        
        with sqlite3.connect(str(main_db_path)) as conn:
            cursor = conn.execute('SELECT DISTINCT video_id FROM video WHERE video_id IS NOT NULL')
            video_ids = [row[0] for row in cursor.fetchall()]
        
        self.logger.info(f"🎯 Found {len(video_ids)} videos to scrape")
        return video_ids
    
    def get_pending_video_ids(self) -> List[str]:
        """Get video IDs that haven't been scraped yet"""
        all_video_ids = self.get_all_video_ids()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute('''
                SELECT video_id FROM fast_scraping_progress 
                WHERE status = 'completed'
            ''')
            completed_ids = {row[0] for row in cursor.fetchall()}
        
        pending_ids = [vid for vid in all_video_ids if vid not in completed_ids]
        self.logger.info(f"📋 Found {len(pending_ids)} pending videos (out of {len(all_video_ids)} total)")
        return pending_ids
    
    def scrape_all_videos_fast(self, max_workers: int = 5, resume: bool = True):
        """Scraper 8,800 vidéos rapidement avec 20 commentaires chacune"""
        
        if resume:
            video_ids = self.get_pending_video_ids()
        else:
            video_ids = self.get_all_video_ids()
        
        if not video_ids:
            self.logger.info("✅ All videos already scraped!")
            return self.get_scraping_stats()
        
        total_videos = len(video_ids)
        total_quota = 0
        total_comments = 0
        successful_videos = 0
        failed_videos = 0
        
        self.logger.info(f"🚀 Starting fast scraping: {total_videos} videos × 20 comments = {total_videos * 20:,} target comments")
        self.logger.info(f"📊 Estimated quota usage: {total_videos} (out of 10,000 daily limit)")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_video = {
                executor.submit(self.get_top_20_comments, video_id): video_id 
                for video_id in video_ids
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_video)):
                video_id = future_to_video[future]
                
                try:
                    result = future.result()
                    total_quota += result['quota_used']
                    
                    if result['success']:
                        successful_videos += 1
                        comments_count = len(result['comments'])
                        total_comments += comments_count
                        
                        if comments_count > 0:
                            self.logger.info(f"✅ [{i+1}/{total_videos}] {video_id}: {comments_count} commentaires")
                        else:
                            note = result.get('note', 'No comments')
                            self.logger.info(f"⚪ [{i+1}/{total_videos}] {video_id}: {note}")
                    else:
                        failed_videos += 1
                        error = result.get('error', 'Unknown error')
                        self.logger.warning(f"❌ [{i+1}/{total_videos}] {video_id}: {error}")
                    
                    # Save to database
                    self.save_video_comments(result)
                    
                    # Progress report every 100 videos
                    if (i + 1) % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = (i + 1) / elapsed
                        eta = (total_videos - i - 1) / rate if rate > 0 else 0
                        
                        self.logger.info(f"""
                        📊 PROGRESS REPORT:
                        ├── Videos processed: {i+1:,}/{total_videos:,} ({(i+1)/total_videos*100:.1f}%)
                        ├── Successful: {successful_videos:,} | Failed: {failed_videos:,}
                        ├── Comments scraped: {total_comments:,}
                        ├── Quota used: {total_quota:,}/10,000
                        ├── Rate: {rate:.1f} videos/sec
                        └── ETA: {eta/60:.1f} minutes
                        """)
                    
                except Exception as e:
                    failed_videos += 1
                    self.logger.error(f"❌ [{i+1}/{total_videos}] {video_id}: Unexpected error: {e}")
        
        # Final report
        elapsed_time = time.time() - start_time
        self.logger.info(f"""
        🎉 FAST SCRAPING COMPLETED!
        ├── Total videos processed: {total_videos:,}
        ├── Successful: {successful_videos:,} | Failed: {failed_videos:,}
        ├── Total comments scraped: {total_comments:,}
        ├── Quota used: {total_quota:,}/10,000 ({total_quota/10000*100:.1f}%)
        ├── Average comments per video: {total_comments/successful_videos:.1f}
        ├── Processing time: {elapsed_time/60:.1f} minutes
        └── Rate: {total_videos/elapsed_time:.1f} videos/sec
        """)
        
        return {
            'videos_processed': total_videos,
            'successful_videos': successful_videos,
            'failed_videos': failed_videos,
            'comments_scraped': total_comments,
            'quota_used': total_quota,
            'processing_time': elapsed_time,
            'database_path': str(self.db_path)
        }
    
    def get_scraping_stats(self) -> Dict:
        """Get current scraping statistics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Total stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_videos,
                    SUM(comments_scraped) as total_comments,
                    SUM(quota_used) as total_quota,
                    AVG(comments_scraped) as avg_comments
                FROM fast_scraping_progress
            ''')
            total_stats = cursor.fetchone()
            
            # Status breakdown
            cursor = conn.execute('''
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(comments_scraped) as comments,
                    SUM(quota_used) as quota
                FROM fast_scraping_progress 
                GROUP BY status
            ''')
            status_breakdown = cursor.fetchall()
            
            # Comments in database
            cursor = conn.execute('SELECT COUNT(*) FROM fast_comments')
            db_comments = cursor.fetchone()[0]
        
        return {
            'total_videos': total_stats[0] if total_stats else 0,
            'total_comments': total_stats[1] if total_stats else 0,
            'total_quota_used': total_stats[2] if total_stats else 0,
            'avg_comments_per_video': total_stats[3] if total_stats else 0,
            'comments_in_db': db_comments,
            'status_breakdown': {
                status: {'videos': count, 'comments': comments, 'quota': quota}
                for status, count, comments, quota in status_breakdown
            }
        }

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run fast scraper
    scraper = FastYouTubeScraper()
    
    # Run fast scraping
    results = scraper.scrape_all_videos_fast(max_workers=5)
    
    print(f"\n🎉 Fast scraping completed!")
    print(f"Results: {results}")