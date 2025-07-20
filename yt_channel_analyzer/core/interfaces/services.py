"""
Service interfaces - Following ISP and DIP principles
Interfaces ségrégées par domaine métier
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ..models import Competitor, Video, Playlist, VideoCategory, ClassificationSource


class CompetitorService(ABC):
    """Interface pour les services de gestion des concurrents"""
    
    @abstractmethod
    def get_competitor_details(self, competitor_id: int) -> Optional[Competitor]:
        """Récupérer les détails complets d'un concurrent"""
        pass
    
    @abstractmethod
    def create_competitor(self, competitor_data: Dict[str, Any]) -> Competitor:
        """Créer un nouveau concurrent"""
        pass
    
    @abstractmethod
    def update_competitor(self, competitor_id: int, updates: Dict[str, Any]) -> Competitor:
        """Mettre à jour un concurrent"""
        pass
    
    @abstractmethod
    def calculate_metrics(self, competitor_id: int) -> Dict[str, Any]:
        """Calculer les métriques d'un concurrent"""
        pass
    
    @abstractmethod
    def get_performance_report(self, competitor_id: int) -> Dict[str, Any]:
        """Générer un rapport de performance"""
        pass


class VideoService(ABC):
    """Interface pour les services de gestion des vidéos"""
    
    @abstractmethod
    def get_video_details(self, video_id: int) -> Optional[Video]:
        """Récupérer les détails d'une vidéo"""
        pass
    
    @abstractmethod
    def import_videos(self, competitor_id: int, video_ids: List[str]) -> List[Video]:
        """Importer des vidéos depuis YouTube"""
        pass
    
    @abstractmethod
    def update_video_metrics(self, video_id: int) -> Video:
        """Mettre à jour les métriques d'une vidéo"""
        pass
    
    @abstractmethod
    def get_video_performance(self, video_id: int) -> Dict[str, Any]:
        """Analyser les performances d'une vidéo"""
        pass
    
    @abstractmethod
    def get_shorts_analysis(self, competitor_id: int) -> Dict[str, Any]:
        """Analyser les Shorts d'un concurrent"""
        pass


class PlaylistService(ABC):
    """Interface pour les services de gestion des playlists"""
    
    @abstractmethod
    def get_playlist_details(self, playlist_id: int) -> Optional[Playlist]:
        """Récupérer les détails d'une playlist"""
        pass
    
    @abstractmethod
    def import_playlists(self, competitor_id: int, playlist_ids: List[str]) -> List[Playlist]:
        """Importer des playlists depuis YouTube"""
        pass
    
    @abstractmethod
    def update_playlist_metrics(self, playlist_id: int) -> Playlist:
        """Mettre à jour les métriques d'une playlist"""
        pass
    
    @abstractmethod
    def get_playlist_performance(self, playlist_id: int) -> Dict[str, Any]:
        """Analyser les performances d'une playlist"""
        pass


class ClassificationService(ABC):
    """Interface pour les services de classification"""
    
    @abstractmethod
    def classify_video(self, video_id: int) -> Tuple[VideoCategory, float]:
        """Classifier une vidéo"""
        pass
    
    @abstractmethod
    def classify_playlist(self, playlist_id: int) -> Tuple[VideoCategory, float]:
        """Classifier une playlist"""
        pass
    
    @abstractmethod
    def bulk_classify_videos(self, video_ids: List[int]) -> Dict[int, Tuple[VideoCategory, float]]:
        """Classifier plusieurs vidéos"""
        pass
    
    @abstractmethod
    def validate_human_classification(self, item_id: int, item_type: str, category: VideoCategory) -> bool:
        """Valider une classification humaine"""
        pass
    
    @abstractmethod
    def get_classification_report(self) -> Dict[str, Any]:
        """Générer un rapport de classification"""
        pass


