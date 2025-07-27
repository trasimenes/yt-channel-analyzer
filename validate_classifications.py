#!/usr/bin/env python3

from yt_channel_analyzer.database import get_db_connection

def validate_classifications():
    conn = get_db_connection()
    cursor = conn.cursor()

    print('=== CLASSIFICATION DATA AUDIT ===')

    # 1. Overall classification coverage
    cursor.execute('''
        SELECT 
            COUNT(*) as total_videos,
            COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as categorized,
            COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
            COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
            COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count,
            COUNT(CASE WHEN category = 'uncategorized' OR category IS NULL OR category = '' THEN 1 END) as uncategorized
        FROM video
    ''')
    classification_stats = cursor.fetchone()
    total = classification_stats[0]
    print(f'Video Classification Coverage:')
    print(f'  Total videos: {total}')
    print(f'  Categorized: {classification_stats[1]} ({classification_stats[1]/total*100:.1f}%)')
    print(f'  Hero: {classification_stats[2]} ({classification_stats[2]/total*100:.1f}%)')
    print(f'  Hub: {classification_stats[3]} ({classification_stats[3]/total*100:.1f}%)')
    print(f'  Help: {classification_stats[4]} ({classification_stats[4]/total*100:.1f}%)')
    print(f'  Uncategorized: {classification_stats[5]} ({classification_stats[5]/total*100:.1f}%)')

    # 2. Check protection of human-validated data
    cursor.execute('''
        SELECT 
            COUNT(*) as total_human_validated,
            COUNT(CASE WHEN classification_source = 'human' THEN 1 END) as source_human,
            COUNT(CASE WHEN is_human_validated = 1 THEN 1 END) as flag_validated
        FROM video
        WHERE (is_human_validated = 1 OR classification_source = 'human')
    ''')
    human_validation = cursor.fetchone()
    print(f'\nHuman Validation Protection:')
    print(f'  Videos with human validation: {human_validation[0]}')
    print(f'  With source=human: {human_validation[1]}')
    print(f'  With is_human_validated=1: {human_validation[2]}')

    # 3. Classification by source
    cursor.execute('''
        SELECT 
            classification_source,
            COUNT(*) as count,
            COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero,
            COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub,
            COUNT(CASE WHEN category = 'help' THEN 1 END) as help
        FROM video
        WHERE category IS NOT NULL AND category != ''
        GROUP BY classification_source
        ORDER BY count DESC
    ''')
    by_source = cursor.fetchall()
    print(f'\nClassification by Source:')
    for source in by_source:
        source_name = source[0] or 'NULL'
        print(f'  {source_name}: {source[1]} videos (Hero: {source[2]}, Hub: {source[3]}, Help: {source[4]})')

    # 4. Playlist classification coverage
    cursor.execute('''
        SELECT 
            COUNT(*) as total_playlists,
            COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as categorized,
            COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
            COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
            COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count,
            COUNT(CASE WHEN is_human_validated = 1 THEN 1 END) as human_validated
        FROM playlist
    ''')
    playlist_stats = cursor.fetchone()
    print(f'\nPlaylist Classification:')
    print(f'  Total playlists: {playlist_stats[0]}')
    print(f'  Categorized: {playlist_stats[1]} ({playlist_stats[1]/playlist_stats[0]*100:.1f}%)')
    print(f'  Hero: {playlist_stats[2]}, Hub: {playlist_stats[3]}, Help: {playlist_stats[4]}')
    print(f'  Human validated: {playlist_stats[5]} ({playlist_stats[5]/playlist_stats[0]*100:.1f}%)')

    # 5. Check by competitor for classification coverage
    cursor.execute('''
        SELECT 
            c.name,
            c.country,
            COUNT(v.id) as total_videos,
            COUNT(CASE WHEN v.category IS NOT NULL AND v.category != '' THEN 1 END) as categorized_videos,
            COUNT(CASE WHEN v.category = 'hero' THEN 1 END) as hero,
            COUNT(CASE WHEN v.category = 'hub' THEN 1 END) as hub,
            COUNT(CASE WHEN v.category = 'help' THEN 1 END) as help
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        GROUP BY c.id, c.name, c.country
        HAVING COUNT(v.id) > 0
        ORDER BY categorized_videos DESC, total_videos DESC
    ''')
    competitor_classification = cursor.fetchall()
    print(f'\nTop Competitors by Classification Coverage:')
    for i, comp in enumerate(competitor_classification[:10], 1):
        coverage = comp[3]/comp[2]*100 if comp[2] > 0 else 0
        print(f'  {i}. {comp[0]} ({comp[1]}): {comp[3]}/{comp[2]} videos classified ({coverage:.1f}%)')
        print(f'     Hero: {comp[4]}, Hub: {comp[5]}, Help: {comp[6]}')

    conn.close()

if __name__ == '__main__':
    validate_classifications()