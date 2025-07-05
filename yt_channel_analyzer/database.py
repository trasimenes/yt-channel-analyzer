"""
Module pour les interactions avec la base de données SQLite.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import re

DB_PATH = 'instance/database.db'

def get_db_connection():
    """Créer une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
    return conn

def extract_video_id_from_url(video_url: str) -> str:
    """Extraire l'ID vidéo depuis l'URL YouTube"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:v\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    
    # Fallback: utiliser l'URL complète comme ID
    return video_url.replace('/', '_').replace(':', '_')[:50]

def extract_channel_id_from_url(channel_url: str) -> str:
    """Extraire l'ID de chaîne depuis l'URL YouTube"""
    if '/channel/' in channel_url:
        return channel_url.split('/channel/')[-1].split('/')[0].split('?')[0]
    elif '/@' in channel_url:
        return channel_url.split('/@')[-1].split('/')[0].split('?')[0]
    elif '/c/' in channel_url:
        return channel_url.split('/c/')[-1].split('/')[0].split('?')[0]
    elif '/user/' in channel_url:
        return channel_url.split('/user/')[-1].split('/')[0].split('?')[0]
    else:
        return channel_url.replace('/', '_').replace(':', '_')[:100]

def save_competitor_and_videos(channel_url: str, videos: List[Dict], channel_info: Dict = None) -> int:
    """
    Sauvegarder un concurrent et ses vidéos dans la base de données.
    Crée automatiquement le concurrent s'il n'existe pas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier si le concurrent existe déjà
        cursor.execute('SELECT id FROM concurrent WHERE channel_url = ?', (channel_url,))
        existing = cursor.fetchone()
        
        if existing:
            competitor_id = existing[0]
            print(f"[DB] Concurrent existant trouvé: ID {competitor_id}")
        else:
            # Créer un nouveau concurrent
            channel_id = extract_channel_id_from_url(channel_url)
            
            # Utiliser les infos de la chaîne si disponibles
            if channel_info:
                name = channel_info.get('title', 'Canal inconnu')
                thumbnail_url = channel_info.get('thumbnail', '')
                banner_url = channel_info.get('banner', '')
                description = channel_info.get('description', '')
                subscriber_count = channel_info.get('subscriber_count')
                view_count = channel_info.get('view_count')
                video_count = len(videos)
                country = channel_info.get('country', '')
                language = channel_info.get('language', '')
            else:
                # Valeurs par défaut
                name = channel_url.split('/')[-1] if '/' in channel_url else 'Canal inconnu'
                thumbnail_url = ''
                banner_url = ''
                description = ''
                subscriber_count = None
                view_count = None
                video_count = len(videos)
                country = ''
                language = ''
            
            cursor.execute('''
                INSERT INTO concurrent (
                    name, channel_id, channel_url, thumbnail_url, banner_url,
                    description, subscriber_count, view_count, video_count,
                    country, language, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, channel_id, channel_url, thumbnail_url, banner_url,
                description, subscriber_count, view_count, video_count,
                country, language, datetime.now(), datetime.now()
            ))
            
            competitor_id = cursor.lastrowid
            print(f"[DB] Nouveau concurrent créé: {name} (ID {competitor_id})")
        
        # Sauvegarder les vidéos
        videos_added = 0
        videos_updated = 0
        
        for video in videos:
            video_id = extract_video_id_from_url(video.get('url', ''))
            
            # Vérifier si la vidéo existe déjà
            cursor.execute('SELECT id FROM video WHERE video_id = ?', (video_id,))
            existing_video = cursor.fetchone()
            
            # Préparer les données de la vidéo
            title = video.get('title', '')[:200]  # Limiter à 200 caractères
            description = video.get('description', '')
            url = video.get('url', '')
            thumbnail_url = video.get('thumbnail', '')
            
            # Traiter la date de publication
            published_at = None
            if video.get('publication_date'):
                try:
                    # Essayer de parser différents formats de date
                    date_str = video['publication_date']
                    if 'il y a' in date_str:
                        # Pour les dates relatives, utiliser la date actuelle
                        published_at = datetime.now()
                    else:
                        # Essayer de parser la date directement
                        published_at = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    published_at = datetime.now()
            
            # Traiter la durée
            duration_seconds = None
            duration_text = video.get('duration', '')
            if duration_text:
                try:
                    # Convertir "2:45" en secondes
                    parts = duration_text.split(':')
                    if len(parts) == 2:
                        duration_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except:
                    pass
            
            # Traiter les métriques
            view_count = video.get('views') or video.get('view_count') or 0
            if isinstance(view_count, str):
                view_count = int(re.sub(r'[^\d]', '', view_count)) if re.sub(r'[^\d]', '', view_count) else 0
            
            like_count = video.get('likes') or video.get('like_count')
            comment_count = video.get('comments') or video.get('comment_count')
            
            if existing_video:
                # Mettre à jour la vidéo existante
                cursor.execute('''
                    UPDATE video SET
                        title = ?, description = ?, url = ?, thumbnail_url = ?,
                        published_at = ?, duration_seconds = ?, duration_text = ?,
                        view_count = ?, like_count = ?, comment_count = ?,
                        last_updated = ?
                    WHERE id = ?
                ''', (
                    title, description, url, thumbnail_url,
                    published_at, duration_seconds, duration_text,
                    view_count, like_count, comment_count,
                    datetime.now(), existing_video[0]
                ))
                videos_updated += 1
            else:
                # Insérer une nouvelle vidéo
                cursor.execute('''
                    INSERT INTO video (
                        concurrent_id, video_id, title, description, url, thumbnail_url,
                        published_at, duration_seconds, duration_text,
                        view_count, like_count, comment_count,
                        created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    competitor_id, video_id, title, description, url, thumbnail_url,
                    published_at, duration_seconds, duration_text,
                    view_count, like_count, comment_count,
                    datetime.now(), datetime.now()
                ))
                videos_added += 1
        
        # Mettre à jour le nombre de vidéos du concurrent
        cursor.execute('SELECT COUNT(*) FROM video WHERE concurrent_id = ?', (competitor_id,))
        total_videos = cursor.fetchone()[0]
        
        cursor.execute('''
            UPDATE concurrent SET video_count = ?, last_updated = ? WHERE id = ?
        ''', (total_videos, datetime.now(), competitor_id))
        
        conn.commit()
        print(f"[DB] Sauvegarde terminée: {videos_added} vidéos ajoutées, {videos_updated} mises à jour, total: {total_videos}")
        
        return competitor_id
        
    except Exception as e:
        conn.rollback()
        print(f"[DB] Erreur lors de la sauvegarde: {e}")
        raise
    finally:
        conn.close()

