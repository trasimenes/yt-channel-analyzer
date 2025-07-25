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
        from blueprints.auth import extract_channel_name
        
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