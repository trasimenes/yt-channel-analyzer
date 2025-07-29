import sys
import os
import traceback
import logging

# Configuration du path
sys.path.insert(0, os.path.dirname(__file__))

# FORCER L'ENVIRONNEMENT PRODUCTION AVANT TOUT IMPORT
os.environ['YTA_ENVIRONMENT'] = 'production'
os.environ['YTA_ENABLE_ML'] = 'false'

# DÉSACTIVER LES MODÈLES SÉMANTIQUES AVANT TOUT IMPORT
sys.modules['sentence_transformers'] = None
sys.modules['transformers'] = None
sys.modules['torch'] = None

# Variables d'environnement pour désactiver les téléchargements
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

# Charger les variables d'environnement de production
from dotenv import load_dotenv
load_dotenv('.env.production')

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    # Import de l'application
    from app import create_app
    
    # Créer l'application Flask
    application = create_app()
    
    # Enregistrer les blueprints manuellement car ils ne sont pas registrés dans create_app
    from blueprints.auth import auth_bp
    from blueprints.competitors import competitors_bp
    from blueprints.api import api_bp  
    from blueprints.insights import insights_bp
    
    # Enregistrer les blueprints avec l'application
    application.register_blueprint(auth_bp)
    application.register_blueprint(competitors_bp, url_prefix='/competitor')
    application.register_blueprint(api_bp, url_prefix='/api')
    application.register_blueprint(insights_bp, url_prefix='/insights')
    
    print("✅ Application Flask initialisée en mode PRODUCTION (ML désactivé)")
    print(f"✅ Blueprints enregistrés: auth, competitors, api, insights")
    
except Exception as e:
    print(f"❌ Erreur lors du chargement de l'application: {e}")
    print(f"❌ Traceback: {traceback.format_exc()}")
    
    # Application de fallback en cas d'erreur
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"Erreur de chargement: {str(e)}"