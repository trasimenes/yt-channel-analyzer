"""
Service layer for country metrics analysis (7 key metrics).
Extracted from monolithic app.py calculate_country_7_metrics() function (complexity 58 -> <10).
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sqlite3


class VideoLengthAnalysisService:
    """Handles video length analysis for a country."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_video_length_metrics(self, country: str) -> Dict[str, Any]:
        """Calculate video length statistics for a country."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                AVG(v.duration_seconds / 60.0) as avg_duration_minutes,
                MIN(v.duration_seconds / 60.0) as min_duration_minutes,
                MAX(v.duration_seconds / 60.0) as max_duration_minutes,
                COUNT(CASE WHEN v.duration_seconds <= 60 THEN 1 END) as shorts_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.duration_seconds IS NOT NULL AND v.duration_seconds > 0
        """, (country,))
        video_length_data = self.cursor.fetchone()
        
        if not video_length_data or not video_length_data[0]:
            return self._empty_video_length_metrics()
        
        return {
            'total_videos': video_length_data[0],
            'avg_duration_minutes': round(video_length_data[1], 1) if video_length_data[1] else 0,
            'min_duration_minutes': round(video_length_data[2], 1) if video_length_data[2] else 0,
            'max_duration_minutes': round(video_length_data[3], 1) if video_length_data[3] else 0,
            'shorts_count': video_length_data[4],
            'shorts_percentage': round((video_length_data[4] / video_length_data[0] * 100), 1) if video_length_data[0] > 0 else 0
        }
    
    def _empty_video_length_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'total_videos': 0,
            'avg_duration_minutes': 0,
            'min_duration_minutes': 0,
            'max_duration_minutes': 0,
            'shorts_count': 0,
            'shorts_percentage': 0
        }


class VideoFrequencyAnalysisService:
    """Handles video frequency analysis for a country."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_video_frequency_metrics(self, country: str) -> Dict[str, Any]:
        """Calculate video frequency statistics for a country."""
        self.cursor.execute("""
            SELECT 
                COUNT(DISTINCT v.id) as total_videos,
                (julianday('now') - julianday(MIN(v.youtube_published_at))) / 7.0 as weeks_active,
                COUNT(DISTINCT DATE(v.youtube_published_at)) as days_active
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.youtube_published_at IS NOT NULL
            AND DATE(v.youtube_published_at) >= '2020-01-01'
        """, (country,))
        freq_data = self.cursor.fetchone()
        
        if not freq_data or not freq_data[0]:
            return self._empty_frequency_metrics()
        
        videos_per_week = 0
        consistency_score = 0
        
        if freq_data[1] and freq_data[1] > 0:
            videos_per_week = round(freq_data[0] / max(freq_data[1], 1), 1)
            consistency_score = min(100, round((freq_data[2] / max(freq_data[1] * 7, 1)) * 100, 1))
        
        return {
            'total_videos': freq_data[0],
            'videos_per_week': videos_per_week,
            'days_active': freq_data[2] if freq_data[2] else 0,
            'consistency_score': consistency_score
        }
    
    def _empty_frequency_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'total_videos': 0,
            'videos_per_week': 0,
            'days_active': 0,
            'consistency_score': 0
        }


class TopicAnalysisService:
    """Handles most liked topics analysis for a country."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_most_liked_topics(self, country: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Calculate most liked topics by engagement rate."""
        self.cursor.execute("""
            SELECT 
                v.title,
                v.like_count,
                v.view_count,
                v.comment_count,
                v.category,
                (CAST(v.like_count + v.comment_count AS FLOAT) / NULLIF(v.view_count, 0) * 100) as engagement_rate
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.view_count > 100
            ORDER BY engagement_rate DESC, v.like_count DESC
            LIMIT ?
        """, (country, limit))
        liked_topics_data = self.cursor.fetchall()
        
        most_liked_topics = []
        for topic in liked_topics_data:
            title = topic[0][:50] + '...' if len(topic[0]) > 50 else topic[0]
            most_liked_topics.append({
                'title': title,
                'like_ratio': round(topic[5], 1) if topic[5] else 0,
                'views': topic[2],
                'category': topic[4] or 'All'
            })
        
        return most_liked_topics


