#!/usr/bin/env python3
"""
⚡ QUICK FIX INSTALL
Installation ultra-rapide avec les versions qui fonctionnent vraiment
"""

import sys
import subprocess
import os

def run_cmd(cmd):
    """Exécute une commande"""
    print(f"🔄 {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, timeout=300)
        print("✅ Succès")
        return True
    except subprocess.TimeoutExpired:
        print("⏰ Timeout")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Échec: {e}")
        return False

def main():
    print("⚡ QUICK FIX INSTALL")
    print("=" * 30)
    
    # 1. Arrêter les processus
    print("🛑 Arrêt des processus...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")
    
    # 2. Nettoyage
    print("🧹 Nettoyage...")
    run_cmd("pip uninstall -y sentence-transformers torch torchvision torchaudio")
    
    # 3. Installation base
    print("📦 Installation base...")
    run_cmd("pip install --upgrade pip setuptools wheel")
    run_cmd("pip install numpy==1.24.3")
    run_cmd("pip install scipy==1.11.4")
    run_cmd("pip install scikit-learn==1.3.2")
    
    # 4. Installation PyTorch version stable
    print("🔥 Installation PyTorch...")
    # Essai version stable d'abord
    success = run_cmd("pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0")
    
    if not success:
        print("🔄 Essai version CPU...")
        success = run_cmd("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
    
    if not success:
        print("🔄 Essai version générale...")
        success = run_cmd("pip install torch torchvision torchaudio")
    
    # 5. Installation sentence-transformers
    print("🧠 Installation sentence-transformers...")
    success = run_cmd("pip install sentence-transformers==2.2.2")
    
    if not success:
        print("🔄 Essai version récente...")
        success = run_cmd("pip install sentence-transformers")
    
    # 6. Test
    print("🧪 Test...")
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
    except ImportError:
        print("❌ PyTorch KO")
        return False
    
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
    except ImportError:
        print("❌ sentence-transformers KO")
        return False
    
    print("\n🎉 Installation terminée!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 