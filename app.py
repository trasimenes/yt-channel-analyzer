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
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api, autocomplete_youtube_channels_api, get_api_quota_status
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
from yt_channel_analyzer.database import competitors_to_legacy_format, get_all_competitors, save_competitor_and_videos, get_db_connection

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
    return render_template('home_modern.html')

@app.route('/home_old')
@login_required
def home_old():
    return render_template('home.html')

@app.route('/concurrents')
@login_required
def concurrents():
    """Page des concurrents - TOUT vient de la base de données"""
    try:
        # SEULE SOURCE DE VÉRITÉ : Base de données
        from yt_channel_analyzer.database import get_all_competitors_with_videos
        
        db_competitors = get_all_competitors_with_videos()
        
        # Convertir en format compatible avec le template existant
        concurrents_with_keys = []
        for competitor in db_competitors:
            # Utiliser l'ID de la base comme clé
            competitor_key = str(competitor['id'])
            
            # Adapter les données pour le template
            competitor_data = {
                'name': competitor['name'],
                'channel_url': competitor['channel_url'],
                'thumbnail': competitor.get('thumbnail_url', ''),
                'banner': competitor.get('banner_url', ''),
                'description': competitor.get('description', ''),
                'video_count': len(competitor['videos']),
                'subscriber_count': competitor.get('subscriber_count'),
                'view_count': competitor.get('total_views', 0),
                'total_views': competitor.get('total_views', 0),
                'country': competitor.get('country', ''),
                'language': competitor.get('language', ''),
                'last_updated': competitor.get('last_updated', ''),
                'videos': competitor['videos']
            }
            
            concurrents_with_keys.append((competitor_key, competitor_data))
        
        # Trier par date de dernière mise à jour (plus récent en premier)
        concurrents_with_keys.sort(key=lambda x: x[1].get('last_updated', ''), reverse=True)
        
        print(f"[CONCURRENTS] ✅ {len(concurrents_with_keys)} concurrents chargés depuis la BASE DE DONNÉES")
        return render_template('concurrents.html', concurrents=concurrents_with_keys)
        
    except Exception as e:
        print(f"[CONCURRENTS] ❌ Erreur critique lors du chargement depuis la base: {e}")
        import traceback
        traceback.print_exc()
        
        # Retourner une page vide plutôt qu'un fallback vers le cache
        return render_template('concurrents.html', concurrents=[], error=str(e))

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
    
    # Charger les paramètres existants
    current_settings = load_settings()
    return render_template('settings.html', current_settings=current_settings)

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
    """Page de monitoring de l'utilisation de l'API"""
    return render_template('api_usage.html')

@app.route('/api/usage')
@login_required
def get_api_usage():
    """Récupérer les données d'utilisation de l'API au format JSON"""
    try:
        # Charger les données du fichier quota
        quota_data = load_api_quota_data()
        
        # Récupérer les données depuis l'API YouTube si possible
        try:
            from yt_channel_analyzer.youtube_adapter import get_api_quota_status
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
        
        print(f"[AUTOCOMPLETE] 🚫 Exclusion de {len(existing_competitors)} concurrents déjà en base")
        
    except Exception as e:
        print(f"[AUTOCOMPLETE] ⚠️ Erreur récupération concurrents existants: {e}")
        existing_urls = set()
        existing_names = set()
    
    # 🚀 Utiliser l'API YouTube en priorité
    try:
        suggestions = autocomplete_youtube_channels_api(q, max_results=15)  # Plus de résultats pour compenser le filtrage
        if suggestions:
            # Filtrer les suggestions déjà en base
            filtered_suggestions = []
            for suggestion in suggestions:
                suggestion_url = suggestion.get('url', '').lower().strip()
                suggestion_name = suggestion.get('name', '').lower().strip()
                
                # Exclure si l'URL ou le nom existe déjà
                if suggestion_url not in existing_urls and suggestion_name not in existing_names:
                    filtered_suggestions.append(suggestion)
                else:
                    print(f"[AUTOCOMPLETE] 🚫 Exclu (déjà en base): {suggestion.get('name', 'Sans nom')}")
            
            print(f"[API] ✅ {len(filtered_suggestions)}/{len(suggestions)} suggestions après filtrage pour '{q}'")
            return jsonify(filtered_suggestions[:10])  # Limiter à 10 résultats finaux
            
    except Exception as e:
        print(f"[API] ❌ Erreur autocomplete API: {e}")
    
    # Fallback vers le scraping avec filtrage
    try:
        print(f"[SCRAPING] 🔄 Fallback autocomplete pour '{q}'")
        suggestions = autocomplete_youtube_channels(q)
        
        # Filtrer les suggestions du scraping aussi
        filtered_suggestions = []
        for suggestion in suggestions:
            suggestion_url = suggestion.get('url', '').lower().strip()
            suggestion_name = suggestion.get('name', '').lower().strip()
            
            if suggestion_url not in existing_urls and suggestion_name not in existing_names:
                filtered_suggestions.append(suggestion)
        
        return jsonify(filtered_suggestions[:10])
        
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

