"""
Service for calculating dual metrics (Local vs Global) for country insights.
Implements the methodology: Local actors only vs All actors (Local + International).
"""
from typing import Dict, List, Set, Any, Tuple
from datetime import datetime
import sqlite3


class LocalGlobalSegmentation:
    """Handles segmentation of actors into local vs international categories."""
    
    # International actors present in all markets
    INTERNATIONAL_ACTORS = {
        'Airbnb', 'Booking.com', 'Expedia', 'Hotels.com', 
        'Marriott International', 'Marriott Bonvoy', 'Hilton', 
        'Switzerland', 'Eurocamp.co.uk'
    }
    
    # Local actors by country
    LOCAL_ACTORS = {
        'France': {
            'Center Parcs France', 'Belambra', 'VVF', 'HOMAIR', 
            'Huttopia Campings & Villages', 'Siblu Villages', 
            'Sunparks France', 'Club Med'
        },
        'Germany': {
            'TUI Deutschland', 'HessenTourismus', 'Bavaria Travel', 
            'simply Munich', 'Maritim Hotels', 'ARD Reisen', 
            'Center Parcs Ferienparks'
        },
        'Netherlands': {
            'Roompot', 'Landal', 'Hof van Saksen', 'Center Parcs'
        },
        'United Kingdom': {
            'Center Parcs'
        }
    }
    
    @classmethod
    def is_international(cls, competitor_name: str) -> bool:
        """Check if a competitor is an international actor."""
        return competitor_name in cls.INTERNATIONAL_ACTORS
    
    @classmethod
    def get_local_actors(cls, country: str) -> Set[str]:
        """Get local actors for a specific country."""
        return cls.LOCAL_ACTORS.get(country, set())
    
    @classmethod
    def get_all_actors(cls, country: str) -> Set[str]:
        """Get all actors (local + international) for a country."""
        local = cls.get_local_actors(country)
        return local.union(cls.INTERNATIONAL_ACTORS)


