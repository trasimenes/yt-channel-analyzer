#!/usr/bin/env python3
"""
Click & Drag Scanner - Inspiré par formazione/utilities et kodo-pp/select-rect
Sélectionnez une région d'écran en cliquant et déplaçant, puis scannez horizontalement
"""

import pygame
import sys
import time
import os
import json
import threading
from datetime import datetime
import mss
import pyautogui
from PIL import Image

# Initialiser pygame et désactiver le failsafe
pygame.init()
pyautogui.FAILSAFE = False

class ClickDragScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "click_drag_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # MSS pour captures ultra-rapides
        self.sct = mss.mss()
        monitor = self.sct.monitors[1]
        self.screen_w = monitor["width"]
        self.screen_h = monitor["height"]
        
        # Variables pour la sélection
        self.selection_active = False
        self.start_pos = None
        self.end_pos = None
        self.selected_rect = None
        
        print(f"🎯 Click & Drag Scanner initialisé")
        print(f"📱 Écran: {self.screen_w}×{self.screen_h}")
    
    def capture_screenshot(self):
        """Capturer une image de l'écran entier"""
        screenshot = self.sct.grab(self.sct.monitors[1])
        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    
    def select_region_interactive(self):
        """Interface pour sélectionner une région par clic-déplacement"""
        print("\n🔴 SÉLECTION DE RÉGION")
        print("=" * 50)
        print("✋ Cliquez et déplacez pour sélectionner la zone")
        print("🖱️  Clic gauche + déplacement = sélection")
        print("🖱️  Clic droit = annuler")
        print("⌨️  ESC = quitter")
        
        # Capturer l'écran de base
        base_image = self.capture_screenshot()
        
        # Créer fenêtre pygame plein écran
        screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.NOFRAME)
        pygame.display.set_caption("Sélection de région")
        
        # Convertir PIL vers pygame surface
        pil_string_image = base_image.tobytes()
        pygame_image = pygame.image.fromstring(pil_string_image, base_image.size, "RGB")
        
        clock = pygame.time.Clock()
        selecting = False
        start_x, start_y = 0, 0
        current_x, current_y = 0, 0
        
        print("\n🔴 Interface active ! Sélectionnez votre zone...")
        
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return None
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic gauche
                        selecting = True
                        start_x, start_y = event.pos
                        current_x, current_y = event.pos
                    elif event.button == 3:  # Clic droit
                        pygame.quit()
                        return None
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and selecting:  # Relâcher clic gauche
                        end_x, end_y = event.pos
                        
                        # Calculer rectangle final
                        x = min(start_x, end_x)
                        y = min(start_y, end_y)
                        width = abs(end_x - start_x)
                        height = abs(end_y - start_y)
                        
                        # Validation
                        if width > 20 and height > 20:
                            pygame.quit()
                            selected = {
                                'x': x, 'y': y,
                                'width': width, 'height': height
                            }
                            print(f"✅ Région sélectionnée: {selected}")
                            return selected
                        else:
                            print("❌ Zone trop petite, recommencez")
                            selecting = False
                
                elif event.type == pygame.MOUSEMOTION and selecting:
                    current_x, current_y = event.pos
            
            # Dessiner l'écran
            screen.blit(pygame_image, (0, 0))
            
            # Dessiner le rectangle de sélection
            if selecting:
                rect_x = min(start_x, current_x)
                rect_y = min(start_y, current_y)
                rect_w = abs(current_x - start_x)
                rect_h = abs(current_y - start_y)
                
                # Overlay semi-transparent
                overlay = pygame.Surface((rect_w, rect_h))
                overlay.set_alpha(50)
                overlay.fill((255, 0, 0))
                screen.blit(overlay, (rect_x, rect_y))
                
                # Bordure rouge
                pygame.draw.rect(screen, (255, 0, 0), 
                               (rect_x, rect_y, rect_w, rect_h), 3)
                
                # Afficher dimensions
                font = pygame.font.Font(None, 24)
                text = f"{rect_w} × {rect_h}"
                text_surface = font.render(text, True, (255, 255, 255))
                text_rect = text_surface.get_rect()
                
                # Fond noir pour le texte
                text_bg = pygame.Surface((text_rect.width + 10, text_rect.height + 6))
                text_bg.fill((0, 0, 0))
                text_bg.set_alpha(180)
                
                screen.blit(text_bg, (rect_x + 5, rect_y - 30))
                screen.blit(text_surface, (rect_x + 10, rect_y - 27))
            
            # Instructions
            font = pygame.font.Font(None, 20)
            instructions = [
                "🔴 Cliquez et déplacez pour sélectionner",
                "🖱️  Clic droit ou ESC pour annuler"
            ]
            
            for i, instruction in enumerate(instructions):
                text = font.render(instruction, True, (255, 255, 255))
                text_bg = pygame.Surface((text.get_width() + 10, text.get_height() + 4))
                text_bg.fill((0, 0, 0))
                text_bg.set_alpha(150)
                
                screen.blit(text_bg, (10, 10 + i * 25))
                screen.blit(text, (15, 12 + i * 25))
            
            pygame.display.flip()
            clock.tick(60)
    
    def confirm_selection(self, rect):
        """Confirmer la sélection avec aperçu"""
        print(f"\n📐 CONFIRMATION DE SÉLECTION")
        print("-" * 40)
        print(f"🔴 Rectangle: ({rect['x']}, {rect['y']}) → {rect['width']}×{rect['height']}")
        
        # Capturer la région sélectionnée
        region = {
            "top": rect['y'],
            "left": rect['x'],
            "width": rect['width'],
            "height": rect['height']
        }
        
        screenshot = self.sct.grab(region)
        preview_img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        # Sauvegarder aperçu
        preview_path = os.path.join(self.output_dir, "selection_preview.png")
        preview_img.save(preview_path)
        print(f"📸 Aperçu sauvé: {preview_path}")
        
        # Ouvrir l'aperçu
        try:
            import subprocess
            subprocess.call(["open", preview_path])
        except:
            pass
        
        # Confirmation
        while True:
            confirm = input("\n✅ Confirmer cette sélection ? (y/n/r=refaire): ").strip().lower()
            if confirm in ['y', 'yes', 'o', 'oui', '']:
                return True
            elif confirm in ['n', 'no', 'non']:
                return False
            elif confirm in ['r', 'refaire', 'retry']:
                return 'retry'
            else:
                print("❌ Réponse invalide")
    
    def configure_scan(self):
        """Configurer les paramètres de scan"""
        print(f"\n⚙️ CONFIGURATION DU SCAN")
        print("-" * 40)
        
        try:
            duration = float(input("Durée du scan (sec) [10]: ") or "10")
            interval = float(input("Intervalle entre captures (sec) [0.2]: ") or "0.2")
            
            captures_est = int(duration / interval)
            print(f"📸 Captures estimées: {captures_est}")
            
            return duration, interval
            
        except ValueError:
            print("❌ Valeurs invalides, utilisation des valeurs par défaut")
            return 10.0, 0.2
    
    def perform_scan(self, rect, duration, interval):
        """Effectuer le scan horizontal dans la région sélectionnée"""
        try:
            self.scanning = True
            self.scan_data = []
            
            # Région MSS
            region = {
                "top": rect['y'],
                "left": rect['x'],
                "width": rect['width'],
                "height": rect['height']
            }
            
            num_captures = int(duration / interval)
            start_x = rect['x'] + 20
            end_x = rect['x'] + rect['width'] - 20
            y_pos = rect['y'] + rect['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            print(f"\n🚀 SCAN EN COURS !")
            print(f"📍 Scan horizontal: X={start_x} → {end_x}")
            print(f"📍 Position Y: {y_pos}")
            print(f"⏱️ {num_captures} captures en {duration}s")
            
            start_time = time.time()
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                
                # Déplacer le curseur
                pyautogui.moveTo(current_x, y_pos, duration=0.05)
                
                # Capturer avec MSS (région spécifique)
                screenshot = self.sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                # Sauvegarder
                timestamp = int(time.time() * 1000)
                filename = f"clickdrag_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                if i % 5 == 0:
                    progress = (i + 1) / num_captures * 100
                    print(f"📸 Capture {i+1}/{num_captures} ({progress:.1f}%)")
                
                time.sleep(interval)
            
            end_time = time.time()
            actual_fps = len(self.scan_data) / (end_time - start_time)
            
            # Sauvegarder métadonnées
            self.save_metadata(rect, duration, interval, actual_fps)
            
            print(f"\n🎉 SCAN TERMINÉ !")
            print(f"📊 {len(self.scan_data)} captures sauvées")
            print(f"⚡ FPS réel: {actual_fps:.1f}")
            print(f"📁 Dossier: {self.output_dir}/")
            
        except Exception as e:
            print(f"❌ Erreur scan: {e}")
        finally:
            self.scanning = False
    
    def save_metadata(self, rect, duration, interval, actual_fps):
        """Sauvegarder les métadonnées du scan"""
        timestamp = int(time.time())
        metadata_file = os.path.join(self.output_dir, f"metadata_{timestamp}.json")
        
        metadata = {
            'scan_info': {
                'method': 'Click & Drag Selection',
                'total_captures': len(self.scan_data),
                'duration': duration,
                'interval': interval,
                'actual_fps': actual_fps,
                'selected_region': rect,
                'screen_size': [self.screen_w, self.screen_h],
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Métadonnées: {metadata_file}")
    
    def run(self):
        """Processus principal"""
        print("\n🎯 CLICK & DRAG SCANNER")
        print("=" * 60)
        print("🖱️  Sélection par clic-déplacement")
        print("⚡ Scan horizontal ultra-rapide")
        print("🍎 Compatible macOS")
        
        while True:
            # Étape 1: Sélection de région
            print(f"\n📍 ÉTAPE 1: Sélection de région")
            selected_rect = self.select_region_interactive()
            
            if not selected_rect:
                print("👋 Au revoir!")
                break
            
            # Étape 2: Confirmation
            print(f"\n📋 ÉTAPE 2: Confirmation")
            confirmation = self.confirm_selection(selected_rect)
            
            if confirmation == 'retry':
                continue
            elif not confirmation:
                print("❌ Sélection annulée")
                continue
            
            # Étape 3: Configuration
            print(f"\n⚙️ ÉTAPE 3: Configuration")
            duration, interval = self.configure_scan()
            
            # Étape 4: Scan
            print(f"\n🚀 ÉTAPE 4: Scan")
            print("⏳ Démarrage dans 3 secondes...")
            for i in range(3, 0, -1):
                print(f"⏰ {i}...")
                time.sleep(1)
            
            self.perform_scan(selected_rect, duration, interval)
            
            # Nouveau scan ?
            while True:
                again = input("\n🔄 Nouveau scan ? (y/n): ").strip().lower()
                if again in ['y', 'yes', 'o', 'oui', '']:
                    break
                elif again in ['n', 'no', 'non']:
                    print("👋 Au revoir!")
                    return
                else:
                    print("❌ Réponse invalide")
    
    def cleanup(self):
        """Nettoyer les ressources"""
        try:
            pygame.quit()
            self.sct.close()
            print("🧹 Ressources nettoyées")
        except:
            pass

def main():
    print("🎯 CLICK & DRAG SCANNER")
    print("=" * 60)
    print("🖱️  Inspiré par formazione/utilities")
    print("🎮 Interface pygame interactive")
    print("🚀 Scan ultra-rapide avec MSS")
    print("🍎 Optimisé pour macOS")
    print()
    
    scanner = None
    try:
        scanner = ClickDragScanner()
        scanner.run()
        
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        if scanner:
            scanner.cleanup()

if __name__ == '__main__':
    main() 