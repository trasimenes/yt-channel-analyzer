#!/usr/bin/env python3
"""
Script pour vérifier les données classifiées humainement disponibles
"""

from yt_channel_analyzer.database.base import get_db_connection

def main():
    print("🔍 Vérification des données classifiées humainement")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier les playlists
    print("\n📚 Playlists classifiées humainement :")
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM playlist
        WHERE (is_human_validated = 1 
           OR classification_source = 'human'
           OR human_verified = 1)
           AND category IS NOT NULL
           AND category != ''
        GROUP BY category
        ORDER BY count DESC
    """)
    
    total_playlists = 0
    for cat, count in cursor.fetchall():
        print(f"  - {cat}: {count} playlists")
        total_playlists += count
    print(f"\n  Total: {total_playlists} playlists")
    
    # Afficher quelques exemples
    print("\n📋 Exemples de playlists classifiées :")
    cursor.execute("""
        SELECT name, category, classification_source
        FROM playlist
        WHERE (is_human_validated = 1 
           OR classification_source = 'human'
           OR human_verified = 1)
           AND category IS NOT NULL
        LIMIT 10
    """)
    
    for name, cat, source in cursor.fetchall():
        print(f"  - [{cat}] {name} (source: {source})")
    
    # Vérifier les vidéos
    print("\n🎬 Vidéos classifiées humainement :")
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM video
        WHERE (is_human_validated = 1 
           OR classification_source = 'human')
           AND category IS NOT NULL
           AND category != ''
        GROUP BY category
        ORDER BY count DESC
    """)
    
    total_videos = 0
    for cat, count in cursor.fetchall():
        print(f"  - {cat}: {count} vidéos")
        total_videos += count
    print(f"\n  Total: {total_videos} vidéos")
    
    conn.close()
    
    print("\n✅ Ces données peuvent être utilisées pour entraîner le modèle sémantique")

if __name__ == "__main__":
    main()