def get_competitor_videos(competitor_id: int) -> List[Dict]:
    """Récupérer toutes les vidéos d'un concurrent"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM video 
        WHERE concurrent_id = ? 
        ORDER BY published_at DESC
    ''', (competitor_id,))
    
    videos = []
    for row in cursor.fetchall():
        videos.append(dict(row))
    
    conn.close()
    return videos

def get_all_competitors() -> List[Dict]:
    """Récupérer tous les concurrents depuis la base de données avec vues totales calculées"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM concurrent 
        ORDER BY name
    ''')
    
    competitors = []
    for row in cursor.fetchall():
        competitor = dict(row)
        
        # Calculer les vues totales en sommant les vues de toutes ses vidéos
        cursor.execute('''
            SELECT COALESCE(SUM(view_count), 0) as total_views
            FROM video 
            WHERE concurrent_id = ?
        ''', (competitor['id'],))
        
        total_views_result = cursor.fetchone()
        competitor['total_views'] = total_views_result[0] if total_views_result else 0
        
        competitors.append(competitor)
    
    conn.close()
    return competitors

def get_competitor_by_url(channel_url: str) -> Optional[Dict]:
    """Récupérer un concurrent par son URL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM concurrent WHERE channel_url = ?', (channel_url,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None

def add_competitor(competitor_data: Dict) -> int:
    """Ajouter un nouveau concurrent"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO concurrent (
            name, channel_id, channel_url, thumbnail_url, banner_url,
            description, subscriber_count, view_count, video_count,
            country, language, created_at, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        competitor_data.get('name'),
        competitor_data.get('channel_id'),
        competitor_data.get('channel_url'),
        competitor_data.get('thumbnail_url'),
        competitor_data.get('banner_url'),
        competitor_data.get('description'),
        competitor_data.get('subscriber_count'),
        competitor_data.get('view_count'),
        competitor_data.get('video_count'),
        competitor_data.get('country'),
        competitor_data.get('language'),
        datetime.now(),
        datetime.now()
    ))
    
    competitor_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return competitor_id

def update_competitor(competitor_id: int, updates: Dict):
    """Mettre à jour un concurrent"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Construire la requête dynamiquement
    set_clause = []
    values = []
    
    for key, value in updates.items():
        if key in ['name', 'thumbnail_url', 'banner_url', 'description', 
                   'subscriber_count', 'view_count', 'video_count', 'country', 'language']:
            set_clause.append(f"{key} = ?")
            values.append(value)
    
    if set_clause:
        set_clause.append("last_updated = ?")
        values.append(datetime.now())
        values.append(competitor_id)
        
        query = f"UPDATE concurrent SET {', '.join(set_clause)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
    
    conn.close()

def delete_competitor(competitor_id: int):
    """Supprimer un concurrent et toutes ses vidéos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # SQLite gère automatiquement la suppression en cascade des vidéos
    cursor.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
    
    conn.commit()
    conn.close()

def competitors_to_legacy_format() -> Dict:
    """Convertir les concurrents de la base vers le format JSON legacy pour compatibilité"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer tous les concurrents avec leurs vidéos
    cursor.execute('''
        SELECT c.*, COUNT(v.id) as video_count_actual
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        GROUP BY c.id
        ORDER BY c.name
    ''')
    
    competitors = cursor.fetchall()
    legacy_data = {}
    
    for comp in competitors:
        # Créer une clé compatible avec l'ancien format
        key = comp['channel_url'].replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_')
        
        # Récupérer les vidéos de ce concurrent
        cursor.execute('''
            SELECT * FROM video WHERE concurrent_id = ? ORDER BY published_at DESC
        ''', (comp['id'],))
        
        videos = []
        for video_row in cursor.fetchall():
            video_dict = dict(video_row)
            # Convertir au format legacy
            videos.append({
                'title': video_dict['title'],
                'url': video_dict['url'],
                'views': video_dict['view_count'] or 0,
                'view_count': video_dict['view_count'] or 0,
                'publication_date': video_dict['published_at'].strftime('%Y-%m-%d') if video_dict['published_at'] and hasattr(video_dict['published_at'], 'strftime') else str(video_dict['published_at']) if video_dict['published_at'] else '',
                'duration': video_dict['duration_text'] or '',
                'thumbnail': video_dict['thumbnail_url'] or '',
                'description': video_dict['description'] or '',
                'likes': video_dict['like_count'],
                'comments': video_dict['comment_count']
            })
        
        legacy_data[key] = {
            'name': comp['name'],
            'channel_url': comp['channel_url'],
            'channel_id': comp['channel_id'],
            'thumbnail': comp['thumbnail_url'],
            'banner': comp['banner_url'],
            'description': comp['description'],
            'subscriber_count': comp['subscriber_count'],
            'view_count': comp['view_count'],
            'video_count': comp['video_count_actual'],  # Utiliser le vrai count
            'country': comp['country'],
            'language': comp['language'],
            'last_updated': comp['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if comp['last_updated'] and hasattr(comp['last_updated'], 'strftime') else str(comp['last_updated']) if comp['last_updated'] else '',
            'videos': videos,
            'total_videos': len(videos),
            'total_views': sum(v.get('view_count', 0) for v in videos)
        }
    
    conn.close()
    return legacy_data

def save_competitor_playlists(competitor_id: int, playlists: List[Dict]):
    """Sauvegarder les playlists d'un concurrent"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for playlist in playlists:
            playlist_id = playlist.get('playlist_id', '')
            name = playlist.get('name', '')[:200]
            description = playlist.get('description', '')
            thumbnail_url = playlist.get('thumbnail_url', '')
            video_count = playlist.get('video_count', 0)
            
            # Vérifier si la playlist existe déjà
            cursor.execute(
                'SELECT id FROM playlist WHERE playlist_id = ? AND concurrent_id = ?',
                (playlist_id, competitor_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Mettre à jour la playlist existante
                cursor.execute('''
                    UPDATE playlist SET
                        name = ?, description = ?, thumbnail_url = ?, video_count = ?,
                        last_updated = ?
                    WHERE id = ?
                ''', (name, description, thumbnail_url, video_count, datetime.now(), existing[0]))
            else:
                # Créer une nouvelle playlist
                cursor.execute('''
                    INSERT INTO playlist (
                        concurrent_id, playlist_id, name, description, thumbnail_url, video_count,
                        created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    competitor_id, playlist_id, name, description, thumbnail_url, video_count,
                    datetime.now(), datetime.now()
                ))
        
        conn.commit()
        print(f"[DB] Sauvegarde terminée: {len(playlists)} playlists")
        
    except Exception as e:
        conn.rollback()
        print(f"[DB] Erreur lors de la sauvegarde des playlists: {e}")
        raise
    finally:
        conn.close()

