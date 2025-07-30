"""
BACKUP PRODUCTION PASSENGER WSGI - 30.07.2025
Configuration sanctuarisée qui FONCTIONNE en production cPanel/Passenger
⚠️ NE PAS MODIFIER - Cette configuration est la SEULE qui marche
"""
import sys
import os

# Configuration du path
sys.path.insert(0, os.path.dirname(__file__))

# Forcer l'environnement production et désactiver les modèles ML
os.environ['YTA_ENVIRONMENT'] = 'production'
os.environ['YTA_ENABLE_ML'] = 'false'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['DISABLE_ML_MODELS'] = '1'

from dotenv import load_dotenv
# Charger le fichier .env.production
load_dotenv(os.path.join(os.path.dirname(__file__), '.env.production'))

from app import app

# Configuration complète des sessions
app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'your-flask-secret-key-unique-change-me-2025'),
    SESSION_COOKIE_NAME='ytanalyzer_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # True si vous avez HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,
    SESSION_TYPE='filesystem',
    PERMANENT_SESSION=True
)

# Importer et enregistrer TOUS les blueprints
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.competitors import competitors_bp
from blueprints.admin import admin_bp
from blueprints.api import api_bp
from blueprints.insights import insights_bp
from yt_channel_analyzer.sentiment_pipeline.emotion_api import emotion_api
from yt_channel_analyzer.sentiment_pipeline.batch_api import batch_api

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(competitors_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(emotion_api)
app.register_blueprint(batch_api)

# Gestionnaire d'erreur simple pour debug
@app.errorhandler(500)
def internal_error(error):
    return """
    <h1>Erreur 500</h1>
    <p>Une erreur s'est produite. Vérifiez les logs.</p>
    <a href="/login">Retour au login</a>
    """, 500

# IMPORTANT pour Passenger
application = app.wsgi_app