class ContentDistributionService:
    """Handles organic vs paid content distribution analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = 100000):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.paid_threshold = paid_threshold
    
    def calculate_organic_vs_paid_distribution(self, country: str) -> Dict[str, Any]:
        """Calculate organic vs paid content distribution."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.view_count < ? THEN 1 END) as organic_count,
                COUNT(CASE WHEN v.view_count >= ? THEN 1 END) as paid_count,
                AVG(CASE WHEN v.view_count < ? THEN v.view_count END) as organic_avg_views,
                AVG(CASE WHEN v.view_count >= ? THEN v.view_count END) as paid_avg_views
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.view_count > 0
        """, (self.paid_threshold, self.paid_threshold, self.paid_threshold, self.paid_threshold, country))
        organic_data = self.cursor.fetchone()
        
        if not organic_data:
            return self._empty_distribution_metrics()
        
        organic_count = organic_data[0] or 0
        paid_count = organic_data[1] or 0
        total_content = organic_count + paid_count
        
        return {
            'organic_count': organic_count,
            'paid_count': paid_count,
            'organic_percentage': round((organic_count / max(total_content, 1)) * 100, 1),
            'paid_percentage': round((paid_count / max(total_content, 1)) * 100, 1),
            'organic_avg_views': int(organic_data[2]) if organic_data[2] else 0
        }
    
    def _empty_distribution_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'organic_count': 0,
            'paid_count': 0,
            'organic_percentage': 0,
            'paid_percentage': 0,
            'organic_avg_views': 0
        }


class CategoryDistributionService:
    """Handles Hub/Help/Hero category distribution analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_hub_help_hero_distribution(self, country: str) -> Dict[str, Any]:
        """Calculate Hub/Help/Hero distribution."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN v.category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN v.category = 'help' THEN 1 END) as help_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.category IS NOT NULL
        """, (country,))
        hhh_data = self.cursor.fetchone()
        
        if not hhh_data:
            return self._empty_category_metrics()
        
        hero_count = hhh_data[0] or 0
        hub_count = hhh_data[1] or 0
        help_count = hhh_data[2] or 0
        total_categorized = hero_count + hub_count + help_count
        
        return {
            'hero_count': hero_count,
            'hub_count': hub_count,
            'help_count': help_count,
            'hero_percentage': round((hero_count / max(total_categorized, 1)) * 100, 1),
            'hub_percentage': round((hub_count / max(total_categorized, 1)) * 100, 1),
            'help_percentage': round((help_count / max(total_categorized, 1)) * 100, 1)
        }
    
    def _empty_category_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'hero_count': 0,
            'hub_count': 0,
            'help_count': 0,
            'hero_percentage': 0,
            'hub_percentage': 0,
            'help_percentage': 0
        }


class ThumbnailConsistencyService:
    """Handles thumbnail consistency analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_thumbnail_consistency(self, country: str) -> Dict[str, Any]:
        """Calculate thumbnail consistency metrics."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN v.thumbnail_url IS NOT NULL AND v.thumbnail_url != '' THEN 1 END) as with_thumbnails
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ?
        """, (country,))
        thumb_data = self.cursor.fetchone()
        
        if not thumb_data or not thumb_data[0]:
            return self._empty_thumbnail_metrics()
        
        total_videos = thumb_data[0]
        with_thumbnails = thumb_data[1] or 0
        consistency_score = round((with_thumbnails / max(total_videos, 1)) * 10, 1)
        
        return {
            'total_videos': total_videos,
            'with_thumbnails': with_thumbnails,
            'consistency_score': consistency_score
        }
    
    def _empty_thumbnail_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'total_videos': 0,
            'with_thumbnails': 0,
            'consistency_score': 0
        }


class ToneOfVoiceService:
    """Handles tone of voice analysis based on video titles."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.emotional_words = ['amazing', 'incredible', 'beautiful', 'fantastic', 'wonderful', 'perfect', 'love', 'best']
        self.action_words = ['discover', 'explore', 'visit', 'experience', 'enjoy', 'learn', 'watch', 'see']
    
    def analyze_tone_of_voice(self, country: str, sample_limit: int = 100) -> Dict[str, Any]:
        """Analyze tone of voice from video titles."""
        self.cursor.execute("""
            SELECT 
                v.title,
                LENGTH(v.title) as title_length
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ? AND v.title IS NOT NULL
            LIMIT ?
        """, (country, sample_limit))
        tone_data = self.cursor.fetchall()
        
        if not tone_data:
            return self._empty_tone_metrics()
        
        return self._analyze_titles(tone_data)
    
    def _analyze_titles(self, tone_data: List[Tuple]) -> Dict[str, Any]:
        """Analyze titles for emotional/action words and keywords."""
        emotional_count = 0
        action_count = 0
        total_length = 0
        top_words = {}
        
        for title_data in tone_data:
            title = title_data[0].lower()
            total_length += title_data[1]
            
            # Count emotional words
            for word in self.emotional_words:
                if word in title:
                    emotional_count += 1
            
            # Count action words
            for word in self.action_words:
                if word in title:
                    action_count += 1
            
            # Extract common words for keyword analysis
            words = title.split()
            for word in words:
                if len(word) > 3:  # Only words longer than 3 chars
                    top_words[word] = top_words.get(word, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(top_words.items(), key=lambda x: x[1], reverse=True)[:5]
        top_keywords = [word[0] for word in top_keywords]
        
        return {
            'emotional_words': emotional_count,
            'action_words': action_count,
            'avg_title_length': round(total_length / max(len(tone_data), 1), 1),
            'top_keywords': top_keywords,
            'dominant_tone': 'Family' if emotional_count > action_count else 'Adventure'
        }
    
    def _empty_tone_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'emotional_words': 0,
            'action_words': 0,
            'avg_title_length': 0,
            'top_keywords': [],
            'dominant_tone': 'Neutral'
        }