def get_competitor_playlists(competitor_id: int) -> List[Dict]:
    """Récupérer toutes les playlists d'un concurrent"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM playlist 
        WHERE concurrent_id = ? 
        ORDER BY video_count DESC, name ASC
    ''', (competitor_id,))
    
    playlists = []
    for row in cursor.fetchall():
        playlists.append(dict(row))
    
    conn.close()
    return playlists

def update_playlist_category(playlist_id: int, category: str):
    """Mettre à jour la catégorie d'une playlist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE playlist SET category = ?, last_updated = ? WHERE id = ?
    ''', (category, datetime.now(), playlist_id))
    
    conn.commit()
    conn.close()

def apply_playlist_categories_to_videos(competitor_id: int):
    """Appliquer automatiquement les catégories des playlists aux vidéos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer toutes les playlists catégorisées du concurrent
        cursor.execute('''
            SELECT id, category FROM playlist 
            WHERE concurrent_id = ? AND category IS NOT NULL
        ''', (competitor_id,))
        
        categorized_playlists = cursor.fetchall()
        videos_updated = 0
        
        for playlist_row in categorized_playlists:
            playlist_db_id = playlist_row[0]
            category = playlist_row[1]
            
            # Mettre à jour toutes les vidéos de cette playlist
            cursor.execute('''
                UPDATE video SET category = ?, last_updated = ?
                WHERE id IN (
                    SELECT pv.video_id FROM playlist_video pv
                    WHERE pv.playlist_id = ?
                )
            ''', (category, datetime.now(), playlist_db_id))
            
            videos_updated += cursor.rowcount
        
        conn.commit()
        print(f"[DB] Classification automatique terminée: {videos_updated} vidéos mises à jour")
        return {
            'videos_updated': videos_updated
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[DB] Erreur lors de la classification automatique: {e}")
        raise
    finally:
        conn.close()

def link_playlist_videos(playlist_db_id: int, video_ids: List[str]):
    """Lier des vidéos à une playlist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for position, video_id in enumerate(video_ids):
            # Récupérer l'ID de la vidéo dans notre base
            cursor.execute('SELECT id FROM video WHERE video_id = ?', (video_id,))
            video_row = cursor.fetchone()
            
            if video_row:
                video_db_id = video_row[0]
                
                # Insérer la liaison (ignore si elle existe déjà)
                cursor.execute('''
                    INSERT OR IGNORE INTO playlist_video (playlist_id, video_id, position)
                    VALUES (?, ?, ?)
                ''', (playlist_db_id, video_db_id, position))
        
        conn.commit()
        print(f"[DB] Liaison terminée: {len(video_ids)} vidéos liées à la playlist")
        
    except Exception as e:
        conn.rollback()
        print(f"[DB] Erreur lors de la liaison playlist-vidéos: {e}")
        raise
    finally:
        conn.close() 

def refresh_competitor_data(channel_url: str, fresh_videos: List[Dict], channel_info: Dict = None) -> Dict:
    """
    Rafraîchir intelligemment les données d'un concurrent existant.
    - Ajoute les nouvelles vidéos
    - Enrichit les vidéos existantes en gardant les valeurs maximales (vues, likes, commentaires)
    - Met à jour les informations de la chaîne
    
    Returns:
        Dict avec les statistiques de mise à jour
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier si le concurrent existe
        cursor.execute('SELECT id, name FROM concurrent WHERE channel_url = ?', (channel_url,))
        existing = cursor.fetchone()
        
        if not existing:
            # Si le concurrent n'existe pas, utiliser la fonction normale
            competitor_id = save_competitor_and_videos(channel_url, fresh_videos, channel_info)
            return {
                'success': True,
                'action': 'created',
                'competitor_id': competitor_id,
                'new_videos': len(fresh_videos),
                'updated_videos': 0,
                'enriched_videos': 0
            }
        
        competitor_id = existing[0]
        competitor_name = existing[1]
        print(f"[REFRESH] 🔄 Rafraîchissement de {competitor_name} (ID {competitor_id})")
        
        # Récupérer les vidéos existantes
        cursor.execute('''
            SELECT video_id, view_count, like_count, comment_count, title, url
            FROM video WHERE concurrent_id = ?
        ''', (competitor_id,))
        existing_videos = {row[0]: {
            'view_count': row[1] or 0,
            'like_count': row[2] or 0, 
            'comment_count': row[3] or 0,
            'title': row[4],
            'url': row[5]
        } for row in cursor.fetchall()}
        
        stats = {
            'new_videos': 0,
            'updated_videos': 0,
            'enriched_videos': 0,
            'total_processed': len(fresh_videos)
        }
        
        # Traiter chaque vidéo fraîche
        for video in fresh_videos:
            video_id = extract_video_id_from_url(video.get('url', ''))
            
            # Préparer les données de base
            title = video.get('title', '')[:200]
            description = video.get('description', '')
            url = video.get('url', '')
            thumbnail_url = video.get('thumbnail', '')
            
            # Traiter la date de publication
            published_at = None
            if video.get('publication_date'):
                try:
                    date_str = video['publication_date']
                    if 'il y a' in date_str:
                        published_at = datetime.now()
                    else:
                        published_at = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    published_at = datetime.now()
            
            # Traiter la durée
            duration_seconds = None
            duration_text = video.get('duration', '')
            if duration_text:
                try:
                    parts = duration_text.split(':')
                    if len(parts) == 2:
                        duration_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except:
                    pass
            
            # Traiter les métriques avec valeurs par défaut
            fresh_view_count = video.get('views') or video.get('view_count') or 0
            if isinstance(fresh_view_count, str):
                fresh_view_count = int(re.sub(r'[^\d]', '', fresh_view_count)) if re.sub(r'[^\d]', '', fresh_view_count) else 0
            
            fresh_like_count = video.get('likes') or video.get('like_count') or 0
            if isinstance(fresh_like_count, str):
                fresh_like_count = int(re.sub(r'[^\d]', '', fresh_like_count)) if re.sub(r'[^\d]', '', fresh_like_count) else 0
                
            fresh_comment_count = video.get('comments') or video.get('comment_count') or 0
            if isinstance(fresh_comment_count, str):
                fresh_comment_count = int(re.sub(r'[^\d]', '', fresh_comment_count)) if re.sub(r'[^\d]', '', fresh_comment_count) else 0
            
            if video_id in existing_videos:
                # Vidéo existante : ENRICHIR avec les valeurs maximales
                existing = existing_videos[video_id]
                
                # Prendre les valeurs maximales
                max_views = max(existing['view_count'], fresh_view_count)
                max_likes = max(existing['like_count'], fresh_like_count)
                max_comments = max(existing['comment_count'], fresh_comment_count)
                
                # Déterminer si on a enrichi les données
                enriched = (
                    max_views > existing['view_count'] or 
                    max_likes > existing['like_count'] or 
                    max_comments > existing['comment_count']
                )
                
                if enriched:
                    stats['enriched_videos'] += 1
                    print(f"[REFRESH] 📈 Enrichi: {title[:50]}... "
                          f"(vues: {existing['view_count']} → {max_views}, "
                          f"likes: {existing['like_count']} → {max_likes})")
                
                # Mettre à jour avec les valeurs maximales
                cursor.execute('''
                    UPDATE video SET
                        title = ?, description = ?, thumbnail_url = ?,
                        published_at = ?, duration_seconds = ?, duration_text = ?,
                        view_count = ?, like_count = ?, comment_count = ?,
                        last_updated = ?
                    WHERE concurrent_id = ? AND video_id = ?
                ''', (
                    title, description, thumbnail_url,
                    published_at, duration_seconds, duration_text,
                    max_views, max_likes, max_comments,
                    datetime.now(), competitor_id, video_id
                ))
                
                stats['updated_videos'] += 1
                
            else:
                # Nouvelle vidéo : AJOUTER
                cursor.execute('''
                    INSERT INTO video (
                        concurrent_id, video_id, title, description, url, thumbnail_url,
                        published_at, duration_seconds, duration_text,
                        view_count, like_count, comment_count,
                        created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    competitor_id, video_id, title, description, url, thumbnail_url,
                    published_at, duration_seconds, duration_text,
                    fresh_view_count, fresh_like_count, fresh_comment_count,
                    datetime.now(), datetime.now()
                ))
                
                stats['new_videos'] += 1
                print(f"[REFRESH] ✨ Nouvelle: {title[:50]}... ({fresh_view_count} vues)")
        
        # Mettre à jour les informations de la chaîne si disponibles
        if channel_info:
            updates = {
                'thumbnail_url': channel_info.get('thumbnail', ''),
                'banner_url': channel_info.get('banner', ''),
                'description': channel_info.get('description', ''),
                'subscriber_count': channel_info.get('subscriber_count'),
                'view_count': channel_info.get('view_count'),
                'country': channel_info.get('country', ''),
                'language': channel_info.get('language', ''),
                'last_updated': datetime.now()
            }
            
            # Construire la requête de mise à jour dynamiquement
            set_clauses = []
            values = []
            for key, value in updates.items():
                if value is not None:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if set_clauses:
                values.append(competitor_id)
                cursor.execute(f'''
                    UPDATE concurrent SET {', '.join(set_clauses)} WHERE id = ?
                ''', values)
                
                # Enregistrer l'évolution des statistiques
                try:
                    # Analytics export supprimé - analyse locale maintenant
                    track_competitor_update(competitor_id, channel_info)
                except Exception as e:
                    print(f"[REFRESH] ⚠️ Erreur lors du tracking: {e}")
        
        # Mettre à jour le nombre total de vidéos
        cursor.execute('SELECT COUNT(*) FROM video WHERE concurrent_id = ?', (competitor_id,))
        total_videos = cursor.fetchone()[0]
        
        cursor.execute('''
            UPDATE concurrent SET video_count = ?, last_updated = ? WHERE id = ?
        ''', (total_videos, datetime.now(), competitor_id))
        
        conn.commit()
        
        print(f"[REFRESH] ✅ Rafraîchissement terminé pour {competitor_name}:")
        print(f"  • {stats['new_videos']} nouvelles vidéos")
        print(f"  • {stats['updated_videos']} vidéos mises à jour")
        print(f"  • {stats['enriched_videos']} vidéos enrichies")
        print(f"  • {total_videos} vidéos au total")
        
        return {
            'success': True,
            'action': 'refreshed',
            'competitor_id': competitor_id,
            'competitor_name': competitor_name,
            'total_videos': total_videos,
            **stats
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[REFRESH] ❌ Erreur lors du rafraîchissement: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        conn.close() 

def get_all_competitors_with_videos() -> List[Dict]:
    """
    Récupérer tous les concurrents avec leurs vidéos
    
    Returns:
        List[Dict]: Liste des concurrents avec leurs vidéos
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer tous les concurrents
        cursor.execute('''
            SELECT id, name, channel_id, channel_url, thumbnail_url, banner_url,
                   description, subscriber_count, view_count, video_count,
                   country, language, created_at, last_updated
            FROM concurrent
            ORDER BY last_updated DESC
        ''')
        
        competitors = []
        for row in cursor.fetchall():
            competitor = {
                'id': row[0],
                'name': row[1],
                'channel_id': row[2],
                'channel_url': row[3],
                'thumbnail_url': row[4],
                'banner_url': row[5],
                'description': row[6],
                'subscriber_count': row[7],
                'view_count': row[8],
                'video_count': row[9],
                'country': row[10],
                'language': row[11],
                'created_at': row[12],
                'last_updated': row[13]
            }
            
            # Récupérer les vidéos pour ce concurrent
            cursor.execute('''
                SELECT video_id, title, description, url, thumbnail_url,
                       published_at, duration_seconds, duration_text,
                       view_count, like_count, comment_count, category
                FROM video
                WHERE concurrent_id = ?
                ORDER BY published_at DESC
            ''', (competitor['id'],))
            
            videos = []
            for video_row in cursor.fetchall():
                video = {
                    'video_id': video_row[0],
                    'title': video_row[1],
                    'description': video_row[2],
                    'url': video_row[3],
                    'thumbnail': video_row[4],
                    'published_at': video_row[5],
                    'duration_seconds': video_row[6],
                    'duration': video_row[7],
                    'view_count': video_row[8] or 0,
                    'like_count': video_row[9] or 0,
                    'comment_count': video_row[10] or 0,
                    'category': video_row[11]
                }
                videos.append(video)
            
            # Calculer les vues totales
            competitor['videos'] = videos
            competitor['total_views'] = sum(video.get('view_count', 0) or 0 for video in videos)
            competitors.append(competitor)
        
        return competitors
        
    finally:
        conn.close() 

def clean_duplicate_competitors() -> Dict:
    """
    Nettoyer les doublons de concurrents en gardant celui avec le plus de vidéos.
    Utilise le nom ET l'URL de chaîne pour détecter les doublons.
    
    Returns:
        Dict avec les statistiques de nettoyage
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("[DB-CLEAN] 🧹 Début du nettoyage des doublons...")
        
        # Récupérer tous les concurrents avec leur nombre de vidéos
        cursor.execute('''
            SELECT c.id, c.name, c.channel_url, c.channel_id, 
                   COUNT(v.id) as video_count,
                   c.created_at, c.last_updated
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id
            ORDER BY c.name, video_count DESC
        ''')
        
        competitors = cursor.fetchall()
        
        if not competitors:
            return {'success': True, 'deleted_count': 0, 'message': 'Aucun concurrent trouvé'}
        
        # Grouper par nom (insensible à la casse) et URL similaire
        groups = {}
        for comp in competitors:
            comp_id, name, channel_url, channel_id, video_count, created_at, last_updated = comp
            
            # Clé de groupement : nom nettoyé + channel_id si disponible
            name_clean = name.lower().strip()
            group_key = name_clean
            
            # Si on a un channel_id, l'utiliser comme clé plus précise
            if channel_id:
                group_key = f"{name_clean}_{channel_id}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append({
                'id': comp_id,
                'name': name,
                'channel_url': channel_url,
                'channel_id': channel_id,
                'video_count': video_count,
                'created_at': created_at,
                'last_updated': last_updated
            })
        
        # Identifier et supprimer les doublons
        deleted_count = 0
        kept_competitors = []
        
        for group_key, group_competitors in groups.items():
            if len(group_competitors) > 1:
                # Trier par nombre de vidéos (desc) puis par date de création (plus récent)
                group_competitors.sort(key=lambda x: (-x['video_count'], x['last_updated'] or ''), reverse=True)
                
                # Garder le premier (celui avec le plus de vidéos)
                best = group_competitors[0]
                to_delete = group_competitors[1:]
                
                print(f"[DB-CLEAN] 🔍 Doublons trouvés pour '{best['name']}':")
                print(f"  ✅ GARDE: ID {best['id']} - {best['video_count']} vidéos - {best['channel_url']}")
                
                # Supprimer les doublons
                for duplicate in to_delete:
                    print(f"  ❌ SUPPRIME: ID {duplicate['id']} - {duplicate['video_count']} vidéos - {duplicate['channel_url']}")
                    
                    # Supprimer le concurrent (les vidéos sont supprimées par CASCADE)
                    cursor.execute('DELETE FROM concurrent WHERE id = ?', (duplicate['id'],))
                    deleted_count += 1
                
                kept_competitors.append(best)
            else:
                # Pas de doublon, garder tel quel
                kept_competitors.append(group_competitors[0])
        
        # Valider les changements
        conn.commit()
        
        print(f"[DB-CLEAN] ✅ Nettoyage terminé:")
        print(f"  • {deleted_count} doublons supprimés")
        print(f"  • {len(kept_competitors)} concurrents uniques conservés")
        
        # Afficher le résultat final
        for comp in kept_competitors:
            print(f"  📊 {comp['name']}: {comp['video_count']} vidéos")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'kept_count': len(kept_competitors),
            'competitors': kept_competitors,
            'message': f'{deleted_count} doublons supprimés, {len(kept_competitors)} concurrents uniques conservés'
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[DB-CLEAN] ❌ Erreur lors du nettoyage: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        conn.close() 

