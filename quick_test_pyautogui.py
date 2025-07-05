#!/usr/bin/env python3
"""
Test PyAutoGUI simple - Balayage horizontal sans dépendances complexes
"""

import pyautogui
import time
import os
from PIL import Image

def test_simple_scan():
    """Test simple du balayage horizontal"""
    print("🎯 TEST SIMPLE - Balayage horizontal avec PyAutoGUI")
    print("=" * 50)
    
    # Désactiver le fail-safe pour le test
    pyautogui.FAILSAFE = False
    
    # Paramètres du test
    duration = 5.0  # 5 secondes
    interval = 0.25  # 1/4 seconde
    num_captures = int(duration / interval)
    
    print(f"📸 {num_captures} captures sur {duration} secondes")
    print(f"⏱️ Intervalle : {interval}s")
    
    # Demander les positions
    print("\n🎯 INSTRUCTIONS :")
    print("1. Positionnez votre souris au DÉBUT de la courbe")
    input("   Appuyez sur Entrée quand c'est prêt...")
    start_pos = pyautogui.position()
    print(f"   ✅ Début : {start_pos}")
    
    print("\n2. Positionnez votre souris à la FIN de la courbe")
    input("   Appuyez sur Entrée quand c'est prêt...")
    end_pos = pyautogui.position()
    print(f"   ✅ Fin : {end_pos}")
    
    # Calculer les étapes
    step_x = (end_pos.x - start_pos.x) / num_captures
    step_y = (end_pos.y - start_pos.y) / num_captures
    
    print(f"\n🚀 Démarrage du balayage dans 3 secondes...")
    time.sleep(3)
    
    # Créer le dossier de sortie
    output_dir = "test_scan"
    os.makedirs(output_dir, exist_ok=True)
    
    # Balayage
    screenshots = []
    print("\n📸 Balayage en cours...")
    
    for i in range(num_captures):
        # Position actuelle
        current_x = start_pos.x + (i * step_x)
        current_y = start_pos.y + (i * step_y)
        
        # Déplacer la souris
        pyautogui.moveTo(current_x, current_y, duration=0.1)
        
        # Capture d'écran
        screenshot = pyautogui.screenshot()
        
        # Sauvegarder
        filename = f"scan_{i:03d}.png"
        filepath = os.path.join(output_dir, filename)
        screenshot.save(filepath)
        
        screenshots.append({
            'index': i,
            'x': current_x,
            'y': current_y,
            'filename': filename
        })
        
        print(f"   📸 Capture {i+1}/{num_captures} - Position: ({current_x:.0f}, {current_y:.0f})")
        
        # Attendre
        time.sleep(interval)
    
    print(f"\n✅ Balayage terminé !")
    print(f"💾 {len(screenshots)} captures sauvegardées dans '{output_dir}/'")
    
    # Afficher les résultats
    print("\n📊 RÉSULTATS :")
    print(f"   🎯 Début : ({start_pos.x}, {start_pos.y})")
    print(f"   🎯 Fin : ({end_pos.x}, {end_pos.y})")
    print(f"   📏 Distance : {((end_pos.x - start_pos.x)**2 + (end_pos.y - start_pos.y)**2)**0.5:.0f} pixels")
    print(f"   ⏱️ Durée : {duration}s")
    print(f"   📸 Captures : {len(screenshots)}")
    
    return screenshots

def test_mouse_control():
    """Test basique du contrôle souris"""
    print("\n🎯 TEST CONTRÔLE SOURIS")
    print("=" * 30)
    
    # Position actuelle
    pos = pyautogui.position()
    print(f"📍 Position actuelle : {pos}")
    
    # Taille de l'écran
    size = pyautogui.size()
    print(f"📱 Taille écran : {size}")
    
    # Test de mouvement
    print("🔄 Test mouvement...")
    original_pos = pyautogui.position()
    
    # Petit carré
    moves = [(10, 0), (0, 10), (-10, 0), (0, -10)]
    for dx, dy in moves:
        pyautogui.move(dx, dy)
        time.sleep(0.2)
    
    # Retour à la position originale
    pyautogui.moveTo(original_pos.x, original_pos.y)
    print("✅ Mouvement OK")
    
    # Test capture
    print("📸 Test capture...")
    screenshot = pyautogui.screenshot()
    print(f"✅ Capture OK : {screenshot.size}")
    
    return True

def main():
    """Fonction principale"""
    print("🎯 PYAUTOGUI - TEST RAPIDE")
    print("=" * 50)
    
    try:
        # Test basique
        if test_mouse_control():
            print("\n✅ Tests basiques OK")
        else:
            print("\n❌ Tests basiques échoués")
            return
        
        # Test de balayage
        print("\n" + "="*50)
        choice = input("Voulez-vous tester le balayage horizontal ? (o/N) : ")
        
        if choice.lower().startswith('o'):
            screenshots = test_simple_scan()
            
            if screenshots:
                print(f"\n🎉 SUCCÈS ! PyAutoGUI fonctionne parfaitement")
                print(f"💡 Vos captures sont dans le dossier 'test_scan/'")
                print(f"🔧 Vous pouvez maintenant utiliser l'outil complet une fois Tesseract installé")
        else:
            print("\n👋 Test terminé")
            
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        if "failsafe" in str(e).lower():
            print("💡 Vous avez déclenché le fail-safe (souris dans un coin)")
        else:
            print("💡 Vérifiez les permissions d'accessibilité sur macOS")

if __name__ == "__main__":
    main() 