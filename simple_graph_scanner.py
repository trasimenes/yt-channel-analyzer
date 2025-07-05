#!/usr/bin/env python3
"""
Simple Graph Scanner - Version simplifiée pour extraire des données de graphiques
Clic & Glisser pour sélectionner une zone, puis balayage horizontal
"""

import time
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
    HAS_DEPENDENCIES = True
except ImportError as e:
    print(f"❌ Dépendance manquante: {e}")
    print("Installez avec: pip install pyautogui opencv-python pillow pytesseract")
    HAS_DEPENDENCIES = False

class SimpleGraphScanner:
    """Scanner de graphique simple avec sélection visuelle"""
    
    def __init__(self):
        self.output_dir = "graph_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Désactiver la protection pyautogui
        if HAS_DEPENDENCIES:
            pyautogui.FAILSAFE = False
    
    def select_region(self) -> Tuple[int, int, int, int]:
        """
        Permet à l'utilisateur de sélectionner une région en cliquant et glissant
        Retourne: (x, y, width, height)
        """
        print("🎯 Sélection de la région à analyser")
        print("Instructions:")
        print("1. Cliquez sur le coin en haut à gauche de la zone à analyser")
        print("2. Puis cliquez sur le coin en bas à droite")
        print()
        
        # Premier clic
        input("Appuyez sur Entrée, puis cliquez sur le coin HAUT-GAUCHE de la zone...")
        print("Cliquez maintenant...")
        
        # Attendre le clic
        start_time = time.time()
        while time.time() - start_time < 10:  # Timeout de 10 secondes
            try:
                x1, y1 = pyautogui.position()
                if pyautogui.click(x1, y1, duration=0.1):
                    break
            except:
                time.sleep(0.1)
        
        print(f"✅ Premier point: ({x1}, {y1})")
        
        # Deuxième clic
        input("Appuyez sur Entrée, puis cliquez sur le coin BAS-DROITE de la zone...")
        print("Cliquez maintenant...")
        
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                x2, y2 = pyautogui.position()
                if pyautogui.click(x2, y2, duration=0.1):
                    break
            except:
                time.sleep(0.1)
        
        print(f"✅ Deuxième point: ({x2}, {y2})")
        
        # Calculer la région
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        print(f"📐 Région sélectionnée: ({x}, {y}) - {width}x{height}")
        
        return (x, y, width, height)
    
    def scan_horizontal(self, region: Tuple[int, int, int, int], num_scans: int = 20) -> List[Dict]:
        """
        Balayage horizontal de la région avec captures
        
        Args:
            region: (x, y, width, height) de la zone à scanner
            num_scans: Nombre de captures à prendre
            
        Returns:
            Liste des données extraites
        """
        x, y, width, height = region
        
        print(f"🔄 Balayage horizontal: {num_scans} captures")
        print(f"📍 Zone: ({x}, {y}) - {width}x{height}")
        
        results = []
        
        for i in range(num_scans):
            # Position X progressive de gauche à droite
            scan_x = x + (i * width // num_scans)
            scan_y = y + height // 2  # Milieu de la hauteur
            
            # Prendre une capture de la zone autour de ce point
            capture_size = 100
            capture_x = max(0, scan_x - capture_size // 2)
            capture_y = max(0, scan_y - capture_size // 2)
            
            # Capture d'écran
            screenshot = pyautogui.screenshot(region=(capture_x, capture_y, capture_size, capture_size))
            
            # Sauvegarder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_{i:03d}_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            screenshot.save(filepath)
            
            # Extraction OCR
            try:
                ocr_text = pytesseract.image_to_string(screenshot, config='--psm 6')
                values = self._extract_numbers(ocr_text)
                main_value = values[0] if values else None
            except:
                ocr_text = ""
                main_value = None
            
            # Données du scan
            scan_data = {
                'index': i,
                'x': scan_x,
                'y': scan_y,
                'filename': filename,
                'ocr_text': ocr_text.strip(),
                'value': main_value,
                'timestamp': datetime.now().isoformat()
            }
            
            results.append(scan_data)
            
            print(f"📸 Scan {i+1}/{num_scans} - Position: ({scan_x}, {scan_y}) - Valeur: {main_value}")
            
            # Petite pause entre les scans
            time.sleep(0.1)
        
        return results
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extrait les nombres du texte OCR"""
        numbers = []
        
        # Patterns pour les nombres avec suffixes K, M
        patterns = [
            r'(\d+\.?\d*[KkMm])',  # 256K, 1.5M
            r'(\d+[,\.]\d+)',      # 1,234.56
            r'(\d+)',              # 1234
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if match.lower().endswith('k'):
                        value = float(match[:-1]) * 1000
                    elif match.lower().endswith('m'):
                        value = float(match[:-1]) * 1000000
                    else:
                        value = float(match.replace(',', ''))
                    numbers.append(value)
                except:
                    continue
        
        return numbers
    
    def run(self):
        """Lance le scanner interactif"""
        if not HAS_DEPENDENCIES:
            print("❌ Impossible de lancer le scanner sans les dépendances")
            return
        
        print("🎯 SIMPLE GRAPH SCANNER")
        print("=" * 30)
        print("Cet outil va :")
        print("1. Vous demander de sélectionner une zone")
        print("2. Faire un balayage horizontal")
        print("3. Extraire les valeurs numériques")
        print("4. Sauvegarder les résultats")
        print()
        
        try:
            # Sélection de la région
            region = self.select_region()
            
            # Confirmer
            print(f"\n📋 Région sélectionnée: {region}")
            confirm = input("Continuer avec cette région ? (o/n): ").lower()
            if confirm != 'o':
                print("❌ Annulé")
                return
            
            # Balayage
            print("\n🚀 Début du balayage dans 3 secondes...")
            time.sleep(3)
            
            results = self.scan_horizontal(region, num_scans=20)
            
            # Sauvegarder les résultats
            output_file = os.path.join(self.output_dir, f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'region': region,
                        'total_scans': len(results),
                        'scan_date': datetime.now().isoformat()
                    },
                    'results': results
                }, f, indent=2, ensure_ascii=False)
            
            # Afficher les résultats
            print(f"\n✅ Balayage terminé !")
            print(f"📊 {len(results)} scans effectués")
            print(f"💾 Résultats sauvegardés: {output_file}")
            
            # Afficher un échantillon
            values = [r['value'] for r in results if r['value'] is not None]
            if values:
                print(f"\n📈 Valeurs extraites: {len(values)} valeurs")
                print(f"   Min: {min(values)}")
                print(f"   Max: {max(values)}")
                print(f"   Moyenne: {sum(values)/len(values):.0f}")
            
        except KeyboardInterrupt:
            print("\n❌ Arrêté par l'utilisateur")
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    scanner = SimpleGraphScanner()
    scanner.run() 