def get_all_competitors_urls():
    """Récupère toutes les URLs des concurrents en base de données"""
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        cursor.execute("SELECT channel_url FROM concurrent")
        urls = [row[0] for row in cursor.fetchall()]
        
        connection.close()
        return urls
        
    except Exception as e:
        print(f"[DATABASE] Erreur lors de la récupération des URLs des concurrents: {e}")
        return [] 

def update_competitor_country(competitor_id, country):
    """Met à jour le pays d'un concurrent"""
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE concurrent 
            SET country = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (country, competitor_id))
        
        connection.commit()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"[DATABASE] Erreur lors de la mise à jour du pays: {e}")
        return False

def get_competitors_by_country():
    """Récupère les concurrents groupés par pays"""
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT country, COUNT(*) as count, 
                   GROUP_CONCAT(name, ', ') as competitors
            FROM concurrent 
            GROUP BY country
            ORDER BY country
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'country': row[0] if row[0] else 'Non défini',
                'count': row[1],
                'competitors': row[2]
            })
        
        connection.close()
        return results
        
    except Exception as e:
        print(f"[DATABASE] Erreur lors de la récupération par pays: {e}")
        return [] 

def classify_playlist_with_ai(name: str, description: str = "") -> str:
    """
    Classifier automatiquement une playlist en analysant son nom et sa description
    Retourne 'hero', 'hub' ou 'help'
    """
    # Nettoyer et normaliser le texte
    text = f"{name} {description}".lower().strip()
    
    # Mots-clés pour chaque catégorie (50+ mots-clés par catégorie)
    hero_keywords = [
        # Expériences exceptionnelles
        'best', 'meilleur', 'top', 'incroyable', 'amazing', 'incredible', 'spectacular',
        'luxury', 'luxe', 'premium', 'exclusive', 'exclusif', 'unique', 'extraordinary',
        'destination', 'voyage', 'travel', 'adventure', 'aventure', 'epic', 'épique',
        'experience', 'expérience', 'découverte', 'discovery', 'exploration',
        'must', 'essentiels', 'featured', 'highlights', 'coup de coeur', 'unforgettable',
        'recommendation', 'recommandation', 'favorite', 'favori', 'preferred',
        'inspiration', 'dream', 'rêve', 'bucket list', 'wishlist', 'fantasy',
        # Performance et succès
        'ultimate', 'ultime', 'supreme', 'suprême', 'world class', 'classe mondiale',
        'exceptional', 'exceptionnel', 'outstanding', 'remarquable', 'stunning',
        'breathtaking', 'à couper le souffle', 'magnificent', 'magnifique',
        'extraordinary', 'extraordinaire', 'legendary', 'légendaire', 'iconic',
        'prestigious', 'prestigieux', 'award', 'prix', 'winner', 'gagnant',
        # Émotions fortes
        'magical', 'magique', 'enchanting', 'enchanteur', 'mesmerizing',
        'captivating', 'captivant', 'thrilling', 'palpitant', 'exhilarating',
        'mind-blowing', 'époustouflant', 'life-changing', 'transformant'
    ]
    
    hub_keywords = [
        # Contenu régulier/hub
        'how to', 'comment', 'tutorial', 'tutoriel', 'guide', 'tips', 'conseils',
        'planning', 'planifier', 'organize', 'organiser', 'prepare', 'préparer',
        'practical', 'pratique', 'useful', 'utile', 'everyday', 'quotidien',
        'general', 'général', 'overview', 'aperçu', 'basics', 'base', 'introduction',
        'information', 'info', 'facts', 'faits', 'details', 'détails', 'data',
        'series', 'série', 'collection', 'regular', 'régulier', 'weekly', 'monthly',
        # Organisation et structure
        'schedule', 'programme', 'agenda', 'calendar', 'calendrier', 'timeline',
        'checklist', 'liste', 'steps', 'étapes', 'process', 'processus',
        'method', 'méthode', 'technique', 'approach', 'approche', 'strategy',
        'system', 'système', 'framework', 'structure', 'organization',
        # Contenu informatif
        'review', 'revue', 'analysis', 'analyse', 'comparison', 'comparaison',
        'update', 'mise à jour', 'news', 'nouvelles', 'report', 'rapport',
        'summary', 'résumé', 'recap', 'récapitulatif', 'overview', 'survol',
        'breakdown', 'décomposition', 'explanation', 'explication', 'insight',
        'behind the scenes', 'en coulisses', 'making of', 'process', 'workflow',
        # Catégories générales
        'standard', 'normal', 'typical', 'typique', 'common', 'commun',
        'regular', 'régulier', 'routine', 'habitual', 'ordinary', 'ordinaire'
    ]
    
    help_keywords = [
        # Support/aide
        'help', 'aide', 'support', 'problem', 'problème', 'issue', 'question',
        'faq', 'frequently', 'fréquent', 'common', 'commun', 'typical', 'typique',
        'solve', 'résoudre', 'fix', 'réparer', 'troubleshoot', 'dépannage',
        'step by step', 'étape par étape', 'beginner', 'débutant', 'basics', 'base',
        'learn', 'apprendre', 'understand', 'comprendre', 'explain', 'expliquer',
        'avoid', 'éviter', 'mistake', 'erreur', 'warning', 'attention', 'caution',
        # Apprentissage et formation
        'tutorial', 'tutoriel', 'lesson', 'leçon', 'course', 'cours', 'training',
        'workshop', 'atelier', 'masterclass', 'formation', 'education', 'éducation',
        'instruction', 'instruction', 'demonstration', 'démonstration', 'example',
        'exemple', 'practice', 'pratique', 'exercise', 'exercice', 'drill',
        # Résolution de problèmes
        'solution', 'resolution', 'answer', 'réponse', 'remedy', 'remède',
        'cure', 'guérison', 'treatment', 'traitement', 'therapy', 'thérapie',
        'diagnosis', 'diagnostic', 'troubleshooting', 'dépannage', 'debugging',
        'repair', 'réparation', 'maintenance', 'entretien', 'service', 'assistance',
        # Orientation et conseils
        'guidance', 'orientation', 'advice', 'conseil', 'recommendation', 'recommandation',
        'suggestion', 'suggestion', 'tip', 'astuce', 'trick', 'truc', 'hack',
        'secret', 'secret', 'insider', 'initié', 'expert', 'specialist', 'professional',
        'consultation', 'mentoring', 'coaching', 'counseling', 'consulting'
    ]
    
    # Compter les occurrences pour chaque catégorie
    hero_score = sum(1 for keyword in hero_keywords if keyword in text)
    hub_score = sum(1 for keyword in hub_keywords if keyword in text)
    help_score = sum(1 for keyword in help_keywords if keyword in text)
    
    # Heuristiques supplémentaires basées sur la structure du nom
    if any(word in text for word in ['best of', 'top 10', 'top 5', 'highlights', 'most beautiful', 'plus beaux']):
        hero_score += 3
    
    if any(word in text for word in ['guide complet', 'complete guide', 'everything about', 'tout sur']):
        hub_score += 3
        
    if any(word in text for word in ['how to', 'comment faire', 'tutorial step', 'pas à pas']):
        help_score += 3
    
    # Patterns spéciaux
    if any(word in text for word in ['collection', 'compilation', 'playlist officielle', 'official playlist']):
        hub_score += 2
        
    if any(word in text for word in ['débutant', 'beginner', 'first time', 'première fois']):
        help_score += 2
        
    if any(word in text for word in ['exclusive', 'premium', 'vip', 'special edition']):
        hero_score += 2
    
    # Déterminer la catégorie avec le score le plus élevé
    scores = {'hero': hero_score, 'hub': hub_score, 'help': help_score}
    max_category = max(scores, key=scores.get)
    max_score = scores[max_category]
    
    # Si aucun score ou égalité, classer comme 'hub' par défaut
    if max_score == 0 or list(scores.values()).count(max_score) > 1:
        return 'hub'
    
    return max_category

