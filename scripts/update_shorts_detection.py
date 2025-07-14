#!/usr/bin/env python3
"""
Script pour mettre à jour la détection des Shorts pour tous les concurrents
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database import get_db_connection

def convert_duration_text_to_seconds(duration_text):
    """Convertit duration_text en secondes"""
    if not duration_text:
        return None
    
    # Supprimer les espaces
    duration_text = duration_text.strip()
    
    # Si c'est juste un nombre, c'est des secondes
    if duration_text.isdigit():
        return int(duration_text)
    
    # Format MM:SS ou HH:MM:SS
    parts = duration_text.split(':')
    if len(parts) == 2:  # MM:SS
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    
    return None

def update_all_competitors_shorts_detection():
    """Met à jour la détection des Shorts pour tous les concurrents"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("🔄 Mise à jour de la détection des Shorts pour tous les concurrents...")
        
        # Récupérer tous les concurrents
        cursor.execute("SELECT id, name FROM concurrent ORDER BY name")
        competitors = cursor.fetchall()
        
        print(f"📊 {len(competitors)} concurrents trouvés")
        
        total_updated = 0
        total_shorts_detected = 0
        
        for competitor_id, competitor_name in competitors:
            print(f"\n🏢 Traitement de {competitor_name} (ID: {competitor_id})...")
            
            # Récupérer les vidéos avec duration_text mais sans duration_seconds
            cursor.execute('''
                SELECT id, duration_text 
                FROM video 
                WHERE concurrent_id = ? 
                AND duration_text IS NOT NULL 
                AND (duration_seconds IS NULL OR is_short IS NULL)
            ''', (competitor_id,))
            
            videos = cursor.fetchall()
            
            if not videos:
                print(f"  ✅ Aucune vidéo à traiter")
                continue
            
            updated_count = 0
            shorts_count = 0
            
            for video_id, duration_text in videos:
                duration_seconds = convert_duration_text_to_seconds(duration_text)
                if duration_seconds is not None:
                    is_short = 1 if duration_seconds <= 60 else 0
                    
                    cursor.execute('''
                        UPDATE video 
                        SET duration_seconds = ?, is_short = ?
                        WHERE id = ?
                    ''', (duration_seconds, is_short, video_id))
                    
                    updated_count += 1
                    if is_short:
                        shorts_count += 1
            
            conn.commit()
            
            print(f"  ✅ {updated_count} vidéos mises à jour")
            print(f"  🎬 {shorts_count} Shorts détectés")
            
            total_updated += updated_count
            total_shorts_detected += shorts_count
        
        print(f"\n🎉 Mise à jour terminée !")
        print(f"📊 Total vidéos mises à jour: {total_updated}")
        print(f"🎬 Total Shorts détectés: {total_shorts_detected}")
        
        # Statistiques finales
        cursor.execute('''
            SELECT 
                COUNT(*) as total_videos,
                SUM(CASE WHEN is_short = 1 THEN 1 ELSE 0 END) as total_shorts,
                COUNT(DISTINCT concurrent_id) as total_competitors
            FROM video
        ''')
        
        stats = cursor.fetchone()
        print(f"\n📈 Statistiques globales:")
        print(f"  - Total vidéos: {stats[0]:,}")
        print(f"  - Total Shorts: {stats[1]:,}")
        print(f"  - Ratio Shorts: {(stats[1]/stats[0]*100):.1f}%")
        print(f"  - Concurrents: {stats[2]}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_all_competitors_shorts_detection() 