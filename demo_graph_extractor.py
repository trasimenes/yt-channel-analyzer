#!/usr/bin/env python3
"""
Démonstration du Graph Data Extractor
Script pour tester l'extraction de données de graphiques
"""

import time
import json
from yt_channel_analyzer.graph_data_extractor import GraphDataExtractor, quick_horizontal_scan

def demo_horizontal_scan():
    """
    Démonstration du balayage horizontal
    """
    print("🎯 DÉMONSTRATION : Balayage horizontal")
    print("=" * 50)
    print("Cette démonstration va :")
    print("1. Balayer horizontalement sur votre écran")
    print("2. Prendre des captures tous les 1/4 de seconde")
    print("3. Extraire les valeurs par OCR")
    print("4. Consolider les données")
    print()
    
    # Configuration
    extractor = GraphDataExtractor()
    extractor.screenshot_interval = 0.25  # 1/4 de seconde
    
    print("📋 Instructions :")
    print("1. Ouvrez votre graphique dans un navigateur")
    print("2. Positionnez-vous pour voir toute la courbe")
    print("3. Suivez les instructions pour définir le début et la fin")
    print()
    
    input("Appuyez sur Entrée pour commencer...")
    
    # Lancer la configuration interactive
    extractor._setup_horizontal_scan()
    
    # Afficher les résultats
    if extractor.data_points:
        print(f"\n✅ Extraction terminée !")
        print(f"📊 {len(extractor.data_points)} points de données extraits")
        
        # Afficher les premiers résultats
        print("\n📈 Échantillon des données :")
        for i, point in enumerate(extractor.data_points[:5]):
            print(f"  Point {i+1}: {point.get('value', 'N/A')} (t={point.get('timestamp', 0):.2f}s)")
        
        if len(extractor.data_points) > 5:
            print(f"  ... et {len(extractor.data_points) - 5} autres points")

def demo_curve_detection():
    """
    Démonstration de la détection automatique de courbe
    """
    print("🎯 DÉMONSTRATION : Détection automatique de courbe")
    print("=" * 50)
    print("Cette démonstration va :")
    print("1. Analyser une région de votre écran")
    print("2. Détecter automatiquement la courbe rouge")
    print("3. Extraire les points de données")
    print()
    
    extractor = GraphDataExtractor()
    
    print("📋 Instructions :")
    print("1. Ouvrez votre graphique avec une courbe rouge")
    print("2. Définissez la région à analyser")
    print()
    
    input("Appuyez sur Entrée pour commencer...")
    
    # Lancer la configuration interactive
    extractor._setup_curve_detection()
    
    # Afficher les résultats
    if extractor.data_points:
        print(f"\n✅ Détection terminée !")
        print(f"📊 {len(extractor.data_points)} points détectés")

def demo_quick_scan():
    """
    Démonstration du balayage rapide
    """
    print("🎯 DÉMONSTRATION : Balayage rapide")
    print("=" * 50)
    print("Cette fonction simple vous permet de :")
    print("1. Définir rapidement début et fin")
    print("2. Lancer un balayage de 10 secondes")
    print("3. Obtenir les résultats")
    print()
    
    input("Appuyez sur Entrée pour commencer...")
    
    # Utiliser la fonction rapide
    data_points = quick_horizontal_scan(duration=10.0)
    
    if data_points:
        print(f"\n✅ Balayage rapide terminé !")
        print(f"📊 {len(data_points)} points extraits")
        
        # Sauvegarder les résultats
        output_file = f"quick_scan_results_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump(data_points, f, indent=2)
        
        print(f"💾 Résultats sauvegardés dans {output_file}")

def demo_video_extraction():
    """
    Démonstration de l'extraction depuis une vidéo
    """
    print("🎯 DÉMONSTRATION : Extraction depuis vidéo")
    print("=" * 50)
    print("Cette fonction permet d'extraire des données depuis :")
    print("1. Une vidéo de graphique")
    print("2. Un screencast d'analytics")
    print("3. Une présentation avec graphiques")
    print()
    
    video_path = input("Entrez le chemin vers votre vidéo (ou Entrée pour passer) : ").strip()
    
    if not video_path:
        print("❌ Pas de vidéo spécifiée, démonstration annulée")
        return
    
    if not video_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        print("❌ Format de vidéo non supporté")
        return
    
    extractor = GraphDataExtractor()
    
    print("🎬 Analyse de la vidéo...")
    data_points = extractor.extract_from_video(video_path)
    
    if data_points:
        print(f"\n✅ Extraction vidéo terminée !")
        print(f"📊 {len(data_points)} points extraits")

def main():
    """
    Menu principal de démonstration
    """
    print("🎯 GRAPH DATA EXTRACTOR - Démonstration")
    print("=" * 50)
    print("Choisissez une démonstration :")
    print()
    print("1. 📸 Balayage horizontal avec captures (recommandé)")
    print("2. 🎯 Détection automatique de courbe")
    print("3. ⚡ Balayage rapide (simple)")
    print("4. 🎬 Extraction depuis vidéo")
    print("5. ℹ️  Informations d'installation")
    print("6. 🚪 Quitter")
    print()
    
    choice = input("Votre choix (1-6) : ").strip()
    
    if choice == "1":
        demo_horizontal_scan()
    elif choice == "2":
        demo_curve_detection()
    elif choice == "3":
        demo_quick_scan()
    elif choice == "4":
        demo_video_extraction()
    elif choice == "5":
        show_installation_info()
    elif choice == "6":
        print("👋 Au revoir !")
        return
    else:
        print("❌ Choix invalide")
        return
    
    # Demander si l'utilisateur veut continuer
    if input("\nVoulez-vous essayer une autre démonstration ? (o/N) : ").lower().startswith('o'):
        main()

def show_installation_info():
    """
    Affiche les informations d'installation
    """
    print("ℹ️  INFORMATIONS D'INSTALLATION")
    print("=" * 50)
    print("Pour utiliser ce tool, vous devez installer :")
    print()
    print("1. 📦 Dépendances Python :")
    print("   pip install opencv-python pyautogui pytesseract pillow")
    print()
    print("2. 🔧 Tesseract OCR :")
    print("   macOS: brew install tesseract")
    print("   Ubuntu: sudo apt-get install tesseract-ocr")
    print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    print()
    print("3. 🐍 Ou utiliser les requirements du projet :")
    print("   pip install -r requirements.txt")
    print()
    print("4. 🖥️  Permissions écran (macOS) :")
    print("   Autorisez l'accès à l'écran dans Préférences Système")
    print()
    print("5. ✅ Test rapide :")
    print("   python demo_graph_extractor.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Démonstration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        print("Vérifiez que toutes les dépendances sont installées") 