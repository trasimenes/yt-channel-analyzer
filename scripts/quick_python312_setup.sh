#!/bin/bash
# 🚀 QUICK PYTHON 3.12 SETUP
# Downgrade rapide vers Python 3.12 pour déverrouiller l'écosystème ML

set -e  # Arrêt sur erreur

echo "🚀 QUICK PYTHON 3.12 SETUP"
echo "=========================="

# 1. Arrêter les processus pip en cours
echo "🛑 Arrêt des processus pip..."
pkill -f "pip install" 2>/dev/null || true

# 2. Installer pyenv via Homebrew
echo "📦 Installation pyenv..."
brew install pyenv || echo "⚠️  pyenv déjà installé"

# 3. Configurer pyenv dans zshrc
echo "⚙️  Configuration pyenv..."
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc || true
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc || true
echo 'eval "$(pyenv init -)"' >> ~/.zshrc || true

# 4. Charger pyenv dans la session courante
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# 5. Installer Python 3.12.3
echo "🐍 Installation Python 3.12.3..."
pyenv install 3.12.3 || echo "⚠️  Python 3.12.3 déjà installé"

# 6. Créer l'environnement virtuel
echo "🏗️  Création environnement torch-env..."
pyenv virtualenv 3.12.3 torch-env || echo "⚠️  torch-env déjà créé"

# 7. Activer l'environnement et installer les dépendances
echo "🔥 Activation environnement torch-env..."
eval "$(pyenv init -)"
pyenv activate torch-env

echo "📦 Installation des dépendances ML..."
pip install --upgrade pip setuptools wheel
pip install torch torchvision torchaudio
pip install sentence-transformers

echo "🧪 Test des imports..."
python -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
python -c "import sentence_transformers; print(f'✅ sentence-transformers {sentence_transformers.__version__}')"

echo ""
echo "🎉 SUCCÈS ! Python 3.12 avec ML stack installé"
echo "💡 Pour utiliser cet environnement :"
echo "   pyenv activate torch-env"
echo "   python -c 'import torch; import sentence_transformers'" 