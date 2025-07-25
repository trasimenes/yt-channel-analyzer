"""
Competitors Blueprint
Handles all competitor-related routes and functionality.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from blueprints.auth import login_required
from services.competitor_service import CompetitorDetailService


competitors_bp = Blueprint('competitors', __name__)


@competitors_bp.route('/concurrents')
@login_required
def concurrents():
    """Page de liste des concurrents"""
    from yt_channel_analyzer.database import get_db_connection
    import sqlite3
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer tous les concurrents avec leurs statistiques
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.channel_url,
                c.country,
                c.subscribers,
                COUNT(v.id) as video_count,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(AVG(v.view_count), 0) as avg_views
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id, c.name, c.channel_url, c.country, c.subscribers
            ORDER BY c.name
        """)
        
        competitors = []
        for row in cursor.fetchall():
            competitors.append({
                'id': row[0],
                'name': row[1],
                'channel_url': row[2],
                'country': row[3],
                'subscribers': row[4] or 0,
                'video_count': row[5],
                'total_views': row[6],
                'avg_views': int(row[7]) if row[7] else 0
            })
        
        conn.close()
        
        return render_template('concurrents_sneat_pro.html', 
                             competitors=competitors,
                             total_competitors=len(competitors))
                             
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in concurrents: {e}")
        flash("Erreur lors du chargement des concurrents", "error")
        return render_template('concurrents_sneat_pro.html', 
                             competitors=[],
                             total_competitors=0)


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
            flash("Concurrent non trouvé.", "error")
            return redirect(url_for('competitors.concurrents'))
        
        # Render template with clean data structure
        return render_template('competitor_detail_sneat_pro.html',
                               competitor=data['competitor'],
                               videos=data['videos'],
                               stats=data['stats'],
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
                               dev_mode=session.get('dev_mode', False))
    
    except Exception as e:
        flash(f"Erreur lors du chargement des données du concurrent: {str(e)}", "error")
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
            flash("Concurrent non trouvé.", "error")
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
        
        conn.close()
        
        return render_template('top_videos_sneat_pro.html',
                             videos=videos,
                             sort_by=sort_by,
                             order=order,
                             category_filter=category_filter,
                             limit=limit,
                             organic_filter=organic_filter,
                             total_videos=len(videos))
                             
    except Exception as e:
        print(f"[ERROR] Error in top_videos: {e}")
        flash("Erreur lors du chargement des vidéos", "error")
        return render_template('top_videos_sneat_pro.html',
                             videos=[],
                             sort_by='view_count',
                             order='desc',
                             category_filter='all',
                             limit=50,
                             organic_filter='all',
                             total_videos=0)


@competitors_bp.route('/top-playlists')
@login_required
def top_playlists():
    """Page des meilleures playlists"""
    from yt_channel_analyzer.database import get_db_connection
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les playlists avec leurs statistiques agrégées
        cursor.execute("""
            SELECT 
                p.id,
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
                MAX(v.published_at) as latest_video_date
            FROM playlist p
            JOIN concurrent c ON p.concurrent_id = c.id
            LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
            LEFT JOIN video v ON pv.video_id = v.id
            GROUP BY p.id, p.name, p.description, p.thumbnail_url, p.category, p.video_count, c.name, c.country
            ORDER BY total_views DESC
            LIMIT 50
        """)
        
        playlists = []
        for row in cursor.fetchall():
            engagement_rate = 0
            if row[8]:  # total_views
                engagement_rate = ((row[9] + row[10]) / row[8]) * 100  # (likes + comments) / views * 100
            
            playlists.append({
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'thumbnail_url': row[3],
                'category': row[4] or 'uncategorized',
                'video_count': row[5] or 0,
                'competitor_name': row[6],
                'country': row[7],
                'total_views': row[8],
                'total_likes': row[9],
                'total_comments': row[10],
                'avg_views': int(row[11]) if row[11] else 0,
                'latest_video_date': row[12],
                'engagement_rate': round(engagement_rate, 2)
            })
        
        conn.close()
        
        return render_template('top_playlists_sneat_pro.html',
                             playlists=playlists,
                             total_playlists=len(playlists))
                             
    except Exception as e:
        print(f"[ERROR] Error in top_playlists: {e}")
        flash("Erreur lors du chargement des playlists", "error")
        return render_template('top_playlists_sneat_pro.html',
                             playlists=[],
                             total_playlists=0)