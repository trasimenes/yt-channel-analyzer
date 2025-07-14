#!/usr/bin/env python3
"""
Script pour migrer les données des concurrents depuis le fichier JSON vers la base de données SQLite.
"""

import sys
import os
import json
from datetime import datetime

# Ajouter le chemin du projet au PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importer la fonction correcte depuis le nouveau module
from yt_channel_analyzer.database.videos import save_competitor_and_videos

def migrate_data():
    """Migrer les données depuis le fichier JSON vers la base de données SQLite."""
    json_path = os.path.join(project_root, 'cache_recherches', 'recherches.json')
    
    print("🚀 Début de la migration des données JSON vers la base de données")
    print("="*60)
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Erreur de chargement du JSON: {e}")
        return

    print(f"📖 Chargement des données depuis: {json_path}")
    print(f"📊 {len(data)} concurrents trouvés dans le JSON")

    success_count = 0
    fail_count = 0

    for channel_url, competitor_data in data.items():
        print(f"\n🔄 Traitement de: {competitor_data.get('channel_info', {}).get('title', channel_url)}")
        
        videos = competitor_data.get('videos', [])
        channel_info = competitor_data.get('channel_info', {})
        
        if not videos:
            print("  ⚠️ Aucune vidéo trouvée pour ce concurrent. Ignoré.")
            continue
            
        try:
            # La fonction save_competitor_and_videos gère tout :
            # création/update du concurrent et ajout/update des vidéos.
            competitor_id = save_competitor_and_videos(
                channel_url=channel_url,
                videos=videos,
                channel_info=channel_info
            )
            print(f"  ✅ Concurrent et vidéos sauvegardés avec succès. ID: {competitor_id}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Erreur d'import pour {channel_url}: {e}")
            fail_count += 1

    print("\n" + "="*60)
    print("🎉 Migration terminée!")
    print(f"✅ Concurrents importés avec succès: {success_count}")
    print(f"❌ Concurrents en échec: {fail_count}")

if __name__ == '__main__':
    migrate_data() 