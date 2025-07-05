#!/usr/bin/env python3
"""
Curve Follower - Suit automatiquement la courbe rouge
"""

import pyautogui
import cv2
import numpy as np
import time
import os
from PIL import Image
import json

class CurveFollower:
    """
    Suit automatiquement une courbe colorée sur l'écran
    """
    
    def __init__(self):
        self.output_dir = "curve_data"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
        
        # Configuration pour la détection de rouge YouTube
        self.red_lower = np.array([0, 0, 200])      # Rouge minimum (BGR)
        self.red_upper = np.array([80, 80, 255])    # Rouge maximum (BGR)
        self.tolerance = 30
        
    def detect_red_curve_in_region(self, region):
        """
        Détecte la courbe rouge dans une région donnée
        
        Args:
            region: (x, y, width, height) région à analyser
            
        Returns:
            List[tuple]: Points de la courbe (x, y) triés par x
        """
        # Capture de la région
        screenshot = pyautogui.screenshot(region=region)
        img_array = np.array(screenshot)
        
        # Conversion BGR pour OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Créer un masque pour le rouge
        mask = cv2.inRange(img_bgr, self.red_lower, self.red_upper)
        
        # Trouver les contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # Prendre le plus grand contour (la courbe principale)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Extraire les points et convertir en coordonnées écran
        curve_points = []
        for point in largest_contour:
            x, y = point[0]
            screen_x = region[0] + x
            screen_y = region[1] + y
            curve_points.append((screen_x, screen_y))
        
        # Trier par x (de gauche à droite)
        curve_points.sort(key=lambda p: p[0])
        
        return curve_points
    
    def follow_curve_with_screenshots(self, region, interval=0.25):
        """
        Suit la courbe rouge en prenant des captures à intervalles réguliers
        
        Args:
            region: (x, y, width, height) région contenant la courbe
            interval: Intervalle entre les captures en secondes
            
        Returns:
            List[dict]: Données extraites avec positions et captures
        """
        print(f"🎯 Détection de la courbe rouge dans la région {region}")
        
        # Détecter la courbe
        curve_points = self.detect_red_curve_in_region(region)
        
        if not curve_points:
            print("❌ Aucune courbe rouge détectée")
            return []
        
        print(f"✅ Courbe détectée avec {len(curve_points)} points")
        
        # Réduire le nombre de points pour un suivi fluide
        # Prendre un point tous les N pixels horizontaux
        simplified_points = []
        last_x = None
        min_distance = 20  # Minimum 20 pixels entre chaque point
        
        for x, y in curve_points:
            if last_x is None or abs(x - last_x) >= min_distance:
                simplified_points.append((x, y))
                last_x = x
        
        print(f"🎯 Suivi de {len(simplified_points)} points clés")
        
        # Suivre la courbe
        captured_data = []
        
        for i, (x, y) in enumerate(simplified_points):
            print(f"📍 Point {i+1}/{len(simplified_points)}: ({x}, {y})")
            
            # Déplacer la souris sur le point
            pyautogui.moveTo(x, y, duration=0.2)
            
            # Petite pause pour la stabilité
            time.sleep(0.1)
            
            # Capture d'écran centrée sur le point
            capture_region = (x - 150, y - 150, 300, 300)
            screenshot = pyautogui.screenshot(region=capture_region)
            
            # Sauvegarder la capture
            filename = f"curve_point_{i:03d}.png"
            filepath = os.path.join(self.output_dir, filename)
            screenshot.save(filepath)
            
            # Extraire les données visibles (OCR simple)
            ocr_text = self.extract_visible_text(screenshot)
            
            # Stocker les données
            point_data = {
                'index': i,
                'x': x,
                'y': y,
                'filename': filename,
                'ocr_text': ocr_text,
                'timestamp': time.time()
            }
            
            captured_data.append(point_data)
            
            # Attendre l'intervalle spécifié
            time.sleep(interval)
        
        # Sauvegarder les données
        self.save_curve_data(captured_data)
        
        return captured_data
    
    def extract_visible_text(self, screenshot):
        """
        Extrait le texte visible d'une capture d'écran
        Méthode simple qui cherche des patterns numériques
        """
        try:
            import pytesseract
            
            # Convertir en niveaux de gris pour améliorer l'OCR
            gray = screenshot.convert('L')
            
            # Améliorer le contraste
            gray = gray.point(lambda x: 0 if x < 128 else 255, '1')
            
            # OCR avec configuration pour les nombres
            text = pytesseract.image_to_string(
                gray, 
                config='--psm 8 -c tessedit_char_whitelist=0123456789.,KkMm%'
            )
            
            return text.strip()
            
        except Exception as e:
            # Fallback sans OCR
            return ""
    
    def save_curve_data(self, data):
        """
        Sauvegarde les données de la courbe au format JSON
        """
        timestamp = int(time.time())
        filename = f"curve_data_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'total_points': len(data),
                    'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'method': 'curve_following'
                },
                'points': data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Données sauvegardées dans {filepath}")
    
    def interactive_curve_follow(self):
        """
        Interface interactive pour suivre une courbe
        """
        print("🎯 SUIVI AUTOMATIQUE DE COURBE")
        print("=" * 50)
        print("Cette fonction va :")
        print("1. Détecter automatiquement la courbe rouge")
        print("2. Suivre la courbe point par point")
        print("3. Prendre des captures à chaque point")
        print("4. Extraire les données visibles")
        print()
        
        # Demander la région
        print("📋 Définissez la région contenant la courbe :")
        print("1. Cliquez sur le coin HAUT-GAUCHE de la région")
        input("   Appuyez sur Entrée quand vous êtes prêt...")
        
        top_left = pyautogui.position()
        print(f"   ✅ Coin haut-gauche : {top_left}")
        
        print("2. Cliquez sur le coin BAS-DROITE de la région")
        input("   Appuyez sur Entrée quand vous êtes prêt...")
        
        bottom_right = pyautogui.position()
        print(f"   ✅ Coin bas-droite : {bottom_right}")
        
        # Calculer la région
        region = (
            top_left.x,
            top_left.y,
            bottom_right.x - top_left.x,
            bottom_right.y - top_left.y
        )
        
        print(f"📐 Région sélectionnée : {region}")
        
        # Demander l'intervalle
        interval = input("⏱️ Intervalle entre captures (défaut 0.25s) : ").strip()
        if not interval:
            interval = 0.25
        else:
            interval = float(interval)
        
        print(f"\n🚀 Démarrage du suivi dans 3 secondes...")
        time.sleep(3)
        
        # Lancer le suivi
        data = self.follow_curve_with_screenshots(region, interval)
        
        if data:
            print(f"\n✅ Suivi terminé !")
            print(f"📊 {len(data)} points capturés")
            print(f"💾 Données dans le dossier '{self.output_dir}/'")
            
            # Afficher un échantillon des données
            print("\n📈 Échantillon des données :")
            for i, point in enumerate(data[:5]):
                print(f"  Point {i+1}: ({point['x']}, {point['y']}) - OCR: '{point['ocr_text']}'")
            
            if len(data) > 5:
                print(f"  ... et {len(data) - 5} autres points")
        
        return data

