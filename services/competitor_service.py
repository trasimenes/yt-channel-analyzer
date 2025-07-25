"""
Service layer for competitor-related business logic.
Extracted from monolithic app.py to improve maintainability and testability.
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sqlite3


class CompetitorDataService:
    """Handles competitor data retrieval and basic operations."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
    
    def get_competitor_by_id(self, competitor_id: int) -> Optional[sqlite3.Row]:
        """Get competitor data by ID."""
        return self.conn.execute(
            'SELECT * FROM concurrent WHERE id = ?', 
            (competitor_id,)
        ).fetchone()
    
    def get_competitor_videos(self, competitor_id: int) -> List[sqlite3.Row]:
        """Get all videos for a competitor, ordered by publication date."""
        return self.conn.execute(
            'SELECT * FROM video WHERE concurrent_id = ? ORDER BY published_at DESC',
            (competitor_id,)
        ).fetchall()
    
    def get_competitor_playlists(self, competitor_id: int) -> List[sqlite3.Row]:
        """Get playlists for a competitor."""
        from yt_channel_analyzer.database import get_competitor_playlists
        return get_competitor_playlists(competitor_id)
    
    def get_subscriber_data(self, competitor_id: int) -> List[sqlite3.Row]:
        """Get subscriber data for a competitor."""
        return self.conn.execute(
            'SELECT date, subscriber_count FROM subscriber_data WHERE concurrent_id = ? ORDER BY date',
            (competitor_id,)
        ).fetchall()


