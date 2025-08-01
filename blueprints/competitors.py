"""
Competitors Blueprint
Handles all competitor-related routes and functionality.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from blueprints.auth import login_required
from services.competitor_service import CompetitorDetailService


competitors_bp = Blueprint('competitors', __name__)


@competitors_bp.route('/test-auth')
@login_required
def test_auth():
    """Test route to debug authentication"""
    return f"Auth test successful! Session: {dict(session)}"


@competitors_bp.route('/concurrents')
@login_required
def concurrents():
    """Competitors list page"""
    from yt_channel_analyzer.database import get_db_connection
    import sqlite3
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all competitors with their statistics including category counters and playlists
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.channel_url,
                c.country,
                c.subscriber_count,
                COUNT(DISTINCT v.id) as video_count,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(AVG(v.view_count), 0) as avg_views,
                COALESCE(SUM(CASE WHEN LOWER(v.category) = 'hero' THEN 1 ELSE 0 END), 0) as hero_count,
                COALESCE(SUM(CASE WHEN LOWER(v.category) = 'hub' THEN 1 ELSE 0 END), 0) as hub_count,
                COALESCE(SUM(CASE WHEN LOWER(v.category) = 'help' THEN 1 ELSE 0 END), 0) as help_count,
                (SELECT COUNT(*) FROM playlist WHERE concurrent_id = c.id) as playlist_count
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id, c.name, c.channel_url, c.country, c.subscriber_count
            ORDER BY c.name
        """)
        
        competitors = []
        for row in cursor.fetchall():
            competitor_id = row[0]
            competitors.append({
                'id': competitor_id,
                'name': row[1],
                'channel_url': row[2],
                'country': row[3],
                'subscribers': row[4] or 0,
                'video_count': row[5],
                'total_views': row[6],
                'avg_views': int(row[7]) if row[7] else 0,
                'hero_count': row[8],
                'hub_count': row[9],
                'help_count': row[10],
                'playlist_count': row[11] or 0,
                'thumbnail_url': f'/static/competitors/images/{competitor_id}.jpg'
            })
        
        conn.close()
        
        print(f"[DEBUG COMPETITORS] Number of competitors found: {len(competitors)}")
        if competitors:
            print(f"[DEBUG COMPETITORS] First competitor: {competitors[0]['name']} with {competitors[0]['video_count']} videos")
        
        # Calculate total videos
        total_videos = sum(comp['video_count'] for comp in competitors)
        
        # Group competitors by country for the tabs template
        competitors_by_country = {
            'international': [],
            'france': [],
            'germany': [],
            'netherlands': [], 
            'uk': []
        }
        
        for comp in competitors:
            country = comp.get('country', '').lower()
            if country == 'france':
                competitors_by_country['france'].append(comp)
            elif country == 'germany':
                competitors_by_country['germany'].append(comp) 
            elif country == 'netherlands':
                competitors_by_country['netherlands'].append(comp)
            elif country in ['united kingdom', 'uk']:
                competitors_by_country['uk'].append(comp)
            else:
                competitors_by_country['international'].append(comp)
        
        return render_template('concurrents_sneat_pro_tabs.html', 
                             competitors=competitors,
                             international_competitors=competitors_by_country['international'],
                             france_competitors=competitors_by_country['france'],
                             germany_competitors=competitors_by_country['germany'],
                             netherlands_competitors=competitors_by_country['netherlands'],
                             uk_competitors=competitors_by_country['uk'],
                             total_competitors=len(competitors),
                             total_videos=total_videos,
                             dev_mode=session.get('dev_mode', False))
                             
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in concurrents: {e}")
        flash("Error loading competitors", "error")
        return render_template('concurrents_sneat_pro_tabs.html', 
                             competitors=[],
                             total_competitors=0,
                             total_videos=0)


