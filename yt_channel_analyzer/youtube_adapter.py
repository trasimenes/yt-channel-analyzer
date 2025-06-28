"""
Adaptateur pour remplacer le scraping par l'API YouTube
Compatible avec l'interface existante de l'application
"""

from datetime import datetime
from typing import List, Dict, Optional
from .youtube_api_client import create_youtube_client

def get_channel_videos_data_api(channel_url: str, video_limit: int = 1000) -> List[Dict]:
    """
    Remplace get_channel_videos_data() de selenium_scraper.py
    Utilise l'API YouTube au lieu du scraping
    
    Args:
        channel_url (str): URL de la chaîne YouTube
        video_limit (int): Nombre maximum de vidéos à récupérer
        
    Returns:
        List[Dict]: Liste des vidéos au format compatible avec l'app existante
    """
    try:
        youtube = create_youtube_client()
        
        # Récupérer les vidéos via l'API
        api_videos = youtube.get_channel_videos(channel_url, max_results=video_limit)
        
        # Convertir au format attendu par l'application
        formatted_videos = []
        for video in api_videos:
            formatted_video = {
                # Champs obligatoires pour l'application existante
                'title': video['title'],
                'url': video['url'],
                'views': format_views_for_app(video['view_count']),  # Nombre exact
                'publication_date': format_date_for_app(video['published_at']),
                
                # Champs supplémentaires de l'API avec données exactes
                'view_count': video['view_count'],  # Nombre exact de vues
                'like_count': video['like_count'],  # Nombre exact de likes
                'comment_count': video['comment_count'],  # Nombre exact de commentaires
                'duration': video['duration'],
                'thumbnail': video['thumbnail'],
                'description': video['description'][:200] + '...' if len(video['description']) > 200 else video['description'],
                
                # Champs pour compatibilité et affichage
                'video_id': video['id'],
                'channel_title': video['channel_title'],
                'views_display': format_views_for_display(video['view_count']),  # Pour l'affichage formaté
                'likes_display': format_views_for_display(video['like_count']),  # Pour l'affichage formaté
                'published_at_iso': video['published_at']  # Date ISO pour tri/calculs
            }
            formatted_videos.append(formatted_video)
        
        print(f"✅ API YouTube: {len(formatted_videos)} vidéos récupérées pour {channel_url}")
        return formatted_videos
        
    except Exception as e:
        print(f"❌ Erreur API YouTube: {e}")
        # Fallback vers le scraping en cas d'erreur
        print("⚠️ Tentative de fallback vers le scraping...")
        return fallback_to_scraping(channel_url, video_limit)

def get_video_data_api(video_url: str) -> Dict:
    """
    Remplace get_video_data() de selenium_scraper.py
    Récupère les données d'une vidéo via l'API
    
    Args:
        video_url (str): URL de la vidéo
        
    Returns:
        Dict: Données de la vidéo
    """
    try:
        youtube = create_youtube_client()
        
        # Extraire l'ID de la vidéo
        video_id = extract_video_id_from_url(video_url)
        if not video_id:
            raise ValueError(f"Impossible d'extraire l'ID vidéo de: {video_url}")
        
        # Récupérer les détails
        videos = youtube.get_videos_details([video_id])
        if not videos:
            raise ValueError(f"Vidéo non trouvée: {video_url}")
        
        video = videos[0]
        
        return {
            'title': video['title'],
            'url': video['url'],
            'views': format_views_for_app(video['view_count']),
            'publication_date': format_date_for_app(video['published_at']),
            'like_count': video['like_count'],
            'comment_count': video['comment_count'],
            'duration': video['duration'],
            'thumbnail': video['thumbnail'],
            'description': video['description'],
            'channel_title': video['channel_title']
        }
        
    except Exception as e:
        print(f"❌ Erreur API YouTube pour vidéo {video_url}: {e}")
        return {}

def autocomplete_youtube_channels_api(query: str, max_results: int = 10) -> List[Dict]:
    """
    Remplace autocomplete_youtube_channels() de scraper.py
    Recherche des chaînes via l'API avec miniatures
    
    Args:
        query (str): Terme de recherche
        max_results (int): Nombre maximum de résultats
        
    Returns:
        List[Dict]: Liste des chaînes trouvées avec miniatures
    """
    try:
        youtube = create_youtube_client()
        channels = youtube.search_channels(query, max_results)
        
        # Convertir au format attendu avec miniatures
        formatted_channels = []
        for channel in channels:
            formatted_channel = {
                'name': channel.get('title', 'Nom inconnu'),
                'url': channel.get('url', ''),
                'thumbnail': channel.get('thumbnail', ''),  # Vraie miniature de la chaîne
                'description': channel.get('description', '')[:100] + '...' if len(channel.get('description', '')) > 100 else channel.get('description', '')
            }
            formatted_channels.append(formatted_channel)
        
        print(f"✅ API YouTube autocomplete: {len(formatted_channels)} chaînes trouvées avec miniatures")
        return formatted_channels
        
    except Exception as e:
        print(f"❌ Erreur recherche API YouTube: {e}")
        return []