class CompetitorStatsService:
    """Handles competitor statistics calculations."""
    
    def __init__(self, paid_threshold: int = 10000):
        self.paid_threshold = paid_threshold
    
    def calculate_basic_stats(self, videos: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculate basic video statistics."""
        paid_count = sum(1 for v in videos if v['view_count'] and v['view_count'] >= self.paid_threshold)
        organic_count = len(videos) - paid_count
        
        stats = {
            'total_videos': len(videos),
            'total_views': sum(v['view_count'] for v in videos if v['view_count']),
            'total_likes': sum(v['like_count'] for v in videos if v['like_count']),
            'hero_count': sum(1 for v in videos if v['category'] == 'hero'),
            'hub_count': sum(1 for v in videos if v['category'] == 'hub'),
            'help_count': sum(1 for v in videos if v['category'] == 'help'),
            'uncategorized_count': sum(1 for v in videos if v['category'] is None or v['category'] == ''),
            'paid_count': paid_count,
            'organic_count': organic_count,
            'paid_threshold': self.paid_threshold,
        }
        
        # Calculate percentages
        if stats['total_videos'] > 0:
            stats['paid_percentage'] = round((stats['paid_count'] / stats['total_videos']) * 100)
            stats['organic_percentage'] = round((stats['organic_count'] / stats['total_videos']) * 100)
        else:
            stats['paid_percentage'] = 0
            stats['organic_percentage'] = 0
            
        return stats
    
    def calculate_shorts_metrics(self, videos: List[sqlite3.Row], competitor_id: int, db_connection: sqlite3.Connection) -> Dict[str, Any]:
        """Calculate YouTube Shorts specific metrics."""
        shorts_count = sum(1 for v in videos if v['is_short'] == 1)
        regular_videos_count = len(videos) - shorts_count
        shorts_views = sum(v['view_count'] for v in videos if v['is_short'] == 1 and v['view_count'])
        regular_views = sum(v['view_count'] for v in videos if v['is_short'] == 0 and v['view_count'])
        
        # Calculate metrics
        shorts_percentage = (shorts_count / len(videos) * 100) if len(videos) > 0 else 0
        avg_views_shorts = shorts_views / shorts_count if shorts_count > 0 else 0
        avg_views_regular = regular_views / regular_videos_count if regular_videos_count > 0 else 0
        performance_relative = (avg_views_shorts / avg_views_regular * 100) if avg_views_regular > 0 else 0
        
        # Get temporal data for frequency calculations
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT 
                MIN(youtube_published_at) as first_date,
                MAX(youtube_published_at) as last_date,
                COUNT(CASE WHEN is_short = 1 THEN 1 END) as shorts_count_db
            FROM video 
            WHERE concurrent_id = ? 
            AND youtube_published_at IS NOT NULL 
            AND youtube_published_at != ''
        """, (competitor_id,))
        
        temporal_data = cursor.fetchone()
        
        # Calculate frequency metrics
        if temporal_data and temporal_data[0] and temporal_data[1]:
            try:
                first_date = datetime.fromisoformat(temporal_data[0].replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(temporal_data[1].replace('Z', '+00:00'))
                days_active = (last_date - first_date).days + 1
                
                if days_active > 0:
                    shorts_per_week = round(shorts_count * 7 / days_active, 1)
                    shorts_per_month = round(shorts_count * 30.5 / days_active, 1)
                else:
                    shorts_per_week = 0
                    shorts_per_month = shorts_count
            except Exception:
                # Fallback if parsing fails
                shorts_per_week = 0
                shorts_per_month = shorts_count
        else:
            # No real dates, use reasonable estimates
            estimated_days = 730  # 2 years
            shorts_per_week = round(shorts_count * 7 / estimated_days, 1) if shorts_count > 0 else 0
            shorts_per_month = round(shorts_count * 30.5 / estimated_days, 1) if shorts_count > 0 else 0
        
        return {
            'shorts_percentage': round(shorts_percentage, 1),
            'shorts_count': shorts_count,
            'total_shorts_views': shorts_views,
            'avg_views_shorts': int(avg_views_shorts),
            'avg_views_regular': int(avg_views_regular),
            'performance_relative': round(performance_relative, 1) if performance_relative > 0 else 'N/A',
            'shorts_per_week': shorts_per_week,
            'shorts_per_month': shorts_per_month
        }


class CompetitorPerformanceService:
    """Handles competitor performance analysis."""
    
    def __init__(self, paid_threshold: int = 10000):
        self.paid_threshold = paid_threshold
    
    def calculate_performance_matrix(self, videos: List[sqlite3.Row]) -> Dict[str, Dict[str, Any]]:
        """Calculate performance matrix by category and type (organic/paid)."""
        performance_matrix = {
            'hero': {'organic': [], 'paid': []},
            'hub': {'organic': [], 'paid': []},
            'help': {'organic': [], 'paid': []}
        }
        
        # Fill matrix with video views
        for video in videos:
            if video['view_count'] is None:
                continue
                
            category = video['category'] or 'hub'  # Default to hub if no category
            views = video['view_count']
            
            if category in performance_matrix:
                if views >= self.paid_threshold:
                    performance_matrix[category]['paid'].append(views)
                else:
                    performance_matrix[category]['organic'].append(views)
        
        # Calculate medians for each cell
        performance_matrix_stats = {}
        for category in ['hero', 'hub', 'help']:
            performance_matrix_stats[category] = {
                'organic_median': self._calculate_median(performance_matrix[category]['organic']),
                'organic_count': len(performance_matrix[category]['organic']),
                'paid_median': self._calculate_median(performance_matrix[category]['paid']),
                'paid_count': len(performance_matrix[category]['paid'])
            }
        
        return performance_matrix_stats
    
    def get_top_videos(self, videos: List[sqlite3.Row], limit: int = 5) -> Tuple[List[sqlite3.Row], List[sqlite3.Row]]:
        """Get top videos by views and likes."""
        top_videos_views = sorted(
            [v for v in videos if v['view_count'] is not None], 
            key=lambda x: x['view_count'], 
            reverse=True
        )[:limit]
        
        top_videos_likes = sorted(
            [v for v in videos if v['like_count'] is not None], 
            key=lambda x: x['like_count'], 
            reverse=True
        )[:limit]
        
        return top_videos_views, top_videos_likes
    
    def _calculate_median(self, values: List[int]) -> int:
        """Calculate median of a list of values."""
        if not values:
            return 0
        values.sort()
        n = len(values)
        return values[n//2] if n % 2 == 1 else (values[n//2-1] + values[n//2]) // 2


class CompetitorChartDataService:
    """Handles chart data preparation for competitor visualization."""
    
    def prepare_top_videos_chart_data(self, top_videos: List[sqlite3.Row]) -> Dict[str, List]:
        """Prepare chart data for top videos visualization."""
        return {
            "labels": [v['title'] for v in top_videos],
            "views": [v['view_count'] for v in top_videos],
            "likes": [v['like_count'] for v in top_videos],
            "video_ids": [v['video_id'] for v in top_videos]
        }
    
    def prepare_performance_chart_data(self, stats: Dict[str, Any]) -> Dict[str, List]:
        """Prepare performance metrics chart data."""
        return {
            "labels": ["Vues", "Likes", "HERO", "HUB", "HELP"],
            "values": [
                stats['total_views'] / stats['total_videos'] if stats['total_videos'] > 0 else 0,
                stats['total_likes'] / stats['total_videos'] if stats['total_videos'] > 0 else 0,
                stats['hero_count'],
                stats['hub_count'],
                stats['help_count']
            ]
        }
    
    def prepare_category_distribution_data(self, stats: Dict[str, Any]) -> Dict[str, List]:
        """Prepare category distribution chart data."""
        return {
            "labels": ["HERO", "HUB", "HELP"],
            "values": [stats['hero_count'], stats['hub_count'], stats['help_count']]
        }
    
    def prepare_content_type_distribution_data(self, stats: Dict[str, Any]) -> Dict[str, List]:
        """Prepare content type distribution chart data."""
        return {
            "labels": ["Payé", "Organique"],
            "values": [stats['paid_count'], stats['organic_count']]
        }
    
    def prepare_engagement_metrics_data(self, top_videos: List[sqlite3.Row]) -> Dict[str, List]:
        """Prepare engagement metrics chart data."""
        return {
            "labels": [v['title'][:20] + '...' for v in top_videos],
            "values": [
                ((v['like_count'] or 0) / v['view_count']) * 100 
                if v['view_count'] and v['view_count'] > 0 else 0 
                for v in top_videos
            ]
        }
    
    def prepare_subscriber_chart_data(self, subscriber_data: List[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """Prepare subscriber growth chart data."""
        if not subscriber_data:
            return {
                'has_data': False,
                'chart_data': None,
                'stats': {
                    'total_entries': 0,
                    'total_growth': 0,
                    'growth_percentage': 0
                }
            }
        
        data_list = [{"date": r["date"], "subscriber_count": r["subscriber_count"]} for r in subscriber_data]
        
        # Calculate statistics
        first_entry = data_list[0]
        last_entry = data_list[-1]
        total_growth = last_entry['subscriber_count'] - first_entry['subscriber_count']
        growth_percentage = (total_growth / first_entry['subscriber_count']) * 100 if first_entry['subscriber_count'] > 0 else 0
        
        # Format data for Chart.js
        chart_data = {
            'labels': [entry['date'] for entry in data_list],
            'datasets': [{
                'label': 'Nombre d\'abonnés',
                'data': [entry['subscriber_count'] for entry in data_list],
                'borderColor': 'rgba(99, 102, 241, 1)',
                'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4,
                'pointBackgroundColor': 'rgba(99, 102, 241, 1)',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'pointRadius': 6,
                'pointHoverRadius': 8
            }]
        }
        
        return {
            'has_data': True,
            'chart_data': chart_data,
            'stats': {
                'total_entries': len(data_list),
                'first_date': first_entry['date'],
                'last_date': last_entry['date'],
                'first_count': first_entry['subscriber_count'],
                'last_count': last_entry['subscriber_count'],
                'total_growth': total_growth,
                'growth_percentage': round(growth_percentage, 2)
            }
        }


class CompetitorDetailService:
    """Main service orchestrating competitor detail page data preparation."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = 10000):
        self.data_service = CompetitorDataService(db_connection)
        self.stats_service = CompetitorStatsService(paid_threshold)
        self.performance_service = CompetitorPerformanceService(paid_threshold)
        self.chart_service = CompetitorChartDataService()
        self.db_connection = db_connection
    
    def get_competitor_detail_data(self, competitor_id: int) -> Dict[str, Any]:
        """Get all data needed for competitor detail page."""
        # 1. Get basic competitor data
        competitor = self.data_service.get_competitor_by_id(competitor_id)
        if not competitor:
            return None
        
        # 2. Get videos and related data
        videos = self.data_service.get_competitor_videos(competitor_id)
        playlists = self.data_service.get_competitor_playlists(competitor_id)
        subscriber_data = self.data_service.get_subscriber_data(competitor_id)
        
        # 3. Calculate statistics
        stats = self.stats_service.calculate_basic_stats(videos)
        shorts_data = self.stats_service.calculate_shorts_metrics(videos, competitor_id, self.db_connection)
        performance_matrix = self.performance_service.calculate_performance_matrix(videos)
        
        # 4. Get top videos
        top_videos_views, top_videos_likes = self.performance_service.get_top_videos(videos)
        
        # 5. Prepare chart data
        top_videos_json = self.chart_service.prepare_top_videos_chart_data(top_videos_views)
        performance_data = self.chart_service.prepare_performance_chart_data(stats)
        category_distribution = self.chart_service.prepare_category_distribution_data(stats)
        content_type_distribution = self.chart_service.prepare_content_type_distribution_data(stats)
        engagement_metrics = self.chart_service.prepare_engagement_metrics_data(top_videos_views)
        subscriber_data_formatted = self.chart_service.prepare_subscriber_chart_data(subscriber_data)
        
        # 6. Group videos by category
        videos_by_category = {
            'hero': [v for v in videos if v['category'] == 'hero'],
            'hub': [v for v in videos if v['category'] == 'hub'],
            'help': [v for v in videos if v['category'] == 'help'],
            'uncategorized': [v for v in videos if v['category'] is None or v['category'] == '']
        }
        
        # 7. Add performance matrix to stats
        stats['performance_matrix'] = performance_matrix
        
        return {
            'competitor': competitor,
            'videos': videos,
            'stats': stats,
            'top_videos_views': top_videos_views,
            'top_videos_likes': top_videos_likes,
            'top_videos_json': top_videos_json,
            'performance_data': performance_data,
            'category_distribution': category_distribution,
            'content_type_distribution': content_type_distribution,
            'engagement_metrics': engagement_metrics,
            'playlists': playlists,
            'subscriber_data': subscriber_data_formatted,
            'shorts_data': shorts_data,
            'videos_by_category': videos_by_category
        }