#!/usr/bin/env python3
"""
Script pour optimiser la base de données SQLite
- Ajouter des index de performance
- Appliquer les optimisations SQLite
- Analyser les performances
"""

import sys
import os
import time
from pathlib import Path

# Ajouter le chemin du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from yt_channel_analyzer.database.base import get_db_connection, create_performance_indexes

def analyze_database_performance():
    """Analyser les performances de la base de données"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 Analyse des performances de la base de données...")
    
    try:
        # Analyser la taille de la base
        cursor.execute("SELECT COUNT(*) FROM video")
        video_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        competitor_count = cursor.fetchone()[0]
        
        print(f"📊 Statistiques de la base:")
        print(f"   - Vidéos: {video_count:,}")
        print(f"   - Concurrents: {competitor_count:,}")
        
        # Tester les performances d'une requête complexe
        start_time = time.time()
        cursor.execute("""
            SELECT v.title, v.view_count, c.name
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            ORDER BY v.view_count DESC
            LIMIT 100
        """)
        results = cursor.fetchall()
        end_time = time.time()
        
        print(f"⏱️  Temps de requête TOP 100: {end_time - start_time:.3f}s")
        
        # Analyser les index existants
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"📋 Index existants: {len(indexes)}")
        
        for index in indexes:
            if index.startswith('idx_'):
                print(f"   - {index}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
    finally:
        conn.close()

def optimize_database():
    """Optimiser la base de données"""
    print("🚀 Optimisation de la base de données...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer les index de performance
        print("📈 Création des index de performance...")
        create_performance_indexes(cursor)
        
        # Analyser les tables pour optimiser le query planner
        print("🔧 Analyse des tables pour optimiser le query planner...")
        cursor.execute("ANALYZE")
        
        # Vacuum pour défragmenter la base
        print("🧹 Nettoyage et défragmentation...")
        cursor.execute("VACUUM")
        
        conn.commit()
        print("✅ Optimisation terminée avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Fonction principale"""
    print("=" * 60)
    print("🏃‍♂️ OPTIMISATION DE LA BASE DE DONNÉES YT ANALYZER")
    print("=" * 60)
    
    # Analyser avant optimisation
    print("\n1️⃣ ANALYSE AVANT OPTIMISATION:")
    analyze_database_performance()
    
    # Optimiser
    print("\n2️⃣ OPTIMISATION:")
    optimize_database()
    
    # Analyser après optimisation
    print("\n3️⃣ ANALYSE APRÈS OPTIMISATION:")
    analyze_database_performance()
    
    print("\n🎉 Optimisation terminée!")
    print("💡 Redémarrez l'application pour profiter des améliorations.")

if __name__ == "__main__":
    main() 