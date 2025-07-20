"""
Competitor service implementation - Following SRP and DIP
Single responsibility: Business logic for competitors
Depends on abstractions (repositories)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..core.interfaces.repository import CompetitorRepository, VideoRepository, PlaylistRepository, AnalyticsRepository
from ..core.interfaces.services import CompetitorService, ValidationService, CacheService
from ..core.models import Competitor, CompetitorMetrics, CompetitorStatus


class CompetitorServiceImpl(CompetitorService):
    """
    Implémentation du service de gestion des concurrents
    Suit le principe SRP: logique métier des concurrents uniquement
    Suit le principe DIP: dépend d'abstractions, pas de concrets
    """
    
    def __init__(
        self,
        competitor_repo: CompetitorRepository,
        video_repo: VideoRepository,
        playlist_repo: PlaylistRepository,
        analytics_repo: AnalyticsRepository,
        validation_service: ValidationService,
        cache_service: CacheService,
        logger: logging.Logger = None
    ):
        self.competitor_repo = competitor_repo
        self.video_repo = video_repo
        self.playlist_repo = playlist_repo
        self.analytics_repo = analytics_repo
        self.validation_service = validation_service
        self.cache_service = cache_service
        self.logger = logger or logging.getLogger(__name__)
    
    def get_competitor_details(self, competitor_id: int) -> Optional[Competitor]:
        """Récupérer les détails complets d'un concurrent"""
        try:
            # Essayer le cache d'abord
            cache_key = f"competitor_details_{competitor_id}"
            cached_data = self.cache_service.get_cached_analytics(cache_key)
            
            if cached_data:
                return Competitor.from_dict(cached_data)
            
            # Récupérer depuis la base
            competitor = self.competitor_repo.get_by_id(competitor_id)
            if not competitor:
                return None
            
            # Enrichir avec les métriques calculées
            competitor = self._enrich_with_metrics(competitor)
            
            # Mettre en cache
            self.cache_service.cache_analytics(cache_key, competitor.to_dict(), ttl=300)
            
            return competitor
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du concurrent {competitor_id}: {e}")
            return None
    
    def create_competitor(self, competitor_data: Dict[str, Any]) -> Competitor:
        """Créer un nouveau concurrent"""
        try:
            # Valider les données
            competitor = Competitor.from_dict(competitor_data)
            validation_errors = self.validation_service.validate_competitor_data(competitor)
            
            if validation_errors:
                raise ValueError(f"Données invalides: {'; '.join(validation_errors)}")
            
            # Vérifier les doublons
            existing = self.competitor_repo.get_by_channel_id(competitor.channel_id)
            if existing:
                raise ValueError(f"Concurrent déjà existant avec le channel_id: {competitor.channel_id}")
            
            # Sauvegarder
            saved_competitor = self.competitor_repo.save(competitor)
            
            # Invalider le cache
            self.cache_service.invalidate_competitor_cache(saved_competitor.id)
            
            self.logger.info(f"Concurrent créé: {saved_competitor.name} (ID: {saved_competitor.id})")
            return saved_competitor
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du concurrent: {e}")
            raise
    
    def update_competitor(self, competitor_id: int, updates: Dict[str, Any]) -> Competitor:
        """Mettre à jour un concurrent"""
        try:
            competitor = self.competitor_repo.get_by_id(competitor_id)
            if not competitor:
                raise ValueError(f"Concurrent non trouvé: {competitor_id}")
            
            # Appliquer les mises à jour
            for key, value in updates.items():
                if hasattr(competitor, key):
                    setattr(competitor, key, value)
            
            competitor.updated_at = datetime.now()
            
            # Valider
            validation_errors = self.validation_service.validate_competitor_data(competitor)
            if validation_errors:
                raise ValueError(f"Données invalides: {'; '.join(validation_errors)}")
            
            # Sauvegarder
            updated_competitor = self.competitor_repo.save(competitor)
            
            # Invalider le cache
            self.cache_service.invalidate_competitor_cache(competitor_id)
            
            self.logger.info(f"Concurrent mis à jour: {updated_competitor.name} (ID: {competitor_id})")
            return updated_competitor
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour du concurrent {competitor_id}: {e}")
            raise
    
    def calculate_metrics(self, competitor_id: int) -> Dict[str, Any]:
        """Calculer les métriques d'un concurrent"""
        try:
            competitor = self.competitor_repo.get_by_id(competitor_id)
            if not competitor:
                raise ValueError(f"Concurrent non trouvé: {competitor_id}")
            
            # Récupérer les données analytiques
            analytics = self.analytics_repo.get_competitor_stats(competitor_id)
            
            # Calculer les métriques
            metrics = CompetitorMetrics(
                subscriber_count=analytics.get('subscriber_count', 0),
                video_count=analytics.get('video_count', 0),
                total_views=analytics.get('total_views', 0),
                avg_views=analytics.get('avg_views', 0.0),
                engagement_rate=analytics.get('engagement_rate', 0.0),
                shorts_count=analytics.get('shorts_count', 0),
                shorts_percentage=analytics.get('shorts_percentage', 0.0),
                organic_count=analytics.get('organic_count', 0),
                paid_count=analytics.get('paid_count', 0),
                last_calculated=datetime.now()
            )
            
            # Mettre à jour le concurrent
            competitor.update_metrics(metrics)
            self.competitor_repo.save(competitor)
            
            # Invalider le cache
            self.cache_service.invalidate_competitor_cache(competitor_id)
            
            return metrics.__dict__
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des métriques pour {competitor_id}: {e}")
            raise
    
    def get_performance_report(self, competitor_id: int) -> Dict[str, Any]:
        """Générer un rapport de performance"""
        try:
            competitor = self.get_competitor_details(competitor_id)
            if not competitor:
                raise ValueError(f"Concurrent non trouvé: {competitor_id}")
            
            # Récupérer les données nécessaires
            videos = self.video_repo.get_by_competitor(competitor_id)
            playlists = self.playlist_repo.get_by_competitor(competitor_id)
            analytics = self.analytics_repo.get_competitor_stats(competitor_id)
            
            # Calculer les métriques de performance
            performance_score = competitor.get_performance_score()
            engagement_rate = competitor.calculate_engagement_rate()
            
            # Analyser les tendances
            shorts_videos = [v for v in videos if v.is_short()]
            regular_videos = [v for v in videos if not v.is_short()]
            
            # Analyser les performances par type de contenu
            shorts_performance = self._analyze_content_performance(shorts_videos)
            regular_performance = self._analyze_content_performance(regular_videos)
            
            # Générer le rapport
            report = {
                'competitor': competitor.to_dict(),
                'overview': {
                    'performance_score': performance_score,
                    'engagement_rate': engagement_rate,
                    'total_videos': len(videos),
                    'total_playlists': len(playlists),
                    'avg_views': competitor.metrics.avg_views,
                    'subscriber_count': competitor.metrics.subscriber_count
                },
                'content_analysis': {
                    'shorts': {
                        'count': len(shorts_videos),
                        'percentage': (len(shorts_videos) / len(videos) * 100) if videos else 0,
                        'performance': shorts_performance
                    },
                    'regular': {
                        'count': len(regular_videos),
                        'percentage': (len(regular_videos) / len(videos) * 100) if videos else 0,
                        'performance': regular_performance
                    }
                },
                'top_performers': self._get_top_performing_content(videos, limit=10),
                'recommendations': self._generate_recommendations(competitor, videos),
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du rapport pour {competitor_id}: {e}")
            raise
    
    def _enrich_with_metrics(self, competitor: Competitor) -> Competitor:
        """Enrichir un concurrent avec ses métriques calculées"""
        try:
            # Récupérer les métriques fraîches si nécessaire
            if (not competitor.metrics.last_calculated or 
                (datetime.now() - competitor.metrics.last_calculated).seconds > 3600):
                
                analytics = self.analytics_repo.get_competitor_stats(competitor.id)
                
                metrics = CompetitorMetrics(
                    subscriber_count=analytics.get('subscriber_count', 0),
                    video_count=analytics.get('video_count', 0),
                    total_views=analytics.get('total_views', 0),
                    avg_views=analytics.get('avg_views', 0.0),
                    engagement_rate=analytics.get('engagement_rate', 0.0),
                    shorts_count=analytics.get('shorts_count', 0),
                    shorts_percentage=analytics.get('shorts_percentage', 0.0),
                    organic_count=analytics.get('organic_count', 0),
                    paid_count=analytics.get('paid_count', 0),
                    last_calculated=datetime.now()
                )
                
                competitor.update_metrics(metrics)
            
            return competitor
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enrichissement des métriques: {e}")
            return competitor
    
    def _analyze_content_performance(self, videos: List) -> Dict[str, Any]:
        """Analyser les performances d'un type de contenu"""
        if not videos:
            return {'avg_views': 0, 'total_views': 0, 'engagement_rate': 0}
        
        total_views = sum(v.metrics.view_count for v in videos)
        avg_views = total_views / len(videos)
        avg_engagement = sum(v.metrics.engagement_rate for v in videos) / len(videos)
        
        return {
            'avg_views': avg_views,
            'total_views': total_views,
            'engagement_rate': avg_engagement,
            'count': len(videos)
        }
    
    def _get_top_performing_content(self, videos: List, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupérer le contenu le plus performant"""
        # Trier par vues et prendre les top
        sorted_videos = sorted(videos, key=lambda v: v.metrics.view_count, reverse=True)
        
        return [
            {
                'video_id': v.video_id,
                'title': v.title,
                'views': v.metrics.view_count,
                'engagement_rate': v.metrics.engagement_rate,
                'is_short': v.is_short(),
                'youtube_url': v.get_youtube_url()
            }
            for v in sorted_videos[:limit]
        ]
    
    def _generate_recommendations(self, competitor: Competitor, videos: List) -> List[str]:
        """Générer des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Analyser les Shorts
        shorts = [v for v in videos if v.is_short()]
        shorts_percentage = (len(shorts) / len(videos) * 100) if videos else 0
        
        if shorts_percentage < 20:
            recommendations.append("Considérer augmenter la production de Shorts (< 20% actuellement)")
        elif shorts_percentage > 80:
            recommendations.append("Équilibrer avec plus de contenu long format")
        
        # Analyser l'engagement
        if competitor.calculate_engagement_rate() < 2:
            recommendations.append("Améliorer l'engagement - taux actuel faible")
        
        # Analyser la consistance
        if len(videos) < 10:
            recommendations.append("Augmenter la fréquence de publication")
        
        # Analyser les performances
        if competitor.metrics.avg_views < 1000:
            recommendations.append("Optimiser les titres et miniatures pour améliorer les vues")
        
        return recommendations