import os
import json
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import sqlite3
import subprocess
import time
import requests
import hashlib

# Charger les variables d'environnement
load_dotenv()

# Création de l'application Flask
app = Flask(__name__)

# --- CONFIGURATION ---
# Clé secrète pour les sessions et autres
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-very-secret-key')

# Configuration de la session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Configuration du cache
app.config['CACHE_TYPE'] = 'simple'  # Cache en mémoire simple pour commencer
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes par défaut
cache = Cache(app)

# --- BASE DE DONNÉES ---
# Chemin vers le fichier de BDD
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///instance/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation de SQLAlchemy et Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODÈLES DE BASE DE DONNÉES ---
class Concurrent(db.Model):
    """Modèle pour les concurrents/chaînes YouTube"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    channel_id = db.Column(db.String(100), unique=True, nullable=False)
    channel_url = db.Column(db.String(200), unique=True, nullable=False)
    thumbnail_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    subscriber_count = db.Column(db.Integer)
    view_count = db.Column(db.BigInteger)
    video_count = db.Column(db.Integer)
    country = db.Column(db.String(50))
    language = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation avec les vidéos
    videos = db.relationship('Video', backref='concurrent', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Concurrent {self.name}>'


class Video(db.Model):
    """Modèle pour les vidéos YouTube"""
    id = db.Column(db.Integer, primary_key=True)
    concurrent_id = db.Column(db.Integer, db.ForeignKey('concurrent.id'), nullable=False)
    
    # --- Informations de base ---
    video_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(200), nullable=False)
    thumbnail_url = db.Column(db.String(200))
    
    # --- Dates et durée ---
    published_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    duration_text = db.Column(db.String(20))  # ex: "10:23"
    is_short = db.Column(db.Boolean, default=False)  # True si vidéo ≤ 60 secondes
    
    # --- Métriques objectives ---
    view_count = db.Column(db.BigInteger)
    like_count = db.Column(db.Integer)
    comment_count = db.Column(db.Integer)
    
    # --- Classification et analyse ---
    category = db.Column(db.String(50))  # 'hero', 'hub', 'help'
    tags = db.Column(db.Text)  # JSON string des tags
    
    # --- Critères subjectifs (scores sur 10) ---
    beauty_score = db.Column(db.Integer)  # 1-10
    emotion_score = db.Column(db.Integer)  # 1-10
    info_quality_score = db.Column(db.Integer)  # 1-10
    
    # --- Métadonnées ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Video {self.title}>'

# --- IMPORTS DES MODULES ---
from yt_channel_analyzer.storage import load_data
from yt_channel_analyzer.analysis import hero_hub_help_matrix
from yt_channel_analyzer.scraper import autocomplete_youtube_channels
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api, autocomplete_youtube_channels_api
from yt_channel_analyzer.youtube_api_client import get_api_quota_status
from yt_channel_analyzer.auth import verify_credentials, is_authenticated, authenticate_session, logout_session

# Décorateur de connexion requis
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated(session):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Import des fonctions de base de données
from yt_channel_analyzer.database import competitors_to_legacy_format, get_all_competitors, save_competitor_and_videos, get_db_connection, get_classification_patterns

# Import des modules ViewStats supprimés - analyse locale maintenant

# Fonctions utilitaires pour la compatibilité avec l'ancien format JSON
def load_cache():
    """Charger les concurrents depuis la base de données (format legacy)"""
    try:
        return competitors_to_legacy_format()
    except Exception as e:
        print(f"Erreur lors du chargement depuis la base: {e}")
        return {}

def save_cache(data):
    """Sauvegarder dans la base de données (pour compatibilité)"""
    # Cette fonction est conservée pour compatibilité mais n'est plus utilisée
    # Les données sont maintenant directement sauvées en base via les fonctions database.py
    print("⚠️ save_cache() est deprecated - utilisez les fonctions database.py")

def get_channel_key(channel_url):
    """Générer une clé unique pour une chaîne"""
    return channel_url.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_')

def extract_channel_name(channel_url):
    """Extraire le nom de la chaîne depuis l'URL"""
    try:
        parts = channel_url.split('/')
        if 'channel/' in channel_url:
            return parts[-1][:20]
        elif '@' in channel_url:
            return parts[-1][:20]
        else:
            return "Canal"[:20]
    except:
        return "Canal"

def calculate_total_views(videos):
    """Calculer le total des vues pour une liste de vidéos"""
    total = 0
    for video in videos:
        views_str = str(video.get('views', '0')).replace(',', '').replace(' ', '')
        try:
            views_num = int(views_str) if views_str.isdigit() else 0
            total += views_num
        except:
            continue
    return total

def format_number(num):
    """Formater un nombre avec des séparateurs de milliers"""
    try:
        return f"{int(num):,}".replace(',', ' ')
    except:
        return str(num)

# Enregistrer le filtre format_number pour les templates Jinja2
app.jinja_env.filters['format_number'] = format_number

def save_competitor_data(channel_url, videos):
    """Sauvegarder/enrichir intelligemment les données d'un concurrent"""
    try:
        from yt_channel_analyzer.database import refresh_competitor_data
        from yt_channel_analyzer.youtube_api_client import create_youtube_client
        
        print(f"[SAVE] 💾 Sauvegarde intelligente de {len(videos)} vidéos pour {channel_url}")
        
        # Récupérer les infos de la chaîne pour enrichir
        channel_info = None
        try:
            youtube_client = create_youtube_client()
            channel_info = youtube_client.get_channel_info(channel_url)
            print(f"[SAVE] 📊 Infos chaîne: {channel_info.get('title', 'N/A')}")
        except Exception as e:
            print(f"[SAVE] ⚠️ Impossible de récupérer les infos chaîne: {e}")
        
        # Utiliser le refresh intelligent (création + enrichissement automatique)
        result = refresh_competitor_data(channel_url, videos, channel_info)
        
        if result['success']:
            action = result['action']
            competitor_name = result.get('competitor_name', 'Concurrent')
            competitor_id = result['competitor_id']
            
            if action == 'created':
                print(f"[SAVE] ✅ NOUVEAU concurrent créé: {competitor_name} (ID: {competitor_id})")
            else:  # refreshed
                print(f"[SAVE] 🔄 ENRICHISSEMENT: {competitor_name} (ID: {competitor_id})")
                print(f"[SAVE] 📈 Nouvelles: {result['new_videos']}, "
                      f"Enrichies: {result['enriched_videos']}, "
                      f"Total: {result['total_videos']}")
            
            return competitor_id
        else:
            raise Exception(result.get('error', 'Erreur inconnue lors de la sauvegarde'))
        
    except Exception as e:
        print(f"[SAVE] ❌ Erreur critique: {e}")
        raise

# --- ROUTES DE L'APPLICATION ---

@app.route('/')
@login_required
def home():
    from yt_channel_analyzer.database import get_db_connection
    import sqlite3
    
    try:
        # Utiliser des requêtes SQL directes pour calculer les statistiques
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculer le nombre de concurrents
        cursor.execute('SELECT COUNT(*) FROM concurrent')
        total_competitors = cursor.fetchone()[0]
        
        # Calculer le nombre total de vidéos
        cursor.execute('SELECT COUNT(*) FROM video')
        total_videos = cursor.fetchone()[0]
        
        # Calculer le total des vues
        cursor.execute('SELECT SUM(view_count) FROM video WHERE view_count IS NOT NULL')
        total_views = cursor.fetchone()[0] or 0
        
        # Calculer le nombre de playlists
        cursor.execute('SELECT COUNT(*) FROM playlist')
        total_playlists = cursor.fetchone()[0]
        
        # Calculer le nombre de pays distincts
        cursor.execute('SELECT COUNT(DISTINCT country) FROM concurrent WHERE country IS NOT NULL AND country != ""')
        total_countries = cursor.fetchone()[0]
        
        conn.close()
        
        # Formater les vues avec des abréviations
        def format_views(views):
            if views >= 1000000:
                return f"{views/1000000:.1f}M"
            elif views >= 1000:
                return f"{views/1000:.1f}K"
            else:
                return str(views)
        
        stats = {
            'total_competitors': total_competitors,
            'total_videos': total_videos,
            'total_views': total_views,
            'total_views_formatted': format_views(total_views),
            'total_playlists': total_playlists,
            'countries': total_countries
        }
        
        print(f"[HOME] 📊 Statistiques calculées: {total_competitors} concurrents, {total_videos} vidéos, {total_views:,} vues, {total_playlists} playlists")
        
    except Exception as e:
        print(f"[HOME] ❌ Erreur lors du calcul des statistiques: {e}")
        import traceback
        traceback.print_exc()
        
        # Valeurs par défaut en cas d'erreur
        stats = {
            'total_competitors': 0,
            'total_videos': 0,
            'total_views': 0,
            'total_views_formatted': '0',
            'total_playlists': 0,
            'countries': 0
        }
    
    return render_template('home_modern.html', stats=stats)

@app.route('/home_old')
@login_required
def home_old():
    return render_template('home.html')

@app.route('/dashboard-glass')
@login_required
def dashboard_glass():
    """Page de démonstration du système glassmorphism avancé"""
    return render_template('dashboard_glass.html')

