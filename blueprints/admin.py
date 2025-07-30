"""
Admin Blueprint
Handles all administrative routes including settings, data management, and system maintenance.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from blueprints.auth import login_required
import os
import json
from datetime import datetime, timedelta


admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres (règles métiers uniquement) - Restored from backup"""
    if request.method == 'POST':
        # Sauvegarder la clé API YouTube si fournie
        youtube_api_key = request.form.get('youtube_api_key', '').strip()
        if youtube_api_key:
            # Sauvegarder dans la base de données
            from yt_channel_analyzer.database import get_db_connection
            from flask import current_app
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Créer la table si elle n'existe pas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insérer ou mettre à jour la clé
            cursor.execute('''
                INSERT OR REPLACE INTO app_config (key, value, updated_at)
                VALUES ('youtube_api_key', ?, datetime('now'))
            ''', (youtube_api_key,))
            
            conn.commit()
            conn.close()
            
            # Mettre à jour la config de l'app
            current_app.config['YOUTUBE_API_KEY'] = youtube_api_key
            os.environ['YOUTUBE_API_KEY'] = youtube_api_key
            
            print(f"[SETTINGS] Clé API YouTube sauvegardée en base de données")
            flash('Clé API YouTube sauvegardée avec succès !', 'success')
        
        # Suite du code existant
        # Sauvegarder les paramètres
        from yt_channel_analyzer.settings import save_settings
        
        settings_data = {
            'paid_threshold': int(request.form.get('paid_threshold', 10000)),
            'industry': request.form.get('industry', 'tourism'),
            'auto_classify': 'auto_classify' in request.form,
            'max_videos': int(request.form.get('max_videos', 1000)),
            'cache_duration': int(request.form.get('cache_duration', 24))
        }
        
        save_settings(settings_data)
        print(f"[SETTINGS] Paramètres sauvegardés: {settings_data}")
        
        return render_template('settings_sneat_pro.html', 
                             current_settings=settings_data,
                             message="Paramètres sauvegardés avec succès !")
    
    from yt_channel_analyzer.settings import load_settings
    current_settings = load_settings()
    
    # Récupérer les patterns de classification multilingues
    from yt_channel_analyzer.database.classification import get_classification_patterns
    patterns = get_classification_patterns()
    
    # Intégrer les patterns depuis enhanced_patterns.py
    try:
        from yt_channel_analyzer.enhanced_patterns import DESCRIPTION_PATTERNS, add_description_patterns_to_db
        
        # Vérifier si les patterns enhanced sont déjà en base
        total_patterns = sum(len(patterns.get(cat, [])) for cat in ['hero', 'hub', 'help'])
        if total_patterns < 50:  # Si moins de 50 patterns, on ajoute les enhanced
            print("[SETTINGS] Ajout des patterns enhanced multilingues...")
            add_description_patterns_to_db()
            patterns = get_classification_patterns()  # Recharger après ajout
        
        # Organiser les patterns par langue
        multilingual_patterns = {
            'fr': {'hero': [], 'hub': [], 'help': []},
            'en': {'hero': [], 'hub': [], 'help': []},
            'de': {'hero': [], 'hub': [], 'help': []},
            'nl': {'hero': [], 'hub': [], 'help': []}
        }
        
        # Ajouter les patterns enhanced directement
        for lang, categories in DESCRIPTION_PATTERNS.items():
            if lang in multilingual_patterns:
                for category, pattern_list in categories.items():
                    multilingual_patterns[lang][category] = pattern_list
        
    except ImportError:
        # Fallback vers les patterns existants
        multilingual_patterns = {
            'fr': {'hero': patterns.get('hero', []), 'hub': patterns.get('hub', []), 'help': patterns.get('help', [])}
        }
    
    # Pour compatibilité avec le template existant
    hero_patterns = patterns.get('hero', [])
    hub_patterns = patterns.get('hub', [])
    help_patterns = patterns.get('help', [])
    
    # Récupérer les statistiques business (paid vs organic)
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer le seuil paid_threshold
        paid_threshold = current_settings.get('paid_threshold', 10000)
        
        # Statistiques organiques (< seuil)
        cursor.execute("""
            SELECT COUNT(*) as count,
                   AVG(CASE WHEN like_count > 0 AND view_count > 0 
                       THEN (like_count + comment_count) * 100.0 / view_count 
                       ELSE 0 END) as engagement
            FROM video 
            WHERE view_count < ? AND view_count > 0
        """, (paid_threshold,))
        organic_result = cursor.fetchone()
        organic_stats = {
            'count': organic_result[0] if organic_result else 0,
            'engagement': organic_result[1] if organic_result and organic_result[1] else 0
        }
        
        # Statistiques payantes (>= seuil)
        cursor.execute("""
            SELECT COUNT(*) as count,
                   AVG(CASE WHEN like_count > 0 AND view_count > 0 
                       THEN (like_count + comment_count) * 100.0 / view_count 
                       ELSE 0 END) as engagement
            FROM video 
            WHERE view_count >= ?
        """, (paid_threshold,))
        paid_result = cursor.fetchone()
        paid_stats = {
            'count': paid_result[0] if paid_result else 0,
            'engagement': paid_result[1] if paid_result and paid_result[1] else 0
        }
        
        # Pas de mots-clés, c'est basé sur le seuil de vues
        paid_keywords = []
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de la récupération des stats business: {e}")
        organic_stats = {'count': 0, 'engagement': 0}
        paid_stats = {'count': 0, 'engagement': 0}
        paid_keywords = []
    
    # Informations cron job (simulation)
    last_cron_run = "2025-01-19 14:30"

    # Récupérer la clé API actuelle (masquée pour la sécurité)
    from flask import current_app
    current_api_key = current_app.config.get('YOUTUBE_API_KEY', '')
    if current_api_key:
        # Masquer la clé en ne montrant que les premiers et derniers caractères
        masked_key = f"{current_api_key[:8]}...{current_api_key[-4:]}" if len(current_api_key) > 12 else "Configurée"
    else:
        masked_key = "Non configurée"
    
    return render_template('settings_sneat_pro.html', 
                         current_settings=current_settings,
                         current_api_key=masked_key,
                         hero_patterns=hero_patterns,
                         hub_patterns=hub_patterns,
                         help_patterns=help_patterns,
                         multilingual_patterns=multilingual_patterns,
                         organic_stats=organic_stats,
                         paid_stats=paid_stats,
                         paid_keywords=paid_keywords,
                         last_cron_run=last_cron_run)


