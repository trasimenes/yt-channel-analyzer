#!/usr/bin/env python3
"""
Script de vérification post-corrections pour valider les améliorations apportées.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'instance' / 'database.db'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def validate_fixes():
    """Vérifie que les corrections ont bien été appliquées."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 VALIDATION POST-CORRECTIONS")
    print("=" * 50)
    
    # 1. Vérifier les métriques d'engagement
    print("\n1️⃣ Vérification Métriques d'Engagement:")
    cursor.execute("""
        SELECT COUNT(*) as impossible_engagement
        FROM video 
        WHERE like_count > view_count AND view_count > 0
    """)
    impossible = cursor.fetchone()[0]
    print(f"   ✅ Métriques impossibles (likes > vues): {impossible}")
    
    cursor.execute("""
        SELECT COUNT(*) as zero_views_engagement  
        FROM video 
        WHERE view_count = 0 AND (like_count > 0 OR comment_count > 0)
    """)
    zero_engagement = cursor.fetchone()[0]
    print(f"   ✅ Vidéos 0 vues avec engagement: {zero_engagement}")
    
    # 2. Vérifier les statistiques des concurrents
    print("\n2️⃣ Vérification Statistiques Concurrents:")
    cursor.execute("""
        SELECT COUNT(*) as missing_stats
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        LEFT JOIN competitor_stats cs ON c.id = cs.competitor_id
        WHERE cs.competitor_id IS NULL
        GROUP BY c.id, c.name
        HAVING COUNT(v.id) > 0
    """)
    result = cursor.fetchone()
    missing_stats = result[0] if result else 0
    print(f"   ✅ Concurrents sans statistiques: {missing_stats}")
    
    # 3. Vérifier les comptages de playlists
    print("\n3️⃣ Vérification Comptages Playlists:")
    cursor.execute("""
        SELECT COUNT(*) as discrepancies
        FROM playlist p
        LEFT JOIN playlist_video pv ON p.id = pv.playlist_id
        GROUP BY p.id, p.video_count
        HAVING ABS(p.video_count - COUNT(pv.video_id)) > 0
    """)
    result = cursor.fetchone()
    discrepancies = result[0] if result else 0
    print(f"   ✅ Playlists avec discordances: {discrepancies}")
    
    # 4. Vérifier la qualité générale des données
    print("\n4️⃣ Qualité Générale des Données:")
    
    cursor.execute("SELECT COUNT(*) FROM video WHERE view_count IS NULL OR view_count < 0")
    invalid_views = cursor.fetchone()[0]
    print(f"   ✅ Vues invalides: {invalid_views}")
    
    cursor.execute("SELECT COUNT(*) FROM video WHERE like_count IS NULL OR like_count < 0")
    invalid_likes = cursor.fetchone()[0]
    print(f"   ✅ Likes invalides: {invalid_likes}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM video 
        WHERE (CAST(like_count AS REAL) / NULLIF(view_count, 0)) > 0.20
    """)
    high_engagement = cursor.fetchone()[0]
    print(f"   ✅ Taux d'engagement > 20%: {high_engagement}")
    
    # 5. Stats globales
    print("\n5️⃣ Statistiques Globales:")
    cursor.execute("SELECT COUNT(*) FROM concurrent")
    total_competitors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM video")
    total_videos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM playlist")
    total_playlists = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM competitor_stats")
    competitors_with_stats = cursor.fetchone()[0]
    
    print(f"   📊 Total concurrents: {total_competitors}")
    print(f"   📊 Total vidéos: {total_videos:,}")
    print(f"   📊 Total playlists: {total_playlists}")
    print(f"   📊 Concurrents avec stats: {competitors_with_stats}")
    
    # Calcul du score de qualité
    quality_score = 100
    if impossible > 0:
        quality_score -= 20
    if zero_engagement > 0:
        quality_score -= 15
    if missing_stats > 0:
        quality_score -= 10
    if discrepancies > 5:
        quality_score -= 10
    if high_engagement > 10:
        quality_score -= 5
    
    print(f"\n🏆 SCORE DE QUALITÉ DES DONNÉES: {quality_score}/100")
    
    if quality_score >= 95:
        print("   🌟 EXCELLENT - Données prêtes pour la production")
    elif quality_score >= 85:
        print("   ✅ BON - Qualité acceptable pour les analyses")
    elif quality_score >= 70:
        print("   ⚠️ MOYEN - Corrections supplémentaires recommandées")
    else:
        print("   ❌ FAIBLE - Corrections critiques nécessaires")
    
    conn.close()
    return quality_score

if __name__ == "__main__":
    validate_fixes()