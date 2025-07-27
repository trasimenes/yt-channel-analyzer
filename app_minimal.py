"""
YT Channel Analyzer - Version minimale pour test
"""
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, session

# Création de l'application Flask
app = Flask(__name__)

# Configuration minimale
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['DEV_MODE'] = True
app.config['DEMO_MODE'] = False

# Variables globales
semantic_analysis_progress = {'status': 'idle'}
topic_analyzer = None

# Fonction simple de chargement de la clé API
def load_youtube_api_key():
    print("[STARTUP] ✅ Clé API YouTube (mode minimal)")
    return True

# Enregistrement minimal des blueprints
def register_blueprints():
    try:
        # Auth Blueprint seulement pour commencer
        from blueprints.auth import auth_bp
        app.register_blueprint(auth_bp)
        print("[STARTUP] ✅ Blueprint 'auth' enregistré")
        
        # Main Blueprint pour la page d'accueil
        from blueprints.main import main_bp
        app.register_blueprint(main_bp)
        print("[STARTUP] ✅ Blueprint 'main' enregistré")
        
        return True
    except Exception as e:
        print(f"[ERROR] Erreur blueprints: {e}")
        return False

# Route de test direct
@app.route('/test')
def test():
    return "Application fonctionne !"

# Gestionnaires d'erreurs
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# Context processor minimal
@app.context_processor
def inject_global_vars():
    return {
        'app_name': 'YT Channel Analyzer',
        'app_version': '2.0.0',
        'current_year': datetime.now().year,
        'dev_mode': True,
        'demo_mode': False
    }

# Point d'entrée
if __name__ == '__main__':
    print(f"[STARTUP] 🚀 Démarrage YT Channel Analyzer (Version Minimale)")
    
    load_youtube_api_key()
    
    if not register_blueprints():
        print("[FATAL] ❌ Impossible de charger les blueprints")
        exit(1)
    
    print(f"[STARTUP] 🎉 Application prête (mode minimal)")
    
    app.run(
        host='127.0.0.1',
        port=8082,
        debug=False,
        threaded=True
    )