#!/usr/bin/env python3
"""
Script pour mettre à jour la base de données existante avec la nouvelle table d'analytics
sans perdre les données existantes.
"""

import sqlite3
import os
from datetime import datetime

def update_database_for_analytics():
    """Met à jour la base de données pour ajouter la table d'analytics"""
    
    db_path = 'instance/database.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Base de données non trouvée: {db_path}")
        print("Veuillez d'abord créer la base avec create_database.py")
        return False
    
    print(f"🔄 Mise à jour de la base de données: {db_path}")
    
    # Créer une sauvegarde
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"💾 Sauvegarde créée: {backup_path}")
    
    # Connexion à la base
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Vérifier si la table existe déjà
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='competitor_stats_history'
        """)
        
        if cursor.fetchone():
            print("✅ Table competitor_stats_history existe déjà")
        else:
            print("🆕 Création de la table competitor_stats_history...")
            
            # Créer la table pour l'historique des statistiques
            cursor.execute('''
                CREATE TABLE competitor_stats_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurrent_id INTEGER NOT NULL,
                    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    subscriber_count INTEGER,
                    view_count BIGINT,
                    video_count INTEGER,
                    subscriber_change INTEGER DEFAULT 0,
                    view_change BIGINT DEFAULT 0,
                    video_change INTEGER DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (concurrent_id) REFERENCES concurrent (id) ON DELETE CASCADE
                )
            ''')
            
            # Créer les index
            cursor.execute('CREATE INDEX idx_stats_concurrent_id ON competitor_stats_history(concurrent_id)')
            cursor.execute('CREATE INDEX idx_stats_recorded_at ON competitor_stats_history(recorded_at)')
            
            print("✅ Table competitor_stats_history créée avec succès")
        
        # Initialiser l'historique avec les données actuelles
        print("📊 Initialisation de l'historique avec les données actuelles...")
        
        cursor.execute('''
            SELECT id, subscriber_count, view_count, video_count, name
            FROM concurrent
            WHERE subscriber_count IS NOT NULL OR view_count IS NOT NULL
        ''')
        
        competitors = cursor.fetchall()
        initialized_count = 0
        
        for competitor in competitors:
            competitor_id, subscriber_count, view_count, video_count, name = competitor
            
            # Vérifier si on a déjà des données pour ce concurrent
            cursor.execute('''
                SELECT COUNT(*) FROM competitor_stats_history WHERE concurrent_id = ?
            ''', (competitor_id,))
            
            if cursor.fetchone()[0] == 0:
                # Ajouter l'entrée initiale
                cursor.execute('''
                    INSERT INTO competitor_stats_history (
                        concurrent_id, subscriber_count, view_count, video_count,
                        subscriber_change, view_change, video_change, notes
                    ) VALUES (?, ?, ?, ?, 0, 0, 0, ?)
                ''', (
                    competitor_id, subscriber_count, view_count, video_count,
                    'Initialisation - données existantes'
                ))
                
                initialized_count += 1
                print(f"  ✅ Initialisé: {name} ({subscriber_count or 0} subscribers)")
        
        # Valider les changements
        conn.commit()
        
        print(f"\n🎉 Mise à jour terminée avec succès!")
        print(f"   • Table competitor_stats_history créée")
        print(f"   • {initialized_count} concurrents initialisés")
        print(f"   • Sauvegarde disponible: {backup_path}")
        
        # Afficher les statistiques finales
        cursor.execute('SELECT COUNT(*) FROM competitor_stats_history')
        total_entries = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM concurrent')
        total_competitors = cursor.fetchone()[0]
        
        print(f"\n📈 Statistiques finales:")
        print(f"   • {total_competitors} concurrents total")
        print(f"   • {total_entries} entrées dans l'historique")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = update_database_for_analytics()
    if success:
        print(f"\n🚀 Vous pouvez maintenant utiliser les nouvelles fonctionnalités d'analytics!")
        print(f"   • Visitez /analytics pour voir le dashboard")
        print(f"   • Utilisez l'export Excel pour obtenir toutes les données")
    else:
        print(f"\n❌ La mise à jour a échoué. Restaurez depuis la sauvegarde si nécessaire.") 