class DualMetricsCalculator:
    """Calculates metrics with Local vs Global distinction."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.segmentation = LocalGlobalSegmentation()
    
    def should_show_dual_value(self, local_value: float, global_value: float) -> bool:
        """Determine if we should show both local and global values (gap > 30%)."""
        if global_value == 0:
            return False
        gap_percentage = abs(local_value - global_value) / global_value * 100
        return gap_percentage > 30
    
    def format_dual_metric(self, local_value: Any, global_value: Any, 
                          metric_type: str = 'number') -> Dict[str, Any]:
        """Format a metric with ALWAYS displayed dual values."""
        if metric_type == 'percentage':
            local_formatted = f"{local_value:.1f}%"
            global_formatted = f"{global_value:.1f}%"
        elif metric_type == 'minutes':
            local_formatted = f"{local_value:.1f}min"
            global_formatted = f"{global_value:.1f}min"
        elif metric_type == 'frequency':
            local_formatted = f"{local_value:.1f}/sem"
            global_formatted = f"{global_value:.1f}/sem"
        else:
            local_formatted = f"{local_value}"
            global_formatted = f"{global_value}"
        
        # ALWAYS show dual values now (règle absolue)
        show_dual = True
        
        # Calculate gap percentage with sign
        if global_value > 0:
            gap_percent = ((local_value - global_value) / global_value) * 100
        else:
            gap_percent = 0
        
        gap_percent_rounded = round(gap_percent)
        gap_formatted = f"{gap_percent_rounded:+d}%"  # +19% ou -69%
        
        # Determine badge color based on performance
        if gap_percent_rounded > 0:
            gap_badge_color = "success"  # Vert : Local > Global
        elif gap_percent_rounded < -10:
            gap_badge_color = "danger"   # Rouge : Local << Global  
        else:
            gap_badge_color = "secondary"  # Gris : Écart faible
        
        return {
            'local': local_value,
            'global': global_value,
            'local_formatted': local_formatted,
            'global_formatted': global_formatted,
            'show_dual': show_dual,  # Always True now
            'gap_percentage': abs(gap_percent),  # For backwards compatibility
            'gap_percent': gap_percent_rounded,  # New: with sign
            'gap_formatted': gap_formatted,     # New: formatted with sign
            'gap_badge_color': gap_badge_color  # New: Bootstrap color
        }
    
    def get_competitor_ids_by_type(self, country: str, local_only: bool = True) -> List[int]:
        """Get competitor IDs based on local/global filter for NATIONAL MARKET ONLY."""
        if local_only:
            # Acteurs locaux uniquement (ex: Belambra pour France)
            local_actors = self.segmentation.get_local_actors(country)
            if not local_actors:
                return []
            placeholders = ','.join(['?' for _ in local_actors])
            query = f"""
                SELECT id FROM concurrent 
                WHERE name IN ({placeholders})
            """
            self.cursor.execute(query, tuple(local_actors))
        else:
            # MARCHÉ NATIONAL COMPLET = Acteurs locaux + Internationaux présents sur ce marché
            # ✅ Pour France : Center Parcs France + Airbnb France + Booking.fr
            # ❌ PAS : Center Parcs UK + Airbnb Germany + Booking.de
            local_actors = self.segmentation.get_local_actors(country)
            international_actors = self.segmentation.INTERNATIONAL_ACTORS
            
            all_national_actors = list(local_actors) + list(international_actors)
            
            if not all_national_actors:
                return []
                
            placeholders = ','.join(['?' for _ in all_national_actors])
            query = f"""
                SELECT id FROM concurrent 
                WHERE name IN ({placeholders})
                AND (country = ? OR country = 'International')
            """
            self.cursor.execute(query, tuple(list(all_national_actors) + [country]))
        
        return [row[0] for row in self.cursor.fetchall()]
    
    def calculate_video_length_dual(self, country: str) -> Dict[str, Any]:
        """Calculate video length metrics for both local and global scope."""
        # Local actors only
        local_ids = self.get_competitor_ids_by_type(country, local_only=True)
        local_metrics = self._calculate_video_length_for_ids(local_ids) if local_ids else {'avg': 0, 'count': 0}
        
        # All actors (local + international)
        global_ids = self.get_competitor_ids_by_type(country, local_only=False)
        global_metrics = self._calculate_video_length_for_ids(global_ids) if global_ids else {'avg': 0, 'count': 0}
        
        return self.format_dual_metric(
            local_metrics['avg'], 
            global_metrics['avg'],
            metric_type='minutes'
        )
    
    def _calculate_video_length_for_ids(self, competitor_ids: List[int]) -> Dict[str, float]:
        """Calculate average video length for specific competitor IDs."""
        if not competitor_ids:
            return {'avg': 0, 'count': 0}
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        # Filtrer les vidéos récentes (3-6 mois) et exclure les shorts < 30s
        query = f"""
            SELECT 
                AVG(duration_seconds / 60.0) as avg_duration_minutes,
                COUNT(*) as video_count
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND duration_seconds IS NOT NULL 
            AND duration_seconds > 30
            AND DATE(published_at) >= DATE('now', '-6 months')
        """
        self.cursor.execute(query, tuple(competitor_ids))
        result = self.cursor.fetchone()
        
        return {
            'avg': round(result[0], 1) if result[0] else 0,
            'count': result[1] or 0
        }
    
    def calculate_frequency_dual(self, country: str) -> Dict[str, Any]:
        """Calculate video frequency metrics for both local and global scope."""
        # Local actors only
        local_ids = self.get_competitor_ids_by_type(country, local_only=True)
        local_metrics = self._calculate_frequency_for_ids(local_ids) if local_ids else {'videos_per_week': 0}
        
        # All actors (local + international)
        global_ids = self.get_competitor_ids_by_type(country, local_only=False)
        global_metrics = self._calculate_frequency_for_ids(global_ids) if global_ids else {'videos_per_week': 0}
        
        return self.format_dual_metric(
            local_metrics['videos_per_week'], 
            global_metrics['videos_per_week'],
            metric_type='frequency'
        )
    
    def _calculate_frequency_for_ids(self, competitor_ids: List[int]) -> Dict[str, float]:
        """Calculate video frequency for specific competitor IDs."""
        if not competitor_ids:
            return {'videos_per_week': 0}
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        query = f"""
            SELECT 
                COUNT(DISTINCT id) as total_videos,
                (julianday('now') - julianday(MIN(youtube_published_at))) / 7.0 as weeks_active
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND youtube_published_at IS NOT NULL
            AND DATE(youtube_published_at) >= '2020-01-01'
        """
        self.cursor.execute(query, tuple(competitor_ids))
        result = self.cursor.fetchone()
        
        if result and result[0] and result[1] and result[1] > 0:
            videos_per_week = round(result[0] / result[1], 1)
        else:
            videos_per_week = 0
        
        return {'videos_per_week': videos_per_week}
    
    def calculate_shorts_percentage_dual(self, country: str) -> Dict[str, Any]:
        """Calculate shorts percentage for both local and global scope."""
        # Local actors only
        local_ids = self.get_competitor_ids_by_type(country, local_only=True)
        local_metrics = self._calculate_shorts_for_ids(local_ids) if local_ids else {'shorts_percentage': 0}
        
        # All actors (local + international)
        global_ids = self.get_competitor_ids_by_type(country, local_only=False)
        global_metrics = self._calculate_shorts_for_ids(global_ids) if global_ids else {'shorts_percentage': 0}
        
        return self.format_dual_metric(
            local_metrics['shorts_percentage'], 
            global_metrics['shorts_percentage'],
            metric_type='percentage'
        )
    
    def _calculate_shorts_for_ids(self, competitor_ids: List[int]) -> Dict[str, float]:
        """Calculate shorts percentage for specific competitor IDs."""
        if not competitor_ids:
            return {'shorts_percentage': 0}
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        query = f"""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN duration_seconds <= 60 THEN 1 END) as shorts_count
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND duration_seconds IS NOT NULL
        """
        self.cursor.execute(query, tuple(competitor_ids))
        result = self.cursor.fetchone()
        
        if result and result[0] > 0:
            shorts_percentage = round((result[1] / result[0]) * 100, 1)
        else:
            shorts_percentage = 0
        
        return {'shorts_percentage': shorts_percentage}
    
    def calculate_organic_percentage_dual(self, country: str) -> Dict[str, Any]:
        """Calculate organic percentage for both local and global scope."""
        # Local actors only
        local_ids = self.get_competitor_ids_by_type(country, local_only=True)
        local_metrics = self._calculate_organic_for_ids(local_ids) if local_ids else {'organic_percentage': 0}
        
        # All actors (local + international)
        global_ids = self.get_competitor_ids_by_type(country, local_only=False)
        global_metrics = self._calculate_organic_for_ids(global_ids) if global_ids else {'organic_percentage': 0}
        
        return self.format_dual_metric(
            local_metrics['organic_percentage'], 
            global_metrics['organic_percentage'],
            metric_type='percentage'
        )
    
    def _calculate_organic_for_ids(self, competitor_ids: List[int]) -> Dict[str, float]:
        """Calculate organic percentage for specific competitor IDs."""
        if not competitor_ids:
            return {'organic_percentage': 0}
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        # Assuming paid threshold of 100K+ views as organic vs paid distinction
        query = f"""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN view_count < 100000 THEN 1 END) as organic_count
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND view_count IS NOT NULL
        """
        self.cursor.execute(query, tuple(competitor_ids))
        result = self.cursor.fetchone()
        
        if result and result[0] > 0:
            organic_percentage = round((result[1] / result[0]) * 100, 1)
        else:
            organic_percentage = 0
        
        return {'organic_percentage': organic_percentage}
    
    def calculate_hhh_distribution_dual(self, country: str) -> Dict[str, Any]:
        """Calculate HHH distribution for both local and global scope."""
        # Local actors only
        local_ids = self.get_competitor_ids_by_type(country, local_only=True)
        local_metrics = self._calculate_hhh_for_ids(local_ids) if local_ids else {'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0}
        
        # All actors (local + international)
        global_ids = self.get_competitor_ids_by_type(country, local_only=False)
        global_metrics = self._calculate_hhh_for_ids(global_ids) if global_ids else {'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0}
        
        # Return complete HHH distribution for both scopes
        return {
            'national': {
                'hero_percentage': local_metrics['hero_percentage'],
                'hub_percentage': local_metrics['hub_percentage'], 
                'help_percentage': local_metrics['help_percentage'],
                'formatted': f"H{local_metrics['hero_percentage']:.0f}% • H{local_metrics['hub_percentage']:.0f}% • H{local_metrics['help_percentage']:.0f}%"
            },
            'marche': {
                'hero_percentage': global_metrics['hero_percentage'],
                'hub_percentage': global_metrics['hub_percentage'],
                'help_percentage': global_metrics['help_percentage'], 
                'formatted': f"H{global_metrics['hero_percentage']:.0f}% • H{global_metrics['hub_percentage']:.0f}% • H{global_metrics['help_percentage']:.0f}%"
            },
            'show_dual': True,
            'dominant_category': 'Hub'  # For display purposes
        }
    
    def _calculate_hhh_for_ids(self, competitor_ids: List[int]) -> Dict[str, float]:
        """Calculate HHH distribution for specific competitor IDs."""
        if not competitor_ids:
            return {'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0}
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        query = f"""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND category IS NOT NULL
        """
        self.cursor.execute(query, tuple(competitor_ids))
        result = self.cursor.fetchone()
        
        if result and result[0] > 0:
            total = result[0]
            hero_percentage = round((result[1] / total) * 100, 1)
            hub_percentage = round((result[2] / total) * 100, 1)
            help_percentage = round((result[3] / total) * 100, 1)
        else:
            hero_percentage = hub_percentage = help_percentage = 0
        
        return {
            'hero_percentage': hero_percentage,
            'hub_percentage': hub_percentage,
            'help_percentage': help_percentage
        }
    
    def calculate_most_liked_topics_dual(self, country: str) -> Dict[str, List[Dict[str, Any]]]:
        """Calculate most liked topics for both national and international scope."""
        
        # 1. Topics nationaux (UNIQUEMENT acteurs locaux du pays)
        # 🇫🇷 France: Center Parcs France, Belambra, VVF, HOMAIR, Huttopia, etc.
        # 🇩🇪 Germany: Center Parcs Ferienparks, TUI Deutschland, Bavaria Travel, etc.
        national_topics = self._calculate_topics_for_scope(country, local_only=True)
        
        # 2. Topics européens/internationaux (tous les acteurs internationaux, toutes langues)
        international_topics = self._calculate_topics_international()
        
        return {
            'national': national_topics,
            'international': international_topics
        }
    
    def _calculate_topics_for_scope(self, country: str, local_only: bool) -> List[Dict[str, Any]]:
        """Calculate topics for a specific scope (national market)."""
        competitor_ids = self.get_competitor_ids_by_type(country, local_only=local_only)
        
        if not competitor_ids:
            return []
        
        placeholders = ','.join(['?' for _ in competitor_ids])
        query = f"""
            SELECT 
                title,
                like_count,
                comment_count,
                (like_count + comment_count) as engagement_score,
                view_count
            FROM video
            WHERE concurrent_id IN ({placeholders})
            AND like_count IS NOT NULL 
            AND comment_count IS NOT NULL
            AND DATE(published_at) >= DATE('now', '-6 months')
            AND duration_seconds > 30
            AND title NOT LIKE '%sponsor%'
            AND title NOT LIKE '%publicit%'
            ORDER BY engagement_score DESC
            LIMIT 100
        """
        self.cursor.execute(query, tuple(competitor_ids))
        results = self.cursor.fetchall()
        
        return self._process_topics_from_results(results)
    
    def _calculate_topics_international(self) -> List[Dict[str, Any]]:
        """Calculate topics for international/European scope (all languages)."""
        # Get all international actors
        international_actors = list(self.segmentation.INTERNATIONAL_ACTORS)
        
        if not international_actors:
            return []
            
        placeholders = ','.join(['?' for _ in international_actors])
        query = f"""
            SELECT 
                v.title,
                v.like_count,
                v.comment_count,
                (v.like_count + v.comment_count) as engagement_score,
                v.view_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.name IN ({placeholders})
            AND v.like_count IS NOT NULL 
            AND v.comment_count IS NOT NULL
            AND DATE(v.published_at) >= DATE('now', '-6 months')
            AND v.duration_seconds > 30
            AND v.title NOT LIKE '%sponsor%'
            AND v.title NOT LIKE '%publicit%'
            ORDER BY engagement_score DESC
            LIMIT 100
        """
        self.cursor.execute(query, tuple(international_actors))
        results = self.cursor.fetchall()
        
        return self._process_topics_from_results(results, international=True)
    
    def _process_topics_from_results(self, results: List, international: bool = False) -> List[Dict[str, Any]]:
        """Process SQL results into top 5 video titles by engagement."""
        topics = []
        for row in results[:5]:  # Take top 5 videos directly
            title, likes, comments, engagement, views = row
            topics.append({
                'topic': title,  # Use the title directly
                'avg_engagement': engagement,
                'likes': likes,
                'comments': comments,
                'views': views
            })
        
        return topics
    


class LocalGlobalMetricsService:
    """Enhanced country metrics service with Local vs Global analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.dual_calculator = DualMetricsCalculator(db_connection)
        # Import the original service for non-dual metrics
        from services.country_metrics_service import CountryMetricsService
        self.base_service = CountryMetricsService(db_connection)
    
    def calculate_enhanced_country_metrics(self, country: str) -> Dict[str, Any]:
        """Calculate country metrics with Local vs Global distinctions where applicable."""
        # Get base metrics
        base_metrics = self.base_service.calculate_country_7_metrics(country)
        
        # Enhance with dual metrics for specific fields
        enhanced_metrics = base_metrics.copy()
        
        # 1. Video Length - Dual metric
        video_length_dual = self.dual_calculator.calculate_video_length_dual(country)
        enhanced_metrics['video_length']['dual_metric'] = video_length_dual
        
        # 2. Video Frequency - Dual metric
        frequency_dual = self.dual_calculator.calculate_frequency_dual(country)
        enhanced_metrics['video_frequency']['dual_metric'] = frequency_dual
        
        # 3. Shorts Percentage - Dual metric
        shorts_dual = self.dual_calculator.calculate_shorts_percentage_dual(country)
        enhanced_metrics['shorts_distribution']['dual_metric'] = shorts_dual
        
        # 4. Organic vs Paid - Dual metric
        organic_dual = self.dual_calculator.calculate_organic_percentage_dual(country)
        enhanced_metrics['organic_vs_paid']['dual_metric'] = organic_dual
        
        # 5. HHH Distribution - Dual metric (focus on Hub percentage)
        hhh_dual = self.dual_calculator.calculate_hhh_distribution_dual(country)
        enhanced_metrics['hub_help_hero']['dual_metric'] = hhh_dual
        
        # 6. Most Liked Topics - Dual analysis (National vs International)
        most_liked_topics_dual = self.dual_calculator.calculate_most_liked_topics_dual(country)
        enhanced_metrics['most_liked_topics_dual'] = most_liked_topics_dual
        
        # Mark which metrics have dual values available
        enhanced_metrics['has_dual_metrics'] = True
        enhanced_metrics['dual_metrics_info'] = {
            'video_length': video_length_dual['show_dual'],
            'frequency': frequency_dual['show_dual'],
            'shorts': shorts_dual['show_dual'],
            'organic': organic_dual['show_dual'],
            'hhh': hhh_dual['show_dual']
        }
        
        return enhanced_metrics