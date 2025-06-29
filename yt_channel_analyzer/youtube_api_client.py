"""
Module pour interagir avec l'API YouTube Data v3
Remplace le scraping par des appels API officiels
"""

import os
import json
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
import re

class YouTubeAPI:
    def __init__(self, api_key: Optional[str] = None):
        """Initialise le client API YouTube"""
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("Clé API YouTube requise. Définissez YOUTUBE_API_KEY dans .env")
        
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.requests_made = 0
        self.quota_used = 0
        self.quota_file = 'api_quota_tracking.json'
        
        # Charger les données de quota existantes
        self._load_quota_data()
        
    def _load_quota_data(self):
        """Charge les données de quota depuis le fichier"""
        try:
            if os.path.exists(self.quota_file):
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    today = str(date.today())
                    
                    # Si c'est un nouveau jour, reset le compteur
                    if data.get('date') != today:
                        data = {'date': today, 'quota_used': 0, 'requests_made': 0}
                    
                    self.quota_used = data.get('quota_used', 0)
                    self.requests_made = data.get('requests_made', 0)
            else:
                # Créer le fichier initial
                self._save_quota_data()
        except Exception as e:
            print(f"[QUOTA] ❌ Erreur chargement quota: {e}")
            self.quota_used = 0
            self.requests_made = 0
    
    def _save_quota_data(self):
        """Sauvegarde les données de quota"""
        try:
            data = {
                'date': str(date.today()),
                'quota_used': self.quota_used,
                'requests_made': self.requests_made,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.quota_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[QUOTA] ❌ Erreur sauvegarde quota: {e}")
        
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Effectue une requête à l'API YouTube"""
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Incrémenter les compteurs
            self.requests_made += 1
            
            # Coûts en quota selon la documentation YouTube API
            quota_costs = {
                'search': 100,        # Recherche
                'channels': 1,        # Info chaîne
                'videos': 1,          # Détails vidéos
                'playlistItems': 1,   # Items de playlist
                'playlists': 1,       # Info playlists
                'activities': 1,      # Activités
                'subscriptions': 1    # Abonnements
            }
            
            cost = quota_costs.get(endpoint, 1)
            self.quota_used += cost
            
            # Sauvegarder après chaque requête
            self._save_quota_data()
            
            print(f"[QUOTA] 📊 Endpoint: {endpoint} | Coût: {cost} | Total utilisé: {self.quota_used}/10000")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur API YouTube: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Code erreur: {e.response.status_code}")
                print(f"Détails: {e.response.text}")
            raise
    
    def extract_channel_id_from_url(self, channel_url: str) -> Optional[str]:
        """Extrait l'ID de chaîne depuis différents formats d'URL"""
        # Format direct: /channel/UCxxxxx
        if '/channel/' in channel_url:
            return channel_url.split('/channel/')[-1].split('/')[0]
        
        # Format custom: @nom
        if '@' in channel_url:
            handle = channel_url.split('@')[-1].split('/')[0]
            return self._get_channel_id_by_handle(handle)
        
        # Format /c/nom
        elif '/c/' in channel_url:
            custom_name = channel_url.split('/c/')[-1].split('/')[0]
            return self._get_channel_id_by_custom_name(custom_name)
        
        # Format /user/nom
        elif '/user/' in channel_url:
            username = channel_url.split('/user/')[-1].split('/')[0]
            return self._get_channel_id_by_username(username)
        
        return None
    
    def _get_channel_id_by_handle(self, handle: str) -> Optional[str]:
        """Récupère l'ID de chaîne par handle (@nom)"""
        try:
            params = {
                'part': 'id',
                'forHandle': handle
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
        """Récupère les informations d'une chaîne"""
        channel_id = self.extract_channel_id_from_url(channel_url)
        if not channel_id:
            raise ValueError(f"Impossible d'extraire l'ID de chaîne de: {channel_url}")
        
        params = {
            'part': 'id,snippet,statistics,contentDetails,brandingSettings',
            'id': channel_id
        }
        
        response = self._make_request('channels', params)
        
        if not response.get('items'):
            raise ValueError(f"Chaîne non trouvée: {channel_url}")
        
        channel = response['items'][0]
        
        # Récupération sécurisée du titre avec fallback
        title = channel.get('snippet', {}).get('title', 'Nom inconnu')
        if not title or title.strip() == '':
            title = 'Nom inconnu'
        
        # Récupération de l'image de bannière (illustration) et de l'avatar
        thumbnails = channel.get('snippet', {}).get('thumbnails', {})
        if thumbnails:
            avatar_url = thumbnails.get('high', {}).get('url') or \
                         thumbnails.get('medium', {}).get('url') or \
                         thumbnails.get('default', {}).get('url', '')
        else:
            avatar_url = ''
        
        banner_url = channel.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl', '')
        
        # Amélioration de la récupération des bannières avec des URLs de haute qualité
        if not banner_url:
            # Essayer d'autres tailles de bannière depuis l'API
            banner_url = (
                channel.get('brandingSettings', {}).get('image', {}).get('bannerImageUrl', '') or
                channel.get('brandingSettings', {}).get('image', {}).get('bannerMobileImageUrl', '') or
                channel.get('brandingSettings', {}).get('image', {}).get('bannerTabletLowImageUrl', '')
            )
        
        # Si toujours pas de bannière, construire l'URL haute qualité manuellement
        if not banner_url and avatar_url:
            # Extraire l'ID de chaîne pour construire l'URL de bannière haute qualité
            # Format: https://yt3.googleusercontent.com/[ID_UNIQUE]=w2560-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj
            try:
                # Essayer de construire l'URL de bannière à partir de l'avatar
                if 'yt3.googleusercontent.com' in avatar_url:
                    # Extraire la partie unique de l'URL avatar
                    avatar_parts = avatar_url.split('/')
                    if len(avatar_parts) > 3:
                        unique_id = avatar_parts[-1].split('=')[0]
                        # Construire l'URL de bannière haute qualité
                        banner_url = f"https://yt3.googleusercontent.com/{unique_id}=w2560-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj"
                        print(f"[BANNER] 🎨 Bannière construite: {banner_url}")
            except Exception as e:
                print(f"[BANNER] ⚠️ Erreur construction bannière: {e}")
        
        # Fallback final sur l'avatar si aucune bannière n'est disponible
        if not banner_url:
            banner_url = avatar_url
        
        return {
            'id': channel['id'],
            'title': title,
            'description': channel.get('snippet', {}).get('description', ''),
            'custom_url': channel.get('snippet', {}).get('customUrl', ''),
            'published_at': channel.get('snippet', {}).get('publishedAt', ''),
            'thumbnail': avatar_url,  # Avatar/logo de la chaîne
            'banner': banner_url,     # Image d'illustration/bannière de la chaîne
            'subscriber_count': int(channel.get('statistics', {}).get('subscriberCount', 0)),
            'video_count': int(channel.get('statistics', {}).get('videoCount', 0)),
            'view_count': int(channel.get('statistics', {}).get('viewCount', 0)),
            'uploads_playlist_id': channel.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads', '')
        }
    
    def get_channel_videos(self, channel_url: str, max_results: int = 1000) -> List[Dict]:
        """Récupère les vidéos d'une chaîne"""
        channel_info = self.get_channel_info(channel_url)
        uploads_playlist_id = channel_info['uploads_playlist_id']
        
        print(f"[API] 📊 Chaîne {channel_info['title']}: {channel_info['video_count']} vidéos totales")
        
        all_videos = []
        next_page_token = None
        
        # Si max_results = 0, récupérer TOUTES les vidéos
        if max_results == 0:
            max_results = channel_info['video_count']  # Utiliser le nombre total de vidéos
            print(f"[API] 🔥 Mode illimité: récupération de toutes les {max_results} vidéos")
        
        while len(all_videos) < max_results:
            # Récupérer les IDs des vidéos depuis la playlist uploads
            params = {
                'part': 'snippet',
                'playlistId': uploads_playlist_id,
                'maxResults': min(50, max_results - len(all_videos))
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            response = self._make_request('playlistItems', params)
            
            if not response.get('items'):
                print(f"[API] ⚠️ Aucune vidéo dans cette page, arrêt à {len(all_videos)} vidéos")
                break
            
            # Extraire les IDs des vidéos
            video_ids = []
            for item in response['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_ids.append(video_id)
            
            # Récupérer les détails des vidéos
            video_details = self.get_videos_details(video_ids)
            all_videos.extend(video_details)
            
            print(f"[API] 📥 Page récupérée: {len(video_details)} vidéos | Total: {len(all_videos)}/{max_results}")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                print(f"[API] 🏁 Fin de pagination atteinte avec {len(all_videos)} vidéos")
                break
            
            if len(all_videos) >= max_results:
                print(f"[API] ✅ Limite atteinte: {len(all_videos)} vidéos")
                break
        
        return all_videos[:max_results]
    
    def get_videos_details(self, video_ids: List[str]) -> List[Dict]:
        """Récupère les détails de plusieurs vidéos"""
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
                duration = self._parse_duration(item.get('contentDetails', {}).get('duration', ''))
                
                # Récupération sécurisée des données avec fallbacks
                title = item.get('snippet', {}).get('title', 'Titre inconnu')
                if not title or title.strip() == '':
                    title = 'Titre inconnu'
                
                channel_title = item.get('snippet', {}).get('channelTitle', 'Chaîne inconnue')
                if not channel_title or channel_title.strip() == '':
                    channel_title = 'Chaîne inconnue'
                
                video = {
                    'id': item.get('id', ''),
                    'title': title,
                    'description': item.get('snippet', {}).get('description', ''),
                    'published_at': item.get('snippet', {}).get('publishedAt', ''),
                    'channel_id': item.get('snippet', {}).get('channelId', ''),
                    'channel_title': channel_title,
                    'thumbnail': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                    'duration': duration,
                    'view_count': int(item.get('statistics', {}).get('viewCount', 0)),
                    'like_count': int(item.get('statistics', {}).get('likeCount', 0)),
                    'comment_count': int(item.get('statistics', {}).get('commentCount', 0)),
                    'url': f"https://www.youtube.com/watch?v={item.get('id', '')}"
                }
                videos.append(video)
        
        return videos
    
    def _parse_duration(self, duration: str) -> int:
        """Parse la durée YouTube (format ISO 8601) en secondes"""
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
        """Recherche des chaînes YouTube"""
        params = {
            'part': 'snippet',
            'type': 'channel',
            'q': query,
            'maxResults': max_results
        }
        
        response = self._make_request('search', params)
        
        channels = []
        for item in response.get('items', []):
            try:
                # Récupération sécurisée de l'ID de chaîne
                channel_id = item.get('id', {}).get('channelId', '')
                if not channel_id:
                    print(f"[API] ⚠️ Chaîne sans ID trouvée, ignorée: {item}")
                    continue
                
                # Récupération sécurisée du titre avec fallback
                title = item.get('snippet', {}).get('title', 'Nom inconnu')
                if not title or title.strip() == '':
                    title = 'Nom inconnu'
                
                channel = {
                    'id': channel_id,
                    'title': title,
                    'description': item.get('snippet', {}).get('description', ''),
                    'thumbnail': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                    'url': f"https://www.youtube.com/channel/{channel_id}"
                }
                channels.append(channel)
                
            except Exception as e:
                print(f"[API] ❌ Erreur traitement chaîne: {e}, item: {item}")
                continue
        
        return channels
    
    def get_quota_usage(self) -> Dict:
        """Retourne l'usage actuel du quota"""
        # Recharger les données les plus récentes
        self._load_quota_data()
        
        return {
            'quota_used': self.quota_used,
            'requests_made': self.requests_made,
            'daily_limit': 10000,
            'remaining': max(0, 10000 - self.quota_used),
            'percentage': (self.quota_used / 10000) * 100 if self.quota_used > 0 else 0,
            'date': str(date.today()),
            'status': 'healthy' if self.quota_used < 8000 else 'warning' if self.quota_used < 9500 else 'critical'
        }


def create_youtube_client() -> YouTubeAPI:
    """Factory function pour créer un client YouTube API"""
    return YouTubeAPI()

def get_api_quota_status() -> Dict:
    """Récupère le statut actuel du quota API YouTube"""
    try:
        client = create_youtube_client()
        quota_info = client.get_quota_usage()
        
        # Ajouter des informations supplémentaires
        quota_info['daily_limit'] = 10000  # Limite quotidienne par défaut
        quota_info['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return quota_info
    except Exception as e:
        print(f"[API] ❌ Erreur récupération quota: {e}")
        # Retourner des données de fallback
        return {
            'quota_used': 0,
            'requests_made': 0,
            'daily_limit': 10000,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        } 