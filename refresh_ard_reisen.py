#!/usr/bin/env python3
"""
Script pour rafraîchir les playlists d'ARD Reisen
"""

import sqlite3
from pathlib import Path
import sys
import os

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

def get_db_connection():
    """Connexion à la base de données"""
    db_path = Path('instance/database.db')
    return sqlite3.connect(db_path)

def get_youtube_client():
    """Créer le client YouTube API"""
    try:
        from yt_channel_analyzer.database import get_db_connection as get_main_db
        
        conn = get_main_db()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM app_config WHERE key = "youtube_api_key"')
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print("❌ Clé API YouTube non trouvée dans la base de données")
            return None
            
        api_key = result[0]
        
        from googleapiclient.discovery import build
        return build('youtube', 'v3', developerKey=api_key)
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du client YouTube: {e}")
        return None

def get_channel_playlists(youtube_client, channel_id):
    """Récupérer toutes les playlists d'une chaîne"""
    try:
        playlists = []
        next_page_token = None
        
        while True:
            request = youtube_client.playlists().list(
                part='snippet,contentDetails',
                channelId=channel_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response['items']:
                playlist_info = {
                    'playlist_id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet'].get('description', ''),
                    'thumbnail_url': item['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                    'video_count': item['contentDetails']['itemCount']
                }
                playlists.append(playlist_info)
                print(f"📋 Trouvé: {playlist_info['title']} ({playlist_info['video_count']} vidéos)")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        return playlists
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des playlists: {e}")
        return []

def save_playlists_to_db(playlists, competitor_id):
    """Sauvegarder les playlists dans la base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Supprimer les anciennes playlists (sauf "All Videos")
        cursor.execute('''
            DELETE FROM playlist 
            WHERE concurrent_id = ? AND name != 'All Videos - ARD Reisen'
        ''', (competitor_id,))
        
        # Insérer les nouvelles playlists
        for playlist in playlists:
            cursor.execute('''
                INSERT OR REPLACE INTO playlist 
                (concurrent_id, playlist_id, name, description, thumbnail_url, video_count, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                competitor_id,
                playlist['playlist_id'],
                playlist['title'],
                playlist['description'],
                playlist['thumbnail_url'],
                playlist['video_count']
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ {len(playlists)} playlists sauvegardées dans la base de données")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Démarrage du refresh des playlists ARD Reisen...")
    
    # Informations ARD Reisen
    competitor_id = 22
    channel_id = "UC2kuG2O3pr60xmclc2c6b4g"
    
    # Créer le client YouTube
    youtube_client = get_youtube_client()
    if not youtube_client:
        return
    
    # Récupérer les playlists
    print(f"📡 Récupération des playlists pour ARD Reisen (ID: {channel_id})...")
    playlists = get_channel_playlists(youtube_client, channel_id)
    
    if not playlists:
        print("❌ Aucune playlist trouvée")
        return
    
    print(f"📊 {len(playlists)} playlists trouvées")
    
    # Sauvegarder dans la base de données
    if save_playlists_to_db(playlists, competitor_id):
        print("🎉 Refresh terminé avec succès!")
        
        # Afficher un résumé
        print("\n📋 Résumé des playlists:")
        for playlist in sorted(playlists, key=lambda x: x['video_count'], reverse=True):
            print(f"  • {playlist['title']}: {playlist['video_count']} vidéos")
    else:
        print("❌ Erreur lors de la sauvegarde")

if __name__ == "__main__":
    main()