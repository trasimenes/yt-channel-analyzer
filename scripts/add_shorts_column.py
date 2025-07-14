#!/usr/bin/env python3
"""
Script de migration pour ajouter la colonne is_short à la table video
"""

import sqlite3
import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database import get_db_connection

def add_shorts_column():
    """Ajouter la colonne is_short à la table video"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier si la colonne existe déjà
        cursor.execute("PRAGMA table_info(video)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_short' not in columns:
            print("🔄 Ajout de la colonne is_short à la table video...")
            cursor.execute('ALTER TABLE video ADD COLUMN is_short BOOLEAN DEFAULT 0')
            
            # Mettre à jour les vidéos existantes selon leur durée
            print("📊 Mise à jour des vidéos existantes...")
            cursor.execute('''
                UPDATE video 
                SET is_short = 1 
                WHERE duration_seconds <= 60 AND duration_seconds > 0
            ''')
            
            # Compter les shorts détectés
            cursor.execute('SELECT COUNT(*) FROM video WHERE is_short = 1')
            shorts_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM video WHERE is_short = 0')
            regular_count = cursor.fetchone()[0]
            
            conn.commit()
            print(f"✅ Colonne is_short ajoutée avec succès!")
            print(f"📹 {shorts_count} Shorts détectés (≤ 60 secondes)")
            print(f"🎬 {regular_count} vidéos classiques")
            
        else:
            print("ℹ️ La colonne is_short existe déjà")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de la colonne: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_shorts_column() 