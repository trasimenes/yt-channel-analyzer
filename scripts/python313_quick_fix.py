#!/usr/bin/env python3
"""
⚡ QUICK FIX INSTALL
✅ Ultra-rapide pour Mac Intel avec Python 3.13.2
"""

import sys
import subprocess
import os

def run_cmd(cmd):
    """Exécute une commande shell"""
    print(f"🔄 {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, timeout=600)
        print("✅ Succès")
        return True
    except subprocess.TimeoutExpired:
        print("⏰ Timeout sur la commande")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("⚡ QUICK FIX INSTALL for Mac Intel + Python 3.13.2")
    print("=" * 50)

    # 1. Arrêt des installations conflictuelles
    print("🛑 Arrêt des processus pip en cours...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")

    # 2. Nettoyage environnement
    print("🧹 Nettoyage packages...")
    run_cmd("pip uninstall -y torch torchvision torchaudio sentence-transformers")

    # 3. Upgrade outils de build
    print("📦 Upgrade pip/setuptools/wheel...")
    run_cmd("python3 -m pip install --upgrade pip setuptools wheel")

    # 4. Dépendances de base
    print("🔗 Installation dépendances Python...")
    run_cmd("pip install numpy==1.26.4")
    run_cmd("pip install scipy==1.12.0")
    run_cmd("pip install scikit-learn==1.4.2")

    # 5. Installation PyTorch (version 2.7.1 compatible Python 3.13)
    print("🔥 Installation PyTorch 2.7.1...")
    success = run_cmd("pip install torch==2.7.1 torchvision==0.18.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cpu")

    if not success:
        print("🔄 Retente installation PyTorch sans index...")
        success = run_cmd("pip install torch torchvision torchaudio")

    if not success:
        print("❌ PyTorch KO sur Python 3.13.2")
        return False

    # 6. Installation sentence-transformers
    print("🧠 Installation sentence-transformers...")
    success = run_cmd("pip install sentence-transformers==2.6.1")

    if not success:
        print("🔄 Retente sentence-transformers version récente...")
        success = run_cmd("pip install sentence-transformers")

    if not success:
        print("❌ sentence-transformers KO")
        return False

    # 7. Vérification finale
    print("🧪 Vérification des imports...")
    try:
        import torch
        print(f"✅ torch version: {torch.__version__}")
        import sentence_transformers
        print(f"✅ sentence-transformers version: {sentence_transformers.__version__}")
    except ImportError as e:
        print(f"❌ Import KO: {e}")
        return False

    print("\n🎉 Tout est installé et prêt sur Python 3.13.2 ✅")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 