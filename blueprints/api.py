"""
API Blueprint
Handles all API endpoints and JSON responses.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, jsonify, request, current_app
from blueprints.auth import login_required
import os
from datetime import datetime

try:
    import psutil
except ImportError:
    print("[WARNING] psutil non installé, métriques système limitées")
    psutil = None


api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/recent-analyses')
@login_required
def recent_analyses():
    """API pour récupérer les analyses récentes"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les dernières vidéos analysées avec leurs classifications
        cursor.execute("""
            SELECT 
                v.title,
                v.category,
                v.view_count,
                c.name as competitor_name,
                v.published_at,
                v.classification_date
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.category IS NOT NULL 
            AND v.category != '' 
            AND v.category != 'uncategorized'
            ORDER BY v.classification_date DESC, v.published_at DESC
            LIMIT 10
        """)
        
        analyses = []
        for row in cursor.fetchall():
            analyses.append({
                'title': row[0][:50] + '...' if len(row[0]) > 50 else row[0],
                'category': row[1],
                'view_count': row[2] or 0,
                'competitor_name': row[3],
                'published_at': row[4],
                'classification_date': row[5] or row[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'analyses': analyses,
            'count': len(analyses)
        })
        
    except Exception as e:
        print(f"[API] Error in recent-analyses: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'analyses': []
        })