def auto_classify_uncategorized_playlists(competitor_id: int) -> Dict:
    """
    Classifier automatiquement avec l'IA toutes les playlists non catégorisées d'un concurrent
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer toutes les playlists non catégorisées
        cursor.execute('''
            SELECT id, name, description FROM playlist 
            WHERE concurrent_id = ? AND (category IS NULL OR category = '')
        ''', (competitor_id,))
        
        uncategorized_playlists = cursor.fetchall()
        
        if not uncategorized_playlists:
            return {
                'success': True,
                'message': 'Aucune playlist non catégorisée trouvée',
                'classified_count': 0,
                'classifications': []
            }
        
        classifications = []
        classified_count = 0
        
        for playlist_row in uncategorized_playlists:
            playlist_id = playlist_row[0]
            name = playlist_row[1] or ''
            description = playlist_row[2] or ''
            
            # Classifier avec l'IA
            predicted_category = classify_playlist_with_ai(name, description)
            
            # Mettre à jour en base
            cursor.execute('''
                UPDATE playlist SET category = ?, last_updated = ? WHERE id = ?
            ''', (predicted_category, datetime.now(), playlist_id))
            
            classifications.append({
                'name': name,
                'predicted_category': predicted_category,
                'confidence': 'medium'  # Pour l'instant toujours medium
            })
            
            classified_count += 1
            print(f"[IA-CLASSIFY] ✨ {name} → {predicted_category.upper() if predicted_category else 'NON_CLASSE'}")
        
        conn.commit()
        
        return {
            'success': True,
            'message': f'{classified_count} playlists classifiées automatiquement',
            'classified_count': classified_count,
            'classifications': classifications
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[IA-CLASSIFY] ❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e),
            'classified_count': 0
        }
    finally:
        conn.close() 

# --- GESTION DES PATTERNS IA ---

def get_classification_patterns() -> Dict:
    """Récupérer tous les patterns de classification IA"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier si la table patterns existe, sinon la créer
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classification_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category VARCHAR(10) NOT NULL,
                pattern VARCHAR(200) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, pattern)
            )
        ''')
        
        # Récupérer les patterns existants
        cursor.execute('''
            SELECT category, pattern FROM classification_patterns 
            ORDER BY category, pattern
        ''')
        
        patterns = {'hero': [], 'hub': [], 'help': []}
        for row in cursor.fetchall():
            category, pattern = row
            if category in patterns:
                patterns[category].append(pattern)
        
        # Si aucun pattern n'existe, initialiser avec les patterns par défaut
        if not any(patterns.values()):
            default_patterns = get_default_classification_patterns()
            for category, pattern_list in default_patterns.items():
                for pattern in pattern_list:
                    cursor.execute('''
                        INSERT OR IGNORE INTO classification_patterns (category, pattern)
                        VALUES (?, ?)
                    ''', (category, pattern))
            conn.commit()
            patterns = default_patterns
        
        return patterns
        
    except Exception as e:
        print(f"[PATTERNS] Erreur: {e}")
        return get_default_classification_patterns()
    finally:
        conn.close()

def get_default_classification_patterns() -> Dict:
    """Patterns par défaut pour la classification IA"""
    return {
        'hero': [
            'best', 'meilleur', 'top', 'incroyable', 'amazing', 'incredible', 'spectacular',
            'luxury', 'luxe', 'premium', 'exclusive', 'exclusif', 'unique', 'extraordinary',
            'destination', 'voyage', 'travel', 'adventure', 'aventure', 'epic', 'épique',
            'experience', 'expérience', 'découverte', 'discovery', 'exploration',
            'must', 'essentiels', 'featured', 'highlights', 'coup de coeur', 'unforgettable',
            'recommendation', 'recommandation', 'favorite', 'favori', 'preferred',
            'inspiration', 'dream', 'rêve', 'bucket list', 'wishlist', 'fantasy',
            'ultimate', 'ultime', 'supreme', 'suprême', 'world class', 'classe mondiale',
            'exceptional', 'exceptionnel', 'outstanding', 'remarquable', 'stunning',
            'breathtaking', 'à couper le souffle', 'magnificent', 'magnifique',
            'legendary', 'légendaire', 'iconic', 'prestigious', 'prestigieux'
        ],
        'hub': [
            'how to', 'comment', 'tutorial', 'tutoriel', 'guide', 'tips', 'conseils',
            'planning', 'planifier', 'organize', 'organiser', 'prepare', 'préparer',
            'practical', 'pratique', 'useful', 'utile', 'everyday', 'quotidien',
            'general', 'général', 'overview', 'aperçu', 'basics', 'base', 'introduction',
            'information', 'info', 'facts', 'faits', 'details', 'détails', 'data',
            'series', 'série', 'collection', 'regular', 'régulier', 'weekly', 'monthly',
            'schedule', 'programme', 'agenda', 'calendar', 'calendrier', 'timeline',
            'checklist', 'liste', 'steps', 'étapes', 'process', 'processus',
            'method', 'méthode', 'technique', 'approach', 'approche', 'strategy',
            'review', 'revue', 'analysis', 'analyse', 'comparison', 'comparaison'
        ],
        'help': [
            'help', 'aide', 'support', 'problem', 'problème', 'issue', 'question',
            'faq', 'frequently', 'fréquent', 'common', 'commun', 'typical', 'typique',
            'solve', 'résoudre', 'fix', 'réparer', 'troubleshoot', 'dépannage',
            'step by step', 'étape par étape', 'beginner', 'débutant', 'basics', 'base',
            'learn', 'apprendre', 'understand', 'comprendre', 'explain', 'expliquer',
            'avoid', 'éviter', 'mistake', 'erreur', 'warning', 'attention', 'caution',
            'tutorial', 'tutoriel', 'lesson', 'leçon', 'course', 'cours', 'training',
            'solution', 'resolution', 'answer', 'réponse', 'remedy', 'remède',
            'guidance', 'orientation', 'advice', 'conseil', 'recommendation',
            'consultation', 'mentoring', 'coaching', 'counseling', 'consulting'
        ]
    }

def add_classification_pattern(category: str, pattern: str) -> bool:
    """Ajouter un nouveau pattern de classification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO classification_patterns (category, pattern)
            VALUES (?, ?)
        ''', (category, pattern.lower().strip()))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"[PATTERNS] Erreur ajout: {e}")
        return False
    finally:
        conn.close()

