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
        """Récupère l'ID de chaîne par handle (@nom) en utilisant le endpoint search"""
        try:
            # Le endpoint 'channels' ne supporte pas 'forHandle'.
            # On doit utiliser le endpoint 'search' pour trouver la chaîne par son handle.
            params = {
                'part': 'id',
                'q': handle,
                'type': 'channel',
                'maxResults': 1
            }
            response = self._make_request('search', params)
            
            if response.get('items'):
                # Vérifier si le handle correspond exactement
                # L'API de recherche peut retourner des résultats partiels
                item = response['items'][0]
                # La recherche retourne un snippet avec le customUrl, qui est le handle
                # Note: Le handle est dans 'customUrl' sans le '@'
                # Nous devons récupérer les détails de la chaîne pour être sûr.
                return item['id']['channelId']
        except Exception as e:
            print(f"[API] ❌ Erreur récupération ID par handle '{handle}': {e}")
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
            
            # Debug: afficher la réponse API
            print(f"[API-DEBUG] 📥 Requête pour {len(batch_ids)} vidéos, réponse: {len(response.get('items', []))} items")
            if len(response.get('items', [])) != len(batch_ids):
                missing_count = len(batch_ids) - len(response.get('items', []))
                print(f"[API-DEBUG] ⚠️ {missing_count} vidéos manquantes dans la réponse (supprimées/privées)")
            
            for item in response.get('items', []):
                duration = self._parse_duration(item.get('contentDetails', {}).get('duration', ''))
                
                # Récupération sécurisée des données avec fallbacks
                title = item.get('snippet', {}).get('title', 'Titre inconnu')
                if not title or title.strip() == '':
                    title = 'Titre inconnu'
                
                channel_title = item.get('snippet', {}).get('channelTitle', 'Chaîne inconnue')
                if not channel_title or channel_title.strip() == '':
                    channel_title = 'Chaîne inconnue'
                
                # Détecter si c'est un Short (≤ 60 secondes)
                is_short = duration <= 60 if duration > 0 else False
                
                video = {
                    'id': item.get('id', ''),
                    'title': title,
                    'description': item.get('snippet', {}).get('description', ''),
                    'published_at': item.get('snippet', {}).get('publishedAt', ''),
                    'channel_id': item.get('snippet', {}).get('channelId', ''),
                    'channel_title': channel_title,
                    'thumbnail': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                    'duration': duration,
                    'duration_seconds': duration,
                    'is_short': is_short,
                    'view_count': int(item.get('statistics', {}).get('viewCount', 0) or 0),
                    'like_count': int(item.get('statistics', {}).get('likeCount', 0) or 0),
                    'comment_count': int(item.get('statistics', {}).get('commentCount', 0) or 0),
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
        """Recherche des chaînes YouTube avec miniatures"""
        params = {
            'part': 'snippet',
            'type': 'channel',
            'q': query,
            'maxResults': max_results
        }
        
        response = self._make_request('search', params)
        
        # Étape 1: Récupérer les IDs des chaînes depuis la recherche
        channel_ids = []
        channel_data = {}
        
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
                
                channel_ids.append(channel_id)
                channel_data[channel_id] = {
                    'title': title,
                    'description': item.get('snippet', {}).get('description', ''),
                    'search_thumbnail': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                }
                
            except Exception as e:
                print(f"[API] ❌ Erreur traitement chaîne: {e}, item: {item}")
                continue
        
        # Étape 2: Récupérer les détails des chaînes avec leurs vraies miniatures
        if channel_ids:
            try:
                details_params = {
                    'part': 'snippet,statistics',
                    'id': ','.join(channel_ids)
                }
                
                details_response = self._make_request('channels', details_params)
                
                # Mettre à jour les données avec les vraies miniatures
                for item in details_response.get('items', []):
                    channel_id = item.get('id', '')
                    if channel_id in channel_data:
                        # Récupérer la meilleure miniature disponible
                        thumbnails = item.get('snippet', {}).get('thumbnails', {})
                        thumbnail_url = ''
                        
                        # Ordre de préférence : high > medium > default
                        if thumbnails.get('high', {}).get('url'):
                            thumbnail_url = thumbnails['high']['url']
                        elif thumbnails.get('medium', {}).get('url'):
                            thumbnail_url = thumbnails['medium']['url']
                        elif thumbnails.get('default', {}).get('url'):
                            thumbnail_url = thumbnails['default']['url']
                        
                        channel_data[channel_id]['thumbnail'] = thumbnail_url
                        
                        # Ajouter le nombre d'abonnés si disponible
                        subscriber_count = item.get('statistics', {}).get('subscriberCount', 0)
                        if subscriber_count:
                            channel_data[channel_id]['subscriber_count'] = int(subscriber_count)
                        
                        print(f"[API] 🖼️ Miniature récupérée pour {channel_data[channel_id]['title']}: {thumbnail_url[:50]}...")
                
            except Exception as e:
                print(f"[API] ⚠️ Erreur récupération détails chaînes: {e}")
        
        # Étape 3: Formatter les résultats finaux
        channels = []
        for channel_id in channel_ids:
            if channel_id in channel_data:
                data = channel_data[channel_id]
                channel = {
                    'id': channel_id,
                    'title': data['title'],
                    'description': data['description'],
                    'thumbnail': data.get('thumbnail', data.get('search_thumbnail', '')),
                    'url': f"https://www.youtube.com/channel/{channel_id}",
                    'subscriber_count': data.get('subscriber_count', 0)
                }
                channels.append(channel)
        
        return channels
    
    def search_local_tourism_competitors(self, country_code: str, max_results: int = 20) -> Dict:
        """
        Recherche spécialisée pour les concurrents locaux dans le tourisme
        
        Args:
            country_code: Code pays (DE, NL, BE, FR, etc.)
            max_results: Nombre maximum de résultats par recherche
            
        Returns:
            Dict avec les résultats organisés par pertinence
        """
        
        # Définir les mots-clés par pays/région
        tourism_keywords = {
            'DE': [
                'Familienurlaub Deutschland',
                'Ferienpark Deutschland', 
                'Camping mit Kindern',
                'Wellness Deutschland',
                'Kurzurlaub Familie',
                'Freizeitpark Deutschland',
                'Familienausflug Deutschland',
                'Urlaub mit Kindern',
                'Ferienanlage Deutschland'
            ],
            'NL': [
                'Familiepark Nederland',
                'Vakantieparken kinderen',
                'Recreatiepark Nederland',
                'Weekendje weg familie',
                'Bungalowpark Nederland',
                'Dagje uit kinderen',
                'Vakantie Nederland',
                'Familievakantie Nederland'
            ],
            'BE': [
                'Familiepark België',
                'Vakantieparken België',
                'Weekendje weg België',
                'Parcs de vacances Belgique',
                'Séjour famille Belgique',
                'Village vacances Belgique',
                'Vakantie België',
                'Familievakantie België'
            ],
            'FR': [
                'Parcs de vacances France',
                'Vacances en famille France',
                'Village vacances France',
                'Camping familial France',
                'Séjour famille France',
                'Résidence de vacances',
                'Tourisme famille France'
            ]
        }
        
        # Mots-clés pour identifier le secteur touristique
        tourism_indicators = [
            'park', 'resort', 'hotel', 'camping', 'vacation', 'holiday', 'familie',
            'urlaub', 'vakantie', 'vacances', 'séjour', 'wellness', 'spa', 'travel',
            'reisen', 'touris', 'recreation', 'freizit', 'leisure', 'family'
        ]
        
        results = {
            'country': country_code,
            'total_found': 0,
            'high_relevance': [],  # Très pertinents pour le tourisme
            'medium_relevance': [], # Moyennement pertinents
            'low_relevance': [],   # Faible pertinence
            'keywords_used': tourism_keywords.get(country_code, []),
            'search_summary': {}
        }
        
        keywords = tourism_keywords.get(country_code, [])
        if not keywords:
            print(f"[TOURISM-SEARCH] ⚠️ Aucun mot-clé défini pour {country_code}")
            return results
        
        print(f"[TOURISM-SEARCH] 🔍 Recherche concurrents locaux pour {country_code}")
        
        all_channels = {}  # Déduplication par channel_id
        
        # Rechercher avec chaque mot-clé
        for keyword in keywords:
            print(f"[TOURISM-SEARCH] 📝 Recherche: '{keyword}'")
            
            try:
                channels = self.search_channels(keyword, max_results=max_results)
                results['search_summary'][keyword] = len(channels)
                
                for channel in channels:
                    channel_id = channel['id']
                    
                    # Éviter les doublons
                    if channel_id not in all_channels:
                        # Calculer le score de pertinence
                        relevance_score = self._calculate_tourism_relevance(
                            channel, tourism_indicators
                        )
                        
                        channel['relevance_score'] = relevance_score
                        channel['found_with_keyword'] = keyword
                        channel['country_code'] = country_code
                        
                        all_channels[channel_id] = channel
                        
                        print(f"[TOURISM-SEARCH] 🏨 Trouvé: {channel['title']} (Score: {relevance_score})")
                
            except Exception as e:
                print(f"[TOURISM-SEARCH] ❌ Erreur recherche '{keyword}': {e}")
                results['search_summary'][keyword] = 0
        
        # Classer les résultats par pertinence
        sorted_channels = sorted(all_channels.values(), key=lambda x: x['relevance_score'], reverse=True)
        
        for channel in sorted_channels:
            score = channel['relevance_score']
            
            if score >= 7:
                results['high_relevance'].append(channel)
            elif score >= 4:
                results['medium_relevance'].append(channel)
            else:
                results['low_relevance'].append(channel)
        
        results['total_found'] = len(sorted_channels)
        
        print(f"[TOURISM-SEARCH] ✅ {results['total_found']} chaînes trouvées pour {country_code}")
        print(f"[TOURISM-SEARCH] 📊 Pertinence: {len(results['high_relevance'])} haute, {len(results['medium_relevance'])} moyenne, {len(results['low_relevance'])} faible")
        
        return results
    
    def _calculate_tourism_relevance(self, channel: Dict, tourism_indicators: list) -> int:
        """
        Calcule un score de pertinence pour le secteur touristique (0-10)
        
        Args:
            channel: Données de la chaîne
            tourism_indicators: Liste des mots-clés du tourisme
            
        Returns:
            Score de pertinence (0-10)
        """
        score = 0
        
        title = channel.get('title', '').lower()
        description = channel.get('description', '').lower()
        
        # Points pour les mots-clés du tourisme dans le titre (plus important)
        for indicator in tourism_indicators:
            if indicator in title:
                score += 2
        
        # Points pour les mots-clés du tourisme dans la description
        for indicator in tourism_indicators:
            if indicator in description:
                score += 1
        
        # Bonus pour les mots-clés spécifiques au tourisme familial
        family_keywords = ['famili', 'family', 'kids', 'kinder', 'enfant', 'children']
        for keyword in family_keywords:
            if keyword in title:
                score += 1
            if keyword in description:
                score += 0.5
        
        # Bonus pour les chaînes avec beaucoup d'abonnés (indicateur de qualité)
        subscriber_count = channel.get('subscriber_count', 0)
        if subscriber_count > 100000:
            score += 2
        elif subscriber_count > 50000:
            score += 1
        elif subscriber_count > 10000:
            score += 0.5
        
        # Malus pour les chaînes qui semblent être des agences de voyage génériques
        generic_keywords = ['travel agency', 'booking', 'flight', 'ticket', 'deal']
        for keyword in generic_keywords:
            if keyword in title or keyword in description:
                score -= 1
        
        return min(max(int(score), 0), 10)  # Limiter entre 0 et 10
    
    def get_channel_playlists(self, channel_id: str) -> List[Dict]:
        """Récupère toutes les playlists d'une chaîne"""
        try:
            params = {
                'part': 'id,snippet,contentDetails',
                'channelId': channel_id,
                'maxResults': 50
            }
            
            response = self._make_request('playlists', params)
            
            playlists = []
            for item in response.get('items', []):
                playlist = {
                    'playlist_id': item.get('id', ''),
                    'name': item.get('snippet', {}).get('title', 'Playlist sans nom'),
                    'description': item.get('snippet', {}).get('description', ''),
                    'thumbnail_url': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                    'video_count': item.get('contentDetails', {}).get('itemCount', 0),
                    'published_at': item.get('snippet', {}).get('publishedAt', ''),
                    'privacy_status': item.get('snippet', {}).get('privacyStatus', 'public')
                }
                playlists.append(playlist)
            
            print(f"[API] 📋 {len(playlists)} playlists trouvées pour la chaîne {channel_id}")
            return playlists
            
        except Exception as e:
            print(f"[API] ❌ Erreur récupération playlists: {e}")
            return []
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = 50) -> List[str]:
        """Récupère les IDs des vidéos d'une playlist"""
        try:
            video_ids = []
            next_page_token = None
            
            while len(video_ids) < max_results:
                params = {
                    'part': 'snippet',
                    'playlistId': playlist_id,
                    'maxResults': min(50, max_results - len(video_ids))
                }
                
                if next_page_token:
                    params['pageToken'] = next_page_token
                
                response = self._make_request('playlistItems', params)
                
                if not response.get('items'):
                    break
                
                for item in response['items']:
                    video_id = item.get('snippet', {}).get('resourceId', {}).get('videoId')
                    if video_id:
                        video_ids.append(video_id)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"[API] 🎬 {len(video_ids)} vidéos trouvées dans la playlist {playlist_id}")
            return video_ids
            
        except Exception as e:
            print(f"[API] ❌ Erreur récupération vidéos playlist: {e}")
            return []
    
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
    # Récupérer la clé API depuis la base de données
    try:
        from yt_channel_analyzer.database.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM app_config WHERE key = "youtube_api_key"')
        result = cursor.fetchone()
        api_key = result[0] if result else None
        conn.close()
        
        if api_key:
            return YouTubeAPI(api_key)
        else:
            print("[YOUTUBE-API] ⚠️ Clé API YouTube non trouvée en base, essai variable d'environnement")
            return YouTubeAPI()
    except Exception as e:
        print(f"[YOUTUBE-API] ⚠️ Erreur récupération clé API depuis la base: {e}, essai variable d'environnement")
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