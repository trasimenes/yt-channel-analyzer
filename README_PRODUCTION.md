# 🚀 YT Channel Analyzer - Production Branch

## ⚠️ BRANCHE PRODUCTION - SANS MODÈLES ML

Cette branche est **strictement optimisée pour la production** sur serveur O2switch. 
**Aucun modèle ML** n'est présent pour éviter les problèmes de mémoire (400MB+ économisés).

## 🏗️ Architecture Production vs Développement

### 🚀 Production (cette branche)
- **Taille**: ~50MB (sans modèles ML)
- **Modèles ML**: DÉSACTIVÉS via `passenger_wsgi.py`
- **Affichage**: Classifications pré-calculées uniquement
- **Performance**: Chargement instantané
- **Sécurité**: Impossible de charger les modèles

### 🔬 Développement (branche main)
- **Taille**: ~450MB (avec modèles ML)
- **Modèles ML**: ACTIVÉS pour calculs locaux
- **Classification**: Sentence Transformers en temps réel
- **Entraînement**: Possible avec données humaines
- **Recherche**: Tous les outils d'analyse disponibles

## 📁 Fichiers Critiques Production

### ✅ Fichiers Présents
- `passenger_wsgi.py` - Configuration WSGI fonctionnelle (**NE PAS MODIFIER**)
- `.env.production` - Variables d'environnement production
- `.gitignore` - Exclusions ML renforcées
- `app.py` - Application Flask avec tous les blueprints
- `blueprints/` - Architecture modulaire complète
- `templates/` - Interface utilisateur traduite
- `static/` - Assets et thèmes Sneat

### 🚫 Fichiers Absents (Exclus)
- `transformers_models/` - Modèles Sentence Transformers (400MB+)
- `venv_semantic/` - Environnement virtuel ML
- `run_development.py` - Script de développement
- `requirements-semantic.txt` - Dépendances ML
- `.env.development` - Configuration développement
- `notebooks/` - Jupyter notebooks

## 🔧 Configuration Passenger WSGI

Le fichier `passenger_wsgi.py` actuel **fonctionne parfaitement** et contient :

```python
# Force l'environnement production et désactive ML
os.environ['YTA_ENVIRONMENT'] = 'production'
os.environ['YTA_ENABLE_ML'] = 'false'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['DISABLE_ML_MODELS'] = '1'
```

**⚠️ IMPORTANT**: Ne jamais modifier ce fichier, il est testé et fonctionnel.

## 🔄 Workflow de Synchronisation

### 1. Développement Local (branche main)
```bash
git checkout main
# ... développer avec tous les modèles ML ...
git add . && git commit -m "Nouvelles fonctionnalités"
git push origin main
```

### 2. Synchronisation vers Production
```bash
git checkout production
./sync_to_production.sh
git push origin production
```

### 3. Déploiement sur O2switch
```bash
cd /home/baptistegourgouillon/public_html/yt-analyzer
git pull origin production
touch tmp/restart.txt
```

## 🛡️ Protections Automatiques

### Script `sync_to_production.sh`
- ✅ Merge automatique main → production
- 🚫 Exclusion automatique des fichiers ML
- 🔒 Préservation du `passenger_wsgi.py` fonctionnel
- ✅ Vérifications post-merge automatiques

### `.gitignore` Renforcé
```
# PRODUCTION BRANCH - ML MODELS STRICTLY FORBIDDEN
transformers_models/
venv_semantic/
ml_models/
run_development.py
requirements-semantic.txt
.env.development
```

## 📊 Métriques Production

### Taille Optimisée
- **Avant**: ~450MB (avec ML)
- **Après**: ~50MB (sans ML)
- **Économie**: 400MB+ (89% de réduction)

### Performance
- **Chargement**: Instantané (0s vs 40s)
- **Mémoire**: Minimale (pas de PyTorch)
- **CPU**: Léger (pas de calculs ML)

## 🔍 Vérifications Automatiques

Le script de sync vérifie automatiquement :
- ❌ Absence de `transformers_models/`
- ❌ Absence de `venv_semantic/`
- ❌ Absence de `run_development.py`
- ✅ Présence de `passenger_wsgi.py`
- ✅ Présence de `.env.production`
- 📊 Comptage des blueprints

## 🚨 En Cas de Problème

### Restaurer passenger_wsgi.py
```bash
# Le script fait automatiquement une sauvegarde
cp passenger_wsgi.py.backup passenger_wsgi.py
```

### Nettoyer les fichiers ML
```bash
rm -rf transformers_models/ venv_semantic/ ml_models/
rm -f run_development.py requirements-semantic.txt .env.development
```

### Recréer la branche production
```bash
git branch -D production
git checkout main
git checkout -b production
# ... refaire la configuration ...
```

## 📞 Support

- **Architecture**: Conforme aux spécifications O2switch
- **Passenger**: Configuration testée et fonctionnelle
- **Performance**: Optimisée pour serveur partagé
- **Sécurité**: Modèles ML totalement isolés

---

🎯 **Cette branche garantit un déploiement production stable et performant sans aucun modèle ML.**