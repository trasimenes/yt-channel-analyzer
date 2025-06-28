#!/usr/bin/env python3
"""
Script de test rapide pour vérifier que l'application fonctionne
"""

def test_app_import():
    """Test l'import de l'app principal"""
    try:
        import app
        print("✅ Import app.py réussi")
        return True
    except Exception as e:
        print(f"❌ Erreur import app.py: {e}")
        return False

def test_cache_functions():
    """Test les fonctions de cache"""
    try:
        from app import load_cache, save_cache
        
        # Test load cache
        cache_data = load_cache()
        print(f"✅ Cache chargé: {len(cache_data)} entrées")
        
        # Test fonctions utilitaires  
        from app import format_number, get_channel_key
        
        test_number = format_number(1234567)
        print(f"✅ Format number: 1234567 → {test_number}")
        
        test_key = get_channel_key("https://www.youtube.com/@test")
        print(f"✅ Channel key: @test → {test_key}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur fonctions cache: {e}")
        return False

def test_classifier():
    """Test le classificateur AI"""
    try:
        from yt_channel_analyzer.ai_classifier import industry_classifier
        
        # Test classification
        test_industry = industry_classifier.classify_industry("Club Med", "vacation resort", [])
        print(f"✅ Classifier: Club Med → {test_industry}")
        
        test_region = industry_classifier.get_region_from_name("Club Med France")
        print(f"✅ Region: Club Med France → {test_region}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur classifier: {e}")
        return False

def main():
    print("🔍 Tests rapides de l'application YT Channel Analyzer")
    print("=" * 50)
    
    tests = [
        ("Import app principal", test_app_import),
        ("Fonctions cache", test_cache_functions), 
        ("Classificateur AI", test_classifier),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Test: {test_name}")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés ! L'application semble fonctionnelle.")
        return True
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return False

if __name__ == "__main__":
    main() 