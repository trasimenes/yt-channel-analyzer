# 🌳 Workflow Git ML/Production - Guide Complet

## 🎯 **Principe Fondamental**
- **`main`** → Développement + ML (calcul + affichage)
- **`production`** → Production (affichage uniquement + fallback)
- **`shared`** → Features communes (UI, traductions, bug fixes)

## 📂 **Classification des Fichiers**

### 🔴 **EXCLUSIFS MAIN (ML Development)**
```
# Modèles & Training
yt_channel_analyzer/semantic_classifier.py
yt_channel_analyzer/enhanced_classifier.py
yt_channel_analyzer/lightweight_semantic.py
yt_channel_analyzer/supervised_learning.py
yt_channel_analyzer/transformers_manager.py
train_semantic_model.py
transformers_data/
transformers_models/

# Scripts ML
youtube_semantic_analyzer.py
analyze_all_topics.py
yt_channel_analyzer/topic_analyzer.py
yt_channel_analyzer/sentiment_pipeline/emotion_analyzer.py
run_emotion_pipeline.py

# Dependencies ML
requirements-semantic.txt
scripts/setup_semantic_classification.py
scripts/install_semantic_deps.py
```

### 🟢 **EXCLUSIFS PRODUCTION**
```
# Configuration Production
passenger_wsgi_production.py
.env.production
requirements.txt
blueprints/sentiment_production.py

# Système Fallback JSON
static/sentiment_analysis_production.json
static/sentiment_analysis_last_backup.json
export_sentiment_production.py
create_sentiment_backup.py
sentiment_analysis_fallback.py

# Logique d'affichage sans calcul
# Routes qui utilisent données pré-calculées uniquement
```

### 🟡 **COMMUNS (Safe pour les deux)**
```
# Interface & Templates
templates/
static/ (CSS, JS, images sauf JSON fallback)
build_theme.py

# Blueprints Core (avec protection ML)
blueprints/main.py
blueprints/auth.py
blueprints/competitors.py
blueprints/admin.py

# Base de données & Services
yt_channel_analyzer/database/
services/
instance/database.db

# Configuration avec protection
config.py
app.py
```

## 🔄 **Workflows par Scénario**

### 1. **Développement ML (main uniquement)**
```bash
git checkout main
# Travail sur semantic classifiers, training, etc.
git add yt_channel_analyzer/semantic_classifier.py
git commit -m "🧠 Améliorer classification sémantique Hero/Hub/Help"
git push origin main
```

### 2. **Features UI/Traductions (communes)**
```bash
# Créer branche shared
git checkout main
git checkout -b shared/ui-improvements
git add templates/ static/css/
git commit -m "🎨 Ajouter traductions FR/EN/DE dans l'interface"
git push origin shared/ui-improvements

# Merger vers main ET production
git checkout main
git merge shared/ui-improvements

git checkout production
git merge shared/ui-improvements

# Nettoyer
git branch -d shared/ui-improvements
git push origin --delete shared/ui-improvements
```

### 3. **Bug Fix Critique (propagation sélective)**
```bash
# Fix sur main
git checkout main
git add config.py
git commit -m "🐛 Fix connexion base de données"

# Cherry-pick vers production (seulement si non-ML)
git checkout production
git cherry-pick <commit-hash>
git push origin production
```

### 4. **Export Production (main → production)**
```bash
# Sur main : générer fallback JSON
git checkout main
python export_sentiment_production.py
git add static/sentiment_analysis_production.json
git commit -m "📊 Export données fallback pour production"

# Copier vers production
git checkout production
git checkout main -- static/sentiment_analysis_production.json
git commit -m "📊 Import données fallback depuis main"
git push origin production
```

### 5. **Sync Database (manuel)**
```bash
# Copier la vraie base main → production
scp instance/database.db production-server:/path/to/instance/
```

## 🛡️ **Protection Automatique**

### Git Hooks (à créer)
```bash
# .git/hooks/pre-commit
#!/bin/bash
branch=$(git branch --show-current)

if [[ "$branch" == "production" ]]; then
    # Interdire les fichiers ML en production
    if git diff --cached --name-only | grep -E "(semantic_classifier|transformers_manager|requirements-semantic)"; then
        echo "❌ ERREUR: Fichiers ML interdits en branche production"
        exit 1
    fi
fi
```

### Protection dans config.py
```python
# Vérification automatique de cohérence
def validate_branch_environment():
    branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
    
    if branch == 'production' and config.YTA_ENABLE_ML:
        raise EnvironmentError("❌ ML activé sur branche production !")
    
    if branch == 'main' and not config.YTA_ENABLE_ML:
        print("⚠️ Warning: ML désactivé sur branche main")
```

## 📋 **Checklist Deployment**

### Avant Push Production
- [ ] ✅ Variables d'environnement : `YTA_ENABLE_ML=false`
- [ ] ✅ Aucun import `sentence_transformers` dans le code
- [ ] ✅ Fallback JSON à jour dans `/static/`
- [ ] ✅ Base de données synchronisée
- [ ] ✅ Tests de l'interface sans ML

### Avant Push Main
- [ ] ✅ Modèles ML téléchargés dans `transformers_models/`
- [ ] ✅ Variables d'environnement : `YTA_ENABLE_ML=true`
- [ ] ✅ Tests de classification sémantique
- [ ] ✅ Export des nouvelles données vers production

## 🚀 **Commandes Rapides**

```bash
# Switcher en mode développement
git checkout main
cp .env.development .env
source venv_semantic/bin/activate
python app.py

# Switcher en mode production
git checkout production  
cp .env.production .env
python passenger_wsgi_production.py

# Synchroniser UI commune
git checkout shared/ui-sync
git merge main -- templates/ static/css/ static/js/
git checkout main && git merge shared/ui-sync
git checkout production && git merge shared/ui-sync

# Export données pour production
python export_sentiment_production.py
git add static/sentiment_analysis_production.json
git commit -m "📊 Export fallback data for production"
```

## ⚠️ **Règles Absolues**

1. **JAMAIS** de modèles ML sur `production`
2. **JAMAIS** de calculs lourds sur `production`
3. **TOUJOURS** tester les deux branches après merge
4. **OBLIGATOIRE** : Export fallback JSON après modification des données
5. **CRITIQUE** : Synchronisation manuelle de la base de données

Cette architecture garantit une séparation totale et une maintenance facile entre développement ML et production légère.