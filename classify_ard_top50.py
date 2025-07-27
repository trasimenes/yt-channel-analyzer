#!/usr/bin/env python3
"""
Script pour classifier les 50 premières vidéos ARD Reisen avec le modèle IA avancé
"""

import sqlite3
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

def get_db_connection():
    """Connexion à la base de données"""
    db_path = Path('instance/database.db')
    return sqlite3.connect(db_path)

def classify_top50_videos():
    """Classifier les 50 premières vidéos ARD Reisen par vues"""
    from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier
    
    print("🚀 Classification des TOP 50 vidéos ARD Reisen")
    print("🤖 Modèle: all-mpnet-base-v2 (420MB, 768 dimensions)")
    print("=" * 60)
    
    # Récupérer les 50 premières vidéos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, description, view_count
        FROM video 
        WHERE concurrent_id = 22 
        ORDER BY view_count DESC NULLS LAST
        LIMIT 50
    """)
    
    videos = cursor.fetchall()
    
    if not videos:
        print("❌ Aucune vidéo trouvée")
        return
    
    print(f"📹 {len(videos)} vidéos à classifier")
    print()
    
    # Initialiser le classificateur
    print("🧠 Initialisation du modèle IA...")
    classifier = AdvancedSemanticClassifier()
    print()
    
    # Classifier et sauvegarder
    results = {'hero': 0, 'hub': 0, 'help': 0}
    total_views = {'hero': 0, 'hub': 0, 'help': 0}
    
    for i, (video_id, title, description, view_count) in enumerate(videos, 1):
        try:
            # Classification
            category, confidence, details = classifier.classify_text(
                title or '', 
                (description or '')[:200]
            )
            
            # Sauvegarde immédiate
            cursor.execute("""
                UPDATE video 
                SET category = ?, 
                    classification_source = 'semantic',
                    classification_date = datetime('now'),
                    classification_confidence = ?
                WHERE id = ?
            """, (category, confidence, video_id))
            
            # Statistiques
            results[category] += 1
            total_views[category] += view_count or 0
            
            # Affichage
            views_str = f"{view_count:,}" if view_count else "0"
            title_short = title[:60] + "..." if len(title) > 60 else title
            
            print(f"[{i:2d}/50] {category.upper():4} ({confidence:.2f}) {views_str:>10} vues: {title_short}")
            
        except Exception as e:
            print(f"[{i:2d}/50] ❌ ERREUR: {str(e)[:50]}...")
    
    # Commit final
    conn.commit()
    conn.close()
    
    # Résumé final
    print()
    print("🎯 RÉSUMÉ DE CLASSIFICATION - TOP 50 ARD REISEN")
    print("=" * 60)
    
    total_videos = sum(results.values())
    for category in ['hero', 'hub', 'help']:
        count = results[category]
        percentage = (count / total_videos * 100) if total_videos > 0 else 0
        views = total_views[category]
        avg_views = views // count if count > 0 else 0
        
        print(f"{category.upper():4}: {count:2d} vidéos ({percentage:5.1f}%) - {views:,} vues totales - {avg_views:,} vues/vidéo")
    
    print(f"\nTOTAL: {total_videos} vidéos classifiées")
    print("✅ Classification terminée !")

if __name__ == "__main__":
    classify_top50_videos()