#!/usr/bin/env python3
"""
🧠 SMART COMPATIBILITY INSTALLER
Détecte automatiquement la configuration et installe les versions compatibles
Spécialement conçu pour Mac Intel 2015 avec Python 3.13
"""

import os
import sys
import subprocess
import platform
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class CompatibilityMatrix:
    """Matrice de compatibilité basée sur la recherche internet"""
    
    # Matrice de compatibilité pour Mac Intel 2015
    PYTHON_PYTORCH_MATRIX = {
        # Python 3.13 - Support expérimental uniquement
        "3.13": {
            "pytorch_index": "https://download.pytorch.org/whl/nightly/cpu",
            "pytorch_cmd": "pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu",
            "sentence_transformers": "sentence-transformers>=2.2.0,<3.0.0",
            "scikit_learn": "scikit-learn>=1.3.0,<1.6.0",
            "numpy": "numpy>=1.24.0,<2.0.0",
            "experimental": True,
            "stable": False
        },
        # Python 3.12 - Recommandé et stable
        "3.12": {
            "pytorch_index": "https://download.pytorch.org/whl/cpu",
            "pytorch_cmd": "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
            "sentence_transformers": "sentence-transformers==2.2.2",
            "scikit_learn": "scikit-learn==1.3.2",
            "numpy": "numpy==1.24.3",
            "experimental": False,
            "stable": True
        },
        # Python 3.11 - Très stable
        "3.11": {
            "pytorch_index": "https://download.pytorch.org/whl/cpu",
            "pytorch_cmd": "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
            "sentence_transformers": "sentence-transformers==2.2.2",
            "scikit_learn": "scikit-learn==1.3.2",
            "numpy": "numpy==1.24.3",
            "experimental": False,
            "stable": True
        },
        # Python 3.10 - Très stable
        "3.10": {
            "pytorch_index": "https://download.pytorch.org/whl/cpu",
            "pytorch_cmd": "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
            "sentence_transformers": "sentence-transformers==2.2.2",
            "scikit_learn": "scikit-learn==1.3.2",
            "numpy": "numpy==1.24.3",
            "experimental": False,
            "stable": True
        },
        # Python 3.9 - Très stable
        "3.9": {
            "pytorch_index": "https://download.pytorch.org/whl/cpu",
            "pytorch_cmd": "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
            "sentence_transformers": "sentence-transformers==2.2.2",
            "scikit_learn": "scikit-learn==1.3.2",
            "numpy": "numpy==1.24.3",
            "experimental": False,
            "stable": True
        }
    }

def get_system_info() -> Dict:
    """Détecte la configuration système"""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    system_info = {
        "python_version": python_version,
        "python_full_version": sys.version,
        "platform": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "mac_version": platform.mac_ver()[0] if platform.system() == "Darwin" else None,
        "is_mac_intel": platform.system() == "Darwin" and platform.machine() == "x86_64",
        "is_compatible": False,
        "recommendations": []
    }
    
    return system_info

def check_compatibility(system_info: Dict) -> Tuple[bool, Dict]:
    """Vérifie la compatibilité avec la matrice"""
    python_version = system_info["python_version"]
    
    if python_version not in CompatibilityMatrix.PYTHON_PYTORCH_MATRIX:
        return False, {
            "error": f"Python {python_version} n'est pas supporté",
            "supported_versions": list(CompatibilityMatrix.PYTHON_PYTORCH_MATRIX.keys())
        }
    
    config = CompatibilityMatrix.PYTHON_PYTORCH_MATRIX[python_version]
    
    # Vérifications spécifiques Mac Intel 2015
    if not system_info["is_mac_intel"]:
        return False, {
            "error": "Ce script est optimisé pour Mac Intel x86_64",
            "detected": f"{system_info['platform']} {system_info['machine']}"
        }
    
    return True, config

def run_command(cmd: str, description: str, timeout: int = 300) -> bool:
    """Exécute une commande avec timeout et gestion d'erreurs"""
    print(f"🔄 {description}")
    print(f"   Commande: {cmd}")
    
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - Succès")
            return True
        else:
            print(f"❌ {description} - Échec")
            print(f"   Erreur: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - Timeout après {timeout}s")
        return False
    except Exception as e:
        print(f"❌ {description} - Erreur: {e}")
        return False

def install_dependencies(config: Dict) -> bool:
    """Installe les dépendances avec la configuration exacte"""
    print("\n🚀 Installation des dépendances compatibles...")
    
    # 1. Mise à jour des outils de base
    if not run_command("python -m pip install --upgrade pip setuptools wheel", "Mise à jour pip", 120):
        print("⚠️  Échec de la mise à jour pip, on continue...")
    
    # 2. Installation des dépendances de base avec versions exactes
    base_deps = [
        config["numpy"],
        "scipy>=1.11.0,<1.15.0",
        config["scikit_learn"]
    ]
    
    for dep in base_deps:
        if not run_command(f"pip install '{dep}'", f"Installation de {dep}", 180):
            print(f"❌ Échec critique pour {dep}")
            return False
    
    # 3. Installation de PyTorch avec l'index spécifique
    print(f"\n🔥 Installation de PyTorch...")
    print(f"   Configuration: {config['pytorch_cmd']}")
    
    if config.get("experimental", False):
        print("⚠️  ATTENTION: Version expérimentale de PyTorch pour Python 3.13")
        user_input = input("Continuer? (o/N): ")
        if user_input.lower() != 'o':
            print("❌ Installation annulée par l'utilisateur")
            return False
    
    if not run_command(config["pytorch_cmd"], "Installation PyTorch", 300):
        print("❌ Échec critique pour PyTorch")
        return False
    
    # 4. Installation de sentence-transformers avec version exacte
    print(f"\n🧠 Installation de sentence-transformers...")
    sentence_cmd = f"pip install '{config['sentence_transformers']}'"
    if not run_command(sentence_cmd, "Installation sentence-transformers", 300):
        print("❌ Échec critique pour sentence-transformers")
        return False
    
    return True

