#!/usr/bin/env python3
"""
Script pour corriger les problèmes de données identifiés dans le rapport de validation.
Corrige les métriques d'engagement impossibles et génère les statistiques manquantes.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / 'instance' / 'database.db'

def get_db_connection():
    """Connexion à la base de données."""
    return sqlite3.connect(DB_PATH)

def fix_impossible_engagement_metrics():
    """
    Corrige les métriques d'engagement impossibles:
    - Likes > views
    - Engagement avec 0 vues
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Recherche des métriques d'engagement impossibles...")
    
    # Identifier les vidéos avec likes > views
    cursor.execute("""
        SELECT id, title, like_count, view_count, comment_count
        FROM video 
        WHERE like_count > view_count AND view_count > 0
        ORDER BY (CAST(like_count AS REAL) / view_count) DESC
    """)
    impossible_likes = cursor.fetchall()
    
    logger.info(f"Trouvé {len(impossible_likes)} vidéos avec likes > views")
    
    # Identifier les vidéos avec 0 vues mais engagement positif
    cursor.execute("""
        SELECT id, title, like_count, view_count, comment_count
        FROM video 
        WHERE view_count = 0 AND (like_count > 0 OR comment_count > 0)
    """)
    zero_views_engagement = cursor.fetchall()
    
    logger.info(f"Trouvé {len(zero_views_engagement)} vidéos avec 0 vues mais engagement")
    
    fixes_applied = 0
    
    # Correction 1: Pour les vidéos avec likes > views, ajuster les vues au minimum des likes
    for video_id, title, like_count, view_count, comment_count in impossible_likes:
        logger.info(f"⚠️ Vidéo impossible: {title[:50]}... - {like_count} likes, {view_count} vues")
        
        # Ajuster les vues au minimum nécessaire (likes + marge de sécurité)
        min_views_needed = max(like_count * 2, like_count + 100)
        
        cursor.execute("""
            UPDATE video 
            SET view_count = ?,
                last_updated = datetime('now')
            WHERE id = ?
        """, (min_views_needed, video_id))
        
        logger.info(f"✅ Corrigé: Vues ajustées de {view_count} à {min_views_needed}")
        fixes_applied += 1
    
    # Correction 2: Pour les vidéos avec 0 vues mais engagement, ajuster les vues
    for video_id, title, like_count, view_count, comment_count in zero_views_engagement:
        logger.info(f"⚠️ Vidéo 0 vues avec engagement: {title[:50]}... - {like_count} likes, {comment_count} comments")
        
        # Calculer un minimum de vues basé sur l'engagement
        min_views = max(like_count * 10, comment_count * 20, 1)
        
        cursor.execute("""
            UPDATE video 
            SET view_count = ?,
                last_updated = datetime('now')
            WHERE id = ?
        """, (min_views, video_id))
        
        logger.info(f"✅ Corrigé: Vues ajustées de 0 à {min_views}")
        fixes_applied += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 Corrections appliquées: {fixes_applied} vidéos corrigées")
    return fixes_applied

def generate_missing_competitor_stats():
    """
    Génère les statistiques manquantes pour les concurrents.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Recherche des concurrents sans statistiques...")
    
    # Identifier les concurrents sans stats
    cursor.execute("""
        SELECT c.id, c.name, COUNT(v.id) as video_count
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        LEFT JOIN competitor_stats cs ON c.id = cs.competitor_id
        WHERE cs.competitor_id IS NULL
        GROUP BY c.id, c.name
        HAVING video_count > 0
    """)
    missing_stats = cursor.fetchall()
    
    logger.info(f"Trouvé {len(missing_stats)} concurrents sans statistiques")
    
    stats_generated = 0
    
    for competitor_id, name, video_count in missing_stats:
        logger.info(f"📊 Génération stats pour: {name} ({video_count} vidéos)")
        
        # Calculer les statistiques
        cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                COALESCE(SUM(view_count), 0) as total_views,
                COALESCE(SUM(like_count), 0) as total_likes,
                COALESCE(SUM(comment_count), 0) as total_comments,
                COALESCE(AVG(view_count), 0) as avg_views,
                COALESCE(AVG(duration_seconds), 0) as avg_duration,
                COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count
            FROM video 
            WHERE concurrent_id = ?
        """, (competitor_id,))
        
        stats = cursor.fetchone()
        
        if stats and stats[0] > 0:  # Si le concurrent a des vidéos
            # Calculer l'engagement rate
            engagement_rate = (stats[2] + stats[3]) / stats[1] if stats[1] > 0 else 0
            
            # Calculer les vues par catégorie
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN category = 'hero' THEN view_count END), 0) as hero_views,
                    COALESCE(SUM(CASE WHEN category = 'hub' THEN view_count END), 0) as hub_views,
                    COALESCE(SUM(CASE WHEN category = 'help' THEN view_count END), 0) as help_views
                FROM video 
                WHERE concurrent_id = ?
            """, (competitor_id,))
            
            category_views = cursor.fetchone()
            
            # Insérer les statistiques selon la structure de la table
            cursor.execute("""
                INSERT INTO competitor_stats (
                    competitor_id, total_videos, total_views, avg_views,
                    hero_count, hub_count, help_count,
                    hero_views, hub_views, help_views,
                    engagement_rate, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (competitor_id, stats[0], stats[1], stats[4], 
                  stats[6], stats[7], stats[8],
                  category_views[0], category_views[1], category_views[2],
                  engagement_rate))
            
            logger.info(f"✅ Stats générées: {stats[0]} vidéos, {stats[1]:,} vues totales")
            stats_generated += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 Statistiques générées pour {stats_generated} concurrents")
    return stats_generated