def remove_classification_pattern(category: str, pattern: str) -> bool:
    """Supprimer un pattern de classification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM classification_patterns 
            WHERE category = ? AND pattern = ?
        ''', (category, pattern.lower().strip()))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"[PATTERNS] Erreur suppression: {e}")
        return False
    finally:
        conn.close()

def get_ai_classification_setting() -> bool:
    """Récupérer le paramètre de classification IA automatique"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer la table settings si elle n'existe pas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            SELECT value FROM app_settings WHERE key = 'ai_classification_enabled'
        ''')
        
        result = cursor.fetchone()
        return result[0] == 'true' if result else False
        
    except Exception as e:
        print(f"[SETTINGS] Erreur: {e}")
        return False
    finally:
        conn.close()

def set_ai_classification_setting(enabled: bool) -> bool:
    """Définir le paramètre de classification IA automatique"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES ('ai_classification_enabled', ?, ?)
        ''', ('true' if enabled else 'false', datetime.now()))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[SETTINGS] Erreur: {e}")
        return False
    finally:
        conn.close()

def classify_videos_directly_with_keywords(competitor_id: int) -> Dict:
    """
    Classifier directement les vidéos non catégorisées en utilisant les mots-clés configurés
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer toutes les vidéos non catégorisées du concurrent
        cursor.execute('''
            SELECT id, title, description FROM video 
            WHERE concurrent_id = ? AND (category IS NULL OR category = '')
        ''', (competitor_id,))
        
        uncategorized_videos = cursor.fetchall()
        
        if not uncategorized_videos:
            return {
                'success': True,
                'message': 'Aucune vidéo non catégorisée trouvée',
                'videos_classified': 0
            }
        
        videos_classified = 0
        
        for video_row in uncategorized_videos:
            video_id = video_row[0]
            title = video_row[1] or ''
            description = video_row[2] or ''
            
            # Classifier avec les mots-clés configurés
            predicted_category = classify_playlist_with_ai(title, description)
            
            # Mettre à jour en base
            cursor.execute('''
                UPDATE video SET category = ?, last_updated = ? WHERE id = ?
            ''', (predicted_category, datetime.now(), video_id))
            
            videos_classified += 1
            
            # Log seulement quelques exemples pour éviter le spam
            if videos_classified <= 5:
                print(f"[DIRECT-CLASSIFY] ✨ {title} → {predicted_category.upper() if predicted_category else 'NON_CLASSE'}")
        
        conn.commit()
        
        if videos_classified > 5:
            print(f"[DIRECT-CLASSIFY] ✨ ... et {videos_classified - 5} vidéos supplémentaires classifiées")
        
        return {
            'success': True,
            'videos_classified': videos_classified,
            'message': f'{videos_classified} vidéos classifiées directement'
        }
        
    except Exception as e:
        print(f"[DIRECT-CLASSIFY] ❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e),
            'videos_classified': 0
        }
    finally:
        conn.close()

def run_global_ai_classification() -> Dict:
    """
    Lance la classification IA globale sur tous les concurrents
    Classifie les playlists puis applique aux vidéos, puis classifie directement les vidéos restantes
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer tous les concurrents
        cursor.execute('SELECT id, name FROM concurrent ORDER BY name')
        competitors = cursor.fetchall()
        
        if not competitors:
            return {
                'success': True,
                'message': 'Aucun concurrent trouvé',
                'competitors_count': 0,
                'playlists_classified': 0,
                'videos_classified': 0
            }
        
        total_playlists_classified = 0
        total_videos_classified = 0
        competitors_with_playlists = 0
        
        for competitor_row in competitors:
            competitor_id = competitor_row[0]
            competitor_name = competitor_row[1]
            
            print(f"[GLOBAL-AI] 🎯 Traitement de {competitor_name}...")
            
            # 1. Classifier les playlists non catégorisées
            playlist_result = auto_classify_uncategorized_playlists(competitor_id)
            if playlist_result.get('classified_count', 0) > 0:
                total_playlists_classified += playlist_result['classified_count']
                competitors_with_playlists += 1
                print(f"[GLOBAL-AI] ✨ {competitor_name}: {playlist_result['classified_count']} playlists classifiées")
            
            # 2. Appliquer les catégories des playlists aux vidéos
            video_result = apply_playlist_categories_to_videos(competitor_id)
            if video_result.get('videos_updated', 0) > 0:
                total_videos_classified += video_result['videos_updated']
                print(f"[GLOBAL-AI] 📹 {competitor_name}: {video_result['videos_updated']} vidéos classifiées via playlists")
            
            # 3. Classifier directement les vidéos restantes non catégorisées
            direct_result = classify_videos_directly_with_keywords(competitor_id)
            if direct_result.get('videos_classified', 0) > 0:
                total_videos_classified += direct_result['videos_classified']
                print(f"[GLOBAL-AI] 🎬 {competitor_name}: {direct_result['videos_classified']} vidéos classifiées directement")
        
        conn.commit()
        
        return {
            'success': True,
            'competitors_count': len(competitors),
            'competitors_with_playlists': competitors_with_playlists,
            'playlists_classified': total_playlists_classified,
            'videos_classified': total_videos_classified,
            'message': f'Classification globale terminée: {len(competitors)} concurrents traités'
        }
        
    except Exception as e:
        print(f"[GLOBAL-AI] ❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e),
            'competitors_count': 0,
            'playlists_classified': 0,
            'videos_classified': 0
        }
    finally:
        conn.close() 

