"""
YT Channel Analyzer - Modular Flask Application
Blueprint architecture to replace the 10,122 line monolithic app.py
"""
import os
from datetime import datetime
from functools import wraps
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv non installé, utilisation des variables d'environnement système")

from flask import Flask, render_template
from blueprints.auth import login_required
try:
    from flask_session import Session
except ImportError:
    print("[WARNING] flask-session non installé, sessions en mémoire")
    Session = None

try:
    from flask_caching import Cache
except ImportError:
    print("[WARNING] flask-caching non installé, pas de cache")
    Cache = None

# Création de l'application Flask
app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['DEV_MODE'] = os.getenv('DEV_MODE', 'true').lower() == 'true'
app.config['DEMO_MODE'] = os.getenv('DEMO_MODE', 'false').lower() == 'true'

# Initialiser les extensions conditionnellement
if Session:
    Session(app)
if Cache:
    cache = Cache(app)
else:
    cache = None

# Variable globale pour le suivi de progression
semantic_analysis_progress = {'status': 'idle'}
topic_analyzer = None

# --- CONTEXT PROCESSORS ---
@app.context_processor
def inject_dev_mode():
    """Injecte le mode développeur dans tous les templates"""
    try:
        from flask import session
        # Initialiser dev_mode s'il n'existe pas
        if 'dev_mode' not in session:
            session['dev_mode'] = app.config.get('DEV_MODE', True)
            print(f"[CONTEXT] Initializing dev_mode to: {session['dev_mode']}")
        
        dev_mode_value = session.get('dev_mode', True)
        from yt_channel_analyzer.auth import is_authenticated
        is_auth = is_authenticated(session)
        
        print(f"[CONTEXT] dev_mode: {dev_mode_value}, is_authenticated: {is_auth}, session_keys: {list(session.keys())}")
        
        return dict(
            dev_mode=dev_mode_value,
            is_authenticated=is_auth
        )
    except Exception as e:
        print(f"[CONTEXT] Erreur inject_dev_mode: {e}")
        import traceback
        traceback.print_exc()
        return dict(
            dev_mode=True,
            is_authenticated=False
        )

# --- DECORATORS ---
def dev_mode_required(f):
    """Decorator to limit access to dev mode functions only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, flash, redirect, url_for
        if not session.get('dev_mode', app.config.get('DEV_MODE', True)):
            flash('This feature is only available in developer mode', 'warning')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# --- FILTRE JINJA2 ---
@app.template_filter('competitor_thumbnail')
def competitor_thumbnail_filter(competitor_id):
    """Filter to get local competitor thumbnail"""
    try:
        from yt_channel_analyzer.utils.thumbnails import get_competitor_thumbnail
        return get_competitor_thumbnail(competitor_id)
    except ImportError:
        return f"/static/competitors/images/{competitor_id}.jpg"

@app.template_filter('format_number')
def format_number_filter(number, short=False):
    """Filter to format numbers"""
    from blueprints.utils import format_number
    return format_number(number, short)

@app.template_filter('format_duration')
def format_duration_filter(seconds):
    """Filter to format durations"""
    from blueprints.utils import format_duration
    return format_duration(seconds)

@app.template_filter('calculate_engagement')
def calculate_engagement_filter(views, likes, comments):
    """Filter to calculate engagement"""
    from blueprints.utils import calculate_engagement_rate
    return calculate_engagement_rate(views, likes, comments)

# --- CHARGEMENT DE LA CLE API ---
def load_youtube_api_key():
    """Load YouTube API key from database"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if table exists
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
                print(f"[STARTUP] ✅ YouTube API key loaded from database")
                conn.close()
                return True
        
        # Try from .env
        env_key = os.getenv('YOUTUBE_API_KEY')
        if env_key:
            app.config['YOUTUBE_API_KEY'] = env_key
            print(f"[STARTUP] ✅ YouTube API key loaded from .env")
            
            # Save to database
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
            print(f"[STARTUP] 💾 API key saved to database")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error loading API key: {e}")
        return False

