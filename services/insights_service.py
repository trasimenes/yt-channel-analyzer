"""
Service layer for brand insights analysis.
Extracted from monolithic app.py insights() function (complexity 62 -> <10).
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sqlite3


class BrandChannelService:
    """Handles brand channel data retrieval and validation."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def get_brand_channels(self, brand_pattern: str = '%Center Parcs%') -> List[sqlite3.Row]:
        """Get all channels matching brand pattern."""
        self.cursor.execute("""
            SELECT id, name, channel_url, country 
            FROM concurrent 
            WHERE name LIKE ? 
            ORDER BY country
        """, (brand_pattern,))
        return self.cursor.fetchall()
    
    def validate_channel_content(self, competitor_id: int) -> bool:
        """Check if channel has video content."""
        self.cursor.execute("SELECT COUNT(*) FROM video WHERE concurrent_id = ?", (competitor_id,))
        video_count = self.cursor.fetchone()[0]
        return video_count > 0


class BrandMetricsService:
    """Handles brand metrics calculations."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_basic_stats(self, competitor_id: int) -> Dict[str, Any]:
        """Calculate basic video statistics for a competitor."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(SUM(v.like_count), 0) as total_likes,
                COALESCE(SUM(v.comment_count), 0) as total_comments,
                COALESCE(AVG(v.view_count), 0) as avg_views,
                COUNT(CASE WHEN v.duration_seconds <= 60 THEN 1 END) as shorts_count,
                COALESCE(AVG(v.duration_seconds), 0) as avg_duration
            FROM video v
            WHERE v.concurrent_id = ?
        """, (competitor_id,))
        return dict(zip([
            'total_videos', 'total_views', 'total_likes', 'total_comments',
            'avg_views', 'shorts_count', 'avg_duration'
        ], self.cursor.fetchone()))
    
    def calculate_category_distribution(self, competitor_id: int) -> Dict[str, int]:
        """Calculate Hub/Help/Hero distribution."""
        self.cursor.execute("""
            SELECT 
                v.category,
                COUNT(*) as count
            FROM video v
            WHERE v.concurrent_id = ? AND v.category IS NOT NULL
            GROUP BY v.category
        """, (competitor_id,))
        
        category_dist = {}
        for category, count in self.cursor.fetchall():
            category_dist[category] = count
        
        return category_dist


class VideoFrequencyService:
    """Handles video frequency analysis with detailed debugging."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_video_frequency(self, competitor_id: int, channel_name: str) -> Optional[float]:
        """Calculate videos per week with comprehensive debugging."""
        print(f"[DEBUG FREQUENCY] 🚀 === DÉMARRAGE DEBUG POUR {channel_name} (ID: {competitor_id}) ===")
        
        # Get date information
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                MIN(COALESCE(v.youtube_published_at, v.published_at)) as first_video,
                MAX(COALESCE(v.youtube_published_at, v.published_at)) as last_video,
                COUNT(v.youtube_published_at) as youtube_dates_count,
                COUNT(v.published_at) as published_dates_count,
                COUNT(*) FILTER (WHERE v.youtube_published_at IS NOT NULL) as youtube_not_null,
                COUNT(*) FILTER (WHERE v.published_at IS NOT NULL) as published_not_null
            FROM video v
            WHERE v.concurrent_id = ?
        """, (competitor_id,))
        video_dates = self.cursor.fetchone()
        
        self._debug_date_info(channel_name, video_dates)
        
        # Get sample videos for debugging
        self._debug_sample_videos(competitor_id, channel_name)
        
        return self._calculate_frequency_from_dates(video_dates, channel_name)
    
    def _debug_date_info(self, channel_name: str, video_dates: sqlite3.Row) -> None:
        """Debug date information."""
        print(f"[DEBUG FREQUENCY] 📊 Résultats SQL pour {channel_name}:")
        if video_dates:
            print(f"  - Total vidéos dans DB: {video_dates[0]}")
            print(f"  - First date (COALESCE): {video_dates[1]}")
            print(f"  - Last date (COALESCE): {video_dates[2]}")
            print(f"  - YouTube dates count: {video_dates[3]}")
            print(f"  - Published dates count: {video_dates[4]}")
            print(f"  - YouTube NOT NULL: {video_dates[5]}")
            print(f"  - Published NOT NULL: {video_dates[6]}")
        else:
            print("  - NULL data returned")
    
    def _debug_sample_videos(self, competitor_id: int, channel_name: str) -> None:
        """Debug sample videos."""
        self.cursor.execute("""
            SELECT youtube_published_at, published_at, title
            FROM video v
            WHERE v.concurrent_id = ?
            ORDER BY COALESCE(v.youtube_published_at, v.published_at) DESC
            LIMIT 5
        """, (competitor_id,))
        sample_videos = self.cursor.fetchall()
        
        print(f"[DEBUG FREQUENCY] 🎬 Échantillon des 5 dernières vidéos pour {channel_name}:")
        for i, (yt_date, pub_date, title) in enumerate(sample_videos):
            print(f"  {i+1}. YouTube: '{yt_date}' | Published: '{pub_date}' | Title: '{title[:50]}...'")
    
    def _calculate_frequency_from_dates(self, video_dates: sqlite3.Row, channel_name: str) -> Optional[float]:
        """Calculate frequency from date data."""
        print(f"[DEBUG FREQUENCY] 🔍 Début calcul pour {channel_name}...")
        
        if not video_dates:
            print(f"[DEBUG FREQUENCY] ❌ {channel_name}: Aucune donnée retournée par la requête SQL")
            return None
        
        if not video_dates[0]:
            print(f"[DEBUG FREQUENCY] ❌ {channel_name}: Total vidéos = 0")
            return None
        
        if not video_dates[1] or not video_dates[2]:
            print(f"[DEBUG FREQUENCY] ❌ {channel_name}: Dates first/last manquantes - first: '{video_dates[1]}', last: '{video_dates[2]}'")
            return None
        
        total_videos = video_dates[0]
        first_date = video_dates[1]
        last_date = video_dates[2]
        youtube_dates_count = video_dates[3]
        
        print(f"[DEBUG FREQUENCY] 💾 {channel_name}: Données extraites - {total_videos} vidéos, première: '{first_date}', dernière: '{last_date}', YouTube dates: {youtube_dates_count}")
        
        # If no authentic YouTube dates, don't calculate (unreliable import data)
        if youtube_dates_count == 0:
            print(f"[DEBUG FREQUENCY] ⚠️ {channel_name}: Pas de dates YouTube authentiques ({youtube_dates_count}) - fréquence N/A")
            return None
        
        # Parse dates (YouTube ISO format with Z)
        try:
            print(f"[DEBUG FREQUENCY] 📅 {channel_name}: Tentative parsing des dates - first: '{first_date}' last: '{last_date}'")
            
            # Format YouTube ISO: 2012-09-27T11:57:27Z
            first_dt = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
            
            # Calculate time difference
            time_diff = last_dt - first_dt
            weeks_active = time_diff.days / 7.0
            
            if weeks_active <= 0:
                print(f"[DEBUG FREQUENCY] ⚠️ {channel_name}: Période active invalide ({weeks_active} semaines)")
                return None
            
            videos_per_week = total_videos / weeks_active
            print(f"[DEBUG FREQUENCY] ✅ {channel_name}: {videos_per_week:.2f} vidéos/semaine ({total_videos} vidéos sur {weeks_active:.1f} semaines)")
            
            return round(videos_per_week, 2)
            
        except Exception as e:
            print(f"[DEBUG FREQUENCY] ❌ {channel_name}: Erreur parsing dates - {e}")
            return None


class BrandInsightsService:
    """Main service orchestrating brand insights analysis."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.channel_service = BrandChannelService(db_connection)
        self.metrics_service = BrandMetricsService(db_connection)
        self.frequency_service = VideoFrequencyService(db_connection)
    
    def generate_brand_insights(self, brand_pattern: str = '%Center Parcs%') -> Dict[str, Any]:
        """Generate comprehensive brand insights."""
        print("[INSIGHTS] 🔍 Génération des brand insights pour les chaînes Center Parcs...")
        
        # Get all brand channels
        channels = self.channel_service.get_brand_channels(brand_pattern)
        
        if not channels:
            return {
                'success': False, 
                'error': 'Aucune chaîne Center Parcs trouvée en base de données'
            }
        
        # Analyze all brand channels
        all_brand_metrics = {}
        
        for channel in channels:
            competitor_id, name, channel_url, country = channel
            print(f"[INSIGHTS] 📊 Analyse de {name} (ID: {competitor_id}) - {country}")
            
            # Check if channel has content
            if not self.channel_service.validate_channel_content(competitor_id):
                all_brand_metrics[country] = {
                    'channel_name': name,
                    'country': country,
                    'has_content': False,
                    'message': 'Chaîne sans contenu (0 vidéos)'
                }
                continue
            
            # Analyze this channel
            print(f"[INSIGHTS] 🔍 Analyse des métriques pour {name}")
            
            # Get metrics
            basic_stats = self.metrics_service.calculate_basic_stats(competitor_id)
            category_distribution = self.metrics_service.calculate_category_distribution(competitor_id)
            video_frequency = self.frequency_service.calculate_video_frequency(competitor_id, name)
            
            # Store results
            all_brand_metrics[country] = self._format_channel_metrics(
                name, country, basic_stats, category_distribution, video_frequency
            )
        
        return self._format_final_insights(all_brand_metrics)
    
    def _format_channel_metrics(self, name: str, country: str, basic_stats: Dict[str, Any], 
                               category_dist: Dict[str, int], frequency: Optional[float]) -> Dict[str, Any]:
        """Format metrics for a single channel."""
        # Calculate derived metrics
        shorts_percentage = 0
        if basic_stats['total_videos'] > 0:
            shorts_percentage = round((basic_stats['shorts_count'] / basic_stats['total_videos']) * 100, 1)
        
        avg_duration_minutes = round(basic_stats['avg_duration'] / 60, 1) if basic_stats['avg_duration'] else 0
        
        return {
            'channel_name': name,
            'country': country,
            'has_content': True,
            'metrics': {
                'total_videos': basic_stats['total_videos'],
                'total_views': basic_stats['total_views'],
                'total_likes': basic_stats['total_likes'],
                'avg_views': round(basic_stats['avg_views']),
                'shorts_count': basic_stats['shorts_count'],
                'shorts_percentage': shorts_percentage,
                'avg_duration_minutes': avg_duration_minutes,
                'videos_per_week': frequency,
                'category_distribution': category_dist
            }
        }
    
    def _format_final_insights(self, all_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format final insights data structure."""
        # Calculate global statistics
        total_channels = len([m for m in all_metrics.values() if m.get('has_content', False)])
        
        # Prepare recommendations based on analysis
        recommendations = self._generate_recommendations(all_metrics)
        
        # Transform structure for template compatibility
        channels_data = {}
        
        for country, metrics in all_metrics.items():
            if metrics.get('has_content', False):
                # Create channel data in format expected by template
                channels_data[country] = {
                    'name': metrics['channel_name'],
                    'region': country,
                    'stats': {
                        'video_count': metrics['metrics']['total_videos'],
                        'total_views': metrics['metrics']['total_views'],
                        'avg_duration_minutes': metrics['metrics']['avg_duration_minutes']
                    }
                }
        
        return {
            'success': True,
            'channels_analyzed': total_channels,
            'channels': channels_data,  # Template expects this key
            'brand_metrics': all_metrics,  # Keep for backward compatibility
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on channel analysis."""
        recommendations = []
        
        # Analyze channels with content
        active_channels = [m for m in metrics.values() if m.get('has_content', False)]
        
        if not active_channels:
            recommendations.append("Aucune chaîne active trouvée - considérer l'import de contenu")
            return recommendations
        
        # Frequency analysis
        frequencies = [m['metrics']['videos_per_week'] for m in active_channels 
                      if m['metrics']['videos_per_week'] is not None]
        
        if frequencies:
            avg_frequency = sum(frequencies) / len(frequencies)
            if avg_frequency < 1:
                recommendations.append("Fréquence de publication faible - augmenter le rythme de publication")
            elif avg_frequency > 3:
                recommendations.append("Fréquence de publication élevée - maintenir la régularité")
        
        # Shorts analysis
        shorts_percentages = [m['metrics']['shorts_percentage'] for m in active_channels]
        avg_shorts = sum(shorts_percentages) / len(shorts_percentages) if shorts_percentages else 0
        
        if avg_shorts < 10:
            recommendations.append("Faible utilisation des Shorts - exploiter ce format pour plus de reach")
        elif avg_shorts > 50:
            recommendations.append("Fort usage des Shorts - équilibrer avec du contenu long format")
        
        return recommendations