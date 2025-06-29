#!/usr/bin/env python3
"""
Script pour migrer les données des concurrents depuis le fichier JSON vers la base de données SQLite.
"""

import os
import json
import sqlite3
from datetime import datetime
# urllib.parse non nécessaire pour ce script

def extract_channel_id_from_url(channel_url):
    """Extraire l'ID de la chaîne depuis l'URL"""
    try:
        if '/channel/' in channel_url:
            return channel_url.split('/channel/')[-1].split('/')[0].split('?')[0]
        elif '/@' in channel_url:
            # Pour les URLs avec @username, on utilise l'username comme ID temporaire
            return channel_url.split('/@')[-1].split('/')[0].split('?')[0]
        elif '/c/' in channel_url:
            return channel_url.split('/c/')[-1].split('/')[0].split('?')[0]
        elif '/user/' in channel_url:
            return channel_url.split('/user/')[-1].split('/')[0].split('?')[0]
        else:
            # Fallback: utiliser l'URL complète comme ID
            return channel_url.replace('/', '_').replace(':', '_').replace('?', '_')[:100]
    except:
        return f"unknown_{hash(channel_url) % 10000}"

def migrate_data():
    """Migrer les données du JSON vers la base de données"""
    
    # Chemins des fichiers
    json_file = 'cache_recherches/recherches.json'
    db_path = 'instance/database.db'
    
    # Vérifier que les fichiers existent
    if not os.path.exists(json_file):
        print(f"❌ Fichier JSON non trouvé: {json_file}")
        return False
    
    if not os.path.exists(db_path):
        print(f"❌ Base de données non trouvée: {db_path}")
        print("💡 Exécutez d'abord: python3 create_database.py")
        return False
    
    # Charger les données JSON
    print(f"📖 Chargement des données depuis: {json_file}")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lors du chargement du JSON: {e}")
        return False
    
    print(f"📊 {len(json_data)} concurrents trouvés dans le JSON")
    
    # Importer la fonction de sauvegarde
    try:
        from yt_channel_analyzer.database import save_competitor_and_videos
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    
    # Compteurs
    migrated_count = 0
    error_count = 0
    total_videos = 0
    
    # Migrer chaque concurrent
    for json_key, competitor_data in json_data.items():
        try:
            # Extraire les informations du concurrent
            name = competitor_data.get('name', 'Nom inconnu')
            channel_url = competitor_data.get('url', '')  # 'url' dans le JSON
            
            if not channel_url:
                print(f"⚠️  URL manquante pour {name}, ignoré")
                continue
            
            # Préparer les infos de la chaîne
            channel_info = {
                'title': name,
                'thumbnail': '',
                'banner': '',
                'description': '',
                'subscriber_count': None,
                'view_count': None,
                'country': '',
                'language': ''
            }
            
            # Récupérer les vidéos
            videos = competitor_data.get('videos', [])
            
            print(f"📹 Migration de {name} avec {len(videos)} vidéos...")
            
            # Sauvegarder dans la base de données
            competitor_id = save_competitor_and_videos(channel_url, videos, channel_info)
            
            print(f"✅ Migré: {name} (ID {competitor_id}) avec {len(videos)} vidéos")
            migrated_count += 1
            total_videos += len(videos)
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration de {competitor_data.get('name', 'Inconnu')}: {e}")
            error_count += 1
    
    # Vérifier les résultats
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM concurrent')
    total_competitors = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM video')
    total_videos_db = cursor.fetchone()[0]
    
    conn.close()
    
    # Résumé
    print(f"\n📋 Résumé de la migration:")
    print(f"   ✅ Concurrents migrés: {migrated_count}")
    print(f"   📹 Vidéos migrées: {total_videos}")
    print(f"   ❌ Erreurs: {error_count}")
    print(f"   📊 Total en base - Concurrents: {total_competitors}, Vidéos: {total_videos_db}")
    
    if migrated_count > 0:
        print(f"\n🎉 Migration terminée avec succès!")
        
        # Proposer de sauvegarder l'ancien fichier
        backup_file = f"{json_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(json_file, backup_file)
            print(f"💾 Sauvegarde créée: {backup_file}")
        except:
            print("⚠️  Impossible de créer une sauvegarde du fichier JSON")
    
    return migrated_count > 0

def verify_migration():
    """Vérifier que la migration s'est bien passée"""
    db_path = 'instance/database.db'
    
    if not os.path.exists(db_path):
        print("❌ Base de données non trouvée")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Compter les concurrents et vidéos
    cursor.execute('SELECT COUNT(*) FROM concurrent')
    total_concurrent = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM video')
    total_videos = cursor.fetchone()[0]
    
    # Afficher quelques exemples
    cursor.execute('''
        SELECT c.name, c.channel_url, COUNT(v.id) as video_count 
        FROM concurrent c 
        LEFT JOIN video v ON c.id = v.concurrent_id 
        GROUP BY c.id 
        LIMIT 5
    ''')
    examples = cursor.fetchall()
    
    conn.close()
    
    print(f"\n🔍 Vérification de la base de données:")
    print(f"   📊 Nombre total de concurrents: {total_concurrent}")
    print(f"   📹 Nombre total de vidéos: {total_videos}")
    print(f"   📋 Exemples:")
    for name, url, video_count in examples:
        print(f"      - {name}: {video_count} vidéos ({url})")

if __name__ == '__main__':
    print("🚀 Début de la migration des données JSON vers la base de données")
    print("=" * 60)
    
    if migrate_data():
        verify_migration()
    else:
        print("❌ Migration échouée") 