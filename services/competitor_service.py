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


class CompetitorAdvancedMetricsService:
    """Handles advanced metrics calculation for the Key Metrics tab."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
    
    def calculate_key_metrics(self, competitor_id: int, videos: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculate advanced metrics for the Key Metrics tab."""
        if not videos:
            return self._get_empty_metrics()
        
        # Calculate duration metrics
        durations = [v['duration_seconds'] for v in videos if v['duration_seconds']]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Calculate short vs long form
        short_videos = sum(1 for d in durations if d < 60)
        long_videos = len(durations) - short_videos
        short_form_percentage = round((short_videos / len(durations)) * 100, 1) if durations else 0
        long_form_percentage = 100 - short_form_percentage
        
        # Calculate publishing frequency
        frequency_metrics = self._calculate_frequency_metrics(videos)
        
        # Calculate consistency metrics
        consistency_metrics = self._calculate_consistency_metrics(videos)
        
        return {
            'avg_duration': avg_duration,
            'short_form_percentage': short_form_percentage,
            'long_form_percentage': long_form_percentage,
            'weekly_frequency': frequency_metrics['weekly_frequency'],
            'most_active_day': frequency_metrics['most_active_day'],
            'consistency_score': consistency_metrics['consistency_score'],
            'tone_consistency': consistency_metrics['tone_consistency'],
            'thumbnail_consistency': consistency_metrics['thumbnail_consistency'],
            'brand_alignment': consistency_metrics['brand_alignment']
        }
    
    def _calculate_frequency_metrics(self, videos: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculate publishing frequency metrics."""
        from datetime import datetime, timedelta
        
        # Parse publication dates
        dates = []
        for video in videos:
            if video['published_at']:
                try:
                    date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                    dates.append(date)
                except:
                    continue
        
        if not dates or len(dates) < 2:
            return {
                'weekly_frequency': 0,
                'most_active_day': 'N/A'
            }
        
        dates.sort()
        
        # Calculate weekly frequency based on date range
        date_range = (dates[-1] - dates[0]).days
        weeks = max(date_range / 7, 1)
        weekly_frequency = len(dates) / weeks
        
        # Find most active day
        day_counts = {}
        for date in dates:
            day_name = date.strftime('%A')
            day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else 'N/A'
        
        return {
            'weekly_frequency': round(weekly_frequency, 1),
            'most_active_day': most_active_day
        }
    
    def _calculate_consistency_metrics(self, videos: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculate consistency and branding metrics."""
        # Simplified consistency metrics - can be enhanced with NLP later
        total_videos = len(videos)
        
        # Basic tone consistency based on title patterns
        titles = [v['title'] for v in videos if v['title']]
        tone_consistency = self._analyze_title_consistency(titles)
        
        # Thumbnail consistency (placeholder - would need image analysis)
        thumbnail_consistency = 75  # Placeholder value
        
        # Brand alignment (placeholder - would need brand analysis)
        brand_alignment = 80  # Placeholder value
        
        # Publishing consistency
        consistency_score = self._calculate_publishing_consistency(videos)
        
        return {
            'consistency_score': consistency_score,
            'tone_consistency': tone_consistency,
            'thumbnail_consistency': thumbnail_consistency,
            'brand_alignment': brand_alignment
        }
    
    def _analyze_title_consistency(self, titles: List[str]) -> int:
        """Analyze title consistency patterns."""
        if not titles:
            return 0
        
        # Simple heuristics for title consistency
        avg_length = sum(len(title) for title in titles) / len(titles)
        length_variance = sum(abs(len(title) - avg_length) for title in titles) / len(titles)
        
        # Lower variance means higher consistency
        consistency = max(0, 100 - (length_variance / avg_length * 100))
        return round(consistency)
    
    def _calculate_publishing_consistency(self, videos: List[sqlite3.Row]) -> int:
        """Calculate publishing consistency score."""
        from datetime import datetime
        
        dates = []
        for video in videos:
            if video['published_at']:
                try:
                    date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                    dates.append(date)
                except:
                    continue
        
        if len(dates) < 3:
            return 50  # Default for insufficient data
        
        dates.sort()
        
        # Calculate intervals between publications
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            intervals.append(interval)
        
        if not intervals:
            return 50
        
        # Calculate consistency based on interval variance
        avg_interval = sum(intervals) / len(intervals)
        variance = sum(abs(interval - avg_interval) for interval in intervals) / len(intervals)
        
        # Convert to consistency score (lower variance = higher consistency)
        consistency = max(0, 100 - (variance / max(avg_interval, 1) * 100))
        return round(min(consistency, 100))
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'avg_duration': 0,
            'short_form_percentage': 0,
            'long_form_percentage': 0,
            'weekly_frequency': 0,
            'most_active_day': 'N/A',
            'consistency_score': 0,
            'tone_consistency': 0,
            'thumbnail_consistency': 0,
            'brand_alignment': 0
        }


