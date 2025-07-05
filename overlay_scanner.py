#!/usr/bin/env python3
"""
Overlay Scanner - Rectangle rouge avec poignées en surimpression sur l'écran
"""

import tkinter as tk
from tkinter import messagebox, ttk
import pyautogui
import time
import os
import json
import threading
from datetime import datetime

class OverlayScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "overlay_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
        
        # Variables pour l'overlay
        self.overlay = None
        self.dragging = False
        self.resizing = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_handle = None
        
        # Rectangle par défaut
        screen_w, screen_h = pyautogui.size()
        self.rect = {
            'x': screen_w // 4,
            'y': screen_h // 4,
            'width': screen_w // 2,
            'height': screen_h // 2
        }
        
        self.create_control_panel()
        self.create_overlay()
    
    def create_control_panel(self):
        """Panneau de contrôle"""
        self.root = tk.Tk()
        self.root.title("🎯 Overlay Scanner Controller")
        self.root.geometry("400x300")
        self.root.configure(bg='#f0f0f0')
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header = tk.Frame(self.root, bg='#d32f2f', height=60)
        header.pack(fill='x', pady=(0, 20))
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="🎯 Overlay Scanner", 
                              font=('Arial', 16, 'bold'), fg='white', bg='#d32f2f')
        title_label.pack(pady=15)
        
        # Infos rectangle
        info_frame = tk.LabelFrame(self.root, text="📐 Rectangle rouge", 
                                  font=('Arial', 10, 'bold'), fg='#d32f2f')
        info_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.rect_info = tk.Label(info_frame, text="", font=('Courier', 9))
        self.rect_info.pack(pady=10)
        
        # Configuration
        config_frame = tk.LabelFrame(self.root, text="⚙️ Configuration", 
                                    font=('Arial', 10, 'bold'), fg='#d32f2f')
        config_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        # Durée
        tk.Label(config_frame, text="Durée (sec):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.duration_var = tk.StringVar(value="10")
        duration_spin = tk.Spinbox(config_frame, from_=1, to=60, increment=0.5, 
                                  textvariable=self.duration_var, width=10)
        duration_spin.grid(row=0, column=1, padx=5, pady=5)
        
        # Intervalle
        tk.Label(config_frame, text="Intervalle (sec):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.interval_var = tk.StringVar(value="0.25")
        interval_spin = tk.Spinbox(config_frame, from_=0.1, to=2, increment=0.05, 
                                  textvariable=self.interval_var, width=10)
        interval_spin.grid(row=1, column=1, padx=5, pady=5)
        
        # Boutons
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill='x', padx=20, pady=20)
        
        self.start_btn = tk.Button(button_frame, text="🚀 Commencer Scan", 
                                  command=self.start_scan, bg='#d32f2f', fg='white', 
                                  font=('Arial', 10, 'bold'), height=2)
        self.start_btn.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        self.stop_btn = tk.Button(button_frame, text="⏹️ Arrêter", 
                                 command=self.stop_scan, bg='#666', fg='white', 
                                 font=('Arial', 10, 'bold'), height=2, state='disabled')
        self.stop_btn.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # Status
        self.status_label = tk.Label(self.root, text="✅ Rectangle rouge affiché ! Déplacez-le et redimensionnez-le.", 
                                    fg='#2e7d2e', font=('Arial', 9))
        self.status_label.pack(pady=10)
        
        # Mettre à jour les infos
        self.update_rect_info()
        
        # Fermeture
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_overlay(self):
        """Créer l'overlay avec rectangle rouge"""
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Overlay")
        self.overlay.configure(bg='black')
        self.overlay.attributes('-alpha', 0.3)  # Transparence
        self.overlay.attributes('-topmost', True)  # Toujours au dessus
        self.overlay.overrideredirect(True)  # Pas de barre de titre
        
        # Position et taille
        self.overlay.geometry(f"{self.rect['width']}x{self.rect['height']}+{self.rect['x']}+{self.rect['y']}")
        
        # Canvas pour dessiner
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, bg='black')
        self.canvas.pack(fill='both', expand=True)
        
        # Dessiner le rectangle
        self.draw_rectangle()
        
        # Bindings pour interaction
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Motion>', self.on_motion)
    
    def draw_rectangle(self):
        """Dessiner le rectangle avec poignées"""
        self.canvas.delete("all")
        
        w = self.rect['width']
        h = self.rect['height']
        
        # Rectangle principal (rouge)
        self.canvas.create_rectangle(2, 2, w-2, h-2, outline='red', width=4, fill='')
        
        # Poignées de redimensionnement (carrés blancs)
        handle_size = 8
        handles = [
            (w-handle_size, h-handle_size),  # Coin bas-droite
            (w//2-handle_size//2, h-handle_size),  # Bas centre
            (w-handle_size, h//2-handle_size//2),  # Droite centre
        ]
        
        for i, (x, y) in enumerate(handles):
            self.canvas.create_rectangle(x, y, x+handle_size, y+handle_size, 
                                       fill='white', outline='red', width=2, tags=f'handle_{i}')
        
        # Texte d'info
        self.canvas.create_text(w//2, h//2, text="🔴 ZONE DE SCAN\nDéplacez-moi !", 
                               fill='red', font=('Arial', 12, 'bold'), justify='center')
    
    def on_click(self, event):
        """Gérer le clic"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # Vérifier si on clique sur une poignée
        clicked_item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(clicked_item)
        
        if any(tag.startswith('handle_') for tag in tags):
            self.resizing = True
            self.resize_handle = [tag for tag in tags if tag.startswith('handle_')][0]
        else:
            self.dragging = True
    
    def on_drag(self, event):
        """Gérer le déplacement"""
        if self.dragging:
            # Déplacement de la fenêtre
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            new_x = self.rect['x'] + dx
            new_y = self.rect['y'] + dy
            
            # Limites d'écran
            screen_w, screen_h = pyautogui.size()
            new_x = max(0, min(new_x, screen_w - self.rect['width']))
            new_y = max(0, min(new_y, screen_h - self.rect['height']))
            
            self.rect['x'] = new_x
            self.rect['y'] = new_y
            self.overlay.geometry(f"{self.rect['width']}x{self.rect['height']}+{new_x}+{new_y}")
            
        elif self.resizing:
            # Redimensionnement
            if self.resize_handle == 'handle_0':  # Coin bas-droite
                new_width = max(100, event.x + 10)
                new_height = max(100, event.y + 10)
                
                screen_w, screen_h = pyautogui.size()
                new_width = min(new_width, screen_w - self.rect['x'])
                new_height = min(new_height, screen_h - self.rect['y'])
                
                self.rect['width'] = new_width
                self.rect['height'] = new_height
                
                self.overlay.geometry(f"{new_width}x{new_height}+{self.rect['x']}+{self.rect['y']}")
                self.draw_rectangle()
        
        self.update_rect_info()
    
    def on_release(self, event):
        """Relâcher le clic"""
        self.dragging = False
        self.resizing = False
        self.resize_handle = None
    
    def on_motion(self, event):
        """Changer le curseur selon la zone"""
        clicked_item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(clicked_item)
        
        if any(tag.startswith('handle_') for tag in tags):
            self.canvas.configure(cursor='bottom_right_corner')
        else:
            self.canvas.configure(cursor='fleur')
    
    def update_rect_info(self):
        """Mettre à jour les infos du rectangle"""
        info_text = f"Position: ({self.rect['x']}, {self.rect['y']})\n"
        info_text += f"Taille: {self.rect['width']} × {self.rect['height']} px"
        self.rect_info.config(text=info_text)
    
    def start_scan(self):
        """Commencer le scan"""
        duration = float(self.duration_var.get())
        interval = float(self.interval_var.get())
        
        # Masquer l'overlay pendant le scan
        self.overlay.withdraw()
        
        self.status_label.config(text="🚀 Scan démarre dans 3 secondes...", fg='#d32f2f')
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Lancer le scan dans un thread
        scan_thread = threading.Thread(target=self.perform_scan, args=(duration, interval))
        scan_thread.daemon = True
        scan_thread.start()
    
    def perform_scan(self, duration, interval):
        """Effectuer le scan"""
        try:
            # Attendre 3 secondes
            time.sleep(3)
            
            self.scanning = True
            self.scan_data = []
            
            num_captures = int(duration / interval)
            start_x = self.rect['x'] + 20
            end_x = self.rect['x'] + self.rect['width'] - 20
            y_pos = self.rect['y'] + self.rect['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                pyautogui.moveTo(current_x, y_pos, duration=0.1)
                
                screenshot = pyautogui.screenshot()
                timestamp = int(time.time() * 1000)
                filename = f"overlay_scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                screenshot.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                # Mettre à jour le status
                self.root.after(0, lambda: self.status_label.config(
                    text=f"📸 Scan en cours... {len(self.scan_data)} captures", fg='#2e7d2e'))
                
                time.sleep(interval)
            
            # Sauvegarder métadonnées
            self.save_metadata(duration, interval)
            
        except Exception as e:
            print(f"Erreur scan: {e}")
        finally:
            self.scanning = False
            # Réafficher l'overlay
            self.root.after(0, self.scan_finished)
    
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
    
    def scan_finished(self):
        """Scan terminé"""
        self.overlay.deiconify()  # Réafficher l'overlay
        self.status_label.config(text=f"🎉 Scan terminé ! {len(self.scan_data)} captures sauvées", fg='#2e7d2e')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
    
    def stop_scan(self):
        """Arrêter le scan"""
        self.scanning = False
        self.status_label.config(text="⏹️ Scan arrêté", fg='#666')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.overlay.deiconify()
    
    def on_closing(self):
        """Fermer l'application"""
        if self.overlay:
            self.overlay.destroy()
        self.root.destroy()
    
    def run(self):
        """Lancer l'application"""
        self.root.mainloop()

if __name__ == '__main__':
    print("🎯 OVERLAY SCANNER")
    print("=" * 50)
    print("✅ Rectangle rouge avec poignées en surimpression")
    print("✅ Déplacez et redimensionnez le rectangle")
    print("✅ Scan horizontal automatique")
    print("✅ Interface de contrôle séparée")
    print()
    print("🔴 Le rectangle rouge va apparaître sur votre écran !")
    print("📐 Déplacez-le sur votre graphique et redimensionnez-le")
    print("🚀 Puis cliquez 'Commencer Scan' dans le panneau")
    print()
    
    try:
        scanner = OverlayScanner()
        scanner.run()
    except Exception as e:
        print(f"Erreur: {e}")
        messagebox.showerror("Erreur", f"Impossible de lancer l'overlay: {e}") 