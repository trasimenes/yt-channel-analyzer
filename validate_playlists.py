#!/usr/bin/env python3

from yt_channel_analyzer.database import get_db_connection

def validate_playlists():
    conn = get_db_connection()
    cursor = conn.cursor()

    print('=== PLAYLIST METRICS VALIDATION ===')

    # 1. Check playlist video_count vs actual videos
    cursor.execute('''
        SELECT 
            p.name,
            p.video_count as declared_count,
            COUNT(pv.video_id) as actual_count,
            c.name as competitor
        FROM playlist p
        LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
        LEFT JOIN concurrent c ON p.concurrent_id = c.id
        GROUP BY p.id, p.name, p.video_count, c.name
        HAVING ABS(COALESCE(p.video_count, 0) - COUNT(pv.video_id)) > 0
        ORDER BY ABS(COALESCE(p.video_count, 0) - COUNT(pv.video_id)) DESC
        LIMIT 15
    ''')
    playlist_mismatches = cursor.fetchall()
    print(f'Playlists with video count mismatches: {len(playlist_mismatches)}')
    for playlist in playlist_mismatches:
        diff = (playlist[1] or 0) - playlist[2]
        print(f'  "{playlist[0][:50]}..." ({playlist[3]})')
        print(f'    Declared: {playlist[1]}, Actual: {playlist[2]}, Difference: {diff}')

    # 2. Check for playlists with zero videos
    cursor.execute('''
        SELECT 
            COUNT(*) as total_playlists,
            COUNT(CASE WHEN video_count = 0 OR video_count IS NULL THEN 1 END) as zero_count_playlists
        FROM playlist
    ''')
    zero_playlists = cursor.fetchone()
    print(f'\nPlaylist Video Count Stats:')
    print(f'  Total playlists: {zero_playlists[0]}')
    print(f'  Playlists with zero/null video count: {zero_playlists[1]}')

    # 3. Check playlist_video junction table integrity
    cursor.execute('''
        SELECT 
            COUNT(*) as total_relationships,
            COUNT(DISTINCT playlist_id) as unique_playlists,
            COUNT(DISTINCT video_id) as unique_videos
        FROM playlist_video
    ''')
    junction_stats = cursor.fetchone()
    print(f'\nPlaylist-Video Junction Table:')
    print(f'  Total relationships: {junction_stats[0]}')
    print(f'  Unique playlists with videos: {junction_stats[1]}')
    print(f'  Unique videos in playlists: {junction_stats[2]}')

    # 4. Check for orphaned records
    cursor.execute('''
        SELECT COUNT(*) as orphaned_playlist_videos
        FROM playlist_video pv
        LEFT JOIN playlist p ON pv.playlist_id = p.id
        LEFT JOIN video v ON pv.video_id = v.id
        WHERE p.id IS NULL OR v.id IS NULL
    ''')
    orphaned = cursor.fetchone()
    print(f'  Orphaned playlist-video relationships: {orphaned[0]}')

    # 5. Videos not in any playlist
    cursor.execute('''
        SELECT 
            COUNT(v.id) as videos_not_in_playlists
        FROM video v
        LEFT JOIN playlist_video pv ON v.id = pv.video_id
        WHERE pv.video_id IS NULL
    ''')
    no_playlist_videos = cursor.fetchone()
    print(f'  Videos not in any playlist: {no_playlist_videos[0]}')

    # 6. Check playlist distribution by competitor
    cursor.execute('''
        SELECT 
            c.name,
            c.country,
            COUNT(p.id) as playlist_count,
            SUM(p.video_count) as total_declared_videos,
            COUNT(DISTINCT pv.video_id) as actual_unique_videos
        FROM concurrent c
        LEFT JOIN playlist p ON c.id = p.concurrent_id
        LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
        GROUP BY c.id, c.name, c.country
        HAVING COUNT(p.id) > 0
        ORDER BY playlist_count DESC
        LIMIT 10
    ''')
    competitor_playlists = cursor.fetchall()
    print(f'\nTop Competitors by Playlist Count:')
    for comp in competitor_playlists:
        print(f'  {comp[0]} ({comp[1]}): {comp[2]} playlists, {comp[3]} declared videos, {comp[4]} actual videos')

    conn.close()

if __name__ == '__main__':
    validate_playlists()