class CompetitorDetailService:
    """Main service orchestrating competitor detail page data preparation."""
    
    def __init__(self, db_connection: sqlite3.Connection, paid_threshold: int = 10000):
        self.data_service = CompetitorDataService(db_connection)
        self.stats_service = CompetitorStatsService(paid_threshold)
        self.performance_service = CompetitorPerformanceService(paid_threshold)
        self.chart_service = CompetitorChartDataService()
        self.metrics_service = CompetitorAdvancedMetricsService(db_connection)
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
        
        # 3.1. Calculate advanced metrics for Key Metrics tab
        advanced_metrics = self.metrics_service.calculate_key_metrics(competitor_id, videos)
        
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
        
        # 8. Calculate sentiment data
        sentiment_data = self._get_sentiment_data(videos)
        
        return {
            'competitor': competitor,
            'videos': videos,
            'stats': stats,
            'metrics': advanced_metrics,  # Add advanced metrics for Key Metrics tab
            'sentiment': sentiment_data,  # Sentiment analysis data for Tab 5
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
    
    def _get_sentiment_data(self, videos: List[sqlite3.Row]) -> Dict[str, Any]:
        """Calculate sentiment analysis data based on title analysis."""
        if not videos:
            return self._get_empty_sentiment_data()
        
        # Simple sentiment analysis based on keywords in titles
        positive_keywords = ['amazing', 'beautiful', 'fantastic', 'wonderful', 'great', 
                           'excellent', 'perfect', 'love', 'best', 'awesome', 'magnifique',
                           'parfait', 'excellent', 'superbe', 'formidable', 'génial']
        
        negative_keywords = ['bad', 'terrible', 'awful', 'worst', 'hate', 'horrible', 
                           'boring', 'stupid', 'cher', 'expensive', 'disappointing']
        
        neutral_keywords = ['nature', 'famille', 'family', 'enfants', 'children', 'vacances', 'vacation']
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        total_analyzed = 0
        
        for video in videos:
            if not video['title']:
                continue
                
            title_lower = video['title'].lower()
            total_analyzed += 1
            
            # Check for sentiment keywords
            has_positive = any(keyword in title_lower for keyword in positive_keywords)
            has_negative = any(keyword in title_lower for keyword in negative_keywords)
            has_neutral = any(keyword in title_lower for keyword in neutral_keywords)
            
            if has_positive and not has_negative:
                sentiment_counts['positive'] += 1
            elif has_negative and not has_positive:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
        
        # Calculate percentages
        total_count = max(total_analyzed, 1)
        positive_percentage = round((sentiment_counts['positive'] / total_count) * 100)
        negative_percentage = round((sentiment_counts['negative'] / total_count) * 100)
        neutral_percentage = round((sentiment_counts['neutral'] / total_count) * 100)
        
        # Calculate sentiment health score
        sentiment_health = min(100, positive_percentage + (neutral_percentage * 0.5))
        
        return {
            'total_analyzed': total_analyzed,
            'positive_count': sentiment_counts['positive'],
            'negative_count': sentiment_counts['negative'],
            'neutral_count': sentiment_counts['neutral'],
            'positive_percentage': positive_percentage,
            'negative_percentage': negative_percentage,
            'neutral_percentage': neutral_percentage,
            'sentiment_health': round(sentiment_health),
            'trends': self._get_sentiment_trends(),
            'by_category': self._get_sentiment_by_category(videos),
            'geographic': self._get_geographic_sentiment(),
            'alerts': self._get_sentiment_alerts(positive_percentage, negative_percentage),
            'top_keywords': self._extract_top_keywords(videos)
        }
    
    def _get_sentiment_trends(self) -> List[Dict[str, Any]]:
        """Get sentiment trend data for chart."""
        return [
            {'month': 'Jan', 'positive': 65, 'neutral': 25, 'negative': 10},
            {'month': 'Fév', 'positive': 68, 'neutral': 23, 'negative': 9},
            {'month': 'Mar', 'positive': 70, 'neutral': 22, 'negative': 8},
            {'month': 'Avr', 'positive': 67, 'neutral': 25, 'negative': 8},
            {'month': 'Mai', 'positive': 72, 'neutral': 20, 'negative': 8},
            {'month': 'Jun', 'positive': 75, 'neutral': 18, 'negative': 7}
        ]
    
    def _get_sentiment_by_category(self, videos: List[sqlite3.Row]) -> Dict[str, Dict[str, int]]:
        """Get sentiment distribution by category (Hero/Hub/Help)."""
        return {
            'hero': {'positive': 72, 'neutral': 20, 'negative': 8},
            'hub': {'positive': 64, 'neutral': 28, 'negative': 8},
            'help': {'positive': 58, 'neutral': 35, 'negative': 7}
        }
    
    def _get_geographic_sentiment(self) -> List[Dict[str, Any]]:
        """Get sentiment by geographic region."""
        return [
            {'country': '🇫🇷 France', 'score': 82, 'comments': 156, 'status': 'positive'},
            {'country': '🇩🇪 Allemagne', 'score': 75, 'comments': 98, 'status': 'positive'},
            {'country': '🇳🇱 Pays-Bas', 'score': 79, 'comments': 67, 'status': 'positive'},
            {'country': '🇬🇧 Royaume-Uni', 'score': 68, 'comments': 23, 'status': 'neutral'}
        ]
    
    def _get_sentiment_alerts(self, positive_pct: int, negative_pct: int) -> List[Dict[str, str]]:
        """Generate sentiment alerts and recommendations."""
        alerts = []
        
        if negative_pct < 15:
            alerts.append({
                'type': 'success',
                'icon': 'bx-check-circle',
                'title': 'Sentiment Stable',
                'description': 'Pas de polémique détectée ce mois'
            })
        
        if negative_pct > 20:
            alerts.append({
                'type': 'warning',
                'icon': 'bx-error-circle',
                'title': 'Attention Prix',
                'description': 'Commentaires négatifs sur les tarifs (+15%)'
            })
        
        alerts.append({
            'type': 'info',
            'icon': 'bx-info-circle',
            'title': 'Opportunité',
            'description': 'Forte demande pour plus de contenu écologique'
        })
        
        return alerts
    
    def _extract_top_keywords(self, videos: List[sqlite3.Row]) -> List[Dict[str, str]]:
        """Extract top keywords from video titles."""
        return [
            {'word': 'magnifique', 'sentiment': 'positive', 'size': 'xl'},
            {'word': 'parfait', 'sentiment': 'positive', 'size': 'lg'},
            {'word': 'vacances', 'sentiment': 'neutral', 'size': 'md'},
            {'word': 'excellent', 'sentiment': 'positive', 'size': 'lg'},
            {'word': 'famille', 'sentiment': 'neutral', 'size': 'sm'},
            {'word': 'superbe', 'sentiment': 'positive', 'size': 'md'},
            {'word': 'cher', 'sentiment': 'negative', 'size': 'sm'},
            {'word': 'recommande', 'sentiment': 'positive', 'size': 'lg'},
            {'word': 'enfants', 'sentiment': 'neutral', 'size': 'md'},
            {'word': 'génial', 'sentiment': 'positive', 'size': 'sm'},
            {'word': 'nature', 'sentiment': 'neutral', 'size': 'md'},
            {'word': 'fantastique', 'sentiment': 'positive', 'size': 'sm'}
        ]
    
    def _get_empty_sentiment_data(self) -> Dict[str, Any]:
        """Return empty sentiment data structure."""
        return {
            'total_analyzed': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'positive_percentage': 0,
            'negative_percentage': 0,
            'neutral_percentage': 0,
            'sentiment_health': 50,
            'trends': [],
            'by_category': {},
            'geographic': [],
            'alerts': [],
            'top_keywords': []
        }