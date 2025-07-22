#!/usr/bin/env python3
import os
import requests
from googleapiclient.discovery import build
from yt_channel_analyzer.database.base import get_db_connection

# Clé API depuis .env
API_KEY = "AIzaSyCKYHty6Zl_wjCXBFVLSU2u5c8sNhgBbxk"

# Construire le service YouTube
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Récupérer les infos de la chaîne centerparcsde
response = youtube.channels().list(
    part='snippet',
    forUsername='centerparcsde'
).execute()

if response['items']:
    channel = response['items'][0]
    channel_id = channel['id']
    channel_title = channel['snippet']['title']
    channel_thumbnail = channel['snippet']['thumbnails']['high']['url']
    
    print(f"✅ Trouvé : {channel_title}")
    print(f"   ID: {channel_id}")
    print(f"   Thumbnail: {channel_thumbnail}")
    
    # Télécharger et sauvegarder la miniature
    response_img = requests.get(channel_thumbnail)
    if response_img.status_code == 200:
        image_path = "static/competitors/images/122.jpg"
        with open(image_path, 'wb') as f:
            f.write(response_img.content)
        print(f"✅ Miniature sauvegardée dans {image_path}")
    
    # Mettre à jour la base de données
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE concurrent 
        SET name = ?, channel_id = ?
        WHERE id = 122
    """, (channel_title, channel_id))
    
    conn.commit()
    conn.close()
    
    print("✅ Base de données mise à jour")
else:
    print("❌ Chaîne non trouvée")