#!/usr/bin/env python3
"""
Script de vérification de sécurité pour YouTube Channel Analyzer
Vérifie qu'aucune information sensible n'est exposée avant upload sur Git
"""

import os
import re
import sys
from pathlib import Path

# Patterns de secrets à détecter
SECRET_PATTERNS = [
    (r'AIzaSy[A-Za-z0-9_-]{35}', 'Clé API Google/YouTube'),
    (r'sk_[A-Za-z0-9]{48}', 'Clé secrète Stripe'),
    (r'pk_[A-Za-z0-9]{50}', 'Clé publique Stripe'),
    (r'password\s*[=:]\s*["\'][^"\']{8,}["\']', 'Mot de passe hardcodé'),
    (r'secret\s*[=:]\s*["\'][^"\']{8,}["\']', 'Secret hardcodé'),
    (r'api_key\s*[=:]\s*["\'][^"\']{8,}["\']', 'Clé API hardcodée'),
    (r'token\s*[=:]\s*["\'][^"\']{16,}["\']', 'Token hardcodé'),
    (r'Palermo1990', 'Mot de passe spécifique détecté'),
    (r'baptiste.*password|password.*baptiste', 'Credentials spécifiques'),
]

# Extensions de fichiers à vérifier
EXTENSIONS_TO_CHECK = ['.py', '.js', '.json', '.md', '.txt', '.yml', '.yaml', '.env.example']

# Fichiers et dossiers à ignorer
IGNORE_PATTERNS = [
    '.git/',
    '__pycache__/',
    'node_modules/',
    '.env',  # Le vrai .env doit être ignoré par Git
    'venv/',
    'env/',
    '.vscode/',
    '.idea/',
]

def should_ignore_file(file_path):
    """Vérifie si un fichier doit être ignoré"""
    for pattern in IGNORE_PATTERNS:
        if pattern in str(file_path):
            return True
    return False

def check_file_for_secrets(file_path):
    """Vérifie un fichier pour des secrets potentiels"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        for line_num, line in enumerate(content.split('\n'), 1):
            for pattern, description in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'file': file_path,
                        'line': line_num,
                        'content': line.strip(),
                        'issue': description,
                        'pattern': pattern
                    })
    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture de {file_path}: {e}")
    
    return issues

def main():
    """Fonction principale"""
    print("🔒 Vérification de sécurité - YouTube Channel Analyzer")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    all_issues = []
    files_checked = 0
    
    # Parcourir tous les fichiers du projet
    for file_path in project_root.rglob('*'):
        if file_path.is_file() and not should_ignore_file(file_path):
            if file_path.suffix in EXTENSIONS_TO_CHECK:
                files_checked += 1
                issues = check_file_for_secrets(file_path)
                all_issues.extend(issues)
    
    print(f"📁 Fichiers vérifiés: {files_checked}")
    print()
    
    if all_issues:
        print("🚨 PROBLÈMES DE SÉCURITÉ DÉTECTÉS:")
        print("=" * 40)
        
        for issue in all_issues:
            print(f"📄 Fichier: {issue['file']}")
            print(f"📍 Ligne: {issue['line']}")
            print(f"⚠️  Problème: {issue['issue']}")
            print(f"📝 Contenu: {issue['content'][:100]}...")
            print("-" * 40)
        
        print(f"\n❌ TOTAL: {len(all_issues)} problème(s) détecté(s)")
        print("\n🔧 ACTIONS REQUISES:")
        print("1. Remplacez les secrets hardcodés par des variables d'environnement")
        print("2. Utilisez des exemples génériques dans les fichiers de documentation")
        print("3. Vérifiez que les vrais secrets sont dans .env (ignoré par Git)")
        
        return 1
    else:
        print("✅ AUCUN PROBLÈME DÉTECTÉ")
        print("🎉 Votre projet est sécurisé pour l'upload sur Git!")
        
        # Vérifications supplémentaires
        print("\n🔍 Vérifications supplémentaires:")
        
        # Vérifier que .env existe mais n'est pas versionné
        env_file = project_root / '.env'
        if env_file.exists():
            print("✅ Fichier .env trouvé localement")
        else:
            print("⚠️  Aucun fichier .env trouvé (normal si pas encore créé)")
        
        # Vérifier .gitignore
        gitignore_file = project_root / '.gitignore'
        if gitignore_file.exists():
            with open(gitignore_file, 'r') as f:
                gitignore_content = f.read()
                if '.env' in gitignore_content:
                    print("✅ .env est bien dans .gitignore")
                else:
                    print("❌ .env n'est PAS dans .gitignore - AJOUTEZ-LE!")
                    return 1
        
        print("\n🚀 Prêt pour git push!")
        return 0

if __name__ == "__main__":
    sys.exit(main())