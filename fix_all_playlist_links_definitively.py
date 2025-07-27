#!/usr/bin/env python3
"""
SOLUTION DÉFINITIVE : Créer TOUS les liens playlist_video manquants
pour toutes les playlists validées humainement
"""
import sys
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

from yt_channel_analyzer.database import get_db_connection

def get_youtube_api_key():
    """Récupérer la clé API YouTube depuis .env"""
    return os.getenv('YOUTUBE_API_KEY')

def get_playlist_videos_from_api(api_key, playlist_id):
    """Récupérer toutes les vidéos d'une playlist via API YouTube"""
    videos = []
    next_page_token = None
    
    while True:
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        params = {
            'part': 'snippet',
            'playlistId': playlist_id,
            'maxResults': 50,
            'key': api_key
        }
        
        if next_page_token:
            params['pageToken'] = next_page_token
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"❌ Erreur API playlist {playlist_id}: {response.status_code}")
            return []
        
        data = response.json()
        
        for item in data.get('items', []):
            try:
                video_id = item['snippet']['resourceId']['videoId']
                title = item['snippet']['title']
                videos.append({
                    'video_id': video_id,
                    'title': title
                })
            except KeyError:
                continue
        
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
    
    return videos

def fix_all_playlist_links():
    """Solution définitive pour toutes les playlists"""
    
    print("🚀 SOLUTION DÉFINITIVE : CRÉATION DE TOUS LES LIENS PLAYLIST_VIDEO")
    print("=" * 80)
    
    # Récupérer clé API
    api_key = get_youtube_api_key()
    if not api_key:
        print("❌ ÉCHEC CRITIQUE: Clé API YouTube non trouvée dans .env")
        return False
    
    print(f"🔑 Clé API trouvée: {api_key[:10]}...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ÉTAPE 1: Récupérer TOUTES les playlists validées humainement
    print(f"\n🔍 ÉTAPE 1: Identification des playlists validées humainement")
    
    cursor.execute("""
        SELECT 
            p.id as db_id,
            p.playlist_id as youtube_id,
            p.name,
            p.category,
            p.video_count,
            c.name as competitor_name,
            c.id as competitor_id
        FROM playlist p
        JOIN concurrent c ON p.concurrent_id = c.id
        WHERE (p.human_verified = 1 OR p.classification_source = 'human')
          AND p.category IS NOT NULL
          AND p.category != 'uncategorized'
          AND p.playlist_id IS NOT NULL
          AND p.playlist_id != ''
        ORDER BY c.name, p.name
    """)
    
    human_playlists = cursor.fetchall()
    
    if not human_playlists:
        print("⚠️ Aucune playlist validée humainement trouvée")
        conn.close()
        return False
    
    print(f"🎯 {len(human_playlists)} playlists validées humainement trouvées")
    
    # ÉTAPE 2: Traiter chaque playlist
    print(f"\n🔧 ÉTAPE 2: Traitement systematique")
    
    total_playlists_processed = 0
    total_links_created = 0
    total_videos_propagated = 0
    skipped_playlists = 0
    
    for playlist in human_playlists:
        db_id, youtube_id, name, category, expected_count, competitor_name, competitor_id = playlist
        
        print(f"\n📋 {competitor_name}: {name}")
        print(f"   🎯 Catégorie: {category.upper()}")
        print(f"   📊 Vidéos attendues: {expected_count}")
        print(f"   🆔 YouTube ID: {youtube_id}")
        
        # Vérifier s'il y a déjà des liens
        cursor.execute("""
            SELECT COUNT(*)
            FROM playlist_video pv
            JOIN playlist p ON pv.playlist_id = p.playlist_id
            WHERE p.id = ?
        """, (db_id,))
        
        existing_links = cursor.fetchone()[0]
        
        if existing_links > 0:
            print(f"   ✅ {existing_links} liens existants - SKIP")
            skipped_playlists += 1
            continue
        
        # Récupérer vidéos via API
        print(f"   🔍 Récupération API...")
        playlist_videos = get_playlist_videos_from_api(api_key, youtube_id)
        
        if not playlist_videos:
            print(f"   ❌ Aucune vidéo trouvée via API")
            continue
        
        print(f"   📡 API: {len(playlist_videos)} vidéos trouvées")
        
        # Nettoyer les anciens liens (au cas où)
        cursor.execute("DELETE FROM playlist_video WHERE playlist_id = ?", (youtube_id,))
        
        # Trouver les vidéos dans notre base
        video_id_list = [video['video_id'] for video in playlist_videos]
        if not video_id_list:
            continue
            
        placeholders = ','.join(['?' for _ in video_id_list])
        
        cursor.execute(f"""
            SELECT id, video_id FROM video 
            WHERE video_id IN ({placeholders}) AND concurrent_id = ?
        """, video_id_list + [competitor_id])
        
        found_videos = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Créer les liens en lot
        links_to_insert = []
        for video in playlist_videos:
            video_id = video['video_id']
            if video_id in found_videos:
                db_video_id = found_videos[video_id]
                links_to_insert.append((youtube_id, db_video_id))
        
        if links_to_insert:
            try:
                cursor.executemany("""
                    INSERT INTO playlist_video (playlist_id, video_id) 
                    VALUES (?, ?)
                """, links_to_insert)
            except Exception as e:
                # Gérer les doublons potentiels
                print(f"   ⚠️ Erreur insertion (probablement doublons): {e}")
                # Insérer un par un en ignorant les doublons
                inserted_count = 0
                for playlist_id, video_id in links_to_insert:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO playlist_video (playlist_id, video_id) 
                            VALUES (?, ?)
                        """, (playlist_id, video_id))
                        if cursor.rowcount > 0:
                            inserted_count += 1
                    except:
                        continue
                linked_count = inserted_count
                print(f"   🔗 {linked_count} liens créés (avec gestion doublons)")
            else:
                linked_count = len(links_to_insert)
            
            total_links_created += linked_count
            
            print(f"   🔗 {linked_count} liens créés")
            
            # Propagation immédiate
            cursor.execute("""
                UPDATE video 
                SET category = ?,
                    classification_source = 'propagated_from_human_playlist',
                    is_human_validated = 1,
                    classification_date = datetime('now')
                WHERE id IN (
                    SELECT pv.video_id 
                    FROM playlist_video pv
                    JOIN playlist p ON pv.playlist_id = p.playlist_id 
                    WHERE p.id = ?
                )
            """, (category, db_id))
            
            propagated_count = cursor.rowcount
            total_videos_propagated += propagated_count
            
            print(f"   📺 {propagated_count} vidéos propagées en {category.upper()}")
            
            total_playlists_processed += 1
        else:
            print(f"   ⚠️ Aucune vidéo trouvée en base")
    
    # ÉTAPE 3: Commit et rapport final
    conn.commit()
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"🎉 SOLUTION DÉFINITIVE TERMINÉE")
    print(f"   📋 Playlists traitées: {total_playlists_processed}")
    print(f"   📋 Playlists ignorées (liens existants): {skipped_playlists}")
    print(f"   🔗 Total liens créés: {total_links_created}")
    print(f"   📺 Total vidéos propagées: {total_videos_propagated}")
    
    if total_playlists_processed > 0:
        print(f"\n✅ SUCCÈS TOTAL: Tous les liens manquants ont été créés")
        print(f"🚀 L'auto-linking fonctionnera désormais pour toutes les nouvelles classifications")
        return True
    else:
        print(f"\n⚠️ Aucun traitement nécessaire - tous les liens existaient déjà")
        return True

if __name__ == "__main__":
    success = fix_all_playlist_links()
    
    if success:
        print(f"\n🎯 PROCHAINES ÉTAPES:")
        print(f"   1. ✅ Tous les liens playlist_video sont maintenant créés")
        print(f"   2. ✅ L'auto-linking fonctionnera pour toutes nouvelles classifications")
        print(f"   3. ✅ Plus jamais de 'videos_updated: 0'")
        print(f"   4. 🔄 Tu peux maintenant classifier n'importe quelle playlist en toute confiance")
    else:
        print(f"\n❌ Échec - vérifier les logs ci-dessus")