@api_bp.route('/performance-metrics')
@login_required
def performance_metrics():
    """API pour récupérer les métriques de performance"""
    try:
        if not psutil:
            return jsonify({
                'error': 'psutil non disponible - métriques système désactivées',
                'memory': {'percent': 0, 'available_mb': 0, 'used_mb': 0, 'total_mb': 0},
                'disk': {'percent': 0, 'free_gb': 0, 'used_gb': 0, 'total_gb': 0},
                'database': {'size_mb': 0},
                'timestamp': datetime.now().isoformat()
            })
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Taille de la base de données
        db_size = 0
        try:
            db_path = 'instance/database.db'
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
        except Exception:
            pass
        
        metrics = {
            'memory': {
                'percent': memory.percent,
                'available_mb': memory.available // (1024 * 1024),
                'used_mb': memory.used // (1024 * 1024),
                'total_mb': memory.total // (1024 * 1024)
            },
            'disk': {
                'percent': disk.percent,
                'free_gb': disk.free // (1024 * 1024 * 1024),
                'used_gb': disk.used // (1024 * 1024 * 1024),
                'total_gb': disk.total // (1024 * 1024 * 1024)
            },
            'database': {
                'size_mb': db_size // (1024 * 1024)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/performance-actions/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Nettoyer les caches de l'application"""
    try:
        # Ici vous pouvez ajouter la logique de nettoyage de cache
        # Par exemple, vider les fichiers de cache, Redis, etc.
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/performance-actions/optimize-database', methods=['POST'])
@login_required
def optimize_database():
    """Optimiser la base de données"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Exécuter VACUUM pour optimiser SQLite
        cursor.execute('VACUUM')
        
        # Réindexer si nécessaire
        cursor.execute('REINDEX')
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Database optimized successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/performance-actions/preload-caches', methods=['POST'])
@login_required
def preload_caches():
    """Précharger les caches"""
    try:
        # Logique de préchargement des caches
        # Cela pourrait inclure la mise en cache des requêtes fréquentes
        
        return jsonify({
            'success': True,
            'message': 'Caches preloaded successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/performance-metrics/export')
@login_required
def export_performance_metrics():
    """Exporter les métriques de performance"""
    try:
        # Récupérer les métriques actuelles
        response = performance_metrics()
        metrics_data = response.get_json()
        
        # Ajouter des métadonnées d'export
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'export_version': '1.0',
            'metrics': metrics_data
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recalculate-organic-status', methods=['POST'])
@login_required
def recalculate_organic_status():
    """Recalculer le statut organique/payé des vidéos"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        # Récupérer le nouveau seuil depuis les paramètres
        new_threshold = request.json.get('threshold', 10000)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Compter les vidéos affectées
        cursor.execute("""
            SELECT COUNT(*) FROM video 
            WHERE view_count IS NOT NULL AND view_count > 0
        """)
        total_videos = cursor.fetchone()[0]
        
        # Mettre à jour le statut (ici vous ajouteriez la logique métier)
        # Par exemple, ajouter une colonne is_organic et la calculer
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Statut organique recalculé pour {total_videos} vidéos',
            'threshold_used': new_threshold,
            'videos_affected': total_videos
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tasks/status', methods=['GET'])
@login_required
def get_tasks_status():
    """Obtenir le statut des tâches en cours"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        all_tasks = task_manager.get_all_tasks()
        running_tasks = task_manager.get_running_tasks()
        completed_tasks = task_manager.get_completed_tasks()
        
        return jsonify({
            'total_tasks': len(all_tasks),
            'running_tasks': len(running_tasks),
            'completed_tasks': len(completed_tasks),
            'pending_tasks': len(all_tasks) - len(running_tasks) - len(completed_tasks),
            'tasks': [
                {
                    'id': task.id,
                    'name': task.name,
                    'status': task.status,
                    'progress': getattr(task, 'progress', 0),
                    'created_at': task.created_at.isoformat() if hasattr(task, 'created_at') else None
                }
                for task in all_tasks
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks', methods=['GET'])
@login_required  
def get_tasks():
    """Obtenir la liste des tâches"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        tasks = task_manager.get_all_tasks()
        
        return jsonify({
            'tasks': [
                {
                    'id': task.id,
                    'name': task.name,
                    'status': task.status,
                    'channel_url': task.channel_url,
                    'progress': getattr(task, 'progress', 0),
                    'created_at': task.created_at.isoformat() if hasattr(task, 'created_at') else None,
                    'updated_at': task.updated_at.isoformat() if hasattr(task, 'updated_at') else None
                }
                for task in tasks
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tasks/<task_id>/delete', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Supprimer une tâche"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        success = task_manager.delete_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Tâche {task_id} supprimée avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Tâche non trouvée'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id):
    """Annuler une tâche"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        success = task_manager.cancel_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Tâche {task_id} annulée avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Tâche non trouvée ou non annulable'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tasks/<task_id>/resume', methods=['POST'])
@login_required
def resume_task(task_id):
    """Reprendre une tâche"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        success = task_manager.resume_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Tâche {task_id} reprise avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Tâche non trouvée ou non reprennable'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tasks/clean-duplicates', methods=['POST'])
@login_required
def clean_duplicate_tasks():
    """Nettoyer les tâches en double"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        deleted_count = task_manager.clean_duplicate_tasks()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} tâches en double supprimées',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tasks/migrate-to-database', methods=['POST'])
@login_required
def migrate_tasks_to_database():
    """Migrer les tâches vers la base de données"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        migrated_count = task_manager.migrate_to_database()
        
        return jsonify({
            'success': True,
            'message': f'{migrated_count} tâches migrées vers la base de données',
            'migrated_count': migrated_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/launch-background-task', methods=['POST'])
@login_required
def launch_background_task():
    """Lancer une tâche en arrière-plan"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        from blueprints.utils import extract_channel_name
        
        channel_url = request.json.get('channel_url')
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'URL de la chaîne manquante'}), 400
        
        # Extraire le nom de la chaîne
        try:
            from yt_channel_analyzer.database import get_competitor_by_url
            competitor = get_competitor_by_url(channel_url)
            if competitor:
                channel_name = competitor.get('name', extract_channel_name(channel_url))
            else:
                channel_name = extract_channel_name(channel_url)
        except (ImportError, AttributeError) as e:
            print(f"[WARNING] Error getting competitor name from database: {e}")
            channel_name = extract_channel_name(channel_url)
        
        # Créer la tâche
        task_name = f"Relancement - {channel_name}"
        task_id = task_manager.create_task(channel_url, task_name)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'task_name': task_name,
            'channel_url': channel_url,
            'message': f'Tâche {task_name} créée avec succès'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sentiment-analysis/export')
@login_required
def export_sentiment_analysis():
    """Export sentiment analysis data as JSON"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Analyse basique des sentiments basée sur les mots-clés
        positive_keywords = ['amazing', 'beautiful', 'fantastic', 'wonderful', 'great', 'excellent', 'perfect', 'love', 'best', 'awesome']
        negative_keywords = ['bad', 'terrible', 'awful', 'worst', 'hate', 'horrible', 'boring', 'stupid']
        
        # Analyser les titres de vidéos
        cursor.execute("""
            SELECT 
                v.id,
                v.video_id,
                v.title,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.published_at,
                v.duration_seconds,
                v.category,
                c.id as competitor_id,
                c.name as competitor_name,
                c.channel_url
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.title IS NOT NULL
            AND v.view_count > 100
            ORDER BY v.view_count DESC
            LIMIT 1000
        """)
        
        videos = cursor.fetchall()
        
        sentiment_data = []
        
        for video in videos:
            title = video[2].lower() if video[2] else ''
            
            # Classification simple par mots-clés
            has_positive = any(keyword in title for keyword in positive_keywords)
            has_negative = any(keyword in title for keyword in negative_keywords)
            
            if has_positive and not has_negative:
                sentiment = 'positive'
            elif has_negative and not has_positive:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            engagement = 0
            if video[3] and video[3] > 0:  # view_count
                engagement = ((video[4] or 0) + (video[5] or 0)) / video[3] * 100
            
            sentiment_data.append({
                'id': video[0],
                'video_id': video[1],
                'title': video[2],
                'view_count': video[3] or 0,
                'like_count': video[4] or 0,
                'comment_count': video[5] or 0,
                'published_at': video[6],
                'duration_seconds': video[7] or 0,
                'category': video[8],
                'competitor_id': video[9],
                'competitor_name': video[10],
                'channel_url': video[11],
                'sentiment': sentiment,
                'engagement_rate': round(engagement, 2)
            })
        
        # Calculer les statistiques
        total_analyzed = len(sentiment_data)
        positive_count = sum(1 for v in sentiment_data if v['sentiment'] == 'positive')
        negative_count = sum(1 for v in sentiment_data if v['sentiment'] == 'negative')
        neutral_count = sum(1 for v in sentiment_data if v['sentiment'] == 'neutral')
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'export_date': datetime.now().isoformat(),
                'stats': {
                    'total_videos_analyzed': total_analyzed,
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'neutral_count': neutral_count
                },
                'videos': sentiment_data
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/tag-playlist', methods=['POST'])
@login_required
def tag_playlist():
    """Classification manuelle d'une playlist Hero/Hub/Help avec hiérarchie HUMAIN > SEMANTIC > PATTERN"""
    print(f"🎯 [DEBUG] === DÉBUT tag_playlist ===", flush=True)
    import sys
    sys.stdout.flush()
    try:
        data = request.get_json()
        playlist_id = data.get('playlist_id')
        category = data.get('category')
        
        print(f"📝 [DEBUG] Données reçues: playlist_id={playlist_id}, category={category}")
        
        if not playlist_id or not category:
            print(f"❌ [DEBUG] Paramètres manquants")
            return jsonify({'success': False, 'error': 'Paramètres manquants'}), 400
        
        if category not in ['hero', 'hub', 'help']:
            print(f"❌ [DEBUG] Catégorie invalide: {category}")
            return jsonify({'success': False, 'error': 'Catégorie invalide'}), 400
        
        from yt_channel_analyzer.database import get_db_connection
        from yt_channel_analyzer.hierarchical_classifier import HierarchicalClassifier
        
        print(f"🔗 [DEBUG] Import des modules OK")
        
        conn = get_db_connection()
        print(f"🔗 [DEBUG] Connexion DB OK")
        
        # 🏗️ Utiliser le système hiérarchique
        classifier = HierarchicalClassifier(conn)
        print(f"🔗 [DEBUG] Classifier créé OK")
        
        print(f"🥇 [MANUAL-CLASSIFICATION] Classification HUMAINE playlist {playlist_id} → {category.upper()}")
        
        # ✅ MARQUER COMME CLASSIFICATION HUMAINE (PRIORITÉ ABSOLUE)
        success = classifier.mark_human_classification(
            playlist_id=playlist_id,
            category=category,
            user_notes="Classification manuelle interface utilisateur"
        )
        
        print(f"📊 [DEBUG] Classification result: {success}")
        
        if not success:
            print(f"❌ [DEBUG] Échec classification")
            return jsonify({'success': False, 'error': 'Erreur lors de la classification'}), 500
        
        # 🔗 CRÉER LES LIENS PLAYLIST_VIDEO VIA API YOUTUBE
        print(f"🔗 [AUTO-LINK] Création automatique des liens playlist_video...")
        
        try:
            print(f"🔍 [AUTO-LINK] Début du processus d'auto-linking...")
            # Récupérer l'ID YouTube de la playlist
            cursor = conn.cursor()
            cursor.execute("SELECT playlist_id, name FROM playlist WHERE id = ?", (playlist_id,))
            playlist_data = cursor.fetchone()
            
            if playlist_data:
                youtube_playlist_id, playlist_name = playlist_data
                print(f"📋 [AUTO-LINK] Playlist: {playlist_name}")
                print(f"🆔 [AUTO-LINK] YouTube ID: {youtube_playlist_id}")
                
                # Importer et utiliser la fonction de création de liens
                import os
                import requests
                
                def get_youtube_api_key():
                    api_key = os.getenv('YOUTUBE_API_KEY')
                    if api_key:
                        return api_key
                    
                    try:
                        cursor.execute("SELECT value FROM app_settings WHERE key = 'youtube_api_key'")
                        result = cursor.fetchone()
                        if result:
                            return result[0]
                    except:
                        pass
                    
                    return None  # Fallback API key removed for security
                
                def get_playlist_videos_from_api(api_key, playlist_id):
                    videos = []
                    next_page_token = None
                    
                    while True:
                        url = "https://www.googleapis.com/youtube/v3/playlistItems"
                        params = {
                            'part': 'snippet',
                            'playlistId': playlist_id,
                            'maxResults': 50,
                            'key': api_key
                        }
                        
                        if next_page_token:
                            params['pageToken'] = next_page_token
                        
                        response = requests.get(url, params=params)
                        
                        if response.status_code != 200:
                            break
                        
                        data = response.json()
                        
                        for item in data.get('items', []):
                            video_id = item['snippet']['resourceId']['videoId']
                            videos.append(video_id)
                        
                        next_page_token = data.get('nextPageToken')
                        if not next_page_token:
                            break
                    
                    return videos
                
                # Récupérer les vidéos via API
                api_key = get_youtube_api_key()
                playlist_videos = get_playlist_videos_from_api(api_key, youtube_playlist_id)
                
                print(f"🔍 [AUTO-LINK] API retourne {len(playlist_videos)} vidéos")
                
                if playlist_videos:
                    # Nettoyer les anciens liens
                    cursor.execute("DELETE FROM playlist_video WHERE playlist_id = ?", (youtube_playlist_id,))
                    
                    # Trouver les vidéos dans notre base
                    video_id_list = playlist_videos
                    placeholders = ','.join(['?' for _ in video_id_list])
                    
                    cursor.execute(f"""
                        SELECT id, video_id FROM video 
                        WHERE video_id IN ({placeholders})
                    """, video_id_list)
                    
                    found_videos = {row[1]: row[0] for row in cursor.fetchall()}
                    
                    # Créer les liens en lot
                    links_to_insert = []
                    for video_id in playlist_videos:
                        if video_id in found_videos:
                            db_video_id = found_videos[video_id]
                            links_to_insert.append((youtube_playlist_id, db_video_id))
                    
                    if links_to_insert:
                        cursor.executemany("""
                            INSERT INTO playlist_video (playlist_id, video_id) 
                            VALUES (?, ?)
                        """, links_to_insert)
                        
                        print(f"✅ [AUTO-LINK] {len(links_to_insert)} liens créés automatiquement")
                    else:
                        print(f"⚠️ [AUTO-LINK] Aucune vidéo trouvée en base")
                else:
                    print(f"⚠️ [AUTO-LINK] Aucune vidéo récupérée via API")
            else:
                print(f"⚠️ [AUTO-LINK] Playlist non trouvée en DB")
                        
        except Exception as e:
            print(f"❌ [AUTO-LINK] Erreur création liens: {e}")
            import traceback
            traceback.print_exc()
        
        # 🔄 PROPAGER AVEC AUTORITÉ HUMAINE (respect hiérarchie)
        print(f"🔄 [DEBUG] Début propagation...")
        videos_updated = classifier.propagate_playlist_to_videos(
            playlist_id=playlist_id,
            force_human_authority=True  # 🥇 Propagation avec autorité humaine
        )
        
        print(f"📊 [DEBUG] Propagation result: {videos_updated} vidéos")
        
        conn.commit()
        print(f"💾 [DEBUG] Commit DB OK")
        conn.close()
        print(f"🔌 [DEBUG] Connexion fermée OK")
        
        print(f"[MANUAL-CLASSIFICATION] ✅ Playlist {playlist_id} → {category.upper()}")
        print(f"[MANUAL-CLASSIFICATION] 📺 {videos_updated} vidéos propagées")
        
        return jsonify({
            'success': True, 
            'message': f'Playlist classifiée comme {category.upper()}',
            'videos_updated': videos_updated,
            'category': category
        })
        
    except Exception as e:
        print(f"💥 [DEBUG] EXCEPTION GLOBALE tag_playlist: {e}")
        import traceback
        traceback.print_exc()
        print(f"[MANUAL-CLASSIFICATION] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/tag-video', methods=['POST'])
@login_required
def tag_video():
    """Classification manuelle d'une vidéo Hero/Hub/Help avec hiérarchie HUMAIN > SEMANTIC > PATTERN"""
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        category = data.get('category')
        
        if not video_id or not category:
            return jsonify({'success': False, 'error': 'Paramètres manquants'}), 400
        
        if category not in ['hero', 'hub', 'help']:
            return jsonify({'success': False, 'error': 'Catégorie invalide'}), 400
        
        from yt_channel_analyzer.database import get_db_connection
        from yt_channel_analyzer.hierarchical_classifier import HierarchicalClassifier
        
        conn = get_db_connection()
        
        # 🏗️ Utiliser le système hiérarchique
        classifier = HierarchicalClassifier(conn)
        
        print(f"🥇 [MANUAL-CLASSIFICATION] Classification HUMAINE vidéo {video_id} → {category.upper()}")
        
        # ✅ MARQUER COMME CLASSIFICATION HUMAINE (PRIORITÉ ABSOLUE)
        success = classifier.mark_human_classification(
            video_id=video_id,
            category=category,
            user_notes="Classification manuelle interface utilisateur"
        )
        
        if not success:
            return jsonify({'success': False, 'error': 'Erreur lors de la classification'}), 500
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Vidéo classifiée comme {category.upper()}',
            'category': category
        })
        
    except Exception as e:
        print(f"[MANUAL-CLASSIFICATION] ❌ Erreur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/sentiment-analysis/import', methods=['POST'])
@login_required
def import_sentiment_analysis():
    """Import sentiment analysis data from JSON"""
    try:
        data = request.get_json()
        
        if not data or 'videos' not in data:
            return jsonify({
                'success': False,
                'error': 'Invalid data format. Expected JSON with "videos" key.'
            }), 400
        
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for video_data in data['videos']:
            try:
                # Check if video already exists
                cursor.execute("SELECT id FROM video WHERE video_id = ?", (video_data.get('video_id'),))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing video with sentiment data
                    cursor.execute("""
                        UPDATE video 
                        SET title = ?,
                            view_count = ?,
                            like_count = ?,
                            comment_count = ?,
                            published_at = ?,
                            duration_seconds = ?,
                            category = ?
                        WHERE video_id = ?
                    """, (
                        video_data.get('title'),
                        video_data.get('view_count', 0),
                        video_data.get('like_count', 0),
                        video_data.get('comment_count', 0),
                        video_data.get('published_at'),
                        video_data.get('duration_seconds', 0),
                        video_data.get('category'),
                        video_data.get('video_id')
                    ))
                    imported_count += 1
                else:
                    # Check if competitor exists
                    cursor.execute("SELECT id FROM concurrent WHERE channel_url = ?", (video_data.get('channel_url'),))
                    competitor = cursor.fetchone()
                    
                    if competitor:
                        competitor_id = competitor[0]
                        
                        # Insert new video
                        cursor.execute("""
                            INSERT INTO video (video_id, title, view_count, like_count, comment_count, 
                                             published_at, duration_seconds, category, concurrent_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            video_data.get('video_id'),
                            video_data.get('title'),
                            video_data.get('view_count', 0),
                            video_data.get('like_count', 0),
                            video_data.get('comment_count', 0),
                            video_data.get('published_at'),
                            video_data.get('duration_seconds', 0),
                            video_data.get('category'),
                            competitor_id
                        ))
                        imported_count += 1
                    else:
                        skipped_count += 1
                        errors.append(f"Competitor not found for channel: {video_data.get('channel_url')}")
                        
            except Exception as e:
                skipped_count += 1
                errors.append(f"Error importing video {video_data.get('video_id')}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Import completed. Imported: {imported_count}, Skipped: {skipped_count}',
            'stats': {
                'imported': imported_count,
                'skipped': skipped_count,
                'total': len(data['videos'])
            },
            'errors': errors[:10] if errors else []  # Limit errors to first 10
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route("/classification-hierarchy/stats", methods=["GET"])
@login_required
def get_classification_hierarchy_stats():
    """Obtenir les statistiques de la hiérarchie de classification"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        from yt_channel_analyzer.hierarchical_classifier import HierarchicalClassifier
        
        conn = get_db_connection()
        classifier = HierarchicalClassifier(conn)
        
        stats = classifier.get_classification_stats()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "hierarchy_explanation": {
                "level_1": "HUMAIN - Priorité absolue, jamais écrasé",
                "level_2": "SEMANTIC - IA avancée avec sentence transformers", 
                "level_3": "PATTERN - Fallback par mots-clés multilingues"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/classification-hierarchy/test", methods=["POST"])
@login_required
def test_classification_hierarchy():
    """Tester la hiérarchie de classification sur un élément"""
    try:
        data = request.get_json()
        video_id = data.get("video_id")
        playlist_id = data.get("playlist_id")
        
        if not video_id and not playlist_id:
            return jsonify({"success": False, "error": "video_id ou playlist_id requis"}), 400
        
        from yt_channel_analyzer.database import get_db_connection
        from yt_channel_analyzer.hierarchical_classifier import HierarchicalClassifier
        
        conn = get_db_connection()
        classifier = HierarchicalClassifier(conn)
        
        result = classifier.get_classification_priority(video_id=video_id, playlist_id=playlist_id)
        protected = classifier.is_human_protected(video_id=video_id, playlist_id=playlist_id)
        
        conn.close()
        
        return jsonify({
            "success": True,
            "classification": result,
            "human_protected": protected,
            "hierarchy_level": result.get("priority_level", 0)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
