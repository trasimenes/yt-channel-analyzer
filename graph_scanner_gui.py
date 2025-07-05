#!/usr/bin/env python3
"""
Graph Scanner GUI - Interface graphique avec rectangle rouge pour définir la région
"""

import tkinter as tk
from tkinter import ttk
import pyautogui
import time
import os
import threading
from PIL import Image, ImageTk
import json

class GraphScannerGUI:
    """
    Interface graphique pour scanner des graphiques avec un rectangle de sélection
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Graph Scanner - Sélection de région")
        self.root.geometry("400x300")
        self.root.attributes('-topmost', True)  # Toujours au-dessus
        
        # Variables
        self.overlay_window = None
        self.scanning = False
        self.scan_thread = None
        self.output_dir = "graph_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Rectangle par défaut (centre de l'écran)
        screen_width, screen_height = pyautogui.size()
        self.rect_x = screen_width // 4
        self.rect_y = screen_height // 4
        self.rect_width = screen_width // 2
        self.rect_height = screen_height // 2
        
        # Configuration
        pyautogui.FAILSAFE = False
        
        self.setup_ui()
        self.create_overlay()
    
    def setup_ui(self):
        """
        Créer l'interface utilisateur
        """
        # Titre
        title_label = tk.Label(
            self.root, 
            text="📊 Graph Scanner", 
            font=("Arial", 16, "bold"),
            fg="red"
        )
        title_label.pack(pady=10)
        
        # Instructions
        instructions = tk.Label(
            self.root,
            text="1. Déplacez/redimensionnez le rectangle rouge\n"
                 "2. Positionnez-le sur votre graphique\n"
                 "3. Cliquez sur 'Commencer le scan'",
            justify="left",
            font=("Arial", 10)
        )
        instructions.pack(pady=10)
        
        # Frame pour les contrôles de position
        pos_frame = ttk.LabelFrame(self.root, text="Position du rectangle", padding=10)
        pos_frame.pack(pady=10, padx=20, fill="x")
        
        # Position X
        tk.Label(pos_frame, text="X:").grid(row=0, column=0, sticky="w")
        self.x_var = tk.IntVar(value=self.rect_x)
        self.x_spin = tk.Spinbox(
            pos_frame, from_=0, to=2880, textvariable=self.x_var, 
            width=8, command=self.update_overlay
        )
        self.x_spin.grid(row=0, column=1, padx=5)
        
        # Position Y
        tk.Label(pos_frame, text="Y:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.y_var = tk.IntVar(value=self.rect_y)
        self.y_spin = tk.Spinbox(
            pos_frame, from_=0, to=1800, textvariable=self.y_var,
            width=8, command=self.update_overlay
        )
        self.y_spin.grid(row=0, column=3, padx=5)
        
        # Largeur
        tk.Label(pos_frame, text="Largeur:").grid(row=1, column=0, sticky="w")
        self.width_var = tk.IntVar(value=self.rect_width)
        self.width_spin = tk.Spinbox(
            pos_frame, from_=100, to=2880, textvariable=self.width_var,
            width=8, command=self.update_overlay
        )
        self.width_spin.grid(row=1, column=1, padx=5)
        
        # Hauteur
        tk.Label(pos_frame, text="Hauteur:").grid(row=1, column=2, sticky="w", padx=(20,0))
        self.height_var = tk.IntVar(value=self.rect_height)
        self.height_spin = tk.Spinbox(
            pos_frame, from_=100, to=1800, textvariable=self.height_var,
            width=8, command=self.update_overlay
        )
        self.height_spin.grid(row=1, column=3, padx=5)
        
        # Configuration du scan
        scan_frame = ttk.LabelFrame(self.root, text="Configuration du scan", padding=10)
        scan_frame.pack(pady=10, padx=20, fill="x")
        
        # Durée
        tk.Label(scan_frame, text="Durée (secondes):").grid(row=0, column=0, sticky="w")
        self.duration_var = tk.DoubleVar(value=10.0)
        duration_spin = tk.Spinbox(
            scan_frame, from_=1.0, to=60.0, increment=0.5,
            textvariable=self.duration_var, width=8
        )
        duration_spin.grid(row=0, column=1, padx=5)
        
        # Intervalle
        tk.Label(scan_frame, text="Intervalle (secondes):").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.interval_var = tk.DoubleVar(value=0.25)
        interval_spin = tk.Spinbox(
            scan_frame, from_=0.1, to=2.0, increment=0.05,
            textvariable=self.interval_var, width=8
        )
        interval_spin.grid(row=0, column=3, padx=5)
        
        # Boutons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Bouton principal
        self.start_button = tk.Button(
            button_frame,
            text="🚀 Commencer le scan",
            font=("Arial", 12, "bold"),
            bg="red",
            fg="white",
            command=self.start_scan,
            width=20,
            height=2
        )
        self.start_button.pack(side="left", padx=10)
        
        # Bouton arrêt
        self.stop_button = tk.Button(
            button_frame,
            text="⏹️ Arrêter",
            font=("Arial", 12),
            bg="gray",
            fg="white",
            command=self.stop_scan,
            width=15,
            height=2,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)
        
        # Status
        self.status_var = tk.StringVar(value="Prêt à scanner")
        status_label = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 10))
        status_label.pack(pady=5)
        
        # Bind pour fermer proprement
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_overlay(self):
        """
        Créer la fenêtre overlay avec le rectangle rouge
        """
        if self.overlay_window:
            self.overlay_window.destroy()
        
        # Fenêtre overlay transparente
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.attributes('-alpha', 0.3)  # Transparence
        self.overlay_window.attributes('-topmost', True)  # Au-dessus de tout
        self.overlay_window.overrideredirect(True)  # Pas de barre de titre
        
        # Positionner et dimensionner
        self.update_overlay_geometry()
        
        # Canvas pour dessiner le rectangle
        canvas = tk.Canvas(
            self.overlay_window, 
            highlightthickness=0,
            bg='red'
        )
        canvas.pack(fill="both", expand=True)
        
        # Bind pour déplacer avec la souris
        canvas.bind("<Button-1>", self.start_drag)
        canvas.bind("<B1-Motion>", self.on_drag)
        canvas.bind("<ButtonRelease-1>", self.end_drag)
        
        self.drag_start_x = 0
        self.drag_start_y = 0
    
    def update_overlay_geometry(self):
        """
        Mettre à jour la géométrie de l'overlay
        """
        if self.overlay_window:
            geometry = f"{self.rect_width}x{self.rect_height}+{self.rect_x}+{self.rect_y}"
            self.overlay_window.geometry(geometry)
    
    def update_overlay(self):
        """
        Mettre à jour l'overlay après modification des spinbox
        """
        self.rect_x = self.x_var.get()
        self.rect_y = self.y_var.get()
        self.rect_width = self.width_var.get()
        self.rect_height = self.height_var.get()
        self.update_overlay_geometry()
    
    def start_drag(self, event):
        """
        Commencer le déplacement du rectangle
        """
        self.drag_start_x = event.x_root - self.rect_x
        self.drag_start_y = event.y_root - self.rect_y
    
    def on_drag(self, event):
        """
        Déplacer le rectangle
        """
        new_x = event.x_root - self.drag_start_x
        new_y = event.y_root - self.drag_start_y
        
        # Limiter aux bords de l'écran
        screen_width, screen_height = pyautogui.size()
        new_x = max(0, min(new_x, screen_width - self.rect_width))
        new_y = max(0, min(new_y, screen_height - self.rect_height))
        
        self.rect_x = new_x
        self.rect_y = new_y
        
        # Mettre à jour les spinbox
        self.x_var.set(new_x)
        self.y_var.set(new_y)
        
        self.update_overlay_geometry()
    
    def end_drag(self, event):
        """
        Terminer le déplacement
        """
        pass
    
    def start_scan(self):
        """
        Démarrer le scan horizontal
        """
        if self.scanning:
            return
        
        self.scanning = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        # Cacher l'overlay pendant le scan
        if self.overlay_window:
            self.overlay_window.withdraw()
        
        # Lancer le scan dans un thread séparé
        self.scan_thread = threading.Thread(target=self.perform_scan)
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def perform_scan(self):
        """
        Effectuer le scan horizontal
        """
        try:
            duration = self.duration_var.get()
            interval = self.interval_var.get()
            num_captures = int(duration / interval)
            
            self.update_status(f"Scan en cours... 0/{num_captures}")
            
            # Calculer les positions de début et fin (gauche à droite dans le rectangle)
            start_x = self.rect_x + 20  # Marge de 20px
            end_x = self.rect_x + self.rect_width - 20
            start_y = self.rect_y + self.rect_height // 2  # Milieu vertical
            end_y = start_y  # Ligne horizontale
            
            # Calculer les étapes
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            step_y = (end_y - start_y) / max(1, num_captures - 1)
            
            # Données capturées
            scan_data = []
            
            for i in range(num_captures):
                if not self.scanning:  # Check si arrêté
                    break
                
                # Position actuelle
                current_x = start_x + (i * step_x)
                current_y = start_y + (i * step_y)
                
                # Déplacer la souris
                pyautogui.moveTo(current_x, current_y, duration=0.1)
                
                # Capture d'écran
                screenshot = pyautogui.screenshot()
                
                # Sauvegarder
                timestamp = int(time.time() * 1000)  # Millisecondes
                filename = f"scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                screenshot.save(filepath)
                
                # Stocker les données
                scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': current_y,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                # Mettre à jour le status
                self.update_status(f"Scan en cours... {i+1}/{num_captures}")
                
                # Attendre l'intervalle
                time.sleep(interval)
            
            # Sauvegarder les métadonnées
            if scan_data:
                self.save_scan_metadata(scan_data)
                self.update_status(f"✅ Scan terminé ! {len(scan_data)} captures")
            else:
                self.update_status("❌ Scan annulé")
                
        except Exception as e:
            self.update_status(f"❌ Erreur: {str(e)}")
        
        finally:
            # Réactiver les boutons
            self.root.after(0, self.scan_finished)
    
    def save_scan_metadata(self, scan_data):
        """
        Sauvegarder les métadonnées du scan
        """
        timestamp = int(time.time())
        metadata_file = os.path.join(self.output_dir, f"scan_metadata_{timestamp}.json")
        
        metadata = {
            'scan_info': {
                'total_captures': len(scan_data),
                'duration': self.duration_var.get(),
                'interval': self.interval_var.get(),
                'region': {
                    'x': self.rect_x,
                    'y': self.rect_y,
                    'width': self.rect_width,
                    'height': self.rect_height
                },
                'scan_date': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'captures': scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Métadonnées sauvegardées: {metadata_file}")
    
    def scan_finished(self):
        """
        Actions à effectuer quand le scan est terminé
        """
        self.scanning = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        # Remettre l'overlay
        if self.overlay_window:
            self.overlay_window.deiconify()
    
    def stop_scan(self):
        """
        Arrêter le scan
        """
        self.scanning = False
        self.update_status("Arrêt du scan...")
    
    def update_status(self, message):
        """
        Mettre à jour le message de status
        """
        if self.root:
            self.root.after(0, lambda: self.status_var.set(message))
    
    def on_closing(self):
        """
        Fermer l'application proprement
        """
        self.scanning = False
        if self.overlay_window:
            self.overlay_window.destroy()
        self.root.destroy()
    
    def run(self):
        """
        Lancer l'application
        """
        print("🎯 Lancement de Graph Scanner GUI")
        print("💡 Utilisez le rectangle rouge pour définir la région à scanner")
        self.root.mainloop()

def main():
    """
    Fonction principale
    """
    print("🎯 GRAPH SCANNER GUI")
    print("=" * 50)
    print("Interface graphique pour scanner des graphiques")
    print("✅ Rectangle rouge déplaçable")
    print("✅ Scan horizontal automatique")
    print("✅ Captures toutes les 1/4 secondes")
    print()
    
    try:
        app = GraphScannerGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Application interrompue")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main() 