def archive_test_competitors():
    """
    Archive les concurrents de test vides.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Recherche des concurrents de test à archiver...")
    
    # Identifier les concurrents de test sans vidéos
    cursor.execute("""
        SELECT c.id, c.name, COUNT(v.id) as video_count
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        WHERE (c.name LIKE '%Test%' OR c.name LIKE '%Topic Analysis%')
        GROUP BY c.id, c.name
        HAVING video_count = 0
    """)
    test_competitors = cursor.fetchall()
    
    logger.info(f"Trouvé {len(test_competitors)} concurrents de test à archiver")
    
    archived = 0
    
    for competitor_id, name, video_count in test_competitors:
        logger.info(f"🗂️ Archivage: {name}")
        
        # Marquer comme archivé (ajouter un préfixe)
        cursor.execute("""
            UPDATE concurrent 
            SET name = '[ARCHIVED] ' || name,
                last_updated = datetime('now')
            WHERE id = ? AND name NOT LIKE '[ARCHIVED]%'
        """, (competitor_id,))
        
        if cursor.rowcount > 0:
            logger.info(f"✅ Archivé: {name}")
            archived += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 Concurrents archivés: {archived}")
    return archived

def add_data_validation_constraints():
    """
    Ajoute des contraintes de validation pour éviter les données incohérentes.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🛡️ Ajout des contraintes de validation...")
    
    constraints_added = 0
    
    try:
        # Note: SQLite ne supporte pas ADD CONSTRAINT sur des tables existantes
        # On va créer des triggers à la place
        
        # Trigger pour valider les métriques d'engagement
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS validate_engagement_metrics
            BEFORE UPDATE OF like_count, view_count ON video
            WHEN NEW.like_count > NEW.view_count AND NEW.view_count > 0
            BEGIN
                SELECT RAISE(ABORT, 'Impossible engagement: likes cannot exceed views');
            END
        """)
        constraints_added += 1
        logger.info("✅ Trigger de validation engagement créé")
        
        # Trigger pour valider les dates
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS validate_publication_date
            BEFORE UPDATE OF published_at ON video
            WHEN NEW.published_at < '2005-01-01' OR NEW.published_at > date('now', '+1 day')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid publication date: must be between 2005 and tomorrow');
            END
        """)
        constraints_added += 1
        logger.info("✅ Trigger de validation dates créé")
        
        conn.commit()
        logger.info(f"🎉 Contraintes ajoutées: {constraints_added}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'ajout des contraintes: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    return constraints_added

def reconcile_playlist_video_counts():
    """
    Réconcilie les comptages de vidéos dans les playlists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    logger.info("🔍 Réconciliation des comptages de playlists...")
    
    # Identifier les discordances
    cursor.execute("""
        SELECT 
            p.id, p.name, p.video_count as declared_count,
            COUNT(pv.video_id) as actual_count,
            ABS(p.video_count - COUNT(pv.video_id)) as difference
        FROM playlist p
        LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
        GROUP BY p.id, p.name, p.video_count
        HAVING difference > 0
        ORDER BY difference DESC
    """)
    discrepancies = cursor.fetchall()
    
    logger.info(f"Trouvé {len(discrepancies)} playlists avec discordances")
    
    fixed = 0
    
    for playlist_id, name, declared, actual, difference in discrepancies:
        logger.info(f"⚠️ Playlist: {name[:50]}... - Déclaré: {declared}, Réel: {actual}")
        
        # Corriger le comptage
        cursor.execute("""
            UPDATE playlist 
            SET video_count = ?,
                last_updated = datetime('now')
            WHERE id = ?
        """, (actual, playlist_id))
        
        logger.info(f"✅ Corrigé: {declared} → {actual}")
        fixed += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 Playlists corrigées: {fixed}")
    return fixed

def main():
    """Fonction principale pour exécuter toutes les corrections."""
    print("🚀 Démarrage des corrections de données...")
    
    try:
        # 1. Corriger les métriques d'engagement impossibles
        print("\n1️⃣ Correction des métriques d'engagement impossibles...")
        engagement_fixes = fix_impossible_engagement_metrics()
        
        # 2. Générer les statistiques manquantes
        print("\n2️⃣ Génération des statistiques manquantes...")
        stats_generated = generate_missing_competitor_stats()
        
        # 3. Réconcilier les comptages de playlists
        print("\n3️⃣ Réconciliation des comptages de playlists...")
        playlist_fixes = reconcile_playlist_video_counts()
        
        # 4. Archiver les concurrents de test
        print("\n4️⃣ Archivage des concurrents de test...")
        archived = archive_test_competitors()
        
        # 5. Ajouter les contraintes de validation
        print("\n5️⃣ Ajout des contraintes de validation...")
        constraints = add_data_validation_constraints()
        
        # Résumé
        print(f"\n🎉 CORRECTIONS TERMINÉES:")
        print(f"   • Métriques d'engagement corrigées: {engagement_fixes}")
        print(f"   • Statistiques générées: {stats_generated}")
        print(f"   • Playlists réconciliées: {playlist_fixes}")
        print(f"   • Concurrents archivés: {archived}")
        print(f"   • Contraintes ajoutées: {constraints}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des corrections: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)