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
    """Récupérer tous les concurrents depuis la base de données"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM concurrent 
        ORDER BY name
    ''')
    
    competitors = []
    for row in cursor.fetchall():
        competitors.append(dict(row))
    
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
            
            competitor['videos'] = videos
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