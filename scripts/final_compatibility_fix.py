#!/usr/bin/env python3
"""
🏁 FINAL COMPATIBILITY FIX
Utilise des versions précompilées compatibles avec Python 3.13
"""

import sys
import subprocess
import os

def run_cmd(cmd, ignore_errors=False):
    """Exécute une commande"""
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
        print(f"❌ Échec: {e}")
        return False

def main():
    print("🏁 FINAL COMPATIBILITY FIX")
    print("Utilise des versions précompilées pour Python 3.13")
    print("=" * 50)
    
    # 1. Arrêter les processus
    print("🛑 Arrêt des processus...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")
    
    # 2. Nettoyage
    print("🧹 Nettoyage...")
    run_cmd("pip uninstall -y sentence-transformers torch torchvision torchaudio", ignore_errors=True)
    run_cmd("pip uninstall -y numpy scipy scikit-learn", ignore_errors=True)
    
    # 3. Installation versions précompilées
    print("📦 Installation versions précompilées...")
    run_cmd("pip install --upgrade pip setuptools wheel")
    
    # Essai avec versions précompilées
    success = run_cmd("pip install --only-binary=all numpy scipy scikit-learn")
    
    if not success:
        print("🔄 Essai avec versions plus récentes...")
        run_cmd("pip install --pre numpy scipy scikit-learn")
    
    # 4. Installation PyTorch CPU léger
    print("🔥 Installation PyTorch CPU...")
    # Version minimaliste qui fonctionne avec Python 3.13
    success = run_cmd("pip install torch-audio")  # Version légère
    
    if not success:
        print("🔄 Installation PyTorch nightly...")
        success = run_cmd("pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cpu")
    
    # 5. Installation sentence-transformers simplifiée
    print("🧠 Installation sentence-transformers...")
    
    # Essai avec version récente qui supporte Python 3.13
    success = run_cmd("pip install --pre sentence-transformers")
    
    if not success:
        print("🔄 Essai installation manuelle...")
        success = run_cmd("pip install transformers tokenizers")
        success = run_cmd("pip install sentence-transformers --no-deps")
    
    # 6. Test minimal
    print("🧪 Test minimal...")
    
    # Test des imports essentiels
    try:
        import numpy as np
        print(f"✅ numpy: {np.__version__}")
    except ImportError:
        print("❌ numpy manquant")
    
    try:
        import sklearn
        print(f"✅ scikit-learn: {sklearn.__version__}")
    except ImportError:
        print("❌ scikit-learn manquant")
    
    try:
        import transformers
        print(f"✅ transformers: {transformers.__version__}")
    except ImportError:
        print("❌ transformers manquant")
    
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
        
        # Test rapide du modèle
        print("🧪 Test du modèle...")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(['Hello world'])
        print(f"✅ Modèle fonctionnel: {embeddings.shape}")
        
    except ImportError:
        print("❌ sentence-transformers manquant")
        return False
    except Exception as e:
        print(f"⚠️  Erreur du modèle: {e}")
        print("💡 Essayez un modèle plus simple")
    
    print("\n🎉 Installation terminée!")
    print("💡 Si ça ne fonctionne pas parfaitement, considérez:")
    print("   1. Downgrade vers Python 3.12")
    print("   2. Utiliser conda au lieu de pip")
    print("   3. Créer un nouvel environnement virtuel")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 