"""
Module de gestion des vidéos.

Ce module contient toutes les fonctions liées à la gestion des vidéos :
- CRUD des vidéos
- Liaison avec les concurrents
- Classification des vidéos
- Analyse des performances
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re

from .base import get_db_connection, DatabaseUtils


class VideoManager:
    """Gestionnaire des vidéos."""
    
    def __init__(self):
        self.db_utils = DatabaseUtils()
    
    def get_competitor_videos(self, competitor_id: int) -> List[Dict]:
        """Récupérer toutes les vidéos d'un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, video_id, title, description, url, thumbnail_url,
                published_at, duration_seconds, duration_text, view_count,
                like_count, comment_count, category, tags, is_short,
                youtube_published_at, classification_source, is_human_validated
            FROM video 
            WHERE concurrent_id = ?
            ORDER BY published_at DESC
        ''', (competitor_id,))
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'id': row[0],
                'video_id': row[1],
                'title': row[2],
                'description': row[3],
                'url': row[4],
                'thumbnail_url': row[5],
                'published_at': row[6],
                'duration_seconds': row[7],
                'duration_text': row[8],
                'view_count': row[9],
                'like_count': row[10],
                'comment_count': row[11],
                'category': row[12],
                'tags': row[13],
                'is_short': row[14],
                'youtube_published_at': row[15],
                'classification_source': row[16],
                'is_human_validated': row[17]
            })
        
        conn.close()
        return videos
    
    def save_competitor_and_videos(self, channel_url: str, videos: List[Dict], channel_info: Dict = None) -> int:
        """Sauvegarder un concurrent et ses vidéos"""
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
                channel_id = self.db_utils.extract_channel_id_from_url(channel_url)
                
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
                video_id = self.db_utils.extract_video_id_from_url(video.get('url', ''))
                
                # Vérifier si la vidéo existe déjà
                cursor.execute('SELECT id FROM video WHERE video_id = ?', (video_id,))
                existing_video = cursor.fetchone()
                
                # Préparer les données de la vidéo
                title = video.get('title', '')[:200]  # Limiter à 200 caractères
                description = video.get('description', '')
                url = video.get('url', '')
                thumbnail_url = video.get('thumbnail', '')
                
                # Traiter la date de publication
                published_at = self.db_utils.parse_date(video.get('published_at') or video.get('publication_date'))
                
                # Traiter la durée
                duration_seconds = self.db_utils.parse_duration_to_seconds(video.get('duration', ''))
                duration_text = video.get('duration', '')
                
                # Traiter les métriques
                view_count = self.db_utils.parse_view_count(video.get('views') or video.get('view_count') or 0)
                like_count = video.get('likes') or video.get('like_count')
                comment_count = video.get('comments') or video.get('comment_count')
                
                # Déterminer si c'est un Short
                is_short = self._is_video_short(duration_seconds, title, description)
                
                if existing_video:
                    # Mettre à jour la vidéo existante
                    cursor.execute('''
                        UPDATE video SET
                            title = ?, description = ?, url = ?, thumbnail_url = ?,
                            published_at = ?, duration_seconds = ?, duration_text = ?,
                            view_count = ?, like_count = ?, comment_count = ?,
                            is_short = ?, last_updated = ?
                        WHERE id = ?
                    ''', (
                        title, description, url, thumbnail_url,
                        published_at, duration_seconds, duration_text,
                        view_count, like_count, comment_count,
                        is_short, datetime.now(), existing_video[0]
                    ))
                    videos_updated += 1
                else:
                    # Créer une nouvelle vidéo
                    cursor.execute('''
                        INSERT INTO video (
                            concurrent_id, video_id, title, description, url, thumbnail_url,
                            published_at, duration_seconds, duration_text, view_count,
                            like_count, comment_count, is_short, created_at, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        competitor_id, video_id, title, description, url, thumbnail_url,
                        published_at, duration_seconds, duration_text, view_count,
                        like_count, comment_count, is_short, datetime.now(), datetime.now()
                    ))
                    videos_added += 1
            
            conn.commit()
            print(f"[DB] Sauvegarde terminée: {videos_added} vidéos ajoutées, {videos_updated} mises à jour")
            
            return competitor_id
            
        except Exception as e:
            conn.rollback()
            print(f"[DB] Erreur lors de la sauvegarde: {e}")
            raise
        finally:
            conn.close()
    
    def _is_video_short(self, duration_seconds: Optional[int], title: str, description: str) -> bool:
        """Déterminer si une vidéo est un Short"""
        # Critères pour identifier un Short
        if duration_seconds and duration_seconds <= 60:
            return True
        
        # Mots-clés dans le titre ou la description
        short_keywords = ['#short', '#shorts', 'short', 'shorts']
        title_lower = title.lower() if title else ''
        description_lower = description.lower() if description else ''
        
        for keyword in short_keywords:
            if keyword in title_lower or keyword in description_lower:
                return True
        
        return False
    
    def link_playlist_videos(self, playlist_db_id: int, video_ids: List[str]):
        """Lier des vidéos à une playlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Supprimer les liens existants
            cursor.execute('DELETE FROM playlist_video WHERE playlist_id = ?', (playlist_db_id,))
            
            # Créer les nouveaux liens
            for video_id in video_ids:
                # Trouver l'ID de la vidéo dans la base
                cursor.execute('SELECT id FROM video WHERE video_id = ?', (video_id,))
                video_row = cursor.fetchone()
                
                if video_row:
                    cursor.execute('''
                        INSERT INTO playlist_video (playlist_id, video_id)
                        VALUES (?, ?)
                    ''', (playlist_db_id, video_row[0]))
            
            conn.commit()
            print(f"✅ {len(video_ids)} vidéos liées à la playlist {playlist_db_id}")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la liaison des vidéos: {e}")
        finally:
            conn.close()
    
    def refresh_competitor_data(self, channel_url: str, fresh_videos: List[Dict], channel_info: Dict = None) -> Dict:
        """Rafraîchir les données d'un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer le concurrent existant
            cursor.execute('SELECT id FROM concurrent WHERE channel_url = ?', (channel_url,))
            existing = cursor.fetchone()
            
            if not existing:
                # Créer un nouveau concurrent
                competitor_id = self.save_competitor_and_videos(channel_url, fresh_videos, channel_info)
                return {
                    'success': True,
                    'action': 'created',
                    'competitor_id': competitor_id,
                    'videos_count': len(fresh_videos)
                }
            
            competitor_id = existing[0]
            
            # Mettre à jour les informations du concurrent si disponibles
            if channel_info:
                cursor.execute('''
                    UPDATE concurrent SET
                        name = ?, thumbnail_url = ?, banner_url = ?, description = ?,
                        subscriber_count = ?, view_count = ?, video_count = ?,
                        country = ?, language = ?, last_updated = ?
                    WHERE id = ?
                ''', (
                    channel_info.get('title', ''),
                    channel_info.get('thumbnail', ''),
                    channel_info.get('banner', ''),
                    channel_info.get('description', ''),
                    channel_info.get('subscriber_count'),
                    channel_info.get('view_count'),
                    len(fresh_videos),
                    channel_info.get('country', ''),
                    channel_info.get('language', ''),
                    datetime.now(),
                    competitor_id
                ))
            
            # Traiter les vidéos
            videos_added = 0
            videos_updated = 0
            
            for video in fresh_videos:
                video_id = self.db_utils.extract_video_id_from_url(video.get('url', ''))
                
                # Vérifier si la vidéo existe déjà
                cursor.execute('SELECT id FROM video WHERE video_id = ? AND concurrent_id = ?', (video_id, competitor_id))
                existing_video = cursor.fetchone()
                
                if existing_video:
                    # Mettre à jour la vidéo existante
                    self._update_video(cursor, existing_video[0], video)
                    videos_updated += 1
                else:
                    # Créer une nouvelle vidéo
                    self._create_video(cursor, competitor_id, video)
                    videos_added += 1
            
            conn.commit()
            
            return {
                'success': True,
                'action': 'updated',
                'competitor_id': competitor_id,
                'videos_added': videos_added,
                'videos_updated': videos_updated,
                'total_videos': len(fresh_videos)
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _update_video(self, cursor, video_db_id: int, video: Dict):
        """Mettre à jour une vidéo existante"""
        title = video.get('title', '')[:200]
        description = video.get('description', '')
        url = video.get('url', '')
        thumbnail_url = video.get('thumbnail', '')
        published_at = self.db_utils.parse_date(video.get('published_at') or video.get('publication_date'))
        duration_seconds = self.db_utils.parse_duration_to_seconds(video.get('duration', ''))
        duration_text = video.get('duration', '')
        view_count = self.db_utils.parse_view_count(video.get('views') or video.get('view_count') or 0)
        like_count = video.get('likes') or video.get('like_count')
        comment_count = video.get('comments') or video.get('comment_count')
        is_short = self._is_video_short(duration_seconds, title, description)
        
        cursor.execute('''
            UPDATE video SET
                title = ?, description = ?, url = ?, thumbnail_url = ?,
                published_at = ?, duration_seconds = ?, duration_text = ?,
                view_count = ?, like_count = ?, comment_count = ?,
                is_short = ?, last_updated = ?
            WHERE id = ?
        ''', (
            title, description, url, thumbnail_url,
            published_at, duration_seconds, duration_text,
            view_count, like_count, comment_count,
            is_short, datetime.now(), video_db_id
        ))
    
    def _create_video(self, cursor, competitor_id: int, video: Dict):
        """Créer une nouvelle vidéo"""
        video_id = self.db_utils.extract_video_id_from_url(video.get('url', ''))
        title = video.get('title', '')[:200]
        description = video.get('description', '')
        url = video.get('url', '')
        thumbnail_url = video.get('thumbnail', '')
        published_at = self.db_utils.parse_date(video.get('published_at') or video.get('publication_date'))
        duration_seconds = self.db_utils.parse_duration_to_seconds(video.get('duration', ''))
        duration_text = video.get('duration', '')
        view_count = self.db_utils.parse_view_count(video.get('views') or video.get('view_count') or 0)
        like_count = video.get('likes') or video.get('like_count')
        comment_count = video.get('comments') or video.get('comment_count')
        is_short = self._is_video_short(duration_seconds, title, description)
        
        cursor.execute('''
            INSERT INTO video (
                concurrent_id, video_id, title, description, url, thumbnail_url,
                published_at, duration_seconds, duration_text, view_count,
                like_count, comment_count, is_short, created_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            competitor_id, video_id, title, description, url, thumbnail_url,
            published_at, duration_seconds, duration_text, view_count,
            like_count, comment_count, is_short, datetime.now(), datetime.now()
        ))


def calculate_publication_frequency(competitor_id: int) -> float:
    """Calcule la fréquence de publication en vidéos par semaine"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                julianday(MAX(published_at)) - julianday(MIN(published_at)) as days_span,
                COUNT(*) as video_count
            FROM video 
            WHERE concurrent_id = ? 
            AND published_at IS NOT NULL
        """, (competitor_id,))
        
        result = cursor.fetchone()
        
        if result and result[0] and result[0] > 0:
            days_span, video_count = result
            return (video_count / days_span) * 7  # Convertir en vidéos par semaine
        else:
            return 0.0
            
    finally:
        conn.close()


class VideoClassificationManager:
    """Gestionnaire de classification des vidéos."""
    
    def mark_human_classification(self, video_id: int = None, playlist_id: int = None, 
                                 category: str = None, user_notes: str = '') -> bool:
        """Marquer une classification comme validée par un humain"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now()
            
            if video_id:
                # Marquer la vidéo comme validée par un humain
                cursor.execute('''
                    UPDATE video SET 
                        category = ?, 
                        classification_source = 'human',
                        is_human_validated = 1,
                        last_updated = ?
                    WHERE id = ?
                ''', (category, timestamp, video_id))
                
                # Note: Historique retiré car la table human_classification_history n'existe pas
                # La classification est déjà trackée via classification_feedback
            
            elif playlist_id:
                # Marquer la playlist comme validée par un humain
                cursor.execute('''
                    UPDATE playlist SET 
                        category = ?, 
                        classification_source = 'human',
                        human_verified = 1,
                        classification_date = ?
                    WHERE id = ?
                ''', (category, timestamp, playlist_id))
                
                # Note: Historique retiré car la table human_classification_history n'existe pas
                # La classification est déjà trackée via classification_feedback
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la validation humaine: {e}")
            return False
        finally:
            conn.close()
    
    def check_human_protection_status(self, video_id: int = None, playlist_id: int = None) -> Dict:
        """Vérifier le statut de protection humaine d'un élément"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if video_id:
                cursor.execute('''
                    SELECT is_human_validated, classification_source, category, last_updated
                    FROM video 
                    WHERE id = ?
                ''', (video_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'is_protected': bool(row[0]),
                        'classification_source': row[1],
                        'category': row[2],
                        'last_updated': row[3],
                        'type': 'video'
                    }
            
            elif playlist_id:
                cursor.execute('''
                    SELECT is_human_validated, classification_source, category, last_updated
                    FROM playlist 
                    WHERE id = ?
                ''', (playlist_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'is_protected': bool(row[0]),
                        'classification_source': row[1],
                        'category': row[2],
                        'last_updated': row[3],
                        'type': 'playlist'
                    }
            
            return {
                'is_protected': False,
                'classification_source': 'auto',
                'category': None,
                'last_updated': None,
                'type': None
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la vérification du statut: {e}")
            return {
                'is_protected': False,
                'error': str(e)
            }
        finally:
            conn.close()


def auto_update_frequency_stats(competitor_id: int):
    """Recalculer automatiquement les statistiques de fréquence pour un concurrent"""
    try:
        import subprocess
        import os
        
        # Chemin vers le script de calcul de fréquence
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'create_frequency_stats.py')
        
        # Lancer le script en mode silencieux
        result = subprocess.run(['python', script_path], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(script_path))
        
        if result.returncode == 0:
            print(f"✅ Statistiques de fréquence mises à jour automatiquement")
        else:
            print(f"⚠️ Erreur lors du calcul automatique de fréquence: {result.stderr}")
    
    except Exception as e:
        print(f"⚠️ Erreur auto-update fréquence: {e}")

# Wrapper functions
video_manager = VideoManager()
classification_manager = VideoClassificationManager()

# Exposer les fonctions
get_competitor_videos = video_manager.get_competitor_videos
save_competitor_and_videos = video_manager.save_competitor_and_videos
refresh_competitor_data = video_manager.refresh_competitor_data
link_playlist_videos = video_manager.link_playlist_videos
mark_human_classification = classification_manager.mark_human_classification
check_human_protection_status = classification_manager.check_human_protection_status 