def test_installation() -> bool:
    """Test l'installation"""
    print("\n🧪 Test de l'installation...")
    
    test_script = """
import sys
print(f"Python: {sys.version}")

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except ImportError as e:
    print(f"❌ PyTorch: {e}")
    sys.exit(1)

try:
    import sentence_transformers
    print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
except ImportError as e:
    print(f"❌ sentence-transformers: {e}")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print("✅ Import SentenceTransformer: OK")
except ImportError as e:
    print(f"❌ Import SentenceTransformer: {e}")
    sys.exit(1)

try:
    import sklearn
    print(f"✅ scikit-learn: {sklearn.__version__}")
except ImportError as e:
    print(f"❌ scikit-learn: {e}")
    sys.exit(1)

print("🎉 Tous les tests sont passés!")
"""
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def save_installation_report(system_info: Dict, config: Dict, success: bool):
    """Sauvegarde un rapport d'installation"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_info": system_info,
        "config_used": config,
        "installation_success": success,
        "script_version": "1.0.0"
    }
    
    report_file = f"installation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Rapport sauvegardé: {report_file}")
    except Exception as e:
        print(f"⚠️  Impossible de sauvegarder le rapport: {e}")

def main():
    """Point d'entrée principal"""
    print("=" * 80)
    print("🧠 SMART COMPATIBILITY INSTALLER")
    print("Matrice de compatibilité pour Mac Intel 2015")
    print("=" * 80)
    
    # 1. Détection du système
    print("\n🔍 Détection de la configuration système...")
    system_info = get_system_info()
    
    print(f"   Python: {system_info['python_version']} ({system_info['python_full_version'].split()[0]})")
    print(f"   Plateforme: {system_info['platform']} {system_info['machine']}")
    if system_info['mac_version']:
        print(f"   macOS: {system_info['mac_version']}")
    
    # 2. Vérification de la compatibilité
    print("\n🔍 Vérification de la compatibilité...")
    is_compatible, config = check_compatibility(system_info)
    
    if not is_compatible:
        print("❌ Configuration non compatible:")
        print(f"   {config.get('error', 'Erreur inconnue')}")
        if 'supported_versions' in config:
            print(f"   Versions Python supportées: {', '.join(config['supported_versions'])}")
        print("\n💡 Recommandations:")
        print("   1. Installer Python 3.12 (recommandé)")
        print("   2. Créer un nouvel environnement virtuel")
        print("   3. Relancer ce script")
        return False
    
    # 3. Affichage de la configuration
    print("✅ Configuration compatible détectée:")
    print(f"   Stable: {'✅' if config['stable'] else '❌'}")
    print(f"   Expérimental: {'⚠️' if config['experimental'] else '✅'}")
    print(f"   PyTorch: Version CPU avec index {config['pytorch_index']}")
    print(f"   sentence-transformers: {config['sentence_transformers']}")
    
    # 4. Confirmation utilisateur
    if config.get("experimental", False):
        print("\n⚠️  ATTENTION: Configuration expérimentale détectée")
        print("   Cette configuration peut être instable")
        print("   Recommandation: Utilisez Python 3.12 pour une stabilité maximale")
        
        user_input = input("\nContinuer avec cette configuration? (o/N): ")
        if user_input.lower() != 'o':
            print("❌ Installation annulée")
            return False
    
    # 5. Installation
    print("\n🚀 Début de l'installation...")
    success = install_dependencies(config)
    
    if not success:
        print("\n❌ Installation échouée")
        save_installation_report(system_info, config, False)
        return False
    
    # 6. Test de l'installation
    test_success = test_installation()
    
    # 7. Rapport final
    save_installation_report(system_info, config, test_success)
    
    if test_success:
        print("\n🎉 Installation terminée avec succès!")
        print("\n💡 Vous pouvez maintenant:")
        print("   - Utiliser sentence-transformers dans vos projets")
        print("   - Exécuter python scripts/train_with_human_data.py")
        print("   - Accéder au tableau de bord transformers")
        
        # Petit exemple
        print("\n🧪 Exemple rapide:")
        print("   from sentence_transformers import SentenceTransformer")
        print("   model = SentenceTransformer('all-MiniLM-L6-v2')")
        print("   embeddings = model.encode(['Hello world'])")
        
        return True
    else:
        print("\n❌ Installation terminée mais les tests ont échoué")
        print("💡 Vérifiez les logs ci-dessus pour plus de détails")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Installation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1) 