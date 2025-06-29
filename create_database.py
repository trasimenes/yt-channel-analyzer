#!/usr/bin/env python3
"""
Script pour créer la base de données SQLite et les tables nécessaires.
"""

import os
import sqlite3
from datetime import datetime

def create_database():
    """Créer la base de données et les tables"""
    
    # S'assurer que le dossier instance existe
    os.makedirs('instance', exist_ok=True)
    
    # Chemin vers la base de données
    db_path = 'instance/database.db'
    
    # Supprimer l'ancienne base si elle existe (pour un nouveau départ)
    if os.path.exists(db_path):
        print(f"Suppression de l'ancienne base de données: {db_path}")
        os.remove(db_path)
    
    # Créer la connexion
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Création de la base de données: {db_path}")
    
    # Créer la table Concurrent
    cursor.execute('''
        CREATE TABLE concurrent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            channel_id VARCHAR(100) UNIQUE NOT NULL,
            channel_url VARCHAR(200) UNIQUE NOT NULL,
            thumbnail_url VARCHAR(200),
            banner_url VARCHAR(200),
            description TEXT,
            subscriber_count INTEGER,
            view_count BIGINT,
            video_count INTEGER,
            country VARCHAR(50),
            language VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer la table Video
    cursor.execute('''
        CREATE TABLE video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concurrent_id INTEGER NOT NULL,
            video_id VARCHAR(50) UNIQUE NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            url VARCHAR(200) NOT NULL,
            thumbnail_url VARCHAR(200),
            published_at DATETIME,
            duration_seconds INTEGER,
            duration_text VARCHAR(20),
            view_count BIGINT,
            like_count INTEGER,
            comment_count INTEGER,
            category VARCHAR(50),
            tags TEXT,
            beauty_score INTEGER,
            emotion_score INTEGER,
            info_quality_score INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (concurrent_id) REFERENCES concurrent (id) ON DELETE CASCADE
        )
    ''')
    
    # Créer des index pour améliorer les performances
    cursor.execute('CREATE INDEX idx_concurrent_channel_id ON concurrent(channel_id)')
    cursor.execute('CREATE INDEX idx_concurrent_channel_url ON concurrent(channel_url)')
    cursor.execute('CREATE INDEX idx_video_concurrent_id ON video(concurrent_id)')
    cursor.execute('CREATE INDEX idx_video_video_id ON video(video_id)')
    cursor.execute('CREATE INDEX idx_video_published_at ON video(published_at)')
    cursor.execute('CREATE INDEX idx_video_view_count ON video(view_count)')
    
    # Sauvegarder les changements
    conn.commit()
    
    print("✅ Tables créées avec succès:")
    print("   - concurrent (concurrents/chaînes YouTube)")
    print("   - video (vidéos des chaînes)")
    print("   - Index créés pour optimiser les performances")
    
    # Vérifier que les tables ont été créées
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n📋 Tables dans la base de données:")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Fermer la connexion
    conn.close()
    
    print(f"\n🎉 Base de données créée avec succès: {db_path}")
    return db_path

if __name__ == '__main__':
    create_database() 