class AnalyticsService(ABC):
    """Interface pour les services d'analytics"""
    
    @abstractmethod
    def get_competitor_analytics(self, competitor_id: int) -> Dict[str, Any]:
        """Récupérer les analytics d'un concurrent"""
        pass
    
    @abstractmethod
    def get_video_analytics(self, video_id: int) -> Dict[str, Any]:
        """Récupérer les analytics d'une vidéo"""
        pass
    
    @abstractmethod
    def get_top_performers(self, metric: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupérer les top performers"""
        pass
    
    @abstractmethod
    def generate_comparison_report(self, competitor_ids: List[int]) -> Dict[str, Any]:
        """Générer un rapport comparatif"""
        pass
    
    @abstractmethod
    def get_trend_analysis(self, competitor_id: int, period: str = '30d') -> Dict[str, Any]:
        """Analyser les tendances"""
        pass


class ValidationService(ABC):
    """Interface pour les services de validation"""
    
    @abstractmethod
    def validate_competitor_data(self, competitor: Competitor) -> List[str]:
        """Valider les données d'un concurrent"""
        pass
    
    @abstractmethod
    def validate_video_data(self, video: Video) -> List[str]:
        """Valider les données d'une vidéo"""
        pass
    
    @abstractmethod
    def validate_playlist_data(self, playlist: Playlist) -> List[str]:
        """Valider les données d'une playlist"""
        pass
    
    @abstractmethod
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Valider l'intégrité globale des données"""
        pass
    
    @abstractmethod
    def fix_data_issues(self, auto_fix: bool = True) -> Dict[str, Any]:
        """Corriger les problèmes de données"""
        pass


class YouTubeAPIService(ABC):
    """Interface pour les services d'API YouTube"""
    
    @abstractmethod
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Récupérer les informations d'une chaîne"""
        pass
    
    @abstractmethod
    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Récupérer les détails d'une vidéo"""
        pass
    
    @abstractmethod
    def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """Récupérer les détails d'une playlist"""
        pass
    
    @abstractmethod
    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Récupérer les vidéos d'une chaîne"""
        pass
    
    @abstractmethod
    def get_channel_playlists(self, channel_id: str) -> List[Dict[str, Any]]:
        """Récupérer les playlists d'une chaîne"""
        pass


class NotificationService(ABC):
    """Interface pour les services de notification"""
    
    @abstractmethod
    def send_analysis_complete(self, competitor_id: int, report: Dict[str, Any]) -> bool:
        """Envoyer une notification d'analyse terminée"""
        pass
    
    @abstractmethod
    def send_data_issue_alert(self, issues: List[str]) -> bool:
        """Envoyer une alerte de problème de données"""
        pass
    
    @abstractmethod
    def send_performance_report(self, competitor_id: int, report: Dict[str, Any]) -> bool:
        """Envoyer un rapport de performance"""
        pass


class CacheService(ABC):
    """Interface pour les services de cache"""
    
    @abstractmethod
    def get_cached_analytics(self, key: str) -> Optional[Dict[str, Any]]:
        """Récupérer des analytics depuis le cache"""
        pass
    
    @abstractmethod
    def cache_analytics(self, key: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Mettre en cache des analytics"""
        pass
    
    @abstractmethod
    def invalidate_competitor_cache(self, competitor_id: int) -> bool:
        """Invalider le cache d'un concurrent"""
        pass
    
    @abstractmethod
    def warm_up_cache(self) -> bool:
        """Préchauffer le cache"""
        pass


class ExportService(ABC):
    """Interface pour les services d'export"""
    
    @abstractmethod
    def export_competitor_report(self, competitor_id: int, format: str = 'pdf') -> str:
        """Exporter un rapport de concurrent"""
        pass
    
    @abstractmethod
    def export_analytics_data(self, competitor_id: int, format: str = 'csv') -> str:
        """Exporter les données d'analytics"""
        pass
    
    @abstractmethod
    def export_classification_report(self, format: str = 'xlsx') -> str:
        """Exporter un rapport de classification"""
        pass