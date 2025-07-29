"""
Brand Metrics Service for Center Parcs channels analysis.
Identical structure to Country Metrics but for individual competitors/channels.
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sqlite3
import json
import os


def load_settings():
    """Load settings from config/settings.json"""
    try:
        settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json')
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'paid_threshold': 10000}  # Default fallback

class BrandMetricsService:
    """Service for calculating brand-level metrics (identical to country metrics but per competitor)."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = None):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        # Load from settings if not provided
        if paid_threshold is None:
            settings = load_settings()
            paid_threshold = settings.get('paid_threshold', 10000)
        self.paid_threshold = paid_threshold
        print(f"[BRAND_METRICS] Using paid_threshold: {self.paid_threshold}")  # Debug log
    
    def get_center_parcs_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get all Center Parcs channels organized by region."""
        self.cursor.execute("""
            SELECT id, name, country 
            FROM concurrent 
            WHERE name LIKE '%Center Parcs%' OR name LIKE '%center parcs%'
            ORDER BY country, name
        """)
        
        channels = {}
        for row in self.cursor.fetchall():
            competitor_id, name, country = row
            # Map to friendly names
            if country == 'Germany':
                key = 'Center Parcs Ferien Parks'
            elif country == 'France':
                key = 'Center Parcs France'
            elif country == 'Netherlands':
                key = 'Center Parcs NL-BE'
            elif country == 'United Kingdom':
                key = 'Center Parcs UK'
            else:
                key = f'Center Parcs {country}'
                
            channels[key] = {
                'competitor_id': competitor_id,
                'name': name,
                'country': country
            }
        
        return channels
    
    def calculate_brand_metrics(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate all metrics for a specific Center Parcs channel (same as country metrics)."""
        try:
            # 1. Video Length Analysis
            video_length = self._calculate_video_length_metrics(competitor_id)
            
            # 2. Video Frequency Analysis  
            video_frequency = self._calculate_video_frequency_metrics(competitor_id)
            
            # 3. Most Liked Topics Analysis
            most_liked_topics = self._calculate_most_liked_topics(competitor_id)
            
            # 4. Organic vs Paid Distribution
            organic_vs_paid = self._calculate_organic_vs_paid_distribution(competitor_id)
            
            # 5. Hub/Help/Hero Distribution
            hub_help_hero = self._calculate_hub_help_hero_distribution(competitor_id)
            
            # 6. Thumbnail Consistency
            thumbnail_consistency = self._calculate_thumbnail_consistency(competitor_id)
            
            # 7. Tone of Voice Analysis
            tone_of_voice = self._analyze_tone_of_voice(competitor_id)
            
            # 8. Shorts vs Regular Distribution
            shorts_distribution = self._calculate_shorts_distribution(video_length)
            
            return {
                'video_length': video_length,
                'video_frequency': video_frequency,
                'most_liked_topics': most_liked_topics,
                'organic_vs_paid': organic_vs_paid,
                'hub_help_hero': hub_help_hero,
                'thumbnail_consistency': thumbnail_consistency,
                'tone_of_voice': tone_of_voice,
                'shorts_distribution': shorts_distribution,
                'generated_at': datetime.now().isoformat(),
                'total_videos': video_length['total_videos']
            }
            
        except Exception as e:
            print(f"[BRAND_METRICS] Error calculating metrics for competitor {competitor_id}: {e}")
            return self._empty_brand_metrics()
    
    def _calculate_video_length_metrics(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate video length statistics for a competitor."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                AVG(v.duration_seconds / 60.0) as avg_duration_minutes,
                MIN(v.duration_seconds / 60.0) as min_duration_minutes,
                MAX(v.duration_seconds / 60.0) as max_duration_minutes,
                COUNT(CASE WHEN v.duration_seconds <= 60 THEN 1 END) as shorts_count
            FROM video v
            WHERE v.concurrent_id = ? AND v.duration_seconds IS NOT NULL AND v.duration_seconds > 0
        """, (competitor_id,))
        
        video_length_data = self.cursor.fetchone()
        
        if not video_length_data or not video_length_data[0]:
            return {
                'total_videos': 0,
                'avg_duration_minutes': 0,
                'min_duration_minutes': 0,
                'max_duration_minutes': 0,
                'shorts_count': 0,
                'shorts_percentage': 0
            }
        
        return {
            'total_videos': video_length_data[0],
            'avg_duration_minutes': round(video_length_data[1], 1) if video_length_data[1] else 0,
            'min_duration_minutes': round(video_length_data[2], 1) if video_length_data[2] else 0,
            'max_duration_minutes': round(video_length_data[3], 1) if video_length_data[3] else 0,
            'shorts_count': video_length_data[4],
            'shorts_percentage': round((video_length_data[4] / video_length_data[0] * 100), 1) if video_length_data[0] > 0 else 0
        }
    
    def _calculate_video_frequency_metrics(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate video frequency statistics for a competitor."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                MIN(DATE(COALESCE(v.youtube_published_at, v.published_at))) as first_video_date,
                MAX(DATE(COALESCE(v.youtube_published_at, v.published_at))) as last_video_date,
                COUNT(v.youtube_published_at) as youtube_dates_count
            FROM video v
            WHERE v.concurrent_id = ? 
              AND (v.youtube_published_at IS NOT NULL OR v.published_at IS NOT NULL)
        """, (competitor_id,))
        
        freq_data = self.cursor.fetchone()
        
        if not freq_data or not freq_data[0]:
            return {
                'total_videos': 0,
                'videos_per_week': 0,
                'days_active': 0,
                'consistency_score': 0
            }
        
        total_videos, first_date, last_date = freq_data[:3]
        youtube_dates_count = freq_data[3] if len(freq_data) > 3 else 0

        # If no authentic YouTube dates and dates seem suspicious, don't calculate
        if youtube_dates_count == 0 and first_date == last_date:
            print(f"[BRAND_METRICS] ⚠️ {competitor_id}: Dates suspectes détectées - toutes identiques")
            return {
                'total_videos': total_videos,
                'videos_per_week': 0,  # Can't calculate reliably
                'days_active': 0,
                'consistency_score': 0
            }
        
        if first_date and last_date:
            from datetime import datetime
            # Handle both date formats (with or without time)
            try:
                # Try parsing as date only first
                first_dt = datetime.strptime(first_date, '%Y-%m-%d')
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
            except ValueError:
                # Try with full datetime format
                first_dt = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
            days_active = (last_dt - first_dt).days + 1
            videos_per_week = (total_videos * 7) / days_active if days_active > 0 else 0
            
            # Safeguard against unrealistic frequencies (likely bad date data)
            # If more than 50 videos per week, assume dates are wrong and estimate
            if videos_per_week > 50:
                print(f"[BRAND_METRICS] ⚠️ Fréquence irréaliste détectée: {videos_per_week:.1f}/sem pour {total_videos} vidéos")
                # Estimate based on typical YouTube channel activity (2-5 years, 1-3 videos/week)
                estimated_months = max(12, total_videos / 4)  # Assume ~4 videos per month minimum
                estimated_days = estimated_months * 30.5
                videos_per_week = (total_videos * 7) / estimated_days
                days_active = int(estimated_days)
                print(f"[BRAND_METRICS] 🔧 Fréquence corrigée: {videos_per_week:.1f}/sem sur {days_active} jours estimés")
        else:
            days_active = 0
            videos_per_week = 0
        
        return {
            'total_videos': total_videos,
            'videos_per_week': round(videos_per_week, 1),
            'days_active': days_active,
            'consistency_score': min(10, videos_per_week * 2)  # Simple consistency score
        }
    
    def _calculate_most_liked_topics(self, competitor_id: int) -> List[Dict[str, Any]]:
        """Calculate TOP 5 individual videos by engagement (likes + comments) for a competitor."""
        self.cursor.execute("""
            SELECT 
                v.title as topic,
                COALESCE(v.like_count, 0) as likes,
                COALESCE(v.comment_count, 0) as comments,
                (COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) as engagement_score
            FROM video v
            WHERE v.concurrent_id = ? 
            AND (v.like_count IS NOT NULL OR v.comment_count IS NOT NULL)
            AND (COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) > 0
            ORDER BY engagement_score DESC
            LIMIT 5
        """, (competitor_id,))
        
        topics = []
        for row in self.cursor.fetchall():
            title, likes, comments, engagement = row
            topics.append({
                'topic': title,
                'likes': int(likes),
                'comments': int(comments),
                'engagement_score': int(engagement)
            })
        
        return topics
    
    def _calculate_organic_vs_paid_distribution(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate organic vs paid distribution for a competitor."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.view_count <= ? THEN 1 END) as organic_count,
                COUNT(CASE WHEN v.view_count > ? THEN 1 END) as paid_count,
                COUNT(*) as total_count
            FROM video v
            WHERE v.concurrent_id = ? AND v.view_count IS NOT NULL
        """, (self.paid_threshold, self.paid_threshold, competitor_id))
        
        dist_data = self.cursor.fetchone()
        
        if not dist_data or not dist_data[2]:
            return {
                'organic_count': 0,
                'paid_count': 0,
                'organic_percentage': 0,
                'paid_percentage': 0
            }
        
        organic_count, paid_count, total_count = dist_data
        
        return {
            'organic_count': organic_count,
            'paid_count': paid_count,
            'organic_percentage': round((organic_count / total_count * 100), 1),
            'paid_percentage': round((paid_count / total_count * 100), 1)
        }
    
    def _calculate_hub_help_hero_distribution(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate Hub/Help/Hero distribution for a competitor (categories already propagated to videos)."""
        # Use video categories directly (already propagated from manual playlist classification)
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN v.category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN v.category = 'help' THEN 1 END) as help_count,
                COUNT(CASE WHEN v.category IS NOT NULL THEN 1 END) as categorized_videos,
                COUNT(*) as total_videos
            FROM video v
            WHERE v.concurrent_id = ?
        """, (competitor_id,))
        
        cat_data = self.cursor.fetchone()
        
        if not cat_data:
            return {
                'hero_count': 0, 'hub_count': 0, 'help_count': 0,
                'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0,
                'uncategorized_count': 0, 'total_videos': 0, 'categorized_videos': 0
            }
        
        hero_count, hub_count, help_count, categorized_videos, total_videos = cat_data
        uncategorized_count = total_videos - categorized_videos
        
        # Vérifier s'il y a des playlists pour ce concurrent
        self.cursor.execute("SELECT COUNT(*) FROM playlist WHERE concurrent_id = ?", (competitor_id,))
        playlist_count = self.cursor.fetchone()[0]
        
        # Log classification status (preserve human work visibility)
        if categorized_videos > 0:
            print(f"[BRAND_METRICS] ✅ HHH: {categorized_videos}/{total_videos} vidéos catégorisées (HUMAN CLASSIFICATION PRESERVED)")
            hero_percentage = round((hero_count / categorized_videos * 100), 1)
            hub_percentage = round((hub_count / categorized_videos * 100), 1)
            help_percentage = round((help_count / categorized_videos * 100), 1)
        else:
            if playlist_count == 0:
                print(f"[BRAND_METRICS] ⚠️ HHH: Concurrent {competitor_id} n'a AUCUNE playlist - Import playlists requis")
            else:
                print(f"[BRAND_METRICS] ⚠️ HHH: {total_videos} vidéos NON catégorisées pour concurrent {competitor_id} - CLASSIFICATION MANUELLE REQUISE")
            hero_percentage = hub_percentage = help_percentage = 0
        
        return {
            'hero_count': hero_count,
            'hub_count': hub_count,
            'help_count': help_count,
            'hero_percentage': hero_percentage,
            'hub_percentage': hub_percentage,
            'help_percentage': help_percentage,
            'uncategorized_count': uncategorized_count,
            'total_videos': total_videos,
            'categorized_videos': categorized_videos
        }
    
    def _calculate_thumbnail_consistency(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate thumbnail consistency for a competitor."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN v.thumbnail_url IS NOT NULL THEN 1 END) as with_thumbnails,
                AVG(CASE WHEN v.beauty_score IS NOT NULL THEN v.beauty_score ELSE 5 END) as avg_beauty_score
            FROM video v
            WHERE v.concurrent_id = ?
        """, (competitor_id,))
        
        thumb_data = self.cursor.fetchone()
        
        if not thumb_data or not thumb_data[0]:
            return {
                'total_videos': 0,
                'with_thumbnails': 0,
                'consistency_score': 0
            }
        
        total_videos, with_thumbnails, avg_beauty_score = thumb_data
        consistency_score = avg_beauty_score if avg_beauty_score else 5
        
        return {
            'total_videos': total_videos,
            'with_thumbnails': with_thumbnails,
            'consistency_score': round(consistency_score, 1)
        }
    
    def _analyze_tone_of_voice(self, competitor_id: int) -> Dict[str, Any]:
        """Analyze tone of voice for a competitor."""
        self.cursor.execute("""
            SELECT 
                v.title,
                v.description,
                LENGTH(v.title) as title_length
            FROM video v
            WHERE v.concurrent_id = ? AND v.title IS NOT NULL
            LIMIT 100
        """, (competitor_id,))
        
        videos = self.cursor.fetchall()
        
        if not videos:
            return {
                'emotional_words': 0,
                'action_words': 0,
                'avg_title_length': 0,
                'top_keywords': [],
                'dominant_tone': 'Family'
            }
        
        # Simple analysis
        total_title_length = sum(row[2] for row in videos if row[2])
        avg_title_length = total_title_length / len(videos) if videos else 0
        
        # Count emotional/action words (simplified)
        emotional_words = sum(1 for row in videos if any(word in (row[0] or '').lower() 
                             for word in ['amazing', 'beautiful', 'fun', 'exciting', 'love']))
        action_words = sum(1 for row in videos if any(word in (row[0] or '').lower() 
                          for word in ['discover', 'explore', 'visit', 'experience', 'enjoy']))
        
        return {
            'emotional_words': emotional_words,
            'action_words': action_words,
            'avg_title_length': round(avg_title_length, 1),
            'top_keywords': ['center parcs', 'holiday', 'family'],  # Simplified
            'dominant_tone': 'Family'
        }
    
    def _calculate_shorts_distribution(self, video_length_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate shorts vs regular video distribution."""
        total_videos = video_length_metrics.get('total_videos', 0)
        shorts_count = video_length_metrics.get('shorts_count', 0)
        
        if total_videos == 0:
            return {
                'total_videos': 0,
                'shorts_count': 0,
                'regular_count': 0,
                'shorts_percentage': 0.0,
                'regular_percentage': 0.0
            }
        
        regular_count = total_videos - shorts_count
        shorts_percentage = round((shorts_count / total_videos) * 100, 1)
        regular_percentage = round((regular_count / total_videos) * 100, 1)
        
        return {
            'total_videos': total_videos,
            'shorts_count': shorts_count,
            'regular_count': regular_count,
            'shorts_percentage': shorts_percentage,
            'regular_percentage': regular_percentage
        }
    
    def _empty_brand_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure when analysis fails."""
        return {
            'video_length': {
                'total_videos': 0, 'avg_duration_minutes': 0, 'min_duration_minutes': 0, 
                'max_duration_minutes': 0, 'shorts_count': 0, 'shorts_percentage': 0
            },
            'video_frequency': {'total_videos': 0, 'videos_per_week': 0, 'days_active': 0, 'consistency_score': 0},
            'most_liked_topics': [],
            'organic_vs_paid': {'organic_count': 0, 'paid_count': 0, 'organic_percentage': 0, 'paid_percentage': 0},
            'hub_help_hero': {
                'hero_count': 0, 'hub_count': 0, 'help_count': 0,
                'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0
            },
            'thumbnail_consistency': {'total_videos': 0, 'with_thumbnails': 0, 'consistency_score': 0},
            'tone_of_voice': {
                'emotional_words': 0, 'action_words': 0, 'avg_title_length': 0, 
                'top_keywords': [], 'dominant_tone': 'Family'
            },
            'shorts_distribution': {
                'total_videos': 0, 'shorts_count': 0, 'regular_count': 0,
                'shorts_percentage': 0.0, 'regular_percentage': 0.0
            },
            'generated_at': datetime.now().isoformat(),
            'total_videos': 0
        }