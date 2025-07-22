#!/usr/bin/env python3
"""
Script direct pour entraîner le modèle avec les données humaines
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from yt_channel_analyzer.database.base import get_db_connection
from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier

def main():
    print("🚀 Entraînement direct du modèle sémantique")
    print("=" * 60)
    
    # Créer le classificateur
    print("\n📊 Initialisation du classificateur...")
    classifier = AdvancedSemanticClassifier()
    
    # Charger les données depuis la base
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Extraire les playlists classifiées
    print("\n🔍 Extraction des playlists classifiées humainement...")
    cursor.execute("""
        SELECT name, description, category
        FROM playlist
        WHERE (is_human_validated = 1 
           OR classification_source = 'human'
           OR human_verified = 1)
           AND category IS NOT NULL
           AND category != ''
    """)
    
    playlists_added = 0
    for name, description, category in cursor.fetchall():
        text = f"{name} {description or ''}"
        classifier.add_example(text.strip(), category.lower())
        playlists_added += 1
    
    print(f"✅ {playlists_added} playlists ajoutées")
    
    # Extraire les vidéos classifiées
    print("\n🔍 Extraction des vidéos classifiées humainement...")
    cursor.execute("""
        SELECT title, description, category
        FROM video
        WHERE (is_human_validated = 1 
           OR classification_source = 'human')
           AND category IS NOT NULL
           AND category != ''
        LIMIT 500
    """)
    
    videos_added = 0
    for title, description, category in cursor.fetchall():
        text = f"{title} {description or ''}"
        if len(text.strip()) > 10:  # Éviter les textes trop courts
            classifier.add_example(text.strip(), category.lower())
            videos_added += 1
    
    print(f"✅ {videos_added} vidéos ajoutées")
    
    conn.close()
    
    # Afficher les statistiques finales
    print(f"\n📈 Total des exemples par catégorie :")
    for category, examples in classifier.category_prototypes.items():
        print(f"  - {category.upper()}: {len(examples)} exemples")
    
    # Tester le modèle
    print("\n🧪 Test du modèle entraîné :")
    test_cases = [
        "How to book your perfect family vacation",
        "Behind the scenes at Center Parcs",
        "Summer activities and entertainment",
        "Booking guide and tips",
        "Our vision for sustainable tourism"
    ]
    
    for text in test_cases:
        category, confidence = classifier.classify(text)
        print(f"  '{text}' -> {category.upper()} ({confidence:.2%})")
    
    print("\n✨ Modèle entraîné avec succès !")
    print(f"Total: {playlists_added} playlists + {videos_added} vidéos = {playlists_added + videos_added} exemples ajoutés")

if __name__ == "__main__":
    main()