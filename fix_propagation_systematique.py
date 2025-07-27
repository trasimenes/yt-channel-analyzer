#!/usr/bin/env python3
"""
Script de correction systémique de la propagation playlist → vidéos
SOLUTION GLOBALE pour tous les concurrents
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.hierarchical_classifier import HierarchicalClassifier

def fix_systematic_propagation():
    """
    Correction systémique de la propagation pour TOUS les concurrents
    """
    
    print("🔧 CORRECTION SYSTÉMIQUE PROPAGATION PLAYLIST → VIDÉOS")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ÉTAPE 1: Identifier TOUS les cas de propagation incorrecte
    print("🔍 ÉTAPE 1: Audit global des propagations incorrectes")
    
    cursor.execute("""
        SELECT 
            c.id as competitor_id,
            c.name as competitor_name,
            COUNT(v.id) as affected_videos,
            v.classification_source
        FROM video v
        JOIN concurrent c ON v.concurrent_id = c.id
        WHERE v.classification_source LIKE '%fallback%'
           OR v.classification_source LIKE '%propagated%'
        GROUP BY c.id, c.name, v.classification_source
        ORDER BY affected_videos DESC
    """)
    
    propagation_issues = cursor.fetchall()
    
    if not propagation_issues:
        print("✅ Aucun problème de propagation détecté")
        conn.close()
        return True
    
    print(f"⚠️ Problèmes détectés sur {len(propagation_issues)} cas:")
    for issue in propagation_issues:
        competitor_id, name, count, source = issue
        print(f"  - {name} (ID {competitor_id}): {count} vidéos avec source '{source}'")
    
    # ÉTAPE 2: Nettoyer TOUTES les propagations incorrectes
    print(f"\n🧹 ÉTAPE 2: Nettoyage des propagations incorrectes")
    
    cursor.execute("""
        UPDATE video 
        SET category = NULL,
            classification_source = NULL,
            is_human_validated = 0,
            classification_date = NULL
        WHERE classification_source LIKE '%fallback%'
           OR (classification_source LIKE '%propagated%' 
               AND classification_source NOT LIKE '%human%')
    """)
    
    cleaned_videos = cursor.rowcount
    print(f"🧹 {cleaned_videos} vidéos nettoyées")
    
    # ÉTAPE 3: Identifier les playlists validées humainement
    print(f"\n🥇 ÉTAPE 3: Récupération des playlists validées humainement")
    
    cursor.execute("""
        SELECT 
            p.id,
            p.playlist_id as youtube_id,
            p.name,
            p.category,
            p.concurrent_id,
            c.name as competitor_name,
            p.video_count
        FROM playlist p
        JOIN concurrent c ON p.concurrent_id = c.id
        WHERE (p.human_verified = 1 OR p.classification_source = 'human')
          AND p.category IS NOT NULL
          AND p.category != 'uncategorized'
        ORDER BY c.name, p.name
    """)
    
    human_playlists = cursor.fetchall()
    
    if not human_playlists:
        print("⚠️ Aucune playlist validée humainement trouvée")
        conn.close()
        return False
    
    print(f"🎯 {len(human_playlists)} playlists validées humainement:")
    for playlist in human_playlists:
        playlist_id, youtube_id, name, category, competitor_id, competitor_name, video_count = playlist
        print(f"  - {competitor_name}: {name} → {category.upper()} ({video_count} vidéos)")
    
    # ÉTAPE 4: Propagation intelligente pour chaque playlist humaine
    print(f"\n🔄 ÉTAPE 4: Propagation intelligente et sécurisée")
    
    classifier = HierarchicalClassifier(conn)
    total_videos_updated = 0
    successful_propagations = 0
    
    for playlist in human_playlists:
        playlist_id, youtube_id, name, category, competitor_id, competitor_name, expected_count = playlist
        
        print(f"\n📋 Traitement: {name} ({competitor_name})")
        print(f"   Category: {category.upper()}, Vidéos attendues: {expected_count}")
        
        # Vérifier s'il y a des liens playlist_video
        cursor.execute("""
            SELECT COUNT(*) 
            FROM playlist_video pv
            JOIN playlist p ON pv.playlist_id = p.playlist_id 
            WHERE p.id = ?
        """, (playlist_id,))
        
        existing_links = cursor.fetchone()[0]
        print(f"   Liens existants: {existing_links}")
        
        if existing_links > 0:
            # Propagation normale via les liens existants
            videos_updated = classifier.propagate_playlist_to_videos(
                playlist_id=playlist_id,
                force_human_authority=True
            )
            
            if videos_updated > 0:
                print(f"   ✅ {videos_updated} vidéos propagées via liens existants")
                total_videos_updated += videos_updated
                successful_propagations += 1
            else:
                print(f"   ⚠️ Aucune vidéo propagée (liens invalides?)")
        
        else:
            # PAS de propagation fallback automatique !
            print(f"   ⚠️ Aucun lien playlist_video - PROPAGATION IGNORÉE")
            print(f"   💡 Solution: Utiliser l'API YouTube pour créer les liens corrects")
    
    # ÉTAPE 5: Rapport final
    print(f"\n" + "=" * 80)
    print(f"📊 RAPPORT FINAL")
    print(f"   - Vidéos nettoyées: {cleaned_videos}")
    print(f"   - Playlists humaines trouvées: {len(human_playlists)}")
    print(f"   - Propagations réussies: {successful_propagations}")
    print(f"   - Total vidéos propagées: {total_videos_updated}")
    
    if successful_propagations < len(human_playlists):
        missing = len(human_playlists) - successful_propagations
        print(f"   ⚠️ {missing} playlists nécessitent une liaison API YouTube")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 CORRECTION SYSTÉMIQUE TERMINÉE")
    
    if total_videos_updated > 0:
        print(f"✅ {total_videos_updated} vidéos correctement propagées")
        return True
    else:
        print(f"⚠️ Aucune propagation effectuée - liens manquants")
        return False

if __name__ == "__main__":
    fix_systematic_propagation()