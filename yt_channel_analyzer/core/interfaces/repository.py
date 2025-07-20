"""
Repository interfaces - Following ISP and DIP principles
Interfaces ségrégées par responsabilité (ISP)
Dépendances vers abstractions (DIP)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import Competitor, Video, Playlist


class CompetitorRepository(ABC):
    """Interface pour l'accès aux données des concurrents"""
    
    @abstractmethod
    def get_by_id(self, competitor_id: int) -> Optional[Competitor]:
        """Récupérer un concurrent par son ID"""
        pass
    
    @abstractmethod
    def get_by_channel_id(self, channel_id: str) -> Optional[Competitor]:
        """Récupérer un concurrent par son channel ID"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Competitor]:
        """Récupérer tous les concurrents"""
        pass
    
    @abstractmethod
    def get_active(self) -> List[Competitor]:
        """Récupérer les concurrents actifs"""
        pass
    
    @abstractmethod
    def save(self, competitor: Competitor) -> Competitor:
        """Sauvegarder un concurrent"""
        pass
    
    @abstractmethod
    def delete(self, competitor_id: int) -> bool:
        """Supprimer un concurrent"""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Competitor]:
        """Rechercher des concurrents"""
        pass


class VideoRepository(ABC):
    """Interface pour l'accès aux données des vidéos"""
    
    @abstractmethod
    def get_by_id(self, video_id: int) -> Optional[Video]:
        """Récupérer une vidéo par son ID"""
        pass
    
    @abstractmethod
    def get_by_video_id(self, video_id: str) -> Optional[Video]:
        """Récupérer une vidéo par son video ID YouTube"""
        pass
    
    @abstractmethod
    def get_by_competitor(self, competitor_id: int) -> List[Video]:
        """Récupérer les vidéos d'un concurrent"""
        pass
    
    @abstractmethod
    def get_by_playlist(self, playlist_id: int) -> List[Video]:
        """Récupérer les vidéos d'une playlist"""
        pass
    
    @abstractmethod
    def get_shorts(self, competitor_id: Optional[int] = None) -> List[Video]:
        """Récupérer les Shorts"""
        pass
    
    @abstractmethod
    def get_unclassified(self) -> List[Video]:
        """Récupérer les vidéos non classifiées"""
        pass
    
    @abstractmethod
    def save(self, video: Video) -> Video:
        """Sauvegarder une vidéo"""
        pass
    
    @abstractmethod
    def save_batch(self, videos: List[Video]) -> List[Video]:
        """Sauvegarder plusieurs vidéos"""
        pass
    
    @abstractmethod
    def delete(self, video_id: int) -> bool:
        """Supprimer une vidéo"""
        pass


class PlaylistRepository(ABC):
    """Interface pour l'accès aux données des playlists"""
    
    @abstractmethod
    def get_by_id(self, playlist_id: int) -> Optional[Playlist]:
        """Récupérer une playlist par son ID"""
        pass
    
    @abstractmethod
    def get_by_playlist_id(self, playlist_id: str) -> Optional[Playlist]:
        """Récupérer une playlist par son playlist ID YouTube"""
        pass
    
    @abstractmethod
    def get_by_competitor(self, competitor_id: int) -> List[Playlist]:
        """Récupérer les playlists d'un concurrent"""
        pass
    
    @abstractmethod
    def get_unclassified(self) -> List[Playlist]:
        """Récupérer les playlists non classifiées"""
        pass
    
    @abstractmethod
    def save(self, playlist: Playlist) -> Playlist:
        """Sauvegarder une playlist"""
        pass
    
    @abstractmethod
    def delete(self, playlist_id: int) -> bool:
        """Supprimer une playlist"""
        pass


class AnalyticsRepository(ABC):
    """Interface pour l'accès aux données d'analytics"""
    
    @abstractmethod
    def get_competitor_stats(self, competitor_id: int) -> Dict[str, Any]:
        """Récupérer les statistiques d'un concurrent"""
        pass
    
    @abstractmethod
    def get_video_performance(self, video_id: int) -> Dict[str, Any]:
        """Récupérer les performances d'une vidéo"""
        pass
    
    @abstractmethod
    def get_playlist_stats(self, playlist_id: int) -> Dict[str, Any]:
        """Récupérer les statistiques d'une playlist"""
        pass
    
    @abstractmethod
    def get_top_videos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupérer les top vidéos"""
        pass
    
    @abstractmethod
    def get_top_playlists(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupérer les top playlists"""
        pass


class CacheRepository(ABC):
    """Interface pour le cache"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Récupérer une valeur du cache"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Stocker une valeur dans le cache"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Supprimer une valeur du cache"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Vider le cache"""
        pass


class SearchRepository(ABC):
    """Interface pour la recherche"""
    
    @abstractmethod
    def search_competitors(self, query: str) -> List[Competitor]:
        """Rechercher des concurrents"""
        pass
    
    @abstractmethod
    def search_videos(self, query: str) -> List[Video]:
        """Rechercher des vidéos"""
        pass
    
    @abstractmethod
    def search_playlists(self, query: str) -> List[Playlist]:
        """Rechercher des playlists"""
        pass
    
    @abstractmethod
    def search_all(self, query: str) -> Dict[str, List[Any]]:
        """Recherche globale"""
        pass


class ExportRepository(ABC):
    """Interface pour l'export de données"""
    
    @abstractmethod
    def export_competitor_data(self, competitor_id: int, format: str = 'json') -> str:
        """Exporter les données d'un concurrent"""
        pass
    
    @abstractmethod
    def export_analytics_report(self, competitor_id: int, start_date: datetime, end_date: datetime) -> str:
        """Exporter un rapport d'analytics"""
        pass
    
    @abstractmethod
    def export_classification_report(self) -> str:
        """Exporter un rapport de classification"""
        pass