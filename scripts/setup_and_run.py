#!/usr/bin/env python3
"""
Script tout-en-un pour nettoyer les duplicatas et démarrer le serveur
"""

import subprocess
import sys
import socket
from pathlib import Path

def find_free_port(start_port=8080):
    """Trouve un port libre"""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise Exception("Aucun port libre trouvé")

def run_cleanup():
    """Exécute le nettoyage des duplicatas"""
    print("🧹 Nettoyage des duplicatas en cours...")
    try:
        result = subprocess.run([sys.executable, 'clean_duplicates.py'], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("⚠️ Warnings:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
        return False

def main():
    print("🎯 Setup et démarrage de YT Channel Analyzer")
    print("=" * 50)
    
    # Vérifier que les fichiers existent
    required_files = ['app.py', 'clean_duplicates.py']
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Fichier manquant: {file}")
            return
    
    # Étape 1: Nettoyer les duplicatas
    print("\n📋 Étape 1: Nettoyage des duplicatas")
    if not run_cleanup():
        print("⚠️ Le nettoyage a échoué, mais on continue...")
    
    # Étape 2: Démarrer le serveur
    print("\n🚀 Étape 2: Démarrage du serveur")
    try:
        port = find_free_port(8080)
        print(f"📱 Serveur démarré sur: http://localhost:{port}")
        print(f"🔧 Pour arrêter: Ctrl+C")
        print("=" * 50)
        
        # Importer et démarrer l'app
        from app import app
        app.run(debug=True, host='0.0.0.0', port=port)
        
    except KeyboardInterrupt:
        print("\n👋 Serveur arrêté par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")

if __name__ == "__main__":
    main() 