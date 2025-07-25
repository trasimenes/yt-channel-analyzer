"""
YT Channel Analyzer - Application Flask Modulaire
Architecture Blueprint pour remplacer le monolithe app.py de 10,122 lignes
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_session import Session
from flask_caching import Cache

# Charger les variables d'environnement
load_dotenv()

# Création de l'application Flask
app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['DEV_MODE'] = os.getenv('DEV_MODE', 'true').lower() == 'true'
app.config['DEMO_MODE'] = os.getenv('DEMO_MODE', 'false').lower() == 'true'

# Initialiser les extensions
Session(app)
cache = Cache(app)

# Variable globale pour le suivi de progression
semantic_analysis_progress = {'status': 'idle'}
topic_analyzer = None

# --- FILTRE JINJA2 ---
@app.template_filter('competitor_thumbnail')
def competitor_thumbnail_filter(competitor_id):
    """Filtre pour obtenir la miniature locale d'un concurrent"""
    try:
        from yt_channel_analyzer.utils.thumbnails import get_competitor_thumbnail
        return get_competitor_thumbnail(competitor_id)
    except ImportError:
        return f"/static/competitors/images/{competitor_id}.jpg"

@app.template_filter('format_number')
def format_number_filter(number, short=False):
    """Filtre pour formater les nombres"""
    from blueprints.utils import format_number
    return format_number(number, short)

@app.template_filter('format_duration')
def format_duration_filter(seconds):
    """Filtre pour formater les durées"""
    from blueprints.utils import format_duration
    return format_duration(seconds)

@app.template_filter('calculate_engagement')
def calculate_engagement_filter(views, likes, comments):
    """Filtre pour calculer l'engagement"""
    from blueprints.utils import calculate_engagement_rate
    return calculate_engagement_rate(views, likes, comments)

# --- CHARGEMENT DE LA CLE API ---
def load_youtube_api_key():
    """Charger la clé API YouTube depuis la base de données"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier si la table existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='app_config'
        """)
        
        if cursor.fetchone():
            cursor.execute("""
                SELECT value FROM app_config 
                WHERE key = 'youtube_api_key'
            """)
            result = cursor.fetchone()
            if result and result[0]:
                app.config['YOUTUBE_API_KEY'] = result[0]
                os.environ['YOUTUBE_API_KEY'] = result[0]
                print(f"[STARTUP] ✅ Clé API YouTube chargée depuis la base de données")
                conn.close()
                return True
        
        # Essayer depuis .env
        env_key = os.getenv('YOUTUBE_API_KEY')
        if env_key:
            app.config['YOUTUBE_API_KEY'] = env_key
            print(f"[STARTUP] ✅ Clé API YouTube chargée depuis .env")
            
            # Sauvegarder en base
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT OR REPLACE INTO app_config (key, value, updated_at)
                VALUES ('youtube_api_key', ?, datetime('now'))
            ''', (env_key,))
            conn.commit()
            print(f"[STARTUP] 💾 Clé API sauvegardée en base de données")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur lors du chargement de la clé API: {e}")
        return False

# --- REGISTRATION DES BLUEPRINTS ---
def register_blueprints():
    """Enregistrer tous les blueprints"""
    try:
        # Authentication Blueprint
        from blueprints.auth import auth_bp
        app.register_blueprint(auth_bp)
        print("[STARTUP] ✅ Blueprint 'auth' enregistré")
        
        # Main Blueprint  
        from blueprints.main import main_bp
        app.register_blueprint(main_bp)
        print("[STARTUP] ✅ Blueprint 'main' enregistré")
        
        # API Blueprint
        from blueprints.api import api_bp
        app.register_blueprint(api_bp)
        print("[STARTUP] ✅ Blueprint 'api' enregistré")
        
        # Competitors Blueprint
        from blueprints.competitors import competitors_bp
        app.register_blueprint(competitors_bp)
        print("[STARTUP] ✅ Blueprint 'competitors' enregistré")
        
        # Insights Blueprint
        from blueprints.insights import insights_bp
        app.register_blueprint(insights_bp)
        print("[STARTUP] ✅ Blueprint 'insights' enregistré")
        
        # Admin Blueprint
        from blueprints.admin import admin_bp
        app.register_blueprint(admin_bp)
        print("[STARTUP] ✅ Blueprint 'admin' enregistré")
        
        print(f"[STARTUP] 🎯 {len(app.blueprints)} blueprints enregistrés avec succès")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Erreur d'import des blueprints: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'enregistrement des blueprints: {e}")
        return False

# --- GESTIONNAIRES D'ERREURS ---
@app.errorhandler(404)
def page_not_found(e):
    """Page d'erreur 404"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Page d'erreur 500"""
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    """Page d'erreur 403"""
    return render_template('errors/403.html'), 403

# --- CONTEXT PROCESSORS ---
@app.context_processor
def inject_global_vars():
    """Injecter des variables globales dans tous les templates"""
    return {
        'app_name': 'YT Channel Analyzer',
        'app_version': '2.0.0',
        'current_year': datetime.now().year,
        'dev_mode': app.config.get('DEV_MODE', False),
        'demo_mode': app.config.get('DEMO_MODE', False)
    }

# --- ROUTES LEGACY (COMPATIBILITE) ---
@app.route('/api/competitor-refresh-data')
def api_competitor_refresh_data():
    """Route de compatibilité pour le refresh des données"""
    from flask import redirect, url_for
    return redirect(url_for('api.performance_metrics'))

@app.route('/supervised-learning')
def supervised_learning_legacy():
    """Route de compatibilité pour supervised learning"""
    from blueprints.auth import login_required
    from flask import redirect, url_for
    
    @login_required
    def redirect_to_admin():
        return redirect(url_for('admin.settings'))
    
    return redirect_to_admin()

# --- INITIALISATION ---
def create_app():
    """Factory function pour créer l'application"""
    print(f"[STARTUP] 🚀 Initialisation de YT Channel Analyzer v2.0.0")
    print(f"[STARTUP] 📁 Mode debug: {app.debug}")
    print(f"[STARTUP] 🔧 Mode dev: {app.config.get('DEV_MODE', False)}")
    
    # Charger la clé API
    load_youtube_api_key()
    
    # Enregistrer les blueprints
    if not register_blueprints():
        print("[ERROR] ❌ Échec de l'enregistrement des blueprints")
        return None
    
    # Initialiser la base de données si nécessaire
    try:
        from yt_channel_analyzer.database import init_db
        init_db()
        print("[STARTUP] ✅ Base de données initialisée")
    except Exception as e:
        print(f"[WARNING] Erreur d'initialisation DB: {e}")
    
    print(f"[STARTUP] 🎉 Application prête avec {len(app.url_map.iter_rules())} routes")
    return app

# --- POINT D'ENTREE ---
if __name__ == '__main__':
    # Créer l'application
    app = create_app()
    
    if app is None:
        print("[FATAL] ❌ Impossible de démarrer l'application")
        exit(1)
    
    # Configuration de démarrage
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', 8082))
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    
    print(f"[STARTUP] 🌐 Démarrage sur http://{host}:{port}")
    print(f"[STARTUP] 🔄 Mode debug: {debug_mode}")
    print(f"[STARTUP] 📊 Architecture: 6 blueprints modulaires")
    print(f"[STARTUP] 🎯 Fini les 10,122 lignes monolithiques !")
    
    # Démarrer le server
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        threaded=True
    )