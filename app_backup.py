from datetime import date, datetime, timedelta
import json
import os
from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from functools import wraps
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

from yt_channel_analyzer.storage import load_data
from yt_channel_analyzer.analysis import hero_hub_help_matrix
from yt_channel_analyzer.scraper import tor_scrape_youtube_videos, autocomplete_youtube_channels
from yt_channel_analyzer.selenium_scraper import get_video_data, get_channel_video_links, get_channel_videos_data
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api, autocomplete_youtube_channels_api, get_api_quota_status
from yt_channel_analyzer.auth import verify_credentials, is_authenticated, authenticate_session, logout_session

app = Flask(__name__, static_folder='static')

# Configuration sécurisée
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key-change-me')
app.permanent_session_lifetime = timedelta(hours=24)

# Configuration du cache
CACHE_DIR = "cache_recherches"
CACHE_FILE = os.path.join(CACHE_DIR, "recherches.json")

def login_required(f):
    """Décorateur pour protéger les routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated(session):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_cache_dir():
    """Créer le dossier de cache s'il n'existe pas"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def load_cache():
    """Charger le cache des recherches"""
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[DEBUG] Erreur lecture cache: {e}")
            return {}
    return {}

def save_cache(cache_data):
    """Sauvegarder le cache des recherches"""
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Cache sauvegardé: {len(cache_data)} recherches")
    except Exception as e:
        print(f"[DEBUG] Erreur sauvegarde cache: {e}")

def get_channel_key(channel_url):
    """Extraire une clé unique pour une chaîne YouTube"""
    # Normaliser l'URL pour créer une clé unique
    if "@" in channel_url:
        # Format @nom
        return channel_url.split("@")[-1].split("/")[0].lower()
    elif "/c/" in channel_url:
        # Format /c/nom
        return channel_url.split("/c/")[-1].split("/")[0].lower()
    elif "/user/" in channel_url:
        # Format /user/nom
        return channel_url.split("/user/")[-1].split("/")[0].lower()
    elif "/channel/" in channel_url:
        # Format /channel/ID
        return channel_url.split("/channel/")[-1].split("/")[0].lower()
    else:
        # Fallback: utiliser l'URL complète
        return channel_url.replace("https://", "").replace("http://", "").replace("/", "_").lower()

def filter_videos_by_date(videos, filter_period, filter_year=None, filter_month=None):
    """Filtrer les vidéos selon les critères de date"""
    if filter_period == "all":
        return videos
    
    filtered_videos = []
    current_date = datetime.now()
    
    for video in videos:
        video_date = parse_video_date(video.get('publication_date', ''))
        if not video_date:
            continue
            
        include_video = False
        
        if filter_period == "last_30":
            include_video = (current_date - video_date).days <= 30
        elif filter_period == "last_90":
            include_video = (current_date - video_date).days <= 90
        elif filter_period == "last_year":
            include_video = (current_date - video_date).days <= 365
        elif filter_period == "year" and filter_year:
            include_video = video_date.year == int(filter_year)
        elif filter_period == "month" and filter_year and filter_month:
            include_video = (video_date.year == int(filter_year) and 
                           video_date.month == int(filter_month))
        
        if include_video:
            filtered_videos.append(video)
    
    return filtered_videos

def parse_video_date(date_str):
    """Parser les différents formats de date YouTube"""
    if not date_str:
        return None
        
    try:
        # Format "il y a X jours/semaines/mois"
        if "il y a" in date_str.lower():
            current_date = datetime.now()
            if "jour" in date_str:
                days = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=days)
            elif "semaine" in date_str:
                weeks = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(weeks=weeks)
            elif "mois" in date_str:
                months = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=months*30)
            elif "an" in date_str:
                years = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=years*365)
        
        # Format "X ago" (anglais)
        elif "ago" in date_str.lower():
            current_date = datetime.now()
            if "day" in date_str:
                days = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=days)
            elif "week" in date_str:
                weeks = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(weeks=weeks)
            elif "month" in date_str:
                months = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=months*30)
            elif "year" in date_str:
                years = int(''.join(filter(str.isdigit, date_str)))
                return current_date - timedelta(days=years*365)
        
        # Format direct "28 mai 2025"
        # Pour l'instant, on retourne la date actuelle si on ne peut pas parser
        return datetime.now()
        
    except Exception:
        return None