@admin_bp.route('/save-settings', methods=['POST'])
@login_required
def save_settings():
    """Sauvegarder les paramètres de l'application"""
    try:
        from yt_channel_analyzer.settings import save_settings as save_settings_func
        
        # Récupérer les paramètres du formulaire
        settings = {
            'paid_threshold': int(request.form.get('paid_threshold', 10000)),
            'max_videos_per_competitor': int(request.form.get('max_videos_per_competitor', 50)),
            'api_delay': float(request.form.get('api_delay', 1.0)),
            'enable_debug': request.form.get('enable_debug') == 'on',
            'cache_timeout': int(request.form.get('cache_timeout', 300)),
            'max_concurrent_tasks': int(request.form.get('max_concurrent_tasks', 3))
        }
        
        save_settings_func(settings)
        flash("Paramètres sauvegardés avec succès", "success")
        
    except Exception as e:
        print(f"[ERROR] Error saving settings: {e}")
        flash(f"Erreur lors de la sauvegarde: {str(e)}", "error")
    
    return redirect(url_for('admin.settings'))


@admin_bp.route('/fix-problems')
@login_required
def fix_problems():
    """Page de résolution des problèmes automatique"""
    try:
        print("[DEBUG] Starting fix_problems route")
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Debug: Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"[DEBUG] Available tables: {[t[0] for t in tables]}")
        
        # Check if video table exists specifically
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video';")
        video_table_exists = cursor.fetchone()
        print(f"[DEBUG] Video table exists: {video_table_exists is not None}")
        
        if not video_table_exists:
            print("[DEBUG] Video table missing - creating empty problems list")
            problems_found = []
            conn.close()
            return render_template('fix_problems_sneat_pro.html',
                                 problems_found=problems_found,
                                 total_problems=0,
                                 system_health={'database': 'error', 'api': 'unknown'},
                                 db_stats={'total_videos': 0, 'total_competitors': 0, 'total_playlists': 0})
        
        # Analyser les problèmes dans la base de données
        problems_found = []
        
        # 1. Vérifier les vidéos sans concurrent_id
        cursor.execute("SELECT COUNT(*) FROM video WHERE concurrent_id IS NULL")
        orphan_videos = cursor.fetchone()[0]
        if orphan_videos > 0:
            problems_found.append({
                'type': 'orphan_videos',
                'count': orphan_videos,
                'description': f'{orphan_videos} vidéos sans concurrent associé',
                'severity': 'high'
            })
        
        # 2. Vérifier les doublons de vidéos
        cursor.execute("""
            SELECT video_id, COUNT(*) as count 
            FROM video 
            WHERE video_id IS NOT NULL 
            GROUP BY video_id 
            HAVING COUNT(*) > 1
        """)
        duplicate_videos = cursor.fetchall()
        if duplicate_videos:
            problems_found.append({
                'type': 'duplicate_videos',
                'count': len(duplicate_videos),
                'description': f'{len(duplicate_videos)} vidéos en double détectées',
                'severity': 'medium'
            })
        
        # 3. Vérifier les concurrents sans vidéos
        cursor.execute("""
            SELECT c.id, c.name 
            FROM concurrent c 
            LEFT JOIN video v ON c.id = v.concurrent_id 
            WHERE v.id IS NULL
        """)
        empty_competitors = cursor.fetchall()
        if empty_competitors:
            problems_found.append({
                'type': 'empty_competitors',
                'count': len(empty_competitors),
                'description': f'{len(empty_competitors)} concurrents sans vidéos',
                'severity': 'low'
            })
        
        # 4. Vérifier les valeurs nulles critiques
        cursor.execute("SELECT COUNT(*) FROM video WHERE view_count IS NULL OR view_count < 0")
        invalid_views = cursor.fetchone()[0]
        if invalid_views > 0:
            problems_found.append({
                'type': 'invalid_views',
                'count': invalid_views,
                'description': f'{invalid_views} vidéos avec vues invalides',
                'severity': 'medium'
            })
        
        # Get database statistics
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        total_competitors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM playlist")
        total_playlists = cursor.fetchone()[0]
        
        conn.close()
        
        # Calculate system health
        system_health = {
            'database': 'healthy' if len(problems_found) == 0 else 'warning',
            'api': 'healthy'  # Assuming API is healthy if we get here
        }
        
        # Database statistics
        db_stats = {
            'total_videos': total_videos,
            'total_competitors': total_competitors,
            'total_playlists': total_playlists
        }
        
        return render_template('fix_problems_sneat_pro.html',
                             problems_found=problems_found,
                             total_problems=len(problems_found),
                             system_health=system_health,
                             db_stats=db_stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in fix_problems: {e}")
        flash("Erreur lors de l'analyse des problèmes", "error")
        return render_template('fix_problems_sneat_pro.html',
                             problems_found=[],
                             total_problems=0,
                             system_health={'database': 'error', 'api': 'error'},
                             db_stats={'total_videos': 0, 'total_competitors': 0, 'total_playlists': 0})


@admin_bp.route('/fix-problem/<problem_type>', methods=['POST'])
@login_required  
def fix_problem(problem_type):
    """Corriger un problème spécifique"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        fixed_count = 0
        
        if problem_type == 'orphan_videos':
            # Supprimer les vidéos orphelines
            cursor.execute("DELETE FROM video WHERE concurrent_id IS NULL")
            fixed_count = cursor.rowcount
            
        elif problem_type == 'duplicate_videos':
            # Supprimer les doublons en gardant le plus récent
            cursor.execute("""
                DELETE FROM video 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM video 
                    WHERE video_id IS NOT NULL 
                    GROUP BY video_id
                )
                AND video_id IS NOT NULL
            """)
            fixed_count = cursor.rowcount
            
        elif problem_type == 'empty_competitors':
            # Supprimer les concurrents sans vidéos
            cursor.execute("""
                DELETE FROM concurrent 
                WHERE id NOT IN (
                    SELECT DISTINCT concurrent_id 
                    FROM video 
                    WHERE concurrent_id IS NOT NULL
                )
            """)
            fixed_count = cursor.rowcount
            
        elif problem_type == 'invalid_views':
            # Mettre à 0 les vues invalides
            cursor.execute("UPDATE video SET view_count = 0 WHERE view_count IS NULL OR view_count < 0")
            fixed_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Problème corrigé: {fixed_count} éléments traités',
            'fixed_count': fixed_count
        })
        
    except Exception as e:
        print(f"[ERROR] Error fixing problem {problem_type}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/admin-api-usage')
@login_required
def api_usage():
    """Page de surveillance de l'utilisation de l'API"""
    try:
        import sys
        print("=" * 80)
        print("[ULTRA DEBUG] Starting api_usage route")
        sys.stdout.flush()
        
        # Lire le fichier de tracking des quotas API
        quota_file = 'api_quota_tracking.json'
        print(f"[ULTRA DEBUG] Looking for quota file: {quota_file}")
        print(f"[ULTRA DEBUG] Current working directory: {os.getcwd()}")
        print(f"[ULTRA DEBUG] Full path would be: {os.path.abspath(quota_file)}")
        print(f"[ULTRA DEBUG] File exists: {os.path.exists(quota_file)}")
        
        quota_data = {}
        
        if os.path.exists(quota_file):
            print(f"[ULTRA DEBUG] File exists, attempting to read...")
            try:
                with open(quota_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    print(f"[ULTRA DEBUG] Raw file content: {file_content}")
                    quota_data = json.loads(file_content)
                    print(f"[ULTRA DEBUG] Parsed JSON data: {quota_data}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ULTRA DEBUG] Error reading file: {e}")
                quota_data = {}
        else:
            print(f"[ULTRA DEBUG] File does not exist!")
            # List files in current directory
            print(f"[ULTRA DEBUG] Files in current directory:")
            for f in os.listdir('.'):
                if f.endswith('.json'):
                    print(f"  - {f}")
        
        print(f"[ULTRA DEBUG] Final quota_data: {quota_data}")
        
        # Calculer les statistiques selon la structure réelle du fichier
        total_requests = quota_data.get('total_requests', 0)
        daily_requests = quota_data.get('daily_requests', {})
        
        print(f"[ULTRA DEBUG] total_requests from file: {total_requests}")
        print(f"[ULTRA DEBUG] daily_requests from file: {daily_requests}")
        
        # Si on a l'ancien format, l'utiliser
        if 'quota_used' in quota_data:
            print("[ULTRA DEBUG] Using old format with quota_used")
            current_usage = quota_data.get('quota_used', 0)
            total_requests = quota_data.get('requests_made', 0)
            print(f"[ULTRA DEBUG] Old format - current_usage: {current_usage}, total_requests: {total_requests}")
        else:
            print("[ULTRA DEBUG] Using new format with daily_requests")
            current_date = datetime.now().strftime('%Y-%m-%d')
            print(f"[ULTRA DEBUG] Looking for date: {current_date}")
            current_usage = daily_requests.get(current_date, 0)
            print(f"[ULTRA DEBUG] New format - current_usage: {current_usage}")
        
        # Dernières 7 jours
        recent_usage = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if daily_requests:
                usage = daily_requests.get(date, 0)
            else:
                # Pour l'ancien format, on ne montre que les données d'aujourd'hui
                usage = current_usage if date == datetime.now().strftime('%Y-%m-%d') else 0
            recent_usage.append({
                'date': date,
                'requests': usage
            })
        
        recent_usage.reverse()
        
        # Limites API (YouTube Data API v3)
        daily_limit = 10000  # Limite quotidienne par défaut
        usage_percentage = (current_usage / daily_limit) * 100
        
        print(f"[ULTRA DEBUG] Calculations:")
        print(f"  daily_limit: {daily_limit}")
        print(f"  current_usage: {current_usage}")
        print(f"  usage_percentage: {usage_percentage}")
        print(f"  remaining_quota: {max(daily_limit - current_usage, 0)}")
        
        api_stats = {
            'total_requests': total_requests,
            'current_daily_usage': current_usage,
            'daily_limit': daily_limit,
            'usage_percentage': min(usage_percentage, 100),
            'remaining_quota': max(daily_limit - current_usage, 0),
            'recent_usage': recent_usage,
            'status': 'healthy' if usage_percentage < 80 else 'warning' if usage_percentage < 95 else 'critical'
        }
        
        print(f"[ULTRA DEBUG] Final api_stats being sent to template:")
        for key, value in api_stats.items():
            print(f"  {key}: {value}")
        
        print("=" * 80)
        
        return render_template('api_usage_sneat_pro.html',
                             api_stats=api_stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in api_usage: {e}")
        return render_template('api_usage_sneat_pro.html',
                             api_stats={
                                 'total_requests': 0,
                                 'current_daily_usage': 0,
                                 'daily_limit': 10000,
                                 'usage_percentage': 0,
                                 'remaining_quota': 10000,
                                 'recent_usage': [],
                                 'status': 'unknown'
                             })


@admin_bp.route('/data-export')
@login_required
def data_export():
    """Page d'export des données"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Statistiques des données à exporter
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        competitors_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video")
        videos_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM playlist")
        playlists_count = cursor.fetchone()[0]
        
        # Taille estimée de l'export
        export_stats = {
            'competitors_count': competitors_count,
            'videos_count': videos_count,
            'playlists_count': playlists_count,
            'estimated_size_mb': (videos_count * 2 + competitors_count * 1) / 1000  # Estimation approximative
        }
        
        conn.close()
        
        return render_template('data_export_sneat_pro.html',
                             export_stats=export_stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in data_export: {e}")
        return render_template('data_export_sneat_pro.html',
                             export_stats={
                                 'competitors_count': 0,
                                 'videos_count': 0,
                                 'playlists_count': 0,
                                 'estimated_size_mb': 0
                             })


@admin_bp.route('/export-data/<data_type>')
@login_required
def export_data(data_type):
    """Exporter des données en JSON"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        from flask import Response
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if data_type == 'competitors':
            cursor.execute("""
                SELECT id, name, channel_url, country, subscribers, 
                       created_at, last_updated
                FROM concurrent
                ORDER BY name
            """)
            columns = ['id', 'name', 'channel_url', 'country', 'subscribers', 'created_at', 'last_updated']
            
        elif data_type == 'videos':
            cursor.execute("""
                SELECT v.id, v.title, v.view_count, v.like_count, v.comment_count,
                       v.published_at, v.duration_seconds, v.category, c.name as competitor_name
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                ORDER BY v.view_count DESC
                LIMIT 1000
            """)
            columns = ['id', 'title', 'view_count', 'like_count', 'comment_count', 
                      'published_at', 'duration_seconds', 'category', 'competitor_name']
            
        elif data_type == 'playlists':
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.category, p.video_count,
                       c.name as competitor_name
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                ORDER BY p.video_count DESC
            """)
            columns = ['id', 'name', 'description', 'category', 'video_count', 'competitor_name']
            
        else:
            return jsonify({'error': 'Type de données non supporté'}), 400
        
        # Convertir en dictionnaires
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        
        conn.close()
        
        # Préparer l'export JSON
        export_data = {
            'export_type': data_type,
            'export_date': datetime.now().isoformat(),
            'total_records': len(data),
            'data': data
        }
        
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        response = Response(
            json_data,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={data_type}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"[ERROR] Error exporting {data_type}: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/database-maintenance')
@login_required
def database_maintenance():
    """Page de maintenance de la base de données"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        import os
        
        # Informations sur la base de données
        db_path = 'instance/database.db'
        db_info = {
            'exists': os.path.exists(db_path),
            'size_mb': 0,
            'last_modified': None
        }
        
        if os.path.exists(db_path):
            stat = os.stat(db_path)
            db_info['size_mb'] = stat.st_size / (1024 * 1024)
            db_info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # Statistiques des tables
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tables_stats = []
        for table_name in ['concurrent', 'video', 'playlist', 'playlist_video']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                tables_stats.append({
                    'name': table_name,
                    'count': count
                })
            except Exception as e:
                tables_stats.append({
                    'name': table_name,
                    'count': 0,
                    'error': str(e)
                })
        
        conn.close()
        
        return render_template('database_maintenance_sneat_pro.html',
                             db_info=db_info,
                             tables_stats=tables_stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in database_maintenance: {e}")
        return render_template('database_maintenance_sneat_pro.html',
                             db_info={'exists': False, 'size_mb': 0, 'last_modified': None},
                             tables_stats=[])


@admin_bp.route('/database-action/<action>', methods=['POST'])
@login_required
def database_action(action):
    """Exécuter une action de maintenance sur la base de données"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if action == 'vacuum':
            cursor.execute('VACUUM')
            message = 'Base de données optimisée (VACUUM)'
            
        elif action == 'reindex':
            cursor.execute('REINDEX')
            message = 'Index reconstruits'
            
        elif action == 'analyze':
            cursor.execute('ANALYZE')
            message = 'Statistiques mises à jour (ANALYZE)'
            
        elif action == 'integrity_check':
            cursor.execute('PRAGMA integrity_check')
            result = cursor.fetchone()[0]
            message = f'Vérification d\'intégrité: {result}'
            
        else:
            return jsonify({'error': 'Action non supportée'}), 400
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        print(f"[ERROR] Error in database action {action}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/system-info')
@login_required
def system_info():
    """Page d'informations système"""
    try:
        import platform
        import sys
        try:
            import psutil
        except ImportError:
            psutil = None
        
        # Informations système
        system_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node(),
        }
        
        if psutil:
            system_info.update({
                'memory_total': psutil.virtual_memory().total // (1024 * 1024 * 1024),  # GB
                'disk_total': psutil.disk_usage('/').total // (1024 * 1024 * 1024),  # GB
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            system_info.update({
                'memory_total': 'N/A (psutil non disponible)',
                'disk_total': 'N/A (psutil non disponible)', 
                'boot_time': 'N/A (psutil non disponible)'
            })
        
        # Informations Flask
        from flask import current_app
        flask_info = {
            'debug_mode': current_app.debug,
            'secret_key_set': bool(current_app.secret_key),
            'config_keys': list(current_app.config.keys())
        }
        
        return render_template('system_info_sneat_pro.html',
                             system_info=system_info,
                             flask_info=flask_info)
                             
    except Exception as e:
        print(f"[ERROR] Error in system_info: {e}")
        return render_template('system_info_sneat_pro.html',
                             system_info={},
                             flask_info={})


@admin_bp.route('/reset-api-quota', methods=['POST'])
@login_required
def reset_api_quota():
    """Réinitialiser le compteur de quota API"""
    try:
        quota_file = 'api_quota_tracking.json'
        
        # Créer un nouveau fichier de quota vide
        new_quota_data = {
            'total_requests': 0,
            'daily_requests': {},
            'last_reset': datetime.now().isoformat(),
            'reset_by': session.get('username', 'admin')
        }
        
        with open(quota_file, 'w', encoding='utf-8') as f:
            json.dump(new_quota_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': 'Compteur de quota API réinitialisé'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500