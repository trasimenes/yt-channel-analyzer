#!/usr/bin/env python3
"""
Script pour réimporter les données Center Parcs avec les vraies dates de publication
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.youtube_adapter import get_channel_videos_data_api
from datetime import datetime

def refresh_center_parcs_with_proper_dates():
    """Réimporter les chaînes Center Parcs avec les vraies dates de publication"""
    
    print("🔄 RÉIMPORT des chaînes Center Parcs avec vraies dates...")
    
    # Connexion à la base de données
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer les chaînes Center Parcs (sauf l'allemande qui a déjà de bonnes dates)
        cursor.execute("""
            SELECT id, name, channel_url, country 
            FROM concurrent 
            WHERE name LIKE '%Center Parcs%' 
              AND id != 122  -- Exclure l'allemande qui a de bonnes dates
            ORDER BY id
        """)
        
        channels = cursor.fetchall()
        
        for channel_id, name, channel_url, country in channels:
            print(f"\n🔄 Réimport de {name} ({country})...")
            
            # Supprimer toutes les vidéos existantes pour cette chaîne
            cursor.execute('DELETE FROM video WHERE concurrent_id = ?', (channel_id,))
            print(f"   🗑️ Anciennes vidéos supprimées")
            
            # Réimporter via l'API avec correction de date
            try:
                fresh_videos = get_channel_videos_data_api(channel_url, video_limit=500)
                print(f"   📥 {len(fresh_videos)} vidéos récupérées depuis YouTube")
                
                if fresh_videos:
                    # Sauvegarder avec les bonnes dates
                    from app import save_competitor_data
                    
                    competitor_id = save_competitor_data(channel_url, fresh_videos)
                    print(f"   ✅ {len(fresh_videos)} vidéos sauvegardées avec dates correctes")
                    
                    # Vérifier un échantillon de dates
                    cursor.execute("""
                        SELECT title, published_at
                        FROM video 
                        WHERE concurrent_id = ?
                        ORDER BY published_at
                        LIMIT 5
                    """, (channel_id,))
                    
                    sample_videos = cursor.fetchall()
                    print("   📅 Échantillon de dates:")
                    for title, date in sample_videos:
                        print(f"      • {title[:40]}... → {date}")
                
                conn.commit()
                
            except Exception as e:
                print(f"   ❌ Erreur import {name}: {e}")
                conn.rollback()
                continue
        
        print("\n📊 Recalcul des statistiques de fréquence...")
        
        # Recalculer les fréquences avec les nouvelles dates
        for channel_id, name, channel_url, country in channels:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_videos,
                    MIN(published_at) as first_video,
                    MAX(published_at) as last_video
                FROM video 
                WHERE concurrent_id = ? 
                  AND published_at IS NOT NULL
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
                        (competitor_id, avg_videos_per_week, total_videos, last_calculated)
                        VALUES (?, ?, ?, ?)
                    """, (channel_id, videos_per_week, total_videos, datetime.now()))
                    
                    print(f"✅ {name}: {total_videos} vidéos sur {period_days} jours = {videos_per_week:.1f} vid/semaine")
                    
                except Exception as e:
                    print(f"⚠️ Erreur calcul fréquence {name}: {e}")
        
        conn.commit()
        print("\n🎉 Réimport terminé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    refresh_center_parcs_with_proper_dates()