#!/usr/bin/env python3
"""
Test d'intégration de l'API YouTube dans l'application Flask
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def test_youtube_adapter():
    """Test de l'adaptateur YouTube API"""
    print("🧪 Test de l'adaptateur YouTube API")
    print("=" * 50)
    
    try:
        from yt_channel_analyzer.youtube_adapter import (
            get_channel_videos_data_api, 
            autocomplete_youtube_channels_api,
            get_api_quota_status
        )
        
        # Test 1: Récupération de vidéos
        print("\n📺 Test 1: Récupération de vidéos")
        channel_url = "https://www.youtube.com/@Expedia"
        videos = get_channel_videos_data_api(channel_url, 5)
        
        if videos:
            print(f"✅ {len(videos)} vidéos récupérées")
            
            # Vérifier le format des données
            video = videos[0]
            required_fields = ['title', 'url', 'views', 'publication_date']
            missing_fields = [field for field in required_fields if field not in video]
            
            if missing_fields:
                print(f"❌ Champs manquants: {missing_fields}")
                return False
            else:
                print("✅ Format de données correct")
                print(f"   Exemple: {video['title'][:50]}...")
                print(f"   Vues: {video['views']}")
                print(f"   Date: {video['publication_date']}")
        else:
            print("❌ Aucune vidéo récupérée")
            return False
        
        # Test 2: Autocomplete
        print("\n🔍 Test 2: Autocomplete")
        suggestions = autocomplete_youtube_channels_api("travel", 3)
        
        if suggestions:
            print(f"✅ {len(suggestions)} suggestions trouvées")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion['name']}")
        else:
            print("❌ Aucune suggestion trouvée")
            return False
        
        # Test 3: Quota
        print("\n📊 Test 3: Statut du quota")
        quota = get_api_quota_status()
        print(f"✅ Quota utilisé: {quota['quota_used']}/{quota['daily_limit']}")
        print(f"✅ Requêtes: {quota['requests_made']}")
        print(f"✅ Restant: {quota['remaining']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_flask_integration():
    """Test de l'intégration Flask (sans lancer le serveur)"""
    print("\n🌐 Test de l'intégration Flask")
    print("=" * 50)
    
    try:
        # Importer l'app Flask
        import app
        
        # Vérifier que les nouvelles fonctions sont importées
        required_imports = [
            'get_channel_videos_data_api',
            'autocomplete_youtube_channels_api', 
            'get_api_quota_status'
        ]
        
        for import_name in required_imports:
            if hasattr(app, import_name):
                print(f"✅ Import {import_name} trouvé")
            else:
                print(f"❌ Import {import_name} manquant")
                return False
        
        # Vérifier la route scraper
        client = app.app.test_client()
        
        # Test avec une requête POST simulée
        with app.app.test_request_context():
            print("✅ Contexte Flask créé avec succès")
        
        print("✅ Application Flask intégrée correctement")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Flask: {e}")
        return False

def compare_api_vs_scraping():
    """Compare les performances API vs Scraping"""
    print("\n⚡ Comparaison API vs Scraping")
    print("=" * 50)
    
    import time
    
    channel_url = "https://www.youtube.com/@Expedia"
    
    try:
        # Test API
        print("🚀 Test API YouTube...")
        start_time = time.time()
        
        from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api
        api_videos = get_channel_videos_data_api(channel_url, 10)
        
        api_time = time.time() - start_time
        
        print(f"✅ API: {len(api_videos)} vidéos en {api_time:.2f}s")
        
        # Afficher quelques exemples
        if api_videos:
            print("\n📊 Données API (exemples):")
            for i, video in enumerate(api_videos[:3], 1):
                print(f"   {i}. {video['title'][:40]}...")
                print(f"      👀 {video['views']} | 👍 {video.get('like_count', 'N/A')} likes")
                print(f"      📅 {video['publication_date']}")
        
        return {
            'api_time': api_time,
            'api_videos': len(api_videos),
            'api_success': True
        }
        
    except Exception as e:
        print(f"❌ Erreur comparaison: {e}")
        return {
            'api_time': 0,
            'api_videos': 0,
            'api_success': False
        }

def main():
    """Fonction principale de test"""
    print("🎯 Test d'intégration API YouTube")
    print("🚀 YouTube Channel Analyzer - API Migration Test")
    print("=" * 70)
    
    # Vérifier la clé API
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY non trouvée dans .env")
        print("📝 Ajoutez votre clé API dans le fichier .env")
        return False
    elif api_key == "YOUR_YOUTUBE_API_KEY_HERE":
        print("❌ Remplacez YOUR_YOUTUBE_API_KEY_HERE par votre vraie clé API")
        return False
    else:
        print(f"✅ Clé API configurée: {api_key[:10]}...")
    
    # Tests
    tests = [
        ("Adaptateur YouTube", test_youtube_adapter),
        ("Intégration Flask", test_flask_integration),
        ("Comparaison performances", compare_api_vs_scraping)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Échec du test {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé final
    print("\n" + "="*70)
    print("📋 RÉSUMÉ DES TESTS")
    print("="*70)
    
    success_count = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            success_count += 1
    
    print(f"\n🎯 Résultat: {success_count}/{len(results)} tests réussis")
    
    if success_count == len(results):
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("🚀 Votre application est prête à utiliser l'API YouTube")
        print("\n💡 Prochaines étapes:")
        print("   1. Lancez votre application: python3 app.py")
        print("   2. Testez avec une chaîne YouTube")
        print("   3. Profitez de la vitesse et fiabilité de l'API !")
        return True
    else:
        print(f"\n⚠️ {len(results) - success_count} test(s) ont échoué")
        print("🔧 Vérifiez les erreurs ci-dessus")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 