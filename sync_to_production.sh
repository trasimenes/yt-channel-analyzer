#!/bin/bash

# 🚀 Script de synchronisation main → production
# Merge intelligemment les changements sans les fichiers ML

set -e

echo "🚀 SYNCHRONISATION MAIN → PRODUCTION"
echo "======================================"

# Vérifier qu'on est sur la branche production
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "production" ]; then
    echo "❌ Erreur: Vous devez être sur la branche 'production'"
    echo "   Exécutez: git checkout production"
    exit 1
fi

# Afficher le statut actuel
echo "📍 Branche actuelle: $CURRENT_BRANCH"
echo "🔍 Vérification des différences avec main..."

# Compter les commits en avance sur main
COMMITS_BEHIND=$(git rev-list --count HEAD..origin/main)
echo "📊 Commits en retard sur main: $COMMITS_BEHIND"

if [ "$COMMITS_BEHIND" -eq 0 ]; then
    echo "✅ La branche production est déjà à jour avec main"
    exit 0
fi

# Sauvegarder les fichiers critiques de production
echo "💾 Sauvegarde des fichiers critiques de production..."
cp passenger_wsgi.py passenger_wsgi.py.backup
cp .env.production .env.production.backup
cp .gitignore .gitignore.backup

# Merge main en excluant les fichiers ML
echo "🔄 Merge de main vers production..."
git fetch origin main

# Utiliser une stratégie de merge qui préserve les fichiers production
git merge origin/main --no-commit --no-ff

# Restaurer les fichiers critiques de production
echo "🔒 Restauration des fichiers critiques de production..."
git checkout HEAD -- passenger_wsgi.py || cp passenger_wsgi.py.backup passenger_wsgi.py
git checkout HEAD -- .env.production || cp .env.production.backup .env.production
git checkout HEAD -- .gitignore || cp .gitignore.backup .gitignore

# Supprimer les fichiers ML qui auraient pu être ajoutés
echo "🚫 Suppression des fichiers ML indésirables..."
rm -rf transformers_models/ 2>/dev/null || true
rm -rf venv_semantic/ 2>/dev/null || true
rm -rf ml_models/ 2>/dev/null || true
rm -rf notebooks/ 2>/dev/null || true
rm -f run_development.py 2>/dev/null || true
rm -f requirements-semantic.txt 2>/dev/null || true
rm -f .env.development 2>/dev/null || true

# Nettoyer les fichiers de sauvegarde
rm -f passenger_wsgi.py.backup .env.production.backup .gitignore.backup

# Vérifier qu'aucun fichier ML n'est ajouté au commit
ML_FILES=$(git diff --cached --name-only | grep -E "(transformers_models|venv_semantic|ml_models|notebooks|run_development.py|requirements-semantic.txt|\.env\.development)" || true)

if [ -n "$ML_FILES" ]; then
    echo "⚠️  Fichiers ML détectés dans le commit, suppression..."
    echo "$ML_FILES" | xargs git reset HEAD -- 2>/dev/null || true
    echo "$ML_FILES" | xargs rm -rf 2>/dev/null || true
fi

# Finaliser le commit de merge
echo "✅ Finalisation du merge..."
git commit -m "🚀 Sync from main to production (ML-free)

Merged latest changes from main branch while preserving:
- Production passenger_wsgi.py configuration
- ML models exclusion (.gitignore)
- Production environment settings

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Vérifications post-merge
echo ""
echo "🔍 VÉRIFICATIONS POST-MERGE"
echo "=========================="

# Vérifier la taille du dépôt
REPO_SIZE=$(du -sh . | cut -f1)
echo "📦 Taille du dépôt: $REPO_SIZE"

# Vérifier qu'aucun fichier ML n'est présent
echo "🚫 Vérification absence fichiers ML:"
[ ! -d "transformers_models" ] && echo "   ✅ transformers_models/ absent" || echo "   ❌ transformers_models/ présent!"
[ ! -d "venv_semantic" ] && echo "   ✅ venv_semantic/ absent" || echo "   ❌ venv_semantic/ présent!"
[ ! -f "run_development.py" ] && echo "   ✅ run_development.py absent" || echo "   ❌ run_development.py présent!"
[ ! -f "requirements-semantic.txt" ] && echo "   ✅ requirements-semantic.txt absent" || echo "   ❌ requirements-semantic.txt présent!"

# Vérifier que les fichiers critiques sont présents
echo "🔒 Vérification fichiers critiques production:"
[ -f "passenger_wsgi.py" ] && echo "   ✅ passenger_wsgi.py présent" || echo "   ❌ passenger_wsgi.py manquant!"
[ -f ".env.production" ] && echo "   ✅ .env.production présent" || echo "   ❌ .env.production manquant!"

# Compter les blueprints
BLUEPRINTS_COUNT=$(find blueprints/ -name "*.py" | grep -v __pycache__ | wc -l | tr -d ' ')
echo "📁 Blueprints détectés: $BLUEPRINTS_COUNT"

echo ""
echo "🎯 SYNCHRONISATION TERMINÉE!"
echo "==========================="
echo "📌 Prochaines étapes sur le serveur O2switch:"
echo "   1. git pull origin production"
echo "   2. touch tmp/restart.txt"
echo ""
echo "💡 La configuration passenger_wsgi.py existante a été préservée"