@app.route('/analyze-channel', methods=['POST'])
@login_required
def analyze_channel():
    """Analyser une nouvelle chaîne depuis le formulaire"""
    try:
        data = request.get_json() if request.is_json else request.form
        channel_url = data.get('channel_url', '').strip()
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de chaîne manquante'})
        
        # Valider l'URL YouTube
        if 'youtube.com' not in channel_url and 'youtu.be' not in channel_url:
            return jsonify({'success': False, 'error': 'URL YouTube invalide'})
        
        # Lancer l'analyse en arrière-plan
        from yt_channel_analyzer.background_tasks import task_manager
        
        # Extraire le nom de la chaîne pour la tâche
        channel_name = extract_channel_name(channel_url)
        
        # Créer la tâche
        task_id = task_manager.create_task(channel_url, f"Analyse - {channel_name}")
        
        # Lancer le scraping en arrière-plan
        task_manager.start_background_scraping(task_id, channel_url)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Analyse lancée en arrière-plan pour {channel_name}',
            'redirect': '/tasks'
        })
        
    except Exception as e:
        print(f"[ANALYZE] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/competitor/<competitor_id>')
@login_required
def competitor_detail(competitor_id):
    """Afficher les détails d'un concurrent spécifique"""
    try:
        print(f"[COMPETITOR-DETAIL] Début pour ID: {competitor_id}")
        
        # Récupérer le concurrent depuis la base de données
        from yt_channel_analyzer.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les informations du concurrent
        cursor.execute('SELECT * FROM concurrent WHERE id = ?', (competitor_id,))
        competitor_row = cursor.fetchone()
        
        if not competitor_row:
            conn.close()
            flash('Concurrent non trouvé', 'error')
            return redirect(url_for('concurrents'))
        
        # Convertir en dictionnaire
        competitor_columns = [desc[0] for desc in cursor.description]
        competitor = dict(zip(competitor_columns, competitor_row))
        
        # Récupérer les vidéos du concurrent
        cursor.execute('''
            SELECT * FROM video 
            WHERE concurrent_id = ? 
            ORDER BY published_at DESC
        ''', (competitor_id,))
        
        videos_rows = cursor.fetchall()
        video_columns = [desc[0] for desc in cursor.description]
        videos = [dict(zip(video_columns, row)) for row in videos_rows]
        
        # CALCULER LES VUES TOTALES
        total_views = sum(video.get('view_count', 0) or 0 for video in videos)
        competitor['total_views'] = total_views
        
        conn.close()
        
        print(f"[COMPETITOR-DETAIL] Concurrent {competitor['name']}: {len(videos)} vidéos chargées, {total_views:,} vues totales")
        
        if not videos:
            # Pas de vidéos, afficher quand même la page avec des stats vides
            stats = {
                'total_videos': 0,
                'paid_percentage': 0,
                'organic_percentage': 0,
                'paid_threshold': load_settings().get('paid_threshold', 10000),
                'performance_matrix': {},
                'hero_count': 0,
                'hub_count': 0,
                'help_count': 0,
                'organic_count': 0,
                'paid_count': 0
            }
            videos_by_category = {'hero': [], 'hub': [], 'help': []}
            
            # Récupérer les playlists du concurrent même s'il n'y a pas de vidéos avec mise à jour automatique
            playlists = auto_update_playlists(competitor_id, competitor['name'], competitor['channel_url'])
            
            return render_template('concurrent_detail.html', 
                                 competitor=competitor, 
                                 stats=stats, 
                                 videos_by_category=videos_by_category,
                                 playlists=playlists)
        
        # AFFICHAGE BASÉ SUR LES VRAIES DONNÉES DE LA BASE
        print(f"[COMPETITOR-DETAIL] Traitement de {len(videos)} vidéos avec catégories réelles")
        
        settings = load_settings()
        paid_threshold = settings.get('paid_threshold', 10000)
        
        # Stats basées sur TOUTES les vidéos avec leurs vraies catégories
        total_videos = len(videos)
        paid_count = sum(1 for v in videos if (v.get('view_count') or 0) >= paid_threshold)
        organic_count = total_videos - paid_count
        
        # Utiliser les vraies données stockées en base
        videos_for_display = []
        for video in videos:  # TOUTES LES VIDÉOS, pas seulement 150
            views = video.get('view_count') or 0
            
            # Utiliser la catégorie stockée en base ou classification par défaut
            category = video.get('category') or 'hub'  # Utiliser la catégorie de la base de données
            
            # Classification basique par mots-clés si pas de catégorie en base
            if not video.get('category'):
                title_lower = (video.get('title') or '').lower()
                if any(word in title_lower for word in ['tutorial', 'how to', 'guide', 'tips', 'help']):
                    category = 'help'
                elif views >= paid_threshold * 1.5:
                    category = 'hero'
                else:
                    category = 'hub'
            
            distribution_type = 'paid' if views >= paid_threshold else 'organic'
            
            video_display = {
                'title': video.get('title', ''),
                'url': video.get('url', ''),
                'views': views,
                'view_count': views,
                'likes': video.get('like_count') or 0,
                'comments': video.get('comment_count') or 0,
                'thumbnail': video.get('thumbnail_url', ''),
                'duration': video.get('duration_text', ''),
                'published_at': video.get('published_at', ''),
                'category': category,
                'distribution_type': distribution_type,
                'confidence': 95 if video.get('category') else 60  # Confiance plus élevée si catégorie en base
            }
            videos_for_display.append(video_display)
        
        # Grouper par catégorie pour l'affichage
        videos_by_category = {'hero': [], 'hub': [], 'help': []}
        for video in videos_for_display:
            category = video.get('category', 'hub')
            if category in videos_by_category:
                # Ajouter le score de performance
                video['performance_score'] = min(10, max(1, int(video.get('view_count', 0) / 10000)))
                videos_by_category[category].append(video)
        
        # Trier chaque catégorie par vues (plus populaires en premier)
        for category in videos_by_category:
            videos_by_category[category].sort(key=lambda x: x.get('view_count', 0), reverse=True)
        
        # Compter par catégorie
        hero_count = len(videos_by_category['hero'])
        hub_count = len(videos_by_category['hub'])
        help_count = len(videos_by_category['help'])
        
        print(f"[COMPETITOR-DETAIL] Statistiques par catégorie:")
        print(f"  🔥 HERO: {hero_count} vidéos")
        print(f"  🏠 HUB: {hub_count} vidéos") 
        print(f"  🆘 HELP: {help_count} vidéos")
        print(f"  💰 PAID: {paid_count} vidéos")
        print(f"  🌱 ORGANIC: {organic_count} vidéos")
        
        # Calculer les médianes pour chaque catégorie
        def calculate_median_views(videos_list):
            if not videos_list:
                return 0
            views = [v.get('view_count', 0) for v in videos_list]
            views.sort()
            n = len(views)
            return views[n//2] if n > 0 else 0
        
        # Organiser par catégorie et type pour la matrice
        performance_matrix = {}
        for category in ['hero', 'hub', 'help']:
            organic_videos = [v for v in videos_for_display if v.get('category') == category and v.get('distribution_type') == 'organic']
            paid_videos = [v for v in videos_for_display if v.get('category') == category and v.get('distribution_type') == 'paid']
            
            organic_median = calculate_median_views(organic_videos)
            paid_median = calculate_median_views(paid_videos)
            
            performance_matrix[category] = {
                'organic_count': len(organic_videos),
                'organic_median': organic_median,
                'paid_count': len(paid_videos),
                'paid_median': paid_median
            }
            
            # Debug de la matrice
            print(f"  📊 {category.upper()}: Organic={len(organic_videos)} vidéos (médiane: {organic_median:,}), Paid={len(paid_videos)} vidéos (médiane: {paid_median:,})")
        
        # Stats finales basées sur les vraies données
        stats = {
            'total_videos': total_videos,
            'paid_percentage': round(paid_count / total_videos * 100, 1) if total_videos > 0 else 0,
            'organic_percentage': round(organic_count / total_videos * 100, 1) if total_videos > 0 else 0,
            'paid_threshold': paid_threshold,
            'performance_matrix': performance_matrix,
            'hero_count': hero_count,
            'hub_count': hub_count,
            'help_count': help_count,
            'organic_count': organic_count,
            'paid_count': paid_count,
            'is_quick_analysis': False  # Maintenant basé sur les vraies données
        }
        
        print(f"[COMPETITOR-DETAIL] 🎯 Statistiques finales calculées: {total_videos} vidéos, {competitor['total_views']:,} vues totales")
        
        # Récupérer les playlists du concurrent avec mise à jour automatique
        playlists = auto_update_playlists(competitor_id, competitor['name'], competitor['channel_url'])
        
        return render_template('concurrent_detail.html', 
                             competitor=competitor, 
                             stats=stats, 
                             videos_by_category=videos_by_category,
                             playlists=playlists)
        
    except Exception as e:
        print(f"[COMPETITOR-DETAIL] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)}"

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
        # Récupérer l'URL de la chaîne
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT channel_url FROM concurrent WHERE id = ?', (competitor_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'Concurrent non trouvé'})
        
        channel_url = result[0]
        
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
        
        # Récupérer les vidéos de chaque playlist et les lier
        print(f"[PLAYLISTS] 🔗 Liaison des vidéos aux playlists...")
        
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
            video_ids = youtube_client.get_playlist_videos(playlist_id, max_results=100)
            
            if video_ids:
                # Lier les vidéos à la playlist
                link_playlist_videos(playlist_db_id, video_ids)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(playlists_data),
            'message': f'{len(playlists_data)} playlists récupérées et liées avec succès'
        })
        
    except Exception as e:
        print(f"[PLAYLISTS] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tag-playlist', methods=['POST'])
@login_required  
def tag_playlist():
    """Tagguer une playlist avec une catégorie (hero/hub/help)"""
    try:
        data = request.get_json()
        playlist_id = data.get('playlist_id')
        category = data.get('category')
        competitor_id = data.get('competitor_id')
        
        if not playlist_id:
            return jsonify({'success': False, 'error': 'ID playlist manquant'})
        
        # Valider la catégorie
        valid_categories = ['hero', 'hub', 'help', None]
        if category not in valid_categories:
            return jsonify({'success': False, 'error': 'Catégorie invalide'})
        
        # Mettre à jour la catégorie de la playlist
        from yt_channel_analyzer.database import update_playlist_category
        update_playlist_category(playlist_id, category)
        
        category_name = category.upper() if category else "Non catégorisée"
        
        return jsonify({
            'success': True,
            'message': f'Playlist marquée comme {category_name} avec succès'
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
        from yt_channel_analyzer.database import auto_classify_uncategorized_playlists
        
        result = auto_classify_uncategorized_playlists(competitor_id)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[AI-CLASSIFY] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Routes ViewStats supprimées - analyse locale maintenant

@app.route('/top-videos')
@login_required
def top_videos():
    """Page du top global des vidéos de tous les concurrents"""
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
        
        # Construire la requête SQL avec tous les critères
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
                   END as organic_status
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE 1=1
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
            'published_hour': 'v.published_at',  # Tri par heure utilise aussi le champ published_at
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
        
        videos = []
        for row in rows:
            # Calculer le ratio engagement
            engagement_ratio = 0
            if row[5]:  # view_count
                engagement_ratio = ((row[6] or 0) + (row[7] or 0)) / row[5] * 100  # (likes + comments) / views * 100
            
            # Calculer le score subjectif moyen
            subjective_scores = [row[12], row[13], row[14]]  # beauty, emotion, info_quality
            avg_subjective_score = sum(s for s in subjective_scores if s) / len([s for s in subjective_scores if s]) if any(subjective_scores) else 0
            
            # Formatage de la durée
            duration_formatted = row[10] or "N/A"
            if row[9]:  # duration_seconds
                minutes = row[9] // 60
                seconds = row[9] % 60
                duration_formatted = f"{minutes}:{seconds:02d}"
            
            # Formatage de la date et heure de publication
            published_at_formatted = "N/A"
            published_hour_formatted = "N/A"
            if row[8]:  # published_at
                try:
                    from datetime import datetime
                    if isinstance(row[8], str):
                        # Parse string date
                        dt = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                        published_at_formatted = dt.strftime('%Y-%m-%d')
                        published_hour_formatted = dt.strftime('%H:%M')
                    else:
                        # Already datetime object
                        published_at_formatted = row[8].strftime('%Y-%m-%d')
                        published_hour_formatted = row[8].strftime('%H:%M')
                except:
                    published_at_formatted = str(row[8])[:10]  # Fallback: first 10 chars
                    published_hour_formatted = "N/A"
            
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
                'published_at_formatted': published_at_formatted,
                'published_hour_formatted': published_hour_formatted,
                'duration_seconds': row[9] or 0,
                'duration_text': duration_formatted,
                'category': row[11] or 'hub',
                'beauty_score': row[12] or 0,
                'emotion_score': row[13] or 0,
                'info_quality_score': row[14] or 0,
                'competitor_name': row[15],
                'competitor_id': row[16],
                'channel_subscribers': row[17] or 0,
                'organic_status': row[18],
                'engagement_ratio': round(engagement_ratio, 2),
                'avg_subjective_score': round(avg_subjective_score, 1)
            }
            videos.append(video)
        
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT concurrent_id) FROM video")
        total_competitors = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM video v
            WHERE v.view_count >= ?
        """, [paid_threshold])
        total_paid_videos = cursor.fetchone()[0]
        
        total_organic_videos = total_videos - total_paid_videos
        
        conn.close()
        
        # Préparer les données pour le template
        stats = {
            'total_videos': total_videos,
            'total_competitors': total_competitors,
            'total_paid_videos': total_paid_videos,
            'total_organic_videos': total_organic_videos,
            'paid_threshold': paid_threshold,
            'shown_videos': len(videos)
        }
        
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
        flash(f'Erreur lors du chargement du top videos: {str(e)}', 'error')
        return redirect(url_for('concurrents'))

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

@app.route('/countries-analysis')
@login_required
def countries_analysis():
    """Page d'analyse par pays"""
    try:
        from yt_channel_analyzer.database import get_all_competitors_with_videos
        
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
                    'country': country,
                    'competitors': [],
                    'total_videos': 0,
                    'total_views': 0,
                    'avg_views_per_video': 0,
                    'competitor_count': 0
                }
            
            # Calculer les statistiques des vidéos
            videos = competitor.get('videos', [])
            competitor_views = competitor.get('total_views', 0)  # Utiliser les vues pré-calculées
            
            countries_data[country]['competitors'].append({
                'name': competitor.get('name'),
                'video_count': len(videos),
                'total_views': competitor_views,
                'avg_views': competitor_views / len(videos) if videos else 0
            })
            
            countries_data[country]['total_videos'] += len(videos)
            countries_data[country]['total_views'] += competitor_views
            countries_data[country]['competitor_count'] += 1
            
            total_videos += len(videos)
            total_views += competitor_views
        
        # Calculer les moyennes par pays
        for country_data in countries_data.values():
            if country_data['total_videos'] > 0:
                country_data['avg_views_per_video'] = country_data['total_views'] / country_data['total_videos']
        
        # Trier par nombre total de vues
        countries_list = sorted(countries_data.values(), key=lambda x: x['total_views'], reverse=True)
        
        global_stats = {
            'total_countries': len(countries_list),
            'total_competitors': len(competitors),
            'total_videos': total_videos,
            'total_views': total_views
        }
        
        print(f"[COUNTRIES-ANALYSIS] ✅ Analyse générée: {len(countries_list)} pays, {len(competitors)} concurrents, {total_videos} vidéos, {total_views:,} vues")
        
        return render_template('countries_analysis.html', 
                             countries=countries_list, 
                             global_stats=global_stats)
        
    except Exception as e:
        print(f"[COUNTRIES-ANALYSIS] ❌ Erreur: {e}")
        return render_template('countries_analysis.html', 
                             countries=[], 
                             global_stats={}, 
                             error=str(e))

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
        patterns = get_classification_patterns()
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
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'})
        
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'success': False, 'error': 'Invalid category'})
        
        from yt_channel_analyzer.database import add_classification_pattern
        success = add_classification_pattern(category, pattern)
        
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
        
        if not category or not pattern:
            return jsonify({'success': False, 'error': 'Category and pattern are required'})
        
        from yt_channel_analyzer.database import remove_classification_pattern
        success = remove_classification_pattern(category, pattern)
        
        if success:
            return jsonify({'success': True, 'message': 'Pattern removed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern not found or could not be removed'})
            
    except Exception as e:
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

@app.route('/api/force-classification', methods=['POST'])
@login_required
def force_classification():
    """Force la propagation des mots-clés configurés sur tous les concurrents"""
    try:
        print(f"[FORCE-CLASSIFICATION] 🚀 Démarrage de la classification forcée...")
        
        from yt_channel_analyzer.database import run_global_ai_classification
        
        result = run_global_ai_classification()
        
        print(f"[FORCE-CLASSIFICATION] ✅ Classification forcée terminée")
        
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
    """Page d'insights et guidelines par pays"""
    try:
        from yt_channel_analyzer.database import generate_country_insights
        
        print("[INSIGHTS] 🔍 Génération des insights...")
        insights_data = generate_country_insights()
        
        print(f"[INSIGHTS] ✅ {insights_data.get('total_countries', 0)} pays analysés, "
              f"{insights_data.get('total_videos_analyzed', 0)} vidéos traitées")
        
        return render_template('insights.html', insights=insights_data)
        
    except Exception as e:
        print(f"[INSIGHTS] ❌ Erreur: {e}")
        return render_template('insights.html', 
                             insights={'insights': {}, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=8081)