@competitors_bp.route('/competitor/<int:competitor_id>')  
@login_required
def competitor_detail(competitor_id):
    """
    Competitor detail page - refactored using service layer architecture.
    Complexity reduced from 75 to ~8 by extracting business logic.
    """
    try:
        from yt_channel_analyzer.database import get_db_connection
        from yt_channel_analyzer.settings import load_settings
        
        conn = get_db_connection()
        settings = load_settings()
        paid_threshold = settings.get('paid_threshold', 10000)
        
        # Use service layer for business logic
        service = CompetitorDetailService(conn, paid_threshold)
        data = service.get_competitor_detail_data(competitor_id)
        
        if data is None:
            flash("Competitor not found.", "error")
            return redirect(url_for('competitors.concurrents'))
        
        # Ajouter l'analyse d'engagement
        from yt_channel_analyzer.engagement_analyzer import EngagementAnalyzer
        engagement_analyzer = EngagementAnalyzer()
        
        # Top 5 vidéos les plus engageantes avec leurs thèmes
        top_engaging_videos = engagement_analyzer.get_top_engaging_videos(competitor_id)
        
        # Aperçu général de l'engagement
        engagement_overview = engagement_analyzer.get_competitor_engagement_overview(competitor_id)
        
        # Render new tabbed template with clean data structure
        return render_template('competitor_detail_tabs.html',
                               competitor=data['competitor'],
                               videos=data['videos'],
                               stats=data['stats'],
                               metrics=data['metrics'],  # Advanced metrics for Key Metrics tab
                               top_videos_views=data['top_videos_views'],
                               top_videos_likes=data['top_videos_likes'],
                               top_videos_json=data['top_videos_json'],
                               performance_data=data['performance_data'],
                               category_distribution=data['category_distribution'],
                               content_type_distribution=data['content_type_distribution'],
                               engagement_metrics=data['engagement_metrics'],
                               playlists=data['playlists'],
                               subscriber_data=data['subscriber_data'],
                               hero_count=data['stats']['hero_count'],
                               hub_count=data['stats']['hub_count'],
                               help_count=data['stats']['help_count'],
                               shorts_data=data['shorts_data'],
                               videos_by_category=data['videos_by_category'],
                               total_videos=len(data['videos']),
                               top_engaging_videos=top_engaging_videos,
                               engagement_overview=engagement_overview,
                               dev_mode=session.get('dev_mode', False))
    
    except Exception as e:
        flash(f"Error loading competitor data: {str(e)}", "error")
        return redirect(url_for('competitors.concurrents'))


