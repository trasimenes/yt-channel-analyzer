#!/usr/bin/env python3
"""
BetterCam Scanner - Ultra-fast screen capture avec rectangle rouge
Utilise BetterCam (240Hz+) + overlay simple pour performance maximale
"""

import time
import os
import json
import threading
from datetime import datetime
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Installation automatique de BetterCam
try:
    import bettercam
    print("✅ BetterCam détecté")
except ImportError:
    print("📦 Installation de BetterCam...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bettercam"])
    import bettercam
    print("✅ BetterCam installé")

# Fallback si BetterCam ne fonctionne pas
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    FALLBACK_MODE = False
except ImportError:
    FALLBACK_MODE = True
    print("⚠️ PyAutoGUI non disponible")

class BetterCamScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "bettercam_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialiser BetterCam
        try:
            self.camera = bettercam.create()
            print("🎯 BetterCam initialisé")
            self.screen_w, self.screen_h = self.get_screen_size()
            self.use_bettercam = True
        except Exception as e:
            print(f"❌ Erreur BetterCam: {e}")
            if not FALLBACK_MODE:
                self.screen_w, self.screen_h = pyautogui.size()
            else:
                self.screen_w, self.screen_h = 1920, 1080
            self.use_bettercam = False
        
        # Rectangle par défaut
        self.rect = {
            'x': self.screen_w // 4,
            'y': self.screen_h // 4,
            'width': self.screen_w // 2,
            'height': self.screen_h // 2
        }
        
        print(f"🖥️ Écran: {self.screen_w}×{self.screen_h}")
        print(f"🔴 Rectangle: {self.rect}")
    
    def get_screen_size(self):
        """Obtenir la taille d'écran via BetterCam"""
        try:
            frame = self.camera.grab()
            if frame is not None:
                return frame.shape[1], frame.shape[0]  # width, height
        except:
            pass
        return 1920, 1080  # Fallback
    
    def create_overlay_preview(self):
        """Créer un aperçu de l'overlay avec le rectangle rouge"""
        try:
            # Capturer l'écran
            if self.use_bettercam:
                frame = self.camera.grab()
                if frame is not None:
                    # Convertir BGR vers RGB si nécessaire
                    if frame.shape[2] == 3:  # RGB
                        screenshot = Image.fromarray(frame)
                    else:  # RGBA
                        screenshot = Image.fromarray(frame[:, :, :3])
                else:
                    # Fallback: image noire
                    screenshot = Image.new('RGB', (self.screen_w, self.screen_h), 'black')
            else:
                if not FALLBACK_MODE:
                    screenshot = pyautogui.screenshot()
                else:
                    screenshot = Image.new('RGB', (self.screen_w, self.screen_h), 'black')
            
            # Dessiner le rectangle rouge et les poignées
            draw = ImageDraw.Draw(screenshot)
            x, y, w, h = self.rect['x'], self.rect['y'], self.rect['width'], self.rect['height']
            
            # Rectangle principal (rouge épais)
            draw.rectangle([x, y, x + w, y + h], outline='red', width=6)
            
            # Fond semi-transparent
            overlay = Image.new('RGBA', screenshot.size, (255, 0, 0, 30))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([x, y, x + w, y + h], fill=(255, 0, 0, 30))
            
            # Combiner avec l'original
            screenshot = screenshot.convert('RGBA')
            screenshot = Image.alpha_composite(screenshot, overlay)
            screenshot = screenshot.convert('RGB')
            draw = ImageDraw.Draw(screenshot)
            
            # Poignées de redimensionnement
            handle_size = 12
            handles = [
                (x + w - handle_size, y + h - handle_size, "↘️"),  # Bas-droite
                (x + w//2 - handle_size//2, y + h - handle_size, "↓"),  # Bas centre
                (x + w - handle_size, y + h//2 - handle_size//2, "→"),  # Droite centre
                (x - handle_size, y - handle_size, "↖️"),  # Haut-gauche
            ]
            
            for hx, hy, symbol in handles:
                # Poignée blanche avec bordure rouge
                draw.rectangle([hx, hy, hx + handle_size, hy + handle_size], 
                             fill='white', outline='red', width=2)
                # Petit symbole
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 8)
                    draw.text((hx + 2, hy + 2), symbol, fill='red', font=font)
                except:
                    pass
            
            # Texte central
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text_lines = ["🔴 ZONE DE SCAN", f"{w}×{h}px", "BetterCam Ready"]
            for i, line in enumerate(text_lines):
                text_bbox = draw.textbbox((0, 0), line, font=font)
                text_w = text_bbox[2] - text_bbox[0]
                text_x = x + (w - text_w) // 2
                text_y = y + (h // 2) - 30 + (i * 25)
                
                # Fond pour le texte
                draw.rectangle([text_x - 5, text_y - 5, text_x + text_w + 5, text_y + 20], 
                             fill='white', outline='red', width=1)
                draw.text((text_x, text_y), line, fill='red', font=font)
            
            # Informations de performance
            perf_text = f"🚀 BetterCam: {self.use_bettercam} | Screen: {self.screen_w}×{self.screen_h}"
            draw.text((10, 10), perf_text, fill='blue', font=font)
            
            return screenshot
            
        except Exception as e:
            print(f"❌ Erreur création overlay: {e}")
            # Image d'erreur
            img = Image.new('RGB', (800, 600), 'black')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), f"Erreur: {e}", fill='red')
            return img
    
    def save_preview(self):
        """Sauvegarder l'aperçu"""
        preview = self.create_overlay_preview()
        preview_path = os.path.join(self.output_dir, "overlay_preview.png")
        preview.save(preview_path)
        print(f"📸 Aperçu sauvé: {preview_path}")
        return preview_path
    
    def interactive_setup(self):
        """Configuration interactive"""
        print("\n🎯 BETTERCAM SCANNER SETUP")
        print("=" * 60)
        print(f"🚀 BetterCam actif: {self.use_bettercam}")
        print(f"📱 Écran: {self.screen_w}×{self.screen_h}")
        print(f"🔴 Rectangle: {self.rect}")
        
        while True:
            print(f"\n⚙️ OPTIONS:")
            print("1. 📏 Modifier rectangle")
            print("2. 🎯 Presets YouTube")
            print("3. 📸 Voir aperçu overlay")
            print("4. 🚀 Lancer scan ULTRA-RAPIDE")
            print("5. ⚡ Test performance BetterCam")
            print("6. ❌ Quitter")
            
            choice = input("\nChoix (1-6): ").strip()
            
            if choice == '1':
                self.modify_rectangle()
            elif choice == '2':
                self.youtube_presets()
            elif choice == '3':
                preview_path = self.save_preview()
                self.open_file(preview_path)
            elif choice == '4':
                self.start_scan()
                break
            elif choice == '5':
                self.test_performance()
            elif choice == '6':
                print("👋 Au revoir!")
                break
            else:
                print("❌ Choix invalide")
    
    def modify_rectangle(self):
        """Modifier le rectangle"""
        print(f"\n📏 MODIFICATION RECTANGLE")
        print("-" * 40)
        
        try:
            print(f"Rectangle actuel: {self.rect}")
            x = int(input(f"X (0-{self.screen_w}) [{self.rect['x']}]: ") or self.rect['x'])
            y = int(input(f"Y (0-{self.screen_h}) [{self.rect['y']}]: ") or self.rect['y'])
            w = int(input(f"Largeur (100-{self.screen_w-x}) [{self.rect['width']}]: ") or self.rect['width'])
            h = int(input(f"Hauteur (100-{self.screen_h-y}) [{self.rect['height']}]: ") or self.rect['height'])
            
            # Validation
            x = max(0, min(x, self.screen_w - 100))
            y = max(0, min(y, self.screen_h - 100))
            w = max(100, min(w, self.screen_w - x))
            h = max(100, min(h, self.screen_h - y))
            
            self.rect = {'x': x, 'y': y, 'width': w, 'height': h}
            print(f"✅ Rectangle mis à jour: {self.rect}")
            
        except ValueError:
            print("❌ Valeurs invalides")
    
    def youtube_presets(self):
        """Presets YouTube Analytics"""
        print(f"\n🎯 PRESETS YOUTUBE ANALYTICS")
        print("-" * 40)
        print("1. 📊 Standard (1100×400)")
        print("2. 📈 Large (1400×500)")
        print("3. 📱 Mobile (800×300)")
        print("4. 🖥️ Full HD (1200×600)")
        
        choice = input("Preset (1-4): ").strip()
        
        presets = {
            '1': {'x': 250, 'y': 200, 'width': 1100, 'height': 400},
            '2': {'x': 200, 'y': 150, 'width': 1400, 'height': 500},
            '3': {'x': 320, 'y': 250, 'width': 800, 'height': 300},
            '4': {'x': 360, 'y': 200, 'width': 1200, 'height': 600}
        }
        
        if choice in presets:
            self.rect = presets[choice]
            print(f"✅ Preset appliqué: {self.rect}")
        else:
            print("❌ Preset invalide")
    
    def test_performance(self):
        """Test de performance BetterCam"""
        print(f"\n⚡ TEST PERFORMANCE")
        print("-" * 40)
        
        if not self.use_bettercam:
            print("❌ BetterCam non disponible")
            return
        
        print("🚀 Test 100 captures ultra-rapides...")
        start_time = time.time()
        
        for i in range(100):
            frame = self.camera.grab()
            if frame is None:
                time.sleep(0.001)  # Micro-pause si pas de frame
        
        end_time = time.time()
        fps = 100 / (end_time - start_time)
        
        print(f"🎯 Performance: {fps:.1f} FPS")
        print(f"⏱️ Temps total: {end_time - start_time:.3f}s")
        
        if fps > 200:
            print("🔥 ULTRA-RAPIDE ! Parfait pour tracking temps réel")
        elif fps > 100:
            print("🚀 RAPIDE ! Excellent pour scanning")
        else:
            print("⚠️ Performance limitée")
    
    def start_scan(self):
        """Démarrer le scan"""
        print(f"\n🚀 SCAN BETTERCAM")
        print("-" * 40)
        
        try:
            duration = float(input("Durée (sec) [10]: ") or "10")
            interval = float(input("Intervalle (sec) [0.1]: ") or "0.1")
            
            # Avec BetterCam, on peut aller plus vite
            if self.use_bettercam and interval > 0.05:
                fast_interval = input(f"🚀 Mode turbo 0.05s ? (y/n) [y]: ").strip().lower()
                if fast_interval != 'n':
                    interval = 0.05
            
            captures_est = int(duration / interval)
            print(f"📸 Captures estimées: {captures_est}")
            print(f"⚡ Mode BetterCam: {self.use_bettercam}")
            
            print(f"\n⏳ Démarrage dans 5 secondes...")
            print(f"🔴 Zone: {self.rect}")
            
            for i in range(5, 0, -1):
                print(f"⏰ {i}...")
                time.sleep(1)
            
            print("🚀 SCAN ULTRA-RAPIDE !")
            self.perform_scan(duration, interval)
            
        except ValueError:
            print("❌ Valeurs invalides")
        except KeyboardInterrupt:
            print("\n⏹️ Scan interrompu")
    
    def perform_scan(self, duration, interval):
        """Effectuer le scan avec BetterCam"""
        try:
            self.scanning = True
            self.scan_data = []
            
            num_captures = int(duration / interval)
            start_x = self.rect['x'] + 20
            end_x = self.rect['x'] + self.rect['width'] - 20
            y_pos = self.rect['y'] + self.rect['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            print(f"📍 Scan: X={start_x}→{end_x}, Y={y_pos}")
            print(f"⚡ Intervalle: {interval}s")
            
            start_time = time.time()
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                
                # Capturer avec BetterCam
                if self.use_bettercam:
                    region = (self.rect['x'], self.rect['y'], 
                             self.rect['x'] + self.rect['width'], 
                             self.rect['y'] + self.rect['height'])
                    frame = self.camera.grab(region=region)
                    
                    if frame is not None:
                        # Sauvegarder frame
                        timestamp = int(time.time() * 1000)
                        filename = f"bettercam_{timestamp}_{i:03d}.png"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        # Convertir numpy vers PIL
                        if frame.shape[2] == 4:  # RGBA
                            img = Image.fromarray(frame[:, :, :3])
                        else:  # RGB
                            img = Image.fromarray(frame)
                        img.save(filepath)
                else:
                    # Fallback PyAutoGUI
                    if not FALLBACK_MODE:
                        # Déplacer curseur
                        pyautogui.moveTo(current_x, y_pos, duration=0.05)
                        screenshot = pyautogui.screenshot()
                        
                        timestamp = int(time.time() * 1000)
                        filename = f"fallback_{timestamp}_{i:03d}.png"
                        filepath = os.path.join(self.output_dir, filename)
                        screenshot.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                if i % 10 == 0:  # Afficher progression
                    print(f"📸 {i+1}/{num_captures} ({(i+1)/num_captures*100:.1f}%)")
                
                time.sleep(interval)
            
            end_time = time.time()
            actual_fps = len(self.scan_data) / (end_time - start_time)
            
            # Sauvegarder métadonnées
            self.save_metadata(duration, interval, actual_fps)
            
            print(f"\n🎉 SCAN TERMINÉ !")
            print(f"📊 {len(self.scan_data)} captures en {end_time - start_time:.2f}s")
            print(f"⚡ FPS réel: {actual_fps:.1f}")
            print(f"📁 Dossier: {self.output_dir}/")
            
        except Exception as e:
            print(f"❌ Erreur scan: {e}")
        finally:
            self.scanning = False
    
    def save_metadata(self, duration, interval, actual_fps):
        """Sauvegarder métadonnées"""
        timestamp = int(time.time())
        metadata_file = os.path.join(self.output_dir, f"metadata_{timestamp}.json")
        
        metadata = {
            'scan_info': {
                'total_captures': len(self.scan_data),
                'duration': duration,
                'interval': interval,
                'actual_fps': actual_fps,
                'rectangle': self.rect,
                'bettercam_used': self.use_bettercam,
                'screen_size': [self.screen_w, self.screen_h],
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Métadonnées: {metadata_file}")
    
    def open_file(self, filepath):
        """Ouvrir un fichier"""
        try:
            if sys.platform == "darwin":
                subprocess.call(["open", filepath])
            elif sys.platform == "win32":
                os.startfile(filepath)
            else:
                subprocess.call(["xdg-open", filepath])
        except Exception as e:
            print(f"❌ Impossible d'ouvrir {filepath}: {e}")
    
    def cleanup(self):
        """Nettoyer les ressources"""
        if self.use_bettercam:
            try:
                self.camera.release()
                print("🧹 BetterCam nettoyé")
            except:
                pass

def main():
    print("🎯 BETTERCAM SCANNER")
    print("=" * 60)
    print("🚀 Ultra-fast screen capture (240Hz+)")
    print("🔴 Rectangle rouge avec overlay")
    print("🎮 Parfait pour YouTube Analytics")
    print("⚡ Performance maximale")
    print()
    
    scanner = None
    try:
        scanner = BetterCamScanner()
        scanner.interactive_setup()
        
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        if scanner:
            scanner.cleanup()

if __name__ == '__main__':
    main() 