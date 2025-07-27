#!/usr/bin/env python3
"""
Script pour corriger les concurrents avec 0 playlists en créant des playlists par défaut
et en y associant leurs vidéos.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / 'instance' / 'database.db'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def fix_zero_playlists():
    """Corrige les concurrents avec 0 playlists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Recherche des concurrents sans playlists...")
    
    # Identifier les concurrents sans playlists mais avec des vidéos
    cursor.execute("""
        SELECT c.id, c.name, COUNT(v.id) as video_count
        FROM concurrent c 
        LEFT JOIN playlist p ON c.id = p.concurrent_id
        LEFT JOIN video v ON c.id = v.concurrent_id
        WHERE p.id IS NULL
        GROUP BY c.id, c.name
        HAVING COUNT(v.id) > 0
        ORDER BY COUNT(v.id) DESC
    """)
    
    competitors_without_playlists = cursor.fetchall()
    logger.info(f"Trouvé {len(competitors_without_playlists)} concurrents sans playlists")
    
    playlists_created = 0
    videos_linked = 0
    
    for competitor_id, name, video_count in competitors_without_playlists:
        # Ignorer les concurrents de test
        if 'Test' in name or 'Topic Analysis' in name:
            logger.info(f"⏭️ Ignoré (test): {name}")
            continue
            
        logger.info(f"🔧 Correction pour: {name} ({video_count} vidéos)")
        
        # Créer une playlist "All Videos" pour ce concurrent
        playlist_id = f"{competitor_id}_all_videos"
        playlist_name = f"All Videos - {name}"
        
        try:
            cursor.execute("""
                INSERT INTO playlist (
                    playlist_id, concurrent_id, name, description, 
                    video_count, created_at, last_updated,
                    classification_source, category
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), 'auto', 'hub')
            """, (
                playlist_id,
                competitor_id, 
                playlist_name,
                f"Auto-generated playlist containing all videos from {name}",
                video_count
            ))
            
            new_playlist_db_id = cursor.lastrowid
            playlists_created += 1
            logger.info(f"✅ Playlist créée: {playlist_name} (ID: {new_playlist_db_id})")
            
            # Récupérer toutes les vidéos de ce concurrent
            cursor.execute("""
                SELECT id FROM video WHERE concurrent_id = ?
            """, (competitor_id,))
            
            video_ids = cursor.fetchall()
            
            # Lier toutes les vidéos à cette playlist
            for (video_id,) in video_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO playlist_video (playlist_id, video_id)
                    VALUES (?, ?)
                """, (new_playlist_db_id, video_id))
                videos_linked += 1
            
            logger.info(f"📹 {len(video_ids)} vidéos liées à la playlist")
            
        except Exception as e:
            logger.error(f"❌ Erreur pour {name}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 CORRECTIONS TERMINÉES:")
    logger.info(f"   • Playlists créées: {playlists_created}")
    logger.info(f"   • Vidéos liées: {videos_linked}")
    
    return playlists_created, videos_linked

def update_playlist_counts():
    """Met à jour les comptages de vidéos dans les playlists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔄 Mise à jour des comptages de playlists...")
    
    cursor.execute("""
        UPDATE playlist 
        SET video_count = (
            SELECT COUNT(*) 
            FROM playlist_video pv 
            WHERE pv.playlist_id = playlist.id
        ),
        last_updated = datetime('now')
    """)
    
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    
    logger.info(f"✅ {updated} playlists mises à jour")
    return updated

def verify_fixes():
    """Vérifie que les corrections ont été appliquées."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Vérification des corrections...")
    
    # Vérifier les concurrents sans playlists
    cursor.execute("""
        SELECT COUNT(*) 
        FROM concurrent c 
        LEFT JOIN playlist p ON c.id = p.concurrent_id
        LEFT JOIN video v ON c.id = v.concurrent_id
        WHERE p.id IS NULL
        GROUP BY c.id
        HAVING COUNT(v.id) > 0
    """)
    
    result = cursor.fetchone()
    remaining_without_playlists = result[0] if result else 0
    
    # Stats globales
    cursor.execute("SELECT COUNT(*) FROM playlist")
    total_playlists = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM playlist_video")
    total_links = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM concurrent c
        JOIN video v ON c.id = v.concurrent_id
        WHERE c.name NOT LIKE '%Test%' AND c.name NOT LIKE '%Topic Analysis%'
        GROUP BY c.id
        HAVING COUNT(v.id) > 0
    """)
    active_competitors = len(cursor.fetchall())
    
    cursor.execute("""
        SELECT COUNT(DISTINCT p.concurrent_id)
        FROM playlist p
        JOIN concurrent c ON p.concurrent_id = c.id
        WHERE c.name NOT LIKE '%Test%' AND c.name NOT LIKE '%Topic Analysis%'
    """)
    competitors_with_playlists = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 RÉSULTATS DE LA VÉRIFICATION:")
    print(f"   • Concurrents actifs avec vidéos: {active_competitors}")
    print(f"   • Concurrents avec playlists: {competitors_with_playlists}")
    print(f"   • Concurrents sans playlists restants: {remaining_without_playlists}")
    print(f"   • Total playlists: {total_playlists}")
    print(f"   • Total liens playlist-vidéo: {total_links}")
    
    if remaining_without_playlists == 0:
        print(f"   🎉 SUCCÈS: Tous les concurrents actifs ont des playlists!")
    else:
        print(f"   ⚠️ Il reste {remaining_without_playlists} concurrents sans playlists")

def main():
    """Fonction principale."""
    print("🚀 Correction des concurrents avec 0 playlists...")
    
    try:
        # 1. Créer les playlists manquantes
        playlists_created, videos_linked = fix_zero_playlists()
        
        # 2. Mettre à jour les comptages
        updated_counts = update_playlist_counts()
        
        # 3. Vérifier les résultats
        verify_fixes()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des corrections: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)