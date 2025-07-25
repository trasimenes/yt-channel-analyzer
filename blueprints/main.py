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
        
        conn.close()
        
        stats = {
            'total_competitors': total_competitors,
            'total_videos': total_videos,
            'total_playlists': total_playlists
        }
        
        return render_template('home_sneat_pro.html', 
                             stats=stats,
                             dev_mode=session.get('dev_mode', False))
                             
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in home: {e}")
        return render_template('home_sneat_pro.html', 
                             stats={'total_competitors': 0, 'total_videos': 0, 'total_playlists': 0},
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
    return redirect(url_for('tasks.tasks_page'))


@main_bp.route('/tasks')
@login_required
def tasks_page():
    """Page de gestion des tâches"""
    try:
        from yt_channel_analyzer.background_tasks import task_manager
        
        # Obtenir toutes les tâches
        all_tasks = task_manager.get_all_tasks()
        running_tasks = task_manager.get_running_tasks()
        completed_tasks = task_manager.get_completed_tasks()
        
        # Statistiques
        stats = {
            'total_tasks': len(all_tasks),
            'running_tasks': len(running_tasks),
            'completed_tasks': len(completed_tasks),
            'pending_tasks': len(all_tasks) - len(running_tasks) - len(completed_tasks)
        }
        
        return render_template('tasks_sneat_pro.html',
                             all_tasks=all_tasks,
                             running_tasks=running_tasks,
                             completed_tasks=completed_tasks,
                             stats=stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in tasks page: {e}")
        return render_template('tasks_sneat_pro.html',
                             all_tasks=[],
                             running_tasks=[],
                             completed_tasks=[],
                             stats={'total_tasks': 0, 'running_tasks': 0, 'completed_tasks': 0, 'pending_tasks': 0})


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