class CountryMetricsService:
    """Main service orchestrating country-level 7 key metrics analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = 100000):
        self.conn = db_connection
        self.video_length_service = VideoLengthAnalysisService(db_connection)
        self.frequency_service = VideoFrequencyAnalysisService(db_connection)
        self.topic_service = TopicAnalysisService(db_connection)
        self.distribution_service = ContentDistributionService(db_connection, paid_threshold)
        self.category_service = CategoryDistributionService(db_connection)
        self.thumbnail_service = ThumbnailConsistencyService(db_connection)
        self.tone_service = ToneOfVoiceService(db_connection)
    
    def calculate_country_7_metrics(self, country: str) -> Dict[str, Any]:
        """Calculate all 7 key metrics for a country."""
        try:
            # 1. Video Length Analysis
            video_length = self.video_length_service.calculate_video_length_metrics(country)
            
            # 2. Video Frequency Analysis
            video_frequency = self.frequency_service.calculate_video_frequency_metrics(country)
            
            # 3. Most Liked Topics Analysis
            most_liked_topics = self.topic_service.calculate_most_liked_topics(country)
            
            # 4. Organic vs Paid Distribution
            organic_vs_paid = self.distribution_service.calculate_organic_vs_paid_distribution(country)
            
            # 5. Hub/Help/Hero Distribution
            hub_help_hero = self.category_service.calculate_hub_help_hero_distribution(country)
            
            # 6. Thumbnail Consistency
            thumbnail_consistency = self.thumbnail_service.calculate_thumbnail_consistency(country)
            
            # 7. Tone of Voice Analysis
            tone_of_voice = self.tone_service.analyze_tone_of_voice(country)
            
            return {
                'video_length': video_length,
                'video_frequency': video_frequency,
                'most_liked_topics': most_liked_topics,
                'organic_vs_paid': organic_vs_paid,
                'hub_help_hero': hub_help_hero,
                'thumbnail_consistency': thumbnail_consistency,
                'tone_of_voice': tone_of_voice,
                'generated_at': datetime.now().isoformat(),
                'competitors_count': 0,  # Will be filled in main function
                'total_videos': video_length['total_videos']
            }
            
        except Exception as e:
            print(f"[COUNTRY_METRICS] Error calculating metrics for {country}: {e}")
            return self._empty_country_metrics()
    
    def _empty_country_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure when analysis fails."""
        return {
            'video_length': self.video_length_service._empty_video_length_metrics(),
            'video_frequency': self.frequency_service._empty_frequency_metrics(),
            'most_liked_topics': [],
            'organic_vs_paid': self.distribution_service._empty_distribution_metrics(),
            'hub_help_hero': self.category_service._empty_category_metrics(),
            'thumbnail_consistency': self.thumbnail_service._empty_thumbnail_metrics(),
            'tone_of_voice': self.tone_service._empty_tone_metrics(),
            'generated_at': datetime.now().isoformat(),
            'competitors_count': 0,
            'total_videos': 0
        }