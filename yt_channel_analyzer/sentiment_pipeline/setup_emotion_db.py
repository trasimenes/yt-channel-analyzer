"""
Database Setup for Emotion Analysis Pipeline
Optimized for 8.8M comment records
Based on youtube_emotion_analysis_pipeline.md
"""
import sqlite3
import logging
from pathlib import Path

def setup_emotion_database():
    """Setup optimized database for 8.8M emotion records"""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    db_path = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_massive.db'
    db_path.parent.mkdir(exist_ok=True)
    
    logger.info(f"🏗️ Setting up emotion database: {db_path}")
    
    with sqlite3.connect(str(db_path)) as conn:
        # Enable WAL mode for better performance with concurrent reads
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA temp_store=memory')
        
        # Main emotion analysis table - 8.8M records
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comment_emotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                emotion_type TEXT NOT NULL CHECK (emotion_type IN ('positive', 'negative', 'neutral')),
                confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                language TEXT NOT NULL CHECK (language IN ('fr', 'en', 'de', 'nl', 'es')),
                like_count INTEGER DEFAULT 0,
                published_at TEXT,
                author_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(comment_id, video_id)
            )
        ''')
        
        # Performance indexes for emotion analysis
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_video_id ON comment_emotions(video_id)',
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_emotion_type ON comment_emotions(emotion_type)', 
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_language ON comment_emotions(language)',
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_confidence ON comment_emotions(confidence)',
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_published_at ON comment_emotions(published_at)',
            'CREATE INDEX IF NOT EXISTS idx_comment_emotions_composite ON comment_emotions(video_id, emotion_type, language)'
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
            
        # Video emotion summary table (8,800 records)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS video_emotion_summary (
                video_id TEXT PRIMARY KEY,
                dominant_emotion TEXT NOT NULL,
                emotion_diversity_score REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                positive_ratio REAL DEFAULT 0,
                negative_ratio REAL DEFAULT 0,
                neutral_ratio REAL DEFAULT 0,
                language_distribution TEXT,  -- JSON format
                country TEXT,
                competitor TEXT,
                high_engagement_emotions TEXT,  -- JSON format
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for video summaries
        conn.execute('CREATE INDEX IF NOT EXISTS idx_video_summary_country ON video_emotion_summary(country)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_video_summary_competitor ON video_emotion_summary(competitor)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_video_summary_dominant ON video_emotion_summary(dominant_emotion)')
        
        # Processing progress tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS emotion_processing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_start_time TIMESTAMP,
                batch_end_time TIMESTAMP,
                comments_processed INTEGER,
                successful_analyses INTEGER,
                batch_size INTEGER,
                processing_rate REAL,
                success_rate REAL,
                model_name TEXT,
                error_details TEXT
            )
        ''')
        
        # Global statistics view for dashboard
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_global_stats AS
            SELECT 
                COUNT(*) as total_comments_analyzed,
                SUM(CASE WHEN emotion_type = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN emotion_type = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN emotion_type = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT video_id) as videos_with_emotions,
                COUNT(DISTINCT language) as languages_detected
            FROM comment_emotions
        ''')
        
        # Country-level emotion breakdown view
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_by_country AS
            SELECT 
                ves.country,
                COUNT(ce.id) as total_comments,
                SUM(CASE WHEN ce.emotion_type = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN ce.emotion_type = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN ce.emotion_type = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                AVG(ce.confidence) as avg_confidence,
                COUNT(DISTINCT ce.video_id) as videos_analyzed
            FROM comment_emotions ce
            JOIN video_emotion_summary ves ON ce.video_id = ves.video_id
            WHERE ves.country IS NOT NULL
            GROUP BY ves.country
        ''')
        
        # Competitor emotion performance view
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_by_competitor AS
            SELECT 
                ves.competitor,
                ves.country,
                COUNT(ce.id) as total_comments,
                AVG(CASE WHEN ce.emotion_type = 'positive' THEN 1.0 ELSE 0.0 END) as positive_ratio,
                AVG(CASE WHEN ce.emotion_type = 'negative' THEN 1.0 ELSE 0.0 END) as negative_ratio,
                AVG(ce.confidence) as avg_confidence,
                COUNT(DISTINCT ce.video_id) as videos_analyzed
            FROM comment_emotions ce
            JOIN video_emotion_summary ves ON ce.video_id = ves.video_id
            WHERE ves.competitor IS NOT NULL
            GROUP BY ves.competitor, ves.country
        ''')
        
        # Temporal emotion trends view
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_trends AS
            SELECT 
                DATE(ce.published_at) as date,
                ce.emotion_type,
                ves.country,
                COUNT(*) as comment_count,
                AVG(ce.confidence) as avg_confidence
            FROM comment_emotions ce
            JOIN video_emotion_summary ves ON ce.video_id = ves.video_id
            WHERE ce.published_at IS NOT NULL
            GROUP BY DATE(ce.published_at), ce.emotion_type, ves.country
            ORDER BY date DESC
        ''')
        
        conn.commit()
        
        # Verify table creation
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"✅ Database setup completed!")
        logger.info(f"   Tables created: {', '.join(tables)}")
        logger.info(f"   Views created: {', '.join(views)}")
        logger.info(f"   Database optimized for 8.8M comment records")
        
        # Get database size
        try:
            cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            result = cursor.fetchone()
            db_size = result[0] if result else 0
            logger.info(f"   Current database size: {db_size / 1024 / 1024:.1f} MB")
        except Exception as e:
            logger.info(f"   Database size: Unable to calculate ({e})")
        
        return db_path

def verify_database_setup():
    """Verify database setup and show statistics"""
    db_path = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_massive.db'
    
    if not db_path.exists():
        print("❌ Database not found. Run setup_emotion_database() first.")
        return
    
    with sqlite3.connect(str(db_path)) as conn:
        # Check tables and indexes
        cursor = conn.execute("""
            SELECT name, type, sql FROM sqlite_master 
            WHERE type IN ('table', 'index', 'view') 
            ORDER BY type, name
        """)
        
        objects = cursor.fetchall()
        
        print("📊 Database Schema Verification:")
        print("=" * 50)
        
        for obj_name, obj_type, sql in objects:
            if obj_type == 'table':
                print(f"📋 TABLE: {obj_name}")
                # Get row count
                try:
                    count_cursor = conn.execute(f"SELECT COUNT(*) FROM {obj_name}")
                    count = count_cursor.fetchone()[0]
                    print(f"   Rows: {count:,}")
                except:
                    print("   Rows: N/A")
            elif obj_type == 'view':
                print(f"👁️  VIEW: {obj_name}")
            elif obj_type == 'index' and not obj_name.startswith('sqlite_'):
                print(f"🔍 INDEX: {obj_name}")
                
        print("=" * 50)

if __name__ == "__main__":
    # Setup database
    db_path = setup_emotion_database()
    
    # Verify setup
    verify_database_setup()
    
    print(f"\n🎯 Next steps:")
    print(f"1. Run comment scraping: python -m yt_channel_analyzer.sentiment_pipeline.comment_scraper")
    print(f"2. Run emotion analysis: python -m yt_channel_analyzer.sentiment_pipeline.emotion_analyzer")
    print(f"3. Check progress with: verify_database_setup()")