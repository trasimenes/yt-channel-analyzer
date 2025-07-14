#!/usr/bin/env python3
"""
Script pour corriger les erreurs sémantiques et optimiser le système
- Crée la table custom_classification_rules manquante
- Optimise la classification pour ne pas initialiser le sentence transformer à chaque fois
- Ajoute un mode "base seulement" pour le quotidien
"""

import sqlite3
import sys
import os
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database import get_db_connection

def create_missing_table():
    """Créer la table custom_classification_rules manquante"""
    print("🔧 Création de la table custom_classification_rules...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer la table avec la structure attendue
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_classification_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                language TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern, category, language)
            )
        ''')
        
        # Migrer les données de custom_rules vers custom_classification_rules si elle existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_rules'")
        if cursor.fetchone():
            print("📦 Migration des données de custom_rules vers custom_classification_rules...")
            cursor.execute('''
                INSERT OR IGNORE INTO custom_classification_rules (pattern, category, language, created_at)
                SELECT pattern, category, language, created_at FROM custom_rules
            ''')
        
        conn.commit()
        print("✅ Table custom_classification_rules créée avec succès")
        
        # Vérifier le contenu
        cursor.execute("SELECT COUNT(*) FROM custom_classification_rules")
        count = cursor.fetchone()[0]
        print(f"📊 {count} règles personnalisées dans la table")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de la création de la table: {e}")
        return False
    finally:
        conn.close()
    
    return True

def add_semantic_settings():
    """Ajouter les paramètres sémantiques à la table settings"""
    print("⚙️  Ajout des paramètres sémantiques...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer la table settings si elle n'existe pas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ajouter les paramètres sémantiques avec des valeurs par défaut
        settings = [
            ('semantic_classification_enabled', 'false'),  # Désactivé par défaut
            ('semantic_auto_init', 'false'),  # Pas d'initialisation automatique
            ('semantic_model', 'all-MiniLM-L6-v2'),  # Modèle par défaut
            ('semantic_weight', '0.7'),  # Poids du sémantique
            ('pattern_weight', '0.3'),  # Poids des patterns
            ('classification_mode', 'database_only'),  # Mode par défaut : base uniquement
        ]
        
        for key, value in settings:
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        print("✅ Paramètres sémantiques ajoutés")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'ajout des paramètres: {e}")
        return False
    finally:
        conn.close()
    
    return True

def optimize_database():
    """Optimiser la base de données"""
    print("🚀 Optimisation de la base de données...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Créer des index pour accélérer les requêtes de classification
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_video_category ON video (category)",
            "CREATE INDEX IF NOT EXISTS idx_video_classification_source ON video (classification_source)",
            "CREATE INDEX IF NOT EXISTS idx_video_human_verified ON video (human_verified)",
            "CREATE INDEX IF NOT EXISTS idx_custom_rules_category ON custom_classification_rules (category)",
            "CREATE INDEX IF NOT EXISTS idx_custom_rules_language ON custom_classification_rules (language)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Analyser la base pour optimiser les requêtes
        cursor.execute("ANALYZE")
        
        conn.commit()
        print("✅ Base de données optimisée")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'optimisation: {e}")
        return False
    finally:
        conn.close()
    
    return True

def show_classification_stats():
    """Afficher les statistiques de classification"""
    print("📊 Statistiques de classification...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video WHERE category IS NOT NULL")
        classified_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video WHERE human_verified = 1")
        human_verified = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM custom_classification_rules")
        custom_rules = cursor.fetchone()[0]
        
        # Statistiques par catégorie
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM video 
            WHERE category IS NOT NULL
            GROUP BY category
        ''')
        categories = cursor.fetchall()
        
        print(f"📈 Total vidéos: {total_videos}")
        print(f"📈 Vidéos classifiées: {classified_videos} ({classified_videos/total_videos*100:.1f}%)")
        print(f"📈 Vérifications humaines: {human_verified}")
        print(f"📈 Règles personnalisées: {custom_rules}")
        
        print("\n📊 Répartition par catégorie:")
        for category, count in categories:
            print(f"  {category.upper()}: {count} vidéos")
        
    except Exception as e:
        print(f"❌ Erreur lors du calcul des statistiques: {e}")
    finally:
        conn.close()

def main():
    """Fonction principale"""
    print("🔧 OPTIMISATION DU SYSTÈME SÉMANTIQUE")
    print("=" * 50)
    
    # Étape 1: Créer la table manquante
    if not create_missing_table():
        print("❌ Échec de la création de la table")
        return False
    
    # Étape 2: Ajouter les paramètres sémantiques
    if not add_semantic_settings():
        print("❌ Échec de l'ajout des paramètres")
        return False
    
    # Étape 3: Optimiser la base
    if not optimize_database():
        print("❌ Échec de l'optimisation")
        return False
    
    # Étape 4: Afficher les statistiques
    show_classification_stats()
    
    print("\n🎉 OPTIMISATION TERMINÉE !")
    print("💡 Le système est maintenant configuré pour :")
    print("  - Utiliser les classifications déjà en base au quotidien")
    print("  - Ne pas initialiser le sentence transformer automatiquement")
    print("  - Permettre l'activation sémantique à la demande")
    print("  - Accélérer les requêtes de classification")
    
    return True

if __name__ == "__main__":
    main() 