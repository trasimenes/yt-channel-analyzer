#!/bin/bash
# Script de vérification de sécurité avant commit

echo "🔍 Vérification de sécurité avant commit..."

# Vérifier que .env n'est pas en staging
if git diff --cached --name-only | grep -q "\.env"; then
    echo "❌ DANGER: fichier .env en staging !"
    echo "🚨 ANNULATION DU COMMIT"
    exit 1
fi

# Vérifier la présence de clés API dans les fichiers stagés
if git diff --cached | grep -i "AIzaSy"; then
    echo "❌ DANGER: Clé API détectée dans les fichiers à commiter !"
    echo "🚨 ANNULATION DU COMMIT"
    exit 1
fi

# Vérifier que .gitignore contient .env
if ! grep -q "^\.env$" .gitignore; then
    echo "❌ DANGER: .env manquant dans .gitignore !"
    exit 1
fi

echo "✅ Vérification de sécurité OK"
echo "🚀 Vous pouvez commiter en sécurité" 