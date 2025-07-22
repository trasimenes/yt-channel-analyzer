#!/usr/bin/env python3
"""
Script pour télécharger les vignettes manquantes des concurrents
"""

import os
import requests
from yt_channel_analyzer.database import get_db_connection
from urllib.parse import urlparse
import time

def download_missing_thumbnails():
    """Télécharge les vignettes manquantes des concurrents"""
    
    # Répertoire de destination
    thumbnail_dir = 'static/competitors/images/'
    os.makedirs(thumbnail_dir, exist_ok=True)
    
    # Récupérer tous les concurrents avec leurs URLs de vignettes
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, thumbnail_url FROM concurrent WHERE thumbnail_url IS NOT NULL AND thumbnail_url != ?', ('',))
    concurrents = cursor.fetchall()
    
    missing_thumbnails = []
    existing_thumbnails = []
    
    # Vérifier quelles vignettes existent déjà
    for concurrent_id, name, thumbnail_url in concurrents:
        thumbnail_path = os.path.join(thumbnail_dir, f'{concurrent_id}.jpg')
        
        if os.path.exists(thumbnail_path):
            existing_thumbnails.append(concurrent_id)
        else:
            missing_thumbnails.append((concurrent_id, name, thumbnail_url))
    
    print(f'📊 État des vignettes:')
    print(f'✅ Vignettes existantes: {len(existing_thumbnails)}')
    print(f'❌ Vignettes manquantes: {len(missing_thumbnails)}')
    
    if not missing_thumbnails:
        print('🎉 Toutes les vignettes sont déjà téléchargées!')
        conn.close()
        return
    
    print('\n🚀 Téléchargement des vignettes manquantes...')
    
    # Télécharger les vignettes manquantes
    downloaded = 0
    failed = 0
    
    for concurrent_id, name, thumbnail_url in missing_thumbnails:
        print(f'📥 Téléchargement: {name} (ID: {concurrent_id})')
        
        try:
            # Télécharger l'image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(thumbnail_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Sauvegarder l'image
            thumbnail_path = os.path.join(thumbnail_dir, f'{concurrent_id}.jpg')
            
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
            
            print(f'  ✅ Succès: {thumbnail_path}')
            downloaded += 1
            
            # Pause courte pour éviter de surcharger les serveurs
            time.sleep(0.5)
            
        except Exception as e:
            print(f'  ❌ Erreur: {e}')
            failed += 1
    
    print(f'\n📊 Résumé:')
    print(f'✅ Téléchargées: {downloaded}')
    print(f'❌ Échecs: {failed}')
    
    conn.close()

if __name__ == '__main__':
    download_missing_thumbnails()