@competitors_bp.route('/competitor/<int:competitor_id>/classify')
@login_required
def classify_competitor(competitor_id):
    """Interface de classification manuelle des playlists pour un concurrent"""
    print(f"🔍 [CLASSIFY-DEBUG] Route called with competitor_id: {competitor_id}")
    print(f"🔍 [CLASSIFY-DEBUG] Session authenticated: {session.get('authenticated', False)}")
    print(f"🔍 [CLASSIFY-DEBUG] Session username: {session.get('username', 'None')}")
    print(f"🔍 [CLASSIFY-DEBUG] Dev mode: {session.get('dev_mode', False)}")
    
    try:
        from yt_channel_analyzer.database import get_db_connection
        print(f"🔍 [CLASSIFY-DEBUG] Database import successful")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"🔍 [CLASSIFY-DEBUG] Database connection established")
        
        # Récupérer les infos du concurrent
        print(f"🔍 [CLASSIFY-DEBUG] Querying competitor with ID: {competitor_id}")
        cursor.execute('SELECT name, channel_url FROM concurrent WHERE id = ?', (competitor_id,))
        competitor = cursor.fetchone()
        print(f"🔍 [CLASSIFY-DEBUG] Competitor query result: {competitor}")
        
        if not competitor:
            print(f"❌ [CLASSIFY-DEBUG] Competitor {competitor_id} not found!")
            flash("Competitor not found.", "error")
            return redirect(url_for('competitors.concurrents'))
        
        # Récupérer toutes les playlists du concurrent
        print(f"🔍 [CLASSIFY-DEBUG] Querying playlists for competitor {competitor_id}")
        cursor.execute('''
            SELECT id, name, description, video_count, category, 
                   classification_source, human_verified, thumbnail_url
            FROM playlist 
            WHERE concurrent_id = ? AND name NOT LIKE '%All Videos%'
            ORDER BY video_count DESC
        ''', (competitor_id,))
        
        playlist_rows = cursor.fetchall()
        print(f"🔍 [CLASSIFY-DEBUG] Found {len(playlist_rows)} playlists")
        
        playlists = []
        for i, row in enumerate(playlist_rows):
            playlist_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'video_count': row[3] or 0,
                'category': row[4],
                'classification_source': row[5],
                'human_verified': row[6],
                'thumbnail_url': row[7] or '/static/competitors/images/default.jpg'
            }
            playlists.append(playlist_data)
            if i < 3:  # Log first 3 playlists for debugging
                print(f"🔍 [CLASSIFY-DEBUG] Playlist {i+1}: {playlist_data['name']} (category: {playlist_data['category']})")
        
        # Statistiques de classification
        cursor.execute('''
            SELECT category, COUNT(*) 
            FROM playlist 
            WHERE concurrent_id = ? AND category IS NOT NULL 
            GROUP BY category
        ''', (competitor_id,))
        
        category_stats = dict(cursor.fetchall())
        
        # Statistiques des vidéos propagées
        cursor.execute('''
            SELECT COUNT(*) 
            FROM video 
            WHERE concurrent_id = ? AND category IS NOT NULL
        ''', (competitor_id,))
        
        classified_videos = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM video WHERE concurrent_id = ?', (competitor_id,))
        total_videos = cursor.fetchone()[0] or 0
        
        conn.close()
        
        competitor_info = {
            'id': competitor_id,
            'name': competitor[0],
            'channel_url': competitor[1]
        }
        
        stats = {
            'total_playlists': len(playlists),
            'classified_playlists': len([p for p in playlists if p['category']]),
            'hero_count': category_stats.get('hero', 0),
            'hub_count': category_stats.get('hub', 0),
            'help_count': category_stats.get('help', 0),
            'classified_videos': classified_videos,
            'total_videos': total_videos,
            'progress_percentage': round((classified_videos / total_videos * 100) if total_videos > 0 else 0, 1)
        }
        
        print(f"🔍 [CLASSIFY-DEBUG] Competitor info: {competitor_info}")
        print(f"🔍 [CLASSIFY-DEBUG] Stats: {stats}")
        print(f"🔍 [CLASSIFY-DEBUG] Attempting to render template: supervised_learning_sneat_pro.html")
        
        try:
            return render_template('supervised_learning_sneat_pro.html',
                                 competitor=competitor_info,
                                 playlists=playlists,
                                 stats=stats,
                                 page_title=f"Classification {competitor[0]}")
        except Exception as template_error:
            print(f"❌ [CLASSIFY-DEBUG] Template error: {template_error}")
            raise template_error
        
    except Exception as e:
        print(f"❌ [CLASSIFY-DEBUG] Exception in classify_competitor: {str(e)}")
        print(f"❌ [CLASSIFY-DEBUG] Exception type: {type(e)}")
        import traceback
        print(f"❌ [CLASSIFY-DEBUG] Traceback: {traceback.format_exc()}")
        flash(f"Erreur lors du chargement de l'interface de classification: {str(e)}", "error")
        return redirect(url_for('competitors.concurrents'))


@competitors_bp.route('/competitor/<int:competitor_id>/delete')
@login_required
def delete_competitor(competitor_id):
    """Supprimer un concurrent et toutes ses données associées."""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        # Vérifier que le concurrent existe
        competitor = conn.execute('SELECT name FROM concurrent WHERE id = ?', (competitor_id,)).fetchone()
        if competitor is None:
            flash("Competitor not found.", "error")
            return redirect(url_for('competitors.concurrents'))
        
        competitor_name = competitor['name']
        
        # Supprimer en cascade (vidéos, playlists, etc.)
        cursor = conn.cursor()
        
        # Supprimer les vidéos
        cursor.execute('DELETE FROM video WHERE concurrent_id = ?', (competitor_id,))
        deleted_videos = cursor.rowcount
        
        # Supprimer les playlists
        cursor.execute('DELETE FROM playlist WHERE concurrent_id = ?', (competitor_id,))
        deleted_playlists = cursor.rowcount
        
        # Supprimer les données d'abonnés
        cursor.execute('DELETE FROM subscriber_data WHERE concurrent_id = ?', (competitor_id,))
        
        # Supprimer le concurrent lui-même
        cursor.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
        
        conn.commit()
        conn.close()
        
        flash(f"Concurrent '{competitor_name}' supprimé avec succès ({deleted_videos} vidéos, {deleted_playlists} playlists).", "success")
        
    except Exception as e:
        flash(f"Erreur lors de la suppression: {str(e)}", "error")
    
    return redirect(url_for('competitors.concurrents'))


