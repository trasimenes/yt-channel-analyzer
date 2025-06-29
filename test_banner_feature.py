#!/usr/bin/env python3
"""
Script de test pour vérifier la récupération des images de bannière
"""

import os
from dotenv import load_dotenv
from yt_channel_analyzer.youtube_api_client import create_youtube_client

# Charger les variables d'environnement
load_dotenv()

def test_banner_feature():
    """Test de la fonctionnalité de récupération des bannières"""
    try:
        # Créer le client
        youtube = create_youtube_client()
        print("✅ Client YouTube API créé avec succès")
        
        # Test avec plusieurs chaînes connues
        test_channels = [
            "https://www.youtube.com/@Expedia",
            "https://www.youtube.com/@AccorHotels",
            "https://www.youtube.com/@CenterParcs",
            "https://www.youtube.com/@ClubMedFr"
        ]
        
        for channel_url in test_channels:
            print(f"\n🔍 Test avec: {channel_url}")
            
            try:
                # Récupérer les infos de la chaîne
                channel_info = youtube.get_channel_info(channel_url)
                
                print(f"📺 Chaîne: {channel_info['title']}")
                print(f"🖼️  Avatar (thumbnail): {channel_info.get('thumbnail', 'Non disponible')}")
                print(f"🎨 Bannière: {channel_info.get('banner', 'Non disponible')}")
                
                if channel_info.get('banner'):
                    print("✅ Bannière disponible pour cette chaîne")
                else:
                    print("⚠️ Pas de bannière disponible pour cette chaîne")
                    
            except Exception as e:
                print(f"❌ Erreur pour {channel_url}: {e}")
        
        print("\n🎉 Test terminé ! Vérifiez les résultats ci-dessus.")
        return True
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Test de la fonctionnalité d'image de bannière")
    test_banner_feature() 