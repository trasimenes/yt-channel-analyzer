#!/usr/bin/env python3
"""
Screen Overlay - Rectangle rouge avec poignées sans tkinter
Utilise PIL + threading pour créer une overlay native
"""

import pyautogui
import time
import os
import json
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys

class ScreenOverlay:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "screen_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
        
        # Rectangle par défaut
        screen_w, screen_h = pyautogui.size()
        self.rect = {
            'x': screen_w // 4,
            'y': screen_h // 4,
            'width': screen_w // 2,
            'height': screen_h // 2
        }
        
        print(f"🔴 Rectangle initial: {self.rect}")
        
    def show_overlay_preview(self):
        """Afficher un aperçu de l'overlay avec capture d'écran"""
        print("📸 Création de l'aperçu overlay...")
        
        # Capturer l'écran
        screenshot = pyautogui.screenshot()
        draw = ImageDraw.Draw(screenshot)
        
        # Dessiner le rectangle rouge
        x, y, w, h = self.rect['x'], self.rect['y'], self.rect['width'], self.rect['height']
        
        # Rectangle principal
        draw.rectangle([x, y, x + w, y + h], outline='red', width=8)
        
        # Poignées
        handle_size = 20
        handles = [
            (x + w - handle_size, y + h - handle_size),  # Bas-droite
            (x + w//2 - handle_size//2, y + h - handle_size),  # Bas centre
            (x + w - handle_size, y + h//2 - handle_size//2),  # Droite centre
        ]
        
        for hx, hy in handles:
            draw.rectangle([hx, hy, hx + handle_size, hy + handle_size], 
                         fill='white', outline='red', width=3)
        
        # Texte central
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text = "🔴 ZONE DE SCAN"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x = x + (w - text_w) // 2
        text_y = y + (h - text_h) // 2
        
        draw.text((text_x, text_y), text, fill='red', font=font)
        
        # Sauvegarder l'aperçu
        preview_file = os.path.join(self.output_dir, "overlay_preview.png")
        screenshot.save(preview_file)
        
        print(f"✅ Aperçu sauvé: {preview_file}")
        return preview_file
    
    def interactive_setup(self):
        """Configuration interactive du rectangle"""
        print("\n🎯 CONFIGURATION DU RECTANGLE ROUGE")
        print("=" * 50)
        
        screen_w, screen_h = pyautogui.size()
        print(f"📱 Écran détecté: {screen_w} × {screen_h} pixels")
        print(f"📐 Rectangle actuel: {self.rect}")
        
        while True:
            print("\n⚙️ Options:")
            print("1. 📏 Modifier position/taille")
            print("2. 🎯 Presets YouTube Analytics")
            print("3. 📸 Voir aperçu")
            print("4. 🚀 Lancer scan")
            print("5. ❌ Quitter")
            
            choice = input("\nVotre choix (1-5): ").strip()
            
            if choice == '1':
                self.modify_rectangle(screen_w, screen_h)
            elif choice == '2':
                self.youtube_presets()
            elif choice == '3':
                preview_file = self.show_overlay_preview()
                self.open_file(preview_file)
            elif choice == '4':
                self.start_scan()
                break
            elif choice == '5':
                print("👋 Au revoir!")
                break
            else:
                print("❌ Choix invalide")
    
    def modify_rectangle(self, screen_w, screen_h):
        """Modifier le rectangle"""
        print("\n📏 MODIFICATION DU RECTANGLE")
        print("-" * 30)
        
        try:
            x = int(input(f"Position X (0-{screen_w}) [{self.rect['x']}]: ") or self.rect['x'])
            y = int(input(f"Position Y (0-{screen_h}) [{self.rect['y']}]: ") or self.rect['y'])
            w = int(input(f"Largeur (100-{screen_w}) [{self.rect['width']}]: ") or self.rect['width'])
            h = int(input(f"Hauteur (100-{screen_h}) [{self.rect['height']}]: ") or self.rect['height'])
            
            # Validation
            x = max(0, min(x, screen_w - 100))
            y = max(0, min(y, screen_h - 100))
            w = max(100, min(w, screen_w - x))
            h = max(100, min(h, screen_h - y))
            
            self.rect = {'x': x, 'y': y, 'width': w, 'height': h}
            print(f"✅ Rectangle mis à jour: {self.rect}")
            
        except ValueError:
            print("❌ Valeurs invalides")
    
    def youtube_presets(self):
        """Presets pour YouTube Analytics"""
        print("\n🎯 PRESETS YOUTUBE ANALYTICS")
        print("-" * 30)
        print("1. 📊 Graphique standard (1100×400)")
        print("2. 📈 Graphique large (1400×500)")
        print("3. 📉 Graphique mobile (800×300)")
        
        choice = input("Preset (1-3): ").strip()
        
        presets = {
            '1': {'x': 250, 'y': 200, 'width': 1100, 'height': 400},
            '2': {'x': 200, 'y': 150, 'width': 1400, 'height': 500},
            '3': {'x': 100, 'y': 250, 'width': 800, 'height': 300}
        }
        
        if choice in presets:
            self.rect = presets[choice]
            print(f"✅ Preset appliqué: {self.rect}")
        else:
            print("❌ Preset invalide")
    
    def start_scan(self):
        """Commencer le scan"""
        print("\n🚀 PRÉPARATION DU SCAN")
        print("-" * 30)
        
        try:
            duration = float(input("Durée du scan (sec) [10]: ") or "10")
            interval = float(input("Intervalle entre captures (sec) [0.25]: ") or "0.25")
            
            captures_estimées = int(duration / interval)
            print(f"📸 Captures estimées: {captures_estimées}")
            
            print("\n⏳ Le scan va commencer dans 5 secondes...")
            print("📌 Positionnez votre graphique sous le rectangle rouge !")
            print("🔴 Zone de scan:", self.rect)
            
            for i in range(5, 0, -1):
                print(f"⏰ {i}...")
                time.sleep(1)
            
            print("🚀 SCAN EN COURS !")
            self.perform_scan(duration, interval)
            
        except ValueError:
            print("❌ Valeurs invalides")
        except KeyboardInterrupt:
            print("\n⏹️ Scan interrompu")
    
    def perform_scan(self, duration, interval):
        """Effectuer le scan horizontal"""
        try:
            self.scanning = True
            self.scan_data = []
            
            num_captures = int(duration / interval)
            start_x = self.rect['x'] + 20
            end_x = self.rect['x'] + self.rect['width'] - 20
            y_pos = self.rect['y'] + self.rect['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            print(f"📍 Scan: X={start_x} → {end_x}, Y={y_pos}")
            print(f"📸 {num_captures} captures en {duration}s")
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                
                # Déplacer le curseur
                pyautogui.moveTo(current_x, y_pos, duration=0.1)
                
                # Capturer
                screenshot = pyautogui.screenshot()
                timestamp = int(time.time() * 1000)
                filename = f"scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                screenshot.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                print(f"📸 Capture {i+1}/{num_captures} - X={int(current_x)}")
                time.sleep(interval)
            
            # Sauvegarder métadonnées
            self.save_metadata(duration, interval)
            
            print(f"\n🎉 SCAN TERMINÉ !")
            print(f"📊 {len(self.scan_data)} captures sauvées dans {self.output_dir}/")
            
        except Exception as e:
            print(f"❌ Erreur scan: {e}")
        finally:
            self.scanning = False
    
    def save_metadata(self, duration, interval):
        """Sauvegarder les métadonnées"""
        timestamp = int(time.time())
        metadata_file = os.path.join(self.output_dir, f"metadata_{timestamp}.json")
        
        metadata = {
            'scan_info': {
                'total_captures': len(self.scan_data),
                'duration': duration,
                'interval': interval,
                'rectangle': self.rect,
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Métadonnées: {metadata_file}")
    
    def open_file(self, filepath):
        """Ouvrir un fichier avec l'application par défaut"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.call(["open", filepath])
            elif sys.platform == "win32":  # Windows
                os.startfile(filepath)
            else:  # Linux
                subprocess.call(["xdg-open", filepath])
        except Exception as e:
            print(f"❌ Impossible d'ouvrir {filepath}: {e}")

def main():
    print("🎯 SCREEN OVERLAY SCANNER")
    print("=" * 50)
    print("✅ Rectangle rouge avec poignées virtuelles")
    print("✅ Configuration interactive")
    print("✅ Presets YouTube Analytics")
    print("✅ Scan horizontal automatique")
    print("✅ Pas de dépendance tkinter")
    print()
    
    try:
        overlay = ScreenOverlay()
        overlay.interactive_setup()
        
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == '__main__':
    main() 