"""
Flask API for Emotion Analysis Dashboard
Serves data from 8.8M analyzed comments
Based on youtube_emotion_analysis_pipeline.md
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from functools import wraps
import time

from flask import Blueprint, jsonify, request

# Create blueprint for emotion API
emotion_api = Blueprint('emotion_api', __name__, url_prefix='/api/emotions')

# Database path
EMOTIONS_DB_PATH = Path(__file__).parent.parent.parent / 'instance' / 'youtube_emotions_massive.db'

def get_emotion_db_connection():
    """Get connection to emotion database"""
    return sqlite3.connect(str(EMOTIONS_DB_PATH))

def cache_response(duration_seconds=300):
    """Simple cache decorator for API responses"""
    def decorator(f):
        cache = {}
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if cached and not expired
            if cache_key in cache:
                cached_data, timestamp = cache[cache_key]
                if time.time() - timestamp < duration_seconds:
                    return cached_data
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

@emotion_api.route('/overview')
@cache_response(600)  # Cache for 10 minutes
def get_emotions_overview():
    """Get global emotion statistics from 8.8M comments"""
    try:
        with get_emotion_db_connection() as conn:
            # Get global stats using the view
            cursor = conn.execute('SELECT * FROM emotion_global_stats')
            stats = cursor.fetchone()
            
            if not stats:
                return jsonify({
                    'success': False,
                    'error': 'No emotion data available'
                })
            
            # Get top emotional videos
            cursor = conn.execute('''
                SELECT 
                    ves.video_id,
                    ves.competitor,
                    ves.country,
                    ves.dominant_emotion,
                    ves.total_comments,
                    ves.positive_ratio,
                    ves.avg_confidence
                FROM video_emotion_summary ves
                WHERE ves.total_comments >= 50
                ORDER BY ves.positive_ratio DESC, ves.total_comments DESC
                LIMIT 10
            ''')
            top_videos = cursor.fetchall()
            
            # Get language distribution
            cursor = conn.execute('''
                SELECT language, COUNT(*) as count
                FROM comment_emotions 
                GROUP BY language 
                ORDER BY count DESC
            ''')
            language_dist = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'total_comments': stats[0],
                    'positive_count': stats[1],
                    'negative_count': stats[2],
                    'neutral_count': stats[3],
                    'positive_percentage': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
                    'negative_percentage': (stats[2] / stats[0] * 100) if stats[0] > 0 else 0,
                    'neutral_percentage': (stats[3] / stats[0] * 100) if stats[0] > 0 else 0,
                    'avg_confidence': stats[4],
                    'videos_analyzed': stats[5],
                    'languages_detected': stats[6],
                    'top_emotional_videos': [
                        {
                            'video_id': video[0],
                            'competitor': video[1],
                            'country': video[2], 
                            'dominant_emotion': video[3],
                            'total_comments': video[4],
                            'positive_ratio': video[5],
                            'avg_confidence': video[6]
                        }
                        for video in top_videos
                    ],
                    'language_distribution': dict(language_dist)
                }
            })
            
    except Exception as e:
        logging.error(f"Error in emotions overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/country/<country>')
@cache_response(300)
def get_country_emotions(country):
    """Get emotion breakdown for specific country"""
    try:
        with get_emotion_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM emotion_by_country WHERE country = ?
            ''', (country,))
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': f'No emotion data for country: {country}'
                })
            
            # Get competitor breakdown for this country
            cursor = conn.execute('''
                SELECT 
                    competitor,
                    total_comments,
                    positive_ratio,
                    negative_ratio,
                    avg_confidence,
                    videos_analyzed
                FROM emotion_by_competitor 
                WHERE country = ?
                ORDER BY positive_ratio DESC
            ''', (country,))
            
            competitors = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'country': result[0],
                    'total_comments': result[1],
                    'positive_count': result[2],
                    'negative_count': result[3],
                    'neutral_count': result[4],
                    'positive_percentage': (result[2] / result[1] * 100) if result[1] > 0 else 0,
                    'negative_percentage': (result[3] / result[1] * 100) if result[1] > 0 else 0,
                    'neutral_percentage': (result[4] / result[1] * 100) if result[1] > 0 else 0,
                    'avg_confidence': result[5],
                    'videos_analyzed': result[6],
                    'competitors': [
                        {
                            'name': comp[0],
                            'total_comments': comp[1],
                            'positive_ratio': comp[2],
                            'negative_ratio': comp[3],
                            'avg_confidence': comp[4],
                            'videos_analyzed': comp[5]
                        }
                        for comp in competitors
                    ]
                }
            })
            
    except Exception as e:
        logging.error(f"Error in country emotions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/competitor/<competitor>')
@cache_response(300)
def get_competitor_emotions(competitor):
    """Get emotion profile for specific competitor"""
    try:
        with get_emotion_db_connection() as conn:
            # Get competitor stats across all countries
            cursor = conn.execute('''
                SELECT 
                    country,
                    total_comments,
                    positive_ratio,
                    negative_ratio,
                    avg_confidence,
                    videos_analyzed
                FROM emotion_by_competitor 
                WHERE competitor = ?
                ORDER BY total_comments DESC
            ''', (competitor,))
            
            countries = cursor.fetchall()
            
            if not countries:
                return jsonify({
                    'success': False,
                    'error': f'No emotion data for competitor: {competitor}'
                })
            
            # Calculate overall stats
            total_comments = sum(c[1] for c in countries)
            weighted_positive = sum(c[1] * c[2] for c in countries) / total_comments if total_comments > 0 else 0
            weighted_negative = sum(c[1] * c[3] for c in countries) / total_comments if total_comments > 0 else 0
            
            # Get top videos for this competitor
            cursor = conn.execute('''
                SELECT 
                    ves.video_id,
                    ves.country,
                    ves.dominant_emotion,
                    ves.total_comments,
                    ves.positive_ratio,
                    ves.avg_confidence
                FROM video_emotion_summary ves
                WHERE ves.competitor = ? AND ves.total_comments >= 20
                ORDER BY ves.positive_ratio DESC, ves.total_comments DESC
                LIMIT 10
            ''', (competitor,))
            
            top_videos = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'competitor': competitor,
                    'total_comments': total_comments,
                    'positive_ratio': weighted_positive,
                    'negative_ratio': weighted_negative,
                    'neutral_ratio': 1 - weighted_positive - weighted_negative,
                    'countries': [
                        {
                            'country': country[0],
                            'total_comments': country[1],
                            'positive_ratio': country[2],
                            'negative_ratio': country[3],
                            'avg_confidence': country[4],
                            'videos_analyzed': country[5]
                        }
                        for country in countries
                    ],
                    'top_videos': [
                        {
                            'video_id': video[0],
                            'country': video[1],
                            'dominant_emotion': video[2],
                            'total_comments': video[3],
                            'positive_ratio': video[4],
                            'avg_confidence': video[5]
                        }
                        for video in top_videos
                    ]
                }
            })
            
    except Exception as e:
        logging.error(f"Error in competitor emotions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/heatmap')
@cache_response(600)
def get_emotion_heatmap():
    """Get emotion heatmap data for countries vs emotions"""
    try:
        with get_emotion_db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    country,
                    SUM(CASE WHEN emotion_type = 'positive' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as positive_ratio,
                    SUM(CASE WHEN emotion_type = 'negative' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as negative_ratio,
                    SUM(CASE WHEN emotion_type = 'neutral' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as neutral_ratio,
                    COUNT(*) as total_comments
                FROM comment_emotions ce
                JOIN video_emotion_summary ves ON ce.video_id = ves.video_id
                WHERE ves.country IS NOT NULL
                GROUP BY country
            ''')
            
            results = cursor.fetchall()
            
            heatmap_data = []
            for row in results:
                country, pos_ratio, neg_ratio, neu_ratio, total = row
                heatmap_data.extend([
                    {'x': country, 'y': 'POSITIVE', 'v': pos_ratio},
                    {'x': country, 'y': 'NEGATIVE', 'v': neg_ratio},
                    {'x': country, 'y': 'NEUTRAL', 'v': neu_ratio}
                ])
            
            return jsonify({
                'success': True,
                'data': heatmap_data
            })
            
    except Exception as e:
        logging.error(f"Error in emotion heatmap: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/trends')
@cache_response(900)  # Cache for 15 minutes
def get_emotion_trends():
    """Get emotion trends over time"""
    try:
        # Get date range from query parameters
        days_back = request.args.get('days', 180, type=int)
        start_date = datetime.now() - timedelta(days=days_back)
        
        with get_emotion_db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    date,
                    emotion_type,
                    SUM(comment_count) as total_comments,
                    AVG(avg_confidence) as avg_confidence
                FROM emotion_trends 
                WHERE date >= ?
                GROUP BY date, emotion_type
                ORDER BY date DESC
                LIMIT 1000
            ''', (start_date.strftime('%Y-%m-%d'),))
            
            results = cursor.fetchall()
            
            # Group by date
            trends_by_date = {}
            for row in results:
                date, emotion, count, confidence = row
                if date not in trends_by_date:
                    trends_by_date[date] = {'positive': 0, 'negative': 0, 'neutral': 0}
                trends_by_date[date][emotion] = count
            
            # Convert to timeline format
            timeline_data = []
            for date in sorted(trends_by_date.keys(), reverse=True)[:30]:  # Last 30 days
                data = trends_by_date[date]
                total = sum(data.values())
                if total > 0:
                    timeline_data.append({
                        'date': date,
                        'positive_percentage': data['positive'] / total * 100,
                        'negative_percentage': data['negative'] / total * 100,
                        'neutral_percentage': data['neutral'] / total * 100,
                        'total_comments': total
                    })
            
            return jsonify({
                'success': True,
                'data': timeline_data
            })
            
    except Exception as e:
        logging.error(f"Error in emotion trends: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/processing-status')
def get_processing_status():
    """Get current processing status of emotion analysis"""
    try:
        with get_emotion_db_connection() as conn:
            # Check if raw comments table exists
            cursor = conn.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='comments_raw'
            ''')
            if not cursor.fetchone():
                return jsonify({
                    'success': True,
                    'status': 'not_started',
                    'message': 'Comment scraping not started'
                })
            
            # Get processing stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_raw,
                    SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed,
                    SUM(CASE WHEN processed = 0 THEN 1 ELSE 0 END) as pending
                FROM comments_raw
            ''')
            raw_stats = cursor.fetchone()
            
            cursor = conn.execute('SELECT COUNT(*) FROM comment_emotions')
            emotion_count = cursor.fetchone()[0]
            
            if raw_stats[0] == 0:
                status = 'not_started'
                completion_rate = 0
            elif raw_stats[2] == 0:
                status = 'completed'
                completion_rate = 100
            else:
                status = 'in_progress'
                completion_rate = (raw_stats[1] / raw_stats[0] * 100) if raw_stats[0] > 0 else 0
            
            return jsonify({
                'success': True,
                'status': status,
                'total_raw_comments': raw_stats[0],
                'processed_comments': raw_stats[1],
                'pending_comments': raw_stats[2],
                'emotion_analyses': emotion_count,
                'completion_rate': completion_rate,
                'target_comments': 8800000
            })
            
    except Exception as e:
        logging.error(f"Error getting processing status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@emotion_api.route('/export')
def export_emotion_data():
    """Export emotion analysis data"""
    try:
        with get_emotion_db_connection() as conn:
            # Get summary statistics
            cursor = conn.execute('SELECT * FROM emotion_global_stats')
            stats = cursor.fetchone()
            
            # Get country breakdown
            cursor = conn.execute('SELECT * FROM emotion_by_country')
            countries = cursor.fetchall()
            
            # Get competitor breakdown
            cursor = conn.execute('SELECT * FROM emotion_by_competitor')
            competitors = cursor.fetchall()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'global_stats': {
                    'total_comments': stats[0] if stats else 0,
                    'positive_count': stats[1] if stats else 0,
                    'negative_count': stats[2] if stats else 0,
                    'neutral_count': stats[3] if stats else 0,
                    'avg_confidence': stats[4] if stats else 0,
                    'videos_analyzed': stats[5] if stats else 0,
                    'languages_detected': stats[6] if stats else 0
                },
                'countries': [
                    {
                        'country': c[0],
                        'total_comments': c[1],
                        'positive_count': c[2],
                        'negative_count': c[3],
                        'neutral_count': c[4],
                        'avg_confidence': c[5],
                        'videos_analyzed': c[6]
                    }
                    for c in countries
                ],
                'competitors': [
                    {
                        'competitor': c[0],
                        'country': c[1],
                        'total_comments': c[2],
                        'positive_ratio': c[3],
                        'negative_ratio': c[4],
                        'avg_confidence': c[5],
                        'videos_analyzed': c[6]
                    }
                    for c in competitors
                ]
            }
            
            return jsonify({
                'success': True,
                'data': export_data
            })
            
    except Exception as e:
        logging.error(f"Error exporting emotion data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Error handler for the blueprint
@emotion_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@emotion_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500