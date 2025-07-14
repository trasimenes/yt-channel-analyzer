#!/usr/bin/env python3
"""
🛑 STOP LOOPS AND INSTALL
Arrête les boucles d'installation et installe les versions exactes compatibles
"""

import os
import sys
import subprocess
import platform
import signal

def kill_pip_processes():
    """Tue tous les processus pip qui traînent"""
    print("🛑 Arrêt des processus pip en cours...")
    
    try:
        # Trouve et tue les processus pip
        result = subprocess.run(
            ["pkill", "-f", "pip install"],
            capture_output=True,
            text=True
        )
        print("✅ Processus pip arrêtés")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'arrêt des processus: {e}")

def get_python_version():
    """Détecte la version Python"""
    return f"{sys.version_info.major}.{sys.version_info.minor}"

def install_for_python_313():
    """Installation spécifique pour Python 3.13"""
    print("\n🔥 Installation pour Python 3.13 (expérimental)")
    
    commands = [
        "python -m pip install --upgrade pip setuptools wheel",
        "pip install numpy>=1.24.0,<2.0.0",
        "pip install scipy>=1.11.0,<1.15.0",
        "pip install scikit-learn>=1.3.0,<1.6.0",
        "pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu",
        "pip install sentence-transformers>=2.2.0,<3.0.0"
    ]
    
    for cmd in commands:
        print(f"🔄 {cmd}")
        try:
            result = subprocess.run(
                cmd.split(),
                timeout=300,
                check=False
            )
            if result.returncode == 0:
                print("✅ Succès")
            else:
                print(f"❌ Échec (code: {result.returncode})")
        except subprocess.TimeoutExpired:
            print("⏰ Timeout - on continue")
        except Exception as e:
            print(f"❌ Erreur: {e}")

def install_for_python_312():
    """Installation pour Python 3.12 (stable)"""
    print("\n✅ Installation pour Python 3.12 (stable)")
    
    commands = [
        "python -m pip install --upgrade pip setuptools wheel",
        "pip install numpy==1.24.3",
        "pip install scipy>=1.11.0,<1.15.0",
        "pip install scikit-learn==1.3.2",
        "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
        "pip install sentence-transformers==2.2.2"
    ]
    
    for cmd in commands:
        print(f"🔄 {cmd}")
        try:
            result = subprocess.run(
                cmd.split(),
                timeout=300,
                check=False
            )
            if result.returncode == 0:
                print("✅ Succès")
            else:
                print(f"❌ Échec (code: {result.returncode})")
        except subprocess.TimeoutExpired:
            print("⏰ Timeout - on continue")
        except Exception as e:
            print(f"❌ Erreur: {e}")

def test_installation():
    """Test rapide"""
    print("\n🧪 Test rapide...")
    
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
    except ImportError:
        print("❌ PyTorch non disponible")
        return False
    
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
    except ImportError:
        print("❌ sentence-transformers non disponible")
        return False
    
    return True

def main():
    print("🛑 STOP LOOPS AND INSTALL")
    print("=" * 50)
    
    # 1. Arrêter les processus en cours
    kill_pip_processes()
    
    # 2. Détecter Python
    python_version = get_python_version()
    print(f"🐍 Python détecté: {python_version}")
    
    # 3. Installation selon la version
    if python_version == "3.13":
        print("⚠️  Python 3.13 détecté - Installation expérimentale")
        install_for_python_313()
    elif python_version == "3.12":
        print("✅ Python 3.12 détecté - Installation stable")
        install_for_python_312()
    else:
        print(f"❌ Python {python_version} non supporté dans ce script rapide")
        print("💡 Utilisez: python scripts/smart_compatibility_installer.py")
        return False
    
    # 4. Test
    if test_installation():
        print("\n🎉 Installation terminée avec succès!")
        return True
    else:
        print("\n❌ Installation échouée")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Arrêté par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1) 