def get_channel_info_api(channel_url: str) -> Dict:
    """
    Récupère les informations complètes d'une chaîne
    
    Args:
        channel_url (str): URL de la chaîne
        
    Returns:
        Dict: Informations de la chaîne
    """
    try:
        youtube = create_youtube_client()
        return youtube.get_channel_info(channel_url)
    except Exception as e:
        print(f"❌ Erreur info chaîne API YouTube: {e}")
        return {}

# === FONCTIONS UTILITAIRES ===

def format_views_for_app(view_count: int) -> int:
    """Retourne le nombre exact de vues (pas de formatage)"""
    return int(view_count) if view_count else 0

def format_views_for_display(view_count: int) -> str:
    """Formate le nombre de vues pour l'affichage"""
    if view_count >= 1000000:
        return f"{view_count/1000000:.1f}M vues"
    elif view_count >= 1000:
        return f"{view_count/1000:.1f}k vues"
    else:
        return f"{view_count:,} vues".replace(',', ' ')

def format_date_for_app(published_at: str) -> str:
    """Formate la date de publication pour l'application existante"""
    try:
        # Convertir de ISO 8601 vers format français
        dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        
        # Calculer "il y a X jours/mois"
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        
        if diff.days == 0:
            return "aujourd'hui"
        elif diff.days == 1:
            return "il y a 1 jour"
        elif diff.days < 30:
            return f"il y a {diff.days} jours"
        elif diff.days < 365:
            months = diff.days // 30
            return f"il y a {months} mois"
        else:
            years = diff.days // 365
            return f"il y a {years} an" + ("s" if years > 1 else "")
    except:
        return published_at[:10]  # Fallback: juste la date

def extract_video_id_from_url(video_url: str) -> Optional[str]:
    """Extrait l'ID d'une vidéo YouTube depuis son URL"""
    if 'watch?v=' in video_url:
        return video_url.split('watch?v=')[1].split('&')[0]
    elif 'youtu.be/' in video_url:
        return video_url.split('youtu.be/')[1].split('?')[0]
    return None

def fallback_to_scraping(channel_url: str, video_limit: int) -> List[Dict]:
    """Fallback vers le scraping en cas d'erreur API"""
    try:
        # Importer ici pour éviter les dépendances circulaires
        from .selenium_scraper import get_channel_videos_data
        print("🔄 Utilisation du scraping Selenium en fallback...")
        return get_channel_videos_data(channel_url, video_limit)
    except Exception as e:
        print(f"❌ Échec du fallback scraping: {e}")
        return []

