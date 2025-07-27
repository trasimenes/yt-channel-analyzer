#!/usr/bin/env python3
"""
Script pour classifier toutes les vidéos ARD Reisen avec le modèle IA avancé
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Dict

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

def get_db_connection():
    """Connexion à la base de données"""
    db_path = Path('instance/database.db')
    return sqlite3.connect(db_path)

def get_ard_videos():
    """Récupérer toutes les vidéos ARD Reisen non classifiées"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, description, view_count, like_count, duration_seconds
        FROM video 
        WHERE concurrent_id = 22 
        AND (category IS NULL OR category = '')
        ORDER BY view_count DESC NULLS LAST
    """)
    
    videos = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'title': row[1] or '',
            'description': row[2] or '',
            'view_count': row[3] or 0,
            'like_count': row[4] or 0,
            'duration_seconds': row[5] or 0
        }
        for row in videos
    ]

def classify_videos_batch(videos: List[Dict], batch_size: int = 10):
    """Classifier les vidéos par batch"""
    from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier
    
    print(f"🧠 Initialisation du modèle IA AdvancedSemanticClassifier...")
    classifier = AdvancedSemanticClassifier()
    
    results = []
    total = len(videos)
    
    print(f"🎯 Classification de {total} vidéos ARD Reisen...")
    print("=" * 80)
    
    for i in range(0, total, batch_size):
        batch = videos[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} vidéos)")
        
        for j, video in enumerate(batch):
            try:
                # Classification avec le modèle IA
                category, confidence, details = classifier.classify_text(
                    video['title'], 
                    video['description'][:200]  # Limiter la description
                )
                
                result = {
                    'video_id': video['id'],
                    'title': video['title'],
                    'category': category,
                    'confidence': confidence,
                    'view_count': video['view_count']
                }
                results.append(result)
                
                # Affichage progressif
                progress = f"[{i+j+1:3d}/{total}]"
                title_short = video['title'][:50] + "..." if len(video['title']) > 50 else video['title']
                views = f"{video['view_count']:,}" if video['view_count'] else "0"
                
                print(f"  {progress} {category.upper():4} ({confidence:.2f}) {views:>8} vues: {title_short}")
                
            except Exception as e:
                print(f"  ❌ Erreur pour '{video['title'][:30]}...': {e}")
                continue
        
        # Sauvegarder chaque batch pour voir la progression
        if results:
            print(f"  💾 Sauvegarde du batch {batch_num}...")
            save_classifications(results[-len(batch):])  # Sauvegarder seulement ce batch
    
    return results

def save_classifications(results: List[Dict]):
    """Sauvegarder les classifications dans la base de données"""
    if not results:
        print("❌ Aucun résultat à sauvegarder")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"\n💾 Sauvegarde de {len(results)} classifications...")
    
    # Mettre à jour les vidéos avec les classifications
    updated = 0
    for result in results:
        try:
            cursor.execute("""
                UPDATE video 
                SET category = ?, 
                    classification_source = 'semantic',
                    classification_date = datetime('now'),
                    classification_confidence = ?
                WHERE id = ?
            """, (
                result['category'],
                result['confidence'],
                result['video_id']
            ))
            updated += 1
        except Exception as e:
            print(f"❌ Erreur sauvegarde vidéo {result['video_id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ {updated} vidéos mises à jour avec succès")
    return updated

def print_classification_summary(results: List[Dict]):
    """Afficher un résumé des classifications"""
    if not results:
        return
    
    # Compter par catégorie
    category_counts = {}
    total_views = {}
    
    for result in results:
        category = result['category'].upper()
        views = result['view_count'] or 0
        
        category_counts[category] = category_counts.get(category, 0) + 1
        total_views[category] = total_views.get(category, 0) + views
    
    total_videos = len(results)
    
    print(f"\n📊 RÉSUMÉ DES CLASSIFICATIONS ARD REISEN")
    print("=" * 60)
    
    for category in ['HERO', 'HUB', 'HELP']:
        count = category_counts.get(category, 0)
        percentage = (count / total_videos * 100) if total_videos > 0 else 0
        views = total_views.get(category, 0)
        avg_views = views // count if count > 0 else 0
        
        print(f"{category:4}: {count:3d} vidéos ({percentage:5.1f}%) - {views:,} vues totales - {avg_views:,} vues/vidéo")
    
    print(f"\nTOTAL: {total_videos} vidéos classifiées")

def main():
    """Fonction principale"""
    print("🚀 Classification automatique ARD Reisen avec IA sémantique")
    print("🤖 Modèle: all-mpnet-base-v2 (420MB, 768 dimensions)")
    print()
    
    # Récupérer les vidéos
    videos = get_ard_videos()
    if not videos:
        print("✅ Toutes les vidéos ARD Reisen sont déjà classifiées")
        return
    
    print(f"📹 {len(videos)} vidéos à classifier")
    
    # Classifier
    results = classify_videos_batch(videos)
    
    if not results:
        print("❌ Aucune classification réussie")
        return
    
    # Sauvegarder
    updated = save_classifications(results)
    
    if updated > 0:
        # Afficher le résumé
        print_classification_summary(results)
        print(f"\n🎉 Classification terminée ! {updated} vidéos ARD Reisen classifiées.")
        print("💡 Vous pouvez maintenant voir les résultats dans l'interface web.")
    else:
        print("❌ Aucune sauvegarde réussie")

if __name__ == "__main__":
    main()