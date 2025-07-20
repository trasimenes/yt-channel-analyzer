#!/usr/bin/env python3
"""
Script pour télécharger toutes les miniatures des concurrents en local
"""

import os
import sqlite3
import requests
from urllib.parse import urlparse

def download_all_thumbnails():
    """Télécharger toutes les miniatures des concurrents"""
    print("🚀 Démarrage du téléchargement des miniatures...")
    
    # Créer le dossier de destination
    os.makedirs("static/competitors/images", exist_ok=True)
    
    # Vérifier si la colonne local_thumbnail_path existe
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT local_thumbnail_path FROM concurrent LIMIT 1")
        print("📝 Colonne local_thumbnail_path déjà existante")
    except sqlite3.OperationalError:
        print("📝 Ajout de la colonne local_thumbnail_path...")
        cursor.execute("ALTER TABLE concurrent ADD COLUMN local_thumbnail_path TEXT")
        conn.commit()
    
    # Récupérer tous les concurrents avec miniatures
    cursor.execute("""
        SELECT id, name, thumbnail_url, local_thumbnail_path 
        FROM concurrent 
        WHERE thumbnail_url IS NOT NULL AND thumbnail_url != ''
        ORDER BY id
    """)
    
    competitors = cursor.fetchall()
    print(f"📊 {len(competitors)} concurrents avec miniatures trouvés")
    
    downloaded = 0
    failed = 0
    
    for competitor_id, name, thumbnail_url, local_path in competitors:
        try:
            local_filename = f"static/competitors/images/{competitor_id}.jpg"
            
            # Vérifier si déjà téléchargé
            if os.path.exists(local_filename):
                print(f"✅ Miniature déjà téléchargée pour {name} (ID: {competitor_id})")
                # Mettre à jour le chemin en base si nécessaire
                if not local_path:
                    cursor.execute(
                        "UPDATE concurrent SET local_thumbnail_path = ? WHERE id = ?",
                        (local_filename, competitor_id)
                    )
                continue
            
            # Télécharger la miniature
            print(f"📥 Téléchargement: {name} (ID: {competitor_id})")
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            # Sauvegarder localement
            with open(local_filename, 'wb') as f:
                f.write(response.content)
            
            # Mettre à jour la base de données
            cursor.execute("""
                UPDATE concurrent 
                SET local_thumbnail_path = ? 
                WHERE id = ?
            """, (local_filename, competitor_id))
            
            downloaded += 1
            print(f"✅ {name} téléchargé")
            
        except Exception as e:
            print(f"❌ Erreur pour {name}: {e}")
            failed += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✨ Terminé!")
    print(f"✅ {downloaded} miniatures téléchargées")
    print(f"❌ {failed} échecs")
    print(f"📁 Miniatures stockées dans: static/competitors/images")

if __name__ == "__main__":
    download_all_thumbnails()