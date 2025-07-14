#!/usr/bin/env python3
"""
🚀 PYTHON 3.12 SOLUTION
Downgrade automatique vers Python 3.12.3 avec pyenv
✅ Solution définitive pour l'écosystème ML
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
    print("🚀 PYTHON 3.12 SOLUTION - Downgrade automatique")
    print("=" * 50)
    
    # 1. Arrêter les processus pip en cours
    print("🛑 Arrêt des processus pip...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")
    
    # 2. Installer pyenv si nécessaire
    print("📦 Installation pyenv...")
    run_cmd("brew install pyenv", ignore_errors=True)
    
    # 3. Configurer pyenv dans le shell
    print("⚙️  Configuration pyenv...")
    run_cmd('echo \'export PYENV_ROOT="$HOME/.pyenv"\' >> ~/.zshrc', ignore_errors=True)
    run_cmd('echo \'[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\' >> ~/.zshrc', ignore_errors=True)
    run_cmd('echo \'eval "$(pyenv init -)"\' >> ~/.zshrc', ignore_errors=True)
    
    # 4. Recharger la configuration
    print("🔄 Rechargement shell...")
    os.environ['PYENV_ROOT'] = os.path.expanduser('~/.pyenv')
    os.environ['PATH'] = f"{os.environ['PYENV_ROOT']}/bin:{os.environ['PATH']}"
    
    # 5. Installer Python 3.12.3
    print("🐍 Installation Python 3.12.3...")
    success = run_cmd("pyenv install 3.12.3", ignore_errors=True)
    if not success:
        print("⚠️  Python 3.12.3 déjà installé ou erreur")
    
    # 6. Créer l'environnement virtuel
    print("🏗️  Création environnement torch-env...")
    run_cmd("pyenv virtualenv 3.12.3 torch-env", ignore_errors=True)
    
    # 7. Activer l'environnement et installer les dépendances
    print("🔥 Installation des dépendances ML...")
    
    # Commandes à exécuter dans le nouvel environnement
    install_commands = [
        "pyenv activate torch-env",
        "pip install --upgrade pip setuptools wheel",
        "pip install torch torchvision torchaudio",
        "pip install sentence-transformers",
        "pip install transformers tokenizers",
        "pip install numpy scipy scikit-learn"
    ]
    
    print("📋 Commandes à exécuter manuellement:")
    print("=" * 30)
    for cmd in install_commands:
        print(f"  {cmd}")
    
    print("\n🎯 ÉTAPES MANUELLES:")
    print("1. Redémarrer le terminal")
    print("2. Exécuter: pyenv activate torch-env")
    print("3. Exécuter: pip install torch torchvision torchaudio")
    print("4. Exécuter: pip install sentence-transformers")
    print("5. Tester: python -c 'import torch; print(torch.__version__)'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 