# --- REGISTRATION DES BLUEPRINTS ---
def register_blueprints():
    """Register all blueprints"""
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
        
        # AI Learning Blueprint (dev/prod dual mode)
        from blueprints.ai_learning import ai_learning_bp
        app.register_blueprint(ai_learning_bp)
        print("[STARTUP] ✅ Blueprint 'ai_learning' enregistré")
        
        # Blueprint pour l'API d'analyse émotionnelle
        from yt_channel_analyzer.sentiment_pipeline.emotion_api import emotion_api
        app.register_blueprint(emotion_api)
        print("[STARTUP] ✅ Blueprint 'emotion_api' enregistré")
        
        # Blueprint pour l'API de traitement par batch
        from yt_channel_analyzer.sentiment_pipeline.batch_api import batch_api
        app.register_blueprint(batch_api)
        print("[STARTUP] ✅ Blueprint 'batch_api' enregistré")
        
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

# Route /frequency-dashboard supprimée - maintenant gérée par insights_bp

@app.route('/api-usage-page')
def api_usage_page_legacy():
    """Route de compatibilité pour api usage"""
    from flask import redirect, url_for
    return redirect(url_for('admin.api_usage'))

@app.route('/api-usage')
def api_usage_legacy():
    """Route de compatibilité pour api usage (route principale)"""
    from flask import redirect, url_for
    return redirect(url_for('admin.api_usage'))

@app.route('/business')
def business_legacy():
    """Route de compatibilité pour business settings"""
    from flask import redirect, url_for
    return redirect(url_for('admin.settings'))

# /data route removed as requested

# Route /learn maintenant gérée par insights_bp

