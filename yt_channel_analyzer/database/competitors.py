"""
Module de gestion des concurrents.

Ce module contient toutes les fonctions liées à la gestion des concurrents :
- CRUD des concurrents
- Gestion des playlists
- Données d'abonnés
- Nettoyage et maintenance
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .base import get_db_connection, DatabaseUtils


class CompetitorManager:
    """Gestionnaire des concurrents."""
    
    def __init__(self):
        self.db_utils = DatabaseUtils()
    
    def get_all_competitors(self) -> List[Dict]:
        """Récupérer tous les concurrents"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, name, channel_id, channel_url, thumbnail_url, banner_url,
                description, subscriber_count, view_count, video_count,
                country, language, created_at, last_updated
            FROM concurrent 
            ORDER BY created_at DESC
        ''')
        
        competitors = []
        for row in cursor.fetchall():
            competitors.append({
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
            })
        
        conn.close()
        return competitors
    
    def get_competitor_by_id(self, competitor_id: int) -> Dict:
        """Récupérer un concurrent par son ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, name, channel_id, channel_url, thumbnail_url, banner_url,
                description, subscriber_count, view_count, video_count,
                country, language, created_at, last_updated
            FROM concurrent 
            WHERE id = ?
        ''', (competitor_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
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
        return {}
    
    def get_competitor_by_url(self, channel_url: str) -> Optional[Dict]:
        """Récupérer un concurrent par son URL"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM concurrent WHERE channel_url = ?', (channel_url,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def add_competitor(self, competitor_data: Dict) -> int:
        """Ajouter un nouveau concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Générer un channel_id si non fourni
        channel_id = competitor_data.get('channel_id')
        if not channel_id and competitor_data.get('channel_url'):
            channel_id = self.db_utils.extract_channel_id_from_url(competitor_data['channel_url'])
        
        cursor.execute('''
            INSERT INTO concurrent (
                name, channel_id, channel_url, thumbnail_url, banner_url,
                description, subscriber_count, view_count, video_count,
                country, language, created_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            competitor_data.get('name', ''),
            channel_id,
            competitor_data.get('channel_url', ''),
            competitor_data.get('thumbnail_url', ''),
            competitor_data.get('banner_url', ''),
            competitor_data.get('description', ''),
            competitor_data.get('subscriber_count'),
            competitor_data.get('view_count'),
            competitor_data.get('video_count'),
            competitor_data.get('country', ''),
            competitor_data.get('language', ''),
            datetime.now(),
            datetime.now()
        ))
        
        competitor_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return competitor_id
    
    def update_competitor(self, competitor_id: int, updates: Dict):
        """Mettre à jour un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construire la requête dynamiquement
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key != 'id':  # Ne pas modifier l'ID
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if set_clauses:
            set_clauses.append("last_updated = ?")
            values.append(datetime.now())
            values.append(competitor_id)
            
            query = f"UPDATE concurrent SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
        
        conn.commit()
        conn.close()
    
    def delete_competitor(self, competitor_id: int):
        """Supprimer un concurrent et ses données associées"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Supprimer les vidéos associées
            cursor.execute('DELETE FROM video WHERE concurrent_id = ?', (competitor_id,))
            
            # Supprimer les playlists associées
            cursor.execute('DELETE FROM playlist WHERE concurrent_id = ?', (competitor_id,))
            
            # Supprimer les données d'abonnés
            cursor.execute('DELETE FROM subscriber_data WHERE concurrent_id = ?', (competitor_id,))
            
            # Supprimer le concurrent
            cursor.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
            
            conn.commit()
            print(f"✅ Concurrent {competitor_id} supprimé avec succès")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la suppression du concurrent {competitor_id}: {e}")
            raise
        finally:
            conn.close()
    
    def get_all_competitors_urls(self):
        """Récupérer toutes les URLs des concurrents"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT channel_url FROM concurrent')
        urls = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return urls
    
    def update_competitor_country(self, competitor_id, country):
        """Mettre à jour le pays d'un concurrent"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE concurrent 
                SET country = ?, last_updated = ?
                WHERE id = ?
            ''', (country, datetime.now(), competitor_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DATABASE] Erreur lors de la mise à jour du pays: {e}")
            return False
    
    def get_competitors_by_country(self):
        """Récupérer les concurrents groupés par pays"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                country,
                COUNT(*) as count,
                GROUP_CONCAT(name, ', ') as names
            FROM concurrent 
            WHERE country IS NOT NULL AND country != ''
            GROUP BY country
            ORDER BY count DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'country': row[0],
                'count': row[1],
                'names': row[2]
            })
        
        conn.close()
        return results
    
    def clean_duplicate_competitors(self) -> Dict:
        """Nettoyer les concurrents en double"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Identifier les doublons par URL
        cursor.execute('''
            SELECT channel_url, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM concurrent
            GROUP BY channel_url
            HAVING count > 1
        ''')
        
        duplicates = cursor.fetchall()
        removed_count = 0
        
        for duplicate in duplicates:
            channel_url, count, ids = duplicate
            id_list = [int(x) for x in ids.split(',')]
            
            # Garder le premier ID, supprimer les autres
            to_keep = min(id_list)
            to_remove = [x for x in id_list if x != to_keep]
            
            for competitor_id in to_remove:
                try:
                    # Déplacer les vidéos vers le concurrent à conserver
                    cursor.execute('''
                        UPDATE video 
                        SET concurrent_id = ? 
                        WHERE concurrent_id = ?
                    ''', (to_keep, competitor_id))
                    
                    # Supprimer le doublon
                    cursor.execute('DELETE FROM concurrent WHERE id = ?', (competitor_id,))
                    removed_count += 1
                    
                except Exception as e:
                    print(f"❌ Erreur lors de la suppression du doublon {competitor_id}: {e}")
        
        conn.commit()
        conn.close()
        
        return {
            'duplicates_found': len(duplicates),
            'duplicates_removed': removed_count,
            'message': f"Suppression de {removed_count} doublons terminée"
        }
    
    def get_all_competitors_with_videos(self) -> List[Dict]:
        """Récupérer tous les concurrents avec leurs statistiques de vidéos"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                c.id,
                c.name,
                c.channel_url,
                c.thumbnail_url,
                c.subscriber_count,
                c.country,
                c.language,
                COUNT(v.id) as video_count,
                SUM(v.view_count) as total_views,
                AVG(v.view_count) as avg_views,
                MAX(v.published_at) as last_video_date
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id
            ORDER BY video_count DESC
        ''')
        
        competitors = []
        for row in cursor.fetchall():
            competitors.append({
                'id': row[0],
                'name': row[1],
                'channel_url': row[2],
                'thumbnail_url': row[3],
                'subscriber_count': row[4],
                'country': row[5],
                'language': row[6],
                'video_count': row[7] or 0,
                'total_views': row[8] or 0,
                'avg_views': int(row[9]) if row[9] else 0,
                'last_video_date': row[10]
            })
        
        conn.close()
        return competitors
    
    def competitors_to_legacy_format(self) -> Dict:
        """Convertir les concurrents au format legacy pour compatibilité"""
        competitors = self.get_all_competitors()
        legacy_format = {}
        
        for competitor in competitors:
            # Utiliser l'URL comme clé pour le format legacy
            key = competitor['channel_url'] or str(competitor['id'])
            legacy_format[key] = {
                'id': competitor['id'],
                'name': competitor['name'],
                'channel_url': competitor['channel_url'],
                'thumbnail_url': competitor['thumbnail_url'],
                'subscriber_count': competitor['subscriber_count'],
                'view_count': competitor['view_count'],
                'video_count': competitor['video_count'],
                'country': competitor['country'],
                'language': competitor['language']
            }
        
        return legacy_format


class CompetitorPlaylistManager:
    """Gestionnaire des playlists de concurrents."""
    
    def save_competitor_playlists(self, competitor_id: int, playlists: List[Dict]):
        """Sauvegarder les playlists d'un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for playlist in playlists:
            # Vérifier si la playlist existe déjà
            cursor.execute('''
                SELECT id FROM playlist 
                WHERE concurrent_id = ? AND playlist_id = ?
            ''', (competitor_id, playlist.get('id', '')))
            
            existing = cursor.fetchone()
            
            if existing:
                # Mettre à jour la playlist existante
                cursor.execute('''
                    UPDATE playlist SET
                        name = ?, description = ?, thumbnail_url = ?,
                        video_count = ?, last_updated = ?
                    WHERE id = ?
                ''', (
                    playlist.get('name', playlist.get('title', '')),
                    playlist.get('description', ''),
                    playlist.get('thumbnail_url', ''),
                    playlist.get('video_count', 0),
                    datetime.now(),
                    existing[0]
                ))
            else:
                # Créer une nouvelle playlist
                cursor.execute('''
                    INSERT INTO playlist (
                        concurrent_id, playlist_id, name, description, 
                        thumbnail_url, video_count, created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    competitor_id,
                    playlist.get('playlist_id', playlist.get('id', '')),
                    playlist.get('name', playlist.get('title', '')),
                    playlist.get('description', ''),
                    playlist.get('thumbnail_url', ''),
                    playlist.get('video_count', 0),
                    datetime.now(),
                    datetime.now()
                ))
        
        conn.commit()
        conn.close()
    
    def get_competitor_playlists(self, competitor_id: int) -> List[Dict]:
        """Récupérer les playlists d'un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, playlist_id, name, description, thumbnail_url,
                video_count, category, classification_source, human_verified,
                created_at, last_updated
            FROM playlist 
            WHERE concurrent_id = ?
            ORDER BY created_at DESC
        ''', (competitor_id,))
        
        playlists = []
        for row in cursor.fetchall():
            playlists.append({
                'id': row[0],
                'playlist_id': row[1],
                'title': row[2],  # Garder 'title' pour compatibilité avec les templates
                'name': row[2],   # Ajouter 'name' aussi
                'description': row[3],
                'thumbnail_url': row[4],
                'video_count': row[5],
                'category': row[6],
                'classification_source': row[7],
                'human_verified': row[8],
                'created_at': row[9],
                'last_updated': row[10]
            })
        
        conn.close()
        return playlists


class CompetitorSubscriberManager:
    """Gestionnaire des données d'abonnés des concurrents."""
    
    def save_subscriber_data(self, competitor_id: int, subscriber_data: List[Dict]) -> bool:
        """Sauvegarder les données d'abonnés d'un concurrent"""
        if not subscriber_data:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for data in subscriber_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO subscriber_data (
                        concurrent_id, date, subscriber_count, created_at
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    competitor_id,
                    data.get('date', datetime.now().date()),
                    data.get('subscriber_count', 0),
                    datetime.now()
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la sauvegarde des données d'abonnés: {e}")
            return False
        finally:
            conn.close()
    
    def get_competitor_subscriber_data(self, competitor_id: int) -> List[Dict]:
        """Récupérer les données d'abonnés d'un concurrent"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, subscriber_count, created_at
            FROM subscriber_data 
            WHERE concurrent_id = ?
            ORDER BY date DESC
        ''', (competitor_id,))
        
        data = []
        for row in cursor.fetchall():
            data.append({
                'date': row[0],
                'subscriber_count': row[1],
                'created_at': row[2]
            })
        
        conn.close()
        return data


# Instances globales des gestionnaires
competitor_manager = CompetitorManager()
playlist_manager = CompetitorPlaylistManager()
subscriber_manager = CompetitorSubscriberManager()

# Fonctions de compatibilité
get_all_competitors = competitor_manager.get_all_competitors
get_competitor_by_id = competitor_manager.get_competitor_by_id
get_competitor_by_url = competitor_manager.get_competitor_by_url
add_competitor = competitor_manager.add_competitor
update_competitor = competitor_manager.update_competitor
delete_competitor = competitor_manager.delete_competitor
get_all_competitors_urls = competitor_manager.get_all_competitors_urls
update_competitor_country = competitor_manager.update_competitor_country
get_competitors_by_country = competitor_manager.get_competitors_by_country
clean_duplicate_competitors = competitor_manager.clean_duplicate_competitors
get_all_competitors_with_videos = competitor_manager.get_all_competitors_with_videos
competitors_to_legacy_format = competitor_manager.competitors_to_legacy_format

save_competitor_playlists = playlist_manager.save_competitor_playlists
get_competitor_playlists = playlist_manager.get_competitor_playlists

save_subscriber_data = subscriber_manager.save_subscriber_data
get_competitor_subscriber_data = subscriber_manager.get_competitor_subscriber_data 

def get_all_competitors_with_videos() -> List[Dict]:
    """Fonction standalone pour récupérer tous les concurrents avec leurs statistiques précalculées"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer les concurrents avec leurs statistiques précalculées
        cursor.execute('''
            SELECT 
                c.id,
                c.name,
                c.channel_url,
                c.thumbnail_url,
                c.subscriber_count,
                c.country,
                c.language,
                COALESCE(c.sector, 'hospitality') as sector,
                COALESCE(c.tags, '') as tags,
                COALESCE(c.custom_region, '') as custom_region,
                COALESCE(c.notes, '') as notes,
                COALESCE(c.is_active, 1) as is_active,
                COALESCE(cs.total_videos, 0) as total_videos,
                COALESCE(cs.total_views, 0) as total_views,
                COALESCE(cs.avg_views, 0) as avg_views,
                COALESCE(cs.hero_count, 0) as hero_count,
                COALESCE(cs.hub_count, 0) as hub_count,
                COALESCE(cs.help_count, 0) as help_count,
                COALESCE(cs.hero_views, 0) as hero_views,
                COALESCE(cs.hub_views, 0) as hub_views,
                COALESCE(cs.help_views, 0) as help_views,
                COALESCE(cs.engagement_rate, 0) as engagement_rate,
                COALESCE(cfs.avg_videos_per_week, 0) as frequency_total,
                (SELECT MAX(published_at) FROM video WHERE concurrent_id = c.id) as last_video_date
            FROM concurrent c
            LEFT JOIN competitor_stats cs ON c.id = cs.competitor_id
            LEFT JOIN competitor_frequency_stats cfs ON c.id = cfs.competitor_id
            WHERE COALESCE(c.is_active, 1) = 1
            ORDER BY COALESCE(cs.total_videos, 0) DESC, c.name ASC
        ''')
        
        competitors = []
        for row in cursor.fetchall():
            competitor_id = row[0]
            name = row[1]
            channel_url = row[2]
            thumbnail_url = row[3]
            subscriber_count = row[4]
            country = row[5]
            language = row[6]
            sector = row[7]
            tags = row[8]
            custom_region = row[9]
            notes = row[10]
            is_active = row[11]
            total_videos = row[12]
            total_views = row[13]
            avg_views = row[14]
            hero_count = row[15]
            hub_count = row[16]
            help_count = row[17]
            hero_views = row[18]
            hub_views = row[19]
            help_views = row[20]
            engagement_rate = row[21]
            frequency_total = row[22]
            last_video_date = row[23]
            
            # Calculer les pourcentages
            hero_percentage = (hero_count / total_videos * 100) if total_videos > 0 else 0
            hub_percentage = (hub_count / total_videos * 100) if total_videos > 0 else 0
            help_percentage = (help_count / total_videos * 100) if total_videos > 0 else 0
            
            competitors.append({
                'id': competitor_id,
                'name': name,
                'channel_url': channel_url,
                'thumbnail_url': thumbnail_url,
                'subscriber_count': subscriber_count,
                'country': country,
                'language': language,
                'video_count': total_videos,
                'total_videos': total_videos,  # Compatibilité avec le template
                'total_views': total_views,
                'avg_views': avg_views,
                'last_video_date': last_video_date,
                'sector': sector,
                'tags': tags,
                'custom_region': custom_region,
                'notes': notes,
                'is_active': is_active,
                # Statistiques HERO/HUB/HELP (précalculées)
                'hero_count': hero_count,
                'hub_count': hub_count,
                'help_count': help_count,
                'hero_views': hero_views,
                'hub_views': hub_views,
                'help_views': help_views,
                'engagement_rate': engagement_rate,
                # Pourcentages
                'hero_percentage': hero_percentage,
                'hub_percentage': hub_percentage,
                'help_percentage': help_percentage,
                # Fréquence
                'frequency_total': frequency_total,
                'frequency_hero': frequency_total * 0.3,  # Approximation
                'frequency_hub': frequency_total * 0.6,   # Approximation
                'frequency_help': frequency_total * 0.1   # Approximation
            })
        
        return competitors
        
    except Exception as e:
        print(f"❌ Erreur dans get_all_competitors_with_videos: {e}")
        return []
    finally:
        conn.close() 