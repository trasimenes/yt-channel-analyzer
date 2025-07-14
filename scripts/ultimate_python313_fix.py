#!/usr/bin/env python3
"""
🚀 ULTIMATE PYTHON 3.13 FIX
Utilise UNIQUEMENT les versions précompilées disponibles
"""

import sys
import subprocess
import os

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
    print("🚀 ULTIMATE PYTHON 3.13 FIX")
    print("Versions précompilées SEULEMENT")
    print("=" * 50)

    # 1. Arrêt des processus
    print("🛑 Arrêt des processus pip...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")

    # 2. Nettoyage
    print("🧹 Nettoyage...")
    run_cmd("pip uninstall -y torch torchvision torchaudio sentence-transformers scipy scikit-learn", ignore_errors=True)

    # 3. Upgrade pip
    print("📦 Upgrade pip...")
    run_cmd("python -m pip install --upgrade pip setuptools wheel")

    # 4. Installation versions précompilées UNIQUEMENT
    print("🔗 Installation numpy (précompilé)...")
    run_cmd("pip install numpy==1.26.4")  # Version qui a marché
    
    print("🔗 Installation scipy (précompilé)...")
    # Essai avec versions précompilées uniquement
    success = run_cmd("pip install --only-binary=all scipy", ignore_errors=True)
    if not success:
        print("⚠️  Scipy non disponible en précompilé - on skip")
    
    print("🔗 Installation scikit-learn (précompilé)...")
    success = run_cmd("pip install --only-binary=all scikit-learn", ignore_errors=True)
    if not success:
        print("⚠️  scikit-learn non disponible en précompilé - on skip")

    # 5. Installation PyTorch (version qui existe vraiment)
    print("🔥 Installation PyTorch...")
    
    # Essai version actuelle stable
    success = run_cmd("pip install torch torchvision torchaudio", ignore_errors=True)
    
    if not success:
        print("🔄 Essai avec index PyTorch...")
        success = run_cmd("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu", ignore_errors=True)
    
    if not success:
        print("🔄 Essai PyTorch nightly...")
        success = run_cmd("pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cpu", ignore_errors=True)
    
    if not success:
        print("⚠️  PyTorch non disponible - on continue sans")

    # 6. Installation transformers et tokenizers
    print("🔗 Installation transformers...")
    run_cmd("pip install transformers tokenizers", ignore_errors=True)

    # 7. Installation sentence-transformers (sans dépendances si nécessaire)
    print("🧠 Installation sentence-transformers...")
    success = run_cmd("pip install sentence-transformers", ignore_errors=True)
    
    if not success:
        print("🔄 Installation sans dépendances...")
        success = run_cmd("pip install sentence-transformers --no-deps", ignore_errors=True)

    # 8. Test final
    print("\n🧪 Test des imports...")
    
    success_count = 0
    total_tests = 4
    
    try:
        import numpy as np
        print(f"✅ numpy: {np.__version__}")
        success_count += 1
    except ImportError:
        print("❌ numpy manquant")
    
    try:
        import sklearn
        print(f"✅ scikit-learn: {sklearn.__version__}")
        success_count += 1
    except ImportError:
        print("⚠️  scikit-learn manquant (optionnel)")
    
    try:
        import transformers
        print(f"✅ transformers: {transformers.__version__}")
        success_count += 1
    except ImportError:
        print("❌ transformers manquant")
    
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
        success_count += 1
        
        # Test minimal du modèle
        try:
            print("🧪 Test minimal du modèle...")
            from sentence_transformers import SentenceTransformer
            
            # Modèle très simple qui ne nécessite pas PyTorch
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            embeddings = model.encode(['Test'])
            print(f"✅ Modèle fonctionnel: {embeddings.shape}")
            
        except Exception as e:
            print(f"⚠️  Erreur modèle: {e}")
            print("💡 Le modèle peut nécessiter PyTorch")
            
    except ImportError:
        print("❌ sentence-transformers manquant")

    print(f"\n📊 Résultat: {success_count}/{total_tests} packages installés")
    
    if success_count >= 2:
        print("🎉 Installation partielle réussie!")
        print("💡 Vous pouvez utiliser les packages installés")
        
        if success_count < total_tests:
            print("\n🔧 Pour une installation complète, considérez:")
            print("   1. Installer Python 3.12 (recommandé)")
            print("   2. Utiliser conda au lieu de pip")
            print("   3. Installer gfortran pour scipy")
        
        return True
    else:
        print("❌ Installation échouée")
        print("💡 Python 3.13 n'est pas encore fully supporté")
        print("   Recommandation: Downgrade vers Python 3.12")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 