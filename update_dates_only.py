#!/usr/bin/env python3
"""
Script simple pour mettre à jour seulement les dates de publication
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api
from datetime import datetime

def update_publication_dates_only():
    """Mettre à jour seulement les dates de publication des vidéos existantes"""
    
    print("📅 MISE À JOUR des dates de publication Center Parcs...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer les chaînes Center Parcs (sauf l'allemande)
        cursor.execute("""
            SELECT id, name, channel_url, country 
            FROM concurrent 
            WHERE name LIKE '%Center Parcs%' 
              AND id IN (2, 5, 9)  -- UK, France, Netherlands uniquement
            ORDER BY id
        """)
        
        channels = cursor.fetchall()
        
        for channel_id, name, channel_url, country in channels:
            print(f"\n📅 Mise à jour dates pour {name} ({country})...")
            
            # Récupérer les vidéos de l'API avec leurs vraies dates
            try:
                api_videos = get_channel_videos_data_api(channel_url, video_limit=100)
                print(f"   📥 {len(api_videos)} vidéos récupérées de l'API")
                
                # Récupérer les vidéos existantes en base
                cursor.execute("""
                    SELECT video_id, id, title
                    FROM video 
                    WHERE concurrent_id = ?
                """, (channel_id,))
                
                db_videos = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}  # video_id -> (db_id, title)
                print(f"   💾 {len(db_videos)} vidéos trouvées en base")
                
                updated_count = 0
                for api_video in api_videos:
                    api_video_id = api_video.get('video_id', '')
                    api_published_at = api_video.get('published_at', '')
                    
                    if api_video_id in db_videos and api_published_at:
                        db_id, db_title = db_videos[api_video_id]
                        
                        # Mettre à jour la date
                        cursor.execute("""
                            UPDATE video 
                            SET published_at = ?
                            WHERE id = ?
                        """, (api_published_at, db_id))
                        
                        updated_count += 1
                        if updated_count <= 5:  # Afficher les 5 premières
                            print(f"   ✅ {db_title[:40]}... → {api_published_at}")
                
                conn.commit()
                print(f"   💾 {updated_count} dates mises à jour")
                
                # Vérifier les nouvelles dates
                cursor.execute("""
                    SELECT MIN(published_at), MAX(published_at), COUNT(*)
                    FROM video 
                    WHERE concurrent_id = ?
                """, (channel_id,))
                
                date_info = cursor.fetchone()
                print(f"   📊 Période: {date_info[0]} → {date_info[1]} ({date_info[2]} vidéos)")
                
                # Calculer la nouvelle fréquence
                if date_info[0] and date_info[1]:
                    if 'T' in date_info[0]:
                        first_dt = datetime.fromisoformat(date_info[0].replace('Z', '+00:00'))
                        last_dt = datetime.fromisoformat(date_info[1].replace('Z', '+00:00'))
                    else:
                        first_dt = datetime.fromisoformat(date_info[0].split('.')[0])
                        last_dt = datetime.fromisoformat(date_info[1].split('.')[0])
                    
                    period_days = max(1, (last_dt - first_dt).days)
                    videos_per_week = (date_info[2] / period_days) * 7
                    
                    print(f"   📈 Nouvelle fréquence: {videos_per_week:.1f} vidéos/semaine")
                    
                    # Mettre à jour la statistique
                    cursor.execute("""
                        INSERT OR REPLACE INTO competitor_frequency_stats
                        (competitor_id, avg_videos_per_week, total_videos)
                        VALUES (?, ?, ?)
                    """, (channel_id, videos_per_week, date_info[2]))
                    
                    conn.commit()
                
            except Exception as e:
                print(f"   ❌ Erreur pour {name}: {e}")
                continue
        
        print("\n✅ Mise à jour des dates terminée!")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_publication_dates_only()