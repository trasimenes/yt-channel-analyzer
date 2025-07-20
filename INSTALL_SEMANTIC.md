# 🤖 Installation des Dépendances Sémantiques

## Problème
Les versions strictes dans `requirements.txt` causent des conflits avec `sentence-transformers`.

## Solutions (par ordre de préférence)

### 🎯 Solution 1: Script automatique (RECOMMANDÉ)
```bash
python scripts/install_semantic_deps.py
```

### 🔧 Solution 2: Installation manuelle progressive
```bash
# 1. Mettre à jour pip
python -m pip install --upgrade pip

# 2. Installer les dépendances de base
pip install numpy scipy scikit-learn --upgrade

# 3. Installer PyTorch (version CPU, plus légère)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 4. Installer sentence-transformers
pip install sentence-transformers

# 5. Vérifier
python -c "import sentence_transformers; print('✅ OK')"
```

### 🆕 Solution 3: Nouvel environnement virtuel
```bash
# Créer un nouvel environnement
python -m venv venv_semantic
source venv_semantic/bin/activate  # macOS/Linux
# ou venv_semantic\Scripts\activate  # Windows

# Installer avec requirements flexibles
pip install -r requirements-semantic.txt
```

### ⚡ Solution 4: Installation forcée
```bash
# Forcer la réinstallation
pip install --force-reinstall --no-deps sentence-transformers
pip install --force-reinstall torch scikit-learn
```

## Test de l'Installation
```bash
python -c "
import sentence_transformers
from sklearn.metrics.pairwise import cosine_similarity
import torch
print('✅ Toutes les dépendances sont installées!')
"
```

## Si Ça Ne Marche Toujours Pas

### Option A: Versions minimales
```bash
pip install sentence-transformers==2.2.0 scikit-learn==1.3.0
```

### Option B: Ignorer les conflits
```bash
pip install sentence-transformers --no-deps
pip install transformers torch tokenizers
```

### Option C: Utiliser conda
```bash
conda install pytorch torchvision torchaudio cpuonly -c pytorch
conda install -c conda-forge sentence-transformers
```

## Après Installation
Une fois installé, vous pouvez:
1. Exécuter `python scripts/train_with_human_data.py`
2. Utiliser les nouveaux classificateurs sémantiques
3. Bénéficier de la compréhension sémantique vraie vs keyword matching

## Dépendances Installées
- `sentence-transformers` : Classification sémantique
- `torch` : Modèles de deep learning
- `scikit-learn` : Algorithmes ML
- `transformers` : Modèles de transformers (auto-installé)
- `tokenizers` : Tokenisation (auto-installé) 