def get_channel_videos_data_api_incremental_background(
    channel_url: str, 
    existing_videos: Optional[List[Dict]] = None, 
    progress_callback=None,
    task_id: Optional[str] = None,
    max_videos: int = 0  # 0 = illimité, récupère TOUTES les vidéos
) -> List[Dict]:
    """
    Version API pour remplacer get_channel_videos_data_incremental_background de selenium_scraper.py
    Récupère les vidéos d'une chaîne de manière incrémentale via l'API YouTube
    
    Args:
        channel_url (str): URL de la chaîne YouTube
        existing_videos (List[Dict]): Vidéos déjà récupérées (pour éviter les doublons)
        progress_callback (callable): Fonction de callback pour les mises à jour de progression
        task_id (str): ID de la tâche pour les logs
        max_videos (int): Nombre maximum de vidéos à récupérer
        
    Returns:
        List[Dict]: Liste complète des vidéos (anciennes + nouvelles)
    """
    try:
        print(f"[API-BACKGROUND] 🚀 Début récupération API pour {channel_url}")
        
        if existing_videos is None:
            existing_videos = []
        
        # Étape 1: Initialisation
        if progress_callback:
            progress_callback("Connexion à l'API YouTube...", 5, len(existing_videos), 0)
        
        youtube = create_youtube_client()
        
        # Étape 2: Récupération des informations de la chaîne
        if progress_callback:
            progress_callback("Récupération des informations de la chaîne...", 10, len(existing_videos), 0)
        
        channel_info = youtube.get_channel_info(channel_url)
        if not channel_info:
            raise ValueError(f"Impossible de récupérer les informations de la chaîne: {channel_url}")
        
        print(f"[API-BACKGROUND] 📊 Chaîne trouvée: {channel_info.get('title', 'Nom inconnu')}")
        
        # Étape 3: Récupération de toutes les vidéos via l'API
        all_videos = list(existing_videos)  # Copier les vidéos existantes
        existing_video_ids = {extract_video_id_from_url(v.get('url', '')) for v in existing_videos if v.get('url')}
        existing_video_ids.discard(None)  # Supprimer les None
        
        if progress_callback:
            progress_callback("Récupération des vidéos via API...", 20, len(all_videos), 0)
        
        # Récupérer TOUTES les vidéos de la chaîne d'un coup
        api_videos = youtube.get_channel_videos(channel_url, max_results=max_videos)
        
        if progress_callback:
            progress_callback("Traitement des vidéos...", 60, len(all_videos), 0)
        
        new_videos_count = 0
        
        # Traiter chaque vidéo
        for i, video in enumerate(api_videos):
            # Callback de progression pendant le traitement
            if progress_callback and i % 50 == 0 and len(api_videos) > 0:
                current_progress = 60 + int((i / len(api_videos)) * 30)  # 60-90%
                progress_callback(
                    f"Traitement des vidéos... ({i}/{len(api_videos)})", 
                    current_progress, 
                    len(all_videos), 
                    i
                )
            
            # Vérifier si on a déjà cette vidéo
            video_id = video.get('id')
            if video_id in existing_video_ids:
                continue  # Skip, on l'a déjà
            
            # Nouvelle vidéo trouvée
            formatted_video = {
                # Champs obligatoires pour l'application existante
                'title': video['title'],
                'url': video['url'],
                'views': format_views_for_app(video['view_count']),  # Nombre exact
                'publication_date': format_date_for_app(video['published_at']),
                
                # Champs supplémentaires de l'API avec données exactes
                'view_count': video['view_count'],  # Nombre exact de vues
                'like_count': video['like_count'],  # Nombre exact de likes
                'comment_count': video['comment_count'],  # Nombre exact de commentaires
                'duration': video['duration'],
                'thumbnail': video['thumbnail'],
                'description': video['description'][:200] + '...' if len(video['description']) > 200 else video['description'],
                
                # Champs pour compatibilité et affichage
                'video_id': video['id'],
                'channel_title': video['channel_title'],
                'views_display': format_views_for_display(video['view_count']),  # Pour l'affichage formaté
                'likes_display': format_views_for_display(video['like_count']),  # Pour l'affichage formaté
                'published_at_iso': video['published_at']  # Date ISO pour tri/calculs
            }
            
            all_videos.append(formatted_video)
            existing_video_ids.add(video_id)
            new_videos_count += 1
        
        print(f"[API-BACKGROUND] ✅ Traitement terminé: {len(api_videos)} vidéos API, {new_videos_count} nouvelles")
        
        # Étape finale: Sauvegarde et finalisation
        if progress_callback:
            progress_callback("Finalisation...", 95, len(all_videos), new_videos_count)
        
        print(f"[API-BACKGROUND] 🎉 Récupération terminée: {len(all_videos)} vidéos total ({len(all_videos) - len(existing_videos)} nouvelles)")
        
        return all_videos
        
    except Exception as e:
        error_msg = f"Erreur API YouTube: {e}"
        print(f"[API-BACKGROUND] ❌ {error_msg}")
        
        # En cas d'erreur critique, essayer un fallback vers le scraping
        existing_videos_safe = existing_videos or []
        if len(existing_videos_safe) == 0:  # Seulement si on n'a rien du tout
            print(f"[API-BACKGROUND] 🔄 Tentative de fallback vers Selenium...")
            try:
                from .selenium_scraper import get_channel_videos_data_incremental_background
                return get_channel_videos_data_incremental_background(
                    channel_url, existing_videos_safe, progress_callback, task_id or ""
                )
            except Exception as fallback_error:
                print(f"[API-BACKGROUND] ❌ Fallback échoué: {fallback_error}")
        
        # Retourner au moins les vidéos existantes
        return existing_videos_safe

# === FONCTIONS POUR COMPATIBILITÉ ===

def get_api_quota_status() -> Dict:
    """Retourne le statut du quota API"""
    try:
        youtube = create_youtube_client()
        return youtube.get_quota_usage()
    except:
        return {
            'requests_made': 0,
            'quota_used': 0,
            'daily_limit': 10000,
            'remaining': 10000
        } 