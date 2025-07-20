"""
Utilitaires pour la gestion des miniatures des concurrents
"""

import os
from pathlib import Path

THUMBNAILS_DIR = Path("static/competitors/images")

def get_competitor_thumbnail(competitor_id, fallback_url=None):
    """
    Obtenir le chemin local de la miniature d'un concurrent
    
    Args:
        competitor_id: ID du concurrent
        fallback_url: URL de fallback si la miniature locale n'existe pas
        
    Returns:
        str: Chemin relatif vers la miniature ou URL de fallback
    """
    # Chemin de la miniature locale
    local_path = THUMBNAILS_DIR / f"{competitor_id}.jpg"
    
    # Si le fichier existe, retourner le chemin relatif pour l'URL
    if local_path.exists():
        return f"/static/competitors/images/{competitor_id}.jpg"
    
    # Sinon, retourner le fallback ou une image par défaut
    if fallback_url:
        return fallback_url
    
    # Image par défaut si aucune miniature n'est disponible
    return "/static/img/default-channel.png"


def get_thumbnail_by_channel_url(channel_url, db_connection):
    """
    Obtenir la miniature d'un concurrent par son URL de chaîne
    
    Args:
        channel_url: URL de la chaîne YouTube
        db_connection: Connexion à la base de données
        
    Returns:
        str: Chemin vers la miniature
    """
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT id, thumbnail_url 
        FROM concurrent 
        WHERE channel_url = ?
    """, (channel_url,))
    
    result = cursor.fetchone()
    if result:
        competitor_id, thumbnail_url = result
        return get_competitor_thumbnail(competitor_id, thumbnail_url)
    
    return "/static/img/default-channel.png"