#!/usr/bin/env python3
"""
Emotion Analysis Pipeline Manager
Orchestrates the complete 8.8M comment sentiment analysis
Based on youtube_emotion_analysis_pipeline.md
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yt_channel_analyzer.sentiment_pipeline.setup_emotion_db import setup_emotion_database, verify_database_setup
from yt_channel_analyzer.sentiment_pipeline.comment_scraper import YouTubeCommentScraper
from yt_channel_analyzer.sentiment_pipeline.fast_comment_scraper import FastYouTubeScraper
from yt_channel_analyzer.sentiment_pipeline.emotion_analyzer import EmotionAnalyzer

def setup_logging(verbose=False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('emotion_pipeline.log')
        ]
    )

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'transformers',
        'torch', 
        'langdetect',
        'pandas',
        'googleapiclient'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True

def run_setup():
    """Setup emotion analysis database"""
    print("🏗️ Setting up emotion analysis database...")
    try:
        db_path = setup_emotion_database()
        print(f"✅ Database setup completed: {db_path}")
        verify_database_setup()
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def run_comment_scraping(api_key=None, batch_size=100, resume=False):
    """Run comment scraping for 8.8M comments"""
    print("🔍 Starting comment scraping pipeline...")
    
    if not api_key:
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("❌ YouTube API key not found. Set YOUTUBE_API_KEY environment variable.")
            return False
    
    try:
        scraper = YouTubeCommentScraper(api_key)
        
        if not resume:
            print("📊 Getting video list from database...")
            video_ids = scraper.get_all_video_ids()
            print(f"🎯 Found {len(video_ids)} videos to scrape")
        
        print(f"🚀 Starting scraping with batch size {batch_size}...")
        results = scraper.scrape_all_videos(batch_size=batch_size)
        
        print(f"✅ Scraping completed!")
        print(f"   Videos processed: {results['videos_processed']:,}")
        print(f"   Comments scraped: {results['comments_scraped']:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comment scraping failed: {e}")
        logging.error(f"Comment scraping error: {e}", exc_info=True)
        return False

def run_fast_comment_scraping(api_key=None, workers=5, resume=True):
    """Run optimized comment scraping for top 20 comments per video"""
    print("⚡ Starting FAST comment scraping pipeline...")
    
    if not api_key:
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("❌ YouTube API key not found. Set YOUTUBE_API_KEY environment variable.")
            return False
    
    try:
        scraper = FastYouTubeScraper(api_key)
        
        print(f"🚀 Fast scraping: top 20 comments per video with {workers} workers")
        print(f"📊 Target: 8,800 videos × 20 comments = 176,000 total comments")
        print(f"⚡ Estimated quota: 8,800 (out of 10,000 daily limit)")
        
        results = scraper.scrape_all_videos_fast(
            max_workers=workers,
            resume=resume
        )
        
        print(f"✅ Fast scraping completed!")
        print(f"   Videos processed: {results['videos_processed']:,}")
        print(f"   Successful: {results['successful_videos']:,}")
        print(f"   Comments scraped: {results['comments_scraped']:,}")
        print(f"   Quota used: {results['quota_used']:,}/10,000")
        print(f"   Processing time: {results['processing_time']/60:.1f} minutes")
        
        return True
        
    except Exception as e:
        print(f"❌ Fast scraping failed: {e}")
        logging.error(f"Fast scraping error: {e}", exc_info=True)
        return False

def run_emotion_analysis(batch_size=1000, max_workers=4):
    """Run emotion analysis on scraped comments"""
    print("🧠 Starting emotion analysis pipeline...")
    
    try:
        analyzer = EmotionAnalyzer()
        
        print(f"🤖 Emotion model loaded: {analyzer.model_name}")
        print(f"📊 Processing with batch size {batch_size}, {max_workers} workers")
        
        results = analyzer.process_all_comments(
            batch_size=batch_size,
            max_workers=max_workers
        )
        
        print(f"✅ Emotion analysis completed!")
        print(f"   Comments processed: {results['total_processed']:,}")
        print(f"   Successful analyses: {results['total_successful']:,}")
        print(f"   Success rate: {results['success_rate']*100:.1f}%")
        print(f"   Processing time: {results['processing_time']/3600:.1f} hours")
        
        # Generate video summaries
        print("📊 Generating video emotion summaries...")
        analyzer.generate_video_summaries()
        
        return True
        
    except Exception as e:
        print(f"❌ Emotion analysis failed: {e}")
        logging.error(f"Emotion analysis error: {e}", exc_info=True)
        return False

def get_pipeline_status():
    """Get current pipeline status"""
    print("📊 Pipeline Status Report")
    print("=" * 50)
    
    try:
        # Check database setup
        db_path = Path(__file__).parent / 'instance' / 'youtube_emotions_massive.db'
        if not db_path.exists():
            print("❌ Emotion database not found - run setup first")
            return
        
        verify_database_setup()
        
        # Check processing status
        from yt_channel_analyzer.sentiment_pipeline.emotion_analyzer import EmotionAnalyzer
        analyzer = EmotionAnalyzer()
        stats = analyzer.get_processing_stats()
        
        print(f"\n📈 Processing Statistics:")
        print(f"   Raw comments: {stats['raw_comments']['total']:,}")
        print(f"   Processed: {stats['raw_comments']['processed']:,}")
        print(f"   Pending: {stats['raw_comments']['pending']:,}")
        print(f"   Completion: {stats['raw_comments']['completion_rate']:.1f}%")
        
        if stats['emotions']:
            print(f"\n🎭 Emotion Distribution:")
            for emotion, data in stats['emotions'].items():
                print(f"   {emotion.capitalize()}: {data['count']:,} ({data['avg_confidence']:.2f} confidence)")
        
        if stats['languages']:
            print(f"\n🌍 Language Distribution:")
            for lang, count in stats['languages'].items():
                print(f"   {lang.upper()}: {count:,}")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def main():
    parser = argparse.ArgumentParser(description='Emotion Analysis Pipeline Manager')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--api-key', help='YouTube API key (or use YOUTUBE_API_KEY env var)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup emotion analysis database')
    
    # Scrape command  
    scrape_parser = subparsers.add_parser('scrape', help='Scrape YouTube comments')
    scrape_parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    scrape_parser.add_argument('--resume', action='store_true', help='Resume from last position')
    
    # Fast scrape command (NEW!)
    fast_scrape_parser = subparsers.add_parser('fast-scrape', help='Fast scrape: top 20 comments per video')
    fast_scrape_parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers')
    fast_scrape_parser.add_argument('--resume', action='store_true', help='Resume from last position')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze emotions from comments')
    analyze_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for emotion analysis')
    analyze_parser.add_argument('--workers', type=int, default=4, help='Number of worker threads')
    
    # Full pipeline command
    full_parser = subparsers.add_parser('full', help='Run complete pipeline (setup -> scrape -> analyze)')
    full_parser.add_argument('--scrape-batch', type=int, default=100, help='Scraping batch size')
    full_parser.add_argument('--analyze-batch', type=int, default=1000, help='Analysis batch size')
    full_parser.add_argument('--workers', type=int, default=4, help='Number of worker threads')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show pipeline status')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install required packages')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'install':
        print("📦 Installing required packages...")
        os.system('pip install -r requirements-sentiment.txt')
        return
    
    # Check requirements
    if not check_requirements():
        print("💡 Run 'python run_emotion_pipeline.py install' to install missing packages")
        return
    
    success = True
    
    if args.command == 'setup':
        success = run_setup()
        
    elif args.command == 'scrape':
        success = run_comment_scraping(
            api_key=args.api_key,
            batch_size=args.batch_size,
            resume=args.resume
        )
        
    elif args.command == 'fast-scrape':
        success = run_fast_comment_scraping(
            api_key=args.api_key,
            workers=args.workers,
            resume=args.resume
        )
        
    elif args.command == 'analyze':
        success = run_emotion_analysis(
            batch_size=args.batch_size,
            max_workers=args.workers
        )
        
    elif args.command == 'full':
        print("🚀 Running complete emotion analysis pipeline...")
        
        # Setup
        success = run_setup()
        if not success:
            return
        
        # Scrape
        success = run_comment_scraping(
            api_key=args.api_key,
            batch_size=args.scrape_batch
        )
        if not success:
            return
            
        # Analyze
        success = run_emotion_analysis(
            batch_size=args.analyze_batch,
            max_workers=args.workers
        )
        
    elif args.command == 'status':
        get_pipeline_status()
        return
    
    if success:
        print(f"\n🎉 Command '{args.command}' completed successfully!")
        print(f"💡 Run 'python run_emotion_pipeline.py status' to check progress")
    else:
        print(f"\n❌ Command '{args.command}' failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()