# 🔬 YT Channel Analyzer - Development Branch

## 🧠 BRANCHE DÉVELOPPEMENT - AVEC MODÈLES ML

Cette branche contient **tous les modèles ML** et outils de développement pour l'analyse sémantique avancée.
**Taille**: ~5.5GB avec tous les modèles Sentence Transformers.

## 🚀 Vérification Rapide de l'Environnement

### ⚡ Commande Instantanée
```bash
./check_environment.sh
```

### 🔧 Alias Pratiques (optionnel)
```bash
source alias_setup.sh

# Puis utiliser :
ytenv          # Vérifier l'environnement
ytdev          # Basculer sur main (développement)  
ytprod         # Basculer sur production
ytstart        # Démarrer l'app
ytsync         # Synchroniser vers production
```

## 🎯 Applications Disponibles

### ✅ Fonctionnalités Complètes
- **Classification sémantique** : Sentence Transformers en temps réel
- **Entraînement de modèles** : Avec données humaines validées
- **Analyse émotionnelle** : Multilingue (FR, EN, DE, NL)
- **Interface complète** : Tous les outils d'analyse

### 🧠 Modèles ML Inclus
- `transformers_models/` : Modèles Sentence Transformers (400MB+)
- `venv_semantic/` : Environnement Python dédié (4GB+)
- **Total** : ~5.5GB de modèles et dépendances

### 🔬 Scripts de Développement
- `run_development.py` : Lanceur avec ML activé
- `requirements-semantic.txt` : Dépendances ML complètes
- `.env.development` : Configuration développement

## 🏗️ Architecture Dev vs Production

### 🔬 Développement (cette branche)
```
Repository/
├── transformers_models/     # 400MB de modèles
├── venv_semantic/          # 4GB environnement ML
├── run_development.py      # Script dev avec ML
├── requirements-semantic.txt
├── .env.development
└── [tous les autres fichiers]
```

### 🚀 Production (branche production)
```
Repository/
├── [PAS de transformers_models/]
├── [PAS de venv_semantic/]
├── passenger_wsgi.py       # Config production
├── .env.production
├── sync_to_production.sh   # Script de sync
└── README_PRODUCTION.md
```

## 🔄 Workflow de Développement

### 1. Développement Local
```bash
# Vérifier l'environnement
./check_environment.sh

# Lancer avec ML
python run_development.py
# ou si indisponible
python app.py
```

### 2. Test et Validation
```bash
# Tester les classifications
curl -X POST http://localhost:8082/api/test-classification \
  -H "Content-Type: application/json" \
  -d '{"text": "Découvrez nos nouvelles attractions aquatiques"}'

# Vérifier les modèles
ls -la transformers_models/
```

### 3. Synchronisation vers Production
```bash
# Basculer et synchroniser
git checkout production
./sync_to_production.sh
git push origin production
```

## 🛠️ Outils de Développement

### 📊 Pages d'Administration ML
- `/human-classifications` : Classifications validées manuellement
- `/classification-stats` : Statistiques de performance
- `/sentence-transformers` : État des modèles

### 🤖 API de Classification
- `POST /api/test-classification` : Test en temps réel
- `POST /api/train-model` : Réentraînement
- `POST /api/global-ai-classification` : Classification massive

### 📈 Métriques Avancées
- Classification Hero/Hub/Help automatique
- Analyse sémantique des titres/descriptions
- Détection automatique de contenu organique vs payé

## ⚙️ Configuration Environnement

### Variables d'Environnement (.env.development)
```bash
YTA_ENVIRONMENT=development
YTA_ENABLE_ML=true
YTA_DB_PATH=./instance/database.db
```

### Détection Automatique
Le système détecte automatiquement l'environnement et charge les modèles appropriés :
```python
from config import config
if config.should_load_ml_models():
    # Charge les modèles ML
else:
    # Mode production (affichage uniquement)
```

## 🚨 Dépannage

### Modèles ML Manquants
```bash
# Réinstaller l'environnement
pip install -r requirements-semantic.txt
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
```

### Erreur de Mémoire
```bash
# Réduire la taille des batches
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python run_development.py
```

### Basculer vers Production
```bash
git checkout production
# Les modèles ML ne seront plus accessibles
```

## 📊 Performances Attendues

- **Chargement initial** : 30-60s (téléchargement modèles)
- **Classification** : <1s par texte
- **Entraînement** : 2-5min pour 100 exemples
- **Mémoire** : 2-4GB RAM recommandés

---

🔬 **Cette branche permet le développement complet avec tous les outils ML disponibles.**