def generate_country_insights() -> Dict:
    """
    Génère des insights et guidelines par pays basés sur l'analyse des données réelles
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer tous les concurrents avec leurs vidéos par pays
        cursor.execute('''
            SELECT 
                c.country,
                c.name as competitor_name,
                v.title,
                v.duration_seconds,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.published_at,
                v.category,
                strftime('%H', v.published_at) as hour_published,
                strftime('%w', v.published_at) as day_of_week
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE v.view_count IS NOT NULL 
            AND v.view_count > 0
            AND c.country IS NOT NULL 
            AND c.country != ''
        ''')
        
        results = cursor.fetchall()
        
        # Organiser les données par pays
        countries_data = {}
        
        for row in results:
            country = row[0]
            if country not in countries_data:
                countries_data[country] = {
                    'videos': [],
                    'competitors': set()
                }
            
            countries_data[country]['competitors'].add(row[1])
            countries_data[country]['videos'].append({
                'title': row[2],
                'duration_seconds': row[3],
                'view_count': row[4] or 0,
                'like_count': row[5] or 0,
                'comment_count': row[6] or 0,
                'published_at': row[7],
                'category': row[8],
                'hour_published': int(row[9]) if row[9] else None,
                'day_of_week': int(row[10]) if row[10] else None
            })
        
        # Générer les insights pour chaque pays
        insights = {}
        
        for country, data in countries_data.items():
            videos = data['videos']
            if len(videos) < 20:  # Pas assez de données
                continue
                
            # Calculer les statistiques
            insights[country] = _analyze_country_performance(country, videos, len(data['competitors']))
        
        return {
            'insights': insights,
            'generated_at': datetime.now().isoformat(),
            'total_countries': len(insights),
            'total_videos_analyzed': sum(len(data['videos']) for data in countries_data.values())
        }
        
    finally:
        conn.close()

def _analyze_country_performance(country: str, videos: List[Dict], competitor_count: int) -> Dict:
    """
    Analyse les performances d'un pays spécifique et génère des insights
    """
    if not videos:
        return {}
    
    # Trier par performance (vues)
    videos_sorted = sorted(videos, key=lambda x: x['view_count'], reverse=True)
    
    # Top 20% des vidéos les plus performantes
    top_20_percent = videos_sorted[:max(1, len(videos_sorted) // 5)]
    
    # Analyse de la durée optimale
    duration_insights = _analyze_optimal_duration(top_20_percent, videos)
    
    # Analyse des heures de publication optimales
    timing_insights = _analyze_optimal_timing(top_20_percent)
    
    # Analyse des catégories performantes
    category_insights = _analyze_category_performance(top_20_percent, videos)
    
    # Analyse de l'engagement
    engagement_insights = _analyze_engagement_patterns(top_20_percent)
    
    # 🆕 NOUVEAUX INSIGHTS ACTIONABLES
    # Analyse des hooks et patterns qui créent l'engagement
    hook_insights = _analyze_engagement_hooks(top_20_percent, videos)
    
    # Analyse du temps de décrochage (corrélation durée vs engagement)
    dropoff_insights = _analyze_dropoff_patterns(top_20_percent, videos)
    
    # Analyse des mots-clés qui performent
    keyword_insights = _analyze_performance_keywords(top_20_percent)
    
    # Calculer les scores globaux
    avg_views = sum(v['view_count'] for v in videos) / len(videos)
    avg_engagement = sum(v['like_count'] / max(v['view_count'], 1) for v in videos) / len(videos)
    
    return {
        'country': country,
        'competitor_count': competitor_count,
        'total_videos': len(videos),
        'avg_views': int(avg_views),
        'avg_engagement_rate': round(avg_engagement * 100, 2),
        'duration': duration_insights,
        'timing': timing_insights,
        'categories': category_insights,
        'engagement': engagement_insights,
        'hooks': hook_insights,  # 🆕 Ce qui accroche
        'dropoff': dropoff_insights,  # 🆕 Temps de décrochage
        'keywords': keyword_insights,  # 🆕 Mots-clés performants
        'performance_score': _calculate_country_performance_score(videos),
        'recommendations': _generate_country_recommendations(country, videos, top_20_percent)
    }

def _analyze_optimal_duration(top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
    """Analyse la durée optimale des vidéos"""
    # Filtrer les vidéos avec durée
    top_with_duration = [v for v in top_videos if v.get('duration_seconds')]
    all_with_duration = [v for v in all_videos if v.get('duration_seconds')]
    
    if not top_with_duration:
        return {'status': 'insufficient_data'}
    
    # Durée moyenne des top vidéos vs toutes les vidéos
    top_avg_duration = sum(v['duration_seconds'] for v in top_with_duration) / len(top_with_duration)
    all_avg_duration = sum(v['duration_seconds'] for v in all_with_duration) / len(all_with_duration)
    
    # Convertir en minutes
    top_avg_minutes = int(top_avg_duration / 60)
    all_avg_minutes = int(all_avg_duration / 60)
    
    # Trouver la plage optimale (durées des top 20%)
    durations = sorted([v['duration_seconds'] for v in top_with_duration])
    optimal_min = int(durations[len(durations)//4] / 60)  # 25e percentile
    optimal_max = int(durations[3*len(durations)//4] / 60)  # 75e percentile
    
    return {
        'optimal_range_minutes': [optimal_min, optimal_max],
        'optimal_avg_minutes': top_avg_minutes,
        'global_avg_minutes': all_avg_minutes,
        'performance_diff': f"+{((top_avg_duration/all_avg_duration-1)*100):.0f}%" if all_avg_duration > 0 else "N/A",
        'recommendation': f"Privilégier des vidéos de {optimal_min}-{optimal_max} minutes"
    }

def _analyze_optimal_timing(top_videos: List[Dict]) -> Dict:
    """Analyse les heures et jours optimaux de publication"""
    videos_with_timing = [v for v in top_videos if v.get('hour_published') is not None]
    
    if not videos_with_timing:
        return {'status': 'insufficient_data'}
    
    # Analyse des heures
    hour_counts = {}
    for video in videos_with_timing:
        hour = video['hour_published']
        if hour not in hour_counts:
            hour_counts[hour] = {'count': 0, 'total_views': 0}
        hour_counts[hour]['count'] += 1
        hour_counts[hour]['total_views'] += video['view_count']
    
    # Meilleure heure (par vues moyennes)
    best_hours = []
    for hour, data in hour_counts.items():
        if data['count'] >= 2:  # Au moins 2 vidéos
            avg_views = data['total_views'] / data['count']
            best_hours.append((hour, avg_views, data['count']))
    
    best_hours.sort(key=lambda x: x[1], reverse=True)
    
    # Analyse des jours de la semaine
    day_counts = {}
    for video in videos_with_timing:
        day = video.get('day_of_week')
        if day is not None:
            if day not in day_counts:
                day_counts[day] = {'count': 0, 'total_views': 0}
            day_counts[day]['count'] += 1
            day_counts[day]['total_views'] += video['view_count']
    
    # Convertir jour de semaine en nom
    day_names = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    best_days = []
    for day, data in day_counts.items():
        if data['count'] >= 2:
            avg_views = data['total_views'] / data['count']
            day_name = day_names[day] if 0 <= day <= 6 else f"Jour {day}"
            best_days.append((day_name, avg_views, data['count']))
    
    best_days.sort(key=lambda x: x[1], reverse=True)
    
    return {
        'best_hours': best_hours[:3],  # Top 3 heures
        'best_days': best_days[:3],    # Top 3 jours
        'recommendation_hour': f"{best_hours[0][0]}h" if best_hours else "Données insuffisantes",
        'recommendation_day': best_days[0][0] if best_days else "Données insuffisantes"
    }

def _analyze_category_performance(top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
    """Analyse des performances par catégorie"""
    # Compter les catégories dans le top
    top_categories = {}
    for video in top_videos:
        category = video.get('category', 'non_classé')
        top_categories[category] = top_categories.get(category, 0) + 1
    
    # Compter toutes les catégories
    all_categories = {}
    for video in all_videos:
        category = video.get('category', 'non_classé')
        all_categories[category] = all_categories.get(category, 0) + 1
    
    # Calculer les ratios de performance
    category_performance = {}
    for category in all_categories:
        top_count = top_categories.get(category, 0)
        all_count = all_categories[category]
        
        # Ratio de présence dans le top vs présence globale
        top_ratio = (top_count / len(top_videos)) if top_videos else 0
        all_ratio = (all_count / len(all_videos)) if all_videos else 0
        performance_ratio = (top_ratio / all_ratio) if all_ratio > 0 else 0
        
        category_performance[category] = {
            'top_count': top_count,
            'total_count': all_count,
            'performance_ratio': round(performance_ratio, 2),
            'success_rate': round((top_count / all_count) * 100, 1) if all_count > 0 else 0
        }
    
    # Trier par ratio de performance
    best_categories = sorted(
        category_performance.items(), 
        key=lambda x: x[1]['performance_ratio'], 
        reverse=True
    )
    
    return {
        'best_performing': best_categories[:3] if best_categories else [],
        'category_breakdown': category_performance
    }

def _analyze_engagement_patterns(top_videos: List[Dict]) -> Dict:
    """Analyse les patterns d'engagement"""
    videos_with_engagement = [v for v in top_videos if v.get('like_count', 0) > 0 and v.get('view_count', 0) > 0]
    
    if not videos_with_engagement:
        return {'status': 'insufficient_data'}
    
    # Calculer les ratios d'engagement
    engagement_rates = []
    like_rates = []
    comment_rates = []
    
    for video in videos_with_engagement:
        views = video['view_count']
        likes = video.get('like_count', 0)
        comments = video.get('comment_count', 0)
        
        like_rate = (likes / views) * 100
        comment_rate = (comments / views) * 100
        
        like_rates.append(like_rate)
        comment_rates.append(comment_rate)
        engagement_rates.append(like_rate + comment_rate)
    
    return {
        'avg_like_rate': round(sum(like_rates) / len(like_rates), 2),
        'avg_comment_rate': round(sum(comment_rates) / len(comment_rates), 2),
        'avg_total_engagement': round(sum(engagement_rates) / len(engagement_rates), 2),
        'top_engagement_threshold': round(max(engagement_rates), 2) if engagement_rates else 0
    }

def _calculate_country_performance_score(videos: List[Dict]) -> float:
    """Calcule un score de performance global pour un pays"""
    if not videos:
        return 0.0
    
    # Métriques de base
    avg_views = sum(v['view_count'] for v in videos) / len(videos)
    
    # Normaliser sur une échelle 0-10
    # 100k vues = score 5, 1M vues = score 10
    view_score = min(10, (avg_views / 100000) * 5)
    
    # Ajouter le facteur d'engagement
    videos_with_engagement = [v for v in videos if v.get('like_count', 0) > 0]
    if videos_with_engagement:
        avg_engagement = sum(v['like_count'] / max(v['view_count'], 1) for v in videos_with_engagement) / len(videos_with_engagement)
        engagement_score = min(3, avg_engagement * 1000)  # Max 3 points bonus
    else:
        engagement_score = 0
    
    return round(view_score + engagement_score, 1)