@competitors_bp.route('/top-videos')
@login_required
def top_videos():
    """Page des meilleures vidéos avec filtres avancés"""
    from yt_channel_analyzer.database import get_db_connection
    
    try:
        # Paramètres de requête
        sort_by = request.args.get('sort_by', 'view_count')
        order = request.args.get('order', 'desc')
        category_filter = request.args.get('category', 'all')
        limit = int(request.args.get('limit', 50))
        organic_filter = request.args.get('organic', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construire la requête avec filtres
        where_conditions = []
        params = []
        
        if category_filter != 'all':
            where_conditions.append("v.category = ?")
            params.append(category_filter)
        
        if organic_filter != 'all':
            threshold = 10000  # Seuil par défaut
            if organic_filter == 'organic':
                where_conditions.append("v.view_count < ?")
            else:  # paid
                where_conditions.append("v.view_count >= ?")
            params.append(threshold)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Colonnes valides pour le tri
        valid_sort_columns = {
            'view_count': 'v.view_count',
            'like_count': 'v.like_count', 
            'comment_count': 'v.comment_count',
            'published_at': 'v.published_at',
            'duration_seconds': 'v.duration_seconds'
        }
        
        sort_column = valid_sort_columns.get(sort_by, 'v.view_count')
        order_clause = 'DESC' if order == 'desc' else 'ASC'
        
        query = f"""
            SELECT 
                v.id,
                v.title,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.published_at,
                v.duration_seconds,
                v.category,
                v.thumbnail_url,
                v.video_id,
                c.name as competitor_name,
                c.country
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            {where_clause}
            ORDER BY {sort_column} {order_clause}
            LIMIT ?
        """
        
        params.append(limit)
        cursor.execute(query, params)
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'id': row[0],
                'title': row[1],
                'view_count': row[2] or 0,
                'like_count': row[3] or 0,
                'comment_count': row[4] or 0,
                'published_at': row[5],
                'duration_seconds': row[6] or 0,
                'category': row[7] or 'uncategorized',
                'thumbnail_url': row[8],
                'video_id': row[9],
                'competitor_name': row[10],
                'country': row[11]
            })
        
        # Calculer les vraies statistiques globales (pas seulement les 50 affichées)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COUNT(DISTINCT v.concurrent_id) as total_competitors,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(SUM(v.like_count), 0) as total_likes,
                COALESCE(SUM(v.comment_count), 0) as total_comments,
                COUNT(CASE WHEN v.view_count < 10000 THEN 1 END) as organic_videos,
                COUNT(CASE WHEN v.view_count >= 10000 THEN 1 END) as paid_videos
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
        """)
        
        global_stats = cursor.fetchone()
        
        conn.close()
        
        # Statistiques globales pour l'affichage
        stats = {
            'total_videos': global_stats[0] or 0,
            'total_competitors': global_stats[1] or 0,
            'total_views': global_stats[2] or 0,
            'total_likes': global_stats[3] or 0,
            'total_comments': global_stats[4] or 0,
            'total_organic_videos': global_stats[5] or 0,  # Fixed key name to match template
            'total_paid_videos': global_stats[6] or 0      # Fixed key name to match template
        }
        
        return render_template('top_videos_sneat_pro.html',
                             videos=videos,
                             sort_by=sort_by,
                             order=order,
                             category_filter=category_filter,
                             limit=limit,
                             current_limit=limit,
                             organic_filter=organic_filter,
                             total_videos=stats['total_videos'],  # Vraies stats globales
                             stats=stats)
                             
    except Exception as e:
        print(f"[ERROR] Error in top_videos: {e}")
        flash("Erreur lors du chargement des vidéos", "error")
        return render_template('top_videos_sneat_pro.html',
                             videos=[],
                             sort_by='view_count',
                             order='desc',
                             category_filter='all',
                             limit=50,
                             current_limit=50,  # Template expects current_limit
                             organic_filter='all',
                             total_videos=0,
                             stats={'total_videos': 0, 'total_competitors': 0, 'total_views': 0, 'total_likes': 0, 'total_comments': 0, 'total_organic_videos': 0, 'total_paid_videos': 0})


@competitors_bp.route('/top-playlists')
@login_required
def top_playlists():
    """Page des meilleures playlists avec filtres et tri"""
    from yt_channel_analyzer.database import get_db_connection
    from datetime import datetime
    
    try:
        # Paramètres de requête
        sort_by = request.args.get('sort_by', 'total_views')
        order = request.args.get('order', 'desc')
        category_filter = request.args.get('category', 'all')
        limit = int(request.args.get('limit', 50))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construire la requête avec filtres
        where_conditions = []
        params = []
        
        if category_filter != 'all':
            where_conditions.append("LOWER(p.category) = LOWER(?)")
            params.append(category_filter)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Colonnes valides pour le tri
        valid_sort_columns = {
            'total_views': 'COALESCE(SUM(v.view_count), 0)',
            'total_likes': 'COALESCE(SUM(v.like_count), 0)', 
            'total_comments': 'COALESCE(SUM(v.comment_count), 0)',
            'engagement_ratio': '(COALESCE(SUM(v.like_count), 0) + COALESCE(SUM(v.comment_count), 0)) / NULLIF(COALESCE(SUM(v.view_count), 0), 0)',
            'video_count': 'p.video_count',
            'linked_videos': 'COUNT(DISTINCT pv.video_id)',
            'latest_video_date': 'MAX(COALESCE(v.youtube_published_at, v.published_at))'
        }
        
        sort_column = valid_sort_columns.get(sort_by, valid_sort_columns['total_views'])
        order_clause = 'DESC' if order == 'desc' else 'ASC'
        
        # Récupérer les playlists avec leurs statistiques agrégées
        query = f"""
            SELECT 
                p.id,
                p.playlist_id,
                p.name,
                p.description,
                p.thumbnail_url,
                p.category,
                p.video_count,
                c.name as competitor_name,
                c.country,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(SUM(v.like_count), 0) as total_likes,
                COALESCE(SUM(v.comment_count), 0) as total_comments,
                COALESCE(AVG(v.view_count), 0) as avg_views,
                MAX(COALESCE(v.youtube_published_at, v.published_at)) as latest_video_date,
                COALESCE(AVG(v.duration_seconds), 0) as avg_duration_seconds,
                COUNT(DISTINCT pv.video_id) as linked_videos
            FROM playlist p
            JOIN concurrent c ON p.concurrent_id = c.id
            LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
            LEFT JOIN video v ON pv.video_id = v.id
            {where_clause}
            GROUP BY p.id, p.playlist_id, p.name, p.description, p.thumbnail_url, p.category, p.video_count, c.name, c.country
            ORDER BY {sort_column} {order_clause}
            LIMIT ?
        """
        
        params.append(limit)
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        playlists = []
        for row in results:
            engagement_rate = 0.0
            try:
                if row[9] and row[9] > 0:  # total_views
                    total_likes = row[10] or 0  # total_likes
                    total_comments = row[11] or 0  # total_comments
                    engagement_rate = ((total_likes + total_comments) / row[9]) * 100
            except (TypeError, ZeroDivisionError):
                engagement_rate = 0.0
            
            # Format duration and date
            avg_duration_formatted = "N/A"
            try:
                if row[14] and row[14] > 0:  # avg_duration_seconds
                    hours = int(row[14] // 3600)
                    minutes = int((row[14] % 3600) // 60)
                    seconds = int(row[14] % 60)
                    if hours > 0:
                        avg_duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        avg_duration_formatted = f"{minutes}:{seconds:02d}"
            except (TypeError, ValueError):
                avg_duration_formatted = "N/A"
            
            latest_video_formatted = "N/A"
            try:
                if row[13]:  # latest_video_date
                    date_obj = datetime.fromisoformat(row[13].replace('Z', '+00:00'))
                    latest_video_formatted = date_obj.strftime("%d/%m/%Y")
            except (TypeError, ValueError):
                latest_video_formatted = str(row[13])[:10] if row[13] else "N/A"
            
            playlists.append({
                'id': row[0] or 0,
                'playlist_id': str(row[1]) if row[1] else 'unknown',
                'name': str(row[2]) if row[2] else 'Unknown',
                'description': str(row[3]) if row[3] else '',
                'thumbnail_url': str(row[4]) if row[4] else '',
                'category': str(row[5]) if row[5] else 'uncategorized',
                'video_count': int(row[6]) if row[6] else 0,
                'competitor_name': str(row[7]) if row[7] else 'Unknown',
                'country': str(row[8]) if row[8] else 'Unknown',
                'total_views': int(row[9]) if row[9] else 0,
                'total_likes': int(row[10]) if row[10] else 0,
                'total_comments': int(row[11]) if row[11] else 0,
                'avg_views': int(row[12]) if row[12] else 0,
                'latest_video_date': str(row[13]) if row[13] else 'N/A',
                'latest_video_formatted': str(latest_video_formatted),
                'avg_duration_seconds': float(row[14]) if row[14] else 0.0,
                'avg_duration_formatted': str(avg_duration_formatted),
                'linked_videos': int(row[15]) if row[15] else 0,
                'engagement_rate': float(engagement_rate) if engagement_rate is not None else 0.0,
                'engagement_ratio': float(engagement_rate) if engagement_rate is not None else 0.0,
                'avg_beauty_score': 0.0,
                'avg_emotion_score': 0.0,
                'avg_info_quality_score': 0.0
            })
        
        # Calculer les statistiques globales pour le template
        stats_query = """
            SELECT 
                COUNT(*) as total_playlists,
                COUNT(DISTINCT p.concurrent_id) as total_competitors,
                COUNT(CASE WHEN LOWER(p.category) = 'hero' THEN 1 END) as hero_playlists,
                COUNT(CASE WHEN LOWER(p.category) = 'hub' THEN 1 END) as hub_playlists,
                COUNT(CASE WHEN LOWER(p.category) = 'help' THEN 1 END) as help_playlists,
                COALESCE(SUM(CASE WHEN pv.video_id IS NOT NULL THEN v.view_count ELSE 0 END), 0) as total_views,
                COALESCE(SUM(CASE WHEN pv.video_id IS NOT NULL THEN v.like_count ELSE 0 END), 0) as total_likes,
                COALESCE(SUM(CASE WHEN pv.video_id IS NOT NULL THEN v.comment_count ELSE 0 END), 0) as total_comments
            FROM playlist p
            LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
            LEFT JOIN video v ON pv.video_id = v.id
        """
        
        cursor.execute(stats_query)
        global_stats = cursor.fetchone()
        conn.close()
        
        stats = {
            'total_playlists': global_stats[0] or 0,
            'total_competitors': global_stats[1] or 0,
            'hero_playlists': global_stats[2] or 0,
            'hub_playlists': global_stats[3] or 0,
            'help_playlists': global_stats[4] or 0,
            'shown_playlists': len(playlists),
            'total_views': global_stats[5] or 0,
            'total_likes': global_stats[6] or 0,
            'total_comments': global_stats[7] or 0
        }
        
        return render_template('top_playlists_sneat_pro.html',
                             playlists=playlists,
                             total_playlists=len(playlists),
                             current_sort=sort_by,
                             current_order=order,
                             current_category=category_filter,
                             current_limit=limit,
                             category_filter=category_filter,
                             limit=limit,
                             stats=stats)
                             
    except Exception as e:
        flash("Erreur lors du chargement des playlists", "error")
        return render_template('top_playlists_sneat_pro.html',
                             playlists=[],
                             total_playlists=0,
                             current_sort='total_views',
                             current_order='desc',
                             current_category='all',
                             current_limit=50,
                             category_filter='all',
                             limit=50,
                             stats={
                                'total_playlists': 0, 
                                'total_competitors': 0, 
                                'hero_playlists': 0, 
                                'hub_playlists': 0, 
                                'help_playlists': 0, 
                                'shown_playlists': 0, 
                                'total_views': 0, 
                                'total_likes': 0, 
                                'total_comments': 0
                             })