# Route countries-analysis avec vraies données
@app.route('/countries-analysis')
@login_required
def countries_analysis():
    """Analyse comparative par pays avec vraies données et insights exploitables"""
    print("[DEBUG] ✅ Route countries_analysis avec vraies données appelée !")
    
    try:
        from yt_channel_analyzer.database import get_db_connection
        import sqlite3
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # D'abord récupérer les statistiques globales réelles
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        total_competitors_real = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos_real = cursor.fetchone()[0]
        
        print(f"[DEBUG] Statistiques réelles: {total_competitors_real} compétiteurs, {total_videos_real} vidéos")
        
        # Nettoyer d'abord les pays vides
        cursor.execute("""
            UPDATE concurrent 
            SET country = 'International' 
            WHERE country IS NULL OR country = '' OR TRIM(country) = ''
        """)
        conn.commit()
        
        # Requête optimisée pour récupérer toutes les métriques par pays
        cursor.execute("""
            SELECT 
                COALESCE(NULLIF(TRIM(c.country), ''), 'International') as country,
                COUNT(DISTINCT c.id) as competitor_count,
                COUNT(DISTINCT v.id) as video_count,
                COALESCE(AVG(v.view_count), 0) as avg_views_per_video,
                COALESCE(AVG(CAST(v.like_count AS FLOAT) / NULLIF(v.view_count, 0) * 100), 0) as avg_engagement_rate,
                MAX(v.view_count) as max_views,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(AVG(v.duration_seconds), 0) as avg_duration,
                -- Distribution par catégorie
                SUM(CASE WHEN LOWER(v.category) = 'hero' THEN 1 ELSE 0 END) as hero_count,
                SUM(CASE WHEN LOWER(v.category) = 'hub' THEN 1 ELSE 0 END) as hub_count,
                SUM(CASE WHEN LOWER(v.category) = 'help' THEN 1 ELSE 0 END) as help_count,
                -- Top performer
                (SELECT cc.name FROM concurrent cc 
                 JOIN video vv ON cc.id = vv.concurrent_id 
                 WHERE COALESCE(NULLIF(TRIM(cc.country), ''), 'International') = COALESCE(NULLIF(TRIM(c.country), ''), 'International')
                 ORDER BY vv.view_count DESC 
                 LIMIT 1) as top_performer,
                -- Opportunity Score (basé sur le potentiel vs performance actuelle)
                CASE 
                    WHEN COUNT(DISTINCT v.id) = 0 THEN 100  -- Pas de contenu = opportunité max
                    WHEN AVG(v.view_count) < 10000 AND COUNT(DISTINCT v.id) < 100 THEN 80
                    WHEN AVG(v.view_count) < 50000 AND COUNT(DISTINCT v.id) < 200 THEN 60
                    WHEN AVG(v.view_count) < 100000 THEN 40
                    ELSE 20
                END as opportunity_score
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY COALESCE(NULLIF(TRIM(c.country), ''), 'International')
            ORDER BY total_views DESC
        """)
        
        countries_data = []
        all_rows = cursor.fetchall()
        
        # Calculer la moyenne globale pour le growth trend
        avg_performance = sum(row[3] for row in all_rows) / len(all_rows) if all_rows else 0
        
        for row in all_rows:
            total_videos = row[8] + row[9] + row[10]
            
            # Calculer les métriques stratégiques avancées
            videos_per_competitor = row[2] / row[1] if row[1] > 0 else 0
            
            # Growth trend basé sur la performance vs moyenne
            growth_trend = "↗️" if row[3] > avg_performance * 1.2 else "↘️" if row[3] < avg_performance * 0.8 else "→"
            
            # Competitive intensity basé sur le nombre de concurrents et vidéos par concurrent
            if videos_per_competitor > 300:
                competitive_intensity = "Élevé"
                intensity_class = "danger"
            elif videos_per_competitor > 150:
                competitive_intensity = "Moyen"
                intensity_class = "warning"
            else:
                competitive_intensity = "Faible"
                intensity_class = "success"
            
            # Content gaps (par rapport au leader International)
            international_hero = 50  # Valeur de référence International
            international_hub = 30
            international_help = 20
            
            hero_pct = (row[8] / total_videos * 100) if total_videos > 0 else 0
            hub_pct = (row[9] / total_videos * 100) if total_videos > 0 else 0
            help_pct = (row[10] / total_videos * 100) if total_videos > 0 else 0
            
            content_gaps = []
            if abs(hero_pct - international_hero) > 15:
                direction = "+" if hero_pct < international_hero else "-"
                content_gaps.append(f"Hero {direction}{abs(hero_pct - international_hero):.0f}%")
            if abs(hub_pct - international_hub) > 15:
                direction = "+" if hub_pct < international_hub else "-"
                content_gaps.append(f"Hub {direction}{abs(hub_pct - international_hub):.0f}%")
            if abs(help_pct - international_help) > 15:
                direction = "+" if help_pct < international_help else "-"
                content_gaps.append(f"Help {direction}{abs(help_pct - international_help):.0f}%")
            
            content_gap_text = ", ".join(content_gaps) if content_gaps else "Équilibré"
            
            # Recommended action basé sur l'analyse
            recommended_action = "Maintenir stratégie"
            if hero_pct > 70:
                recommended_action = "Diversifier vers Hub/Help"
            elif help_pct < 15 and total_videos > 200:
                recommended_action = "Augmenter contenu Help"
            elif hub_pct < 20 and row[3] < 50000:
                recommended_action = "Focus contenu Hub"
            elif row[2] < 100 and row[4] > 1.0:
                recommended_action = "Expansion rapide"
            
            countries_data.append({
                'country': row[0],
                'competitor_count': row[1],
                'video_count': row[2],
                'avg_views_per_video': int(row[3]),
                'engagement_rate': round(row[4], 2),
                'max_views': row[5],
                'total_views': row[6],
                'avg_duration': int(row[7]),
                'hero_count': row[8],
                'hub_count': row[9],
                'help_count': row[10],
                'hero_percentage': round(hero_pct, 1),
                'hub_percentage': round(hub_pct, 1),
                'help_percentage': round(help_pct, 1),
                'top_performer': row[11],
                'opportunity_score': row[12],
                # Nouvelles métriques stratégiques
                'growth_trend': growth_trend,
                'content_gaps': content_gap_text,
                'competitive_intensity': competitive_intensity,
                'competitive_intensity_class': intensity_class,
                'recommended_action': recommended_action,
                'videos_per_competitor': round(videos_per_competitor, 0)
            })
        
        print(f"[DEBUG] Trouvé {len(countries_data)} pays avec des données")
        
        # Générer des insights stratégiques basés sur les vraies données
        insights = []
        
        if countries_data:
            # Analyser les opportunités d'expansion
            low_volume_high_engagement = [c for c in countries_data if c['video_count'] < 100 and c['engagement_rate'] > 1.0]
            if low_volume_high_engagement:
                best = max(low_volume_high_engagement, key=lambda x: x['engagement_rate'])
                insights.append({
                    'type': 'success',
                    'icon': 'bx-trending-up',
                    'title': '💡 Opportunité d\'expansion détectée',
                    'message': f"{best['country']} a le meilleur engagement ({best['engagement_rate']:.2f}%) mais seulement {best['video_count']} vidéos - Potentiel de croissance énorme"
                })
            
            # Analyser les gaps de contenu par rapport au leader
            leader = max(countries_data, key=lambda x: x['video_count'])
            content_gaps = []
            for country in countries_data:
                if country['country'] != leader['country'] and country['video_count'] > 200:
                    hero_gap = leader['hero_percentage'] - country['hero_percentage']
                    if abs(hero_gap) > 20:
                        gap_type = "manque" if hero_gap > 0 else "excès"
                        content_gaps.append({
                            'country': country['country'],
                            'gap': abs(hero_gap),
                            'type': 'Hero',
                            'direction': gap_type
                        })
            
            if content_gaps:
                biggest_gap = max(content_gaps, key=lambda x: x['gap'])
                insights.append({
                    'type': 'warning',
                    'icon': 'bx-analyse',
                    'title': f"🎯 Gap concurrentiel majeur détecté",
                    'message': f"{biggest_gap['country']} {biggest_gap['direction']} {biggest_gap['gap']:.0f}% de contenu {biggest_gap['type']} vs {leader['country']} - Réajustement stratégique nécessaire"
                })
            
            # Détecter la sur-saturation de contenu Hero
            oversaturated = [c for c in countries_data if c['hero_percentage'] > 60 and c['video_count'] > 500]
            if oversaturated:
                country = oversaturated[0]
                insights.append({
                    'type': 'warning',
                    'icon': 'bx-error-circle',
                    'title': f"⚠️ Sur-saturation de contenu Hero",
                    'message': f"{country['country']} concentre {country['hero_percentage']:.0f}% sur le Hero content - Diversifier vers Hub/Help pour améliorer l'acquisition"
                })
            
            # Identifier les marchés sous-performants avec potentiel
            underperformers = [c for c in countries_data if c['avg_views_per_video'] < 30000 and c['competitor_count'] >= 4]
            if underperformers:
                market = max(underperformers, key=lambda x: x['competitor_count'])
                insights.append({
                    'type': 'info',
                    'icon': 'bx-target-lock',
                    'title': f"🚀 Marché concurrentiel sous-exploité",
                    'message': f"{market['country']} : {market['competitor_count']} concurrents mais seulement {market['avg_views_per_video']:,} vues/vidéo - Opportunité de domination avec contenu de qualité"
                })
            
            # Recommandations basées sur les patterns de succès
            top_performer = max(countries_data, key=lambda x: x['avg_views_per_video'])
            avg_engagement = sum(c['engagement_rate'] for c in countries_data) / len(countries_data)
            
            if top_performer['hub_percentage'] > 40:
                insights.append({
                    'type': 'success',
                    'icon': 'bx-bulb',
                    'title': f"📈 Success pattern identified",
                    'message': f"{top_performer['country']} (performance leader) focuses on {top_performer['hub_percentage']:.0f}% Hub content - Replicate this model in other markets"
                })
            
            # Alerte sur les marchés avec faible engagement générale
            if avg_engagement < 1.0:
                low_engagement_markets = [c for c in countries_data if c['engagement_rate'] < avg_engagement and c['video_count'] > 300]
                if low_engagement_markets:
                    market = low_engagement_markets[0]
                    insights.append({
                        'type': 'warning',
                        'icon': 'bx-time',
                        'title': f"📉 Critical engagement",
                        'message': f"Low global engagement ({avg_engagement:.2f}%). {market['country']} particularly affected - Review content strategy and formats"
                    })
        
        # Récupérer les top vidéos par pays pour le drill-down
        cursor.execute("""
            SELECT 
                cc.country,
                v.title,
                v.view_count,
                cc.name as competitor_name,
                v.url,
                v.category
            FROM video v
            JOIN concurrent cc ON v.concurrent_id = cc.id
            WHERE cc.country IS NOT NULL 
            AND v.view_count = (
                SELECT MAX(v2.view_count)
                FROM video v2
                JOIN concurrent c2 ON v2.concurrent_id = c2.id
                WHERE c2.country = cc.country
            )
            ORDER BY v.view_count DESC
        """)
        
        top_videos_by_country = {}
        for row in cursor.fetchall():
            country = row[0]
            if country not in top_videos_by_country:
                top_videos_by_country[country] = []
            top_videos_by_country[country].append({
                'title': row[1],
                'views': row[2],
                'competitor': row[3],
                'url': row[4],
                'category': row[5]
            })
        
        conn.close()
        
        print(f"[DEBUG] Généré {len(insights)} insights")
        print(f"[DEBUG] Top vidéos pour {len(top_videos_by_country)} pays")
        
        return render_template('countries_analysis_pro.html',
                             countries_data=countries_data,
                             insights=insights,
                             top_videos_by_country=top_videos_by_country,
                             total_countries=len(countries_data),
                             total_competitors_real=total_competitors_real,
                             total_videos_real=total_videos_real)
    
    except Exception as e:
        print(f"[ERROR] Erreur dans countries_analysis: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback avec message d'erreur
        return render_template('countries_analysis_pro.html',
                             countries_data=[],
                             insights=[{
                                 'type': 'warning',
                                 'icon': 'bx-error',
                                 'title': 'Erreur de chargement',
                                 'message': f'Impossible de charger les données: {str(e)}'
                             }],
                             top_videos_by_country={},
                             total_countries=0,
                             total_competitors_real=0,
                             total_videos_real=0)

@app.route('/help')
def help_page():
    """Page d'aide"""
    from flask import redirect, url_for
    return redirect(url_for('main.home'))

# Route /tasks supprimée - maintenant gérée par main_bp.tasks_page

@app.route('/toggle-dev-mode', methods=['POST'])
def toggle_dev_mode_legacy():
    """Route de compatibilité pour toggle dev mode"""
    from blueprints.auth import login_required
    from flask import session, jsonify
    
    @login_required
    def toggle_dev_mode():
        try:
            current_state = session.get('dev_mode', False)
            new_state = not current_state
            session['dev_mode'] = new_state
            
            return jsonify({
                'success': True,
                'dev_mode': new_state,
                'message': f"Mode développeur {'activé' if new_state else 'désactivé'}"
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return toggle_dev_mode()

@app.route('/toggle-performance-mode', methods=['POST'])
def toggle_performance_mode_legacy():
    """Route de compatibilité pour toggle performance mode"""
    from blueprints.auth import login_required
    from flask import session, jsonify
    
    @login_required
    def toggle_performance_mode():
        try:
            current_state = session.get('performance_mode', False)
            new_state = not current_state
            session['performance_mode'] = new_state
            
            return jsonify({
                'success': True,
                'performance_mode': new_state,
                'message': f"Mode performance {'activé' if new_state else 'désactivé'}"
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return toggle_performance_mode()

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
    
    print(f"[STARTUP] 🎉 Application prête avec {len(list(app.url_map.iter_rules()))} routes")
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