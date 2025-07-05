#!/usr/bin/env python3
"""
Real Overlay Scanner - Vrai rectangle rouge flottant sur l'écran
Utilise pygame pour créer une overlay transparente avec poignées
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

# Initialiser pygame
pygame.init()
pyautogui.FAILSAFE = False

class RealOverlayScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "real_overlay_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # MSS pour captures rapides
        self.sct = mss.mss()
        monitor = self.sct.monitors[1]
        self.screen_w = monitor["width"]
        self.screen_h = monitor["height"]
        
        # Rectangle par défaut
        self.rect = {
            'x': 300,
            'y': 200,
            'width': 800,
            'height': 400
        }
        
        # Variables overlay
        self.overlay_active = False
        self.dragging = False
        self.resizing = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.handle_size = 15
        
        print(f"🎯 Real Overlay Scanner initialisé")
        print(f"📱 Écran: {self.screen_w}×{self.screen_h}")
        print(f"🔴 Rectangle: {self.rect}")
    
    def create_overlay_window(self):
        """Créer une fenêtre overlay transparente"""
        try:
            # Créer fenêtre pygame transparente
            os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
            
            # Fenêtre sans bordures
            self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), 
                                                 pygame.NOFRAME)
            pygame.display.set_caption("Overlay Scanner")
            
            # Couleur transparente
            self.screen.fill((0, 0, 0))
            self.screen.set_alpha(100)  # Semi-transparent
            
            # Essayer de mettre au premier plan (pas toujours supporté)
            try:
                pygame.display.set_mode((self.screen_w, self.screen_h), 
                                       pygame.NOFRAME | pygame.DOUBLEBUF)
            except:
                pass
            
            self.overlay_active = True
            print("✅ Overlay créé avec pygame")
            
        except Exception as e:
            print(f"❌ Erreur création overlay: {e}")
            return False
        
        return True
    
    def draw_overlay(self):
        """Dessiner le rectangle rouge avec poignées"""
        if not self.overlay_active:
            return
        
        # Effacer l'écran
        self.screen.fill((0, 0, 0))
        
        x, y, w, h = self.rect['x'], self.rect['y'], self.rect['width'], self.rect['height']
        
        # Rectangle principal (rouge)
        pygame.draw.rect(self.screen, (255, 0, 0), (x, y, w, h), 4)
        
        # Fond semi-transparent
        overlay_surf = pygame.Surface((w, h))
        overlay_surf.set_alpha(30)
        overlay_surf.fill((255, 0, 0))
        self.screen.blit(overlay_surf, (x, y))
        
        # Poignées de redimensionnement
        handles = [
            (x + w - self.handle_size, y + h - self.handle_size, "BR"),  # Bas-droite
            (x + w//2 - self.handle_size//2, y + h - self.handle_size, "B"),  # Bas
            (x + w - self.handle_size, y + h//2 - self.handle_size//2, "R"),  # Droite
            (x - self.handle_size//2, y - self.handle_size//2, "TL"),  # Haut-gauche
        ]
        
        for hx, hy, pos in handles:
            pygame.draw.rect(self.screen, (255, 255, 255), 
                           (hx, hy, self.handle_size, self.handle_size))
            pygame.draw.rect(self.screen, (255, 0, 0), 
                           (hx, hy, self.handle_size, self.handle_size), 2)
        
        # Texte central
        font = pygame.font.Font(None, 24)
        text_lines = [
            "🔴 ZONE DE SCAN",
            f"{w} × {h} pixels",
            "Déplacez-moi !"
        ]
        
        for i, line in enumerate(text_lines):
            text = font.render(line, True, (255, 0, 0))
            text_rect = text.get_rect()
            text_x = x + (w - text_rect.width) // 2
            text_y = y + (h - len(text_lines) * 25) // 2 + (i * 25)
            
            # Fond blanc pour le texte
            pygame.draw.rect(self.screen, (255, 255, 255), 
                           (text_x - 5, text_y - 2, text_rect.width + 10, text_rect.height + 4))
            self.screen.blit(text, (text_x, text_y))
        
        # Instructions
        inst_font = pygame.font.Font(None, 18)
        instructions = [
            "• Cliquez et déplacez le rectangle",
            "• Utilisez les poignées pour redimensionner",
            "• Appuyez ESPACE pour lancer le scan",
            "• Appuyez ESC pour quitter"
        ]
        
        for i, inst in enumerate(instructions):
            text = inst_font.render(inst, True, (255, 255, 255))
            self.screen.blit(text, (10, 10 + i * 20))
        
        pygame.display.flip()
    
    def handle_mouse_event(self, event):
        """Gérer les événements souris"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic gauche
                mouse_x, mouse_y = event.pos
                
                # Vérifier si on clique sur une poignée
                x, y, w, h = self.rect['x'], self.rect['y'], self.rect['width'], self.rect['height']
                
                handles = [
                    (x + w - self.handle_size, y + h - self.handle_size, "resize"),
                    (x + w//2 - self.handle_size//2, y + h - self.handle_size, "resize"),
                    (x + w - self.handle_size, y + h//2 - self.handle_size//2, "resize"),
                ]
                
                for hx, hy, action in handles:
                    if hx <= mouse_x <= hx + self.handle_size and hy <= mouse_y <= hy + self.handle_size:
                        self.resizing = True
                        self.drag_start_x = mouse_x
                        self.drag_start_y = mouse_y
                        return
                
                # Sinon, déplacer le rectangle
                if x <= mouse_x <= x + w and y <= mouse_y <= y + h:
                    self.dragging = True
                    self.drag_start_x = mouse_x - x
                    self.drag_start_y = mouse_y - y
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                self.resizing = False
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mouse_x, mouse_y = event.pos
                new_x = mouse_x - self.drag_start_x
                new_y = mouse_y - self.drag_start_y
                
                # Limiter aux bords d'écran
                new_x = max(0, min(new_x, self.screen_w - self.rect['width']))
                new_y = max(0, min(new_y, self.screen_h - self.rect['height']))
                
                self.rect['x'] = new_x
                self.rect['y'] = new_y
                
            elif self.resizing:
                mouse_x, mouse_y = event.pos
                
                # Redimensionner depuis le coin bas-droite
                new_width = mouse_x - self.rect['x']
                new_height = mouse_y - self.rect['y']
                
                # Limites
                new_width = max(100, min(new_width, self.screen_w - self.rect['x']))
                new_height = max(100, min(new_height, self.screen_h - self.rect['y']))
                
                self.rect['width'] = new_width
                self.rect['height'] = new_height
    
    def run_overlay(self):
        """Boucle principale de l'overlay"""
        if not self.create_overlay_window():
            return
        
        clock = pygame.time.Clock()
        running = True
        
        print("\n🔴 OVERLAY ACTIF !")
        print("=" * 40)
        print("• Déplacez le rectangle rouge")
        print("• Redimensionnez avec les poignées")
        print("• ESPACE = Lancer scan")
        print("• ESC = Quitter")
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.start_scan_from_overlay()
                    elif event.key == pygame.K_RETURN:
                        self.show_config_menu()
                
                else:
                    self.handle_mouse_event(event)
            
            self.draw_overlay()
            clock.tick(60)  # 60 FPS
        
        pygame.quit()
        print("👋 Overlay fermé")
    
    def show_config_menu(self):
        """Afficher le menu de configuration"""
        print(f"\n⚙️ CONFIGURATION")
        print("-" * 30)
        print(f"Rectangle actuel: {self.rect}")
        print("1. Modifier précisément")
        print("2. Presets YouTube")
        print("3. Retour overlay")
        
        # Minimiser la fenêtre pygame temporairement
        # (pas idéal mais nécessaire pour interaction console)
    
    def start_scan_from_overlay(self):
        """Lancer le scan depuis l'overlay"""
        print(f"\n🚀 LANCEMENT SCAN")
        print(f"🔴 Rectangle: {self.rect}")
        
        # Masquer l'overlay
        self.overlay_active = False
        pygame.display.iconify()
        
        # Configuration rapide
        duration = 10.0
        interval = 0.1
        
        print(f"⏱️ Durée: {duration}s")
        print(f"📸 Intervalle: {interval}s")
        print(f"🎯 Captures estimées: {int(duration/interval)}")
        
        print("\n⏳ Démarrage dans 3 secondes...")
        for i in range(3, 0, -1):
            print(f"⏰ {i}...")
            time.sleep(1)
        
        self.perform_scan(duration, interval)
        
        # Réactiver l'overlay
        self.overlay_active = True
        pygame.display.iconify()  # Restaurer
    
    def perform_scan(self, duration, interval):
        """Effectuer le scan avec MSS"""
        try:
            self.scanning = True
            self.scan_data = []
            
            # Région MSS
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
            
            print(f"🚀 SCAN EN COURS !")
            print(f"📍 X: {start_x} → {end_x}")
            print(f"📍 Y: {y_pos}")
            
            start_time = time.time()
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                
                # Déplacer curseur
                pyautogui.moveTo(current_x, y_pos, duration=0.05)
                
                # Capturer avec MSS
                screenshot = self.sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                # Sauvegarder
                timestamp = int(time.time() * 1000)
                filename = f"overlay_scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                if i % 10 == 0:
                    print(f"📸 {i+1}/{num_captures}")
                
                time.sleep(interval)
            
            end_time = time.time()
            actual_fps = len(self.scan_data) / (end_time - start_time)
            
            print(f"\n🎉 SCAN TERMINÉ !")
            print(f"📊 {len(self.scan_data)} captures")
            print(f"⚡ FPS: {actual_fps:.1f}")
            
            # Sauvegarder métadonnées
            self.save_metadata(duration, interval, actual_fps)
            
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
                'method': 'Real Overlay + MSS',
                'platform': 'macOS',
                'screen_size': [self.screen_w, self.screen_h],
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Métadonnées: {metadata_file}")
    
    def cleanup(self):
        """Nettoyer les ressources"""
        try:
            pygame.quit()
            self.sct.close()
            print("🧹 Ressources nettoyées")
        except:
            pass

def main():
    print("🎯 REAL OVERLAY SCANNER")
    print("=" * 50)
    print("🔴 Vrai rectangle rouge flottant")
    print("🎮 Interface pygame interactive")
    print("🚀 Scan ultra-rapide avec MSS")
    print("🍎 Optimisé pour macOS")
    print()
    
    scanner = None
    try:
        scanner = RealOverlayScanner()
        scanner.run_overlay()
        
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        if scanner:
            scanner.cleanup()

if __name__ == '__main__':
    main() 