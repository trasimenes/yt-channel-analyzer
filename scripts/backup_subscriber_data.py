#!/usr/bin/env python3
"""
Script de sauvegarde des données d'abonnés
Exporte les données d'abonnés de tous les concurrents en CSV
"""

import csv
import os
from datetime import datetime
from yt_channel_analyzer.database import get_db_connection, get_all_competitors

def backup_subscriber_data():
    """Sauvegarde toutes les données d'abonnés en CSV"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer le dossier de sauvegarde s'il n'existe pas
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"subscriber_data_backup_{timestamp}.csv")
        
        # Récupérer toutes les données d'abonnés avec les noms des concurrents
        cursor.execute('''
            SELECT c.name, c.channel_url, s.date, s.subscriber_count, s.source, s.imported_at
            FROM subscriber_data s
            JOIN concurrent c ON s.concurrent_id = c.id
            ORDER BY c.name, s.date
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ Aucune donnée d'abonnés trouvée à sauvegarder")
            return
        
        # Écrire le fichier CSV
        with open(backup_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            
            # En-têtes
            writer.writerow([
                'Concurrent', 'Channel_URL', 'Date', 'Subscriber_Count', 
                'Source', 'Imported_At'
            ])
            
            # Données
            for row in rows:
                writer.writerow(row)
        
        print(f"✅ Sauvegarde terminée : {len(rows)} entrées sauvegardées")
        print(f"📁 Fichier : {backup_file}")
        
        # Statistiques par concurrent
        cursor.execute('''
            SELECT c.name, COUNT(s.id) as data_count, 
                   MIN(s.date) as first_date, MAX(s.date) as last_date,
                   MIN(s.subscriber_count) as min_subs, MAX(s.subscriber_count) as max_subs
            FROM subscriber_data s
            JOIN concurrent c ON s.concurrent_id = c.id
            GROUP BY c.name
            ORDER BY c.name
        ''')
        
        stats = cursor.fetchall()
        
        print("\n📊 Statistiques par concurrent :")
        for stat in stats:
            name, count, first_date, last_date, min_subs, max_subs = stat
            growth = max_subs - min_subs
            print(f"  🏢 {name}: {count} points de données")
            print(f"     📅 {first_date} → {last_date}")
            print(f"     👥 {min_subs:,} → {max_subs:,} abonnés (+{growth:,})")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")
        return None
    finally:
        conn.close()

def restore_subscriber_data(backup_file):
    """Restaure les données d'abonnés depuis un fichier CSV"""
    
    if not os.path.exists(backup_file):
        print(f"❌ Fichier de sauvegarde introuvable : {backup_file}")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            
            restored_count = 0
            
            for row in reader:
                # Récupérer l'ID du concurrent
                cursor.execute(
                    'SELECT id FROM concurrent WHERE channel_url = ?',
                    (row['Channel_URL'],)
                )
                
                competitor_row = cursor.fetchone()
                if not competitor_row:
                    continue
                
                competitor_id = competitor_row[0]
                
                # Insérer ou ignorer les données
                cursor.execute('''
                    INSERT OR IGNORE INTO subscriber_data 
                    (concurrent_id, date, subscriber_count, source, imported_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    competitor_id,
                    row['Date'],
                    int(row['Subscriber_Count']),
                    row['Source'],
                    row['Imported_At']
                ))
                
                if cursor.rowcount > 0:
                    restored_count += 1
        
        conn.commit()
        print(f"✅ Restauration terminée : {restored_count} nouvelles entrées restaurées")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la restauration : {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Démarrage de la sauvegarde des données d'abonnés...")
    backup_file = backup_subscriber_data()
    
    if backup_file:
        print(f"\n💾 Données sauvegardées avec succès dans : {backup_file}")
        print("   Pour restaurer : python3 backup_subscriber_data.py restore <fichier>")
    else:
        print("\n❌ Échec de la sauvegarde") 