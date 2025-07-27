"""
Flask API for Batch Processing Management
Handles batch comment scraping and emotion analysis
"""
import sqlite3
import json
import logging
import uuid
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

from flask import Blueprint, jsonify, request

# Create blueprint for batch API
batch_api = Blueprint('batch_api', __name__, url_prefix='/api/batch')

# Database paths
MAIN_DB_PATH = Path(__file__).parent.parent.parent / 'instance' / 'database.db'
FAST_DB_PATH = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_fast.db'

# Global batch tracking
active_batches = {}
batch_lock = threading.Lock()

def get_main_db_connection():
    """Get connection to main database"""
    return sqlite3.connect(str(MAIN_DB_PATH))

def get_fast_db_connection():
    """Get connection to fast scraping database"""
    return sqlite3.connect(str(FAST_DB_PATH))

@batch_api.route('/start-scraping', methods=['POST'])
def start_batch_scraping():
    """Start a new batch scraping job"""
    try:
        data = request.get_json()
        batch_size = data.get('batch_size', 100)
        
        # Validate batch size
        if batch_size == -1:
            batch_size = None  # All videos
            batch_label = "ALL"
        elif batch_size < 1 or batch_size > 10000:
            return jsonify({
                'success': False,
                'error': 'Invalid batch size. Must be between 1 and 10000, or -1 for all videos'
            }), 400
        else:
            batch_label = str(batch_size)
        
        # Check if another batch is already running
        with batch_lock:
            active_batch_ids = [bid for bid, batch_info in active_batches.items() 
                              if batch_info.get('status') in ['running', 'starting']]
            
            if active_batch_ids:
                return jsonify({
                    'success': False,
                    'error': f'Another batch is already running: {active_batch_ids[0]}'
                }), 409
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())[:8]
        
        # Initialize batch tracking
        with batch_lock:
            active_batches[batch_id] = {
                'batch_id': batch_id,
                'batch_size': batch_size,
                'batch_label': batch_label,
                'status': 'starting',
                'start_time': datetime.now(),
                'processed_videos': 0,
                'total_videos': 0,
                'comments_scraped': 0,
                'quota_used': 0,
                'error': None
            }
        
        # Start the batch in a separate thread
        thread = threading.Thread(
            target=run_batch_scraping, 
            args=(batch_id, batch_size),
            daemon=True
        )
        thread.start()
        
        logging.info(f"✅ Batch {batch_id} started with size {batch_label}")
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'batch_size': batch_label,
            'message': f'Batch scraping started for {batch_label} videos'
        })
        
    except Exception as e:
        logging.error(f"Error starting batch scraping: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_api.route('/progress/<batch_id>')
def get_batch_progress(batch_id):
    """Get progress of a specific batch"""
    try:
        with batch_lock:
            if batch_id not in active_batches:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }), 404
            
            batch_info = active_batches[batch_id].copy()
        
        # Add calculated fields
        elapsed_time = (datetime.now() - batch_info['start_time']).total_seconds()
        batch_info['elapsed_time'] = elapsed_time
        
        if batch_info['processed_videos'] > 0 and elapsed_time > 0:
            batch_info['processing_rate'] = batch_info['processed_videos'] / elapsed_time
        else:
            batch_info['processing_rate'] = 0
        
        # Remove datetime object for JSON serialization
        batch_info['start_time'] = batch_info['start_time'].isoformat()
        
        return jsonify({
            'success': True,
            'data': batch_info
        })
        
    except Exception as e:
        logging.error(f"Error getting batch progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_api.route('/stop-scraping/<batch_id>', methods=['POST'])
def stop_batch_scraping(batch_id):
    """Stop a running batch"""
    try:
        with batch_lock:
            if batch_id not in active_batches:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }), 404
            
            batch_info = active_batches[batch_id]
            if batch_info['status'] not in ['running', 'starting']:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} is not running (status: {batch_info["status"]})'
                }), 400
            
            # Mark batch as stopped
            active_batches[batch_id]['status'] = 'stopped'
            active_batches[batch_id]['stop_time'] = datetime.now()
        
        logging.info(f"🛑 Batch {batch_id} stopped by user request")
        
        return jsonify({
            'success': True,
            'message': f'Batch {batch_id} stopped successfully'
        })
        
    except Exception as e:
        logging.error(f"Error stopping batch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_api.route('/list')
def list_batches():
    """List all batches (active and recent)"""
    try:
        with batch_lock:
            batches = []
            for batch_id, batch_info in active_batches.items():
                batch_copy = batch_info.copy()
                batch_copy['start_time'] = batch_copy['start_time'].isoformat()
                if 'stop_time' in batch_copy:
                    batch_copy['stop_time'] = batch_copy['stop_time'].isoformat()
                batches.append(batch_copy)
        
        return jsonify({
            'success': True,
            'batches': batches
        })
        
    except Exception as e:
        logging.error(f"Error listing batches: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_batch_scraping(batch_id: str, batch_size: Optional[int]):
    """Run the actual batch scraping process"""
    try:
        logging.info(f"🚀 Starting batch scraping: {batch_id}")
        
        # Import scraper here to avoid circular imports
        from yt_channel_analyzer.sentiment_pipeline.fast_comment_scraper import FastYouTubeScraper
        
        # Initialize scraper
        api_key = get_youtube_api_key()
        if not api_key:
            with batch_lock:
                active_batches[batch_id]['status'] = 'failed'
                active_batches[batch_id]['error'] = 'YouTube API key not found'
            return
        
        scraper = FastYouTubeScraper(api_key)
        
        # Get video list
        all_video_ids = scraper.get_all_video_ids()
        
        if batch_size:
            video_ids = all_video_ids[:batch_size]
        else:
            video_ids = all_video_ids
        
        total_videos = len(video_ids)
        
        # Update batch info
        with batch_lock:
            active_batches[batch_id]['status'] = 'running'
            active_batches[batch_id]['total_videos'] = total_videos
        
        logging.info(f"📊 Batch {batch_id}: Processing {total_videos} videos")
        
        # Process videos
        processed_count = 0
        comments_count = 0
        quota_used = 0
        
        for i, video_id in enumerate(video_ids):
            # Check if batch was stopped
            with batch_lock:
                if active_batches[batch_id]['status'] == 'stopped':
                    logging.info(f"🛑 Batch {batch_id} stopped at video {i+1}/{total_videos}")
                    return
            
            # Scrape comments for this video
            try:
                result = scraper.get_top_20_comments(video_id)
                scraper.save_video_comments(result)
                
                processed_count += 1
                comments_count += len(result.get('comments', []))
                quota_used += result.get('quota_used', 1)
                
                # Update progress every 10 videos or at the end
                if processed_count % 10 == 0 or processed_count == total_videos:
                    with batch_lock:
                        active_batches[batch_id]['processed_videos'] = processed_count
                        active_batches[batch_id]['comments_scraped'] = comments_count
                        active_batches[batch_id]['quota_used'] = quota_used
                
                # Small delay to be respectful to API
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"❌ Error processing video {video_id}: {e}")
                processed_count += 1  # Count as processed even if failed
        
        # Mark batch as completed
        with batch_lock:
            active_batches[batch_id]['status'] = 'completed'
            active_batches[batch_id]['processed_videos'] = processed_count
            active_batches[batch_id]['comments_scraped'] = comments_count
            active_batches[batch_id]['quota_used'] = quota_used
            active_batches[batch_id]['end_time'] = datetime.now()
        
        logging.info(f"✅ Batch {batch_id} completed: {processed_count} videos, {comments_count} comments")
        
    except Exception as e:
        logging.error(f"❌ Batch {batch_id} failed: {e}")
        with batch_lock:
            active_batches[batch_id]['status'] = 'failed'
            active_batches[batch_id]['error'] = str(e)

def get_youtube_api_key():
    """Get YouTube API key from database"""
    try:
        with get_main_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM app_config WHERE key = "youtube_api_key"')
            result = cursor.fetchone()
            if result and result[0]:
                api_key = result[0].strip()
                # Clean up any log messages that might be in the key
                if '\n' in api_key:
                    api_key = api_key.split('\n')[0].strip()
                return api_key
        return None
    except Exception as e:
        logging.error(f"Error getting API key: {e}")
        return None

# Error handlers
@batch_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Batch endpoint not found'
    }), 404

@batch_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500