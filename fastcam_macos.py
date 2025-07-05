#!/usr/bin/env python3
"""
FastCam macOS Scanner - Ultra-fast screen capture pour macOS
Utilise MSS (cross-platform) + overlay interactif avec rectangle rouge
"""

import time
import os
import json
import threading
import subprocess
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pyautogui
import mss
import numpy as np

class FastCamMacOS:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "fastcam_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
        
        # Initialiser MSS
        self.sct = mss.mss()
        
        # Obtenir la taille d'écran
        monitor = self.sct.monitors[1]  # Monitor principal
        self.screen_w = monitor["width"]
        self.screen_h = monitor["height"]
        
        # Rectangle par défaut
        self.rect = {
            'x': self.screen_w // 4,
            'y': self.screen_h // 4,
            'width': self.screen_w // 2,
            'height': self.screen_h // 2
        }
        
        print(f"🍎 FastCam macOS initialisé")
        print(f"📱 Écran: {self.screen_w}×{self.screen_h}")
        print(f"🔴 Rectangle: {self.rect}")
    
    def create_interactive_overlay(self):
        """Créer un overlay interactif avec rectangle rouge"""
        try:
            # Capture d'écran complète avec MSS
            screenshot = self.sct.grab(self.sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # Créer l'overlay
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            x, y, w, h = self.rect['x'], self.rect['y'], self.rect['width'], self.rect['height']
            
            # Zone de scan avec fond semi-transparent
            draw.rectangle([x, y, x + w, y + h], fill=(255, 0, 0, 50), outline=(255, 0, 0, 255), width=4)
            
            # Poignées de redimensionnement
            handle_size = 16
            handles = [
                (x + w - handle_size, y + h - handle_size, "↘️", "resize"),
                (x + w//2 - handle_size//2, y + h - handle_size, "↕️", "resize-h"),
                (x + w - handle_size, y + h//2 - handle_size//2, "↔️", "resize-w"),
                (x - handle_size//2, y - handle_size//2, "✋", "move"),
            ]
            
            for hx, hy, emoji, action in handles:
                # Poignée avec fond blanc
                draw.rectangle([hx, hy, hx + handle_size, hy + handle_size], 
                             fill=(255, 255, 255, 200), outline=(255, 0, 0, 255), width=2)
                # Emoji
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 10)
                    draw.text((hx + 3, hy + 3), emoji, fill=(255, 0, 0, 255), font=font)
                except:
                    draw.text((hx + 3, hy + 3), action[:2], fill=(255, 0, 0, 255))
            
            # Texte d'information
            try:
                font_title = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                font_info = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
            except:
                font_title = ImageFont.load_default()
                font_info = ImageFont.load_default()
            
            # Titre central
            title = "🎯 FASTCAM SCAN ZONE"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_w = title_bbox[2] - title_bbox[0]
            title_x = x + (w - title_w) // 2
            title_y = y + h // 2 - 40
            
            # Fond pour le titre
            draw.rectangle([title_x - 10, title_y - 5, title_x + title_w + 10, title_y + 30], 
                         fill=(255, 255, 255, 220), outline=(255, 0, 0, 255), width=2)
            draw.text((title_x, title_y), title, fill=(255, 0, 0, 255), font=font_title)
            
            # Informations
            info_lines = [
                f"📏 Taille: {w} × {h} pixels",
                f"📍 Position: ({x}, {y})",
                f"🚀 MSS Ready - macOS"
            ]
            
            for i, line in enumerate(info_lines):
                line_y = title_y + 40 + (i * 20)
                line_bbox = draw.textbbox((0, 0), line, font=font_info)
                line_w = line_bbox[2] - line_bbox[0]
                line_x = x + (w - line_w) // 2
                
                # Fond pour chaque ligne
                draw.rectangle([line_x - 5, line_y - 3, line_x + line_w + 5, line_y + 17], 
                             fill=(255, 255, 255, 180), outline=(255, 0, 0, 100), width=1)
                draw.text((line_x, line_y), line, fill=(255, 0, 0, 255), font=font_info)
            
            # Combiner avec l'image originale
            img = img.convert('RGBA')
            combined = Image.alpha_composite(img, overlay)
            
            return combined.convert('RGB')
            
        except Exception as e:
            print(f"❌ Erreur overlay: {e}")
            # Image d'erreur simple
            error_img = Image.new('RGB', (800, 600), 'black')
            draw = ImageDraw.Draw(error_img)
            draw.text((50, 50), f"Erreur overlay: {e}", fill='red')
            return error_img
    
    def save_overlay_preview(self):
        """Sauvegarder l'aperçu de l'overlay"""
        overlay_img = self.create_interactive_overlay()
        preview_path = os.path.join(self.output_dir, "fastcam_overlay.png")
        overlay_img.save(preview_path)
        print(f"📸 Aperçu overlay sauvé: {preview_path}")
        return preview_path
    
    def test_mss_performance(self):
        """Tester les performances de MSS"""
        print(f"\n⚡ TEST PERFORMANCE MSS")
        print("-" * 40)
        
        # Test région complète
        print("🖥️ Test écran complet...")
        start_time = time.time()
        
        for i in range(50):
            screenshot = self.sct.grab(self.sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        end_time = time.time()
        fps_full = 50 / (end_time - start_time)
        
        # Test région spécifique
        print("🔴 Test région spécifique...")
        region = {
            "top": self.rect['y'],
            "left": self.rect['x'],
            "width": self.rect['width'],
            "height": self.rect['height']
        }
        
        start_time = time.time()
        
        for i in range(100):
            screenshot = self.sct.grab(region)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        end_time = time.time()
        fps_region = 100 / (end_time - start_time)
        
        print(f"📊 Résultats:")
        print(f"🖥️  Écran complet: {fps_full:.1f} FPS")
        print(f"🔴 Région: {fps_region:.1f} FPS")
        
        if fps_region > 100:
            print("🔥 ULTRA-RAPIDE ! Parfait pour tracking temps réel")
        elif fps_region > 50:
            print("🚀 RAPIDE ! Excellent pour scanning")
        else:
            print("⚠️ Performance moyenne")
    
    def interactive_setup(self):
        """Configuration interactive"""
        print("\n🎯 FASTCAM MACOS SETUP")
        print("=" * 50)
        print(f"🍎 Système: macOS")
        print(f"📱 Écran: {self.screen_w}×{self.screen_h}")
        print(f"🔴 Rectangle: {self.rect}")
        
        while True:
            print(f"\n⚙️ OPTIONS:")
            print("1. 📏 Modifier rectangle")
            print("2. 🎯 Presets YouTube Analytics")
            print("3. 📸 Voir overlay avec rectangle rouge")
            print("4. ⚡ Test performance MSS")
            print("5. 🚀 Lancer scan ULTRA-RAPIDE")
            print("6. 🔧 Ajustement précis (clavier)")
            print("7. ❌ Quitter")
            
            choice = input("\nChoix (1-7): ").strip()
            
            if choice == '1':
                self.modify_rectangle()
            elif choice == '2':
                self.youtube_presets()
            elif choice == '3':
                preview_path = self.save_overlay_preview()
                self.open_file(preview_path)
            elif choice == '4':
                self.test_mss_performance()
            elif choice == '5':
                self.start_scan()
                break
            elif choice == '6':
                self.precise_adjustment()
            elif choice == '7':
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
            w = int(input(f"Largeur [{self.rect['width']}]: ") or self.rect['width'])
            h = int(input(f"Hauteur [{self.rect['height']}]: ") or self.rect['height'])
            
            # Validation
            x = max(0, min(x, self.screen_w - 100))
            y = max(0, min(y, self.screen_h - 100))
            w = max(100, min(w, self.screen_w - x))
            h = max(100, min(h, self.screen_h - y))
            
            self.rect = {'x': x, 'y': y, 'width': w, 'height': h}
            print(f"✅ Rectangle mis à jour: {self.rect}")
            
        except ValueError:
            print("❌ Valeurs invalides")
    
    def precise_adjustment(self):
        """Ajustement précis avec clavier"""
        print(f"\n🔧 AJUSTEMENT PRÉCIS")
        print("-" * 40)
        print("Utilisez les touches:")
        print("• ↑↓←→ : Déplacer rectangle")
        print("• +/- : Redimensionner")
        print("• ENTER : Valider")
        print("• ESC : Annuler")
        
        original_rect = self.rect.copy()
        
        while True:
            print(f"\n🔴 Rectangle: {self.rect}")
            key = input("Touche (↑↓←→ +- ENTER ESC): ").strip().lower()
            
            if key in ['↑', 'up', 'u']:
                self.rect['y'] = max(0, self.rect['y'] - 10)
            elif key in ['↓', 'down', 'd']:
                self.rect['y'] = min(self.screen_h - self.rect['height'], self.rect['y'] + 10)
            elif key in ['←', 'left', 'l']:
                self.rect['x'] = max(0, self.rect['x'] - 10)
            elif key in ['→', 'right', 'r']:
                self.rect['x'] = min(self.screen_w - self.rect['width'], self.rect['x'] + 10)
            elif key in ['+', 'plus']:
                self.rect['width'] = min(self.screen_w - self.rect['x'], self.rect['width'] + 20)
                self.rect['height'] = min(self.screen_h - self.rect['y'], self.rect['height'] + 20)
            elif key in ['-', 'minus']:
                self.rect['width'] = max(100, self.rect['width'] - 20)
                self.rect['height'] = max(100, self.rect['height'] - 20)
            elif key in ['enter', 'ok', '']:
                print("✅ Ajustement validé")
                break
            elif key in ['esc', 'cancel', 'q']:
                self.rect = original_rect
                print("❌ Ajustement annulé")
                break
            else:
                print("❌ Touche invalide")
    
    def youtube_presets(self):
        """Presets YouTube Analytics"""
        print(f"\n🎯 PRESETS YOUTUBE ANALYTICS")
        print("-" * 40)
        print("1. 📊 Standard (1100×400)")
        print("2. 📈 Large (1400×500)")
        print("3. 📱 Compact (900×350)")
        print("4. 🖥️ Full (1200×600)")
        print("5. 🎮 Gaming (800×300)")
        
        choice = input("Preset (1-5): ").strip()
        
        presets = {
            '1': {'x': 170, 'y': 200, 'width': 1100, 'height': 400},
            '2': {'x': 120, 'y': 150, 'width': 1200, 'height': 500},
            '3': {'x': 270, 'y': 225, 'width': 900, 'height': 350},
            '4': {'x': 120, 'y': 150, 'width': 1200, 'height': 600},
            '5': {'x': 320, 'y': 200, 'width': 800, 'height': 300}
        }
        
        if choice in presets:
            self.rect = presets[choice]
            print(f"✅ Preset appliqué: {self.rect}")
        else:
            print("❌ Preset invalide")
    
    def start_scan(self):
        """Démarrer le scan"""
        print(f"\n🚀 SCAN FASTCAM")
        print("-" * 40)
        
        try:
            duration = float(input("Durée (sec) [10]: ") or "10")
            interval = float(input("Intervalle (sec) [0.1]: ") or "0.1")
            
            # Mode turbo pour MSS
            if interval > 0.05:
                turbo = input("🚀 Mode turbo 0.05s ? (y/n) [y]: ").strip().lower()
                if turbo != 'n':
                    interval = 0.05
            
            captures_est = int(duration / interval)
            print(f"📸 Captures estimées: {captures_est}")
            
            print(f"\n⏳ Démarrage dans 5 secondes...")
            print(f"🔴 Zone: {self.rect}")
            print(f"🍎 MSS macOS prêt")
            
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
        """Effectuer le scan avec MSS"""
        try:
            self.scanning = True
            self.scan_data = []
            
            # Préparer la région MSS
            region = {
                "top": self.rect['y'],
                "left": self.rect['x'],
                "width": self.rect['width'],
                "height": self.rect['height']
            }
            
            num_captures = int(duration / interval)
            start_x = self.rect['x'] + 20
            end_x = self.rect['x'] + self.rect['width'] - 20
            y_pos = self.rect['y'] + self.rect['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            print(f"📍 Scan: X={start_x}→{end_x}, Y={y_pos}")
            print(f"⚡ Intervalle: {interval}s")
            print(f"🔴 Région MSS: {region}")
            
            start_time = time.time()
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                
                # Déplacer le curseur
                pyautogui.moveTo(current_x, y_pos, duration=0.05)
                
                # Capturer avec MSS (ultra-rapide)
                screenshot = self.sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                # Sauvegarder
                timestamp = int(time.time() * 1000)
                filename = f"fastcam_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                if i % 20 == 0:  # Progression
                    print(f"📸 {i+1}/{num_captures} ({(i+1)/num_captures*100:.1f}%)")
                
                time.sleep(interval)
            
            end_time = time.time()
            actual_fps = len(self.scan_data) / (end_time - start_time)
            
            # Sauvegarder métadonnées
            self.save_metadata(duration, interval, actual_fps)
            
            print(f"\n🎉 SCAN TERMINÉ !")
            print(f"📊 {len(self.scan_data)} captures en {end_time - start_time:.2f}s")
            print(f"⚡ FPS réel: {actual_fps:.1f}")
            print(f"🍎 MSS Performance: Excellent")
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
                'capture_method': 'MSS',
                'platform': 'macOS',
                'screen_size': [self.screen_w, self.screen_h],
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Métadonnées: {metadata_file}")
    
    def open_file(self, filepath):
        """Ouvrir un fichier sur macOS"""
        try:
            subprocess.call(["open", filepath])
        except Exception as e:
            print(f"❌ Impossible d'ouvrir {filepath}: {e}")
    
    def cleanup(self):
        """Nettoyer les ressources"""
        try:
            self.sct.close()
            print("🧹 MSS nettoyé")
        except:
            pass

def main():
    print("🎯 FASTCAM MACOS SCANNER")
    print("=" * 60)
    print("🍎 Optimisé pour macOS")
    print("🚀 Ultra-fast capture avec MSS")
    print("🔴 Rectangle rouge interactif")
    print("🎮 Parfait pour YouTube Analytics")
    print("⚡ Performance native macOS")
    print()
    
    scanner = None
    try:
        scanner = FastCamMacOS()
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