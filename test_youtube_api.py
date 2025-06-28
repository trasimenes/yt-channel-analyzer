#!/usr/bin/env python3
"""
Script de test pour l'API YouTube Data v3
"""

import os
from dotenv import load_dotenv
from yt_channel_analyzer.youtube_api_client import create_youtube_client

# Charger les variables d'environnement
load_dotenv()

def test_youtube_api():
    """Test simple de l'API YouTube"""
    try:
        # Créer le client
        youtube = create_youtube_client()
        print("✅ Client YouTube API créé avec succès")
        
        # Test avec la chaîne Expedia
        channel_url = "https://www.youtube.com/@Expedia"
        print(f"🔍 Test avec: {channel_url}")
        
        # Récupérer les infos de la chaîne
        print("📊 Récupération des informations de la chaîne...")
        channel_info = youtube.get_channel_info(channel_url)
        
        print(f"📺 Chaîne: {channel_info['title']}")
        print(f"👥 Abonnés: {channel_info['subscriber_count']:,}")
        print(f"🎬 Vidéos: {channel_info['video_count']:,}")
        print(f"👀 Vues totales: {channel_info['view_count']:,}")
        
        # Récupérer quelques vidéos
        print("\n🎥 Récupération des dernières vidéos...")
        videos = youtube.get_channel_videos(channel_url, max_results=5)
        
        print(f"✅ {len(videos)} vidéos récupérées:")
        for i, video in enumerate(videos, 1):
            print(f"  {i}. {video['title']}")
            print(f"     👀 {video['view_count']:,} vues | 👍 {video['like_count']:,} likes")
            print(f"     📅 {video['published_at'][:10]}")
            print()
        
        # Afficher l'utilisation du quota
        quota = youtube.get_quota_usage()
        print(f"📊 Quota utilisé: {quota['quota_used']}/{quota['daily_limit']} unités")
        print(f"📈 Requêtes effectuées: {quota['requests_made']}")
        
        print("\n🎉 Test réussi ! L'API YouTube fonctionne parfaitement.")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n🔧 Solutions possibles:")
        print("1. Vérifiez que YOUTUBE_API_KEY est définie dans .env")
        print("2. Vérifiez que l'API YouTube Data v3 est activée")
        print("3. Vérifiez que votre clé API est valide")
        return False

if __name__ == "__main__":
    print("🚀 Test de l'API YouTube Data v3")
    print("=" * 50)
    
    # Vérifier la clé API
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY non trouvée dans .env")
        print("📝 Créez un fichier .env avec votre clé API")
        exit(1)
    elif api_key == "YOUR_YOUTUBE_API_KEY_HERE":
        print("❌ Remplacez YOUR_YOUTUBE_API_KEY_HERE par votre vraie clé API")
        exit(1)
    else:
        print(f"✅ Clé API trouvée: {api_key[:10]}...")
    
    print()
    test_youtube_api() 