def extract_channel_name(channel_url):
    """Extraire le nom de la chaîne depuis l'URL"""
    try:
        if "@" in channel_url:
            return channel_url.split("@")[-1].split("/")[0]
        elif "/c/" in channel_url:
            return channel_url.split("/c/")[-1].split("/")[0]
        elif "/user/" in channel_url:
            return channel_url.split("/user/")[-1].split("/")[0]
        else:
            return "Chaîne inconnue"
    except:
        return "Chaîne inconnue"

def calculate_total_views(videos):
    """Calculer le total des vues en convertissant les chaînes en nombres"""
    total = 0
    for video in videos:
        views = video.get('views', '')
        if isinstance(views, str) and views:
            # Nettoyer la chaîne et convertir en nombre
            clean_views = views.replace(',', '').replace(' ', '').replace('vues', '').strip()
            try:
                # Gérer les suffixes k, K, M
                if clean_views.endswith(('k', 'K')):
                    total += float(clean_views[:-1]) * 1000
                elif clean_views.endswith(('M', 'm')):
                    total += float(clean_views[:-1]) * 1000000
                else:
                    total += int(clean_views)
            except (ValueError, TypeError):
                continue
        elif isinstance(views, (int, float)):
            total += views
    return int(total)

def format_number(num):
    """Formater un nombre avec des suffixes k/M"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}k"
    else:
        return str(num)

def load_settings():
    """Charger les paramètres depuis le fichier de configuration"""
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Valeurs par défaut
        return {
            'paid_threshold': 10000,
            'industry': 'tourism',
            'auto_classify': True,
            'max_videos': 30,
            'cache_duration': 24
        }

def save_settings(settings_data):
    """Sauvegarder les paramètres dans le fichier de configuration"""
    try:
        with open('settings.json', 'w') as f:
            json.dump(settings_data, f, indent=2)
        print(f"[SETTINGS] Paramètres sauvegardés dans settings.json")
    except Exception as e:
        print(f"[SETTINGS] Erreur lors de la sauvegarde: {e}")

def generate_competitor_stats(classified_videos, paid_threshold):
    """Générer les statistiques pour un concurrent"""
    if not classified_videos:
        return {}
        
    total = len(classified_videos)
    
    # Compter par catégorie
    hero_count = sum(1 for v in classified_videos if v.get('category') == 'hero')
    hub_count = sum(1 for v in classified_videos if v.get('category') == 'hub')
    help_count = sum(1 for v in classified_videos if v.get('category') == 'help')
    
    # Compter organic vs paid
    paid_count = sum(1 for v in classified_videos if v.get('distribution_type') == 'paid')
    organic_count = total - paid_count
    
    # Performance par catégorie et type
    performance_matrix = {
        'hero': {'paid': [], 'organic': []},
        'hub': {'paid': [], 'organic': []},
        'help': {'paid': [], 'organic': []}
    }
    
    for video in classified_videos:
        category = video.get('category', 'hub')
        dist_type = video.get('distribution_type', 'organic')
        views = int(video.get('views', 0)) if isinstance(video.get('views'), (int, str)) and str(video.get('views')).replace(',', '').isdigit() else 0
        
        if category in performance_matrix and dist_type in performance_matrix[category]:
            performance_matrix[category][dist_type].append(views)
    
    # Calculer les médianes pour la matrice de performance
    def safe_median(values):
        if not values:
            return 0
        values.sort()
        n = len(values)
        return values[n//2] if n % 2 == 1 else (values[n//2-1] + values[n//2]) // 2
    
    performance_stats = {}
    for category in performance_matrix:
        performance_stats[category] = {
            'paid_median': safe_median(performance_matrix[category]['paid']),
            'paid_count': len(performance_matrix[category]['paid']),
            'organic_median': safe_median(performance_matrix[category]['organic']),
            'organic_count': len(performance_matrix[category]['organic'])
        }
    
    return {
        'hero_count': hero_count,
        'hub_count': hub_count,
        'help_count': help_count,
        'hero_percentage': round(hero_count / total * 100, 1) if total > 0 else 0,
        'hub_percentage': round(hub_count / total * 100, 1) if total > 0 else 0,
        'help_percentage': round(help_count / total * 100, 1) if total > 0 else 0,
        'paid_count': paid_count,
        'organic_count': organic_count,
        'paid_percentage': round(paid_count / total * 100, 1) if total > 0 else 0,
        'organic_percentage': round(organic_count / total * 100, 1) if total > 0 else 0,
        'performance_matrix': performance_stats,
        'total_videos': total,
        'paid_threshold': paid_threshold
    }

def save_competitor_data(channel_url, videos):
    """Sauvegarder les données d'un concurrent dans le cache"""
    try:
        cache_data = load_cache()
        channel_key = get_channel_key(channel_url)
        channel_name = extract_channel_name(channel_url)
        
        # Si la chaîne existe déjà, fusionner les données
        if channel_key in cache_data:
            existing_data = cache_data[channel_key]
            print(f"[CACHE] Chaîne {channel_name} déjà en cache, fusion des données...")
            
            # Fusionner les vidéos (éviter les doublons par URL)
            existing_video_urls = {v.get('url', '') for v in existing_data.get('videos', [])}
            new_videos = [v for v in videos if v.get('url', '') not in existing_video_urls]
            
            existing_data['videos'].extend(new_videos)
            existing_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existing_data['total_videos'] = len(existing_data['videos'])
            
            # Recalculer le total des vues
            total_views = calculate_total_views(existing_data['videos'])
            existing_data['total_views'] = format_number(total_views)
            
            print(f"[CACHE] {len(new_videos)} nouvelles vidéos ajoutées, total: {existing_data['total_videos']}, vues: {existing_data['total_views']}")
        else:
            # Nouvelle chaîne
            total_views = calculate_total_views(videos)
            print(f"[CACHE] Nouvelle chaîne {channel_name} ajoutée au cache")
            cache_data[channel_key] = {
                'name': channel_name,
                'channel_url': channel_url,
                'videos': videos,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_videos': len(videos),
                'total_views': format_number(total_views),
                'first_analyzed': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        save_cache(cache_data)
        print(f"[CACHE] Données sauvegardées pour {channel_name}")
        
    except Exception as e:
        print(f"[CACHE] Erreur lors de la sauvegarde: {e}")

TEMPLATE = """
<!doctype html>
<title>YouTube Channel Analyzer</title>
<h1>YouTube Channel Analyzer</h1>
<form method="get">
  Start date: <input type="date" name="start_date" value="{{ request.args.get('start_date', '') }}">
  End date: <input type="date" name="end_date" value="{{ request.args.get('end_date', '') }}">
  <input type="submit" value="Filter">
</form>
<table border="1">
  <tr><th>Channel</th><th>Hero (videos/views)</th><th>Hub (videos/views)</th><th>Help (videos/views)</th></tr>
  {% for r in results %}
    <tr>
      <td>{{ r.name }}</td>
      <td>{{ r.counts.hero }} / {{ r.views.hero }}</td>
      <td>{{ r.counts.hub }} / {{ r.views.hub }}</td>
      <td>{{ r.counts.help }} / {{ r.views.help }}</td>
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_credentials(username, password):
            authenticate_session(session)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('home'))
        else:
            flash('Identifiants incorrects', 'error')
            return render_template('login_modern.html', error='Identifiants incorrects')
    
    # Si déjà connecté, rediriger vers l'accueil
    if is_authenticated(session):
        return redirect(url_for('home'))
    
    return render_template('login_modern.html')

@app.route('/logout')
def logout():
    logout_session(session)
    flash('Déconnexion réussie', 'info')
    return redirect(url_for('login'))

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
    cache_data = load_cache()
    # Passer les couples (key, data) pour avoir accès aux clés dans le template
    concurrents_with_keys = list(cache_data.items())
    
    # Trier par date de dernière mise à jour (plus récent en premier)
    concurrents_with_keys.sort(key=lambda x: x[1].get('last_updated', ''), reverse=True)
    
    print(f"[CONCURRENTS] {len(concurrents_with_keys)} concurrents trouvés dans le cache")
    return render_template('concurrents.html', concurrents=concurrents_with_keys)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Sauvegarder les paramètres
        settings_data = {
            'paid_threshold': int(request.form.get('paid_threshold', 10000)),
            'industry': request.form.get('industry', 'tourism'),
            'auto_classify': 'auto_classify' in request.form,
            'max_videos': int(request.form.get('max_videos', 30)),
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

@app.route('/competitor/<competitor_id>')
@login_required  
def competitor_detail(competitor_id):
    cache_data = load_cache()
    
    # Trouver le concurrent par clé de cache
    competitor = None
    for key, data in cache_data.items():
        if key == competitor_id or data.get('name', '').lower().replace(' ', '') == competitor_id.lower():
            competitor = data
            break
    
    if not competitor:
        return "Concurrent introuvable", 404
        
    settings_data = load_settings()
    paid_threshold = settings_data.get('paid_threshold', 10000)
    
    # Classifier les vidéos avec l'IA
    try:
        from yt_channel_analyzer.ai_classifier import classify_videos_batch
        classified_videos = classify_videos_batch(competitor['videos'], paid_threshold)
    except Exception as e:
        print(f"[ERROR] Erreur lors de la classification: {e}")
        # Fallback simple sans classification IA
        classified_videos = []
        for video in competitor.get('videos', []):
            views_str = str(video.get('views', '0')).replace(',', '').replace(' ', '')
            try:
                views_num = int(views_str) if views_str.isdigit() else 0
            except:
                views_num = 0
                
            video_with_classification = video.copy()
            video_with_classification.update({
                'category': 'hub',  # Par défaut
                'confidence': 50,
                'distribution_type': 'paid' if views_num > paid_threshold else 'organic',
                'views_numeric': views_num,
                'performance_score': 5.0
            })
            classified_videos.append(video_with_classification)
    
    # Générer les statistiques
    stats = generate_competitor_stats(classified_videos, paid_threshold)
    
    # Organiser les vidéos par catégorie
    videos_by_category = {
        'hero': [v for v in classified_videos if v.get('category') == 'hero'],
        'hub': [v for v in classified_videos if v.get('category') == 'hub'],
        'help': [v for v in classified_videos if v.get('category') == 'help']
    }
    
    return render_template('concurrent_detail.html',
                         competitor=competitor,
                         stats=stats,
                         videos_by_category=videos_by_category,
                         classified_videos=classified_videos)

@app.route('/api/patterns', methods=['GET'])
@login_required
def get_patterns():
    """API pour récupérer les patterns actuels"""
    try:
        from yt_channel_analyzer.ai_classifier import HubHeroHelpClassifier
        classifier = HubHeroHelpClassifier()
        return jsonify(classifier.patterns)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/patterns', methods=['POST'])
@login_required
def update_patterns():
    """API pour mettre à jour les patterns"""
    try:
        from yt_channel_analyzer.ai_classifier import HubHeroHelpClassifier
        classifier = HubHeroHelpClassifier()
        
        data = request.get_json()
        action = data.get('action')
        category = data.get('category')
        pattern = data.get('pattern')
        
        if action == 'add' and category and pattern:
            success = classifier.add_pattern(category, pattern)
            return jsonify({'success': success})
        elif action == 'remove' and category and pattern:
            success = classifier.remove_pattern(category, pattern)
            return jsonify({'success': success})
        else:
            return jsonify({'error': 'Paramètres manquants'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tag-video', methods=['POST'])
@login_required
def tag_video():
    """API pour tagger une vidéo et apprendre automatiquement"""
    try:
        from yt_channel_analyzer.ai_classifier import HubHeroHelpClassifier
        classifier = HubHeroHelpClassifier()
        
        data = request.get_json()
        title = data.get('title')
        category = data.get('category')
        competitor_id = data.get('competitor_id')
        video_url = data.get('video_url')
        
        if not all([title, category, competitor_id, video_url]):
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        # Apprendre depuis cette vidéo
        classifier.learn_from_video(title, category)
        
        # Mettre à jour le cache avec le nouveau tag
        cache_data = load_cache()
        if competitor_id in cache_data:
            for video in cache_data[competitor_id]['videos']:
                if video.get('url') == video_url:
                    video['manual_category'] = category
                    break
            save_cache(cache_data)
        
        return jsonify({'success': True, 'message': f'Vidéo taggée comme {category.upper()}'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyser', methods=['POST'])
@login_required
def analyser():
    chaine = request.form.get('chaine')
    data = load_data()
    competitors = data.get('competitors', {}) or {}
    comp = next((c for c in competitors.values() if c and c.get('name', '').lower() == (chaine or '').lower()), None)
    if not comp:
        return render_template('result.html', error="Chaîne non trouvée")
    counts, views = hero_hub_help_matrix(comp)
    return render_template('result.html', chaine=comp['name'], counts=counts, views=views)

@app.route('/scraper', methods=['POST'])
@login_required
def scraper():
    channel_url = request.form.get('channel_url')
    max_videos = int(request.form.get('max_videos', 10))
    use_api = request.form.get('use_api', 'true') == 'true'  # Par défaut, utiliser l'API
    
    if not channel_url:
        return render_template('scraper_result.html', error="L'URL de la chaîne est requise.", videos=None)
    
    try:
        # Récupérer les vidéos existantes du cache pour cette chaîne
        cache_data = load_cache()
        channel_key = get_channel_key(channel_url)
        existing_videos = []
        
        if channel_key in cache_data:
            existing_videos = cache_data[channel_key].get('videos', [])
            print(f"[CACHE] {len(existing_videos)} vidéos trouvées en cache pour {channel_key}")
        
        # Si max_videos = 0, on veut toutes les vidéos (mode illimité)
        video_limit = max_videos  # Passer 0 pour le mode illimité, sinon la limite demandée
        
        # 🚀 UTILISER L'API YOUTUBE en priorité
        if use_api:
            print(f"[API] 🚀 Utilisation de l'API YouTube pour {channel_url}")
            try:
                videos = get_channel_videos_data_api(channel_url, video_limit)
                
                if videos:
                    print(f"[API] ✅ {len(videos)} vidéos récupérées via API YouTube")
                    
                    # Afficher les statistiques du quota
                    quota_stats = get_api_quota_status()
                    print(f"[API] 📊 Quota utilisé: {quota_stats['quota_used']}/{quota_stats['daily_limit']} unités")
                    
                    # Sauvegarder automatiquement dans le cache des concurrents
                    save_competitor_data(channel_url, videos)
                    
                    return render_template('scraper_result.html', 
                                         videos=videos, 
                                         channel_url=channel_url,
                                         api_used=True,
                                         quota_stats=quota_stats)
                else:
                    print("[API] ⚠️ Aucune vidéo trouvée via API, tentative de fallback...")
                    
            except Exception as api_error:
                print(f"[API] ❌ Erreur API YouTube: {api_error}")
                print("[API] 🔄 Fallback vers l'API YouTube incrémentale...")
        
        # Fallback vers API YouTube en mode incrémental
        print(f"[API-FALLBACK] 🔧 Utilisation de l'API YouTube incrémentale pour {channel_url}")
        from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api_incremental_background
        videos = get_channel_videos_data_api_incremental_background(
            channel_url, 
            existing_videos, 
            max_videos=video_limit  # Passer 0 pour toutes les vidéos
        )
        
        if not videos:
            return render_template('scraper_result.html', 
                                 error="Aucune vidéo trouvée sur cette chaîne.", 
                                 videos=None)
        
        # Sauvegarder automatiquement dans le cache des concurrents
        save_competitor_data(channel_url, videos)
        
        # Calculer le nombre de nouvelles vidéos
        new_videos_count = len(videos) - len(existing_videos)
        print(f"[API-FALLBACK] {len(videos)} vidéos totales ({new_videos_count} nouvelles + {len(existing_videos)} existantes)")
        
        return render_template('scraper_result.html', 
                             videos=videos, 
                             channel_url=channel_url,
                             api_used=True)
        
    except Exception as e:
        return render_template('scraper_result.html', error=str(e), videos=None)

@app.route('/autocomplete')
@login_required
def autocomplete():
    q = request.args.get('q', '')
    if not q.strip():
        return jsonify([])
    
    # 🚀 Utiliser l'API YouTube en priorité
    try:
        suggestions = autocomplete_youtube_channels_api(q, max_results=10)
        if suggestions:
            print(f"[API] ✅ {len(suggestions)} suggestions trouvées via API YouTube pour '{q}'")
            return jsonify(suggestions)
    except Exception as e:
        print(f"[API] ❌ Erreur autocomplete API: {e}")
    
    # Fallback vers le scraping
    print(f"[SCRAPING] 🔄 Fallback autocomplete pour '{q}'")
    suggestions = autocomplete_youtube_channels(q)
    return jsonify(suggestions)

@app.route('/api/delete-competitor', methods=['POST'])
@login_required
def api_delete_competitor():
    """API pour supprimer un concurrent"""
    try:
        data = request.get_json()
        competitor_id = data.get('competitor_id')
        
        if not competitor_id:
            return jsonify({'success': False, 'error': 'ID concurrent manquant'})
        
        # Charger les données du cache
        cache_data = load_cache()
        
        if competitor_id not in cache_data:
            return jsonify({'success': False, 'error': 'Concurrent non trouvé'})
        
        # Supprimer le concurrent
        competitor_name = cache_data[competitor_id].get('name', competitor_id)
        del cache_data[competitor_id]
        
        # Sauvegarder
        save_cache(cache_data)
        
        return jsonify({'success': True, 'message': f'Concurrent {competitor_name} supprimé avec succès'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/background-analysis', methods=['POST'])
@login_required
def start_background_analysis():
    """Lance une analyse en arrière-plan"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        data = request.get_json()
        channel_url = data.get('channel_url')
        channel_name = data.get('channel_name', 'Canal sans nom')
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de la chaîne manquante'})
        
        # Créer la tâche
        task_id = task_manager.create_task(channel_url, channel_name)
        
        # Lancer le scraping en arrière-plan
        task_manager.start_background_scraping(task_id, channel_url)
        
        return jsonify({
            'success': True, 
            'task_id': task_id,
            'message': f'Analyse en arrière-plan lancée pour {channel_name}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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

@app.route('/api/tasks/<task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Récupère une tâche spécifique"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        task = task_manager.get_task(task_id)
        if task:
            return jsonify(task.to_dict())
        else:
            return jsonify({'error': 'Tâche non trouvée'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id):
    """Annule une tâche"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        task_manager.cancel_task(task_id)
        return jsonify({'success': True, 'message': 'Tâche annulée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/<task_id>/resume', methods=['POST'])
@login_required
def resume_task(task_id):
    """Reprend une tâche depuis son état sauvegardé"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': 'Tâche non trouvée'})
        
        if task.status == 'running':
            return jsonify({'success': False, 'error': 'Tâche déjà en cours'})
        
        # Reprendre la tâche depuis le JSON sauvegardé
        task_manager.resume_task(task_id)
        return jsonify({'success': True, 'message': 'Tâche reprise avec succès'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
        
        # Extraire le nom de la chaîne depuis le cache ou l'URL
        channel_name = "Canal"
        try:
            cache_data = load_cache()
            channel_key = get_channel_key(channel_url)
            if channel_key in cache_data:
                channel_name = cache_data[channel_key].get('name', extract_channel_name(channel_url))
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

if __name__ == '__main__':
    app.run(debug=True, port=8080)
