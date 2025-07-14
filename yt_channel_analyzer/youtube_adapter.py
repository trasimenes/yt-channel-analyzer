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
            # Convertir la durée en secondes pour compatibilité
            duration_seconds = video.get('duration_seconds', 0)
            
            # Formatage compatible avec l'ancien système
            formatted_video = {
                'title': video.get('title', 'Titre inconnu'),
                'url': video.get('url', ''),
                'thumbnail': video.get('thumbnail', ''),
                'views': video.get('view_count', 0),
                'likes': video.get('like_count', 0),
                'published_at': video.get('published_at', ''),
                'duration': f"{duration_seconds // 3600:02d}:{(duration_seconds % 3600) // 60:02d}:{duration_seconds % 60:02d}" if duration_seconds > 0 else "00:00:00",
                'duration_seconds': duration_seconds,
                'description': video.get('description', ''),
                'video_id': video.get('video_id', ''),
                'category': video.get('category', 'hub'),  # Défaut hub
                'tags': video.get('tags', [])
            }
            
            formatted_videos.append(formatted_video)
        
        print(f"✅ API YouTube: {len(formatted_videos)} vidéos récupérées pour {channel_url}")
        return formatted_videos
        
    except Exception as e:
        print(f"❌ Erreur API YouTube get_channel_videos_data_api: {e}")
        return []


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extrait l'ID d'une vidéo YouTube depuis son URL
    
    Args:
        url (str): URL de la vidéo YouTube
        
    Returns:
        Optional[str]: ID de la vidéo ou None si non trouvé
    """
    if not url:
        return None
    
    # Formats d'URL YouTube supportés
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_channel_info_api(channel_url: str) -> Dict:
    """
    Récupère les informations d'une chaîne via l'API YouTube
    
    Args:
        channel_url (str): URL de la chaîne
        
    Returns:
        Dict: Informations de la chaîne
    """
    try:
        youtube = create_youtube_client()
        channel_info = youtube.get_channel_info(channel_url)
        
        # Formatage compatible avec l'application
        formatted_info = {
            'id': channel_info.get('id', ''),
            'title': channel_info.get('title', 'Nom inconnu'),
            'description': channel_info.get('description', ''),
            'thumbnail': channel_info.get('thumbnail', ''),
            'banner': channel_info.get('banner', ''),
            'subscriber_count': channel_info.get('subscriber_count', 0),
            'view_count': channel_info.get('view_count', 0),
            'video_count': channel_info.get('video_count', 0),
            'custom_url': channel_info.get('custom_url', ''),
            'published_at': channel_info.get('published_at', ''),
            'country': channel_info.get('country', ''),
            'language': channel_info.get('language', '')
        }
        
        return formatted_info
        
    except Exception as e:
        print(f"❌ Erreur API YouTube get_channel_info_api: {e}")
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


def search_local_tourism_competitors_api(country_code: str, max_results: int = 15) -> Dict:
    """
    Recherche des concurrents locaux dans le tourisme pour un pays spécifique
    
    Args:
        country_code (str): Code pays (DE, NL, BE, FR)
        max_results (int): Nombre maximum de résultats par recherche
        
    Returns:
        Dict: Résultats organisés par pertinence avec conseils d'analyse
    """
    try:
        youtube = create_youtube_client()
        results = youtube.search_local_tourism_competitors(country_code, max_results)
        
        # Ajouter des conseils d'analyse pour chaque niveau de pertinence
        analysis_tips = {
            'high_relevance': {
                'title': 'Concurrents Directs 🎯',
                'description': 'Ces chaînes sont vos concurrents directs. Analysez leur stratégie de contenu, fréquence de publication et engagement.',
                'action': 'Priorité haute - Ajoutez-les à votre analyse concurrentielle'
            },
            'medium_relevance': {
                'title': 'Concurrents Potentiels 📊',
                'description': 'Ces chaînes touchent votre secteur mais avec un angle différent. Observez leurs innovations.',
                'action': 'À surveiller - Analysez leurs meilleures pratiques'
            },
            'low_relevance': {
                'title': 'Secteur Élargi 🔍',
                'description': 'Ces chaînes sont dans le secteur du tourisme mais moins directement concurrentes.',
                'action': 'Veille sectorielle - Gardez un œil sur les tendances'
            }
        }
        
        # Enrichir les résultats avec les conseils
        results['analysis_tips'] = analysis_tips
        
        # Ajouter des recommandations d'action
        results['recommendations'] = generate_local_competitor_recommendations(results, country_code)
        
        print(f"✅ Recherche concurrents locaux {country_code}: {results['total_found']} chaînes trouvées")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur recherche concurrents locaux: {e}")
        return {
            'country': country_code,
            'total_found': 0,
            'high_relevance': [],
            'medium_relevance': [],
            'low_relevance': [],
            'error': str(e)
        }


def generate_local_competitor_recommendations(results: Dict, country_code: str) -> List[str]:
    """
    Génère des recommandations d'action basées sur les résultats de recherche
    
    Args:
        results (Dict): Résultats de la recherche
        country_code (str): Code pays
        
    Returns:
        List[str]: Liste des recommandations
    """
    recommendations = []
    
    high_count = len(results.get('high_relevance', []))
    medium_count = len(results.get('medium_relevance', []))
    
    # Conseils basés sur le nombre de concurrents trouvés
    if high_count == 0:
        recommendations.append("🏆 Opportunité : Peu de concurrents directs identifiés. Positionnez-vous comme leader sur ce marché.")
    elif high_count <= 3:
        recommendations.append(f"👀 Surveillez de près ces {high_count} concurrents directs - analysez leur stratégie contenu.")
    else:
        recommendations.append(f"⚠️ Marché concurrentiel : {high_count} concurrents directs. Différenciation nécessaire.")
    
    # Conseils spécifiques par pays
    country_advice = {
        'DE': "🇩🇪 Allemagne : Mettez l'accent sur la qualité, la sécurité et les activités familiales. Contenu en allemand indispensable.",
        'NL': "🇳🇱 Pays-Bas : Privilégiez le contenu pratique et les 'weekendje weg'. Les Néerlandais apprécient l'authenticité.",
        'BE': "🇧🇪 Belgique : Contenu bilingue recommandé (NL/FR). Mettez en avant la proximité et l'accessibilité.",
        'FR': "🇫🇷 France : Valorisez l'art de vivre et les expériences uniques. Contenu émotionnel et inspirant."
    }
    
    if country_code in country_advice:
        recommendations.append(country_advice[country_code])
    
    # Conseils d'action
    if high_count > 0:
        recommendations.append("📈 Action : Créez des listes de surveillance pour suivre les publications de vos concurrents directs.")
    
    if medium_count > 0:
        recommendations.append("🔍 Veille : Analysez les mots-clés et hashtags utilisés par les concurrents potentiels.")
    
    recommendations.append("🎯 Next Step : Analysez les top vidéos de vos concurrents pour identifier les formats qui fonctionnent.")
    
    return recommendations 