def _analyze_engagement_hooks(top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
    """Analyse ce qui crée l'engagement - patterns de titres, mots-clés, formats"""
    import re
    from collections import Counter
    
    # Analyser les titres des vidéos les plus engageantes
    top_titles = [v.get('title', '').lower() for v in top_videos if v.get('title')]
    all_titles = [v.get('title', '').lower() for v in all_videos if v.get('title')]
    
    if not top_titles:
        return {'status': 'insufficient_data'}
    
    # Mots-clés qui apparaissent plus souvent dans les top vidéos
    def extract_keywords(titles):
        # Extraire les mots significatifs (ignorer les mots vides)
        stop_words = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou', 'à', 'au', 'aux', 'pour', 'avec', 'dans', 'sur', 'par', 'ce', 'cette', 'ces', 'comment', 'que', 'qui', 'quoi', 'où', 'quand', 'the', 'a', 'an', 'and', 'or', 'to', 'at', 'in', 'on', 'by', 'for', 'with', 'how', 'what', 'when', 'where', 'why'}
        keywords = []
        for title in titles:
            words = re.findall(r'\b\w+\b', title)
            keywords.extend([w for w in words if len(w) > 3 and w not in stop_words])
        return keywords
    
    top_keywords = Counter(extract_keywords(top_titles))
    all_keywords = Counter(extract_keywords(all_titles))
    
    # Mots-clés surreprésentés dans les top vidéos
    engagement_keywords = {}
    for keyword, top_count in top_keywords.most_common(20):
        if keyword in all_keywords:
            all_count = all_keywords[keyword]
            # Ratio de surreprésentation
            overrepresentation = (top_count / len(top_titles)) / (all_count / len(all_titles))
            if overrepresentation > 1.2:  # Au moins 20% de surreprésentation
                engagement_keywords[keyword] = {
                    'count': top_count,
                    'ratio': round(overrepresentation, 2)
                }
    
    # Patterns de titres qui performent
    title_patterns = []
    
    # Titres avec questions
    question_titles = [t for t in top_titles if any(q in t for q in ['?', 'comment', 'pourquoi', 'how', 'why', 'what'])]
    if question_titles:
        title_patterns.append(f"Questions: {len(question_titles)}/{len(top_titles)} des top vidéos")
    
    # Titres avec chiffres
    number_titles = [t for t in top_titles if re.search(r'\d+', t)]
    if number_titles:
        title_patterns.append(f"Chiffres: {len(number_titles)}/{len(top_titles)} contiennent des chiffres")
    
    # Titres avec émotions fortes
    emotion_words = ['incroyable', 'fou', 'choc', 'révélé', 'secret', 'amazing', 'incredible', 'shocking', 'revealed', 'secret']
    emotion_titles = [t for t in top_titles if any(word in t for word in emotion_words)]
    if emotion_titles:
        title_patterns.append(f"Émotions: {len(emotion_titles)}/{len(top_titles)} avec mots émotionnels")
    
    return {
        'engagement_keywords': dict(list(engagement_keywords.items())[:10]),  # Top 10
        'title_patterns': title_patterns,
        'total_analyzed': len(top_videos)
    }

def _analyze_dropoff_patterns(top_videos: List[Dict], all_videos: List[Dict]) -> Dict:
    """Analyse les temps de décrochage - corrélation durée vs engagement"""
    
    # Analyser les vidéos avec données complètes
    complete_videos = [v for v in all_videos if v.get('duration_seconds') and v.get('view_count') and v.get('like_count')]
    
    if len(complete_videos) < 10:
        return {'status': 'insufficient_data'}
    
    # Grouper par tranches de durée
    duration_groups = {
        'courte': [],    # 0-3 minutes
        'moyenne': [],   # 3-10 minutes
        'longue': []     # 10+ minutes
    }
    
    for video in complete_videos:
        duration_min = video['duration_seconds'] / 60
        engagement_rate = video['like_count'] / max(video['view_count'], 1)
        
        if duration_min <= 3:
            duration_groups['courte'].append(engagement_rate)
        elif duration_min <= 10:
            duration_groups['moyenne'].append(engagement_rate)
        else:
            duration_groups['longue'].append(engagement_rate)
    
    # Calculer l'engagement moyen par groupe
    group_stats = {}
    for group_name, rates in duration_groups.items():
        if rates:
            avg_engagement = sum(rates) / len(rates)
            group_stats[group_name] = {
                'avg_engagement': round(avg_engagement * 100, 2),
                'video_count': len(rates)
            }
    
    # Déterminer le point de décrochage optimal
    best_group = max(group_stats.items(), key=lambda x: x[1]['avg_engagement']) if group_stats else None
    
    # Analyse des vidéos longues vs courtes dans le top
    top_short = [v for v in top_videos if v.get('duration_seconds', 0) <= 180]  # 3 minutes
    top_long = [v for v in top_videos if v.get('duration_seconds', 0) > 600]   # 10 minutes
    
    insights = {
        'duration_groups': group_stats,
        'optimal_length': best_group[0] if best_group else 'moyenne',
        'top_short_count': len(top_short),
        'top_long_count': len(top_long),
        'dropoff_recommendation': f"Les vidéos {best_group[0]}s performent mieux ({best_group[1]['avg_engagement']}% d'engagement)" if best_group else "Données insuffisantes"
    }
    
    return insights

def _analyze_performance_keywords(top_videos: List[Dict]) -> Dict:
    """Analyse les mots-clés qui performent le mieux"""
    import re
    from collections import Counter
    
    # Extraire tous les mots des titres des top vidéos
    all_words = []
    for video in top_videos:
        title = video.get('title', '').lower()
        if title:
            # Extraire les mots significatifs
            words = re.findall(r'\b\w+\b', title)
            all_words.extend([w for w in words if len(w) > 3])
    
    if not all_words:
        return {'status': 'insufficient_data'}
    
    # Compter les occurrences
    word_counts = Counter(all_words)
    
    # Associer chaque mot à la performance moyenne des vidéos qui le contiennent
    word_performance = {}
    for word, count in word_counts.most_common(30):
        if count >= 2:  # Au moins 2 occurrences
            videos_with_word = [v for v in top_videos if word in v.get('title', '').lower()]
            if videos_with_word:
                avg_views = sum(v.get('view_count', 0) for v in videos_with_word) / len(videos_with_word)
                avg_engagement = sum(v.get('like_count', 0) / max(v.get('view_count', 1), 1) for v in videos_with_word) / len(videos_with_word)
                
                word_performance[word] = {
                    'count': count,
                    'avg_views': int(avg_views),
                    'avg_engagement': round(avg_engagement * 100, 2),
                    'videos_count': len(videos_with_word)
                }
    
    # Trier par engagement
    top_keywords = sorted(word_performance.items(), key=lambda x: x[1]['avg_engagement'], reverse=True)
    
    return {
        'top_keywords': dict(top_keywords[:10]),  # Top 10 mots-clés
        'total_analyzed': len(top_videos)
    }

def _generate_country_recommendations(country: str, all_videos: List[Dict], top_videos: List[Dict]) -> List[str]:
    """Génère des recommandations spécifiques pour un pays"""
    recommendations = []
    
    # Recommandation de durée
    if top_videos:
        durations = [v.get('duration_seconds', 0) for v in top_videos if v.get('duration_seconds')]
        if durations:
            avg_duration = sum(durations) / len(durations)
            recommendations.append(f"🎯 Durée optimale: {int(avg_duration/60)} minutes en moyenne")
    
    # Recommandation de timing
    hours = [v.get('hour_published') for v in top_videos if v.get('hour_published') is not None]
    if hours:
        best_hour = max(set(hours), key=hours.count)
        recommendations.append(f"⏰ Heure optimale: {best_hour}h pour maximiser l'engagement")
    
    # Recommandation de catégorie
    categories = [v.get('category') for v in top_videos if v.get('category')]
    if categories:
        best_category = max(set(categories), key=categories.count)
        category_names = {'hero': 'HERO', 'hub': 'HUB', 'help': 'HELP'}
        recommendations.append(f"📈 Catégorie recommandée: {category_names.get(best_category, best_category)}")
    
    # 🆕 Recommandations basées sur les hooks d'engagement
    import re
    top_titles = [v.get('title', '').lower() for v in top_videos if v.get('title')]
    if top_titles:
        # Analyser les patterns de succès
        question_count = sum(1 for t in top_titles if any(q in t for q in ['?', 'comment', 'pourquoi', 'how', 'why']))
        number_count = sum(1 for t in top_titles if re.search(r'\d+', t))
        
        if question_count > len(top_titles) * 0.3:  # Plus de 30% de questions
            recommendations.append(f"❓ Utilisez des questions dans vos titres ({question_count}/{len(top_titles)} vidéos top)")
        
        if number_count > len(top_titles) * 0.4:  # Plus de 40% avec des chiffres
            recommendations.append(f"🔢 Intégrez des chiffres dans vos titres ({number_count}/{len(top_titles)} vidéos top)")
    
    # 🆕 Recommandation sur le temps de décrochage
    complete_videos = [v for v in top_videos if v.get('duration_seconds') and v.get('view_count') and v.get('like_count')]
    if len(complete_videos) >= 5:
        short_videos = [v for v in complete_videos if v['duration_seconds'] <= 180]  # 3 minutes
        long_videos = [v for v in complete_videos if v['duration_seconds'] > 600]   # 10 minutes
        
        short_engagement = sum(v['like_count'] / max(v['view_count'], 1) for v in short_videos) / len(short_videos) if short_videos else 0
        long_engagement = sum(v['like_count'] / max(v['view_count'], 1) for v in long_videos) / len(long_videos) if long_videos else 0
        
        if short_engagement > long_engagement * 1.2:  # 20% de plus d'engagement
            recommendations.append(f"⚡ Privilégiez les vidéos courtes (<3min) pour l'engagement")
        elif long_engagement > short_engagement * 1.2:
            recommendations.append(f"🎬 Les vidéos longues (>10min) génèrent plus d'engagement")
    
    # Recommandation d'engagement standard
    engagement_rates = [
        v['like_count'] / max(v['view_count'], 1) 
        for v in top_videos 
        if v.get('like_count', 0) > 0 and v.get('view_count', 0) > 0
    ]
    if engagement_rates:
        target_engagement = sum(engagement_rates) / len(engagement_rates)
        recommendations.append(f"💬 Viser {target_engagement*100:.1f}% d'engagement (likes/vues)")
    
    return recommendations 