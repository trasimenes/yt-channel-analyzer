"""
Module d'analyse et d'insights.

Ce module contient toutes les fonctions liées aux analyses et insights :
- Analyses de performance
- Insights par pays
- Analyses de fréquence
- Analyses de Shorts
- Recommandations
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import re

from .base import get_db_connection


class CountryInsightsAnalyzer:
    """Analyseur d'insights par pays."""
    
    def generate_country_insights(self) -> Dict:
        """Générer des insights par pays pour tous les concurrents"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer tous les pays avec leurs statistiques
            cursor.execute('''
                SELECT 
                    c.country,
                    COUNT(DISTINCT c.id) as competitor_count,
                    COUNT(v.id) as total_videos,
                    AVG(v.view_count) as avg_views,
                    AVG(v.duration_seconds) as avg_duration,
                    SUM(v.view_count) as total_views
                FROM concurrent c
                LEFT JOIN video v ON c.id = v.concurrent_id
                WHERE c.country IS NOT NULL AND c.country != ''
                GROUP BY c.country
                HAVING competitor_count > 0
                ORDER BY total_views DESC
            ''')
            
            countries_data = cursor.fetchall()
            
            if not countries_data:
                return {
                    'success': False,
                    'error': 'Aucune donnée de pays disponible'
                }
            
            insights = {}
            
            for row in countries_data:
                country = row[0]
                competitor_count = row[1]
                total_videos = row[2] or 0
                avg_views = row[3] or 0
                avg_duration = row[4] or 0
                total_views = row[5] or 0
                
                # Générer des insights détaillés pour ce pays
                country_insights = self.generate_detailed_country_insights(country)
                
                insights[country] = {
                    'competitor_count': competitor_count,
                    'total_videos': total_videos,
                    'avg_views': int(avg_views),
                    'avg_duration_minutes': round(avg_duration / 60, 1) if avg_duration > 0 else 0,
                    'total_views': total_views,
                    'detailed_insights': country_insights
                }
            
            return {
                'success': True,
                'insights': insights,
                'total_countries': len(insights),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def generate_detailed_country_insights(self, target_country: str) -> Dict:
        """Générer des insights détaillés pour un pays spécifique"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer les données du pays
            cursor.execute('''
                SELECT 
                    v.id, v.title, v.description, v.view_count, v.like_count, 
                    v.comment_count, v.duration_seconds, v.category, v.published_at,
                    c.name as competitor_name, c.subscriber_count
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE c.country = ?
                ORDER BY v.view_count DESC
            ''', (target_country,))
            
            videos = cursor.fetchall()
            
            if not videos:
                return {
                    'success': False,
                    'error': f'Aucune vidéo trouvée pour le pays: {target_country}'
                }
            
            # Analyser les données
            all_videos = [dict(zip([desc[0] for desc in cursor.description], row)) for row in videos]
            top_videos = all_videos[:50]  # Top 50 vidéos
            
            # Analyses spécifiques
            duration_analysis = self._analyze_optimal_duration(top_videos, all_videos)
            timing_analysis = self._analyze_optimal_timing(top_videos)
            category_analysis = self._analyze_category_performance(top_videos, all_videos)
            engagement_analysis = self._analyze_engagement_patterns(top_videos)
            
            # Générer des recommandations
            recommendations = self._generate_country_recommendations(target_country, all_videos, top_videos)
            
            return {
                'success': True,
                'country': target_country,
                'total_videos': len(all_videos),
                'top_videos_analyzed': len(top_videos),
                'duration_analysis': duration_analysis,
                'timing_analysis': timing_analysis,
                'category_analysis': category_analysis,
                'engagement_analysis': engagement_analysis,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _analyze_optimal_duration(self, top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
        """Analyser la durée optimale des vidéos"""
        if not top_videos:
            return {'error': 'Pas de données disponibles'}
        
        # Calculer la durée moyenne des top vidéos
        top_durations = [v['duration_seconds'] for v in top_videos if v['duration_seconds'] and v['duration_seconds'] > 0]
        all_durations = [v['duration_seconds'] for v in all_videos if v['duration_seconds'] and v['duration_seconds'] > 0]
        
        if not top_durations:
            return {'error': 'Pas de données de durée disponibles'}
        
        avg_top_duration = sum(top_durations) / len(top_durations)
        avg_all_duration = sum(all_durations) / len(all_durations) if all_durations else 0
        
        # Analyser les segments de durée
        duration_segments = {
            'short': (0, 180),      # 0-3 min
            'medium': (180, 600),   # 3-10 min
            'long': (600, 1800),    # 10-30 min
            'very_long': (1800, float('inf'))  # 30+ min
        }
        
        segment_performance = {}
        for segment_name, (min_dur, max_dur) in duration_segments.items():
            segment_videos = [v for v in top_videos if v['duration_seconds'] and min_dur <= v['duration_seconds'] < max_dur]
            if segment_videos:
                avg_views = sum(v['view_count'] for v in segment_videos) / len(segment_videos)
                segment_performance[segment_name] = {
                    'count': len(segment_videos),
                    'avg_views': avg_views,
                    'percentage': (len(segment_videos) / len(top_videos)) * 100
                }
        
        # Trouver le segment optimal
        optimal_segment = max(segment_performance.items(), key=lambda x: x[1]['avg_views']) if segment_performance else None
        
        return {
            'avg_top_duration_minutes': round(avg_top_duration / 60, 1),
            'avg_all_duration_minutes': round(avg_all_duration / 60, 1),
            'optimal_segment': optimal_segment[0] if optimal_segment else None,
            'segment_performance': segment_performance,
            'recommendation': self._get_duration_recommendation(avg_top_duration, optimal_segment)
        }
    
    def _analyze_optimal_timing(self, top_videos: List[Dict]) -> Dict:
        """Analyser les meilleurs moments de publication"""
        if not top_videos:
            return {'error': 'Pas de données disponibles'}
        
        # Analyser les jours de la semaine et les heures
        weekday_performance = defaultdict(list)
        hour_performance = defaultdict(list)
        
        for video in top_videos:
            if video['published_at']:
                try:
                    pub_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                    weekday = pub_date.strftime('%A')
                    hour = pub_date.hour
                    
                    weekday_performance[weekday].append(video['view_count'])
                    hour_performance[hour].append(video['view_count'])
                except:
                    continue
        
        # Calculer les moyennes
        weekday_avg = {day: sum(views) / len(views) for day, views in weekday_performance.items()}
        hour_avg = {hour: sum(views) / len(views) for hour, views in hour_performance.items()}
        
        # Trouver les meilleurs moments
        best_weekday = max(weekday_avg.items(), key=lambda x: x[1]) if weekday_avg else None
        best_hour = max(hour_avg.items(), key=lambda x: x[1]) if hour_avg else None
        
        return {
            'best_weekday': best_weekday[0] if best_weekday else None,
            'best_weekday_avg_views': int(best_weekday[1]) if best_weekday else 0,
            'best_hour': best_hour[0] if best_hour else None,
            'best_hour_avg_views': int(best_hour[1]) if best_hour else 0,
            'weekday_performance': {k: int(v) for k, v in weekday_avg.items()},
            'hour_performance': {k: int(v) for k, v in hour_avg.items()}
        }
    
    def _analyze_category_performance(self, top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
        """Analyser les performances par catégorie"""
        if not top_videos:
            return {'error': 'Pas de données disponibles'}
        
        # Grouper par catégorie
        category_performance = defaultdict(list)
        for video in top_videos:
            category = video['category'] or 'uncategorized'
            category_performance[category].append(video['view_count'])
        
        # Calculer les moyennes
        category_avg = {cat: sum(views) / len(views) for cat, views in category_performance.items()}
        category_counts = {cat: len(views) for cat, views in category_performance.items()}
        
        # Trouver la meilleure catégorie
        best_category = max(category_avg.items(), key=lambda x: x[1]) if category_avg else None
        
        return {
            'best_category': best_category[0] if best_category else None,
            'best_category_avg_views': int(best_category[1]) if best_category else 0,
            'category_performance': {k: int(v) for k, v in category_avg.items()},
            'category_counts': category_counts
        }
    
    def _analyze_engagement_patterns(self, top_videos: List[Dict]) -> Dict:
        """Analyser les patterns d'engagement"""
        if not top_videos:
            return {'error': 'Pas de données disponibles'}
        
        # Calculer les taux d'engagement
        engagement_data = []
        for video in top_videos:
            if video['view_count'] and video['view_count'] > 0:
                like_rate = (video['like_count'] or 0) / video['view_count'] * 100
                comment_rate = (video['comment_count'] or 0) / video['view_count'] * 100
                
                engagement_data.append({
                    'like_rate': like_rate,
                    'comment_rate': comment_rate,
                    'total_engagement': like_rate + comment_rate
                })
        
        if not engagement_data:
            return {'error': 'Pas de données d\'engagement disponibles'}
        
        # Calculer les moyennes
        avg_like_rate = sum(d['like_rate'] for d in engagement_data) / len(engagement_data)
        avg_comment_rate = sum(d['comment_rate'] for d in engagement_data) / len(engagement_data)
        avg_total_engagement = sum(d['total_engagement'] for d in engagement_data) / len(engagement_data)
        
        return {
            'avg_like_rate': round(avg_like_rate, 3),
            'avg_comment_rate': round(avg_comment_rate, 3),
            'avg_total_engagement': round(avg_total_engagement, 3),
            'engagement_benchmark': self._get_engagement_benchmark(avg_total_engagement)
        }
    
    def _generate_country_recommendations(self, country: str, all_videos: List[Dict], top_videos: List[Dict]) -> List[str]:
        """Générer des recommandations spécifiques au pays"""
        recommendations = []
        
        # Analyser les performances
        if top_videos:
            avg_top_views = sum(v['view_count'] for v in top_videos) / len(top_videos)
            avg_all_views = sum(v['view_count'] for v in all_videos) / len(all_videos)
            
            performance_ratio = avg_top_views / avg_all_views if avg_all_views > 0 else 1
            
            if performance_ratio > 5:
                recommendations.append(f"📈 Excellente performance en {country}: les top vidéos génèrent {performance_ratio:.1f}x plus de vues que la moyenne")
            elif performance_ratio > 2:
                recommendations.append(f"📊 Bonne performance en {country}: potentiel d'amélioration identifié")
            else:
                recommendations.append(f"⚠️ Performance modérée en {country}: optimisation nécessaire")
        
        # Recommandations spécifiques par pays
        country_specific = {
            'France': [
                "🇫🇷 Privilégiez le contenu en français authentique",
                "🎯 Ciblez les audiences locales avec des références culturelles",
                "📱 Optimisez pour les habitudes de consommation françaises"
            ],
            'Germany': [
                "🇩🇪 Développez le contenu en allemand",
                "🔧 Mettez l'accent sur la qualité et la précision",
                "📊 Utilisez des données et des faits dans vos contenus"
            ],
            'United Kingdom': [
                "🇬🇧 Créez du contenu humoristique et divertissant",
                "🎬 Exploitez les formats courts et dynamiques",
                "🌍 Profitez de l'audience internationale anglophone"
            ]
        }
        
        if country in country_specific:
            recommendations.extend(country_specific[country])
        
        return recommendations
    
    def _get_duration_recommendation(self, avg_duration: float, optimal_segment: Optional[Tuple]) -> str:
        """Obtenir une recommandation sur la durée"""
        minutes = avg_duration / 60
        
        if optimal_segment:
            segment_name = optimal_segment[0]
            if segment_name == 'short':
                return f"Privilégiez les formats courts (3-5 min) pour maximiser l'engagement"
            elif segment_name == 'medium':
                return f"Les formats moyens (5-10 min) performent bien dans votre secteur"
            elif segment_name == 'long':
                return f"Le contenu long (10-30 min) génère de bons résultats"
            else:
                return f"Le contenu très long (30+ min) fonctionne pour votre audience"
        
        return f"Durée moyenne optimale: {minutes:.1f} minutes"
    
    def _get_engagement_benchmark(self, engagement_rate: float) -> str:
        """Obtenir un benchmark d'engagement"""
        if engagement_rate > 5:
            return "Excellent engagement"
        elif engagement_rate > 2:
            return "Bon engagement"
        elif engagement_rate > 1:
            return "Engagement modéré"
        else:
            return "Faible engagement"


class FrequencyAnalyzer:
    """Analyseur de fréquence de publication."""
    
    def calculate_publication_frequency(self, competitor_id: int = None, 
                                       start_date: datetime = None, 
                                       end_date: datetime = None) -> Dict:
        """Calculer la fréquence de publication"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Construire la requête avec youtube_published_at
            base_query = '''
                SELECT 
                    c.name, c.id, v.published_at, v.category, v.view_count,
                    v.like_count, v.comment_count, v.duration_seconds, v.youtube_published_at
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.published_at IS NOT NULL
            '''
            
            params = []
            
            if competitor_id:
                base_query += ' AND c.id = ?'
                params.append(competitor_id)
            
            if start_date:
                base_query += ' AND COALESCE(v.youtube_published_at, v.published_at) >= ?'
                params.append(start_date)
            
            if end_date:
                base_query += ' AND COALESCE(v.youtube_published_at, v.published_at) <= ?'
                params.append(end_date)
            
            base_query += ' ORDER BY COALESCE(v.youtube_published_at, v.published_at) DESC'
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            if not results:
                return {
                    'success': False,
                    'error': 'Aucune donnée de publication trouvée'
                }
            
            # Analyser la fréquence
            frequency_data = self._analyze_frequency_data(results)
            
            return {
                'success': True,
                'frequency_data': frequency_data,
                'total_videos': len(results),
                'analyzed_period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _analyze_frequency_data(self, results: List[Tuple]) -> Dict:
        """Analyser les données de fréquence"""
        # Grouper par concurrent et par semaine
        competitor_frequency = defaultdict(lambda: defaultdict(int))
        competitor_category_frequency = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        for row in results:
            competitor_name = row[0]
            competitor_id = row[1]
            published_at = row[2]
            category = row[3] or 'unknown'  # HERO/HUB/HELP
            
            try:
                # Utiliser la vraie date de publication YouTube si disponible
                # Sinon se rabattre sur la date de scraping
                if len(row) > 8 and row[8]:  # youtube_published_at existe à l'index 8
                    pub_date = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                else:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                
                # Calculer la clé de semaine de manière plus robuste
                # Utiliser le lundi comme début de semaine
                week_start = pub_date - timedelta(days=pub_date.weekday())
                week_key = week_start.strftime('%Y-W%U')
                
                # Compter pour le total et par catégorie
                competitor_frequency[competitor_name][week_key] += 1
                competitor_category_frequency[competitor_name][category][week_key] += 1
                
            except Exception as e:
                # Si parsing échoue, ignorer cette vidéo
                continue
        
        # Calculer les statistiques
        frequency_stats = {}
        for competitor_name, weekly_data in competitor_frequency.items():
            videos_per_week = list(weekly_data.values())
            
            if videos_per_week:
                # Calculer les fréquences par catégorie
                category_frequencies = {}
                for category in ['hero', 'hub', 'help']:
                    category_weekly_data = competitor_category_frequency[competitor_name].get(category, {})
                    if category_weekly_data:
                        category_videos_per_week = list(category_weekly_data.values())
                        # Moyenner sur toutes les semaines (même celles sans vidéos de cette catégorie)
                        total_category_videos = sum(category_videos_per_week)
                        total_weeks = len(weekly_data)  # Utiliser le nombre total de semaines actives
                        category_frequencies[category] = round(total_category_videos / total_weeks, 1) if total_weeks > 0 else 0.0
                    else:
                        category_frequencies[category] = 0.0
                
                frequency_stats[competitor_name] = {
                    'avg_videos_per_week': round(sum(videos_per_week) / len(videos_per_week), 1),
                    'max_videos_per_week': max(videos_per_week),
                    'min_videos_per_week': min(videos_per_week),
                    'total_weeks': len(videos_per_week),
                    'total_videos': sum(videos_per_week),
                    'consistency_score': self._calculate_consistency_score(videos_per_week),
                    # Ajout des fréquences par catégorie
                    'hero_frequency': category_frequencies['hero'],
                    'hub_frequency': category_frequencies['hub'],
                    'help_frequency': category_frequencies['help']
                }
        
        return frequency_stats
    
    def _calculate_consistency_score(self, videos_per_week: List[int]) -> float:
        """Calculer un score de consistance de publication"""
        if len(videos_per_week) < 2:
            return 0.0
        
        # Calculer la variation
        avg = sum(videos_per_week) / len(videos_per_week)
        variance = sum((x - avg) ** 2 for x in videos_per_week) / len(videos_per_week)
        
        # Score de consistance inversé (plus la variance est faible, plus le score est élevé)
        consistency_score = max(0, 100 - (variance / avg * 100)) if avg > 0 else 0
        
        return round(consistency_score, 1)


class ShortsAnalyzer:
    """Analyseur de Shorts YouTube."""
    
    def analyze_shorts_vs_regular_videos(self, competitor_id: int = None) -> Dict:
        """Analyser les Shorts vs vidéos régulières"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Requête pour les Shorts et vidéos régulières
            base_query = '''
                SELECT 
                    v.is_short, v.view_count, v.like_count, v.comment_count,
                    v.duration_seconds, v.published_at, c.name as competitor_name
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.view_count IS NOT NULL
            '''
            
            params = []
            if competitor_id:
                base_query += ' AND c.id = ?'
                params.append(competitor_id)
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            if not results:
                return {
                    'success': False,
                    'error': 'Aucune donnée vidéo trouvée'
                }
            
            # Séparer les Shorts et vidéos régulières
            shorts = [row for row in results if row[0] == 1]
            regular_videos = [row for row in results if row[0] == 0]
            
            # Analyser les performances
            shorts_analysis = self._analyze_video_group(shorts, "Shorts")
            regular_analysis = self._analyze_video_group(regular_videos, "Vidéos régulières")
            
            # Comparaison
            comparison = self._compare_video_groups(shorts_analysis, regular_analysis)
            
            return {
                'success': True,
                'shorts_analysis': shorts_analysis,
                'regular_analysis': regular_analysis,
                'comparison': comparison,
                'total_videos': len(results),
                'shorts_count': len(shorts),
                'regular_count': len(regular_videos)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _analyze_video_group(self, videos: List[Tuple], group_name: str) -> Dict:
        """Analyser un groupe de vidéos"""
        if not videos:
            return {
                'count': 0,
                'avg_views': 0,
                'avg_likes': 0,
                'avg_comments': 0,
                'avg_duration': 0,
                'total_views': 0
            }
        
        total_views = sum(v[1] for v in videos if v[1])
        total_likes = sum(v[2] for v in videos if v[2])
        total_comments = sum(v[3] for v in videos if v[3])
        total_duration = sum(v[4] for v in videos if v[4])
        
        return {
            'count': len(videos),
            'avg_views': round(total_views / len(videos)),
            'avg_likes': round(total_likes / len(videos)),
            'avg_comments': round(total_comments / len(videos)),
            'avg_duration': round(total_duration / len(videos)),
            'total_views': total_views,
            'engagement_rate': round((total_likes + total_comments) / total_views * 100, 3) if total_views > 0 else 0
        }
    
    def _compare_video_groups(self, shorts: Dict, regular: Dict) -> Dict:
        """Comparer deux groupes de vidéos"""
        comparison = {}
        
        if shorts['count'] > 0 and regular['count'] > 0:
            comparison['views_ratio'] = round(shorts['avg_views'] / regular['avg_views'], 2) if regular['avg_views'] > 0 else 0
            comparison['engagement_ratio'] = round(shorts['engagement_rate'] / regular['engagement_rate'], 2) if regular['engagement_rate'] > 0 else 0
            
            if comparison['views_ratio'] > 1.2:
                comparison['recommendation'] = "Les Shorts performent mieux que les vidéos régulières"
            elif comparison['views_ratio'] < 0.8:
                comparison['recommendation'] = "Les vidéos régulières performent mieux que les Shorts"
            else:
                comparison['recommendation'] = "Performance équivalente entre Shorts et vidéos régulières"
        
        return comparison


class CenterParcsInsightsAnalyzer:
    """Analyseur d'insights spécifiques à Center Parcs."""
    
    def generate_center_parcs_insights(self) -> Dict:
        """Générer des conseils spécifiques pour les chaînes Center Parcs"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Identifier les chaînes Center Parcs
            cursor.execute('''
                SELECT 
                    c.id, c.name, c.country, c.channel_url, c.subscriber_count,
                    c.view_count, c.video_count, c.thumbnail_url,
                    COUNT(v.id) as actual_video_count,
                    SUM(v.view_count) as total_views,
                    AVG(v.view_count) as avg_views,
                    AVG(v.duration_seconds) as avg_duration,
                    SUM(CASE WHEN v.category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                    SUM(CASE WHEN v.category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                    SUM(CASE WHEN v.category = 'help' THEN 1 ELSE 0 END) as help_count
                FROM concurrent c
                LEFT JOIN video v ON c.id = v.concurrent_id
                WHERE c.name LIKE '%Center Parcs%' 
                   OR c.name LIKE '%centerparcs%'
                   OR c.channel_url LIKE '%CenterParcs%'
                   OR c.channel_url LIKE '%centerparcs%'
                GROUP BY c.id
                ORDER BY actual_video_count DESC
            ''')
            
            results = cursor.fetchall()
            
            if not results:
                return {
                    'success': False,
                    'error': 'Aucune chaîne Center Parcs trouvée'
                }
            
            # Analyser chaque chaîne
            channels_insights = {}
            for row in results:
                channel_insights = self._analyze_center_parcs_channel(cursor, row)
                if channel_insights:
                    region_key = channel_insights.get('region_key', 'international')
                    channels_insights[region_key] = channel_insights
            
            return {
                'success': True,
                'channels': channels_insights,
                'total_channels': len(channels_insights),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _analyze_center_parcs_channel(self, cursor, channel_data: Tuple) -> Dict:
        """Analyser une chaîne Center Parcs spécifique"""
        # Extraire les données
        competitor_id, name, country, channel_url = channel_data[0], channel_data[1], channel_data[2], channel_data[3]
        subscriber_count, view_count, video_count = channel_data[4], channel_data[5], channel_data[6]
        thumbnail_url, actual_video_count = channel_data[7], channel_data[8]
        total_views, avg_views, avg_duration = channel_data[9], channel_data[10], channel_data[11]
        hero_count, hub_count, help_count = channel_data[12], channel_data[13], channel_data[14]
        
        # Déterminer la région
        region_key, region = self._determine_region(name, channel_url, country)
        
        # Calculer les ratios
        total_categorized = hero_count + hub_count + help_count
        hero_ratio = (hero_count / total_categorized * 100) if total_categorized > 0 else 0
        hub_ratio = (hub_count / total_categorized * 100) if total_categorized > 0 else 0
        help_ratio = (help_count / total_categorized * 100) if total_categorized > 0 else 0
        
        # Récupérer les vidéos top et flop
        top_videos = self._get_top_videos(cursor, competitor_id)
        bottom_videos = self._get_bottom_videos(cursor, competitor_id)
        
        # Générer les conseils
        sector_benchmarks = self._get_sector_benchmarks_for_region(region_key)
        advice = self._generate_center_parcs_advice(
            top_videos, bottom_videos, sector_benchmarks, region_key,
            avg_duration, hero_ratio, hub_ratio, help_ratio, avg_views
        )
        
        return {
            'name': name,
            'region': region,
            'region_key': region_key,
            'channel_url': channel_url,
            'thumbnail_url': thumbnail_url,
            'stats': {
                'subscriber_count': subscriber_count or 0,
                'video_count': actual_video_count or 0,
                'total_views': total_views or 0,
                'avg_views': int(avg_views) if avg_views else 0,
                'avg_duration_minutes': round(avg_duration / 60, 1) if avg_duration and avg_duration > 0 else 0
            },
            'content_distribution': {
                'hero_count': hero_count or 0,
                'hub_count': hub_count or 0,
                'help_count': help_count or 0,
                'hero_ratio': round(hero_ratio, 1),
                'hub_ratio': round(hub_ratio, 1),
                'help_ratio': round(help_ratio, 1),
                'total_categorized': total_categorized
            },
            'advice': advice
        }
    
    def _determine_region(self, name: str, channel_url: str, country: str) -> Tuple[str, str]:
        """Déterminer la région d'une chaîne Center Parcs"""
        name = name or ""
        channel_url = channel_url or ""
        country = country or ""
        
        if 'France' in name or 'France' in channel_url:
            return 'france', 'France'
        elif any(term in name or term in channel_url for term in ['Belgi', 'Belgium', 'Nederland', 'NLBE', 'NL']) or \
             country.lower() in ['netherlands', 'belgium', 'nl', 'be']:
            return 'belgium_netherlands', 'Belgique/Pays-Bas'
        elif any(term in name or term in channel_url for term in ['Deutschland', 'Germany', 'DE', '@CenterParcsDE']) or \
             country.lower() in ['germany', 'deutschland', 'de']:
            return 'germany', 'Allemagne'
        else:
            return 'international', 'International'
    
    def _get_top_videos(self, cursor, competitor_id: int) -> List[Tuple]:
        """Récupérer les vidéos les plus performantes"""
        cursor.execute('''
            SELECT title, view_count, category, published_at, duration_seconds, like_count, comment_count
            FROM video
            WHERE concurrent_id = ?
            ORDER BY view_count DESC
            LIMIT 10
        ''', (competitor_id,))
        return cursor.fetchall()
    
    def _get_bottom_videos(self, cursor, competitor_id: int) -> List[Tuple]:
        """Récupérer les vidéos les moins performantes"""
        cursor.execute('''
            SELECT title, view_count, category, published_at, duration_seconds, like_count, comment_count
            FROM video
            WHERE concurrent_id = ? AND view_count > 0
            ORDER BY view_count ASC
            LIMIT 10
        ''', (competitor_id,))
        return cursor.fetchall()
    
    def _get_sector_benchmarks_for_region(self, region_key: str) -> Dict:
        """Récupérer les benchmarks sectoriels pour une région"""
        benchmarks = {
            'germany': {
                'hero_ratio_benchmark': 15,
                'hub_ratio_benchmark': 60,
                'help_ratio_benchmark': 25,
                'avg_views_benchmark': 8000,
                'engagement_topics': ['outdoor', 'sport', 'familie', 'natur', 'wellness'],
                'low_engagement_topics': ['hund', 'haustier', 'politik', 'wetter']
            },
            'france': {
                'hero_ratio_benchmark': 20,
                'hub_ratio_benchmark': 50,
                'help_ratio_benchmark': 30,
                'avg_views_benchmark': 6000,
                'engagement_topics': ['famille', 'gastronomie', 'nature', 'détente', 'vacances'],
                'low_engagement_topics': ['animaux', 'politique', 'météo']
            },
            'belgium_netherlands': {
                'hero_ratio_benchmark': 18,
                'hub_ratio_benchmark': 55,
                'help_ratio_benchmark': 27,
                'avg_views_benchmark': 7000,
                'engagement_topics': ['aqua mundo', 'natuur', 'familie', 'fiets', 'cottage'],
                'low_engagement_topics': ['weer', 'dieren', 'politiek']
            },
            'international': {
                'hero_ratio_benchmark': 15,
                'hub_ratio_benchmark': 60,
                'help_ratio_benchmark': 25,
                'avg_views_benchmark': 5000,
                'engagement_topics': ['family', 'nature', 'vacation', 'outdoor', 'wellness'],
                'low_engagement_topics': ['weather', 'pets', 'politics']
            }
        }
        
        return benchmarks.get(region_key, benchmarks['international'])
    
    def _generate_center_parcs_advice(self, top_videos, bottom_videos, benchmarks, region_key, 
                                    avg_duration, hero_ratio, hub_ratio, help_ratio, avg_views) -> List[str]:
        """Générer des conseils personnalisés"""
        advice = []
        
        # Conseils régionaux spécifiques
        regional_advice = {
            'france': [
                "🇫🇷 Mettre en avant les spécificités françaises : terroir, gastronomie locale",
                "🏞️ Valoriser les activités nature et bien-être typiques",
                "👨‍👩‍👧‍👦 Créer du contenu famille multigénérationnel"
            ],
            'belgium_netherlands': [
                "🇧🇪🇳🇱 Capitaliser sur la notoriété historique de Center Parcs",
                "🌲 Mettre en avant l'authenticité et la proximité avec la nature",
                "🏊‍♀️ Valoriser l'Aqua Mundo comme signature unique"
            ],
            'germany': [
                "🇩🇪 Développer le contenu en allemand authentique",
                "🏕️ Mettre en avant les activités outdoor et sportives",
                "🎯 Cibler les familles actives et les groupes d'amis"
            ],
            'international': [
                "🌍 Créer du contenu universel compréhensible internationalement",
                "🏖️ Mettre en avant les destinations iconiques"
            ]
        }
        
        # Ajouter les conseils régionaux
        advice.extend(regional_advice.get(region_key, []))
        
        # Conseils généraux
        advice.extend([
            "📱 Optimiser pour mobile : 70% du trafic YouTube",
            "🎬 Créer des vignettes attractives et cohérentes",
            "📅 Publier régulièrement : 2-3 vidéos par semaine idéalement"
        ])
        
        return advice


# Instances globales des analyseurs
country_insights_analyzer = CountryInsightsAnalyzer()
frequency_analyzer = FrequencyAnalyzer()
shorts_analyzer = ShortsAnalyzer()
center_parcs_analyzer = CenterParcsInsightsAnalyzer()

# Fonctions de compatibilité
generate_country_insights = country_insights_analyzer.generate_country_insights
generate_detailed_country_insights = country_insights_analyzer.generate_detailed_country_insights
calculate_publication_frequency = frequency_analyzer.calculate_publication_frequency
analyze_shorts_vs_regular_videos = shorts_analyzer.analyze_shorts_vs_regular_videos
generate_center_parcs_insights = center_parcs_analyzer.generate_center_parcs_insights

def get_country_insights(country):
    """Récupérer les insights pour un pays donné"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mapper le pays
        country_mapping = {
            'France': 'FR',
            'Germany': 'DE',
            'Belgium': 'BE',
            'Netherlands': 'NL',
            'International': 'INT'
        }
        
        country_code = country_mapping.get(country, country)
        
        insights = {
            'country': country,
            'country_code': country_code,
            'metrics': {}
        }
        
        # 1. Top catégories par engagement
        cursor.execute("""
            SELECT 
                v.category,
                COUNT(*) as video_count,
                AVG((v.like_count + v.comment_count) * 1.0 / NULLIF(v.view_count, 0)) as avg_engagement_rate,
                SUM(v.view_count) as total_views
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ?
            AND v.category IS NOT NULL
            AND v.view_count > 0
            GROUP BY v.category
            ORDER BY avg_engagement_rate DESC
            LIMIT 5
        """, (country_code,))
        
        insights['metrics']['top_categories'] = [
            {
                'category': row[0],
                'video_count': row[1],
                'avg_engagement_rate': round(row[2] * 100, 2) if row[2] else 0,
                'total_views': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # 2. Durée optimale des vidéos
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN duration_seconds < 60 THEN '< 1 min'
                    WHEN duration_seconds < 300 THEN '1-5 min'
                    WHEN duration_seconds < 600 THEN '5-10 min'
                    WHEN duration_seconds < 1200 THEN '10-20 min'
                    ELSE '> 20 min'
                END as duration_range,
                AVG((like_count + comment_count) * 1.0 / NULLIF(view_count, 0)) as avg_engagement_rate,
                COUNT(*) as video_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ?
            AND v.view_count > 0
            AND v.duration_seconds > 0
            GROUP BY duration_range
            ORDER BY avg_engagement_rate DESC
        """, (country_code,))
        
        insights['metrics']['optimal_duration'] = [
            {
                'duration_range': row[0],
                'avg_engagement_rate': round(row[1] * 100, 2) if row[1] else 0,
                'video_count': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # 3. Meilleurs jours de publication
        cursor.execute("""
            SELECT 
                CASE cast(strftime('%w', published_at) as integer)
                    WHEN 0 THEN 'Dimanche'
                    WHEN 1 THEN 'Lundi'
                    WHEN 2 THEN 'Mardi'
                    WHEN 3 THEN 'Mercredi'
                    WHEN 4 THEN 'Jeudi'
                    WHEN 5 THEN 'Vendredi'
                    WHEN 6 THEN 'Samedi'
                END as day_of_week,
                AVG(view_count) as avg_views,
                COUNT(*) as video_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ?
            AND v.published_at IS NOT NULL
            GROUP BY day_of_week
            ORDER BY avg_views DESC
        """, (country_code,))
        
        insights['metrics']['best_days'] = [
            {
                'day': row[0],
                'avg_views': int(row[1]) if row[1] else 0,
                'video_count': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # 4. Shorts vs Regular performance
        cursor.execute("""
            SELECT 
                CASE WHEN is_short = 1 THEN 'Shorts' ELSE 'Regular' END as video_type,
                COUNT(*) as count,
                AVG(view_count) as avg_views,
                AVG((like_count + comment_count) * 1.0 / NULLIF(view_count, 0)) as avg_engagement_rate
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE c.country = ?
            AND v.view_count > 0
            GROUP BY is_short
        """, (country_code,))
        
        insights['metrics']['video_types'] = [
            {
                'type': row[0],
                'count': row[1],
                'avg_views': int(row[2]) if row[2] else 0,
                'avg_engagement_rate': round(row[3] * 100, 2) if row[3] else 0
            }
            for row in cursor.fetchall()
        ]
        
        # 5. Top performing competitors
        cursor.execute("""
            SELECT 
                c.name,
                COUNT(v.id) as video_count,
                SUM(v.view_count) as total_views,
                AVG((v.like_count + v.comment_count) * 1.0 / NULLIF(v.view_count, 0)) as avg_engagement_rate
            FROM concurrent c
            JOIN video v ON c.id = v.concurrent_id
            WHERE c.country = ?
            AND v.view_count > 0
            GROUP BY c.id
            ORDER BY avg_engagement_rate DESC
            LIMIT 3
        """, (country_code,))
        
        insights['metrics']['top_competitors'] = [
            {
                'name': row[0],
                'video_count': row[1],
                'total_views': row[2],
                'avg_engagement_rate': round(row[3] * 100, 2) if row[3] else 0
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return insights
        
    except Exception as e:
        print(f"Erreur lors de la récupération des insights pour {country}: {e}")
        return {
            'country': country,
            'country_code': country,
            'metrics': {},
            'error': str(e)
        } 