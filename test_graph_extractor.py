#!/usr/bin/env python3
"""
Test script for Graph Data Extractor
Vérifie que l'installation et les fonctionnalités de base fonctionnent
"""

import sys
import os
import time
import traceback

def test_imports():
    """Test des imports nécessaires"""
    print("🔍 Test des imports...")
    
    missing_deps = []
    
    try:
        import cv2
        print("✅ OpenCV installé")
    except ImportError:
        missing_deps.append("opencv-python")
        print("❌ OpenCV manquant")
    
    try:
        import pyautogui
        print("✅ PyAutoGUI installé")
    except ImportError:
        missing_deps.append("pyautogui")
        print("❌ PyAutoGUI manquant")
    
    try:
        import pytesseract
        print("✅ PyTesseract installé")
    except ImportError:
        missing_deps.append("pytesseract")
        print("❌ PyTesseract manquant")
    
    try:
        from PIL import Image
        print("✅ Pillow installé")
    except ImportError:
        missing_deps.append("pillow")
        print("❌ Pillow manquant")
    
    try:
        import numpy as np
        print("✅ NumPy installé")
    except ImportError:
        missing_deps.append("numpy")
        print("❌ NumPy manquant")
    
    if missing_deps:
        print(f"\n❌ Dépendances manquantes : {', '.join(missing_deps)}")
        print("Installation : pip install " + " ".join(missing_deps))
        return False
    
    print("✅ Tous les imports OK")
    return True

def test_screenshot():
    """Test de capture d'écran"""
    print("\n🔍 Test de capture d'écran...")
    
    try:
        import pyautogui
        
        # Prendre une capture d'écran
        screenshot = pyautogui.screenshot()
        print(f"✅ Capture d'écran réussie : {screenshot.size}")
        
        # Sauvegarder un test
        test_file = "test_screenshot.png"
        screenshot.save(test_file)
        print(f"✅ Sauvegarde réussie : {test_file}")
        
        # Nettoyer
        if os.path.exists(test_file):
            os.remove(test_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur capture d'écran : {e}")
        return False

def test_ocr():
    """Test OCR avec Tesseract"""
    print("\n🔍 Test OCR...")
    
    try:
        import pytesseract
        from PIL import Image, ImageDraw, ImageFont
        
        # Créer une image de test avec du texte
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Ajouter du texte simple
        draw.text((10, 30), "Test 123", fill='black')
        draw.text((10, 50), "8.56K", fill='black')
        
        # Sauvegarder temporairement
        test_file = "test_ocr.png"
        img.save(test_file)
        
        # Test OCR
        text = pytesseract.image_to_string(img)
        print(f"✅ OCR réussi : '{text.strip()}'")
        
        # Nettoyer
        if os.path.exists(test_file):
            os.remove(test_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur OCR : {e}")
        if "tesseract" in str(e).lower():
            print("💡 Tesseract n'est pas installé. Voir le guide d'installation.")
        return False

def test_opencv():
    """Test OpenCV"""
    print("\n🔍 Test OpenCV...")
    
    try:
        import cv2
        import numpy as np
        
        # Créer une image de test
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:, :] = (255, 0, 0)  # Rouge
        
        # Test de détection de couleur
        lower_red = np.array([0, 0, 200])
        upper_red = np.array([100, 100, 255])
        mask = cv2.inRange(img, lower_red, upper_red)
        
        # Compter les pixels rouges
        red_pixels = cv2.countNonZero(mask)
        print(f"✅ OpenCV fonctionne : {red_pixels} pixels rouges détectés")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur OpenCV : {e}")
        return False

def test_graph_extractor():
    """Test du module GraphDataExtractor"""
    print("\n🔍 Test GraphDataExtractor...")
    
    try:
        from yt_channel_analyzer.graph_data_extractor import GraphDataExtractor
        
        # Créer l'extracteur
        extractor = GraphDataExtractor()
        print("✅ GraphDataExtractor initialisé")
        
        # Test de configuration
        extractor.screenshot_interval = 0.5
        extractor.curve_color = (255, 0, 0)
        extractor.tolerance = 30
        print("✅ Configuration appliquée")
        
        # Test du dossier de sortie
        if os.path.exists(extractor.output_dir):
            print(f"✅ Dossier de sortie créé : {extractor.output_dir}")
        else:
            print("❌ Dossier de sortie non créé")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur GraphDataExtractor : {e}")
        traceback.print_exc()
        return False

def test_number_extraction():
    """Test d'extraction des nombres"""
    print("\n🔍 Test extraction des nombres...")
    
    try:
        from yt_channel_analyzer.graph_data_extractor import GraphDataExtractor
        
        extractor = GraphDataExtractor()
        
        # Test avec différents formats
        test_cases = [
            ("8.56K", [8560]),
            ("1.2M", [1200000]),
            ("123,456", [123456]),
            ("42", [42]),
            ("Test 8.56K views", [8560]),
            ("1.5M subscribers", [1500000]),
        ]
        
        for text, expected in test_cases:
            result = extractor._extract_numbers_from_text(text)
            if result == expected:
                print(f"✅ '{text}' -> {result}")
            else:
                print(f"❌ '{text}' -> {result} (attendu: {expected})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur extraction nombres : {e}")
        return False

def test_permissions():
    """Test des permissions système"""
    print("\n🔍 Test des permissions...")
    
    try:
        import pyautogui
        
        # Test de position de souris
        pos = pyautogui.position()
        print(f"✅ Position souris : {pos}")
        
        # Test de mouvement (petit)
        current_pos = pyautogui.position()
        pyautogui.moveTo(current_pos.x + 1, current_pos.y)
        time.sleep(0.1)
        pyautogui.moveTo(current_pos.x, current_pos.y)
        print("✅ Mouvement souris OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur permissions : {e}")
        print("💡 Vérifiez les permissions d'accessibilité sur macOS")
        return False

def main():
    """Fonction principale de test"""
    print("🎯 TEST GRAPH DATA EXTRACTOR")
    print("=" * 50)
    
    all_tests = [
        ("Imports", test_imports),
        ("Capture d'écran", test_screenshot),
        ("OCR", test_ocr),
        ("OpenCV", test_opencv),
        ("GraphDataExtractor", test_graph_extractor),
        ("Extraction nombres", test_number_extraction),
        ("Permissions", test_permissions),
    ]
    
    results = []
    
    for test_name, test_func in all_tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur dans {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé final
    print("\n🎯 RÉSUMÉ DES TESTS")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{test_name:<20} : {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 Résultats : {passed} réussis, {failed} échoués")
    
    if failed == 0:
        print("🎉 Tous les tests sont passés ! L'outil est prêt à utiliser.")
        print("💡 Lancez 'python demo_graph_extractor.py' pour une démonstration")
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez l'installation.")
        print("📖 Consultez GRAPH_EXTRACTOR_GUIDE.md pour l'aide")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 