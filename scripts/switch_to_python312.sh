#!/bin/bash
# 🚀 SWITCH TO PYTHON 3.12
# Bascule vers Python 3.12 en réutilisant le cache pip (ultra-rapide !)

set -e

echo "🚀 SWITCH TO PYTHON 3.12"
echo "========================"

# 1. Arrêter tous les processus pip en boucle
echo "🛑 Arrêt des processus pip en boucle..."
pkill -f "pip install" 2>/dev/null || true
sleep 2

# 2. Vérifier Python 3.12
echo "🐍 Vérification Python 3.12..."
/usr/local/bin/python3.12 --version

# 3. Sauvegarder l'ancien environnement
echo "💾 Sauvegarde de l'ancien venv_semantic..."
if [ -d "venv_semantic" ]; then
    mv venv_semantic venv_semantic_python313_backup
    echo "✅ Ancien environnement sauvegardé vers venv_semantic_python313_backup"
fi

# 4. Créer le nouveau avec Python 3.12
echo "🏗️  Création nouveau venv_semantic avec Python 3.12..."
/usr/local/bin/python3.12 -m venv venv_semantic

# 5. Activer et installer (ultra-rapide avec cache)
echo "⚡ Installation ultra-rapide avec cache pip..."
source venv_semantic/bin/activate

echo "📦 Upgrade pip..."
pip install --upgrade pip setuptools wheel

echo "🔥 Installation PyTorch (avec cache)..."
pip install torch torchvision torchaudio

echo "🧠 Installation sentence-transformers (avec cache)..."
pip install sentence-transformers

echo "🔧 Installation transformers..."
pip install transformers tokenizers

echo "📚 Installation autres dépendances..."
pip install numpy scipy scikit-learn tqdm requests huggingface-hub

# 6. Test final
echo "🧪 Test des imports..."
python -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
python -c "import sentence_transformers; print(f'✅ sentence-transformers {sentence_transformers.__version__}')"
python -c "import transformers; print(f'✅ transformers {transformers.__version__}')"

echo ""
echo "🎉 SUCCÈS ! venv_semantic avec Python 3.12 est prêt !"
echo "💡 Votre app devrait maintenant fonctionner sans boucles"
echo "🔄 Pour l'utiliser: source venv_semantic/bin/activate" 