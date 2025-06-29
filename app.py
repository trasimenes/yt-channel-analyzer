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
from yt_channel_analyzer.database import competitors_to_legacy_format, get_all_competitors, save_competitor_and_videos

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
                'view_count': competitor.get('view_count'),
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
        tasks = task_manager.get_all_tasks()
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
        
        conn.close()
        
        print(f"[COMPETITOR-DETAIL] Concurrent {competitor['name']}: {len(videos)} vidéos chargées")
        
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
            
            return render_template('concurrent_detail.html', 
                                 competitor=competitor, 
                                 stats=stats, 
                                 videos_by_category=videos_by_category)
        
        # AFFICHAGE IMMÉDIAT : Stats de base sans classification IA lourde
        print(f"[COMPETITOR-DETAIL] Affichage immédiat de {len(videos)} vidéos")
        
        settings = load_settings()
        paid_threshold = settings.get('paid_threshold', 10000)
        
        # Stats rapides basées sur les vues seulement
        total_videos = len(videos)
        paid_count = sum(1 for v in videos if (v.get('view_count') or 0) >= paid_threshold)
        organic_count = total_videos - paid_count
        
        # Classification ultra-simple pour affichage immédiat
        videos_for_display = []
        for i, video in enumerate(videos[:150]):  # Limiter à 150 vidéos pour l'affichage
            views = video.get('view_count') or 0
            
            # Classification basique par mots-clés et vues
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
                'distribution_type': distribution_type
            }
            videos_for_display.append(video_display)
        
        # Grouper par catégorie pour l'affichage
        videos_by_category = {'hero': [], 'hub': [], 'help': []}
        for video in videos_for_display:
            category = video.get('category', 'hub')
            if category in videos_by_category:
                videos_by_category[category].append(video)
        
        # Compter par catégorie
        hero_count = len(videos_by_category['hero'])
        hub_count = len(videos_by_category['hub'])
        help_count = len(videos_by_category['help'])
        
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
            
            performance_matrix[category] = {
                'organic_count': len(organic_videos),
                'organic_median': calculate_median_views(organic_videos),
                'paid_count': len(paid_videos),
                'paid_median': calculate_median_views(paid_videos)
            }
        
        # Stats finales pour affichage immédiat
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
            'is_quick_analysis': True  # Flag pour indiquer que c'est une analyse rapide
        }
        
        return render_template('concurrent_detail.html', 
                             competitor=competitor, 
                             stats=stats, 
                             videos_by_category=videos_by_category)
        
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

if __name__ == '__main__':
    app.run(debug=True, port=8081)
