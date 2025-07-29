"""
Module pour interagir avec l'API YouTube Data v3
Remplace le scraping par des appels API officiels
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
import time
import re

class YouTubeAPI:
    def __init__(self, api_key: str = None):
        """
        Initialise le client API YouTube
        
        Args:
            api_key (str): Clé API YouTube Data v3
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("Clé API YouTube requise. Définissez YOUTUBE_API_KEY dans .env")
        
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.requests_made = 0
        self.quota_used = 0
        
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Effectue une requête à l'API YouTube
        
        Args:
            endpoint (str): Point de terminaison de l'API
            params (Dict): Paramètres de la requête
            
        Returns:
            Dict: Réponse de l'API
        """
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            self.requests_made += 1
            # Estimation du quota utilisé (coût approximatif par endpoint)
            quota_costs = {
                'search': 100,
                'channels': 1,
                'videos': 1,
                'playlistItems': 1
            }
            self.quota_used += quota_costs.get(endpoint, 1)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur API YouTube: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Code erreur: {e.response.status_code}")
                print(f"Détails: {e.response.text}")
            raise
    
    def extract_channel_id_from_url(self, channel_url: str) -> Optional[str]:
        """
        Extrait l'ID de chaîne depuis différents formats d'URL
        
        Args:
            channel_url (str): URL de la chaîne
            
        Returns:
            str: ID de la chaîne ou None
        """
        # Format direct: /channel/UCxxxxx
        if '/channel/' in channel_url:
            return channel_url.split('/channel/')[-1].split('/')[0]
        
        # Format custom: @nom ou /c/nom ou /user/nom
        if '@' in channel_url:
            handle = channel_url.split('@')[-1].split('/')[0]
            return self._get_channel_id_by_handle(f"@{handle}")
        elif '/c/' in channel_url:
            custom_name = channel_url.split('/c/')[-1].split('/')[0]
            return self._get_channel_id_by_custom_name(custom_name)
        elif '/user/' in channel_url:
            username = channel_url.split('/user/')[-1].split('/')[0]
            return self._get_channel_id_by_username(username)
        
        return None
    
    def _get_channel_id_by_handle(self, handle: str) -> Optional[str]:
        """Récupère l'ID de chaîne par handle (@nom)"""
        try:
            params = {
                'part': 'id',
                'forHandle': handle.replace('@', '')
            }
            response = self._make_request('channels', params)
            
            if response.get('items'):
                return response['items'][0]['id']
        except:
            pass
        return None
    
    def _get_channel_id_by_custom_name(self, custom_name: str) -> Optional[str]:
        """Récupère l'ID de chaîne par nom personnalisé"""
        try:
            params = {
                'part': 'id',
                'forUsername': custom_name
            }
            response = self._make_request('channels', params)
            
            if response.get('items'):
                return response['items'][0]['id']
        except:
            pass
        return None
    
    def _get_channel_id_by_username(self, username: str) -> Optional[str]:
        """Récupère l'ID de chaîne par nom d'utilisateur"""
        try:
            params = {
                'part': 'id',
                'forUsername': username
            }
            response = self._make_request('channels', params)
            
            if response.get('items'):
                return response['items'][0]['id']
        except:
            pass
        return None
    
    def get_channel_info(self, channel_url: str) -> Dict:
        """
        Récupère les informations d'une chaîne
        
        Args:
            channel_url (str): URL de la chaîne
            
        Returns:
            Dict: Données de la chaîne
        """
        channel_id = self.extract_channel_id_from_url(channel_url)
        if not channel_id:
            raise ValueError(f"Impossible d'extraire l'ID de chaîne de: {channel_url}")
        
        params = {
            'part': 'id,snippet,statistics,contentDetails',
            'id': channel_id
        }
        
        response = self._make_request('channels', params)
        
        if not response.get('items'):
            raise ValueError(f"Chaîne non trouvée: {channel_url}")
        
        channel = response['items'][0]
        
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'],
            'custom_url': channel['snippet'].get('customUrl', ''),
            'published_at': channel['snippet']['publishedAt'],
            'thumbnail': channel['snippet']['thumbnails'].get('high', {}).get('url', ''),
            'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
            'video_count': int(channel['statistics'].get('videoCount', 0)),
            'view_count': int(channel['statistics'].get('viewCount', 0)),
            'uploads_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads']
        }
    
    def get_channel_videos(self, channel_url: str, max_results: int = 1000) -> List[Dict]:
        # Implémentation simplifiée pour commencer
        channel_id = self.extract_channel_id_from_url(channel_url)
        if not channel_id:
            raise ValueError(f"Impossible d'extraire l'ID de chaîne de: {channel_url}")
        
        # TODO: Implémenter la récupération des vidéos
        return []
    
    def get_videos_details(self, video_ids: List[str]) -> List[Dict]:
        """
        Récupère les détails de plusieurs vidéos
        
        Args:
            video_ids (List[str]): Liste des IDs de vidéos
            
        Returns:
            List[Dict]: Détails des vidéos
        """
        videos = []
        
        # L'API limite à 50 IDs par requête
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            params = {
                'part': 'id,snippet,statistics,contentDetails',
                'id': ','.join(batch_ids)
            }
            
            response = self._make_request('videos', params)
            
            for item in response.get('items', []):
                duration = self._parse_duration(item['contentDetails']['duration'])
                
                # Détecter si c'est un Short (≤ 60 secondes)
                is_short = duration <= 60 if duration > 0 else False
                
                video = {
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'published_at': item['snippet']['publishedAt'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'thumbnail': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                    'duration': duration,
                    'duration_seconds': duration,
                    'is_short': is_short,
                    'view_count': int(item['statistics'].get('viewCount', 0)),
                    'like_count': int(item['statistics'].get('likeCount', 0)),
                    'comment_count': int(item['statistics'].get('commentCount', 0)),
                    'url': f"https://www.youtube.com/watch?v={item['id']}"
                }
                videos.append(video)
        
        return videos
    
    def _parse_duration(self, duration: str) -> int:
        """
        Parse la durée YouTube (format ISO 8601) en secondes
        
        Args:
            duration (str): Durée au format PT1M30S
            
        Returns:
            int: Durée en secondes
        """
        if not duration.startswith('PT'):
            return 0
        
        duration = duration[2:]  # Enlever 'PT'
        
        hours = 0
        minutes = 0
        seconds = 0
        
        # Extraire heures
        if 'H' in duration:
            hours = int(duration.split('H')[0])
            duration = duration.split('H')[1]
        
        # Extraire minutes
        if 'M' in duration:
            minutes = int(duration.split('M')[0])
            duration = duration.split('M')[1]
        
        # Extraire secondes
        if 'S' in duration:
            seconds = int(duration.split('S')[0])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def search_channels(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Recherche des chaînes YouTube
        
        Args:
            query (str): Terme de recherche
            max_results (int): Nombre maximum de résultats
            
        Returns:
            List[Dict]: Liste des chaînes trouvées
        """
        params = {
            'part': 'snippet',
            'type': 'channel',
            'q': query,
            'maxResults': max_results
        }
        
        response = self._make_request('search', params)
        
        channels = []
        for item in response.get('items', []):
            channel = {
                'id': item['id']['channelId'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'thumbnail': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                'url': f"https://www.youtube.com/channel/{item['id']['channelId']}"
            }
            channels.append(channel)
        
        return channels
    
    def get_videos_info(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        Récupère les informations de base de plusieurs vidéos
        
        Args:
            video_ids (List[str]): Liste des IDs de vidéos
            
        Returns:
            Dict[str, Dict]: Dictionnaire {video_id: data} des vidéos
        """
        videos_info = {}
        
        # L'API limite à 50 IDs par requête
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            params = {
                'part': 'id,snippet',
                'id': ','.join(batch_ids)
            }
            
            response = self._make_request('videos', params)
            
            for item in response.get('items', []):
                videos_info[item['id']] = {
                    'snippet': {
                        'publishedAt': item['snippet']['publishedAt'],
                        'title': item['snippet']['title'],
                        'channelTitle': item['snippet']['channelTitle']
                    }
                }
        
        return videos_info
    
    def get_quota_usage(self) -> Dict:
        """
        Retourne l'utilisation du quota
        
        Returns:
            Dict: Statistiques d'utilisation
        """
        return {
            'requests_made': self.requests_made,
            'quota_used': self.quota_used,
            'daily_limit': 10000,  # Limite par défaut Google
            'remaining': 10000 - self.quota_used
        }


def create_youtube_client() -> YouTubeAPI:
    """
    Factory function pour créer un client YouTube API
    
    Returns:
        YouTubeAPI: Instance configurée du client
    """
    return YouTubeAPI() 