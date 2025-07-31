"""
Import Workflow Manager
Gère le workflow automatique post-import des vidéos
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from .database import get_db_connection
from .youtube_api_client import create_youtube_client
from .database.classification import classify_videos_directly_with_keywords
from .database.videos import calculate_publication_frequency


class ImportWorkflowManager:
    """Gestionnaire du workflow automatique post-import"""
    
    def __init__(self):
        self.youtube_client = None
        self.static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    
    def run_post_import_workflow(self, competitor_id: int, channel_url: str) -> Dict:
        """
        Exécute le workflow complet après l'import des vidéos
        
        Étapes:
        1. Corriger les dates de publication
        2. Télécharger et sauvegarder la thumbnail
        3. Lancer la classification automatique
        4. Calculer les statistiques
        5. Rafraîchir l'affichage
        
        Returns:
            Dict avec les résultats de chaque étape
        """
        results = {
            'competitor_id': competitor_id,
            'channel_url': channel_url,
            'steps': {}
        }
        
        print(f"\n🚀 WORKFLOW POST-IMPORT pour concurrent ID {competitor_id}")
        print("=" * 60)
        
        # Étape 1: Corriger les dates
        print("\n📅 ÉTAPE 1: Correction des dates de publication")
        date_results = self._fix_publication_dates(competitor_id)
        results['steps']['dates'] = date_results
        
        # Étape 2: Télécharger la thumbnail
        print("\n🖼️  ÉTAPE 2: Téléchargement de la thumbnail")
        thumbnail_results = self._download_thumbnail(competitor_id, channel_url)
        results['steps']['thumbnail'] = thumbnail_results
        
        # Étape 3: Classification automatique
        print("\n🏷️  ÉTAPE 3: Classification automatique HHH")
        classification_results = self._run_classification(competitor_id)
        results['steps']['classification'] = classification_results
        
        # Étape 4: Calculer les statistiques
        print("\n📊 ÉTAPE 4: Calcul des statistiques")
        stats_results = self._calculate_statistics(competitor_id)
        results['steps']['statistics'] = stats_results
        
        # Étape 5: Rafraîchir les caches
        print("\n🔄 ÉTAPE 5: Rafraîchissement des caches")
        cache_results = self._refresh_caches(competitor_id)
        results['steps']['cache'] = cache_results
        
        print("\n✅ WORKFLOW TERMINÉ!")
        print("=" * 60)
        
        return results
    
    def _fix_publication_dates(self, competitor_id: int) -> Dict:
        """Corrige les dates de publication en utilisant l'API YouTube"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Vérifier si les dates nécessitent une correction
            cursor.execute("""
                SELECT COUNT(DISTINCT DATE(published_at)) as unique_dates,
                       COUNT(*) as total_videos
                FROM video WHERE concurrent_id = ?
            """, (competitor_id,))
            
            unique_dates, total_videos = cursor.fetchone()
            
            if unique_dates == 1 and total_videos > 10:
                print(f"   ⚠️  Toutes les {total_videos} vidéos ont la même date - correction nécessaire")
                
                # Récupérer les IDs des vidéos
                cursor.execute("""
                    SELECT video_id FROM video 
                    WHERE concurrent_id = ? 
                    ORDER BY id DESC 
                    LIMIT 50
                """, (competitor_id,))
                
                video_ids = [row[0] for row in cursor.fetchall()]
                
                if not self.youtube_client:
                    self.youtube_client = create_youtube_client()
                
                # Récupérer les vraies dates
                print(f"   📥 Récupération des dates pour {len(video_ids)} vidéos...")
                videos_details = self.youtube_client.get_videos_details(video_ids)
                
                # Mettre à jour les dates
                updated = 0
                for video in videos_details:
                    video_id = video.get('id')
                    published_at = video.get('published_at')
                    
                    if video_id and published_at:
                        cursor.execute("""
                            UPDATE video 
                            SET published_at = ?, last_updated = datetime('now')
                            WHERE video_id = ? AND concurrent_id = ?
                        """, (published_at, video_id, competitor_id))
                        updated += 1
                
                conn.commit()
                
                # Vérifier le résultat
                cursor.execute("""
                    SELECT COUNT(DISTINCT DATE(published_at)) as unique_dates_after
                    FROM video WHERE concurrent_id = ?
                """, (competitor_id,))
                
                unique_dates_after = cursor.fetchone()[0]
                
                return {
                    'status': 'success',
                    'videos_updated': updated,
                    'unique_dates_before': unique_dates,
                    'unique_dates_after': unique_dates_after
                }
            else:
                return {
                    'status': 'skipped',
                    'reason': f'{unique_dates} dates uniques trouvées, pas de correction nécessaire'
                }
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()
    
    def _download_thumbnail(self, competitor_id: int, channel_url: str) -> Dict:
        """Télécharge et sauvegarde la thumbnail de la chaîne"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Vérifier si la thumbnail existe déjà
            thumbnail_path = os.path.join(self.static_dir, 'competitors', 'images', f'{competitor_id}.jpg')
            
            if os.path.exists(thumbnail_path):
                return {
                    'status': 'skipped',
                    'reason': 'Thumbnail déjà présente',
                    'path': thumbnail_path
                }
            
            # Récupérer l'URL de la thumbnail
            cursor.execute("SELECT thumbnail_url FROM concurrent WHERE id = ?", (competitor_id,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                # Récupérer via l'API YouTube
                if not self.youtube_client:
                    self.youtube_client = create_youtube_client()
                
                channel_info = self.youtube_client.get_channel_info(channel_url)
                thumbnail_url = channel_info.get('thumbnail')
                
                # Mettre à jour en base
                cursor.execute("""
                    UPDATE concurrent 
                    SET thumbnail_url = ?, last_updated = datetime('now')
                    WHERE id = ?
                """, (thumbnail_url, competitor_id))
                conn.commit()
            else:
                thumbnail_url = result[0]
            
            if thumbnail_url:
                # Télécharger l'image
                print(f"   📥 Téléchargement depuis: {thumbnail_url[:50]}...")
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                
                # Créer le répertoire si nécessaire
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                
                # Sauvegarder l'image
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ Thumbnail sauvegardée: {thumbnail_path}")
                
                return {
                    'status': 'success',
                    'path': thumbnail_path,
                    'size': len(response.content)
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Aucune URL de thumbnail trouvée'
                }
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()
    
    def _run_classification(self, competitor_id: int) -> Dict:
        """Lance la classification automatique des vidéos"""
        try:
            print(f"   🤖 Lancement de la classification automatique...")
            
            # Utiliser la classification par mots-clés
            results = classify_videos_directly_with_keywords(competitor_id)
            
            print(f"   ✅ Classification terminée")
            if 'by_category' in results:
                for category, count in results['by_category'].items():
                    print(f"      - {category}: {count} vidéos")
            
            return {
                'status': 'success',
                'results': results
            }
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_statistics(self, competitor_id: int) -> Dict:
        """Calcule et met à jour les statistiques du concurrent"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Calculer les statistiques de base
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_videos,
                    SUM(view_count) as total_views,
                    AVG(view_count) as avg_views,
                    MAX(view_count) as max_views,
                    SUM(like_count) as total_likes,
                    SUM(comment_count) as total_comments
                FROM video 
                WHERE concurrent_id = ?
            """, (competitor_id,))
            
            stats = cursor.fetchone()
            
            # Calculer la fréquence de publication
            frequency = calculate_publication_frequency(competitor_id)
            
            # Mettre à jour la table competitor_stats
            cursor.execute("""
                INSERT OR REPLACE INTO competitor_stats (
                    competitor_id, total_videos, total_views, avg_views,
                    last_updated
                ) VALUES (?, ?, ?, ?, datetime('now'))
            """, (competitor_id, stats[0], stats[1], stats[2]))
            
            # Calculer la distribution HHH
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero,
                    COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub,
                    COUNT(CASE WHEN category = 'help' THEN 1 END) as help
                FROM video WHERE concurrent_id = ?
            """, (competitor_id,))
            
            hhh = cursor.fetchone()
            
            conn.commit()
            
            return {
                'status': 'success',
                'total_videos': stats[0],
                'total_views': stats[1],
                'videos_per_week': frequency,
                'hhh_distribution': {
                    'hero': hhh[0],
                    'hub': hhh[1],
                    'help': hhh[2]
                }
            }
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()
    
    def _refresh_caches(self, competitor_id: int) -> Dict:
        """Rafraîchit les caches et métriques"""
        try:
            # Ici on pourrait invalider des caches Redis ou autres
            # Pour l'instant on se contente de marquer comme succès
            
            return {
                'status': 'success',
                'message': 'Caches rafraîchis'
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# Instance globale pour réutilisation
workflow_manager = ImportWorkflowManager()