def demo_youtube_analytics():
    """
    Démonstration spécifique pour YouTube Analytics
    """
    print("🎯 DÉMONSTRATION : YouTube Analytics")
    print("=" * 50)
    print("Cette démonstration est optimisée pour les graphiques YouTube Analytics")
    print("avec des courbes rouges comme dans vos images.")
    print()
    
    follower = CurveFollower()
    
    # Configuration spécifique pour YouTube Analytics
    follower.red_lower = np.array([0, 0, 180])     # Rouge YouTube plus permissif
    follower.red_upper = np.array([100, 100, 255])
    
    print("📋 INSTRUCTIONS :")
    print("1. Ouvrez YouTube Analytics dans votre navigateur")
    print("2. Affichez le graphique d'abonnés (comme dans vos images)")
    print("3. Agrandissez le graphique pour une meilleure détection")
    print("4. Suivez les instructions pour définir la région")
    print()
    
    input("Appuyez sur Entrée pour commencer...")
    
    # Lancer le suivi interactif
    data = follower.interactive_curve_follow()
    
    return data

def main():
    """
    Menu principal
    """
    print("🎯 CURVE FOLLOWER - Suivi automatique de courbe")
    print("=" * 50)
    print("Options disponibles :")
    print("1. 📊 Suivi automatique générique")
    print("2. 🎬 Démonstration YouTube Analytics")
    print("3. 🚪 Quitter")
    print()
    
    choice = input("Votre choix (1-3) : ").strip()
    
    if choice == "1":
        follower = CurveFollower()
        follower.interactive_curve_follow()
    elif choice == "2":
        demo_youtube_analytics()
    elif choice == "3":
        print("👋 Au revoir !")
        return
    else:
        print("❌ Choix invalide")

if __name__ == "__main__":
    main() 