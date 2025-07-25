"""
Utilities Module
Common functions and utilities used across blueprints.
Extracted from monolithic app.py to improve maintainability.
"""
import re
import os
from urllib.parse import urlparse, parse_qs


def extract_channel_name(channel_url):
    """
    Extraire le nom de la chaîne depuis une URL YouTube
    """
    if not channel_url:
        return "Chaîne inconnue"
    
    try:
        # Pattern pour extraire l'ID de la chaîne
        patterns = [
            r'/channel/([^/]+)',
            r'/c/([^/]+)', 
            r'/user/([^/]+)',
            r'/@([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_url)
            if match:
                return match.group(1).replace('_', ' ').title()
        
        # Si aucun pattern ne match, utiliser le domaine
        parsed = urlparse(channel_url)
        if parsed.netloc:
            return parsed.netloc.replace('www.', '').replace('.com', '').title()
        
        return "Chaîne inconnue"
        
    except Exception as e:
        print(f"[WARNING] Error extracting channel name from {channel_url}: {e}")
        return "Chaîne inconnue"


def format_duration(seconds):
    """
    Convertir une durée en secondes vers un format lisible
    """
    if not seconds:
        return "0:00"
    
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
            
    except (ValueError, TypeError):
        return "0:00"


def format_number(number, short=False):
    """
    Formater un nombre avec des séparateurs ou en format court
    """
    if number is None:
        return "0"
    
    try:
        number = int(number)
        
        if short:
            if number >= 1_000_000:
                return f"{number / 1_000_000:.1f}M"
            elif number >= 1_000:
                return f"{number / 1_000:.1f}K"
            else:
                return str(number)
        else:
            return f"{number:,}".replace(',', ' ')
            
    except (ValueError, TypeError):
        return "0"


def calculate_engagement_rate(views, likes, comments):
    """
    Calculer le taux d'engagement
    """
    try:
        views = int(views or 0)
        likes = int(likes or 0)
        comments = int(comments or 0)
        
        if views == 0:
            return 0.0
        
        engagement = ((likes + comments) / views) * 100
        return round(engagement, 2)
        
    except (ValueError, TypeError):
        return 0.0


def is_video_organic(view_count, threshold=10000):
    """
    Déterminer si une vidéo est organique ou payée basé sur les vues
    """
    try:
        return int(view_count or 0) < threshold
    except (ValueError, TypeError):
        return True


def clean_title(title):
    """
    Nettoyer un titre de vidéo
    """
    if not title:
        return ""
    
    try:
        # Supprimer les caractères de contrôle
        title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', title)
        
        # Limiter la longueur
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title.strip()
        
    except Exception:
        return str(title)[:100]


def validate_youtube_url(url):
    """
    Valider une URL YouTube
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Vérifier le domaine
        valid_domains = ['youtube.com', 'www.youtube.com', 'youtu.be']
        if parsed.netloc not in valid_domains:
            return False
        
        # Vérifier la structure de l'URL
        if '/channel/' in url or '/c/' in url or '/user/' in url or '/@' in url:
            return True
        
        return False
        
    except Exception:
        return False


def extract_video_id_from_url(url):
    """
    Extraire l'ID d'une vidéo YouTube depuis son URL
    """
    if not url:
        return None
    
    try:
        # Pattern pour différents formats d'URL YouTube
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
        
    except Exception:
        return None


def get_file_size_mb(file_path):
    """
    Obtenir la taille d'un fichier en MB
    """
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path) / (1024 * 1024)
        return 0
    except Exception:
        return 0


def truncate_text(text, max_length=50, suffix="..."):
    """
    Tronquer un texte à une longueur maximale
    """
    if not text:
        return ""
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_duration_text(duration_text):
    """
    Parser une durée textuelle en secondes
    Exemple: "PT4M13S" -> 253 secondes
    """
    if not duration_text:
        return 0
    
    try:
        # Pattern pour ISO 8601 duration (YouTube API format)
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_text)
        
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            return hours * 3600 + minutes * 60 + seconds
        
        # Pattern pour format classique (MM:SS ou HH:MM:SS)
        if ':' in duration_text:
            parts = duration_text.split(':')
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        return 0
        
    except (ValueError, AttributeError):
        return 0


def categorize_video_length(duration_seconds):
    """
    Catégoriser une vidéo par sa durée
    """
    if not duration_seconds:
        return "unknown"
    
    try:
        duration = int(duration_seconds)
        
        if duration < 60:
            return "shorts"  # Moins d'1 minute
        elif duration < 300:
            return "short"   # 1-5 minutes
        elif duration < 600:
            return "medium"  # 5-10 minutes
        elif duration < 1800:
            return "long"    # 10-30 minutes
        else:
            return "very_long"  # Plus de 30 minutes
            
    except (ValueError, TypeError):
        return "unknown"


def safe_divide(numerator, denominator, default=0):
    """
    Division sécurisée avec valeur par défaut
    """
    try:
        num = float(numerator or 0)
        den = float(denominator or 0)
        
        if den == 0:
            return default
        
        return num / den
        
    except (ValueError, TypeError):
        return default


def extract_keywords_from_title(title, min_length=3):
    """
    Extraire les mots-clés d'un titre
    """
    if not title:
        return []
    
    try:
        # Mots vides français et anglais
        stop_words = {
            'de', 'la', 'le', 'et', 'à', 'un', 'une', 'du', 'des', 'les', 'en', 'pour', 
            'avec', 'sur', 'dans', 'par', 'ce', 'qui', 'que', 'est', 'il', 'se', 'ne', 
            'pas', 'tout', 'être', 'avoir', 'faire', 'voir', 'plus', 'bien', 'où', 
            'comment', 'quand', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 
            'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those'
        }
        
        # Nettoyer et séparer les mots
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', title.lower())
        
        # Filtrer les mots-clés
        keywords = []
        for word in words:
            if len(word) >= min_length and word not in stop_words:
                keywords.append(word)
        
        return keywords
        
    except Exception:
        return []