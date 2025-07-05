#!/usr/bin/env python3
"""
Script de restauration directe avec API YouTube
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Ajouter le dossier du projet au path
sys.path.append('.')

from yt_channel_analyzer.youtube_api_client import create_youtube_client
from yt_channel_analyzer.database import save_competitor_and_videos

def restore_competitors():
    """Restaure directement les concurrents avec l'API YouTube"""
    
    # URLs des concurrents identifiés
    competitors = [
        "https://www.youtube.com/@Expedia",
        "https://www.youtube.com/@AccorHotels", 
        "https://www.youtube.com/@CenterParcs",
        "https://www.youtube.com/@ClubMedFr",
        "https://www.youtube.com/@Hilton"
    ]
    
    print("🔄 Restauration directe des concurrents...")
    print(f"📋 {len(competitors)} concurrents à restaurer")
    
    # Créer le client YouTube API
    try:
        youtube_client = create_youtube_client()
        print("✅ Client YouTube API créé avec succès")
    except Exception as e:
        print(f"❌ Erreur création client API: {e}")
        return
    
    # Ajouter chaque concurrent
    for i, channel_url in enumerate(competitors, 1):
        print(f"\n[{i}/{len(competitors)}] 📺 Traitement de {channel_url}")
        
        try:
            # Récupérer les informations de la chaîne
            print("🔍 Récupération des infos de la chaîne...")
            channel_info = youtube_client.get_channel_info(channel_url)
            
            # Récupérer les vidéos
            print("🎬 Récupération des vidéos...")
            videos = youtube_client.get_channel_videos(channel_url, max_results=500)
            
            # Sauvegarder en base
            print("💾 Sauvegarde en base de données...")
            competitor_id = save_competitor_and_videos(channel_url, videos, channel_info)
            
            print(f"✅ Succès: {channel_info.get('title', 'Chaîne')} ajoutée avec {len(videos)} vidéos (ID: {competitor_id})")
            
        except Exception as e:
            print(f"❌ Erreur pour {channel_url}: {e}")
            continue
    
    print("\n🎉 Restauration terminée !")
    print("🔍 Vérifiez sur http://127.0.0.1:8081/concurrents")

if __name__ == "__main__":
    restore_competitors()
