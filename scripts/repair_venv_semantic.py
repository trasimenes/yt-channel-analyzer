#!/usr/bin/env python3
"""
🔧 REPAIR VENV_SEMANTIC
Répare l'environnement venv_semantic existant avec Python 3.13
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
    print("🔧 REPAIR VENV_SEMANTIC - Python 3.13.2")
    print("=" * 40)
    
    # 1. Vérifier qu'on est dans venv_semantic
    if 'venv_semantic' not in os.environ.get('VIRTUAL_ENV', ''):
        print("❌ L'environnement venv_semantic n'est pas activé")
        print("💡 Activez-le avec: source venv_semantic/bin/activate")
        return False
    
    # 2. Arrêter les processus pip
    print("🛑 Arrêt des processus pip...")
    os.system("pkill -f 'pip install' 2>/dev/null || true")
    
    # 3. Nettoyer les packages problématiques
    print("🧹 Nettoyage packages corrompus...")
    run_cmd("pip uninstall -y sentence-transformers torch torchvision torchaudio", ignore_errors=True)
    
    # 4. Upgrade pip
    print("📦 Upgrade pip...")
    run_cmd("python -m pip install --upgrade pip setuptools wheel")
    
    # 5. Installer les dépendances qui marchent avec Python 3.13
    print("📚 Installation dépendances compatibles Python 3.13...")
    
    # Ces versions marchent avec Python 3.13
    compatible_packages = [
        "numpy>=1.26.0",
        "scipy>=1.11.0",  
        "scikit-learn>=1.4.0",
        "tqdm>=4.65.0",
        "requests>=2.31.0",
        "huggingface-hub>=0.19.0",
        "safetensors>=0.4.0",
        "tokenizers>=0.15.0"
    ]
    
    for package in compatible_packages:
        run_cmd(f"pip install '{package}'", ignore_errors=True)
    
    # 6. Essayer d'installer PyTorch (version nightly compatible Python 3.13)
    print("🔥 Tentative installation PyTorch nightly...")
    torch_success = run_cmd("pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu", ignore_errors=True)
    
    if not torch_success:
        print("⚠️  PyTorch nightly échec, essai version standard...")
        torch_success = run_cmd("pip install torch torchvision torchaudio", ignore_errors=True)
    
    # 7. Si PyTorch installé, installer sentence-transformers
    if torch_success:
        print("🧠 Installation sentence-transformers...")
        run_cmd("pip install sentence-transformers", ignore_errors=True)
    else:
        print("❌ PyTorch non installé, sentence-transformers sera skip")
    
    # 8. Test final
    print("🧪 Test des imports...")
    try:
        import transformers
        print(f"✅ transformers {transformers.__version__}")
        
        try:
            import torch
            print(f"✅ torch {torch.__version__}")
            
            try:
                import sentence_transformers
                print(f"✅ sentence-transformers {sentence_transformers.__version__}")
                print("🎉 SUCCÈS COMPLET !")
                return True
            except ImportError:
                print("⚠️  sentence-transformers manquant")
        except ImportError:
            print("⚠️  torch manquant")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    
    print("🔧 Environnement partiellement réparé")
    print("💡 Pour sentence-transformers, utilisez Python 3.12")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 