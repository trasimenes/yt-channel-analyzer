#!/usr/bin/env python3
"""
Script de correction manuelle des dates Pierre et Vacances
Récupère les vraies dates de publication depuis YouTube et les applique en base.
"""

import sqlite3
import re
import urllib.request
import urllib.parse
from datetime import datetime
import time
from yt_channel_analyzer.database import get_db_connection

def get_youtube_publish_date(video_id):
    """Récupérer la date de publication d'une vidéo YouTube via scraping léger"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
        
        # Chercher différents patterns de date dans le HTML
        patterns = [
            r'"publishDate":"([^"]*)"',
            r'"datePublished":"([^"]*)"',
            r'datePublished":\s*"([^"]*)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                iso_date = match.group(1)
                try:
                    # Convertir la date ISO en format SQLite
                    date_obj = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
                    return date_obj.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    continue
        
        return None
        
    except Exception as e:
        print(f"Erreur pour {video_id}: {e}")
        return None

def fix_pierre_vacances_dates():
    """Corriger les dates de Pierre et Vacances"""
    
    print("🔧 Correction des dates Pierre et Vacances")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer les vidéos avec dates corrompues
    cursor.execute("""
    SELECT id, video_id, title, published_at
    FROM video 
    WHERE concurrent_id = 504 
    AND DATE(published_at) = '2025-07-30'
    ORDER BY id
    LIMIT 25
    """)
    
    videos = cursor.fetchall()
    print(f"📊 {len(videos)} vidéos à corriger")
    
    corrections = 0
    
    for i, (db_id, video_id, title, current_date) in enumerate(videos, 1):
        print(f"\n🎬 [{i}/{len(videos)}] {title[:50]}...")
        print(f"   Video ID: {video_id}")
        print(f"   Date actuelle: {current_date}")
        
        # Récupérer la vraie date YouTube
        real_date = get_youtube_publish_date(video_id)
        
        if real_date:
            print(f"   ✅ Vraie date: {real_date}")
            
            # Appliquer la correction en base
            cursor.execute("""
            UPDATE video 
            SET published_at = ?, 
                youtube_published_at = ?, 
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (real_date, real_date, db_id))
            
            corrections += 1
            print(f"   🔧 CORRIGÉ en base")
        else:
            print(f"   ❌ Impossible de récupérer la date")
        
        # Délai pour éviter le rate limiting
        time.sleep(2)
    
    # Sauvegarder les modifications
    conn.commit()
    conn.close()
    
    print(f"\n✅ Correction terminée : {corrections}/{len(videos)} vidéos corrigées")
    
    # Vérifier les résultats
    print("\n📊 Vérification des corrections...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN DATE(published_at) = '2025-07-30' THEN 1 END) as still_corrupted,
        MIN(DATE(published_at)) as earliest_date,
        MAX(DATE(published_at)) as latest_date
    FROM video 
    WHERE concurrent_id = 504
    """)
    
    result = cursor.fetchone()
    print(f"Total vidéos: {result[0]}")
    print(f"Dates encore corrompues: {result[1]}")
    print(f"Date la plus ancienne: {result[2]}")
    print(f"Date la plus récente: {result[3]}")
    
    conn.close()

if __name__ == "__main__":
    fix_pierre_vacances_dates()