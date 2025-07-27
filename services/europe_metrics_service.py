"""
Europe Metrics Service - Consolidation de tous les pays européens
Architecture: CHANNELS < COUNTRIES < EUROPE
Métriques identiques aux autres pages insights mais scope européen/international
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
        return {'paid_threshold': 10000}

class EuropeMetricsService:
    """Service for calculating Europe-level consolidated metrics from all countries."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = None):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        # Load from settings if not provided
        if paid_threshold is None:
            settings = load_settings()
            paid_threshold = settings.get('paid_threshold', 10000)
        self.paid_threshold = paid_threshold
        print(f"[EUROPE_METRICS] Using paid_threshold: {self.paid_threshold}")
    
    def get_european_countries(self) -> Dict[str, Dict[str, Any]]:
        """Get all European countries with their competitor counts."""
        self.cursor.execute("""
            SELECT 
                country,
                COUNT(DISTINCT id) as competitor_count,
                COUNT(DISTINCT CASE WHEN country IS NOT NULL AND country != '' THEN id END) as valid_competitors
            FROM concurrent 
            WHERE country IS NOT NULL AND country != ''
            GROUP BY country 
            ORDER BY competitor_count DESC
        """)
        
        countries = {}
        total_competitors = 0
        
        for row in self.cursor.fetchall():
            country, competitor_count, valid_competitors = row
            
            # Map to friendly display names with flags
            if country == 'Germany':
                display_name = '🇩🇪 Allemagne'
            elif country == 'France':
                display_name = '🇫🇷 France'
            elif country == 'Netherlands':
                display_name = '🇳🇱 Pays-Bas'
            elif country == 'United Kingdom':
                display_name = '🇬🇧 Royaume-Uni'
            elif country == 'International':
                display_name = '🌍 International'
            else:
                display_name = f"🏳️ {country}"
                
            countries[country] = {
                'display_name': display_name,
                'competitor_count': competitor_count,
                'valid_competitors': valid_competitors
            }
            total_competitors += competitor_count
        
        print(f"[EUROPE_METRICS] 🌍 {len(countries)} pays trouvés, {total_competitors} concurrents total")
        return countries
    
    def calculate_europe_metrics(self) -> Dict[str, Any]:
        """Calculate consolidated metrics for all Europe (all countries combined)."""
        try:
            print(f"[EUROPE_METRICS] 🌍 Calcul des métriques européennes consolidées...")
            
            # 1. Video Length Analysis (Europe-wide)
            video_length = self._calculate_video_length_metrics()
            
            # 2. Video Frequency Analysis (Europe-wide)  
            video_frequency = self._calculate_video_frequency_metrics()
            
            # 3. Most Liked Topics Analysis (Europe-wide)
            most_liked_topics = self._calculate_most_liked_topics()
            
            # 4. Organic vs Paid Distribution (Europe-wide)
            organic_vs_paid = self._calculate_organic_vs_paid_distribution()
            
            # 5. Hub/Help/Hero Distribution (Europe-wide)
            hub_help_hero = self._calculate_hub_help_hero_distribution()
            
            # 6. Thumbnail Consistency (Europe-wide)
            thumbnail_consistency = self._calculate_thumbnail_consistency()
            
            # 7. Tone of Voice Analysis (Europe-wide)
            tone_of_voice = self._analyze_tone_of_voice()
            
            # 8. Shorts vs Regular Distribution (Europe-wide)
            shorts_distribution = self._calculate_shorts_distribution(video_length)
            
            # 9. Country breakdown for detailed view
            country_breakdown = self._calculate_country_breakdown()
            
            return {
                'video_length': video_length,
                'video_frequency': video_frequency,
                'most_liked_topics': most_liked_topics,
                'organic_vs_paid': organic_vs_paid,
                'hub_help_hero': hub_help_hero,
                'thumbnail_consistency': thumbnail_consistency,
                'tone_of_voice': tone_of_voice,
                'shorts_distribution': shorts_distribution,
                'country_breakdown': country_breakdown,
                'generated_at': datetime.now().isoformat(),
                'total_countries': len(self.get_european_countries()),
                'total_videos': video_length['total_videos']
            }
            
        except Exception as e:
            print(f"[EUROPE_METRICS] Error calculating Europe metrics: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_europe_metrics()
    
    def _calculate_video_length_metrics(self) -> Dict[str, Any]:
        """Calculate video length statistics for all Europe."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                AVG(v.duration_seconds / 60.0) as avg_duration_minutes,
                MIN(v.duration_seconds / 60.0) as min_duration_minutes,
                MAX(v.duration_seconds / 60.0) as max_duration_minutes,
                COUNT(CASE WHEN v.duration_seconds <= 60 THEN 1 END) as shorts_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.duration_seconds IS NOT NULL AND v.duration_seconds > 0
        """)
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
    
    def _calculate_video_frequency_metrics(self) -> Dict[str, Any]:
        """Calculate video frequency statistics for all Europe - FRÉQUENCE PONDÉRÉE."""
        # Calculer la vraie fréquence européenne pondérée, pas une moyenne des moyennes
        self.cursor.execute("""
            SELECT 
                c.id,
                c.name,
                COUNT(v.id) as video_count,
                MIN(DATE(v.youtube_published_at)) as first_date,
                MAX(DATE(v.youtube_published_at)) as last_date,
                CASE 
                    WHEN MIN(DATE(v.youtube_published_at)) IS NOT NULL AND MAX(DATE(v.youtube_published_at)) IS NOT NULL
                    THEN (julianday(MAX(DATE(v.youtube_published_at))) - julianday(MIN(DATE(v.youtube_published_at)))) / 7.0
                    ELSE 0 
                END as weeks_span
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id 
            WHERE v.youtube_published_at IS NOT NULL
            AND DATE(v.youtube_published_at) >= '2020-01-01'
            GROUP BY c.id, c.name
            HAVING video_count > 5
        """)
        
        total_videos = 0
        total_weighted_weeks = 0
        competitor_count = 0
        frequencies = []
        
        for row in self.cursor.fetchall():
            competitor_id, name, video_count, first_date, last_date, weeks_span = row
            
            if weeks_span and weeks_span > 0:
                # Calculer la fréquence individuelle
                freq_per_week = video_count / weeks_span
                
                # Safeguard contre les fréquences absurdes
                if freq_per_week > 20:
                    estimated_weeks = video_count / 3  # Estimer 3 vidéos/semaine max
                    weeks_span = estimated_weeks
                    freq_per_week = 3.0
                    print(f"[EUROPE_FREQ] 🚨 {name}: fréquence ajustée à 3.0/sem")
                
                # Accumulation pondérée par le nombre de vidéos
                total_videos += video_count
                total_weighted_weeks += weeks_span * video_count  # Pondération !
                frequencies.append(freq_per_week)
                competitor_count += 1
        
        if not frequencies or total_weighted_weeks == 0:
            return self._empty_frequency_metrics()
        
        # Fréquence européenne pondérée = total vidéos / moyenne pondérée des semaines
        weighted_avg_weeks = total_weighted_weeks / total_videos
        videos_per_week = round(total_videos / weighted_avg_weeks, 1)
        
        print(f"[EUROPE_FREQ] 📊 {competitor_count} concurrents analysés")
        print(f"[EUROPE_FREQ] 📈 {total_videos:,} vidéos sur {weighted_avg_weeks:.1f} semaines pondérées")
        print(f"[EUROPE_FREQ] 🎯 Fréquence européenne pondérée: {videos_per_week:.1f} vidéos/semaine")
        
        return {
            'total_videos': total_videos,
            'videos_per_week': videos_per_week,
            'competitor_count': competitor_count,
            'consistency_score': round((min(frequencies) / max(frequencies)) * 100, 1) if len(frequencies) > 1 else 100
        }
    
    def _calculate_most_liked_topics(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Calculate most liked topics across all Europe."""
        self.cursor.execute("""
            SELECT 
                v.title,
                v.like_count,
                v.view_count,
                v.comment_count,
                v.category,
                c.country,
                (CAST(v.like_count + v.comment_count AS FLOAT) / NULLIF(v.view_count, 0) * 100) as engagement_rate
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.view_count > 100
            ORDER BY engagement_rate DESC, v.like_count DESC
            LIMIT ?
        """, (limit,))
        liked_topics_data = self.cursor.fetchall()
        
        most_liked_topics = []
        for topic in liked_topics_data:
            title = topic[0][:50] + '...' if len(topic[0]) > 50 else topic[0]
            most_liked_topics.append({
                'title': title,
                'like_ratio': round(topic[6], 1) if topic[6] else 0,
                'views': topic[2],
                'country': topic[5],
                'category': topic[4] or 'All'
            })
        
        return most_liked_topics
    
    def _calculate_organic_vs_paid_distribution(self) -> Dict[str, Any]:
        """Calculate organic vs paid content distribution across all Europe."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.view_count < ? THEN 1 END) as organic_count,
                COUNT(CASE WHEN v.view_count >= ? THEN 1 END) as paid_count,
                AVG(CASE WHEN v.view_count < ? THEN v.view_count END) as organic_avg_views,
                AVG(CASE WHEN v.view_count >= ? THEN v.view_count END) as paid_avg_views
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.view_count > 0
        """, (self.paid_threshold, self.paid_threshold, self.paid_threshold, self.paid_threshold))
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
    
    def _calculate_hub_help_hero_distribution(self) -> Dict[str, Any]:
        """Calculate Hub/Help/Hero distribution across all Europe."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN v.category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN v.category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN v.category = 'help' THEN 1 END) as help_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.category IS NOT NULL
        """)
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
            'help_percentage': round((help_count / max(total_categorized, 1)) * 100, 1),
            'total_categorized': total_categorized
        }
    
    def _calculate_thumbnail_consistency(self) -> Dict[str, Any]:
        """Calculate thumbnail consistency across all Europe."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN v.thumbnail_url IS NOT NULL AND v.thumbnail_url != '' THEN 1 END) as with_thumbnails
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
        """)
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
    
    def _analyze_tone_of_voice(self, sample_limit: int = 200) -> Dict[str, Any]:
        """Analyze tone of voice across all Europe."""
        self.cursor.execute("""
            SELECT 
                v.title,
                LENGTH(v.title) as title_length,
                c.country
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.title IS NOT NULL
            LIMIT ?
        """, (sample_limit,))
        tone_data = self.cursor.fetchall()
        
        if not tone_data:
            return self._empty_tone_metrics()
        
        return self._analyze_titles(tone_data)
    
    def _analyze_titles(self, tone_data: List[Tuple]) -> Dict[str, Any]:
        """Analyze titles for emotional/action words and keywords."""
        emotional_words = ['amazing', 'incredible', 'beautiful', 'fantastic', 'wonderful', 'perfect', 'love', 'best']
        action_words = ['discover', 'explore', 'visit', 'experience', 'enjoy', 'learn', 'watch', 'see']
        
        emotional_count = 0
        action_count = 0
        total_length = 0
        top_words = {}
        country_distribution = {}
        
        for title_data in tone_data:
            title = title_data[0].lower()
            total_length += title_data[1]
            country = title_data[2]
            
            # Count by country
            country_distribution[country] = country_distribution.get(country, 0) + 1
            
            # Count emotional words
            for word in emotional_words:
                if word in title:
                    emotional_count += 1
            
            # Count action words
            for word in action_words:
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
            'dominant_tone': 'Adventure' if action_count > emotional_count else 'Family',
            'country_distribution': country_distribution
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
    
    def _calculate_country_breakdown(self) -> Dict[str, Any]:
        """Calculate breakdown by country for Europe overview."""
        self.cursor.execute("""
            SELECT 
                c.country,
                COUNT(DISTINCT c.id) as competitor_count,
                COUNT(v.id) as video_count,
                AVG(v.view_count) as avg_views,
                COUNT(CASE WHEN v.view_count >= ? THEN 1 END) as paid_videos,
                COUNT(CASE WHEN v.category IS NOT NULL THEN 1 END) as categorized_videos
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE c.country IS NOT NULL AND c.country != ''
            GROUP BY c.country
            ORDER BY video_count DESC
        """, (self.paid_threshold,))
        
        countries = {}
        for row in self.cursor.fetchall():
            country, competitors, videos, avg_views, paid_videos, categorized = row
            
            countries[country] = {
                'competitor_count': competitors,
                'video_count': videos,
                'avg_views': round(avg_views, 0) if avg_views else 0,
                'paid_percentage': round((paid_videos / max(videos, 1)) * 100, 1),
                'categorized_videos': categorized
            }
        
        return countries
    
    def _empty_video_length_metrics(self) -> Dict[str, Any]:
        return {
            'total_videos': 0, 'avg_duration_minutes': 0, 'min_duration_minutes': 0, 
            'max_duration_minutes': 0, 'shorts_count': 0, 'shorts_percentage': 0
        }
    
    def _empty_frequency_metrics(self) -> Dict[str, Any]:
        return {'total_videos': 0, 'videos_per_week': 0, 'days_active': 0, 'consistency_score': 0}
    
    def _empty_distribution_metrics(self) -> Dict[str, Any]:
        return {
            'organic_count': 0, 'paid_count': 0, 'organic_percentage': 0, 
            'paid_percentage': 0, 'organic_avg_views': 0
        }
    
    def _empty_category_metrics(self) -> Dict[str, Any]:
        return {
            'hero_count': 0, 'hub_count': 0, 'help_count': 0,
            'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0, 'total_categorized': 0
        }
    
    def _empty_thumbnail_metrics(self) -> Dict[str, Any]:
        return {'total_videos': 0, 'with_thumbnails': 0, 'consistency_score': 0}
    
    def _empty_tone_metrics(self) -> Dict[str, Any]:
        return {
            'emotional_words': 0, 'action_words': 0, 'avg_title_length': 0, 
            'top_keywords': [], 'dominant_tone': 'Neutral', 'country_distribution': {}
        }
    
    def _empty_europe_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure when analysis fails."""
        return {
            'video_length': self._empty_video_length_metrics(),
            'video_frequency': self._empty_frequency_metrics(),
            'most_liked_topics': [],
            'organic_vs_paid': self._empty_distribution_metrics(),
            'hub_help_hero': self._empty_category_metrics(),
            'thumbnail_consistency': self._empty_thumbnail_metrics(),
            'tone_of_voice': self._empty_tone_metrics(),
            'shorts_distribution': {
                'total_videos': 0, 'shorts_count': 0, 'regular_count': 0,
                'shorts_percentage': 0.0, 'regular_percentage': 0.0
            },
            'country_breakdown': {},
            'generated_at': datetime.now().isoformat(),
            'total_countries': 0,
            'total_videos': 0
        }