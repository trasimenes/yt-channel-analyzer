#!/usr/bin/env python3
"""
Script de vérification finale de sécurité
Vérifie qu'aucune clé API n'est exposée dans le projet
"""

import os
import re
import sys
from pathlib import Path

# Patterns de clés API sensibles
API_KEY_PATTERNS = [
    r'AIza[0-9A-Za-z_-]{35}',  # Google API Keys
    r'ya29\.[0-9A-Za-z_-]+',  # Google OAuth tokens
    r'[0-9]+-[0-9A-Za-z_-]{32}\.apps\.googleusercontent\.com',  # Google Client IDs
    r'sk-[a-zA-Z0-9]{48}',  # OpenAI API Keys
    r'xoxb-[0-9]+-[0-9]+-[0-9A-Za-z]+',  # Slack Bot tokens
]

# Patterns de mots de passe/secrets en dur
SECRET_PATTERNS = [
    r'password\s*=\s*["\'][^"\']{8,}["\']',
    r'secret\s*=\s*["\'][^"\']{16,}["\']',
    r'token\s*=\s*["\'][^"\']{20,}["\']',
]

# Fichiers à ignorer
IGNORE_PATTERNS = [
    r'DO_NOT_UPLOAD_INTERNAL/',
    r'node_modules/',
    r'\.git/',
    r'__pycache__/',
    r'\.pyc$',
    r'\.log$',
    r'\.env_ORIGINAL_AVEC_CLES_API$',
]

def should_ignore_file(file_path):
    """Vérifie si un fichier doit être ignoré"""
    file_str = str(file_path)
    return any(re.search(pattern, file_str) for pattern in IGNORE_PATTERNS)

def scan_file_for_secrets(file_path):
    """Scanne un fichier pour des secrets"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        issues = []
        
        # Vérifier les clés API
        for pattern in API_KEY_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'API_KEY',
                    'pattern': pattern,
                    'match': match.group(),
                    'line': line_num,
                    'file': str(file_path)
                })
        
        # Vérifier les secrets en dur (sauf dans les templates)
        if not str(file_path).endswith('.example') and not 'template' in str(file_path).lower():
            for pattern in SECRET_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Ignorer les placeholders
                    if any(placeholder in match.group().lower() for placeholder in 
                           ['your_', 'change_me', 'here', 'example', 'placeholder']):
                        continue
                    
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': 'SECRET',
                        'pattern': pattern,
                        'match': match.group(),
                        'line': line_num,
                        'file': str(file_path)
                    })
        
        return issues
    
    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture de {file_path}: {e}")
        return []

def main():
    """Fonction principale"""
    print("🔍 Vérification finale de sécurité...")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    all_issues = []
    
    # Scanner tous les fichiers
    for file_path in project_root.rglob('*'):
        if file_path.is_file() and not should_ignore_file(file_path):
            issues = scan_file_for_secrets(file_path)
            all_issues.extend(issues)
    
    # Afficher les résultats
    if all_issues:
        print("🚨 PROBLÈMES DE SÉCURITÉ DÉTECTÉS:")
        print("-" * 40)
        
        for issue in all_issues:
            print(f"❌ {issue['type']}: {issue['file']}:{issue['line']}")
            print(f"   Pattern: {issue['pattern']}")
            print(f"   Match: {issue['match'][:50]}...")
            print()
        
        print(f"Total: {len(all_issues)} problème(s) détecté(s)")
        return 1
    
    else:
        print("✅ AUCUN PROBLÈME DE SÉCURITÉ DÉTECTÉ")
        print()
        print("Vérifications effectuées:")
        print("- ✅ Clés API Google/YouTube")
        print("- ✅ Tokens OAuth")
        print("- ✅ Clés OpenAI")
        print("- ✅ Tokens Slack")
        print("- ✅ Mots de passe en dur")
        print("- ✅ Secrets en dur")
        print()
        print("🛡️  Le projet est sécurisé pour l'upload!")
        return 0

if __name__ == "__main__":
    sys.exit(main())