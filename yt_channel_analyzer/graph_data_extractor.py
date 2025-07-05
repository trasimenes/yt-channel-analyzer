#!/usr/bin/env python3
"""
Graph Data Extractor - Outil pour extraire des données de graphiques
Permet de simuler une souris qui suit une courbe ou d'extraire des données par OCR
"""

import time
import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image, ImageDraw
import json
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import threading
import queue
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

class GraphDataExtractor:
    """
    Extracteur de données de graphiques avec plusieurs méthodes :
    1. Balayage horizontal avec captures périodiques
    2. Suivi automatique de courbe par détection de couleur
    3. Extraction OCR des valeurs
    4. Consolidation des données
    """
    
    def __init__(self, output_dir: str = "graph_extractions"):
        self.output_dir = output_dir
        self.screenshots = []
        self.data_points = []
        self.is_scanning = False
        self.scan_thread = None
        
        # Configuration par défaut
        self.screenshot_interval = 0.25  # 1/4 de seconde
        self.curve_color = (255, 0, 0)  # Rouge par défaut
        self.tolerance = 30  # Tolérance de couleur
        
        # Créer le dossier de sortie
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Désactiver la protection contre les mouvements de souris
        pyautogui.FAILSAFE = False
    
    def horizontal_scan_with_screenshots(self, 
                                       start_x: int, 
                                       start_y: int, 
                                       end_x: int, 
                                       end_y: int,
                                       duration: float = 10.0,
                                       extract_ocr: bool = True) -> List[Dict]:
        """
        Balaye horizontalement de gauche à droite en prenant des captures d'écran périodiques.
        
        Args:
            start_x, start_y: Position de départ
            end_x, end_y: Position de fin
            duration: Durée totale du balayage en secondes
            extract_ocr: Si True, extrait les valeurs par OCR
            
        Returns:
            Liste des points de données extraits
        """
        print(f"🎯 Début du balayage horizontal de ({start_x}, {start_y}) à ({end_x}, {end_y})")
        print(f"📸 Capture toutes les {self.screenshot_interval}s pendant {duration}s")
        
        # Calculer le nombre de captures
        num_captures = int(duration / self.screenshot_interval)
        step_x = (end_x - start_x) / num_captures
        step_y = (end_y - start_y) / num_captures
        
        # Réinitialiser les données
        self.screenshots = []
        self.data_points = []
        
        # Démarrer le balayage
        start_time = time.time()
        
        for i in range(num_captures):
            # Calculer la position actuelle
            current_x = start_x + (i * step_x)
            current_y = start_y + (i * step_y)
            
            # Déplacer la souris
            pyautogui.moveTo(current_x, current_y, duration=0.1)
            
            # Prendre une capture d'écran
            screenshot = pyautogui.screenshot()
            timestamp = time.time() - start_time
            
            # Sauvegarder la capture
            filename = f"scan_{i:04d}_{timestamp:.2f}s.png"
            filepath = os.path.join(self.output_dir, filename)
            screenshot.save(filepath)
            
            # Stocker les infos
            capture_data = {
                'index': i,
                'timestamp': timestamp,
                'x': current_x,
                'y': current_y,
                'filename': filename,
                'filepath': filepath
            }
            
            # Extraction OCR si demandée
            if extract_ocr:
                ocr_data = self._extract_ocr_from_screenshot(screenshot, current_x, current_y)
                capture_data.update(ocr_data)
            
            self.screenshots.append(capture_data)
            
            # Attendre jusqu'à la prochaine capture
            time.sleep(self.screenshot_interval)
            
            print(f"📸 Capture {i+1}/{num_captures} - Position: ({current_x:.0f}, {current_y:.0f})")
        
        print(f"✅ Balayage terminé ! {len(self.screenshots)} captures sauvegardées")
        
        # Consolidation finale
        self._consolidate_data()
        
        return self.data_points
    
    def detect_and_follow_curve(self, 
                              region: Tuple[int, int, int, int],
                              curve_color: Tuple[int, int, int] = (255, 0, 0),
                              tolerance: int = 30) -> List[Dict]:
        """
        Détecte automatiquement une courbe et la suit de gauche à droite.
        
        Args:
            region: (x, y, width, height) région à analyser
            curve_color: Couleur de la courbe à suivre (RGB)
            tolerance: Tolérance pour la détection de couleur
            
        Returns:
            Liste des points de données de la courbe
        """
        print(f"🎯 Détection de courbe couleur {curve_color} dans la région {region}")
        
        # Prendre une capture de la région
        screenshot = pyautogui.screenshot(region=region)
        img_array = np.array(screenshot)
        
        # Conversion BGR pour OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Créer un masque pour la couleur de la courbe
        lower_color = np.array([max(0, c - tolerance) for c in curve_color[::-1]])  # BGR
        upper_color = np.array([min(255, c + tolerance) for c in curve_color[::-1]])  # BGR
        
        mask = cv2.inRange(img_bgr, lower_color, upper_color)
        
        # Trouver les contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("❌ Aucune courbe détectée avec cette couleur")
            return []
        
        # Prendre le plus grand contour (probablement la courbe principale)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Extraire les points et les trier par x
        points = []
        for point in largest_contour:
            x, y = point[0]
            # Convertir en coordonnées écran
            screen_x = region[0] + x
            screen_y = region[1] + y
            points.append((screen_x, screen_y))
        
        # Trier par x (de gauche à droite)
        points.sort(key=lambda p: p[0])
        
        print(f"📊 {len(points)} points détectés sur la courbe")
        
        # Extraire les données à intervalles réguliers
        self.data_points = []
        interval = max(1, len(points) // 50)  # Maximum 50 points
        
        for i in range(0, len(points), interval):
            x, y = points[i]
            
            # Prendre une capture centrée sur ce point
            capture_region = (x - 100, y - 100, 200, 200)
            screenshot = pyautogui.screenshot(region=capture_region)
            
            # Extraction OCR
            ocr_data = self._extract_ocr_from_screenshot(screenshot, x, y)
            
            data_point = {
                'x': x,
                'y': y,
                'timestamp': time.time(),
                **ocr_data
            }
            
            self.data_points.append(data_point)
            
            print(f"📍 Point {len(self.data_points)}: ({x}, {y}) - Valeur: {ocr_data.get('value', 'N/A')}")
        
        return self.data_points
    
    def _extract_ocr_from_screenshot(self, screenshot: Image.Image, x: int, y: int) -> Dict:
        """
        Extrait les valeurs numériques d'une capture d'écran par OCR.
        
        Args:
            screenshot: Image PIL
            x, y: Position du curseur
            
        Returns:
            Dictionnaire avec les valeurs extraites
        """
        try:
            # Prendre une région autour du curseur pour l'OCR
            region_size = 150
            left = max(0, x - region_size)
            top = max(0, y - region_size)
            right = min(screenshot.width, x + region_size)
            bottom = min(screenshot.height, y + region_size)
            
            # Recadrer la région d'intérêt
            ocr_region = screenshot.crop((left, top, right, bottom))
            
            # Améliorer l'image pour l'OCR
            ocr_region = ocr_region.convert('L')  # Niveaux de gris
            ocr_region = ocr_region.point(lambda x: 0 if x < 128 else 255, '1')  # Binarisation
            
            # Extraction OCR
            text = pytesseract.image_to_string(ocr_region, config='--psm 8 -c tessedit_char_whitelist=0123456789.,KkMm%')
            
            # Chercher des valeurs numériques
            values = self._extract_numbers_from_text(text)
            
            return {
                'ocr_text': text.strip(),
                'value': values[0] if values else None,
                'all_values': values,
                'ocr_region': (left, top, right, bottom)
            }
            
        except Exception as e:
            print(f"❌ Erreur OCR: {e}")
            return {
                'ocr_text': '',
                'value': None,
                'all_values': [],
                'error': str(e)
            }
    
    def _extract_numbers_from_text(self, text: str) -> List[float]:
        """
        Extrait les nombres d'un texte OCR.
        
        Args:
            text: Texte brut de l'OCR
            
        Returns:
            Liste des nombres trouvés
        """
        values = []
        
        # Patterns pour différents formats de nombres
        patterns = [
            r'(\d+\.?\d*[KkMm]?)',  # Nombres avec K, M
            r'(\d+[,\.]\d+)',        # Décimaux
            r'(\d+)',                # Entiers
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # Convertir les suffixes K, M
                    if match.lower().endswith('k'):
                        value = float(match[:-1]) * 1000
                    elif match.lower().endswith('m'):
                        value = float(match[:-1]) * 1000000
                    else:
                        value = float(match.replace(',', '.'))
                    
                    values.append(value)
                except ValueError:
                    continue
        
        return values
    
    def _consolidate_data(self):
        """
        Consolide toutes les données extraites dans un format structuré.
        """
        print("📊 Consolidation des données...")
        
        # Trier par timestamp
        self.screenshots.sort(key=lambda x: x['timestamp'])
        
        # Extraire les valeurs uniques
        values = []
        timestamps = []
        
        for capture in self.screenshots:
            if capture.get('value') is not None:
                values.append(capture['value'])
                timestamps.append(capture['timestamp'])
        
        # Créer les points de données consolidés
        self.data_points = []
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):
            self.data_points.append({
                'index': i,
                'timestamp': timestamp,
                'value': value,
                'source': 'horizontal_scan'
            })
        
        print(f"✅ {len(self.data_points)} points de données consolidés")
        
        # Sauvegarder en JSON
        output_file = os.path.join(self.output_dir, f"consolidated_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'total_screenshots': len(self.screenshots),
                    'total_data_points': len(self.data_points),
                    'extraction_date': datetime.now().isoformat(),
                    'screenshot_interval': self.screenshot_interval
                },
                'screenshots': self.screenshots,
                'data_points': self.data_points
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Données sauvegardées dans {output_file}")
    
    def interactive_setup(self):
        """
        Interface interactive pour configurer l'extraction.
        """
        print("🎯 Configuration interactive de l'extraction de graphique")
        print("=" * 50)
        
        # Demander le type d'extraction
        print("\nTypes d'extraction disponibles :")
        print("1. Balayage horizontal avec captures périodiques")
        print("2. Détection automatique de courbe")
        print("3. Extraction depuis une vidéo")
        
        choice = input("\nChoisissez une option (1-3): ").strip()
        
        if choice == "1":
            self._setup_horizontal_scan()
        elif choice == "2":
            self._setup_curve_detection()
        elif choice == "3":
            self._setup_video_extraction()
        else:
            print("❌ Option invalide")
    
    def _setup_horizontal_scan(self):
        """
        Configuration du balayage horizontal.
        """
        print("\n🎯 Configuration du balayage horizontal")
        print("Cliquez sur le point de départ, puis sur le point d'arrivée")
        
        input("Appuyez sur Entrée quand vous êtes prêt à cliquer le point de départ...")
        start_pos = self._wait_for_click()
        print(f"Point de départ: {start_pos}")
        
        input("Appuyez sur Entrée quand vous êtes prêt à cliquer le point d'arrivée...")
        end_pos = self._wait_for_click()
        print(f"Point d'arrivée: {end_pos}")
        
        # Demander la durée
        duration = float(input("Durée du balayage en secondes (défaut: 10): ") or "10")
        
        # Lancer l'extraction
        print(f"\n🚀 Lancement du balayage dans 3 secondes...")
        time.sleep(3)
        
        self.horizontal_scan_with_screenshots(
            start_pos[0], start_pos[1],
            end_pos[0], end_pos[1],
            duration=duration
        )
    
    def _setup_curve_detection(self):
        """
        Configuration de la détection de courbe.
        """
        print("\n🎯 Configuration de la détection de courbe")
        print("Cliquez sur deux coins opposés de la région à analyser")
        
        input("Appuyez sur Entrée pour cliquer le coin haut-gauche...")
        top_left = self._wait_for_click()
        
        input("Appuyez sur Entrée pour cliquer le coin bas-droite...")
        bottom_right = self._wait_for_click()
        
        # Calculer la région
        region = (
            top_left[0], top_left[1],
            bottom_right[0] - top_left[0],
            bottom_right[1] - top_left[1]
        )
        
        print(f"Région sélectionnée: {region}")
        
        # Demander la couleur de la courbe
        print("\nCouleur de la courbe :")
        print("1. Rouge (défaut)")
        print("2. Bleu")
        print("3. Vert")
        print("4. Personnalisée")
        
        color_choice = input("Choisissez (1-4): ").strip() or "1"
        
        color_map = {
            "1": (255, 0, 0),
            "2": (0, 0, 255),
            "3": (0, 255, 0),
        }
        
        if color_choice in color_map:
            curve_color = color_map[color_choice]
        else:
            # Couleur personnalisée
            r = int(input("Rouge (0-255): ") or "255")
            g = int(input("Vert (0-255): ") or "0")
            b = int(input("Bleu (0-255): ") or "0")
            curve_color = (r, g, b)
        
        print(f"\n🚀 Détection de la courbe...")
        self.detect_and_follow_curve(region, curve_color)
    
    def _wait_for_click(self) -> Tuple[int, int]:
        """
        Attend que l'utilisateur clique et retourne la position.
        """
        print("Cliquez sur la position souhaitée...")
        
        # Attendre un clic
        while True:
            try:
                # Vérifier si la souris est cliquée
                if pyautogui.click is not None:
                    time.sleep(0.1)
                    pos = pyautogui.position()
                    # Attendre que l'utilisateur clique réellement
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    root.update()
                    
                    # Méthode simple: attendre un changement de position
                    initial_pos = pyautogui.position()
                    while pyautogui.position() == initial_pos:
                        time.sleep(0.1)
                    
                    return pyautogui.position()
            except:
                time.sleep(0.1)
    
    def extract_from_video(self, video_path: str, frame_interval: int = 30) -> List[Dict]:
        """
        Extrait des données d'une vidéo de graphique.
        
        Args:
            video_path: Chemin vers la vidéo
            frame_interval: Intervalle entre les frames analysées
            
        Returns:
            Liste des données extraites
        """
        print(f"🎬 Extraction depuis la vidéo: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        data_points = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                # Convertir en PIL pour OCR
                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # Extraction OCR sur toute la frame
                ocr_data = self._extract_ocr_from_screenshot(frame_pil, frame.shape[1]//2, frame.shape[0]//2)
                
                if ocr_data['value'] is not None:
                    data_points.append({
                        'frame': frame_count,
                        'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS),
                        'value': ocr_data['value'],
                        'source': 'video'
                    })
                    
                    print(f"📍 Frame {frame_count}: {ocr_data['value']}")
            
            frame_count += 1
        
        cap.release()
        
        print(f"✅ Extraction terminée: {len(data_points)} points extraits")
        return data_points

# Fonction utilitaire pour utilisation simple
def quick_horizontal_scan(duration: float = 10.0) -> List[Dict]:
    """
    Fonction rapide pour un balayage horizontal simple.
    
    Args:
        duration: Durée du balayage en secondes
        
    Returns:
        Liste des points de données extraits
    """
    extractor = GraphDataExtractor()
    
    print("🎯 Balayage horizontal rapide")
    print("1. Positionnez votre souris au point de départ")
    input("Appuyez sur Entrée quand vous êtes prêt...")
    start_pos = pyautogui.position()
    
    print("2. Positionnez votre souris au point d'arrivée")
    input("Appuyez sur Entrée quand vous êtes prêt...")
    end_pos = pyautogui.position()
    
    print("🚀 Démarrage dans 3 secondes...")
    time.sleep(3)
    
    return extractor.horizontal_scan_with_screenshots(
        start_pos[0], start_pos[1],
        end_pos[0], end_pos[1],
        duration=duration
    )

if __name__ == "__main__":
    # Exemple d'utilisation
    extractor = GraphDataExtractor()
    extractor.interactive_setup() 