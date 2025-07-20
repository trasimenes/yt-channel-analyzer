#!/usr/bin/env python3
"""
Script pour recalculer et mettre à jour les statistiques des concurrents
basées sur les données réelles des vidéos en base.
"""

import sqlite3
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database.base import get_db_connection

def update_competitor_stats():
    """Mettre à jour toutes les statistiques des concurrents"""
    
    print("🔄 Mise à jour des statistiques des concurrents...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer tous les concurrents
        cursor.execute("SELECT id, name FROM concurrent")
        competitors = cursor.fetchall()
        
        updated_count = 0
        
        for competitor in competitors:
            competitor_id = competitor[0]
            competitor_name = competitor[1]
            
            # Calculer les statistiques réelles depuis les vidéos
            cursor.execute("""
                SELECT 
                    COUNT(*) as video_count,
                    COALESCE(SUM(view_count), 0) as total_views,
                    COALESCE(SUM(like_count), 0) as total_likes,
                    COALESCE(SUM(comment_count), 0) as total_comments,
                    COALESCE(AVG(view_count), 0) as avg_views,
                    MAX(published_at) as latest_video_date
                FROM video 
                WHERE concurrent_id = ? AND view_count IS NOT NULL
            """, (competitor_id,))
            
            stats = cursor.fetchone()
            
            if stats and stats[0] > 0:  # Si le concurrent a des vidéos
                video_count = stats[0]
                total_views = stats[1]
                total_likes = stats[2]
                total_comments = stats[3]
                avg_views = stats[4]
                latest_video_date = stats[5]
                
                # Mettre à jour les statistiques du concurrent
                cursor.execute("""
                    UPDATE concurrent 
                    SET 
                        video_count = ?,
                        view_count = ?,
                        last_updated = ?
                    WHERE id = ?
                """, (video_count, total_views, datetime.now(), competitor_id))
                
                updated_count += 1
                
                print(f"✅ {competitor_name}: {video_count} vidéos, {total_views:,} vues totales")
            else:
                print(f"⚠️  {competitor_name}: Aucune vidéo trouvée")
        
        conn.commit()
        print(f"\n🎉 Mise à jour terminée: {updated_count} concurrents mis à jour")
        
        # Afficher un résumé des totaux
        cursor.execute("""
            SELECT 
                COUNT(*) as total_competitors,
                SUM(video_count) as total_videos,
                SUM(view_count) as total_views,
                SUM(subscriber_count) as total_subscribers
            FROM concurrent
            WHERE video_count > 0
        """)
        
        summary = cursor.fetchone()
        if summary:
            print(f"\n📊 Résumé global:")
            print(f"   • {summary[0]} concurrents actifs")
            print(f"   • {summary[1]} vidéos totales")
            print(f"   • {summary[2]:,} vues totales")
            print(f"   • {summary[3]:,} abonnés totaux")
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True

def check_data_consistency():
    """Vérifier la cohérence des données"""
    
    print("\n🔍 Vérification de la cohérence des données...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier les incohérences
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.video_count as declared_videos,
                COUNT(v.id) as actual_videos,
                c.view_count as declared_views,
                COALESCE(SUM(v.view_count), 0) as actual_views
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id
            HAVING c.video_count != COUNT(v.id) OR c.view_count != COALESCE(SUM(v.view_count), 0)
            ORDER BY c.name
        """)
        
        inconsistencies = cursor.fetchall()
        
        if inconsistencies:
            print(f"\n⚠️  {len(inconsistencies)} incohérences trouvées:")
            for row in inconsistencies:
                comp_id, name, declared_videos, actual_videos, declared_views, actual_views = row
                print(f"   • {name}:")
                if declared_videos != actual_videos:
                    print(f"     - Vidéos: {declared_videos} déclarées vs {actual_videos} réelles")
                if declared_views != actual_views:
                    print(f"     - Vues: {declared_views:,} déclarées vs {actual_views:,} réelles")
        else:
            print("✅ Aucune incohérence détectée")
    
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Démarrage du script de mise à jour des statistiques concurrents")
    
    # Vérifier la cohérence avant
    check_data_consistency()
    
    # Mettre à jour les statistiques
    if update_competitor_stats():
        # Vérifier la cohérence après
        check_data_consistency()
        print("\n✅ Script terminé avec succès!")
    else:
        print("\n❌ Échec du script")
        sys.exit(1)