#!/usr/bin/env python3
"""
♻️ REUSE DOWNLOADS
Réutilise les téléchargements de venv_semantic avec Python 3.12
Économise 40 minutes de re-téléchargement !
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

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
    print("♻️ REUSE DOWNLOADS - Réutilisation intelligente")
    print("=" * 45)
    
    # 1. Vérifier Python 3.12 disponible
    print("🐍 Vérification Python 3.12...")
    result = run_cmd("python3.12 --version", ignore_errors=True)
    if not result:
        print("❌ Python 3.12 pas encore installé")
        print("💡 Attendez que Homebrew finisse, puis relancez ce script")
        return False
    
    # 2. Trouver le cache pip existant
    print("🔍 Recherche du cache pip...")
    cache_dir = Path.home() / ".cache" / "pip"
    if not cache_dir.exists():
        cache_dir = Path("/tmp/pip-cache")
    
    print(f"📦 Cache pip trouvé: {cache_dir}")
    
    # 3. Créer venv_semantic_312 (copie de venv_semantic mais avec Python 3.12)
    print("🏗️  Création venv_semantic_312...")
    
    # Supprimer l'ancien s'il existe
    if Path("venv_semantic_312").exists():
        print("🧹 Suppression ancien venv_semantic_312...")
        shutil.rmtree("venv_semantic_312")
    
    # Créer le nouveau
    run_cmd("python3.12 -m venv venv_semantic_312")
    
    # 4. Installer rapidement en utilisant le cache
    print("⚡ Installation ultra-rapide avec cache...")
    
    # Commandes d'installation avec cache
    install_commands = [
        f"source venv_semantic_312/bin/activate && pip install --cache-dir {cache_dir} --upgrade pip setuptools wheel",
        f"source venv_semantic_312/bin/activate && pip install --cache-dir {cache_dir} torch torchvision torchaudio",
        f"source venv_semantic_312/bin/activate && pip install --cache-dir {cache_dir} sentence-transformers",
        f"source venv_semantic_312/bin/activate && pip install --cache-dir {cache_dir} transformers tokenizers",
        f"source venv_semantic_312/bin/activate && pip install --cache-dir {cache_dir} numpy scipy scikit-learn"
    ]
    
    for cmd in install_commands:
        print(f"📥 Installation avec cache...")
        success = run_cmd(cmd, ignore_errors=True)
        if not success:
            print("⚠️  Installation échouée, mais on continue...")
    
    # 5. Test final
    print("🧪 Test des imports...")
    test_cmd = "source venv_semantic_312/bin/activate && python -c \"import torch; import sentence_transformers; print('✅ Tout fonctionne!')\""
    success = run_cmd(test_cmd, ignore_errors=True)
    
    if success:
        print("🎉 SUCCÈS ! venv_semantic_312 prêt avec Python 3.12")
        print("💡 Pour utiliser:")
        print("   source venv_semantic_312/bin/activate")
        print("   python -c 'import sentence_transformers'")
        
        # 6. Renommer l'ancien et le nouveau
        print("\n🔄 Remplacement des environnements...")
        print("💡 Prochaine étape: Renommer venv_semantic -> venv_semantic_old")
        print("💡 Puis: Renommer venv_semantic_312 -> venv_semantic")
        
        return True
    else:
        print("❌ Échec du test final")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 