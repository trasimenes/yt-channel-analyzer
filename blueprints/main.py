"""
Main Blueprint
Handles core application routes including home, dashboard, and navigation.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, redirect, url_for, session
from blueprints.auth import login_required


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def home():
    """Page d'accueil principale"""
    from yt_channel_analyzer.database import get_db_connection
    import sqlite3
    
    # Initialiser le mode développeur si pas déjà fait
    if 'dev_mode' not in session:
        session['dev_mode'] = False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Statistiques rapides pour le dashboard
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        total_competitors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM playlist")
        total_playlists = cursor.fetchone()[0]
        
        # Compter les classifications IA (vidéos avec catégorie non vide)
        cursor.execute("SELECT COUNT(*) FROM video WHERE category IS NOT NULL AND category != '' AND category != 'uncategorized'")
        ai_classifications = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            'total_channels': total_competitors,  # Template expects 'total_channels'
            'total_competitors': total_competitors,  # Keep for backward compatibility
            'total_videos': total_videos,
            'total_playlists': total_playlists,
            'ai_classifications': ai_classifications
        }
        
        return render_template('home_sneat_pro.html', 
                             stats=stats,
                             dev_mode=session.get('dev_mode', False))
                             
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in home: {e}")
        return render_template('home_sneat_pro.html', 
                             stats={'total_channels': 0, 'total_competitors': 0, 'total_videos': 0, 'total_playlists': 0, 'ai_classifications': 0},
                             dev_mode=session.get('dev_mode', False))


@main_bp.route('/home_old')
@login_required
def home_old():
    """Ancienne page d'accueil (pour compatibilité)"""
    return render_template('home.html')


@main_bp.route('/dashboard-glass')
@login_required
def dashboard_glass():
    """Page de démonstration du système glassmorphism avancé"""
    return render_template('dashboard_glass.html')


@main_bp.route('/fresh')
@login_required
def fresh():
    """Page d'accueil version fresh"""
    return render_template('home_fresh.html')


@main_bp.route('/test-collapse-pro')
@login_required
def test_collapse_pro():
    """Route de test pour les éléments collapse de Bootstrap Pro"""
    return render_template('test_collapse_pro.html')


@main_bp.route('/sneat-test')
@login_required
def sneat_test():
    """Route de test pour le template Sneat exact"""
    return render_template('home_sneat_exact.html')


@main_bp.route('/sneat-clean')
@login_required
def sneat_clean():
    """Redirection vers la page des tâches"""
    return redirect(url_for('main.tasks_page'))


@main_bp.route('/tasks')
@login_required
def tasks_page():
    """Page des tâches en cours avec organisation par pays - Restored from backup"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        from yt_channel_analyzer.database import get_db_connection
        
        tasks = task_manager.get_all_tasks_with_warnings()
        
        # Éliminer les doublons basés sur l'ID de la tâche
        seen_ids = set()
        unique_tasks = []
        for task in tasks:
            if task.id not in seen_ids:
                seen_ids.add(task.id)
                unique_tasks.append(task)
        
        tasks = unique_tasks
        print(f"[TASKS] {len(tasks)} tâches uniques trouvées")
        
        # Organiser les tâches par pays
        tasks_by_country = {
            'FR': [],
            'DE': [],
            'BE': [],
            'NL': [],
            'International': [],
            'Unknown': []
        }
        
        crashed_tasks = []
        
        # Récupérer les pays et IDs des concurrents pour associer aux tâches
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, channel_url, country FROM concurrent")
        url_data = {}
        for row in cursor.fetchall():
            url_data[row[1]] = {'id': row[0], 'country': row[2]}
        conn.close()
        
        # Importer la fonction pour obtenir les miniatures
        from yt_channel_analyzer.utils.thumbnails import get_competitor_thumbnail
        
        for task in tasks:
            # Déterminer le pays de la tâche et ajouter la miniature locale
            country = 'Unknown'
            if hasattr(task, 'channel_url') and task.channel_url:
                data = url_data.get(task.channel_url, {})
                country = data.get('country', 'Unknown')
                
                # Utiliser la miniature locale stockée sur le serveur
                if data.get('id'):
                    task.channel_thumbnail = get_competitor_thumbnail(data['id'])
            
            # Séparer les tâches en erreur
            if task.status == 'error':
                crashed_tasks.append(task)
            else:
                if country in tasks_by_country:
                    tasks_by_country[country].append(task)
                else:
                    tasks_by_country['Unknown'].append(task)
        
        return render_template('tasks_sneat_pro.html', 
                             tasks=tasks, 
                             tasks_by_country=tasks_by_country,
                             crashed_tasks=crashed_tasks)
    except Exception as e:
        return render_template('tasks_sneat_pro.html', 
                             tasks=[], 
                             tasks_by_country={},
                             crashed_tasks=[],
                             error=str(e))


@main_bp.route('/performance-dashboard')
@login_required
def performance_dashboard():
    """Dashboard de performance du système"""
    try:
        import psutil
    except ImportError:
        psutil = None
    import os
    from datetime import datetime
    
    try:
        if not psutil:
            return render_template('performance_dashboard.html', 
                                 metrics={'memory_percent': 0, 'memory_available': 0, 
                                        'disk_percent': 0, 'disk_free': 0, 
                                        'database_size': 0, 'last_updated': 'psutil non disponible'})
        
        # Métriques système
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Métriques application
        db_size = 0
        try:
            db_path = 'instance/database.db'
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
        except Exception:
            pass
        
        metrics = {
            'memory_percent': memory.percent,
            'memory_available': memory.available // (1024 * 1024),  # MB
            'disk_percent': disk.percent,
            'disk_free': disk.free // (1024 * 1024 * 1024),  # GB
            'database_size': db_size // (1024 * 1024),  # MB
            'last_updated': datetime.now().strftime('%H:%M:%S')
        }
        
        return render_template('performance_dashboard.html', metrics=metrics)
        
    except Exception as e:
        print(f"[ERROR] Error in performance dashboard: {e}")
        return render_template('performance_dashboard.html', 
                             metrics={'memory_percent': 0, 'memory_available': 0, 
                                    'disk_percent': 0, 'disk_free': 0, 
                                    'database_size': 0, 'last_updated': 'N/A'})