#!/usr/bin/env python3
"""
Script pour corriger les données Center Parcs avec les vraies dates de publication YouTube
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.youtube_api_client import create_youtube_client
from datetime import datetime

def fix_center_parcs_publication_dates():
    """Corriger les dates de publication des vidéos Center Parcs"""
    
    print("🔧 CORRECTION des dates de publication Center Parcs...")
    
    # Connexion à la base de données
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer les chaînes Center Parcs
        cursor.execute("""
            SELECT id, name, channel_url, country 
            FROM concurrent 
            WHERE name LIKE '%Center Parcs%'
            ORDER BY id
        """)
        
        channels = cursor.fetchall()
        youtube = create_youtube_client()
        
        for channel_id, name, channel_url, country in channels:
            print(f"\n📊 Traitement de {name} ({country})...")
            
            # Récupérer les vidéos existantes
            cursor.execute("""
                SELECT id, video_id, title, published_at
                FROM video 
                WHERE concurrent_id = ?
                ORDER BY id
                LIMIT 10
            """, (channel_id,))
            
            existing_videos = cursor.fetchall()
            print(f"   Vidéos trouvées en base: {len(existing_videos)}")
            
            # Récupérer les vraies données YouTube pour un échantillon
            try:
                real_videos = youtube.get_channel_videos(channel_url, max_results=50)
                print(f"   Vidéos récupérées de YouTube: {len(real_videos)}")
                
                updated_count = 0
                for db_video in existing_videos:
                    db_id, video_id, title, current_date = db_video
                    
                    # Trouver la vidéo correspondante sur YouTube
                    matching_video = None
                    for yt_video in real_videos:
                        if yt_video.get('video_id') == video_id:
                            matching_video = yt_video
                            break
                    
                    if matching_video and matching_video.get('published_at'):
                        real_date = matching_video['published_at']
                        
                        # Mettre à jour seulement si la date est différente
                        if real_date != current_date:
                            cursor.execute("""
                                UPDATE video 
                                SET published_at = ?
                                WHERE id = ?
                            """, (real_date, db_id))
                            
                            updated_count += 1
                            print(f"   ✅ {title[:50]}... : {current_date} → {real_date}")
                
                if updated_count > 0:
                    conn.commit()
                    print(f"   💾 {updated_count} vidéos mises à jour pour {name}")
                else:
                    print(f"   ℹ️ Aucune mise à jour nécessaire pour {name}")
                    
            except Exception as e:
                print(f"   ❌ Erreur API pour {name}: {e}")
                continue
        
        print("\n🎉 Correction terminée!")
        
        # Recalculer les statistiques de fréquence
        print("\n📊 Recalcul des statistiques de fréquence...")
        
        for channel_id, name, channel_url, country in channels:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_videos,
                    MIN(published_at) as first_video,
                    MAX(published_at) as last_video
                FROM video 
                WHERE concurrent_id = ? 
                  AND published_at IS NOT NULL
                  AND published_at NOT LIKE '2025-07-05%'  -- Exclure les dates d'import
            """, (channel_id,))
            
            result = cursor.fetchone()
            if result and result[0] > 0:
                total_videos, first_date, last_date = result
                
                try:
                    # Parser les dates
                    if 'T' in first_date:
                        first_dt = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
                        last_dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
                    else:
                        first_dt = datetime.fromisoformat(first_date.split('.')[0])
                        last_dt = datetime.fromisoformat(last_date.split('.')[0])
                    
                    # Calculer la fréquence
                    period_days = max(1, (last_dt - first_dt).days)
                    videos_per_week = (total_videos / period_days) * 7
                    
                    # Mettre à jour les statistiques
                    cursor.execute("""
                        INSERT OR REPLACE INTO competitor_frequency_stats
                        (competitor_id, avg_videos_per_week, total_videos, days_active, last_calculated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (channel_id, videos_per_week, total_videos, period_days, datetime.now()))
                    
                    print(f"📈 {name}: {total_videos} vidéos sur {period_days} jours = {videos_per_week:.1f} vid/semaine")
                    
                except Exception as e:
                    print(f"⚠️ Erreur calcul fréquence {name}: {e}")
        
        conn.commit()
        print("\n✅ Statistiques recalculées!")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_center_parcs_publication_dates()