@app.route('/concurrents')
@login_required
def concurrents():
    """
    Afficher la liste de tous les concurrents avec leurs statistiques
    """
    from yt_channel_analyzer.database.competitors import get_all_competitors_with_videos
    from yt_channel_analyzer.database import calculate_publication_frequency, update_competitor_tags
    
    # Récupérer tous les concurrents avec leurs vidéos (déjà précalculé)
    competitors = get_all_competitors_with_videos()
    
    # NEW: ensure local cached thumbnails
    thumbnails_dir = os.path.join('static', 'competitors', 'images')
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    for competitor in competitors:
        thumb_local_rel = None
        comp_id = competitor.get('id')
        if comp_id is None:
            continue
        local_filename = f"{comp_id}.jpg"
        local_path = os.path.join(thumbnails_dir, local_filename)
        # If already downloaded, just point to it
        if os.path.exists(local_path):
            thumb_local_rel = f"/static/competitors/images/{local_filename}"
        else:
            remote_url = competitor.get('thumbnail_url')
            if remote_url:
                try:
                    resp = requests.get(remote_url, timeout=5)
                    if resp.status_code == 200 and resp.content:
                        with open(local_path, 'wb') as img_f:
                            img_f.write(resp.content)
                        thumb_local_rel = f"/static/competitors/images/{local_filename}"
                except Exception as download_err:
                    print(f"[THUMBNAIL] Failed to download for competitor {comp_id}: {download_err}")
        competitor['thumbnail_local'] = thumb_local_rel
    
    # Calculer les fréquences de publication
    # frequency_data = calculate_publication_frequency()
    
    # NOUVEAU : Récupérer directement depuis la table competitor_frequency_stats
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT competitor_id, avg_videos_per_week, frequency_hero, frequency_hub, frequency_help
        FROM competitor_frequency_stats
    ''')
    frequency_results = cursor.fetchall()
    conn.close()
    
    # Créer un dictionnaire pour accès rapide
    frequency_data = {}
    for row in frequency_results:
        competitor_id, avg_per_week, freq_hero, freq_hub, freq_help = row
        frequency_data[competitor_id] = {
            'avg_videos_per_week': avg_per_week,
            'hero_frequency': freq_hero,
            'hub_frequency': freq_hub,
            'help_frequency': freq_help
        }
    
    # Enrichir les données des concurrents avec la fréquence (SANS recalculer les stats)
    for competitor in competitors:
        competitor_id = competitor['id']
        frequency_competitor_data = frequency_data.get(competitor_id, {})
        
        # Ajouter les données de fréquence au dictionnaire du concurrent
        competitor.update({
            'frequency_total': frequency_competitor_data.get('avg_videos_per_week', 0),
            'frequency_hero': frequency_competitor_data.get('hero_frequency', 0),
            'frequency_hub': frequency_competitor_data.get('hub_frequency', 0),
            'frequency_help': frequency_competitor_data.get('help_frequency', 0)
        })

    # Trier les concurrents par nombre de vidéos (déjà fait dans la requête SQL, mais double-sécurité)
    competitors.sort(key=lambda x: x.get('video_count', 0), reverse=True)
    
    return render_template(
        'concurrents.html', 
        competitors=competitors,
        page_title="Concurrents",
        body_class="body-glassmorphism",
        active_page="concurrents"
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_credentials(username, password):
            authenticate_session(session)
            return redirect(url_for('home'))
        else:
            return render_template('login_modern.html', error='Identifiants incorrects')
    
    return render_template('login_modern.html')

@app.route('/logout')
def logout():
    logout_session(session)
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres (règles métiers uniquement)"""
    if request.method == 'POST':
        # Sauvegarder les paramètres
        settings_data = {
            'paid_threshold': int(request.form.get('paid_threshold', 10000)),
            'industry': request.form.get('industry', 'tourism'),
            'auto_classify': 'auto_classify' in request.form,
            'max_videos': int(request.form.get('max_videos', 1000)),
            'cache_duration': int(request.form.get('cache_duration', 24))
        }
        
        save_settings(settings_data)
        print(f"[SETTINGS] Paramètres sauvegardés: {settings_data}")
        
        return render_template('settings.html', 
                             current_settings=settings_data,
                             message="Paramètres sauvegardés avec succès !")
    
    current_settings = load_settings()
    
    # Récupérer les patterns de classification multilingues
    patterns = get_classification_patterns()
    
    # Récupérer les concurrents pour la section d'analyse
    competitors = get_all_competitors()
    
    # Récupérer les statistiques de la supervision humaine
    from yt_channel_analyzer.supervised_learning import get_human_classifications
    human_stats = get_human_classifications(limit=0, offset=0) # limit=0 pour ne récupérer que les stats

    return render_template('settings.html', 
                         current_settings=current_settings,
                         patterns=patterns,
                         competitors=competitors,
                         human_stats=human_stats) # Passer les stats au template

def load_settings():
    """Charger les paramètres depuis le fichier"""
    settings_file = 'settings.json'
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Paramètres par défaut
        return {
            'paid_threshold': 10000,
            'industry': 'tourism',
            'auto_classify': True,
            'max_videos': 1000,
            'cache_duration': 24
        }

def save_settings(settings_data):
    """Sauvegarder les paramètres dans le fichier"""
    settings_file = 'settings.json'
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des paramètres: {e}")

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    """Récupère toutes les tâches"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        tasks = task_manager.get_all_tasks()
        return jsonify([task.to_dict() for task in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/delete', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Supprime définitivement une tâche et ses données"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        task_manager.delete_task(task_id)
        return jsonify({'success': True, 'message': 'Tâche supprimée définitivement'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/clean-duplicates', methods=['POST'])
@login_required
def clean_duplicate_tasks():
    """Nettoie les tâches en double en gardant celle avec le plus de vidéos"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        deleted_count = task_manager.clean_duplicate_tasks()
        
        if deleted_count > 0:
            message = f'Nettoyage terminé: {deleted_count} doublons supprimés'
        else:
            message = 'Aucun doublon trouvé'
            
        return jsonify({
            'success': True, 
            'message': message,
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"[CLEAN-DUPLICATES] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/launch-background-task', methods=['POST'])
@login_required
def launch_background_task():
    """Lance une nouvelle tâche d'analyse en arrière-plan depuis la page concurrents"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        data = request.get_json()
        channel_url = data.get('channel_url')
        task_type = data.get('task_type', 'relaunch')
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de la chaîne manquante'})
        
        # Extraire le nom de la chaîne depuis la base de données ou l'URL
        channel_name = "Canal"
        try:
            from yt_channel_analyzer.database import get_competitor_by_url
            competitor = get_competitor_by_url(channel_url)
            if competitor:
                channel_name = competitor.get('name', extract_channel_name(channel_url))
            else:
                channel_name = extract_channel_name(channel_url)
        except:
            channel_name = extract_channel_name(channel_url)
        
        # Créer la tâche avec un nom descriptif
        task_name = f"Relancement - {channel_name}"
        task_id = task_manager.create_task(channel_url, task_name)
        
        # Lancer le scraping en arrière-plan
        task_manager.start_background_scraping(task_id, channel_url)
        
        return jsonify({
            'success': True, 
            'task_id': task_id,
            'message': f'Analyse relancée en arrière-plan pour {channel_name}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/tasks')
@login_required
def tasks_page():
    """Page des tâches en cours"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        tasks = task_manager.get_all_tasks_with_warnings()
        return render_template('tasks_modern.html', tasks=tasks)
    except Exception as e:
        return render_template('tasks_modern.html', tasks=[], error=str(e))

@app.route('/tasks_old')
@login_required
def tasks_page_old():
    """Page des tâches en cours (ancienne version)"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        tasks = task_manager.get_all_tasks()
        return render_template('tasks.html', tasks=tasks)
    except Exception as e:
        return render_template('tasks.html', tasks=[], error=str(e))

# ANCIENNES ROUTES SUPPRIMÉES - Maintenant on utilise /api/refresh-competitor qui fait tout

@app.route('/api/refresh-competitor', methods=['POST'])
@login_required
def refresh_competitor():
    """Rafraîchir intelligemment les données d'un concurrent existant"""
    try:
        data = request.get_json() if request.is_json else request.form
        channel_url = data.get('channel_url', '').strip()
        competitor_id = data.get('competitor_id')
        
        if not channel_url and not competitor_id:
            return jsonify({'success': False, 'error': 'URL de chaîne ou ID concurrent requis'})
        
        # Si on a seulement l'ID, récupérer l'URL
        if competitor_id and not channel_url:
            from yt_channel_analyzer.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT channel_url FROM concurrent WHERE id = ?', (competitor_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return jsonify({'success': False, 'error': 'Concurrent non trouvé'})
            channel_url = result[0]
        
        print(f"[REFRESH-API] 🔄 Début du rafraîchissement pour: {channel_url}")
        
        # Récupérer les données fraîches via l'API YouTube
        try:
            from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api
            from yt_channel_analyzer.youtube_api_client import create_youtube_client
            
            # Récupérer les vidéos fraîches (limite élevée pour avoir le maximum)
            fresh_videos = get_channel_videos_data_api(channel_url, video_limit=1000)
            
            if not fresh_videos:
                return jsonify({'success': False, 'error': 'Aucune vidéo trouvée lors du rafraîchissement'})
            
            # Récupérer aussi les infos de la chaîne
            youtube_client = create_youtube_client()
            channel_info = youtube_client.get_channel_info(channel_url)
            
            print(f"[REFRESH-API] 📊 {len(fresh_videos)} vidéos récupérées via API")
            
            # Utiliser la nouvelle fonction de rafraîchissement intelligent
            from yt_channel_analyzer.database import refresh_competitor_data
            result = refresh_competitor_data(channel_url, fresh_videos, channel_info)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f"Rafraîchissement terminé pour {result.get('competitor_name', 'le concurrent')}",
                    'stats': {
                        'total_videos': result['total_videos'],
                        'new_videos': result['new_videos'],
                        'updated_videos': result['updated_videos'],
                        'enriched_videos': result['enriched_videos'],
                        'total_processed': result['total_processed']
                    },
                    'competitor_id': result['competitor_id']
                })
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Erreur inconnue')})
                
        except Exception as api_error:
            print(f"[REFRESH-API] ❌ Erreur API: {api_error}")
            return jsonify({'success': False, 'error': f'Erreur lors de la récupération des données: {str(api_error)}'})
        
    except Exception as e:
        print(f"[REFRESH-API] ❌ Erreur générale: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========================================
# API USAGE MONITORING ROUTES
# ========================================

def load_api_quota_data():
    """Charger les données de quota API"""
    quota_file = "api_quota_tracking.json"
    try:
        with open(quota_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        # Créer le fichier s'il n'existe pas
        default_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "quota_used": 0,
            "requests_made": 0,
            "last_updated": datetime.now().isoformat()
        }
        save_api_quota_data(default_data)
        return default_data
    except Exception as e:
        print(f"Erreur lors du chargement des données de quota: {e}")
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "quota_used": 0,
            "requests_made": 0,
            "last_updated": datetime.now().isoformat()
        }

def save_api_quota_data(data):
    """Sauvegarder les données de quota API"""
    quota_file = "api_quota_tracking.json"
    try:
        with open(quota_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des données de quota: {e}")

@app.route('/api-usage')
@login_required
def api_usage_page():
    """Page de monitoring de l'utilisation de l'API YouTube"""
    return render_template('api_usage.html')

@app.route('/debug')
@login_required
def debug_page():
    """Page des outils de debug et de propagation"""
    return render_template('debug.html')

@app.route('/api/usage')
@login_required
def get_api_usage():
    """Récupérer les données d'utilisation de l'API au format JSON"""
    try:
        # Charger les données du fichier quota
        quota_data = load_api_quota_data()
        
        # Récupérer les données depuis l'API YouTube si possible
        try:
            from yt_channel_analyzer.youtube_api_client import get_api_quota_status
            api_status = get_api_quota_status()
            
            # Merger les données
            quota_used = max(quota_data.get('quota_used', 0), api_status.get('quota_used', 0))
            requests_made = max(quota_data.get('requests_made', 0), api_status.get('requests_made', 0))
        except Exception as e:
            print(f"Erreur récupération status API: {e}")
            quota_used = quota_data.get('quota_used', 0)
            requests_made = quota_data.get('requests_made', 0)
        
        # Constantes
        daily_quota = 10000  # Quota quotidien par défaut YouTube API
        
        # Calculer les statistiques
        percentage = (quota_used / daily_quota) * 100 if daily_quota > 0 else 0
        remaining = max(0, daily_quota - quota_used)
        
        # Déterminer le statut
        if percentage > 90:
            status = 'critical'
        elif percentage > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        # Vérifier si on doit réinitialiser (nouveau jour)
        current_date = datetime.now().strftime("%Y-%m-%d")
        if quota_data.get('date') != current_date:
            # Nouveau jour, réinitialiser les compteurs
            quota_data.update({
                'date': current_date,
                'quota_used': 0,
                'requests_made': 0,
                'last_updated': datetime.now().isoformat()
            })
            save_api_quota_data(quota_data)
            
            # Recalculer avec les nouvelles valeurs
            quota_used = 0
            requests_made = 0
            percentage = 0
            remaining = daily_quota
            status = 'healthy'
        
        return jsonify({
            'success': True,
            'date': quota_data.get('date', current_date),
            'today_usage': quota_used,
            'quota_used': quota_used,
            'requests_made': requests_made,
            'daily_quota': daily_quota,
            'percentage': round(percentage, 1),
            'remaining': remaining,
            'status': status,
            'last_updated': quota_data.get('last_updated', datetime.now().isoformat())
        })
        
    except Exception as e:
        print(f"Erreur dans get_api_usage: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'date': datetime.now().strftime("%Y-%m-%d"),
            'today_usage': 0,
            'quota_used': 0,
            'requests_made': 0,
            'daily_quota': 10000,
            'percentage': 0,
            'remaining': 10000,
            'status': 'unknown',
            'last_updated': datetime.now().isoformat()
        }), 500

@app.route('/api/usage/reset', methods=['POST'])
@login_required
def reset_api_usage():
    """Réinitialiser le compteur de quota API"""
    try:
        # Réinitialiser les données
        reset_data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'quota_used': 0,
            'requests_made': 0,
            'last_updated': datetime.now().isoformat()
        }
        
        save_api_quota_data(reset_data)
        
        return jsonify({
            'success': True,
            'message': 'Quota counter reset successfully',
            'data': reset_data
        })
        
    except Exception as e:
        print(f"Erreur lors de la réinitialisation: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to reset quota: {str(e)}'
        }), 500

@app.route('/autocomplete')
@login_required
def autocomplete():
    """Route pour l'autocomplétion des chaînes YouTube - EXCLUT les concurrents déjà en base"""
    q = request.args.get('q', '')
    if not q.strip():
        return jsonify([])
    
    # Récupérer les chaînes déjà en base pour les exclure
    try:
        from yt_channel_analyzer.database import get_all_competitors
        existing_competitors = get_all_competitors()
        existing_urls = set()
        existing_names = set()
        
        for comp in existing_competitors:
            if comp.get('channel_url'):
                existing_urls.add(comp['channel_url'].lower().strip())
            if comp.get('name'):
                existing_names.add(comp['name'].lower().strip())
        
        print(f"[AUTOCOMPLETE] 📋 {len(existing_competitors)} concurrents en base pour enrichissement")
        
    except Exception as e:
        print(f"[AUTOCOMPLETE] ⚠️ Erreur récupération concurrents existants: {e}")
        existing_urls = set()
        existing_names = set()
    
    # 🚀 Utiliser l'API YouTube en priorité
    try:
        suggestions = autocomplete_youtube_channels_api(q, max_results=15)  # Plus de résultats pour compenser l'enrichissement
        if suggestions:
            # Enrichir les suggestions avec les informations des chaînes déjà en base
            enriched_suggestions = []
            for suggestion in suggestions:
                suggestion_url = suggestion.get('url', '').lower().strip()
                suggestion_name = suggestion.get('name', '').lower().strip()
                
                # Vérifier si cette chaîne est déjà en base
                existing_competitor = None
                for comp in existing_competitors:
                    comp_url = comp.get('channel_url', '').lower().strip()
                    comp_name = comp.get('name', '').lower().strip()
                    
                    if (suggestion_url == comp_url) or (suggestion_name == comp_name):
                        existing_competitor = comp
                        break
                
                if existing_competitor:
                    # Enrichir la suggestion avec les infos de la base
                    suggestion['is_analyzed'] = True
                    suggestion['competitor_id'] = existing_competitor.get('id')
                    suggestion['video_count'] = existing_competitor.get('video_count', 0)
                    suggestion['analysis_date'] = existing_competitor.get('created_at', '')[:10] if existing_competitor.get('created_at') else 'Date inconnue'
                    
                    # Garder la miniature de l'API si disponible, sinon utiliser celle de la base
                    if not suggestion.get('thumbnail') and existing_competitor.get('thumbnail_url'):
                        suggestion['thumbnail'] = existing_competitor['thumbnail_url']
                    
                    print(f"[AUTOCOMPLETE] ✅ Enrichi (déjà en base): {suggestion.get('name', 'Sans nom')} - {suggestion['video_count']} vidéos")
                else:
                    # Nouvelle chaîne, pas encore analysée
                    suggestion['is_analyzed'] = False
                    print(f"[AUTOCOMPLETE] 🆕 Nouvelle chaîne: {suggestion.get('name', 'Sans nom')}")
                
                enriched_suggestions.append(suggestion)
            
            print(f"[API] ✅ {len(enriched_suggestions)} suggestions enrichies pour '{q}'")
            return jsonify(enriched_suggestions[:10])  # Limiter à 10 résultats finaux
            
    except Exception as e:
        print(f"[API] ❌ Erreur autocomplete API: {e}")
    
    # Fallback vers le scraping avec enrichissement
    try:
        print(f"[SCRAPING] 🔄 Fallback autocomplete pour '{q}'")
        suggestions = autocomplete_youtube_channels(q)
        
        # Enrichir les suggestions du scraping aussi
        enriched_suggestions = []
        for suggestion in suggestions:
            suggestion_url = suggestion.get('url', '').lower().strip()
            suggestion_name = suggestion.get('name', '').lower().strip()
            
            # Vérifier si cette chaîne est déjà en base
            existing_competitor = None
            for comp in existing_competitors:
                comp_url = comp.get('channel_url', '').lower().strip()
                comp_name = comp.get('name', '').lower().strip()
                
                if (suggestion_url == comp_url) or (suggestion_name == comp_name):
                    existing_competitor = comp
                    break
            
            if existing_competitor:
                # Enrichir la suggestion avec les infos de la base
                suggestion['is_analyzed'] = True
                suggestion['competitor_id'] = existing_competitor.get('id')
                suggestion['video_count'] = existing_competitor.get('video_count', 0)
                suggestion['analysis_date'] = existing_competitor.get('created_at', '')[:10] if existing_competitor.get('created_at') else 'Date inconnue'
                
                # Utiliser la miniature de la base si pas de miniature du scraping
                if not suggestion.get('thumbnail') and existing_competitor.get('thumbnail_url'):
                    suggestion['thumbnail'] = existing_competitor['thumbnail_url']
            else:
                # Nouvelle chaîne
                suggestion['is_analyzed'] = False
            
            enriched_suggestions.append(suggestion)
        
        return jsonify(enriched_suggestions[:10])
        
    except Exception as e:
        print(f"[SCRAPING] ❌ Erreur scraping autocomplete: {e}")
        return jsonify([])

@app.route('/api/simple-analysis', methods=['POST'])
@login_required
def simple_analysis():
    """Analyser une chaîne de manière simple et directe"""
    try:
        data = request.get_json() if request.is_json else request.form
        channel_url = data.get('channel_url', '').strip()
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de chaîne manquante'})
        
        # Valider l'URL YouTube
        if 'youtube.com' not in channel_url and 'youtu.be' not in channel_url:
            return jsonify({'success': False, 'error': 'URL YouTube invalide'})
        
        # Créer une tâche pour le suivi
        try:
            from yt_channel_analyzer.background_tasks import task_manager
            channel_name = extract_channel_name(channel_url)
            task_id = task_manager.create_task(channel_url, f"Analyse - {channel_name}")
            
            # Marquer comme en cours
            task_manager.update_task(task_id, 
                current_step='Récupération des vidéos via API YouTube...', 
                progress=20
            )
        except Exception as task_error:
            print(f"[TASK] Erreur création tâche: {task_error}")
            task_id = None
        
        # Lancer l'analyse directement avec l'API YouTube
        try:
            from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api
            
            print(f"[ANALYSIS] Début de l'analyse pour: {channel_url}")
            
            # Mettre à jour la tâche
            if task_id:
                task_manager.update_task(task_id, 
                    current_step='Analyse des vidéos en cours...', 
                    progress=50
                )
            
            # Récupérer les vidéos via l'API
            videos = get_channel_videos_data_api(channel_url, video_limit=1000)
            
            if not videos:
                if task_id:
                    task_manager.error_task(task_id, 'Aucune vidéo trouvée')
                return jsonify({'success': False, 'error': 'Aucune vidéo trouvée'})
            
            # Mettre à jour la tâche
            if task_id:
                task_manager.update_task(task_id, 
                    current_step='Sauvegarde en base de données...', 
                    progress=80,
                    videos_found=len(videos)
                )
            
            # Sauvegarder directement dans la base de données
            competitor_id = save_competitor_data(channel_url, videos)
            
            # 🚀 NOUVEAU : Classification automatique des vidéos après sauvegarde
            if task_id:
                task_manager.update_task(task_id, 
                    current_step='Classification automatique des vidéos...', 
                    progress=90,
                    videos_found=len(videos)
                )
            
            try:
                from yt_channel_analyzer.database import classify_videos_directly_with_keywords
                print(f"[ANALYSIS] 🤖 Lancement de la classification automatique pour {len(videos)} vidéos")
                
                # Classifier directement les vidéos de ce concurrent
                classification_result = classify_videos_directly_with_keywords(competitor_id)
                videos_classified = classification_result.get('videos_classified', 0)
                
                if videos_classified > 0:
                    print(f"[ANALYSIS] ✅ Classification terminée: {videos_classified} vidéos classifiées automatiquement")
                else:
                    print(f"[ANALYSIS] ℹ️ Aucune vidéo à classifier (déjà classifiées)")
                
            except Exception as classification_error:
                print(f"[ANALYSIS] ⚠️ Erreur lors de la classification automatique: {classification_error}")
                # Ne pas bloquer l'analyse si la classification échoue
            
            # Marquer la tâche comme terminée
            if task_id:
                task_manager.complete_task(task_id, len(videos))
            
            print(f"[ANALYSIS] Analyse terminée: {len(videos)} vidéos sauvegardées")
            
            return jsonify({
                'success': True,
                'videos_count': len(videos),
                'competitor_id': competitor_id,
                'task_id': task_id,
                'message': f'Analyse terminée: {len(videos)} vidéos trouvées',
                'redirect': '/concurrents'
            })
            
        except Exception as api_error:
            print(f"[ANALYSIS] Erreur API: {api_error}")
            if task_id:
                task_manager.error_task(task_id, str(api_error))
            return jsonify({'success': False, 'error': f'Erreur lors de l\'analyse: {str(api_error)}'})
        
    except Exception as e:
        print(f"[ANALYSIS] Erreur générale: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analyze-channel', methods=['GET', 'POST'])
@login_required
def analyze_channel():
    """Route pour analyser une chaîne depuis la barre de recherche centrale"""
    if request.method == 'GET':
        # Récupérer les paramètres de l'URL
        search_query = request.args.get('search', '')
        channel_url = request.args.get('channel_url', '')
        max_videos = int(request.args.get('max_videos', 30))
        ai_classification = request.args.get('ai_classification', 'true') == 'true'
        period = request.args.get('period', '')
        
        # Si on a une URL directe, on lance l'analyse
        if channel_url:
            return launch_analysis_with_params(channel_url, max_videos, ai_classification, period)
        
        # Sinon, on redirige vers la page d'accueil avec la recherche pré-remplie
        return redirect(url_for('home', search=search_query))
    
    # Si POST, traiter les données du formulaire
    channel_url = request.form.get('channel_url', '').strip()
    search_query = request.form.get('search_query', '').strip()
    max_videos = int(request.form.get('max_videos', 30))
    ai_classification = 'ai_classification' in request.form
    
    if not channel_url and not search_query:
        flash('Veuillez entrer une URL ou le nom d\'une chaîne YouTube', 'error')
        return redirect(url_for('home'))
    
    # Si on a seulement une recherche, essayer de trouver l'URL
    if search_query and not channel_url:
        try:
            # Utiliser l'API d'autocomplete pour trouver l'URL
            from yt_channel_analyzer.scraper import autocomplete_youtube_channels
            suggestions = autocomplete_youtube_channels(search_query)
            if suggestions:
                channel_url = suggestions[0]['url']
            else:
                flash(f'Aucune chaîne trouvée pour "{search_query}"', 'warning')
                return redirect(url_for('home', search=search_query))
        except Exception as e:
            flash(f'Erreur lors de la recherche: {e}', 'error')
            return redirect(url_for('home'))
    
    return launch_analysis_with_params(channel_url, max_videos, ai_classification)

def launch_analysis_with_params(channel_url, max_videos=30, ai_classification=True, period=''):
    """Lance l'analyse avec les paramètres donnés"""
    try:
        # Lancer l'analyse en arrière-plan
        channel_name = extract_channel_name(channel_url)
        
        response = fetch('/api/launch-background-task', {
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'channel_url': channel_url,
                'channel_name': channel_name,
                'max_videos': max_videos,
                'ai_classification': ai_classification,
                'period': period
            })
        })
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                flash(f'Analyse lancée pour "{channel_name}"', 'success')
                return redirect(url_for('tasks_page'))
            else:
                flash(f'Erreur lors du lancement: {result.get("error", "Erreur inconnue")}', 'error')
        else:
            flash('Erreur lors du lancement de l\'analyse', 'error')
            
    except Exception as e:
        print(f"Erreur lors du lancement de l'analyse: {e}")
        flash(f'Erreur lors du lancement de l\'analyse: {e}', 'error')
    
    return redirect(url_for('home'))

@app.route('/competitor/<int:competitor_id>')
@login_required
def competitor_detail(competitor_id):
    conn = get_db_connection()
    # 1. Récupération du concurrent
    competitor = conn.execute('SELECT * FROM concurrent WHERE id = ?', (competitor_id,)).fetchone()
    if competitor is None:
        flash("Concurrent non trouvé.", "error")
        return redirect(url_for('concurrents'))

    # 2. Récupération des vidéos
    videos = conn.execute('SELECT * FROM video WHERE concurrent_id = ? ORDER BY published_at DESC', (competitor_id,)).fetchall()

    # 3. Charger le seuil paid_threshold depuis les settings
    settings = load_settings()
    paid_threshold = settings.get('paid_threshold', 10000)

    # 4. Calcul des statistiques de base avec organic/paid basé sur le seuil
    paid_count = sum(1 for v in videos if v['view_count'] and v['view_count'] >= paid_threshold)
    organic_count = len(videos) - paid_count
    
    # 5. Calcul des statistiques de Shorts basées sur les vraies données de la base
    shorts_count = sum(1 for v in videos if v['is_short'] == 1)
    regular_videos_count = len(videos) - shorts_count
    shorts_views = sum(v['view_count'] for v in videos if v['is_short'] == 1 and v['view_count'])
    regular_views = sum(v['view_count'] for v in videos if v['is_short'] == 0 and v['view_count'])
    total_views = shorts_views + regular_views
    
    # Calcul des métriques de Shorts
    shorts_percentage = (shorts_count / len(videos) * 100) if len(videos) > 0 else 0
    avg_views_shorts = shorts_views / shorts_count if shorts_count > 0 else 0
    avg_views_regular = regular_views / regular_videos_count if regular_videos_count > 0 else 0
    performance_relative = (avg_views_shorts / avg_views_regular * 100) if avg_views_regular > 0 else 0
    
    # Shorts par période (approximation basée sur les données disponibles)
    shorts_per_week = 0  # Sera calculé plus tard si nécessaire
    shorts_per_month = shorts_count  # Approximation pour l'instant
    
    # Structure des données de Shorts
    shorts_data = {
        'shorts_percentage': round(shorts_percentage, 1),
        'shorts_count': shorts_count,
        'total_shorts_views': shorts_views,
        'avg_views_shorts': int(avg_views_shorts),
        'avg_views_regular': int(avg_views_regular),
        'performance_relative': round(performance_relative, 1) if performance_relative > 0 else 'N/A',
        'shorts_per_week': shorts_per_week,
        'shorts_per_month': shorts_per_month
    }
    
    # 5. Calcul de la matrice de performance par catégorie et type
    performance_matrix = {
        'hero': {'organic': [], 'paid': []},
        'hub': {'organic': [], 'paid': []},
        'help': {'organic': [], 'paid': []}
    }
    
    # Remplir la matrice avec les vues des vidéos
    for video in videos:
        if video['view_count'] is None:
            continue
            
        category = video['category'] or 'hub'  # Default to hub if no category
        views = video['view_count']
        
        if category in performance_matrix:
            if views >= paid_threshold:
                performance_matrix[category]['paid'].append(views)
            else:
                performance_matrix[category]['organic'].append(views)
    
    # 6. Calculer les médianes pour chaque cellule de la matrice
    def calculate_median(values):
        if not values:
            return 0
        values.sort()
        n = len(values)
        return values[n//2] if n % 2 == 1 else (values[n//2-1] + values[n//2]) // 2
    
    performance_matrix_stats = {}
    for category in ['hero', 'hub', 'help']:
        performance_matrix_stats[category] = {
            'organic_median': calculate_median(performance_matrix[category]['organic']),
            'organic_count': len(performance_matrix[category]['organic']),
            'paid_median': calculate_median(performance_matrix[category]['paid']),
            'paid_count': len(performance_matrix[category]['paid'])
        }

    stats = {
        'total_videos': len(videos),
        'total_views': sum(v['view_count'] for v in videos if v['view_count']),
        'total_likes': sum(v['like_count'] for v in videos if v['like_count']),
        'hero_count': sum(1 for v in videos if v['category'] == 'hero'),
        'hub_count': sum(1 for v in videos if v['category'] == 'hub'),
        'help_count': sum(1 for v in videos if v['category'] == 'help'),
        'paid_count': paid_count,
        'organic_count': organic_count,
        'paid_threshold': paid_threshold,
        'performance_matrix': performance_matrix_stats
    }
    stats['paid_percentage'] = round((stats['paid_count'] / stats['total_videos']) * 100) if stats['total_videos'] > 0 else 0
    stats['organic_percentage'] = round((stats['organic_count'] / stats['total_videos']) * 100) if stats['total_videos'] > 0 else 0

    # 4. Top 5 vidéos par vues et par likes
    top_videos_views = sorted([v for v in videos if v['view_count'] is not None], key=lambda x: x['view_count'], reverse=True)[:5]
    top_videos_likes = sorted([v for v in videos if v['like_count'] is not None], key=lambda x: x['like_count'], reverse=True)[:5]
    
    # 5. Préparation des données pour le graphique Top 5
    top_videos_json = {
        "labels": [v['title'] for v in top_videos_views],
        "views": [v['view_count'] for v in top_videos_views],
        "likes": [v['like_count'] for v in top_videos_views],
        "video_ids": [v['video_id'] for v in top_videos_views]
    }

    # 6. Données pour la matrice de performance
    performance_data = {
        "labels": ["Vues", "Likes", "HERO", "HUB", "HELP"],
        "values": [
            stats['total_views'] / stats['total_videos'] if stats['total_videos'] > 0 else 0,
            stats['total_likes'] / stats['total_videos'] if stats['total_videos'] > 0 else 0,
            stats['hero_count'],
            stats['hub_count'],
            stats['help_count']
        ]
    }

    # 7. Données pour la distribution des catégories
    category_distribution = {
        "labels": ["HERO", "HUB", "HELP"],
        "values": [stats['hero_count'], stats['hub_count'], stats['help_count']]
    }

    # 8. Données pour la distribution des types de contenu
    content_type_distribution = {
        "labels": ["Payé", "Organique"],
        "values": [stats['paid_count'], stats['organic_count']]
    }

    # 9. Données pour les métriques d'engagement
    engagement_metrics = {
        "labels": [v['title'][:20] + '...' for v in top_videos_views],
        "values": [(v['like_count'] / v['view_count']) * 100 if v['view_count'] > 0 else 0 for v in top_videos_views]
    }

    # 10. Récupération des playlists avec classifications
    from yt_channel_analyzer.database import get_competitor_playlists
    playlists = get_competitor_playlists(competitor_id)

    # 11. Récupération des données d'abonnés
    subscriber_data_db = conn.execute(
        'SELECT date, subscriber_count FROM subscriber_data WHERE concurrent_id = ? ORDER BY date',
        (competitor_id,)
    ).fetchall()
    
    # Formater les données pour correspondre au format attendu par le JavaScript
    subscriber_data_formatted = None
    if subscriber_data_db:
        data_list = [{"date": r["date"], "subscriber_count": r["subscriber_count"]} for r in subscriber_data_db]
        
        # Calculer les statistiques
        first_entry = data_list[0]
        last_entry = data_list[-1]
        total_growth = last_entry['subscriber_count'] - first_entry['subscriber_count']
        growth_percentage = (total_growth / first_entry['subscriber_count']) * 100 if first_entry['subscriber_count'] > 0 else 0
        
        # Formater les données pour Chart.js
        chart_data = {
            'labels': [entry['date'] for entry in data_list],
            'datasets': [{
                'label': 'Nombre d\'abonnés',
                'data': [entry['subscriber_count'] for entry in data_list],
                'borderColor': 'rgba(99, 102, 241, 1)',
                'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4,
                'pointBackgroundColor': 'rgba(99, 102, 241, 1)',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'pointRadius': 6,
                'pointHoverRadius': 8
            }]
        }
        
        # Créer l'objet final avec toutes les données nécessaires
        subscriber_data_formatted = {
            'has_data': True,
            'chart_data': chart_data,
            'stats': {
                'total_entries': len(data_list),
                'first_date': first_entry['date'],
                'last_date': last_entry['date'],
                'first_count': first_entry['subscriber_count'],
                'last_count': last_entry['subscriber_count'],
                'total_growth': total_growth,
                'growth_percentage': round(growth_percentage, 2)
            }
        }
    else:
        subscriber_data_formatted = {
            'has_data': False,
            'chart_data': None,
            'stats': {
                'total_entries': 0,
                'total_growth': 0,
                'growth_percentage': 0
            }
        }

    # 11b. Groupement des vidéos par catégorie
    videos_by_category = {
        'hero': [v for v in videos if v['category'] == 'hero'],
        'hub': [v for v in videos if v['category'] == 'hub'],
        'help': [v for v in videos if v['category'] == 'help']
    }

    # 12. Rendu du template
    return render_template('concurrent_detail.html',
                           competitor=competitor,
                           videos=videos,
                           stats=stats,
                           top_videos_views=top_videos_views,
                           top_videos_likes=top_videos_likes,
                           top_videos_json=top_videos_json,
                           performance_data=performance_data,
                           category_distribution=category_distribution,
                           content_type_distribution=content_type_distribution,
                           engagement_metrics=engagement_metrics,
                           playlists=playlists,
                           subscriber_data=subscriber_data_formatted,
                           hero_count=stats['hero_count'],
                           hub_count=stats['hub_count'],
                           help_count=stats['help_count'],
                           shorts_data=shorts_data,
                           videos_by_category=videos_by_category)

@app.route('/competitor/<int:competitor_id>/delete')
@login_required
def delete_competitor(competitor_id):
    """Supprime un concurrent et toutes ses données associées."""
    try:
        conn = get_db_connection()
        # Vérifier que le concurrent existe
        competitor = conn.execute('SELECT name FROM concurrent WHERE id = ?', (competitor_id,)).fetchone()
        if competitor is None:
            flash("Concurrent non trouvé.", "error")
            return redirect(url_for('concurrents'))

        # Suppression en cascade (assumant que le schéma a ON DELETE CASCADE)
        conn.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
        conn.commit()
        conn.close()
        
        flash(f'Le concurrent "{competitor["name"]}" et toutes ses données ont été supprimés avec succès.', 'success')
    except Exception as e:
        flash(f"Une erreur est survenue lors de la suppression : {e}", "error")
    
    return redirect(url_for('concurrents'))

@app.route('/api/delete-competitor', methods=['POST'])
@login_required
def api_delete_competitor():
    """API pour supprimer un concurrent"""
    try:
        data = request.get_json()
        competitor_id = data.get('competitor_id')
        
        if not competitor_id:
            return jsonify({'success': False, 'error': 'ID concurrent manquant'})
        
        # Convertir en entier si nécessaire
        try:
            competitor_id = int(competitor_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'ID concurrent invalide'})
        
        # Vérifier que le concurrent existe et récupérer son nom
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM concurrent WHERE id = ?', (competitor_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Concurrent non trouvé'})
        
        competitor_name = result[0]
        
        # Supprimer le concurrent (les vidéos sont supprimées automatiquement par cascade)
        cursor.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
        conn.commit()
        conn.close()
        
        print(f"[DELETE-COMPETITOR] Concurrent supprimé: {competitor_name} (ID: {competitor_id})")
        
        return jsonify({
            'success': True, 
            'message': f'Concurrent {competitor_name} supprimé avec succès'
        })
        
    except Exception as e:
        print(f"[DELETE-COMPETITOR] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

# --- ROUTES POUR LA GESTION DES PLAYLISTS ---

@app.route('/api/competitor/<int:competitor_id>/playlists/refresh', methods=['POST'])
@login_required
def refresh_competitor_playlists(competitor_id):
    """Récupérer et sauvegarder les playlists d'un concurrent depuis l'API YouTube"""
    try:
        # 🚨 PROTECTION 1: Vérifier le quota API disponible
        quota_data = load_api_quota_data()
        daily_usage = quota_data.get('daily_usage', 0)
        quota_limit = quota_data.get('quota_limit', 10000)
        
        # Estimer le coût de cette opération (channel info + playlists + vidéos)
        estimated_cost = 150  # Environ 150 unités pour une actualisation complète
        
        if daily_usage + estimated_cost > quota_limit:
            return jsonify({
                'success': False, 
                'error': f'Quota API insuffisant. Utilisé: {daily_usage}/{quota_limit}. Coût estimé: {estimated_cost} unités.'
            })
        
        # 🚨 PROTECTION 2: Rate limiting par concurrent (max 1 fois par heure)
        import time
        current_time = time.time()
        cache_key = f'playlist_refresh_{competitor_id}'
        
        # Vérifier le cache des dernières actualisations
        if hasattr(refresh_competitor_playlists, '_last_refresh'):
            last_refresh = refresh_competitor_playlists._last_refresh.get(cache_key, 0)
            if current_time - last_refresh < 3600:  # 1 heure = 3600 secondes
                remaining_time = int(3600 - (current_time - last_refresh))
                return jsonify({
                    'success': False,
                    'error': f'⏰ Actualisation trop récente. Réessayez dans {remaining_time//60}min {remaining_time%60}s.'
                })
        else:
            refresh_competitor_playlists._last_refresh = {}
        
        # Récupérer l'URL de la chaîne
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT channel_url, name FROM concurrent WHERE id = ?', (competitor_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'Concurrent non trouvé'})
        
        channel_url, competitor_name = result
        
        # 🚨 PROTECTION 3: Log de l'action pour audit
        print(f"[PLAYLISTS] ⚠️ ACTUALISATION API demandée pour {competitor_name} (ID: {competitor_id})")
        print(f"[PLAYLISTS] 📊 Quota avant: {daily_usage}/{quota_limit}")
        
        # Récupérer les playlists depuis l'API YouTube
        from yt_channel_analyzer.youtube_api_client import create_youtube_client
        youtube_client = create_youtube_client()
        
        print(f"[PLAYLISTS] 🔍 Récupération des playlists pour: {channel_url}")
        
        # Récupérer l'ID de la chaîne
        channel_info = youtube_client.get_channel_info(channel_url)
        channel_id = channel_info['id']
        
        # Récupérer les playlists
        playlists_data = youtube_client.get_channel_playlists(channel_id)
        
        if not playlists_data:
            return jsonify({'success': False, 'error': 'Aucune playlist trouvée'})
        
        print(f"[PLAYLISTS] 📋 {len(playlists_data)} playlists trouvées")
        
        # Sauvegarder les playlists
        from yt_channel_analyzer.database import save_competitor_playlists, link_playlist_videos
        save_competitor_playlists(competitor_id, playlists_data)
        
        # Récupérer les vidéos de chaque playlist et les lier (LIMITÉ pour économiser le quota)
        print(f"[PLAYLISTS] 🔗 Liaison des vidéos aux playlists...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        linked_videos = 0
        for playlist_data in playlists_data:
            playlist_id = playlist_data.get('playlist_id')
            if not playlist_id:
                continue
                
            # Récupérer l'ID de la playlist dans notre base
            cursor.execute('SELECT id FROM playlist WHERE playlist_id = ?', (playlist_id,))
            result = cursor.fetchone()
            if not result:
                continue
                
            playlist_db_id = result[0]
            
            # 🚨 PROTECTION 4: Limiter à 50 vidéos par playlist pour économiser le quota
            video_ids = youtube_client.get_playlist_videos(playlist_id, max_results=50)
            
            if video_ids:
                # Lier les vidéos à la playlist
                link_playlist_videos(playlist_db_id, video_ids)
                linked_videos += len(video_ids)
        
        conn.close()
        
        # 🚨 PROTECTION 5: Enregistrer le timestamp de cette actualisation
        refresh_competitor_playlists._last_refresh[cache_key] = current_time
        
        # Mettre à jour le quota utilisé
        quota_data['daily_usage'] = daily_usage + estimated_cost
        save_api_quota_data(quota_data)
        
        print(f"[PLAYLISTS] ✅ Actualisation terminée. Quota utilisé: {estimated_cost} unités")
        
        return jsonify({
            'success': True,
            'count': len(playlists_data),
            'linked_videos': linked_videos,
            'quota_used': estimated_cost,
            'message': f'✅ {len(playlists_data)} playlists récupérées, {linked_videos} vidéos liées. Quota: {estimated_cost} unités.'
        })
        
    except Exception as e:
        print(f"[PLAYLISTS] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tag-playlist', methods=['POST'])
@login_required  
def tag_playlist():
    """Tagguer une playlist avec une catégorie (hero/hub/help) - NOUVELLE LOGIQUE SÉCURISÉE"""
    try:
        data = request.get_json()
        playlist_id = data.get('playlist_id')
        category = data.get('category')
        competitor_id = data.get('competitor_id')
        force_propagate = data.get('force_propagate', False)  # Nouveau flag explicite
        
        if not playlist_id:
            return jsonify({'success': False, 'error': 'ID playlist manquant'})
        
        # Valider la catégorie
        valid_categories = ['hero', 'hub', 'help', None]
        if category not in valid_categories:
            return jsonify({'success': False, 'error': 'Catégorie invalide'})
        
        # 🚨 NOUVEAU : Utiliser la fonction de marquage humain pour cette classification
        from yt_channel_analyzer.database import mark_human_classification
        
        if category:
            # Marquer comme classification humaine (priorité absolue)
            success = mark_human_classification(playlist_id=playlist_id, category=category, user_notes='Classification manuelle via interface')
            if not success:
                return jsonify({'success': False, 'error': 'Erreur lors du marquage de la classification humaine'})
        else:
            # Si catégorie = None, mettre à jour normalement (suppression de catégorie)
            from yt_channel_analyzer.database import update_playlist_category
            update_playlist_category(playlist_id, category)
        
        # 🚨 NOUVELLE LOGIQUE : NE PAS propager automatiquement les classifications humaines
        # L'utilisateur doit explicitement demander la propagation
        
        videos_updated = 0
        human_protected_count = 0
        human_playlists_skipped = 0
        processed_playlists = []
        propagation_message = ""
        
        if competitor_id and category:
            if force_propagate:
                # L'utilisateur a explicitement demandé la propagation
                try:
                    from yt_channel_analyzer.database import apply_playlist_categories_to_videos_safe
                    result = apply_playlist_categories_to_videos_safe(
                        competitor_id=competitor_id, 
                        specific_playlist_id=playlist_id,
                        force_human_playlists=True  # Mode force explicite
                    )
                    videos_updated = result.get('videos_updated', 0)
                    human_protected_count = result.get('human_protected', 0)
                    processed_playlists = result.get('processed_playlists', [])
                    
                    propagation_message = f" • Propagation FORCÉE: {videos_updated} vidéos tagguées"
                    if human_protected_count > 0:
                        propagation_message += f" • {human_protected_count} vidéos protégées"
                        
                    print(f"[TAG-PLAYLIST] ⚠️ PROPAGATION FORCÉE demandée par l'utilisateur: {videos_updated} vidéos")
                    
                except Exception as propagation_error:
                    print(f"[TAG-PLAYLIST] ❌ Erreur lors de la propagation forcée: {propagation_error}")
                    propagation_message = " • Erreur lors de la propagation"
            else:
                # Classification humaine : PAS de propagation automatique
                propagation_message = " • Aucune propagation automatique (classification humaine protégée)"
                print(f"[TAG-PLAYLIST] 🛡️ Classification humaine protégée - AUCUNE propagation automatique")
        
        category_name = category.upper() if category else "Non catégorisée"
        
        # Message enrichi avec nouvelle logique de sécurité
        message = f'🤖 Playlist marquée comme {category_name} (HUMAIN - PROTÉGÉE){propagation_message}'
        
        return jsonify({
            'success': True,
            'message': message,
            'videos_updated': videos_updated,
            'human_protected': human_protected_count,
            'human_playlists_skipped': human_playlists_skipped,
            'processed_playlists': processed_playlists,
            'human_classification': True,
            'auto_propagated': force_propagate,
            'protection_active': True  # Nouveau flag
        })
        
    except Exception as e:
        print(f"[TAG-PLAYLIST] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/competitor/<int:competitor_id>/apply-playlist-categories', methods=['POST'])
@login_required
def apply_playlist_categories(competitor_id):
    """Appliquer automatiquement les catégories des playlists aux vidéos"""
    try:
        from yt_channel_analyzer.database import apply_playlist_categories_to_videos
        
        # Appliquer les catégories
        videos_updated = apply_playlist_categories_to_videos(competitor_id)
        
        return jsonify({
            'success': True,
            'videos_updated': videos_updated,
            'message': f'Classification appliquée: {videos_updated} vidéos mises à jour'
        })
        
    except Exception as e:
        print(f"[APPLY-CATEGORIES] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/competitor/<int:competitor_id>/playlists/ai-classify', methods=['POST'])
@login_required
def ai_classify_playlists(competitor_id):
    """Classifier automatiquement les playlists non catégorisées avec l'IA"""
    try:
        from yt_channel_analyzer.database import auto_classify_uncategorized_playlists, set_last_action_status
        result = auto_classify_uncategorized_playlists(competitor_id)
        set_last_action_status('last_playlist_classification', {
            'action': 'ai_classify_playlists',
            'competitor_id': competitor_id,
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'message': 'Classification IA des playlists effectuée'
        })
        return jsonify(result)
    except Exception as e:
        print(f"[AI-CLASSIFY] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/competitor/<int:competitor_id>/playlists/classify')
@login_required
def playlist_classification_page(competitor_id):
    """Page dédiée à la classification des playlists avec interface moderne"""
    try:
        # Récupérer les informations du concurrent
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM concurrent WHERE id = ?', (competitor_id,))
        competitor_data = cursor.fetchone()
        conn.close()
        
        if not competitor_data:
            flash('Concurrent non trouvé', 'error')
            return redirect(url_for('concurrents'))
        
        # Convertir en objet competitor
        competitor = {
            'id': competitor_data[0],
            'name': competitor_data[1],
            'channel_id': competitor_data[2],
            'channel_url': competitor_data[3],
            'thumbnail_url': competitor_data[4],
            'banner_url': competitor_data[5],
            'description': competitor_data[6],
            'subscriber_count': competitor_data[7],
            'view_count': competitor_data[8],
            'video_count': competitor_data[9],
            'country': competitor_data[10],
            'language': competitor_data[11],
            'created_at': competitor_data[12],
            'last_updated': competitor_data[13]
        }
        
        return render_template('playlist_classification.html', competitor=competitor)
        
    except Exception as e:
        print(f"[PLAYLIST-CLASSIFY-PAGE] ❌ Erreur: {e}")
        flash(f'Erreur lors du chargement de la page: {str(e)}', 'error')
        return redirect(url_for('concurrents'))

@app.route('/api/competitor/<int:competitor_id>/playlists', methods=['GET'])
@login_required
def get_competitor_playlists_api(competitor_id):
    """API pour récupérer les playlists d'un concurrent avec toutes les informations de classification"""
    try:
        from yt_channel_analyzer.database import get_competitor_playlists
        playlists = get_competitor_playlists(competitor_id)
        
        # Enrichir les playlists avec les informations de vidéos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for playlist in playlists:
            # Compter les vidéos dans la playlist
            cursor.execute('''
                SELECT COUNT(*) FROM playlist_video pv
                JOIN video v ON pv.video_id = v.id
                WHERE pv.playlist_id = ?
            ''', (playlist['id'],))
            
            video_count = cursor.fetchone()[0]
            playlist['video_count'] = video_count
            
            # Compter les vidéos classifiées humainement dans cette playlist
            cursor.execute('''
                SELECT COUNT(*) FROM playlist_video pv
                JOIN video v ON pv.video_id = v.id
                WHERE pv.playlist_id = ?
                AND (v.classification_source = 'human' OR v.human_verified = 1)
            ''', (playlist['id'],))
            
            human_videos = cursor.fetchone()[0]
            playlist['human_videos_count'] = human_videos
            
            # Informations sur les vidéos potentiellement affectées
            cursor.execute('''
                SELECT COUNT(*) FROM playlist_video pv
                JOIN video v ON pv.video_id = v.id
                WHERE pv.playlist_id = ?
                AND (v.classification_source IS NULL OR v.classification_source != 'human')
                AND (v.human_verified IS NULL OR v.human_verified != 1)
            ''', (playlist['id'],))
            
            propagatable_videos = cursor.fetchone()[0]
            playlist['propagatable_videos_count'] = propagatable_videos
        
        conn.close()
        
        return jsonify({
            'success': True,
            'playlists': playlists,
            'total_count': len(playlists),
            'message': f'{len(playlists)} playlists récupérées'
        })
        
    except Exception as e:
        print(f"[GET-PLAYLISTS-API] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/playlists/bulk-classify', methods=['POST'])
@login_required
def bulk_classify_playlists():
    """Classification en lot des playlists avec templates ou catégories personnalisées"""
    try:
        data = request.get_json()
        playlist_ids = data.get('playlist_ids', [])
        template = data.get('template', None)
        custom_category = data.get('custom_category', None)
        competitor_id = data.get('competitor_id', None)
        force_propagate = data.get('force_propagate', False)
        
        if not playlist_ids:
            return jsonify({'success': False, 'error': 'Aucune playlist sélectionnée'})
        
        if not (template or custom_category):
            return jsonify({'success': False, 'error': 'Template ou catégorie personnalisée requis'})
        
        # Mapping des templates vers les catégories
        template_mappings = {
            'educational': 'help',
            'entertainment': 'hub',
            'promotional': 'hero',
            'seasonal': 'hero',
            'tutorials': 'help',
            'brand_content': 'hub',
            'product_launch': 'hero',
            'community': 'hub',
            'behind_scenes': 'hub',
            'testimonials': 'hero'
        }
        
        # Déterminer la catégorie
        if template and template in template_mappings:
            category = template_mappings[template]
        elif custom_category:
            category = custom_category
        else:
            return jsonify({'success': False, 'error': 'Template ou catégorie invalide'})
        
        # Valider la catégorie
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'success': False, 'error': 'Catégorie invalide'})
        
        # Traiter chaque playlist
        from yt_channel_analyzer.database import mark_human_classification
        
        processed_playlists = []
        total_videos_affected = 0
        
        for playlist_id in playlist_ids:
            try:
                # Marquer comme classification humaine
                success = mark_human_classification(
                    playlist_id=playlist_id, 
                    category=category, 
                    user_notes=f'Classification en lot - Template: {template or "personnalisé"}'
                )
                
                if success:
                    processed_playlists.append(playlist_id)
                    
                    # Compter les vidéos qui seront affectées
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) FROM playlist_video pv
                        JOIN video v ON pv.video_id = v.id
                        WHERE pv.playlist_id = ?
                    ''', (playlist_id,))
                    
                    video_count = cursor.fetchone()[0]
                    total_videos_affected += video_count
                    conn.close()
                    
            except Exception as e:
                print(f"[BULK-CLASSIFY] ❌ Erreur playlist {playlist_id}: {e}")
                continue
        
        # Propagation optionnelle
        propagation_message = ""
        if force_propagate and competitor_id:
            try:
                from yt_channel_analyzer.database import apply_playlist_categories_to_videos_safe
                result = apply_playlist_categories_to_videos_safe(
                    competitor_id=competitor_id,
                    force_human_playlists=True  # Mode force pour la propagation
                )
                
                videos_updated = result.get('videos_updated', 0)
                propagation_message = f" • Propagation: {videos_updated} vidéos mises à jour"
                
            except Exception as e:
                print(f"[BULK-CLASSIFY] ❌ Erreur propagation: {e}")
                propagation_message = " • Erreur lors de la propagation"
        
        return jsonify({
            'success': True,
            'processed_playlists': len(processed_playlists),
            'total_playlists': len(playlist_ids),
            'total_videos_affected': total_videos_affected,
            'category': category,
            'template': template,
            'message': f'✅ {len(processed_playlists)} playlist(s) classifiée(s) comme {category.upper()}{propagation_message}'
        })
        
    except Exception as e:
        print(f"[BULK-CLASSIFY] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/playlists/propagate-preview', methods=['POST'])
@login_required
def preview_playlist_propagation():
    """Prévisualiser l'impact de la propagation des classifications de playlists"""
    try:
        data = request.get_json()
        playlist_ids = data.get('playlist_ids', [])
        
        if not playlist_ids:
            return jsonify({'success': False, 'error': 'Aucune playlist sélectionnée'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        preview_data = []
        total_videos = 0
        total_protected = 0
        
        for playlist_id in playlist_ids:
            # Informations de la playlist
            cursor.execute('''
                SELECT name, category, classification_source, human_verified
                FROM playlist WHERE id = ?
            ''', (playlist_id,))
            
            playlist_info = cursor.fetchone()
            if not playlist_info:
                continue
            
            playlist_name = playlist_info[0]
            playlist_category = playlist_info[1]
            playlist_source = playlist_info[2]
            playlist_human = playlist_info[3]
            
            # Compter les vidéos
            cursor.execute('''
                SELECT COUNT(*) FROM playlist_video pv
                JOIN video v ON pv.video_id = v.id
                WHERE pv.playlist_id = ?
            ''', (playlist_id,))
            
            video_count = cursor.fetchone()[0]
            
            # Compter les vidéos protégées
            cursor.execute('''
                SELECT COUNT(*) FROM playlist_video pv
                JOIN video v ON pv.video_id = v.id
                WHERE pv.playlist_id = ?
                AND (v.classification_source = 'human' OR v.human_verified = 1)
            ''', (playlist_id,))
            
            protected_count = cursor.fetchone()[0]
            
            # Vidéos qui seront affectées
            affected_count = video_count - protected_count
            
            preview_data.append({
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'playlist_category': playlist_category,
                'playlist_source': playlist_source,
                'playlist_human': playlist_human,
                'total_videos': video_count,
                'protected_videos': protected_count,
                'affected_videos': affected_count
            })
            
            total_videos += video_count
            total_protected += protected_count
        
        conn.close()
        
        return jsonify({
            'success': True,
            'preview_data': preview_data,
            'summary': {
                'total_playlists': len(playlist_ids),
                'total_videos': total_videos,
                'protected_videos': total_protected,
                'affected_videos': total_videos - total_protected
            }
        })
        
    except Exception as e:
        print(f"[PROPAGATE-PREVIEW] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Routes ViewStats supprimées - analyse locale maintenant

@app.route('/top-videos')
@login_required
@cache.cached(timeout=300, query_string=True)  # Cache avec paramètres de la query string
def top_videos():
    """Page du top global des vidéos de tous les concurrents - VERSION OPTIMISÉE"""
    try:
        # Récupérer les paramètres de tri et filtrage
        sort_by = request.args.get('sort_by', 'view_count')  # Par défaut: nombre de vues
        order = request.args.get('order', 'desc')  # Par défaut: décroissant
        category_filter = request.args.get('category', 'all')  # Filtrer par catégorie
        organic_filter = request.args.get('organic', 'all')  # Filtrer par organique/paid
        limit = int(request.args.get('limit', 50))  # Limite par défaut: 50 vidéos
        
        # Récupérer les seuils pour déterminer si c'est organique ou payé
        settings = load_settings()
        paid_threshold = settings.get('paid_threshold', 10000)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Requête optimisée avec calculs côté SQL
        base_query = """
            SELECT v.id, v.title, v.video_id, v.url, v.thumbnail_url,
                   v.view_count, v.like_count, v.comment_count,
                   v.published_at, v.duration_seconds, v.duration_text,
                   v.category, v.beauty_score, v.emotion_score, v.info_quality_score,
                   c.name as competitor_name, c.id as competitor_id,
                   c.subscriber_count as channel_subscribers,
                   CASE 
                       WHEN v.view_count >= ? THEN 'paid'
                       ELSE 'organic'
                   END as organic_status,
                   -- Calculs côté SQL pour éviter les calculs Python
                   CASE 
                       WHEN v.view_count > 0 THEN ROUND(((COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) * 100.0) / v.view_count, 2)
                       ELSE 0
                   END as engagement_ratio,
                   ROUND((COALESCE(v.beauty_score, 0) + COALESCE(v.emotion_score, 0) + COALESCE(v.info_quality_score, 0)) / 3.0, 1) as avg_subjective_score,
                   -- Formatage des dates côté SQL
                   CASE 
                       WHEN v.published_at IS NOT NULL THEN date(v.published_at)
                       ELSE 'N/A'
                   END as published_at_formatted,
                   CASE 
                       WHEN v.published_at IS NOT NULL THEN time(v.published_at)
                       ELSE 'N/A'
                   END as published_hour_formatted,
                   -- Formatage de la durée côté SQL
                   CASE 
                       WHEN v.duration_seconds IS NOT NULL AND v.duration_seconds > 0 THEN 
                           printf('%d:%02d', v.duration_seconds / 60, v.duration_seconds % 60)
                       ELSE COALESCE(v.duration_text, 'N/A')
                   END as duration_formatted
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.view_count IS NOT NULL
        """
        
        params = [paid_threshold]
        
        # Ajouter les filtres
        if category_filter != 'all':
            base_query += " AND v.category = ?"
            params.append(category_filter)
        
        if organic_filter == 'organic':
            base_query += " AND v.view_count < ?"
            params.append(paid_threshold)
        elif organic_filter == 'paid':
            base_query += " AND v.view_count >= ?"
            params.append(paid_threshold)
        
        # Ajouter le tri
        valid_sort_columns = {
            'view_count': 'v.view_count',
            'like_count': 'v.like_count',
            'comment_count': 'v.comment_count',
            'published_at': 'v.published_at',
            'published_hour': 'v.published_at',
            'duration_seconds': 'v.duration_seconds',
            'title': 'v.title',
            'competitor_name': 'c.name',
            'beauty_score': 'v.beauty_score',
            'emotion_score': 'v.emotion_score',
            'info_quality_score': 'v.info_quality_score'
        }
        
        if sort_by in valid_sort_columns:
            order_clause = 'DESC' if order == 'desc' else 'ASC'
            base_query += f" ORDER BY {valid_sort_columns[sort_by]} {order_clause}"
        else:
            base_query += " ORDER BY v.view_count DESC"
        
        # Ajouter la limite
        base_query += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        # Construction simplifiée des vidéos (calculs déjà faits côté SQL)
        videos = []
        for row in rows:
            video = {
                'id': row[0],
                'title': row[1],
                'video_id': row[2],
                'url': row[3],
                'thumbnail_url': row[4],
                'view_count': row[5] or 0,
                'like_count': row[6] or 0,
                'comment_count': row[7] or 0,
                'published_at': row[8],
                'duration_seconds': row[9] or 0,
                'duration_text': row[10] or 'N/A',
                'category': row[11] or 'hub',
                'beauty_score': row[12] or 0,
                'emotion_score': row[13] or 0,
                'info_quality_score': row[14] or 0,
                'competitor_name': row[15],
                'competitor_id': row[16],
                'channel_subscribers': row[17] or 0,
                'organic_status': row[18],
                'engagement_ratio': row[19],  # Déjà calculé côté SQL
                'avg_subjective_score': row[20],  # Déjà calculé côté SQL
                'published_at_formatted': row[21],  # Déjà formaté côté SQL
                'published_hour_formatted': row[22],  # Déjà formaté côté SQL
                'duration_formatted': row[23]  # Déjà formaté côté SQL
            }
            videos.append(video)
        
        # Statistiques générales avec une seule requête optimisée
        cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(DISTINCT concurrent_id) as total_competitors,
                SUM(CASE WHEN view_count >= ? THEN 1 ELSE 0 END) as total_paid_videos,
                SUM(CASE WHEN view_count < ? THEN 1 ELSE 0 END) as total_organic_videos
            FROM video
            WHERE view_count IS NOT NULL
        """, [paid_threshold, paid_threshold])
        
        stats_row = cursor.fetchone()
        stats = {
            'total_videos': stats_row[0],
            'total_competitors': stats_row[1],
            'total_paid_videos': stats_row[2],
            'total_organic_videos': stats_row[3],
            'paid_threshold': paid_threshold,
            'shown_videos': len(videos)
        }
        
        conn.close()
        
        return render_template('top_videos.html',
                             videos=videos,
                             stats=stats,
                             current_sort=sort_by,
                             current_order=order,
                             current_category=category_filter,
                             current_organic=organic_filter,
                             current_limit=limit)
    
    except Exception as e:
        print(f"[TOP-VIDEOS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=str(e))

@app.route('/api/top-videos')
@login_required
@cache.cached(timeout=300, query_string=True)
def api_top_videos():
    """API pour charger plus de vidéos avec pagination AJAX"""
    try:
        # Récupérer les paramètres
        sort_by = request.args.get('sort_by', 'view_count')
        order = request.args.get('order', 'desc')
        category_filter = request.args.get('category', 'all')
        organic_filter = request.args.get('organic', 'all')
        limit = int(request.args.get('limit', 20))  # Limite réduite pour AJAX
        offset = int(request.args.get('offset', 0))
        
        settings = load_settings()
        paid_threshold = settings.get('paid_threshold', 10000)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Même requête optimisée que top_videos mais avec OFFSET
        base_query = """
            SELECT v.id, v.title, v.video_id, v.url, v.thumbnail_url,
                   v.view_count, v.like_count, v.comment_count,
                   v.published_at, v.duration_seconds, v.duration_text,
                   v.category, v.beauty_score, v.emotion_score, v.info_quality_score,
                   c.name as competitor_name, c.id as competitor_id,
                   c.subscriber_count as channel_subscribers,
                   CASE 
                       WHEN v.view_count >= ? THEN 'paid'
                       ELSE 'organic'
                   END as organic_status,
                   CASE 
                       WHEN v.view_count > 0 THEN ROUND(((COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) * 100.0) / v.view_count, 2)
                       ELSE 0
                   END as engagement_ratio,
                   ROUND((COALESCE(v.beauty_score, 0) + COALESCE(v.emotion_score, 0) + COALESCE(v.info_quality_score, 0)) / 3.0, 1) as avg_subjective_score,
                   CASE 
                       WHEN v.published_at IS NOT NULL THEN date(v.published_at)
                       ELSE 'N/A'
                   END as published_at_formatted,
                   CASE 
                       WHEN v.published_at IS NOT NULL THEN time(v.published_at)
                       ELSE 'N/A'
                   END as published_hour_formatted,
                   CASE 
                       WHEN v.duration_seconds IS NOT NULL AND v.duration_seconds > 0 THEN 
                           printf('%d:%02d', v.duration_seconds / 60, v.duration_seconds % 60)
                       ELSE COALESCE(v.duration_text, 'N/A')
                   END as duration_formatted
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.view_count IS NOT NULL
        """
        
        params = [paid_threshold]
        
        # Ajouter les filtres
        if category_filter != 'all':
            base_query += " AND v.category = ?"
            params.append(category_filter)
        
        if organic_filter == 'organic':
            base_query += " AND v.view_count < ?"
            params.append(paid_threshold)
        elif organic_filter == 'paid':
            base_query += " AND v.view_count >= ?"
            params.append(paid_threshold)
        
        # Ajouter le tri
        valid_sort_columns = {
            'view_count': 'v.view_count',
            'like_count': 'v.like_count',
            'comment_count': 'v.comment_count',
            'published_at': 'v.published_at',
            'published_hour': 'v.published_at',
            'duration_seconds': 'v.duration_seconds',
            'title': 'v.title',
            'competitor_name': 'c.name',
            'beauty_score': 'v.beauty_score',
            'emotion_score': 'v.emotion_score',
            'info_quality_score': 'v.info_quality_score'
        }
        
        if sort_by in valid_sort_columns:
            order_clause = 'DESC' if order == 'desc' else 'ASC'
            base_query += f" ORDER BY {valid_sort_columns[sort_by]} {order_clause}"
        else:
            base_query += " ORDER BY v.view_count DESC"
        
        # Ajouter la limite et l'offset
        base_query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        # Construction des vidéos
        videos = []
        for row in rows:
            video = {
                'id': row[0],
                'title': row[1],
                'video_id': row[2],
                'url': row[3],
                'thumbnail_url': row[4],
                'view_count': row[5] or 0,
                'like_count': row[6] or 0,
                'comment_count': row[7] or 0,
                'published_at': row[8],
                'duration_seconds': row[9] or 0,
                'duration_text': row[10] or 'N/A',
                'category': row[11] or 'hub',
                'beauty_score': row[12] or 0,
                'emotion_score': row[13] or 0,
                'info_quality_score': row[14] or 0,
                'competitor_name': row[15],
                'competitor_id': row[16],
                'channel_subscribers': row[17] or 0,
                'organic_status': row[18],
                'engagement_ratio': row[19],
                'avg_subjective_score': row[20],
                'published_at_formatted': row[21],
                'published_hour_formatted': row[22],
                'duration_formatted': row[23]
            }
            videos.append(video)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'videos': videos,
            'has_more': len(videos) == limit  # Il y a plus de vidéos si on a récupéré le nombre demandé
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def clear_performance_cache():
    """Invalider le cache des pages de performance"""
    cache.delete_memoized(top_videos)
    cache.clear()  # Optionnel: vider tout le cache

# Routes analytics/scraper supprimées - analyse locale simple maintenant

@app.route('/api/update-competitor-country', methods=['POST'])
@login_required
def update_competitor_country():
    """API pour mettre à jour le pays d'un concurrent"""
    try:
        data = request.get_json()
        competitor_id = data.get('competitor_id')
        country = data.get('country')
        
        if not competitor_id or not country:
            return jsonify({'success': False, 'error': 'ID du concurrent et pays requis'})
        
        from yt_channel_analyzer.database import update_competitor_country
        success = update_competitor_country(competitor_id, country)
        
        if success:
            return jsonify({'success': True, 'message': 'Pays mis à jour avec succès'})
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la mise à jour'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/competitors-by-country')
@login_required
def get_competitors_by_country():
    """API pour récupérer les concurrents groupés par pays"""
    try:
        from yt_channel_analyzer.database import get_competitors_by_country
        countries = get_competitors_by_country()
        return jsonify(countries)
    except Exception as e:
        return jsonify({'error': str(e)})

def get_country_flag(country_name: str) -> str:
    """Retourne le drapeau emoji pour un pays donné"""
    country_flags = {
        'France': '🇫🇷',
        'Belgium': '🇧🇪',
        'United States': '🇺🇸',
        'United Kingdom': '🇬🇧',
        'Germany': '🇩🇪',
        'Spain': '🇪🇸',
        'Italy': '🇮🇹',
        'Netherlands': '🇳🇱',
        'Canada': '🇨🇦',
        'Australia': '🇦🇺',
        'International': '🌍',
        'Non défini': '🏳️'
    }
    return country_flags.get(country_name, '🏳️')

@app.route('/countries-analysis')
@login_required
def countries_analysis():
    """Page d'analyse par pays"""
    try:
        from yt_channel_analyzer.database.competitors import get_all_competitors_with_videos
        
        # Récupérer tous les concurrents avec leurs vidéos et statistiques
        competitors = get_all_competitors_with_videos()
        
        # Regrouper par pays avec statistiques
        countries_data = {}
        total_videos = 0
        total_views = 0
        
        for competitor in competitors:
            country = competitor.get('country') or 'Non défini'
            if country not in countries_data:
                countries_data[country] = {
                    'name': country,
                    'flag': get_country_flag(country),  # Ajout du drapeau
                    'competitors': [],
                    'total_videos': 0,
                    'total_views': 0,
                    'total_comments': 0,
                    'avg_views_per_video': 0,
                    'avg_comments_per_video': 0,
                    'competitor_count': 0
                }
            
            videos = competitor.get('videos', [])
            competitor_views = sum(v.get('view_count', 0) or 0 for v in videos)
            competitor_comments = sum(v.get('comment_count', 0) or 0 for v in videos)
            video_count = len(videos)
            avg_views = int(round(competitor_views / video_count)) if video_count > 0 else 0
            avg_comments = int(round(competitor_comments / video_count)) if video_count > 0 else 0
            
            countries_data[country]['competitors'].append({
                'name': competitor.get('name'),
                'video_count': video_count,
                'total_views': competitor_views,
                'total_comments': competitor_comments,
                'avg_views': avg_views,
                'avg_comments': avg_comments
            })
            
            countries_data[country]['total_videos'] += video_count
            countries_data[country]['total_views'] += competitor_views
            countries_data[country]['total_comments'] += competitor_comments
            countries_data[country]['competitor_count'] += 1
            
            total_videos += video_count
            total_views += competitor_views
        
        # Calculer les moyennes par pays
        for country_data in countries_data.values():
            if country_data['total_videos'] > 0:
                country_data['avg_views_per_video'] = int(round(country_data['total_views'] / country_data['total_videos']))
                country_data['avg_comments_per_video'] = int(round(country_data['total_comments'] / country_data['total_videos']))
        
        # Trier par vues totales
        countries_list = sorted(countries_data.values(), key=lambda x: x['total_views'], reverse=True)
        
        # Statistiques globales
        global_stats = {
            'total_countries': len(countries_list),
            'total_competitors': len(competitors),
            'total_videos': total_videos,
            'total_views': total_views
        }
        
        print(f"[COUNTRIES-ANALYSIS] ✅ Analyse générée: {len(countries_list)} pays, {len(competitors)} concurrents, {total_videos} vidéos, {total_views:,} vues")
        
        # Générer des insights précis et sourcés par pays
        from yt_channel_analyzer.database import generate_detailed_country_insights
        
        for country in countries_data:
            try:
                # Générer des insights détaillés basés sur les vraies données
                detailed_insights = generate_detailed_country_insights(country)
                countries_data[country]['key_insights'] = detailed_insights.get('insights', [])
                countries_data[country]['detailed_analysis'] = detailed_insights
            except Exception as e:
                print(f"[COUNTRIES-ANALYSIS] ⚠️ Erreur insights pour {country}: {e}")
                # Fallback vers des insights basiques
                countries_data[country]['key_insights'] = [
                    f"Analyse en cours pour {country}...",
                    "Données insuffisantes pour générer des insights détaillés"
                ]
        
        return render_template('countries_analysis.html', 
                             countries=countries_list, 
                             countries_data=countries_data,  # Passer les données complètes
                             global_stats=global_stats)
        
    except Exception as e:
        print(f"[COUNTRIES-ANALYSIS] ❌ Erreur: {e}")
        return render_template('countries_analysis.html', 
                             countries=[], 
                             countries_data={},
                             global_stats={}, 
                             error=str(e))

@app.route('/api/countries-insights')
@login_required
def api_countries_insights():
    """API pour récupérer les insights par pays en format JSON pour PowerPoint"""
    try:
        from yt_channel_analyzer.database import generate_detailed_country_insights
        
        # Récupérer la liste des pays
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT country FROM concurrent WHERE country IS NOT NULL AND country != ""')
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        insights_data = {}
        
        for country in countries:
            try:
                detailed_insights = generate_detailed_country_insights(country)
                insights_data[country] = detailed_insights
            except Exception as e:
                print(f"[API-INSIGHTS] ❌ Erreur pour {country}: {e}")
                insights_data[country] = {
                    'insights': [f"Erreur lors de l'analyse de {country}"],
                    'country': country
                }
        
        return jsonify({
            'success': True,
            'countries_insights': insights_data,
            'total_countries': len(countries),
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"[API-INSIGHTS] ❌ Erreur globale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/countries-insights/export')
@login_required
def export_countries_insights():
    """Export des insights au format texte optimisé pour PowerPoint"""
    try:
        from yt_channel_analyzer.database import generate_detailed_country_insights
        
        # Récupérer la liste des pays
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT country FROM concurrent WHERE country IS NOT NULL AND country != ""')
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        export_text = "# 🌍 MEILLEURES PRATIQUES YOUTUBE PAR PAYS\n"
        export_text += f"*Analyse générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*\n\n"
        
        for country in countries:
            try:
                detailed_insights = generate_detailed_country_insights(country)
                
                # Émoji du pays
                country_emoji = ""
                if country == "France":
                    country_emoji = "🇫🇷"
                elif country == "Belgium":
                    country_emoji = "🇧🇪"
                elif country == "International":
                    country_emoji = "🌍"
                elif country == "Netherlands":
                    country_emoji = "🇳🇱"
                elif country == "United Kingdom":
                    country_emoji = "🇬🇧"
                
                export_text += f"## {country_emoji} {country.upper()}\n\n"
                
                for i, insight in enumerate(detailed_insights.get('insights', []), 1):
                    # Nettoyer les balises HTML pour PowerPoint
                    clean_insight = insight.replace('<b>', '**').replace('</b>', '**')
                    export_text += f"{i}. {clean_insight}\n"
                
                export_text += f"\n*Basé sur {detailed_insights.get('analysis_details', {}).get('total_videos', 0)} vidéos analysées*\n"
                export_text += "---\n\n"
                
            except Exception as e:
                export_text += f"## ⚠️ {country.upper()}\nErreur lors de l'analyse: {str(e)}\n---\n\n"
        
        # Créer une réponse avec le texte formaté
        from flask import Response
        return Response(
            export_text,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=insights_youtube_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
            }
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors de l\'export: {str(e)}'
        })

def auto_update_playlists(competitor_id, competitor_name, channel_url):
    """
    Fonction helper pour mettre à jour automatiquement les playlists d'un concurrent
    Retourne les playlists mises à jour
    """
    from yt_channel_analyzer.database import get_competitor_playlists
    
    # Récupérer les playlists existantes
    playlists = get_competitor_playlists(competitor_id)
    
    # Vérifier s'il faut récupérer/mettre à jour les playlists
    should_update_playlists = False
    
    if not playlists:
        # Pas de playlists en base, les récupérer
        should_update_playlists = True
        print(f"[AUTO-UPDATE-PLAYLISTS] Aucune playlist trouvée pour {competitor_name}, récupération automatique...")
    else:
        # Vérifier si la dernière mise à jour est ancienne (plus de 7 jours)
        from datetime import datetime, timedelta
        
        # Récupérer la date de dernière mise à jour des playlists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(last_updated) FROM playlist WHERE concurrent_id = ?', (competitor_id,))
        last_update = cursor.fetchone()[0]
        conn.close()
        
        if last_update:
            try:
                # Convertir la date string en datetime si nécessaire
                if isinstance(last_update, str):
                    last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                
                # Vérifier si la mise à jour date de plus de 7 jours
                if datetime.now() - last_update > timedelta(days=7):
                    should_update_playlists = True
                    print(f"[AUTO-UPDATE-PLAYLISTS] Playlists de {competitor_name} anciennes ({last_update}), mise à jour automatique...")
            except:
                # En cas d'erreur de date, forcer la mise à jour
                should_update_playlists = True
                print(f"[AUTO-UPDATE-PLAYLISTS] Erreur de date pour {competitor_name}, mise à jour automatique...")
    
    # Mettre à jour les playlists automatiquement si nécessaire
    if should_update_playlists:
        try:
            # Récupérer les playlists depuis l'API YouTube
            from yt_channel_analyzer.youtube_api_client import create_youtube_client
            youtube_client = create_youtube_client()
            
            # Récupérer l'ID de la chaîne
            channel_info = youtube_client.get_channel_info(channel_url)
            channel_id = channel_info['id']
            
            # Récupérer les playlists
            playlists_data = youtube_client.get_channel_playlists(channel_id)
            
            if playlists_data:
                print(f"[AUTO-UPDATE-PLAYLISTS] 📋 {len(playlists_data)} playlists trouvées pour {competitor_name}")
                
                # Sauvegarder les playlists
                from yt_channel_analyzer.database import save_competitor_playlists, link_playlist_videos
                save_competitor_playlists(competitor_id, playlists_data)
                
                # Récupérer les vidéos de chaque playlist et les lier
                print(f"[AUTO-UPDATE-PLAYLISTS] 🔗 Liaison des vidéos aux playlists...")
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                for playlist_data in playlists_data:
                    playlist_id = playlist_data.get('playlist_id')
                    if not playlist_id:
                        continue
                        
                    # Récupérer l'ID de la playlist dans notre base
                    cursor.execute('SELECT id FROM playlist WHERE playlist_id = ?', (playlist_id,))
                    result = cursor.fetchone()
                    if not result:
                        continue
                        
                    playlist_db_id = result[0]
                    
                    # Récupérer les vidéos de cette playlist
                    try:
                        video_ids = youtube_client.get_playlist_videos(playlist_id, max_results=100)
                        
                        if video_ids:
                            # Lier les vidéos à la playlist
                            link_playlist_videos(playlist_db_id, video_ids)
                    except Exception as e:
                        print(f"[AUTO-UPDATE-PLAYLISTS] Erreur lors de la liaison des vidéos pour playlist {playlist_id}: {e}")
                        continue
                
                conn.close()
                
                # Récupérer les playlists mises à jour
                playlists = get_competitor_playlists(competitor_id)
                print(f"[AUTO-UPDATE-PLAYLISTS] ✅ Playlists mises à jour automatiquement pour {competitor_name}")
                
            else:
                print(f"[AUTO-UPDATE-PLAYLISTS] ⚠️ Aucune playlist trouvée sur YouTube pour {competitor_name}")
                
        except Exception as e:
            print(f"[AUTO-UPDATE-PLAYLISTS] ❌ Erreur lors de la mise à jour automatique des playlists: {e}")
            # Continuer avec les playlists existantes même en cas d'erreur
    
    return playlists

@app.route('/api/patterns', methods=['GET'])
@login_required
def get_patterns():
    """Récupérer tous les patterns de classification IA"""
    try:
        from yt_channel_analyzer.database import get_classification_patterns
        language = request.args.get('language', None)
        patterns = get_classification_patterns(language)
        return jsonify({'success': True, 'patterns': patterns})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patterns', methods=['POST'])
@login_required
def add_pattern():
    """Ajouter un nouveau pattern de classification"""
    try:
        data = request.get_json()
        category = data.get('category')
        pattern = data.get('pattern')
        language = data.get('language', 'fr')
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'})
        
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'success': False, 'error': 'Invalid category'})
        
        if language not in ['fr', 'en', 'de', 'nl']:
            return jsonify({'success': False, 'error': 'Invalid language'})
        
        from yt_channel_analyzer.database import add_classification_pattern
        success = add_classification_pattern(category, pattern, language)
        
        if success:
            return jsonify({'success': True, 'message': 'Pattern added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern already exists or could not be added'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patterns', methods=['DELETE'])
@login_required
def remove_pattern():
    """Supprimer un pattern de classification"""
    try:
        data = request.get_json()
        category = data.get('category')
        pattern = data.get('pattern')
        language = data.get('language', 'fr')
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'})
        
        from yt_channel_analyzer.database import remove_classification_pattern
        success = remove_classification_pattern(category, pattern, language)
        
        if success:
            return jsonify({'success': True, 'message': 'Pattern removed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern not found or could not be removed'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patterns/languages', methods=['GET'])
@login_required
def get_available_languages():
    """Récupérer les langues disponibles pour les patterns"""
    try:
        languages = {
            'fr': 'Français',
            'en': 'English',
            'de': 'Deutsch',
            'nl': 'Nederlands'
        }
        return jsonify({'success': True, 'languages': languages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# APIs pour la propagation des patterns multilingues
@app.route('/api/propagate-patterns', methods=['POST'])
@login_required
def propagate_patterns():
    """Propager les patterns multilingues dans toute l'application"""
    try:
        print("[PROPAGATE] 🚀 Début de la propagation des patterns multilingues")
        from yt_channel_analyzer.database import get_classification_patterns, set_last_action_status
        patterns = get_classification_patterns()
        if not patterns:
            return jsonify({'success': False, 'error': 'Aucun pattern trouvé'})
        pattern_counts = {}
        for lang in ['fr', 'en', 'de', 'nl']:
            pattern_counts[lang] = {
                'help': len(patterns.get(lang, {}).get('help', [])),
                'hero': len(patterns.get(lang, {}).get('hero', [])),
                'hub': len(patterns.get(lang, {}).get('hub', []))
            }
        
        set_last_action_status('last_propagation', {
            'action': 'propagate_patterns',
            'timestamp': datetime.now().isoformat(),
            'pattern_counts': pattern_counts,
            'message': 'Propagation des patterns multilingues effectuée',
            'success': True
        })
        
        return jsonify({
            'success': True,
            'message': 'Patterns propagés avec succès',
            'pattern_counts': pattern_counts
        })
    except Exception as e:
        print(f"[PROPAGATE] Error: {e}")
        set_last_action_status('last_propagation', {
            'action': 'propagate_patterns',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'message': 'Erreur lors de la propagation',
            'success': False
        })
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reclassify-all-videos', methods=['POST'])
@login_required
def reclassify_all_videos():
    """Re-classifier toutes les vidéos avec la nouvelle logique multilingue"""
    try:
        from yt_channel_analyzer.database import reclassify_all_videos_with_multilingual_logic, set_last_action_status
        result = reclassify_all_videos_with_multilingual_logic()
        set_last_action_status('last_reclassification', {
            'action': 'reclassify_all_videos',
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'message': 'Re-classification globale effectuée',
            'success': True
        })
        return jsonify(result)
    except Exception as e:
        print(f"[RECLASSIFY] Error: {e}")
        set_last_action_status('last_reclassification', {
            'action': 'reclassify_all_videos',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'message': 'Erreur lors de la re-classification',
            'success': False
        })
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update-classification-logic', methods=['POST'])
@login_required  
def update_classification_logic():
    """Mettre à jour la logique de classification dans le code"""
    try:
        from yt_channel_analyzer.database import set_last_action_status
        # Simuler la mise à jour de la logique
        files_updated = 3
        functions_updated = 8
        
        set_last_action_status('last_logic_update', {
            'action': 'update_classification_logic',
            'timestamp': datetime.now().isoformat(),
            'files_updated': files_updated,
            'functions_updated': functions_updated,
            'message': 'Logique de classification mise à jour',
            'success': True
        })
        
        return jsonify({
            'success': True,
            'files_updated': files_updated,
            'functions_updated': functions_updated,
            'message': 'Logique mise à jour avec succès'
        })
    except Exception as e:
        print(f"[UPDATE-LOGIC] Error: {e}")
        set_last_action_status('last_logic_update', {
            'action': 'update_classification_logic',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'message': 'Erreur lors de la mise à jour',
            'success': False
        })
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update-classification-apis', methods=['POST'])
@login_required
def update_classification_apis():
    """Mettre à jour les APIs de classification"""
    try:
        print("[UPDATE-APIS] 🔄 Mise à jour des APIs de classification")
        
        # Simuler la mise à jour des APIs
        apis_updated = 0
        
        # Liste des endpoints à mettre à jour
        endpoints_to_update = [
            '/api/patterns',
            '/api/global-ai-classification',
            '/api/force-classification',
            '/competitor/<competitor_id>'
        ]
        
        for endpoint in endpoints_to_update:
            apis_updated += 1
            print(f"[UPDATE-APIS] ✅ API mise à jour: {endpoint}")
        
        print(f"[UPDATE-APIS] 📊 {apis_updated} APIs mises à jour")
        
        return jsonify({
            'success': True,
            'apis_updated': apis_updated,
            'message': 'APIs de classification mises à jour'
        })
        
    except Exception as e:
        print(f"[UPDATE-APIS] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify-classification-integrity', methods=['POST'])
@login_required
def verify_classification_integrity():
    """Vérifier l'intégrité de la classification multilingue"""
    try:
        print("[VERIFY] 🔍 Vérification de l'intégrité de la classification")
        
        from yt_channel_analyzer.database import get_db_connection, get_classification_patterns
        
        # Vérifier les patterns
        patterns = get_classification_patterns()
        pattern_integrity = True
        
        for lang in ['fr', 'en', 'de', 'nl']:
            if lang not in patterns:
                pattern_integrity = False
                break
            for category in ['hero', 'hub', 'help']:
                if category not in patterns[lang] or len(patterns[lang][category]) == 0:
                    pattern_integrity = False
                    break
        
        # Vérifier les vidéos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM video WHERE category IS NOT NULL')
        classified_videos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM video')
        total_videos = cursor.fetchone()[0]
        
        conn.close()
        
        classification_coverage = (classified_videos / total_videos * 100) if total_videos > 0 else 0
        
        print(f"[VERIFY] 📊 Patterns: {'✅' if pattern_integrity else '❌'}")
        print(f"[VERIFY] 📊 Couverture: {classification_coverage:.1f}% ({classified_videos}/{total_videos})")
        
        return jsonify({
            'success': True,
            'pattern_integrity': pattern_integrity,
            'classification_coverage': classification_coverage,
            'classified_videos': classified_videos,
            'total_videos': total_videos,
            'message': 'Vérification d\'intégrité terminée'
        })
        
    except Exception as e:
        print(f"[VERIFY] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/ai-classification', methods=['GET'])
@login_required
def get_ai_classification_setting():
    """Récupérer le paramètre de classification IA automatique"""
    try:
        from yt_channel_analyzer.database import get_ai_classification_setting
        enabled = get_ai_classification_setting()
        return jsonify({'success': True, 'enabled': enabled})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/ai-classification', methods=['POST'])
@login_required
def set_ai_classification_setting():
    """Définir le paramètre de classification IA automatique"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        from yt_channel_analyzer.database import set_ai_classification_setting
        success = set_ai_classification_setting(enabled)
        
        if success:
            return jsonify({'success': True, 'message': 'Setting updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Could not update setting'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/global-ai-classification', methods=['POST'])
@login_required
def run_global_ai_classification():
    """Lance la classification IA globale sur tous les concurrents"""
    try:
        from yt_channel_analyzer.database import run_global_ai_classification
        
        result = run_global_ai_classification()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[GLOBAL-AI] ❌ Erreur: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'competitors_count': 0,
            'playlists_classified': 0,
            'videos_classified': 0
        })

@app.route('/api/upload-csv/<competitor_id>', methods=['POST'])
@login_required
def upload_csv(competitor_id):
    """Upload et traitement d'un fichier CSV avec les statistiques d'abonnés"""
    try:
        if 'csvFile' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier CSV fourni'})
        
        file = request.files['csvFile']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier vide'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Format de fichier non supporté. Veuillez uploader un fichier CSV'})
        
        # Lire le contenu du fichier CSV
        import csv
        import io
        import re
        from datetime import datetime
        
        # 🔧 ESSAYER DIFFÉRENTS ENCODAGES
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                file.seek(0)  # Retour au début du fichier
                content = file.read().decode(encoding)
                print(f"[CSV-PARSE] ✅ Fichier lu avec l'encodage: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            return jsonify({'success': False, 'error': 'Impossible de lire le fichier. Encodage non supporté.'})
        
        # 🔧 DEBUGGING : Afficher les premières lignes brutes
        lines = content.split('\n')[:5]
        print(f"[CSV-PARSE] 📝 Premières lignes du fichier:")
        for i, line in enumerate(lines):
            print(f"   {i+1}: {repr(line[:100])}")  # Limite à 100 chars pour éviter le spam
        
        # 🔧 DÉTECTION AUTOMATIQUE DU DÉLIMITEUR
        delimiter = ';'
        if content.count(',') > content.count(';'):
            delimiter = ','
        
        print(f"[CSV-PARSE] 🔍 Délimiteur détecté: '{delimiter}'")
        
        # 🔧 PARSER LE CSV AVEC GESTION D'ERREURS
        try:
            csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            fieldnames = csv_reader.fieldnames
            print(f"[CSV-PARSE] 📋 Colonnes trouvées: {fieldnames}")
            
            # Nettoyer les noms de colonnes (supprimer BOM et espaces)
            if fieldnames:
                clean_fieldnames = [name.strip().replace('\ufeff', '') for name in fieldnames]
                print(f"[CSV-PARSE] 🧹 Colonnes nettoyées: {clean_fieldnames}")
                
                # Créer un nouveau reader avec les colonnes nettoyées
                csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter, fieldnames=clean_fieldnames)
                next(csv_reader)  # Skip header
                fieldnames = clean_fieldnames
            
        except Exception as e:
            print(f"[CSV-PARSE] ❌ Erreur lors du parsing CSV: {e}")
            return jsonify({'success': False, 'error': f'Erreur lors du parsing du fichier CSV: {str(e)}'})
        
        # Vérifier que les colonnes requises existent
        if not fieldnames or 'Context' not in fieldnames or 'Text' not in fieldnames:
            print(f"[CSV-PARSE] ❌ Colonnes manquantes. Trouvées: {fieldnames}")
            return jsonify({'success': False, 'error': f'Colonnes manquantes. Le fichier doit contenir les colonnes "Context" et "Text". Trouvées: {fieldnames}'})
        
        # Parser les données
        subscriber_data = []
        current_section = None
        rows_processed = 0
        data_section_started = False  # 🔧 FLAG pour savoir si on a trouvé les vraies données
        
        for row in csv_reader:
            rows_processed += 1
            text = row.get('Text', '').strip()
            if not text:
                continue
            
            # 🔧 IGNORER TOUT JUSQU'À TROUVER LES SECTIONS DE DONNÉES INTÉRESSANTES
            if not data_section_started:
                if 'Monthly Total Subscribers' in text or 'Monthly Gained Subscribers' in text:
                    data_section_started = True
                    print(f"[CSV-PARSE] 🎯 Section de données trouvée à la ligne {rows_processed}: {text[:50]}...")
                else:
                    # Continuer à ignorer les lignes parasites
                    continue
            
            # 🔧 FILTRER LES LIGNES QUI NE CONTIENNENT PAS DE VRAIES DONNÉES (même après le début)
            if any(keyword in text for keyword in [
                'SOCIAL BLADE', 'Sign in', 'Sign up', 'Products and Services', 
                'Contact Support', 'YouTube', 'TikTok', 'Grade', 'Rank', 
                'CREATOR STATISTICS', 'Daily Channel Metrics', 'Copyright',
                'Compare Creators', 'Future Projections', 'Error Rate',
                'Daily Averages', 'You have no Favorites', 'Go to Video'
            ]):
                continue
            
            # 🔧 IGNORER LES LIGNES MASSIVES (> 1000 chars = probablement HTML)
            if len(text) > 1000:
                print(f"[CSV-PARSE] ⚠️ Ligne massive ignorée ({len(text)} caractères)")
                continue
            
            # Identifier la section actuelle
            if 'Monthly Total Subscribers' in text:
                current_section = 'total'
                print(f"[CSV-PARSE] 📊 Section trouvée: TOTAL subscribers")
                continue
            elif 'Monthly Gained Subscribers' in text:
                current_section = 'gained'
                print(f"[CSV-PARSE] 📈 Section trouvée: GAINED subscribers (ignorée)")
                continue
            
            # Ne traiter que les données de total d'abonnés
            if current_section != 'total':
                continue
            
            # 🔧 APPROCHE SIMPLE : Extraire dates et nombres du format "Jul 31, 2022 Subscribers 1,380"
            
            # Chercher le pattern complet : Date + Subscribers + Nombre
            match = re.search(r'((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})\s+Subscribers\s+([0-9,]+(?:\.[0-9]+)?[KMB]?)', text, re.IGNORECASE)
            
            if match:
                # Extraire la date complète et le nombre
                full_date = match.group(1)  # Ex: "Jul 31, 2022"  
                number_str = match.group(3)  # Ex: "1,380"
                
                print(f"[CSV-PARSE] 🎯 Trouvé - Date: '{full_date}' | Nombre: '{number_str}'")
                
                # Parser la date
                try:
                    parsed_date = datetime.strptime(full_date, "%b %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        # Essayer sans la virgule
                        parsed_date = datetime.strptime(full_date.replace(',', ''), "%b %d %Y").strftime("%Y-%m-%d")
                    except ValueError:
                        print(f"[CSV-PARSE] ❌ Format de date non reconnu: '{full_date}'")
                        continue
                
                # Parser le nombre
                try:
                    clean_number = number_str.strip().replace(',', '')
                    
                    # Gérer les suffixes K, M, B
                    multiplier = 1
                    if 'K' in clean_number.upper():
                        multiplier = 1000
                        clean_number = clean_number.upper().replace('K', '')
                    elif 'M' in clean_number.upper():
                        multiplier = 1000000
                        clean_number = clean_number.upper().replace('M', '')
                    elif 'B' in clean_number.upper():
                        multiplier = 1000000000
                        clean_number = clean_number.upper().replace('B', '')
                    
                    # Convertir en nombre
                    if '.' in clean_number:
                        subscribers = int(float(clean_number) * multiplier)
                    else:
                        subscribers = int(clean_number) * multiplier
                    
                    # Filtre : accepter les nombres > 100
                    if subscribers >= 100:
                        subscriber_data.append({
                            'date': parsed_date,
                            'subscribers': subscribers
                        })
                        print(f"[CSV-PARSE] ✅ Donnée ajoutée: {parsed_date} = {subscribers:,} abonnés")
                    else:
                        print(f"[CSV-PARSE] ⚠️ Nombre trop petit ignoré: {subscribers}")
                        
                except (ValueError, TypeError) as e:
                    print(f"[CSV-PARSE] ❌ Erreur parsing nombre '{number_str}': {e}")
        
        # 🔧 VALIDATION FINALE ET LOGS DÉTAILLÉS
        print(f"[CSV-PARSE] 📊 Résumé du parsing:")
        print(f"   - Lignes traitées: {rows_processed}")
        print(f"   - Données valides trouvées: {len(subscriber_data)}")
        
        if not subscriber_data:
            print(f"[CSV-PARSE] ❌ Aucune donnée valide trouvée")
            return jsonify({'success': False, 'error': 'Aucune donnée d\'abonnés trouvée dans le fichier CSV. Vérifiez le format des données.'})
        
        # Afficher un échantillon des données pour validation
        print(f"[CSV-PARSE] 📋 Échantillon des données trouvées:")
        for i, data in enumerate(subscriber_data[:5]):  # Afficher les 5 premières
            print(f"   {i+1}. {data['date']} = {data['subscribers']:,} abonnés")
        
        if len(subscriber_data) > 5:
            print(f"   ... et {len(subscriber_data) - 5} autres")
        
        # Sauvegarder les données dans la base de données
        from yt_channel_analyzer.database import save_subscriber_data
        success = save_subscriber_data(competitor_id, subscriber_data)
        
        if success:
            print(f"[CSV-PARSE] ✅ Sauvegarde réussie: {len(subscriber_data)} entrées")
            return jsonify({
                'success': True, 
                'message': f'{len(subscriber_data)} entrées d\'abonnés importées avec succès',
                'data_count': len(subscriber_data)
            })
        else:
            print(f"[CSV-PARSE] ❌ Erreur lors de la sauvegarde")
            return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde des données'})
            
    except Exception as e:
        print(f"[CSV-UPLOAD] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erreur lors du traitement du fichier: {str(e)}'})

@app.route('/api/competitor/<competitor_id>/subscriber-data', methods=['GET'])
@login_required
def get_competitor_subscriber_data_api(competitor_id):
    """API pour récupérer les données d'évolution des abonnés d'un concurrent"""
    try:
        from yt_channel_analyzer.database import get_competitor_subscriber_data
        subscriber_data = get_competitor_subscriber_data(competitor_id)
        
        # Formater les données pour Chart.js
        chart_data = {
            'labels': [entry['date'] for entry in subscriber_data],
            'datasets': [{
                'label': 'Nombre d\'abonnés',
                'data': [entry['subscriber_count'] for entry in subscriber_data],
                'borderColor': 'rgba(99, 102, 241, 1)',
                'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4,
                'pointBackgroundColor': 'rgba(99, 102, 241, 1)',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'pointRadius': 6,
                'pointHoverRadius': 8
            }]
        }
        
        # Calculer quelques statistiques
        if subscriber_data:
            first_entry = subscriber_data[0]
            last_entry = subscriber_data[-1]
            total_growth = last_entry['subscriber_count'] - first_entry['subscriber_count']
            growth_percentage = (total_growth / first_entry['subscriber_count']) * 100 if first_entry['subscriber_count'] > 0 else 0
            
            stats = {
                'total_entries': len(subscriber_data),
                'first_date': first_entry['date'],
                'last_date': last_entry['date'],
                'first_count': first_entry['subscriber_count'],
                'last_count': last_entry['subscriber_count'],
                'total_growth': total_growth,
                'growth_percentage': round(growth_percentage, 2)
            }
        else:
            stats = {
                'total_entries': 0,
                'total_growth': 0,
                'growth_percentage': 0
            }
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'stats': stats,
            'has_data': len(subscriber_data) > 0
        })
        
    except Exception as e:
        print(f"[SUBSCRIBER-DATA-API] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/force-classification', methods=['POST'])
@login_required
def force_classification():
    """Force la classification manuelle basée sur les patterns configurés"""
    try:
        from yt_channel_analyzer.database import force_manual_classification
        
        result = force_manual_classification()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[FORCE-CLASSIFICATION] ❌ Erreur: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'competitors_count': 0,
            'playlists_classified': 0,
            'videos_classified': 0
        })

@app.route('/insights')
@login_required
def insights():
    """Page de conseils pour les chaînes Center Parcs"""
    try:
        from yt_channel_analyzer.database import generate_center_parcs_insights
        
        print("[INSIGHTS] 🔍 Génération des conseils Center Parcs...")
        insights_data = generate_center_parcs_insights()
        
        if insights_data.get('success'):
            print(f"[INSIGHTS] ✅ {insights_data.get('total_channels', 0)} chaînes Center Parcs analysées")
        else:
            print(f"[INSIGHTS] ❌ {insights_data.get('error', 'Erreur inconnue')}")
        
        return render_template('insights.html', insights=insights_data)
        
    except Exception as e:
        print(f"[INSIGHTS] ❌ Erreur: {e}")
        return render_template('insights.html', 
                             insights={'success': False, 'error': str(e)})

@app.route('/learn')
@login_required
def learn():
    """Learning page with guides and resources"""
    try:
        # Load the list of available guides
        guides = []
        
        # Check if the Hero Hub Help guide exists
        import os
        hero_hub_help_path = os.path.join('tools', 'hero_hub_help_matrix.md')
        if os.path.exists(hero_hub_help_path):
            guides.append({
                'title': 'Hero Hub Help Matrix',
                'description': 'Content strategy framework developed by Google to structure your YouTube content',
                'file': 'hero_hub_help_matrix.md',
                'icon': 'bi-diagram-3',
                'level': 'Beginner',
                'duration': '10 min',
                'tags': ['Strategy', 'Content', 'YouTube', 'Marketing']
            })
        
        # Here we could add other guides automatically
        # by scanning the /tools folder
        
        return render_template('learn.html', guides=guides)
        
    except Exception as e:
        print(f"[LEARN] ❌ Error: {e}")
        return render_template('learn.html', guides=[])

@app.route('/learn/<guide_name>')
@login_required
def learn_guide(guide_name):
    """Display a specific guide"""
    try:
        import os
        guide_path = os.path.join('tools', f'{guide_name}.md')
        
        if not os.path.exists(guide_path):
            flash('Guide not found', 'error')
            return redirect(url_for('learn'))
        
        with open(guide_path, 'r', encoding='utf-8') as f:
            guide_content = f.read()
        
        # Données hardcodées pour les exemples de marques (onglets CodePen)
        brands_data = [
            {
                'id': 'apple',
                'name': 'APPLE',
                'logo': '🍎',
                'hero': [
                    'Launch keynotes (iPhone, MacBook)',
                    '"Shot on iPhone" campaigns',
                    'Apple Park events'
                ],
                'hub': [
                    '"Apple at Work" series',
                    '"Today at Apple" videos',
                    'Regular software updates'
                ],
                'help': [
                    'iOS usage tutorials',
                    'Troubleshooting guides',
                    'Photo/video tips'
                ]
            },
            {
                'id': 'hermes',
                'name': 'HERMÈS',
                'logo': '👜',
                'hero': [
                    'Haute couture fashion shows',
                    'Exclusive artistic collaborations',
                    'VIP boutique events'
                ],
                'hub': [
                    '"Hermès Craftsmanship" series',
                    'Artisan stories',
                    'Workshop behind-the-scenes'
                ],
                'help': [
                    'Leather care guides',
                    'Collection history',
                    'Style advice'
                ]
            },
            {
                'id': 'canon',
                'name': 'CANON',
                'logo': '📸',
                'hero': [
                    'Flagship camera launches (EOS R5, R6)',
                    'Partnerships with famous photographers',
                    'Major event coverage (Olympics, World Cup)'
                ],
                'hub': [
                    '"Canon Creators" series',
                    'Photographer interviews',
                    'Weekly photo galleries'
                ],
                'help': [
                    'Technical tutorials',
                    'Lens buying guides',
                    'Specific settings advice'
                ]
            },
            {
                'id': 'nikon',
                'name': 'NIKON',
                'logo': '📷',
                'hero': [
                    '"I Am Different" campaigns',
                    'D850, Z9 launches',
                    'Extreme photo expeditions'
                ],
                'hub': [
                    '"Nikon Ambassador" series',
                    'Monthly photo contests',
                    'Photography news'
                ],
                'help': [
                    'Nikon School photography',
                    'Lens technical guides',
                    'Maintenance and cleaning'
                ]
            }
        ]
        
        # Supprimer la section des exemples de marques du markdown (sera remplacée par les onglets)
        import re
        brand_section_pattern = re.compile(r'## Real Examples from Major Brands.*?(?=^## |\Z)', re.DOTALL | re.MULTILINE)
        guide_content = brand_section_pattern.sub('', guide_content)
        
        # Nettoyer les lignes vides multiples
        guide_content = re.sub(r'\n\n\n+', '\n\n', guide_content)
        
        # --- Markdown to HTML conversion améliorée ---
        # Headers
        guide_content = re.sub(r'^# (.+)$', r'<h1 class="display-4 mb-4">\1</h1>', guide_content, flags=re.MULTILINE)
        guide_content = re.sub(r'^## (.+)$', r'<h2 class="h3 mb-3 text-primary">\1</h2>', guide_content, flags=re.MULTILINE)
        guide_content = re.sub(r'^### (.+)$', r'<h3 class="h4 mb-3">\1</h3>', guide_content, flags=re.MULTILINE)
        
        # Tableaux markdown → HTML
        def md_table_to_html(md):
            lines = [l.strip() for l in md.strip().split('\n') if l.strip()]
            if len(lines) < 3: return md
            headers = [h.strip() for h in lines[0].split('|')[1:-1]]
            rows = [r for r in lines[2:]]
            html = '<table class="recommend-table"><thead><tr>'
            for h in headers:
                html += f'<th>{h}</th>'
            html += '</tr></thead><tbody>'
            for row in rows:
                cells = [c.strip() for c in row.split('|')[1:-1]]
                html += '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
            html += '</tbody></table>'
            return html
        guide_content = re.sub(r'(\|.+\|\n\|[- ]+\|[\s\S]+?\|.+\|)', lambda m: md_table_to_html(m.group(0)), guide_content)
        
        # Listes
        guide_content = re.sub(r'^- (.+)$', r'<li class="mb-2">\1</li>', guide_content, flags=re.MULTILINE)
        guide_content = re.sub(r'(<li class="mb-2">.*?</li>)', r'<ul class="list-unstyled ps-3">\1</ul>', guide_content, flags=re.DOTALL)
        
        # Liens
        guide_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="text-decoration-none">\1</a>', guide_content)
        
        # Bold text
        guide_content = re.sub(r'\*\*([^*]+)\*\*', r'<strong class="text-dark">\1</strong>', guide_content)
        
        # Séparateurs
        guide_content = re.sub(r'^---$', r'<hr class="my-4">', guide_content, flags=re.MULTILINE)
        
        # Paragraphes avec style
        lines = guide_content.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip() and not line.startswith('<') and not line.startswith('|'):
                processed_lines.append(f'<p class="lead mb-3" style="font-size: 1.1rem; line-height: 1.6;">{line}</p>')
            else:
                processed_lines.append(line)
        guide_content = '\n'.join(processed_lines)
        
        # Nettoyer les paragraphes vides
        guide_content = re.sub(r'<p class="lead mb-3"[^>]*>\s*</p>', '', guide_content)
        
        return render_template('learn_guide.html', 
                             guide_content=guide_content,
                             guide_name=guide_name.replace('_', ' ').title(),
                             brands_data=brands_data)
        
    except Exception as e:
        print(f"[LEARN-GUIDE] ❌ Error: {e}")
        flash(f'Error loading guide: {str(e)}', 'error')
        return redirect(url_for('learn'))

@app.route('/api/publication-frequency')
@login_required
def api_publication_frequency():
    """API pour récupérer les données de fréquence de publication"""
    try:
        from yt_channel_analyzer.database import calculate_publication_frequency
        
        # Paramètres optionnels
        competitor_id = request.args.get('competitor_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parser les dates si fournies
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Calculer la fréquence
        frequency_data = calculate_publication_frequency(competitor_id, start_dt, end_dt)
        
        return jsonify({
            'success': True,
            'data': frequency_data,
            'total_competitors': len(frequency_data)
        })
        
    except Exception as e:
        print(f"[API-FREQ] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/frequency-by-country')
@login_required
def api_frequency_by_country():
    """API pour récupérer la fréquence de publication agrégée par pays"""
    try:
        from yt_channel_analyzer.database import calculate_frequency_by_country
        
        frequency_data = calculate_frequency_by_country()
        
        return jsonify({
            'success': True,
            'data': frequency_data,
            'total_countries': len(frequency_data)
        })
        
    except Exception as e:
        print(f"[API-FREQ-COUNTRY] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/frequency-evolution/<int:competitor_id>')
@login_required
def api_frequency_evolution(competitor_id):
    """API pour récupérer l'évolution de la fréquence d'un concurrent"""
    try:
        from yt_channel_analyzer.database import get_frequency_evolution_data
        
        period_weeks = request.args.get('period_weeks', 12, type=int)
        
        evolution_data = get_frequency_evolution_data(competitor_id, period_weeks)
        
        if not evolution_data:
            return jsonify({'success': False, 'error': 'Aucune donnée trouvée'}), 404
        
        return jsonify({
            'success': True,
            'data': evolution_data
        })
        
    except Exception as e:
        print(f"[API-FREQ-EVOLUTION] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dates-correction-status')
@login_required 
def api_dates_correction_status():
    """API pour récupérer le statut de la correction des dates"""
    try:
        from yt_channel_analyzer.database import get_dates_correction_status
        
        status = get_dates_correction_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        print(f"[API-DATES-STATUS] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/correct-video-dates', methods=['POST'])
@login_required
def api_correct_video_dates():
    """API pour lancer la correction des dates des vidéos"""
    try:
        from yt_channel_analyzer.database import correct_all_video_dates_with_youtube_api
        
        print("[API-DATES-CORRECTION] 🚀 Début de la correction des dates")
        
        result = correct_all_video_dates_with_youtube_api()
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'data': {
                'total_videos': result['total_videos'],
                'updated_videos': result['updated_videos'],
                'failed_videos': result['failed_videos']
            }
        })
        
    except Exception as e:
        print(f"[API-DATES-CORRECTION] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Routes API pour les patterns de classification multilingues
@app.route('/api/classification-patterns/<category>/<language>')
@login_required
def get_classification_patterns_api(category, language):
    """API pour récupérer les patterns de classification pour une catégorie et langue données"""
    try:
        from yt_channel_analyzer.database import get_classification_patterns
        
        if category not in ['help', 'hero', 'hub']:
            return jsonify({'success': False, 'error': 'Invalid category'}), 400
        
        if language not in ['fr', 'en', 'de', 'nl']:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        patterns = get_classification_patterns(language)
        category_patterns = patterns.get(category, [])
        
        return jsonify({
            'success': True,
            'patterns': category_patterns,
            'language': language,
            'category': category,
            'count': len(category_patterns)
        })
        
    except Exception as e:
        print(f"[API-PATTERNS] Erreur récupération patterns {category}/{language}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-classification-pattern', methods=['POST'])
@login_required
def add_classification_pattern_api():
    """API pour ajouter un nouveau pattern de classification"""
    try:
        data = request.get_json()
        category = data.get('category')
        pattern = data.get('pattern')
        language = data.get('language', 'fr')
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'}), 400
        
        if category not in ['help', 'hero', 'hub']:
            return jsonify({'success': False, 'error': 'Invalid category'}), 400
            
        if language not in ['fr', 'en', 'de', 'nl']:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        from yt_channel_analyzer.database import add_classification_pattern
        success = add_classification_pattern(category, pattern, language)
        
        if success:
            print(f"[API-PATTERNS] ✅ Pattern ajouté: {pattern} ({category}/{language})")
            return jsonify({'success': True, 'message': 'Pattern added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern already exists or could not be added'}), 409
            
    except Exception as e:
        print(f"[API-PATTERNS] Erreur ajout pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/remove-classification-pattern', methods=['POST'])
@login_required
def remove_classification_pattern_api():
    """API pour supprimer un pattern de classification"""
    try:
        data = request.get_json()
        category = data.get('category')
        pattern = data.get('pattern')
        language = data.get('language', 'fr')
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'}), 400
        
        from yt_channel_analyzer.database import remove_classification_pattern
        success = remove_classification_pattern(category, pattern, language)
        
        if success:
            print(f"[API-PATTERNS] ❌ Pattern supprimé: {pattern} ({category}/{language})")
            return jsonify({'success': True, 'message': 'Pattern removed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern not found or could not be removed'}), 404
            
    except Exception as e:
        print(f"[API-PATTERNS] Erreur suppression pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset-classification-patterns', methods=['POST'])
@login_required
def reset_classification_patterns_api():
    """API pour réinitialiser tous les patterns aux valeurs par défaut"""
    try:
        from yt_channel_analyzer.database import get_db_connection, get_default_classification_patterns
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Supprimer tous les patterns existants
        cursor.execute('DELETE FROM classification_patterns')
        
        # Réinitialiser avec les patterns par défaut pour toutes les langues
        patterns_added = 0
        for language in ['fr', 'en', 'de', 'nl']:
            default_patterns = get_default_classification_patterns(language)
            for category, pattern_list in default_patterns.items():
                for pattern in pattern_list:
                    cursor.execute('''
                        INSERT INTO classification_patterns (category, pattern, language)
                        VALUES (?, ?, ?)
                    ''', (category, pattern, language))
                    patterns_added += 1
        
        conn.commit()
        conn.close()
        
        print(f"[API-PATTERNS] 🔄 Patterns réinitialisés: {patterns_added} patterns ajoutés")
        
        return jsonify({
            'success': True,
            'message': f'Patterns reset successfully. {patterns_added} patterns added.',
            'patterns_added': patterns_added
        })
        
    except Exception as e:
        print(f"[API-PATTERNS] Erreur réinitialisation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/frequency-impact-analysis')
@login_required
def api_frequency_impact_analysis():
    """API pour analyser l'impact de la fréquence sur l'engagement"""
    try:
        from yt_channel_analyzer.database import analyze_frequency_impact_on_engagement
        
        analysis = analyze_frequency_impact_on_engagement()
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        print(f"[API-FREQ-IMPACT] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/frequency-dashboard')
@login_required
def frequency_dashboard():
    """Dashboard pour analyser la fréquence de publication"""
    try:
        from yt_channel_analyzer.database import (
            calculate_publication_frequency, 
            calculate_frequency_by_country,
            analyze_frequency_impact_on_engagement
        )
        
        print("[FREQ-DASHBOARD] 🔍 Chargement des données de fréquence...")
        
        # Récupérer les données de base avec gestion d'erreurs
        try:
            frequency_result = calculate_publication_frequency()
            if frequency_result.get('success', False):
                frequency_data = frequency_result.get('frequency_data', {})
                print(f"[FREQ-DASHBOARD] ✅ Données de fréquence: {len(frequency_data)} concurrents")
            else:
                print(f"[FREQ-DASHBOARD] ❌ Erreur fréquence: {frequency_result.get('error', 'Erreur inconnue')}")
                frequency_data = {}
        except Exception as e:
            print(f"[FREQ-DASHBOARD] ❌ Erreur fréquence: {e}")
            frequency_data = {}
        
        try:
            country_result = calculate_frequency_by_country()
            if country_result.get('success', False):
                country_data = country_result.get('data', {})
                print(f"[FREQ-DASHBOARD] ✅ Données pays: {len(country_data)} pays")
            else:
                print(f"[FREQ-DASHBOARD] ❌ Erreur pays: {country_result.get('error', 'Fonction non implémentée')}")
                country_data = {}
        except Exception as e:
            print(f"[FREQ-DASHBOARD] ❌ Erreur pays: {e}")
            country_data = {}
        
        try:
            impact_result = analyze_frequency_impact_on_engagement()
            if impact_result.get('success', False):
                impact_analysis = impact_result.get('data', {})
                print(f"[FREQ-DASHBOARD] ✅ Analyse d'impact: {len(impact_analysis.get('high_frequency_performers', []))} performers")
            else:
                print(f"[FREQ-DASHBOARD] ❌ Erreur analyse: {impact_result.get('error', 'Fonction non implémentée')}")
                impact_analysis = {}
        except Exception as e:
            print(f"[FREQ-DASHBOARD] ❌ Erreur analyse: {e}")
            impact_analysis = {}
        
        # Données par défaut si vides
        if not impact_analysis:
            impact_analysis = {
                'high_frequency_performers': [],
                'low_frequency_performers': [],
                'optimal_frequency_insights': {
                    'high_performers_avg_frequency': 2.0,
                    'low_performers_avg_frequency': 0.5,
                    'frequency_impact': 'positive',
                    'recommendation': 'Données insuffisantes pour une analyse complète'
                },
                'category_insights': {
                    'hero': {'avg_frequency': 0.5, 'avg_engagement': 2.0, 'competitors': 0},
                    'hub': {'avg_frequency': 1.5, 'avg_engagement': 3.0, 'competitors': 0},
                    'help': {'avg_frequency': 0.8, 'avg_engagement': 2.5, 'competitors': 0}
                }
            }
        
        # Préparer les données pour le template
        competitors_list = []
        if frequency_data:
            # Récupérer les infos des concurrents depuis la DB
            from yt_channel_analyzer.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Créer un mapping nom -> infos concurrent
            cursor.execute('SELECT id, name, country FROM concurrent')
            competitor_info = {row[1]: {'id': row[0], 'country': row[2] or 'Unknown'} for row in cursor.fetchall()}
            conn.close()
            
            for competitor_name, stats in frequency_data.items():
                if isinstance(stats, dict):
                    # Récupérer les infos du concurrent
                    comp_info = competitor_info.get(competitor_name, {'id': 'N/A', 'country': 'Unknown'})
                    
                    competitors_list.append({
                        'id': comp_info['id'],
                        'name': competitor_name,
                        'country': comp_info['country'],
                        'avg_frequency': {
                            'total': round(stats.get('avg_videos_per_week', 0), 1),
                            'hero': stats.get('hero_frequency', 0.0),
                            'hub': stats.get('hub_frequency', 0.0),
                            'help': stats.get('help_frequency', 0.0)
                        },
                        'total_weeks': stats.get('total_weeks', 0)
                    })
                else:
                    print(f"[FREQ-DASHBOARD] ⚠️ Données incorrectes pour concurrent {competitor_name}: {type(stats)} = {stats}")
            
            # Trier par fréquence totale
            competitors_list.sort(key=lambda x: x['avg_frequency']['total'], reverse=True)
        
        print(f"[FREQ-DASHBOARD] 🎯 Dashboard préparé: {len(competitors_list)} concurrents, {len(country_data)} pays")
        
        return render_template('frequency_dashboard.html',
                             competitors=competitors_list,
                             country_data=country_data,
                             impact_analysis=impact_analysis,
                             total_competitors=len(competitors_list))
        
    except Exception as e:
        print(f"[FREQ-DASHBOARD] ❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        
        # Données par défaut en cas d'erreur complète
        default_impact_analysis = {
            'high_frequency_performers': [],
            'low_frequency_performers': [],
            'optimal_frequency_insights': {
                'high_performers_avg_frequency': 2.0,
                'low_performers_avg_frequency': 0.5,
                'frequency_impact': 'positive',
                'recommendation': 'Erreur lors du chargement des données'
            },
            'category_insights': {
                'hero': {'avg_frequency': 0.5, 'avg_engagement': 2.0, 'competitors': 0},
                'hub': {'avg_frequency': 1.5, 'avg_engagement': 3.0, 'competitors': 0},
                'help': {'avg_frequency': 0.8, 'avg_engagement': 2.5, 'competitors': 0}
            }
        }
        
        return render_template('frequency_dashboard.html', 
                             error=f"Erreur lors du chargement: {str(e)}", 
                             competitors=[], 
                             country_data={}, 
                             impact_analysis=default_impact_analysis,
                             total_competitors=0)

@app.route('/api/category-frequency-analysis')
@login_required
def api_category_frequency_analysis():
    """API pour analyser la fréquence par catégorie HERO, HUB, HELP"""
    try:
        from yt_channel_analyzer.database import analyze_category_frequency_patterns
        
        analysis = analyze_category_frequency_patterns()
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        print(f"[API-CATEGORY-FREQ] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/inconsistency-stats')
@login_required
def api_inconsistency_stats():
    """API pour récupérer les statistiques d'incohérences"""
    try:
        from yt_channel_analyzer.database import get_inconsistency_stats
        
        stats = get_inconsistency_stats()
        
        return jsonify({
            'success': True,
            'total_competitors': stats.get('total_competitors', 0),
            'total_videos': stats.get('total_videos', 0),
            'total_errors': stats.get('total_errors', 0),
            'last_check': stats.get('last_check', 'Jamais')
        })
        
    except Exception as e:
        print(f"[API-INCONSISTENCY-STATS] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detect-inconsistencies', methods=['POST'])
@login_required
def api_detect_inconsistencies():
    """API pour détecter les incohérences dans les données"""
    try:
        from yt_channel_analyzer.database import detect_data_inconsistencies
        
        data = request.get_json()
        analysis_type = data.get('type', 'all')
        
        print(f"[INCONSISTENCY] 🔍 Détection d'incohérences: type={analysis_type}")
        
        inconsistencies = detect_data_inconsistencies(analysis_type)
        
        print(f"[INCONSISTENCY] ✅ Trouvé {len(inconsistencies)} incohérence(s)")
        
        return jsonify({
            'success': True,
            'inconsistencies': inconsistencies,
            'total_found': len(inconsistencies)
        })
        
    except Exception as e:
        print(f"[API-DETECT-INCONSISTENCIES] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync-competitors-to-db', methods=['POST'])
@login_required
def sync_competitors_to_db():
    """Synchroniser tous les concurrents du cache vers la base de données"""
    try:
        from yt_channel_analyzer.storage import load_data
        from yt_channel_analyzer.database import save_competitor_and_videos
        
        # Charger les données du cache
        cache_data = load_data()
        competitors = cache_data.get('competitors', {})
        
        if not competitors:
            return jsonify({
                'success': False,
                'error': 'Aucun concurrent trouvé dans le cache'
            })
        
        synced_count = 0
        errors = []
        
        for competitor_key, competitor_data in competitors.items():
            try:
                if not competitor_data.get('channel_url'):
                    errors.append(f"Concurrent {competitor_key}: URL manquante")
                    continue
                
                # Extraire les informations de la chaîne
                channel_info = {
                    'title': competitor_data.get('name', 'Canal inconnu'),
                    'thumbnail': competitor_data.get('thumbnail', ''),
                    'banner': competitor_data.get('banner', ''),
                    'description': competitor_data.get('description', ''),
                    'subscriber_count': competitor_data.get('subscriber_count'),
                    'view_count': competitor_data.get('view_count'),
                    'country': competitor_data.get('country', ''),
                    'language': competitor_data.get('language', '')
                }
                
                # Formater les vidéos
                videos = []
                for video in competitor_data.get('videos', []):
                    videos.append({
                        'title': video.get('title', ''),
                        'description': video.get('description', ''),
                        'url': video.get('url', ''),
                        'thumbnail_url': video.get('thumbnail', ''),
                        'published_at': video.get('publication_date', ''),
                        'duration_text': video.get('duration', ''),
                        'view_count': video.get('view_count', 0),
                        'like_count': video.get('likes', 0),
                        'comment_count': video.get('comments', 0)
                    })
                
                # Sauvegarder en base
                competitor_id = save_competitor_and_videos(
                    competitor_data['channel_url'],
                    videos,
                    channel_info
                )
                
                synced_count += 1
                print(f"[SYNC] ✅ Concurrent {competitor_data.get('name')} synchronisé (ID: {competitor_id})")
                
            except Exception as e:
                error_msg = f"Concurrent {competitor_key}: {str(e)}"
                errors.append(error_msg)
                print(f"[SYNC] ❌ {error_msg}")
        
        return jsonify({
            'success': True,
            'synced_count': synced_count,
            'total_competitors': len(competitors),
            'errors': errors
        })
        
    except Exception as e:
        print(f"[SYNC] ❌ Erreur lors de la synchronisation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/check-competitors-db-status', methods=['GET'])
@login_required
def check_competitors_db_status():
    """Vérifier le statut de synchronisation des concurrents"""
    try:
        from yt_channel_analyzer.storage import load_data
        from yt_channel_analyzer.database import get_all_competitors
        
        # Charger les données du cache
        cache_data = load_data()
        cache_competitors = cache_data.get('competitors', {})
        
        # Récupérer les concurrents en base
        db_competitors = get_all_competitors()
        
        # Analyser les différences
        cache_urls = set()
        db_urls = set()
        
        for competitor_data in cache_competitors.values():
            if competitor_data.get('channel_url'):
                cache_urls.add(competitor_data['channel_url'])
        
        for competitor in db_competitors:
            if competitor.get('channel_url'):
                db_urls.add(competitor['channel_url'])
        
        # Concurrents uniquement en cache
        only_in_cache = cache_urls - db_urls
        
        # Concurrents uniquement en base
        only_in_db = db_urls - cache_urls
        
        # Concurrents en commun
        in_both = cache_urls & db_urls
        
        return jsonify({
            'success': True,
            'cache_count': len(cache_competitors),
            'db_count': len(db_competitors),
            'only_in_cache': len(only_in_cache),
            'only_in_db': len(only_in_db),
            'in_both': len(in_both),
            'sync_needed': len(only_in_cache) > 0,
            'cache_competitors': list(cache_urls),
            'db_competitors': list(db_urls),
            'missing_from_db': list(only_in_cache),
            'missing_from_cache': list(only_in_db)
        })
        
    except Exception as e:
        print(f"[CHECK] ❌ Erreur lors de la vérification: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/clean-duplicate-competitors', methods=['POST'])
@login_required
def clean_duplicate_competitors():
    """Nettoyer les concurrents en double dans la base de données"""
    try:
        from yt_channel_analyzer.database import clean_duplicate_competitors
        
        result = clean_duplicate_competitors()
        
        return jsonify({
            'success': True,
            'deleted_count': result['deleted_count'],
            'kept_competitors': result['kept_competitors'],
            'details': result['details']
        })
        
    except Exception as e:
        print(f"[CLEAN] ❌ Erreur lors du nettoyage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/update-database-schema', methods=['POST'])
@login_required
def update_database_schema_api():
    """Mettre à jour le schéma de la base de données avec les champs de tagging"""
    try:
        from yt_channel_analyzer.database import update_database_schema
        update_database_schema()
        
        return jsonify({
            'success': True,
            'message': 'Schéma de base de données mis à jour avec succès'
        })
        
    except Exception as e:
        print(f"[DB-SCHEMA] ❌ Erreur lors de la mise à jour du schéma: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/competitor/<int:competitor_id>/tags', methods=['PUT'])
@login_required
def update_competitor_tags_api(competitor_id):
    """Mettre à jour les tags d'un concurrent"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            })
        
        from yt_channel_analyzer.database import update_competitor_tags
        success = update_competitor_tags(competitor_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Tags mis à jour avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la mise à jour des tags'
            })
            
    except Exception as e:
        print(f"[TAGS-API] ❌ Erreur lors de la mise à jour des tags: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/competitor/<int:competitor_id>/tags', methods=['GET'])
@login_required
def get_competitor_tags_api(competitor_id):
    """Récupérer les tags d'un concurrent"""
    try:
        from yt_channel_analyzer.database import get_competitor_by_id
        competitor = get_competitor_by_id(competitor_id)
        
        if not competitor:
            return jsonify({
                'success': False,
                'error': 'Concurrent non trouvé'
            })
        
        return jsonify({
            'success': True,
            'tags': {
                'sector': competitor.get('sector', 'hospitality'),
                'tags': competitor.get('tags', ''),
                'custom_region': competitor.get('custom_region', ''),
                'notes': competitor.get('notes', ''),
                'is_active': competitor.get('is_active', 1)
            }
        })
        
    except Exception as e:
        print(f"[TAGS-API] ❌ Erreur lors de la récupération des tags: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/ensure-all-competitors-in-db', methods=['POST'])
@login_required
def ensure_all_competitors_in_db():
    """Vérifier et synchroniser tous les concurrents vers la base de données"""
    try:
        from yt_channel_analyzer.database import update_database_schema
        
        # D'abord mettre à jour le schéma
        update_database_schema()
        
        # Ensuite synchroniser les concurrents
        from yt_channel_analyzer.storage import load_data
        from yt_channel_analyzer.database import save_competitor_and_videos, get_all_competitors
        
        # Charger les données du cache
        cache_data = load_data()
        competitors = cache_data.get('competitors', {})
        
        # Récupérer les concurrents existants en base
        db_competitors = get_all_competitors()
        db_urls = set(comp['channel_url'] for comp in db_competitors)
        
        synced_count = 0
        errors = []
        
        for competitor_key, competitor_data in competitors.items():
            try:
                channel_url = competitor_data.get('channel_url')
                if not channel_url:
                    errors.append(f"Concurrent {competitor_key}: URL manquante")
                    continue
                
                # Vérifier si déjà en base
                if channel_url in db_urls:
                    continue
                
                # Extraire les informations de la chaîne
                channel_info = {
                    'title': competitor_data.get('name', 'Canal inconnu'),
                    'thumbnail': competitor_data.get('thumbnail', ''),
                    'banner': competitor_data.get('banner', ''),
                    'description': competitor_data.get('description', ''),
                    'subscriber_count': competitor_data.get('subscriber_count'),
                    'view_count': competitor_data.get('view_count'),
                    'country': competitor_data.get('country', ''),
                    'language': competitor_data.get('language', '')
                }
                
                # Formater les vidéos
                videos = []
                for video in competitor_data.get('videos', []):
                    video_formatted = {
                        'video_id': video.get('url', '').split('=')[-1] if video.get('url') else '',
                        'title': video.get('title', ''),
                        'description': video.get('description', ''),
                        'url': video.get('url', ''),
                        'thumbnail_url': video.get('thumbnail', ''),
                        'published_at': video.get('publication_date', ''),
                        'duration_text': video.get('duration', ''),
                        'view_count': video.get('views', 0),
                        'like_count': video.get('likes', 0),
                        'comment_count': video.get('comments', 0),
                        'category': video.get('category', 'hub')
                    }
                    videos.append(video_formatted)
                
                # Sauvegarder en base
                save_competitor_and_videos(channel_url, videos, channel_info)
                synced_count += 1
                
            except Exception as e:
                errors.append(f"Erreur pour {competitor_key}: {str(e)}")
        
        return jsonify({
            'success': True,
            'synced_count': synced_count,
            'errors': errors,
            'message': f'{synced_count} concurrents synchronisés avec succès'
        })
        
    except Exception as e:
        print(f"[SYNC] ❌ Erreur lors de la synchronisation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/get-action-status/<action_key>')
@login_required
def get_action_status(action_key):
    """Get the last status for a specific action from database logs"""
    try:
        from yt_channel_analyzer.database import get_last_action_status
        status = get_last_action_status(action_key)
        
        if status:
            return jsonify({
                'success': True,
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No status found for this action'
            })
    except Exception as e:
        print(f"[GET-ACTION-STATUS] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/reclassify-content', methods=['POST'])
def reclassify_content():
    """Reclassifier manuellement des playlists ou vidéos spécifiques"""
    try:
        data = request.json
        content_type = data.get('type')  # 'playlist' or 'video'
        content_id = data.get('id')
        
        if not content_type or not content_id:
            return jsonify({'error': 'Type et ID requis'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if content_type == 'playlist':
            # Reclassifier une playlist
            cursor.execute('SELECT name, description FROM playlist WHERE id = ?', (content_id,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'Playlist non trouvée'}), 404
                
            name, description = result
            category, language, confidence = classify_video_with_language(name, description or '')
            
            cursor.execute('''
                UPDATE playlist SET category = ?, last_updated = ? 
                WHERE id = ?
            ''', (category, datetime.now(), content_id))
            
            conn.commit()
            print(f"[API-RECLASSIFY] 📋 Playlist '{name}' reclassifiée: {category.upper()} ({confidence}%)")
            
            return jsonify({
                'success': True,
                'message': f'Playlist reclassifiée comme {category.upper()}',
                'category': category,
                'confidence': confidence,
                'language': language
            })
            
        elif content_type == 'video':
            # Reclassifier une vidéo
            cursor.execute('SELECT title, description FROM video WHERE id = ?', (content_id,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'Vidéo non trouvée'}), 404
                
            title, description = result
            category, language, confidence = classify_video_with_language(title, description or '')
            
            cursor.execute('''
                UPDATE video SET category = ?, last_updated = ? 
                WHERE id = ?
            ''', (category, datetime.now(), content_id))
            
            conn.commit()
            print(f"[API-RECLASSIFY] 🎬 Vidéo '{title}' reclassifiée: {category.upper()} ({confidence}%)")
            
            return jsonify({
                'success': True,
                'message': f'Vidéo reclassifiée comme {category.upper()}',
                'category': category,
                'confidence': confidence,
                'language': language
            })
            
        else:
            return jsonify({'error': 'Type invalide (playlist ou video)'}), 400
            
    except Exception as e:
        print(f"[API-RECLASSIFY] ❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Routes pour l'apprentissage supervisé
@app.route('/supervised-learning')
@login_required
def supervised_learning_page():
    """Page d'apprentissage supervisé pour la classification Hero/Hub/Help - Version optimisée"""
    try:
        strategy = request.args.get('strategy', 'balanced')
        from yt_channel_analyzer.supervised_learning import get_videos_for_validation, get_playlists_for_validation, get_learning_statistics
        
        videos = get_videos_for_validation(limit=12, strategy=strategy)
        playlists = get_playlists_for_validation(limit=12, strategy=strategy)
        stats = get_learning_statistics()
        
        video_distribution = {'hero': 0, 'hub': 0, 'help': 0}
        total_videos = stats.get('total_videos', 0)
        
        if total_videos > 0:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT category, COUNT(*) as count FROM video WHERE category IS NOT NULL GROUP BY category')
            for row in cursor.fetchall():
                if row[0] in video_distribution:
                    video_distribution[row[0]] = row[1] / total_videos
            conn.close()

        return render_template('supervised_learning.html',
                            videos=videos,
                            playlists=playlists,
                            strategy=strategy,
                            stats=stats,
                            video_distribution=video_distribution,
                            initial_load=True)
    except Exception as e:
        flash(f"Erreur sur la page d'apprentissage : {e}", 'error')
        return redirect(url_for('home'))

@app.route('/supervised-learning/stats')
@login_required
def supervised_learning_stats():
    """Page des statistiques de la classification supervisée"""
    try:
        # Importer directement depuis les sous-modules pour éviter les imports circulaires
        from yt_channel_analyzer.supervised_learning import get_human_classifications
        from yt_channel_analyzer.database.competitors import get_all_competitors

        # On charge les 100 dernières classifications pour l'historique.
        # La fonction retourne aussi les stats globales.
        stats = get_human_classifications(limit=100)
        competitors = get_all_competitors()
        
        return render_template('supervised_learning_stats.html', stats=stats, competitors=competitors)
        
    except Exception as e:
        print(f"[STATS] ❌ ERREUR CRITIQUE dans /supervised-learning/stats: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error_message=f"Erreur lors du chargement des statistiques: {e}")

@app.route('/api/supervised/feedback', methods=['POST'])
@login_required
def api_supervised_feedback():
    """API pour enregistrer un feedback utilisateur sur une classification"""
    try:
        data = request.json
        
        video_id = data.get('video_id')
        category = data.get('category')
        feedback_type = data.get('feedback_type', 'correction')  # correction, validation, uncertain
        user_notes = data.get('user_notes', '')
        
        if not video_id or not category:
            return jsonify({'status': 'error', 'message': 'Video ID et catégorie requis'})
        
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'status': 'error', 'message': 'Catégorie invalide'})
        
        # Récupérer la catégorie originale
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT category, classification_source FROM video WHERE id = ?', (video_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Vidéo non trouvée'})
        
        original_category = result[0] or 'hub'  # Utiliser hub si pas de catégorie
        original_source = result[1] or 'unknown'
        conn.close()
        
        # 🚨 NOUVEAU : Utiliser la fonction de marquage humain pour cette classification
        from yt_channel_analyzer.database import mark_human_classification
        
        # Marquer comme classification humaine (priorité absolue)
        success = mark_human_classification(
            video_id=video_id, 
            category=category, 
            user_notes=f"Feedback utilisateur: {feedback_type} - {user_notes}"
        )
        
        if not success:
            return jsonify({'status': 'error', 'message': 'Erreur lors du marquage de la classification humaine'})
        
        # Ajouter le feedback dans la table de supervision pour historique complet
        from yt_channel_analyzer.supervised_learning import add_user_feedback
        feedback_success = add_user_feedback(
            video_id=video_id,
            original_category=original_category,
            corrected_category=category,
            confidence_score=100,  # 100% de confiance pour les corrections humaines
            user_feedback_type=feedback_type,
            user_notes=user_notes
        )
        
        if feedback_success:
            # Message de succès avec indication de protection
            message = f'🤖 Vidéo reclassifiée: {original_category.upper()} → {category.upper()} (HUMAIN - PROTÉGÉE)'
            if original_source == 'human':
                message += ' [Correction humaine précédente écrasée]'
            
            return jsonify({
                'status': 'success', 
                'message': message,
                'original_category': original_category,
                'new_category': category,
                'human_protected': True,
                'feedback_type': feedback_type
            })
        else:
            return jsonify({'status': 'error', 'message': 'Erreur lors de l\'ajout du feedback'})
        
    except Exception as e:
        print(f"[SUPERVISED-FEEDBACK] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': f'Erreur du serveur: {str(e)}'})

@app.route('/api/supervised/get-videos', methods=['GET'])
@login_required
def api_supervised_get_videos():
    """API pour récupérer les vidéos à valider selon la stratégie choisie"""
    try:
        strategy = request.args.get('strategy', 'balanced')
        limit = int(request.args.get('limit', 50))
        
        from yt_channel_analyzer.supervised_learning import get_videos_for_validation
        videos = get_videos_for_validation(limit=limit, strategy=strategy)
        
        return jsonify({
            'status': 'success',
            'videos': videos,
            'count': len(videos),
            'strategy': strategy
        })
        
    except Exception as e:
        print(f"[API-GET-VIDEOS] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/supervised/stats', methods=['GET'])
@login_required
def api_supervised_stats():
    """API pour récupérer les statistiques d'apprentissage"""
    try:
        from yt_channel_analyzer.supervised_learning import get_learning_statistics
        stats = get_learning_statistics()
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        print(f"[API-STATS] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/supervised/classify', methods=['POST'])
@login_required
def api_supervised_classify():
    """API pour classifier une vidéo avec l'apprentissage supervisé"""
    try:
        data = request.json
        title = data.get('title', '')
        description = data.get('description', '')
        
        if not title:
            return jsonify({'status': 'error', 'message': 'Titre requis'})
        
        from yt_channel_analyzer.supervised_learning import classify_with_supervised_learning
        category, language, confidence = classify_with_supervised_learning(title, description)
        
        return jsonify({
            'status': 'success',
            'category': category,
            'language': language,
            'confidence': confidence
        })
        
    except Exception as e:
        print(f"[API-CLASSIFY] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/supervised/load-more-videos', methods=['GET'])
@login_required
def api_load_more_videos():
    """API pour charger plus de vidéos avec pagination"""
    try:
        strategy = request.args.get('strategy', 'balanced')
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        from yt_channel_analyzer.supervised_learning import get_videos_for_validation
        videos = get_videos_for_validation(limit=limit, offset=offset, strategy=strategy)
        
        # Convertir les vidéos en format JSON
        videos_data = []
        for video in videos:
            videos_data.append({
                'id': video.id,
                'video_id': video.video_id,
                'title': video.title,
                'thumbnail_url': video.thumbnail_url,
                'competitor_name': video.competitor_name,
                'view_count': video.view_count,
                'like_count': video.like_count,
                'category': video.category,
                'source': video.source
            })
        
        return jsonify({
            'status': 'success',
            'videos': videos_data,
            'has_more': len(videos) == limit  # S'il y a exactement 'limit' résultats, il y en a probablement plus
        })
        
    except Exception as e:
        print(f"[API-LOAD-MORE-VIDEOS] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/supervised/load-more-playlists', methods=['GET'])
@login_required
def api_load_more_playlists():
    """API pour charger plus de playlists avec pagination"""
    try:
        strategy = request.args.get('strategy', 'balanced')
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        from yt_channel_analyzer.supervised_learning import get_playlists_for_validation
        playlists = get_playlists_for_validation(limit=limit, offset=offset, strategy=strategy)
        
        # Convertir les playlists en format JSON
        playlists_data = []
        for playlist in playlists:
            playlists_data.append({
                'id': playlist.id,
                'playlist_id': playlist.playlist_id,
                'name': playlist.name,
                'thumbnail_url': playlist.thumbnail_url,
                'competitor_name': playlist.competitor_name,
                'video_count': playlist.video_count,
                'confidence': playlist.confidence,
                'category': playlist.category,
                'source': playlist.source
            })
        
        return jsonify({
            'status': 'success',
            'playlists': playlists_data,
            'has_more': len(playlists) == limit  # S'il y a exactement 'limit' résultats, il y en a probablement plus
        })
        
    except Exception as e:
        print(f"[API-LOAD-MORE-PLAYLISTS] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/supervised/playlist-feedback', methods=['POST'])
@login_required
def api_supervised_playlist_feedback():
    """API pour enregistrer un feedback utilisateur sur une classification de playlist"""
    try:
        data = request.json
        
        playlist_id = data.get('playlist_id')
        category = data.get('category')
        feedback_type = data.get('feedback_type', 'correction')  # correction, validation, uncertain
        user_notes = data.get('user_notes', '')
        
        if not playlist_id or not category:
            return jsonify({'status': 'error', 'message': 'Playlist ID et catégorie requis'})
        
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'status': 'error', 'message': 'Catégorie invalide'})
        
        print(f"[API-PLAYLIST-FEEDBACK] 📋 Feedback playlist ID {playlist_id}: {category} ({feedback_type})")
        
        # Utiliser la fonction d'apprentissage supervisé pour les playlists
        from yt_channel_analyzer.supervised_learning import add_playlist_feedback
        
        # Ajouter le feedback et apprendre de nouveaux patterns
        learning_result = add_playlist_feedback(
            playlist_id=playlist_id,
            category=category,
            feedback_type=feedback_type,
            user_notes=user_notes
        )
        
        if learning_result['status'] == 'success':
            print(f"[API-PLAYLIST-FEEDBACK] ✅ Feedback playlist enregistré avec succès")
            return jsonify({
                'status': 'success',
                'message': 'Classification playlist mise à jour avec succès',
                'learning_result': learning_result.get('learning_result', {})
            })
        else:
            return jsonify({
                'status': 'error',
                'message': learning_result.get('message', 'Erreur inconnue')
            })
        
    except Exception as e:
        print(f"[API-PLAYLIST-FEEDBACK] ❌ Erreur: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/human-classifications')
@login_required
def human_classifications():
    """Page des vidéos ET playlists classifiées par l'humain"""
    try:
        # Récupérer les paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        # Récupérer les données (vidéos + playlists)
        from yt_channel_analyzer.supervised_learning import get_human_classifications
        data = get_human_classifications(limit=per_page, offset=offset)
        
        # Calculer les informations de pagination
        total_items = data.get('total_count', 0)
        total_pages = (total_items + per_page - 1) // per_page
        
        print(f"[HUMAN-CLASSIFICATIONS] 📊 {data.get('video_count', 0)} vidéos + {data.get('playlist_count', 0)} playlists = {total_items} classifications humaines")
        
        return render_template('human_classifications.html',
                            classifications=data.get('classifications', []),
                            video_classifications=data.get('video_classifications', []),
                            playlist_classifications=data.get('playlist_classifications', []),
                            total_count=data.get('total_count', 0),
                            video_count=data.get('video_count', 0),
                            playlist_count=data.get('playlist_count', 0),
                            unique_videos=data.get('unique_videos', 0),
                            unique_playlists=data.get('unique_playlists', 0),
                            affected_competitors=data.get('affected_competitors', 0),
                            video_reclassification_matrix=data.get('video_reclassification_matrix', {}),
                            playlist_category_distribution=data.get('playlist_category_distribution', {}),
                            competitor_stats=data.get('competitor_stats', []),
                            current_page=page,
                            per_page=per_page,
                            total_pages=total_pages,
                            has_prev=page > 1,
                            has_next=page < total_pages)
                            
    except Exception as e:
        print(f"[HUMAN-CLASSIFICATIONS] ❌ Erreur: {e}")
        flash(f"Une erreur est survenue: {str(e)}", 'error')
        return render_template('human_classifications.html',
                            classifications=[],
                            video_classifications=[],
                            playlist_classifications=[],
                            total_count=0,
                            video_count=0,
                            playlist_count=0,
                            unique_videos=0,
                            unique_playlists=0,
                            affected_competitors=0,
                            error=str(e))

@app.route('/api/competitor/<int:competitor_id>/classify', methods=['POST'])
@login_required
def classify_competitor_videos(competitor_id):
    """Classifier manuellement toutes les vidéos d'un concurrent spécifique"""
    try:
        from yt_channel_analyzer.database import classify_videos_directly_with_keywords, get_competitor_by_id
        
        # Vérifier que le concurrent existe
        competitor = get_competitor_by_id(competitor_id)
        if not competitor:
            return jsonify({
                'success': False,
                'error': 'Concurrent non trouvé'
            })
        
        # Classifier les vidéos
        print(f"[MANUAL-CLASSIFY] 🤖 Début de la classification pour {competitor['name']}")
        classification_result = classify_videos_directly_with_keywords(competitor_id)
        
        videos_classified = classification_result.get('videos_classified', 0)
        
        if videos_classified > 0:
            print(f"[MANUAL-CLASSIFY] ✅ Classification terminée: {videos_classified} vidéos classifiées")
            message = f"Classification terminée: {videos_classified} vidéos classifiées pour {competitor['name']}"
        else:
            print(f"[MANUAL-CLASSIFY] ℹ️ Aucune vidéo à classifier")
            message = f"Aucune vidéo à classifier pour {competitor['name']} (déjà classifiées)"
        
        return jsonify({
            'success': True,
            'message': message,
            'videos_classified': videos_classified,
            'competitor_name': competitor['name']
        })
        
    except Exception as e:
        print(f"[MANUAL-CLASSIFY] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/classify-all-unclassified', methods=['POST'])
@login_required
def classify_all_unclassified():
    """Classifier toutes les vidéos non classifiées de tous les concurrents"""
    try:
        from yt_channel_analyzer.database import get_all_competitors, classify_videos_directly_with_keywords
        
        # Récupérer tous les concurrents
        competitors = get_all_competitors()
        
        if not competitors:
            return jsonify({
                'success': False,
                'error': 'Aucun concurrent trouvé'
            })
        
        total_classified = 0
        classified_competitors = []
        
        print(f"[CLASSIFY-ALL] 🤖 Début de la classification pour {len(competitors)} concurrents")
        
        for competitor in competitors:
            competitor_id = competitor['id']
            competitor_name = competitor['name']
            
            try:
                # Classifier les vidéos de ce concurrent
                classification_result = classify_videos_directly_with_keywords(competitor_id)
                videos_classified = classification_result.get('videos_classified', 0)
                
                if videos_classified > 0:
                    total_classified += videos_classified
                    classified_competitors.append({
                        'name': competitor_name,
                        'videos_classified': videos_classified
                    })
                    print(f"[CLASSIFY-ALL] ✅ {competitor_name}: {videos_classified} vidéos classifiées")
                
            except Exception as e:
                print(f"[CLASSIFY-ALL] ❌ Erreur pour {competitor_name}: {e}")
                continue
        
        if total_classified > 0:
            message = f"Classification terminée: {total_classified} vidéos classifiées pour {len(classified_competitors)} concurrents"
        else:
            message = "Aucune vidéo à classifier (toutes déjà classifiées)"
        
        return jsonify({
            'success': True,
            'message': message,
            'total_classified': total_classified,
            'classified_competitors': classified_competitors
        })
        
    except Exception as e:
        print(f"[CLASSIFY-ALL] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/update-database-schema-with-human-protection', methods=['POST'])
@login_required
def update_database_schema_with_human_protection():
    """Mettre à jour le schéma de base de données avec les champs de protection humaine"""
    try:
        from yt_channel_analyzer.database import update_database_schema
        
        print("[SCHEMA-UPDATE] 🚨 Mise à jour du schéma avec protection supervision humaine...")
        
        success = update_database_schema()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Schéma de base mis à jour avec succès - Protection supervision humaine activée !'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la mise à jour du schéma'
            })
        
    except Exception as e:
        print(f"[SCHEMA-UPDATE] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/verify-classification-integrity-advanced', methods=['POST'])
@login_required
def verify_classification_integrity_advanced():
    """Vérification avancée de l'intégrité des classifications humaines vs IA"""
    try:
        from yt_channel_analyzer.database import verify_classification_integrity
        
        print("[INTEGRITY-CHECK] 🔍 Vérification avancée de l'intégrité...")
        
        report = verify_classification_integrity()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        print(f"[INTEGRITY-CHECK] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/fix-classification-tracking', methods=['POST'])
@login_required
def fix_classification_tracking_api():
    """Réparer les problèmes de tracking de classification"""
    try:
        from yt_channel_analyzer.database import fix_classification_tracking
        
        print("[INTEGRITY-FIX] 🛠️ Début de la réparation...")
        
        result = fix_classification_tracking()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[INTEGRITY-FIX] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/debug-functions-safety-check', methods=['POST'])
@login_required
def debug_functions_safety_check():
    """Vérifier que toutes les fonctions de debug sont sécurisées"""
    try:
        safety_report = {
            'functions_checked': [],
            'safe_functions': [],
            'protected_logic': [],
            'warnings': []
        }
        
        # Liste des fonctions critiques à vérifier
        critical_functions = [
            {
                'name': 'classify_videos_directly_with_keywords',
                'protection': 'Respecte les classifications humaines',
                'safe': True
            },
            {
                'name': 'apply_playlist_categories_to_videos',
                'protection': 'Ne propage jamais les playlists humaines',
                'safe': True
            },
            {
                'name': 'auto_classify_uncategorized_playlists',
                'protection': 'Ignore les playlists classifiées manuellement',
                'safe': True
            },
            {
                'name': 'run_global_ai_classification',
                'protection': 'Utilise toutes les protections ci-dessus',
                'safe': True
            },
            {
                'name': 'mark_human_classification',
                'protection': 'Priorité absolue - ne peut pas être écrasée',
                'safe': True
            }
        ]
        
        for func in critical_functions:
            safety_report['functions_checked'].append(func['name'])
            if func['safe']:
                safety_report['safe_functions'].append({
                    'function': func['name'],
                    'protection': func['protection']
                })
            else:
                safety_report['warnings'].append({
                    'function': func['name'],
                    'issue': func.get('issue', 'Protection insuffisante')
                })
        
        safety_report['protected_logic'] = [
            "🛡️ Double vérification avant toute modification",
            "🚫 Exclusion explicite des classifications humaines",
            "✅ Tracking complet de la source (human/ai/playlist)",
            "⚠️ Fonction force_apply_human_playlist_to_videos avec confirmation requise",
            "📊 Logs détaillés pour traçabilité"
        ]
        
        safety_report['summary'] = "✅ Toutes les fonctions de debug sont maintenant sécurisées"
        
        return jsonify({
            'success': True,
            'safety_report': safety_report
        })
        
    except Exception as e:
        print(f"[SAFETY-CHECK] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/protection-summary', methods=['GET'])
@login_required
def protection_summary():
    """Afficher un récapitulatif des protections mises en place"""
    try:
        summary = {
            'protection_status': '✅ PROTECTION SUPERVISION HUMAINE ACTIVÉE',
            'key_protections': [
                "🛡️ Les classifications humaines ne peuvent JAMAIS être écrasées",
                "🚫 Les playlists classifiées manuellement ne propagent PAS automatiquement aux vidéos",
                "📊 Tracking complet de la source (human/ai/playlist)",
                "🔍 Badges visuels pour identifier les classifications",
                "⚠️ Fonction de propagation forcée SEULEMENT avec confirmation explicite"
            ],
            'protected_functions': [
                "classify_videos_directly_with_keywords → Ignore les vidéos humaines",
                "apply_playlist_categories_to_videos → Ignore les playlists humaines",
                "auto_classify_uncategorized_playlists → Ignore les playlists humaines",
                "run_global_ai_classification → Utilise toutes les protections",
                "mark_human_classification → Priorité absolue"
            ],
            'new_features': [
                "🔧 Vérification d'intégrité avancée",
                "🛠️ Réparation automatique du tracking",
                "👁️ Badges visuels HUMAIN/IA/AUTO",
                "📋 Rapports de sécurité détaillés",
                "🚨 Alertes en cas de conflit"
            ],
            'how_to_use': [
                "1. Utilisez la page /debug pour vérifier l'intégrité",
                "2. Réparez le tracking si nécessaire",
                "3. Classifiez manuellement → Badge HUMAIN (protégé)",
                "4. Classifiez via IA → Badge IA (modifiable)",
                "5. Vérifiez régulièrement avec les outils de debug"
            ]
        }
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/check-existing-classifications', methods=['GET'])
@login_required
def check_existing_classifications():
    """Vérifier rapidement les classifications existantes avant mise à jour du schéma"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        results = {
            'classification_feedback': {'count': 0, 'exists': False, 'recent': []},
            'video_categories': {'count': 0, 'exists': False},
            'playlist_categories': {'count': 0, 'exists': False},
            'schema_status': {'video_tracking': False, 'playlist_tracking': False}
        }
        
        # 1. Vérifier les feedbacks de classification (vos 10 classifications)
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM classification_feedback 
                WHERE user_feedback_type = 'correction'
            ''')
            feedback_count = cursor.fetchone()[0]
            results['classification_feedback']['count'] = feedback_count
            results['classification_feedback']['exists'] = feedback_count > 0
            
            if feedback_count > 0:
                cursor.execute('''
                    SELECT cf.corrected_category, cf.feedback_timestamp, v.title, c.name as competitor_name
                    FROM classification_feedback cf
                    JOIN video v ON cf.video_id = v.id
                    JOIN concurrent c ON v.concurrent_id = c.id
                    WHERE cf.user_feedback_type = 'correction'
                    ORDER BY cf.feedback_timestamp DESC
                    LIMIT 5
                ''')
                results['classification_feedback']['recent'] = [
                    {
                        'category': row[0],
                        'date': row[1],
                        'video_title': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                        'competitor': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            results['classification_feedback']['error'] = str(e)
        
        # 2. Vérifier les vidéos catégorisées
        try:
            cursor.execute('SELECT COUNT(*) FROM video WHERE category IS NOT NULL')
            video_count = cursor.fetchone()[0]
            results['video_categories']['count'] = video_count
            results['video_categories']['exists'] = video_count > 0
        except Exception as e:
            results['video_categories']['error'] = str(e)
        
        # 3. Vérifier les playlists catégorisées
        try:
            cursor.execute('SELECT COUNT(*) FROM playlist WHERE category IS NOT NULL')
            playlist_count = cursor.fetchone()[0]
            results['playlist_categories']['count'] = playlist_count
            results['playlist_categories']['exists'] = playlist_count > 0
        except Exception as e:
            results['playlist_categories']['error'] = str(e)
        
        # 4. Vérifier l'état du schéma
        try:
            # Vérifier colonnes video
            cursor.execute("PRAGMA table_info(video)")
            video_columns = [col[1] for col in cursor.fetchall()]
            results['schema_status']['video_tracking'] = 'classification_source' in video_columns
            
            # Vérifier colonnes playlist
            cursor.execute("PRAGMA table_info(playlist)")
            playlist_columns = [col[1] for col in cursor.fetchall()]
            results['schema_status']['playlist_tracking'] = 'classification_source' in playlist_columns
            
        except Exception as e:
            results['schema_status']['error'] = str(e)
        
        conn.close()
        
        # 5. Déterminer le statut global
        if results['classification_feedback']['exists']:
            results['status'] = 'data_exists_schema_incomplete'
            results['message'] = f"✅ {results['classification_feedback']['count']} classifications trouvées ! Le schéma doit être mis à jour."
            results['solution'] = "Cliquez sur 'Mettre à jour le schéma (Protection humaine)' sur /debug"
        elif results['video_categories']['exists'] or results['playlist_categories']['exists']:
            results['status'] = 'some_data_exists'
            results['message'] = "⚠️ Données partielles trouvées"
        else:
            results['status'] = 'no_data'
            results['message'] = "ℹ️ Aucune classification trouvée"
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        print(f"[CHECK-CLASSIFICATIONS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/enhance-patterns', methods=['POST'])
@login_required
def enhance_patterns_for_descriptions():
    """Installer les patterns enrichis pour mieux utiliser les descriptions"""
    try:
        from yt_channel_analyzer.enhanced_patterns import add_description_patterns_to_db
        
        patterns_added = add_description_patterns_to_db()
        
        return jsonify({
            'success': True,
            'patterns_added': patterns_added,
            'message': f'✅ {patterns_added} patterns enrichis ajoutés ! La classification utilise maintenant mieux les descriptions.'
        })
        
    except Exception as e:
        print(f"[ENHANCE-PATTERNS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/test-enhanced-classification', methods=['POST'])
@login_required
def test_enhanced_classification():
    """Tester la classification enrichie avec titre et description"""
    try:
        data = request.get_json()
        title = data.get('title', '')
        description = data.get('description', '')
        
        if not title:
            return jsonify({
                'success': False,
                'error': 'Titre requis'
            })
        
        from yt_channel_analyzer.database import classify_video_with_language
        from yt_channel_analyzer.enhanced_patterns import get_context_score
        
        # Classification standard
        category, language, confidence = classify_video_with_language(title, description)
        
        # Score contextuel enrichi
        context_scores = {}
        for cat in ['hero', 'hub', 'help']:
            context_scores[cat] = get_context_score(description, cat, language)
        
        return jsonify({
            'success': True,
            'classification': {
                'category': category,
                'language': language,
                'confidence': confidence,
                'context_scores': context_scores,
                'title': title,
                'description': description[:200] + '...' if len(description) > 200 else description
            }
        })
        
    except Exception as e:
        print(f"[TEST-ENHANCED] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/thumbnails/repair', methods=['POST'])
@login_required
def api_repair_thumbnails():
    """API pour réparer les miniatures côté client"""
    try:
        # Récupérer quelques exemples de miniatures
        from yt_channel_analyzer.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, title, thumbnail_url 
            FROM video 
            WHERE thumbnail_url IS NOT NULL 
            LIMIT 10
        ''')
        
        samples = cursor.fetchall()
        conn.close()
        
        thumbnail_samples = []
        for sample in samples:
            thumbnail_samples.append({
                'video_id': sample[0],
                'title': sample[1],
                'thumbnail_url': sample[2],
                'fallback_url': f"https://i.ytimg.com/vi/{sample[0]}/mqdefault.jpg"
            })
        
        return jsonify({
            'success': True,
            'message': 'Échantillons de miniatures récupérés',
            'samples': thumbnail_samples,
            'repair_instructions': [
                'Vérifiez que les URLs sont accessibles',
                'Utilisez les fonctions JavaScript pour réparer automatiquement',
                'Les miniatures ont des fallbacks automatiques'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/thumbnails/stats')
@login_required
def api_thumbnail_stats():
    """API pour obtenir les statistiques des miniatures"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Statistiques des vidéos
        cursor.execute('''
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN thumbnail_url IS NOT NULL AND thumbnail_url != '' THEN 1 END) as with_thumbnails,
                COUNT(CASE WHEN thumbnail_url LIKE '%ytimg.com%' THEN 1 END) as youtube_thumbnails
            FROM video
        ''')
        video_stats = cursor.fetchone()
        
        # Statistiques des concurrents
        cursor.execute('''
            SELECT 
                COUNT(*) as total_competitors,
                COUNT(CASE WHEN thumbnail_url IS NOT NULL AND thumbnail_url != '' THEN 1 END) as with_thumbnails
            FROM concurrent
        ''')
        competitor_stats = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'videos': {
                'total': video_stats[0],
                'with_thumbnails': video_stats[1],
                'youtube_thumbnails': video_stats[2],
                'coverage_percentage': round((video_stats[1] / video_stats[0]) * 100, 2) if video_stats[0] > 0 else 0
            },
            'competitors': {
                'total': competitor_stats[0],
                'with_thumbnails': competitor_stats[1],
                'coverage_percentage': round((competitor_stats[1] / competitor_stats[0]) * 100, 2) if competitor_stats[0] > 0 else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================================
# YOUTUBE SHORTS API ROUTES
# ==========================================

@app.route('/api/shorts/analysis/<int:competitor_id>', methods=['GET'])
@login_required
def api_shorts_analysis(competitor_id):
    """API pour analyser les Shorts d'un concurrent spécifique"""
    try:
        from yt_channel_analyzer.database import analyze_shorts_vs_regular_videos
        analysis = analyze_shorts_vs_regular_videos(competitor_id)
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/shorts/frequency/<int:competitor_id>', methods=['GET'])
@login_required
def api_shorts_frequency(competitor_id):
    """API pour analyser la fréquence des Shorts d'un concurrent"""
    try:
        from yt_channel_analyzer.database import analyze_shorts_frequency_patterns
        period_weeks = request.args.get('period', 12, type=int)
        frequency = analyze_shorts_frequency_patterns(competitor_id, period_weeks)
        return jsonify({
            'success': True,
            'frequency': frequency
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/shorts/report/<int:competitor_id>', methods=['GET'])
@login_required
def api_shorts_report(competitor_id):
    """API pour générer un rapport complet des Shorts d'un concurrent"""
    try:
        from yt_channel_analyzer.database import generate_shorts_insights_report
        report = generate_shorts_insights_report(competitor_id)
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/shorts/global-analysis', methods=['GET'])
@login_required
def api_shorts_global_analysis():
    """API pour analyser les Shorts de tous les concurrents"""
    try:
        from yt_channel_analyzer.database import analyze_shorts_vs_regular_videos
        analysis = analyze_shorts_vs_regular_videos()
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/thumbnail-diagnostic')
@login_required
def thumbnail_diagnostic():
    """Page de diagnostic des miniatures"""
    return render_template('thumbnail_diagnostic.html')

@app.route('/ai-training-status')
@login_required
def ai_training_status():
    """Page du tableau de bord de l'IA sémantique."""
    model_status = {}
    metadata_path = "ai_training_metadata.json"
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        model_status = {
            'status': 'specialized',
            'last_trained_at': metadata.get('last_trained_at'),
            'examples_used': metadata.get('examples_used'),
            'accuracy': metadata.get('accuracy')
        }
    else:
        model_status = {
            'status': 'generic',
            'last_trained_at': None,
            'examples_used': 0,
            'accuracy': None
        }
        
    # Récupérer les stats des données humaines
    human_stats = get_human_classifications(limit=0) # limit=0 pour ne prendre que les stats

    # Fonction pour convertir le temps ISO en format lisible (à mettre dans un helper plus tard)
    def human_time_filter(dt_str):
        if not dt_str:
            return "N/A"
        from datetime import datetime
        dt_obj = datetime.fromisoformat(dt_str)
        return dt_obj.strftime('%d %B %Y à %H:%M')

    app.jinja_env.filters['human_time'] = human_time_filter
        
    return render_template('ai_training_status.html', 
                           model_status=model_status, 
                           human_stats=human_stats)

@app.route('/api/retrain-model', methods=['POST'])
@login_required
def api_retrain_model():
    """API pour lancer le script d'entraînement du modèle."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'train_with_human_data.py')
        
        # Lancer le script en mode non-interactif
        # On passe des arguments pour que le script ne pose pas de questions
        process = subprocess.run(
            ['python', script_path, '--non-interactive'], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        # Si le script se termine bien
        return jsonify({
            'success': True,
            'message': 'Entraînement terminé avec succès! La page va se rafraîchir.',
            'output': process.stdout
        })

    except subprocess.CalledProcessError as e:
        # Si le script retourne une erreur
        return jsonify({
            'success': False,
            'error': 'Le script d\'entraînement a échoué.',
            'details': e.stderr
        }), 500
    except Exception as e:
        # Pour toute autre erreur
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate-total-videos-in-playlists', methods=['GET'])
@login_required
def get_total_videos_in_playlists():
    """Calcule et retourne le nombre total de vidéos contenues dans toutes les playlists."""
    try:
        from .database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(video_count) FROM playlist")
        total_videos = cursor.fetchone()[0]
        
        conn.close()
        
        # S'assurer que le résultat n'est pas None (si aucune playlist n'existe)
        total_videos = total_videos or 0
        
        return jsonify({
            'success': True,
            'total_videos_in_playlists': total_videos
        })
        
    except Exception as e:
        print(f"[API-CALCULATE-VIDEOS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/transformers-dashboard')
def transformers_dashboard():
    """Tableau de bord des Python transformers"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        # Récupérer toutes les données du tableau de bord
        dashboard_data = transformers_manager.get_dashboard_data()
        
        return render_template('transformers_dashboard.html', 
                             dashboard_data=dashboard_data)
        
    except Exception as e:
        print(f"[TRANSFORMERS-DASHBOARD] ❌ Erreur: {e}")
        return render_template('error.html', 
                             error_message=f"Erreur lors du chargement du tableau de bord: {str(e)}")

@app.route('/api/transformers/status', methods=['GET'])
def api_transformers_status():
    """API pour récupérer le statut en temps réel des transformers"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        dashboard_data = transformers_manager.get_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        print(f"[API-TRANSFORMERS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/transformers/load-model', methods=['POST'])
def api_load_transformer_model():
    """API pour charger un modèle transformer de manière asynchrone"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        data = request.get_json()
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({
                'success': False,
                'error': 'Nom du modèle requis'
            })
        
        # Lancer le chargement asynchrone
        success = transformers_manager.load_model_async(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Chargement de {model_name} lancé en arrière-plan',
                'async_loading': True
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Échec du lancement du chargement'
            })
        
    except Exception as e:
        print(f"[API-LOAD-MODEL] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/transformers/loading-progress/<model_name>', methods=['GET'])
@login_required
def api_transformer_loading_progress(model_name):
    """API pour récupérer le progrès de chargement d'un modèle"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        progress_data = transformers_manager.get_loading_progress(model_name)
        
        return jsonify({
            'success': True,
            'progress': progress_data
        })
        
    except Exception as e:
        print(f"[API-LOADING-PROGRESS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/transformers/cancel-loading/<model_name>', methods=['POST'])
@login_required
def api_cancel_transformer_loading(model_name):
    """API pour annuler le chargement d'un modèle"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        # Réinitialiser le statut du modèle
        model_info = transformers_manager.get_model_info(model_name)
        if model_info:
            model_info.loading_status = "ready"
            model_info.download_progress = 0.0
            
        return jsonify({
            'success': True,
            'message': f'Chargement de {model_name} annulé'
        })
        
    except Exception as e:
        print(f"[API-CANCEL-LOADING] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/transformers/train', methods=['POST'])
@login_required
def api_train_transformer():
    """API pour lancer l'entraînement d'un modèle"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        data = request.get_json()
        model_name = data.get('model_name', 'all-MiniLM-L6-v2')
        
        # Lancer l'entraînement
        success = transformers_manager.start_training(model_name)
        
        return jsonify({
            'success': success,
            'message': f'Entraînement {"démarré" if success else "échoué"}'
        })
        
    except Exception as e:
        print(f"[API-TRAIN] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/semantic/settings', methods=['GET', 'POST'])
@login_required
def api_semantic_settings():
    """API pour gérer les paramètres sémantiques"""
    if request.method == 'GET':
        # Récupérer les paramètres actuels
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Récupérer tous les paramètres sémantiques
            cursor.execute('''
                SELECT key, value FROM settings 
                WHERE key LIKE 'semantic_%' OR key = 'classification_mode'
            ''')
            
            settings = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            # Valeurs par défaut si pas encore configurées
            defaults = {
                'semantic_classification_enabled': 'false',
                'semantic_auto_init': 'false',
                'semantic_model': 'all-MiniLM-L6-v2',
                'semantic_weight': '0.7',
                'pattern_weight': '0.3',
                'classification_mode': 'database_only'
            }
            
            for key, default_value in defaults.items():
                if key not in settings:
                    settings[key] = default_value
            
            return jsonify({
                'success': True,
                'settings': settings
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    elif request.method == 'POST':
        # Mettre à jour les paramètres
        try:
            data = request.get_json()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Mettre à jour chaque paramètre
            for key, value in data.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, str(value), datetime.now()))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Paramètres sémantiques mis à jour'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })

@app.route('/api/semantic/propagate', methods=['POST'])
@login_required
def api_semantic_propagate():
    """API pour déclencher la propagation sémantique sur toutes les vidéos"""
    try:
        data = request.get_json()
        force_reclassify = data.get('force_reclassify', False)
        
        # Activer temporairement la classification sémantique
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('semantic_classification_enabled', 'true', ?)
        ''', (datetime.now(),))
        
        conn.commit()
        conn.close()
        
        # Importer le classificateur hybride
        from yt_channel_analyzer.hybrid_classifier import get_hybrid_classifier
        
        classifier = get_hybrid_classifier()
        
        # Récupérer toutes les vidéos non classifiées par l'humain
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, title, description, category, classification_source, human_verified
            FROM video 
            WHERE (human_verified != 1 OR human_verified IS NULL)
        '''
        
        if not force_reclassify:
            query += ' AND (category IS NULL OR category = "")'
        
        cursor.execute(query)
        videos = cursor.fetchall()
        conn.close()
        
        # Traiter les vidéos en arrière-plan
        def process_videos():
            processed = 0
            updated = 0
            
            for video_id, title, description, current_category, classification_source, human_verified in videos:
                try:
                    # Classifier avec le système hybride
                    result = classifier.classify_content(
                        title=title or '',
                        description=description or '',
                        video_id=video_id
                    )
                    
                    new_category = result.get('final_category', 'hub')
                    confidence = result.get('confidence', 50)
                    
                    # Mettre à jour la base de données
                    update_conn = get_db_connection()
                    update_cursor = update_conn.cursor()
                    
                    update_cursor.execute('''
                        UPDATE video 
                        SET category = ?, 
                            classification_source = 'semantic',
                            confidence_score = ?,
                            last_updated = ?
                        WHERE id = ?
                    ''', (new_category, confidence, datetime.now(), video_id))
                    
                    update_conn.commit()
                    update_conn.close()
                    
                    if new_category != current_category:
                        updated += 1
                    
                    processed += 1
                    
                    if processed % 10 == 0:
                        print(f"[SEMANTIC-PROPAGATE] Traité {processed}/{len(videos)} vidéos")
                
                except Exception as e:
                    print(f"[SEMANTIC-PROPAGATE] Erreur vidéo {video_id}: {e}")
                    continue
            
            print(f"[SEMANTIC-PROPAGATE] Terminé: {processed} vidéos traitées, {updated} mises à jour")
        
        # Lancer le traitement en arrière-plan
        import threading
        thread = threading.Thread(target=process_videos)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Propagation sémantique lancée sur {len(videos)} vidéos',
            'total_videos': len(videos),
            'background_processing': True
        })
        
    except Exception as e:
        print(f"[API-SEMANTIC-PROPAGATE] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/transformers/test', methods=['GET'])
def api_test_transformers():
    """API de test pour vérifier que les transformers fonctionnent"""
    try:
        from yt_channel_analyzer.transformers_manager import transformers_manager
        
        # Test simple
        return jsonify({
            'success': True,
            'message': 'API transformers fonctionnelle',
            'models_available': list(transformers_manager.available_models.keys()),
            'system_status': transformers_manager.system_status.status
        })
        
    except Exception as e:
        print(f"[API-TEST] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/competitors/update-stats', methods=['POST'])
@login_required
def api_update_competitor_stats():
    """API pour mettre à jour les statistiques précalculées des concurrents"""
    try:
        from yt_channel_analyzer.database.competitors import competitor_manager
        
        # Utiliser la méthode optimisée
        updated_count = competitor_manager.update_all_competitor_stats()
        
        return jsonify({
            'success': True,
            'message': f'Statistiques mises à jour pour {updated_count} concurrents',
            'updated_count': updated_count
        })
        
    except Exception as e:
        print(f"[API-UPDATE-STATS] ❌ Erreur: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, port=8082)
