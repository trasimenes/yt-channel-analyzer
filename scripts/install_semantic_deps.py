#!/usr/bin/env python3
"""
Script d'installation des dépendances sémantiques
Gère les conflits de versions automatiquement
"""
import subprocess
import sys
import os

def run_command(cmd, description=""):
    """Exécute une commande et affiche le résultat"""
    print(f"🔄 {description or cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Erreur: {result.stderr}")
            return False
        else:
            print(f"✅ Succès: {description or cmd}")
            return True
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def install_semantic_dependencies():
    """Installe les dépendances sémantiques étape par étape"""
    
    print("🚀 Installation des dépendances sémantiques...")
    
    # 1. Mettre à jour pip
    if not run_command("python -m pip install --upgrade pip", "Mise à jour de pip"):
        return False
    
    # 2. Installer les dépendances de base d'abord
    base_deps = [
        "numpy>=1.24.0",
        "scipy>=1.11.0", 
        "scikit-learn>=1.3.0"
    ]
    
    for dep in base_deps:
        if not run_command(f"pip install '{dep}'", f"Installation de {dep}"):
            print(f"⚠️  Échec de {dep}, on continue...")
    
    # 3. Installer PyTorch (version CPU plus légère)
    print("\n🔄 Installation de PyTorch...")
    torch_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"
    if not run_command(torch_cmd, "Installation de PyTorch CPU"):
        # Fallback: version standard
        run_command("pip install torch>=2.0.0", "Installation PyTorch standard")
    
    # 4. Installer sentence-transformers
    print("\n🔄 Installation de sentence-transformers...")
    if not run_command("pip install sentence-transformers>=2.2.0", "Installation sentence-transformers"):
        print("❌ Échec de l'installation des transformers")
        return False
    
    # 5. Vérifier l'installation
    print("\n🔍 Vérification de l'installation...")
    try:
        import sentence_transformers
        import sklearn
        import torch
        print("✅ Toutes les dépendances sont installées correctement!")
        print(f"   - sentence-transformers: {sentence_transformers.__version__}")
        print(f"   - scikit-learn: {sklearn.__version__}")
        print(f"   - torch: {torch.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🤖 INSTALLATION SÉMANTIQUE POUR YT-CHANNEL-ANALYZER")
    print("=" * 60)
    
    # Vérifier qu'on est dans le bon répertoire
    if not os.path.exists("app.py"):
        print("❌ Erreur: Exécutez ce script depuis le répertoire racine du projet")
        sys.exit(1)
    
    success = install_semantic_dependencies()
    
    if success:
        print("\n🎉 Installation terminée avec succès!")
        print("💡 Vous pouvez maintenant utiliser:")
        print("   - python scripts/train_with_human_data.py")
        print("   - Les nouveaux classificateurs sémantiques")
    else:
        print("\n❌ L'installation a échoué.")
        print("💡 Solutions alternatives:")
        print("   1. Créer un nouvel environnement virtuel")
        print("   2. Utiliser pip install --force-reinstall")
        print("   3. Installer manuellement: pip install sentence-transformers")

if __name__ == "__main__":
    main() 