"""
Emotion Analyzer for 8.8M YouTube Comments
Processes comments using multilingual sentiment analysis
Based on youtube_emotion_analysis_pipeline.md
"""
import logging
import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import json

# Core ML libraries
from transformers import pipeline
from langdetect import detect, DetectorFactory
import torch

# Set seed for consistent language detection
DetectorFactory.seed = 0

class EmotionAnalyzer:
    """Analyzes emotions from 8.8M YouTube comments using multilingual models"""
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual"):
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        self.supported_languages = ['fr', 'en', 'de', 'nl', 'es']  # FR, EN, DE, NL, BE
        
        # Database paths
        self.emotions_db_path = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_massive.db'
        self.main_db_path = Path(__file__).parent.parent.parent / 'instance' / 'database.db'
        
        # Initialize emotion analyzer
        self.emotion_analyzer = None
        self._load_model()
        
    def _load_model(self):
        """Load the multilingual sentiment analysis model"""
        try:
            self.logger.info(f"🤖 Loading emotion model: {self.model_name}")
            
            # Use GPU if available
            device = 0 if torch.cuda.is_available() else -1
            self.emotion_analyzer = pipeline(
                "text-classification",
                model=self.model_name,
                device=device,
                return_all_scores=True
            )
            
            self.logger.info(f"✅ Emotion model loaded successfully (device: {'GPU' if device == 0 else 'CPU'})")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load emotion model: {e}")
            raise
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of the comment text"""
        try:
            if len(text.strip()) < 3:
                return None
            
            detected_lang = detect(text)
            return detected_lang if detected_lang in self.supported_languages else None
            
        except:
            return None
    
    def analyze_comment_emotion(self, comment_text: str) -> Optional[Dict]:
        """Analyze emotion of a single comment"""
        try:
            # Filter short comments
            if len(comment_text.strip()) < 10:
                return None
            
            # Detect language
            language = self.detect_language(comment_text)
            if not language:
                return None
            
            # Clean text (remove excessive whitespace, emojis that might break the model)
            cleaned_text = ' '.join(comment_text.split())[:512]  # Limit to 512 chars
            
            # Analyze emotion
            results = self.emotion_analyzer(cleaned_text)
            
            # Find best prediction
            best_prediction = max(results[0], key=lambda x: x['score'])
            
            # Map labels to our format
            emotion_mapping = {
                'LABEL_0': 'negative',
                'LABEL_1': 'neutral', 
                'LABEL_2': 'positive',
                'NEGATIVE': 'negative',
                'NEUTRAL': 'neutral',
                'POSITIVE': 'positive'
            }
            
            emotion_type = emotion_mapping.get(best_prediction['label'], 'neutral')
            
            return {
                'emotion_type': emotion_type,
                'confidence': best_prediction['score'],
                'language': language,
                'all_scores': {
                    result['label']: result['score'] for result in results[0]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing comment emotion: {e}")
            return None
    
    def process_comment_batch(self, comments_batch: List[Dict]) -> List[Dict]:
        """Process a batch of comments for emotion analysis"""
        results = []
        batch_size = len(comments_batch)
        
        self.logger.info(f"🧠 Processing batch of {batch_size} comments")
        
        for i, comment in enumerate(comments_batch):
            try:
                emotion_result = self.analyze_comment_emotion(comment['comment_text'])
                
                if emotion_result:
                    results.append({
                        'comment_id': comment['comment_id'],
                        'video_id': comment['video_id'],
                        'emotion_type': emotion_result['emotion_type'],
                        'confidence': emotion_result['confidence'],
                        'language': emotion_result['language'],
                        'like_count': comment.get('like_count', 0),
                        'published_at': comment.get('published_at'),
                        'author_name': comment.get('author_name')
                    })
                
                # Progress tracking
                if (i + 1) % 100 == 0:
                    self.logger.info(f"   Processed {i + 1}/{batch_size} comments")
                    
            except Exception as e:
                self.logger.error(f"Error processing comment {comment.get('comment_id', 'unknown')}: {e}")
                continue
        
        success_rate = len(results) / batch_size * 100 if batch_size > 0 else 0
        self.logger.info(f"✅ Batch processed: {len(results)}/{batch_size} comments ({success_rate:.1f}% success)")
        
        return results
    
    def save_emotion_results(self, emotion_results: List[Dict]):
        """Save emotion analysis results to database"""
        if not emotion_results:
            return
        
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            # Insert emotion results
            conn.executemany('''
                INSERT OR REPLACE INTO comment_emotions 
                (comment_id, video_id, emotion_type, confidence, language, like_count, published_at, author_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (r['comment_id'], r['video_id'], r['emotion_type'], r['confidence'], 
                 r['language'], r['like_count'], r['published_at'], r['author_name'])
                for r in emotion_results
            ])
            
            conn.commit()
            self.logger.info(f"💾 Saved {len(emotion_results)} emotion results to database")
    
    def aggregate_video_emotions(self, video_id: str) -> Optional[Dict]:
        """Calculate emotion metrics for a specific video"""
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            # Get all emotions for this video
            cursor = conn.execute('''
                SELECT emotion_type, confidence, language, like_count
                FROM comment_emotions 
                WHERE video_id = ?
            ''', (video_id,))
            
            results = cursor.fetchall()
            
        if not results:
            return None
        
        df = pd.DataFrame(results, columns=['emotion_type', 'confidence', 'language', 'like_count'])
        
        total_comments = len(df)
        emotion_counts = df['emotion_type'].value_counts()
        
        # Get competitor and country info from main database
        with sqlite3.connect(str(self.main_db_path)) as conn:
            cursor = conn.execute('''
                SELECT c.name, c.country 
                FROM video v 
                JOIN concurrent c ON v.concurrent_id = c.id 
                WHERE v.video_id = ?
            ''', (video_id,))
            result = cursor.fetchone()
            competitor, country = result if result else (None, None)
        
        return {
            'video_id': video_id,
            'dominant_emotion': emotion_counts.index[0] if len(emotion_counts) > 0 else 'neutral',
            'total_comments': total_comments,
            'positive_ratio': emotion_counts.get('positive', 0) / total_comments,
            'negative_ratio': emotion_counts.get('negative', 0) / total_comments,
            'neutral_ratio': emotion_counts.get('neutral', 0) / total_comments,
            'avg_confidence': df['confidence'].mean(),
            'emotion_diversity': len(df['emotion_type'].unique()),
            'language_distribution': df['language'].value_counts().to_dict(),
            'competitor': competitor,
            'country': country,
            'high_engagement_emotions': df[df['like_count'] > 5]['emotion_type'].value_counts().to_dict()
        }
    
    def save_video_emotion_summary(self, video_summary: Dict):
        """Save aggregated video emotion summary"""
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO video_emotion_summary 
                (video_id, dominant_emotion, emotion_diversity_score, avg_confidence, total_comments,
                 positive_ratio, negative_ratio, neutral_ratio, language_distribution, country, competitor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_summary['video_id'],
                video_summary['dominant_emotion'],
                video_summary['emotion_diversity'],
                video_summary['avg_confidence'],
                video_summary['total_comments'],
                video_summary['positive_ratio'],
                video_summary['negative_ratio'],
                video_summary['neutral_ratio'],
                json.dumps(video_summary['language_distribution']),
                video_summary['country'],
                video_summary['competitor']
            ))
            
            conn.commit()
            self.logger.info(f"📊 Saved emotion summary for video {video_summary['video_id']}")
    
    def get_unprocessed_comments(self, batch_size: int = 1000) -> List[Dict]:
        """Get batch of unprocessed comments from raw comments table"""
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            cursor = conn.execute('''
                SELECT id, video_id, comment_id, comment_text, like_count, published_at, author_name
                FROM comments_raw 
                WHERE processed = 0 
                LIMIT ?
            ''', (batch_size,))
            
            results = cursor.fetchall()
            
        return [
            {
                'id': r[0],
                'video_id': r[1], 
                'comment_id': r[2],
                'comment_text': r[3],
                'like_count': r[4],
                'published_at': r[5],
                'author_name': r[6]
            }
            for r in results
        ]
    
    def mark_comments_processed(self, comment_ids: List[int]):
        """Mark comments as processed in the raw table"""
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            conn.executemany(
                'UPDATE comments_raw SET processed = 1 WHERE id = ?',
                [(cid,) for cid in comment_ids]
            )
            conn.commit()
    
    def process_all_comments(self, batch_size: int = 1000, max_workers: int = 4):
        """Main function: Process all 8.8M comments for emotion analysis"""
        self.logger.info(f"🚀 Starting emotion analysis of 8.8M comments")
        
        total_processed = 0
        total_successful = 0
        start_time = time.time()
        
        while True:
            # Get batch of unprocessed comments
            comments_batch = self.get_unprocessed_comments(batch_size)
            
            if not comments_batch:
                self.logger.info("✅ No more comments to process")
                break
            
            batch_start_time = time.time()
            
            # Process emotion analysis
            emotion_results = self.process_comment_batch(comments_batch)
            
            # Save results
            if emotion_results:
                self.save_emotion_results(emotion_results)
                total_successful += len(emotion_results)
            
            # Mark as processed
            comment_ids = [c['id'] for c in comments_batch]
            self.mark_comments_processed(comment_ids)
            
            total_processed += len(comments_batch)
            batch_time = time.time() - batch_start_time
            
            # Progress reporting
            if total_processed % (batch_size * 10) == 0:  # Every 10 batches
                elapsed_time = time.time() - start_time
                processing_rate = total_processed / elapsed_time
                success_rate = total_successful / total_processed * 100
                eta_seconds = (8800000 - total_processed) / processing_rate if processing_rate > 0 else 0
                
                self.logger.info(f"""
                📊 EMOTION ANALYSIS PROGRESS:
                ├── Comments processed: {total_processed:,}/8,800,000 ({total_processed/8800000*100:.1f}%)
                ├── Successful analyses: {total_successful:,} ({success_rate:.1f}%)
                ├── Processing rate: {processing_rate:.1f} comments/sec
                ├── Batch time: {batch_time:.1f}s
                └── ETA: {eta_seconds/3600:.1f} hours
                """)
        
        # Final summary
        total_time = time.time() - start_time
        self.logger.info(f"""
        🎉 EMOTION ANALYSIS COMPLETED!
        ├── Total processed: {total_processed:,} comments
        ├── Successful analyses: {total_successful:,} comments
        ├── Success rate: {total_successful/total_processed*100:.1f}%
        ├── Total time: {total_time/3600:.1f} hours
        └── Average rate: {total_processed/total_time:.1f} comments/sec
        """)
        
        return {
            'total_processed': total_processed,
            'total_successful': total_successful,
            'processing_time': total_time,
            'success_rate': total_successful / total_processed if total_processed > 0 else 0
        }
    
    def generate_video_summaries(self):
        """Generate emotion summaries for all videos"""
        self.logger.info("📊 Generating video emotion summaries...")
        
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            cursor = conn.execute('SELECT DISTINCT video_id FROM comment_emotions')
            video_ids = [row[0] for row in cursor.fetchall()]
        
        for i, video_id in enumerate(video_ids):
            summary = self.aggregate_video_emotions(video_id)
            if summary:
                self.save_video_emotion_summary(summary)
            
            if (i + 1) % 100 == 0:
                self.logger.info(f"Generated summaries for {i + 1}/{len(video_ids)} videos")
        
        self.logger.info(f"✅ Generated emotion summaries for {len(video_ids)} videos")
    
    def get_processing_stats(self) -> Dict:
        """Get current emotion processing statistics"""
        with sqlite3.connect(str(self.emotions_db_path)) as conn:
            # Raw comments stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_raw,
                    SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed_raw,
                    SUM(CASE WHEN processed = 0 THEN 1 ELSE 0 END) as pending_raw
                FROM comments_raw
            ''')
            raw_stats = cursor.fetchone()
            
            # Emotion analysis stats
            cursor = conn.execute('''
                SELECT 
                    emotion_type,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM comment_emotions 
                GROUP BY emotion_type
            ''')
            emotion_stats = cursor.fetchall()
            
            # Language distribution
            cursor = conn.execute('''
                SELECT language, COUNT(*) as count
                FROM comment_emotions 
                GROUP BY language
            ''')
            language_stats = cursor.fetchall()
        
        return {
            'raw_comments': {
                'total': raw_stats[0] if raw_stats else 0,
                'processed': raw_stats[1] if raw_stats else 0,
                'pending': raw_stats[2] if raw_stats else 0,
                'completion_rate': (raw_stats[1] / raw_stats[0] * 100) if raw_stats and raw_stats[0] > 0 else 0
            },
            'emotions': {
                emotion[0]: {'count': emotion[1], 'avg_confidence': emotion[2]}
                for emotion in emotion_stats
            },
            'languages': dict(language_stats)
        }


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run emotion analyzer
    analyzer = EmotionAnalyzer()
    
    # Process all comments
    results = analyzer.process_all_comments()
    
    # Generate video summaries
    analyzer.generate_video_summaries()
    
    print(f"\n🎉 Emotion analysis pipeline completed!")
    print(f"Results: {results}")