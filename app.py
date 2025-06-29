from datetime import datetime, timedelta
import json
import os
from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from functools import wraps
from dotenv import load_dotenv
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Charger les variables d'environnement depuis .env
load_dotenv()

from yt_channel_analyzer.storage import load_data
from yt_channel_analyzer.analysis import hero_hub_help_matrix
from yt_channel_analyzer.scraper import autocomplete_youtube_channels
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api, autocomplete_youtube_channels_api, get_api_quota_status
from yt_channel_analyzer.auth import verify_credentials, is_authenticated, authenticate_session, logout_session

from yt_channel_analyzer import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8081)

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

@app.route('/api/refresh-thumbnails', methods=['POST'])
@login_required
def refresh_thumbnails():
    """Rafraîchir les vignettes de tous les concurrents"""
    try:
        from yt_channel_analyzer.youtube_api_client import create_youtube_client
        
        # Charger les données des concurrents
        cache = load_cache()
        updated_count = 0
        errors = []
        
        # Créer le client YouTube API
        youtube_client = create_youtube_client()
        
        for competitor_key, competitor_data in cache.items():
            try:
                channel_url = competitor_data.get('channel_url', '')
                if not channel_url:
                    continue
                
                print(f"[REFRESH] Mise à jour thumbnail pour: {competitor_data.get('name', 'Unknown')}")
                
                # Récupérer les nouvelles informations de la chaîne
                channel_info = youtube_client.get_channel_info(channel_url)
                
                if channel_info:
                    updated_something = False
                    
                    # Mettre à jour le thumbnail (avatar)
                    if channel_info.get('thumbnail'):
                        old_thumbnail = competitor_data.get('thumbnail', '')
                        new_thumbnail = channel_info['thumbnail']
                        
                        if old_thumbnail != new_thumbnail:
                            competitor_data['thumbnail'] = new_thumbnail
                            updated_something = True
                            print(f"[REFRESH] ✅ Avatar mis à jour pour {competitor_data.get('name')}")
                    
                    # Mettre à jour la bannière
                    if channel_info.get('banner'):
                        old_banner = competitor_data.get('banner', '')
                        new_banner = channel_info['banner']
                        
                        if old_banner != new_banner:
                            competitor_data['banner'] = new_banner
                            updated_something = True
                            print(f"[REFRESH] ✅ Bannière mise à jour pour {competitor_data.get('name')}")
                    
                    if updated_something:
                        competitor_data['thumbnail_updated'] = datetime.now().isoformat()
                        updated_count += 1
                    else:
                        print(f"[REFRESH] ℹ️ Images inchangées pour {competitor_data.get('name')}")
                        
            except Exception as e:
                error_msg = f"Erreur pour {competitor_data.get('name', 'Unknown')}: {str(e)}"
                errors.append(error_msg)
                print(f"[REFRESH] ❌ {error_msg}")
        
        # Sauvegarder les modifications
        if updated_count > 0:
            save_cache(cache)
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'total_competitors': len(cache),
            'errors': errors,
            'message': f'{updated_count} vignettes mises à jour avec succès'
        })
        
    except Exception as e:
        print(f"[REFRESH] Erreur générale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh-single-thumbnail', methods=['POST'])
@login_required
def refresh_single_thumbnail():
    """Rafraîchir la vignette d'un seul concurrent"""
    try:
        from yt_channel_analyzer.youtube_api_client import create_youtube_client
        
        data = request.get_json()
        competitor_id = data.get('competitor_id')
        
        if not competitor_id:
            return jsonify({'success': False, 'error': 'ID du concurrent manquant'}), 400
        
        # Charger les données
        cache = load_cache()
        
        if competitor_id not in cache:
            return jsonify({'success': False, 'error': 'Concurrent non trouvé'}), 404
        
        competitor_data = cache[competitor_id]
        channel_url = competitor_data.get('channel_url', '')
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de la chaîne manquante'}), 400
        
        print(f"[REFRESH] Mise à jour des images pour: {competitor_data.get('name', 'Unknown')}")
        
        # Créer le client YouTube API et récupérer les nouvelles informations
        youtube_client = create_youtube_client()
        channel_info = youtube_client.get_channel_info(channel_url)
        
        if not channel_info:
            return jsonify({'success': False, 'error': 'Impossible de récupérer les informations de la chaîne'}), 500
        
        # Mettre à jour les images
        updated_something = False
        updates = {}
        
        # Mettre à jour le thumbnail (avatar)
        if channel_info.get('thumbnail'):
            old_thumbnail = competitor_data.get('thumbnail', '')
            new_thumbnail = channel_info['thumbnail']
            
            if old_thumbnail != new_thumbnail:
                competitor_data['thumbnail'] = new_thumbnail
                updated_something = True
                updates['thumbnail'] = {'old': old_thumbnail, 'new': new_thumbnail}
                print(f"[REFRESH] ✅ Avatar mis à jour pour {competitor_data.get('name')}")
        
        # Mettre à jour la bannière
        if channel_info.get('banner'):
            old_banner = competitor_data.get('banner', '')
            new_banner = channel_info['banner']
            
            if old_banner != new_banner:
                competitor_data['banner'] = new_banner
                updated_something = True
                updates['banner'] = {'old': old_banner, 'new': new_banner}
                print(f"[REFRESH] ✅ Bannière mise à jour pour {competitor_data.get('name')}")
        
        if updated_something:
            competitor_data['thumbnail_updated'] = datetime.now().isoformat()
        
        # Sauvegarder
        save_cache(cache)
        
        return jsonify({
            'success': True,
            'updated': updated_something,
            'updates': updates,
            'message': 'Images mises à jour avec succès' if updated_something else 'Images déjà à jour'
        })
        
    except Exception as e:
        print(f"[REFRESH] Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

if __name__ == '__main__':
    app.run(debug=True, port=8081)
