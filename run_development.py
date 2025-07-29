#!/usr/bin/env python3
"""
Script de démarrage pour l'environnement de développement
Charge les modèles ML et toutes les fonctionnalités
"""

import os
from dotenv import load_dotenv

# Charger la configuration de développement
load_dotenv('.env.development')

# S'assurer qu'on est en mode développement
os.environ['YTA_ENVIRONMENT'] = 'development'
os.environ['YTA_ENABLE_ML'] = 'true'

print("🚀 Démarrage en mode DÉVELOPPEMENT")
print("✅ Modèles ML activés")
print("✅ Toutes les fonctionnalités disponibles")

if __name__ == '__main__':
    from app import app
    app.run(debug=True, host='0.0.0.0', port=5000)