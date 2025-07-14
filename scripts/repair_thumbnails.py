#!/usr/bin/env python3
"""
Script pour réparer les miniatures manquantes dans la base de données
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database import get_db_connection, extract_video_id_from_url
from datetime import datetime

def repair_missing_thumbnails():
    """
    Réparer les miniatures manquantes en générant les URLs depuis les video_id
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("🔍 Recherche des miniatures manquantes...")
        
        # Récupérer les vidéos sans miniatures ou avec des miniatures invalides
        cursor.execute('''
            SELECT id, video_id, title, url, thumbnail_url 
            FROM video 
            WHERE thumbnail_url IS NULL 
               OR thumbnail_url = '' 
               OR thumbnail_url NOT LIKE '%ytimg.com%'
        ''')
        videos_to_repair = cursor.fetchall()
        
        if not videos_to_repair:
            print("✅ Aucune miniature à réparer")
            return
        
        print(f"📋 {len(videos_to_repair)} miniatures à réparer")
        repaired_count = 0
        
        for video in videos_to_repair:
            video_id = video[1]  # video_id
            video_url = video[3]  # url
            
            # Essayer d'extraire l'ID vidéo depuis l'URL si le video_id n'est pas valide
            if not video_id or len(video_id) != 11:
                video_id = extract_video_id_from_url(video_url)
            
            if video_id and len(video_id) == 11:
                # Générer l'URL de miniature
                new_thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                
                # Mettre à jour la base de données
                cursor.execute('''
                    UPDATE video 
                    SET thumbnail_url = ?, last_updated = ?
                    WHERE id = ?
                ''', (new_thumbnail_url, datetime.now(), video[0]))
                
                repaired_count += 1
                print(f"🔧 Miniature réparée pour: {video[2][:50]}...")
        
        conn.commit()
        print(f"✅ {repaired_count} miniatures réparées avec succès")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de la réparation des miniatures: {e}")
        raise
    finally:
        conn.close()

def get_thumbnail_stats():
    """
    Obtenir des statistiques sur les miniatures
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Statistiques des vidéos
        cursor.execute('''
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN thumbnail_url IS NOT NULL AND thumbnail_url != '' THEN 1 END) as with_thumbnails,
                COUNT(CASE WHEN thumbnail_url IS NULL OR thumbnail_url = '' THEN 1 END) as without_thumbnails,
                COUNT(CASE WHEN thumbnail_url LIKE '%ytimg.com%' THEN 1 END) as youtube_thumbnails
            FROM video
        ''')
        video_stats = cursor.fetchone()
        
        # Statistiques des concurrents
        cursor.execute('''
            SELECT 
                COUNT(*) as total_competitors,
                COUNT(CASE WHEN thumbnail_url IS NOT NULL AND thumbnail_url != '' THEN 1 END) as with_thumbnails,
                COUNT(CASE WHEN thumbnail_url IS NULL OR thumbnail_url = '' THEN 1 END) as without_thumbnails
            FROM concurrent
        ''')
        competitor_stats = cursor.fetchone()
        
        print("\n📊 STATISTIQUES DES MINIATURES")
        print("=" * 50)
        print(f"🎬 VIDÉOS:")
        print(f"   Total: {video_stats[0]}")
        print(f"   Avec miniatures: {video_stats[1]}")
        print(f"   Sans miniatures: {video_stats[2]}")
        print(f"   YouTube miniatures: {video_stats[3]}")
        print(f"   Couverture: {round((video_stats[1] / video_stats[0]) * 100, 2)}%")
        
        print(f"\n🏢 CONCURRENTS:")
        print(f"   Total: {competitor_stats[0]}")
        print(f"   Avec miniatures: {competitor_stats[1]}")
        print(f"   Sans miniatures: {competitor_stats[2]}")
        print(f"   Couverture: {round((competitor_stats[1] / competitor_stats[0]) * 100, 2)}%")
        
    except Exception as e:
        print(f"❌ Erreur lors du calcul des statistiques: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🖼️  RÉPARATION DES MINIATURES YOUTUBE")
    print("=" * 50)
    
    # Afficher les statistiques avant
    print("\n📊 ÉTAT ACTUEL:")
    get_thumbnail_stats()
    
    # Réparer les miniatures
    print("\n🔧 RÉPARATION EN COURS...")
    repair_missing_thumbnails()
    
    # Afficher les statistiques après
    print("\n📊 ÉTAT APRÈS RÉPARATION:")
    get_thumbnail_stats()
    
    print("\n✅ Script terminé avec succès!") 