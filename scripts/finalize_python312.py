#!/usr/bin/env python3
"""
🎯 FINALIZE PYTHON 3.12 SETUP
Script pour finaliser l'installation après brew install python@3.12
"""

import os
import sys
import subprocess
import time

def run_cmd(cmd, ignore_errors=False):
    """Exécute une commande shell"""
    print(f"🔄 {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=not ignore_errors, timeout=300)
        if result.returncode == 0:
            print("✅ Succès")
            return True
        else:
            print(f"⚠️  Échec mais on continue...")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ Timeout")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("🎯 FINALIZE PYTHON 3.12 SETUP")
    print("=" * 35)
    
    # 1. Arrêter les processus pip en boucle
    print("🛑 Arrêt des processus pip en boucle...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")
    time.sleep(2)
    
    # 2. Vérifier Python 3.12 installé
    print("🐍 Vérification Python 3.12...")
    result = run_cmd("python3.12 --version", ignore_errors=True)
    if not result:
        print("❌ Python 3.12 non trouvé")
        print("💡 Exécutez: brew install python@3.12")
        return False
    
    # 3. Créer l'environnement virtuel ML
    print("🏗️  Création environnement virtuel ML...")
    run_cmd("python3.12 -m venv venv_ml", ignore_errors=True)
    
    # 4. Activer et installer les dépendances
    print("🔥 Installation des dépendances ML...")
    
    # Commandes d'installation
    install_commands = [
        "source venv_ml/bin/activate",
        "pip install --upgrade pip setuptools wheel",
        "pip install torch torchvision torchaudio",
        "pip install sentence-transformers",
        "pip install transformers tokenizers",
        "pip install numpy scipy scikit-learn",
        "pip install requests tqdm huggingface-hub"
    ]
    
    print("📋 Commandes à exécuter:")
    print("=" * 25)
    for cmd in install_commands:
        print(f"  {cmd}")
    
    print("\n🎯 ÉTAPES FINALES:")
    print("1. Attendre que Homebrew finisse")
    print("2. Exécuter: source venv_ml/bin/activate")
    print("3. Exécuter: pip install torch sentence-transformers")
    print("4. Tester: python -c 'import torch; import sentence_transformers; print(\"✅ Succès\")'")
    
    print("\n💡 POUR VOTRE APP:")
    print("- Modifier le code pour utiliser venv_ml au lieu de venv_semantic")
    print("- Ou copier les packages installés vers venv_semantic")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 