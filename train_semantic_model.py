#!/usr/bin/env python3
"""
Script pour entraîner le modèle sémantique avec toutes les classifications humaines.
Utilise les 49 playlists et autres vidéos classifiées manuellement.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent))

from yt_channel_analyzer.semantic_training import SemanticTrainingManager
from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier
from yt_channel_analyzer.database.base import get_db_connection

def main():
    print("🚀 Démarrage de l'entraînement du modèle sémantique")
    print("=" * 60)
    
    # Créer le classificateur avancé
    print("\n📊 Initialisation du classificateur...")
    classifier = AdvancedSemanticClassifier()
    
    # Créer le gestionnaire d'entraînement
    print("📚 Création du gestionnaire d'entraînement...")
    trainer = SemanticTrainingManager(classifier)
    
    # Extraire les classifications humaines
    print("\n🔍 Extraction des classifications humaines de la base de données...")
    try:
        trainer.extract_human_classifications()
        print("✅ Extraction terminée")
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction : {e}")
        import traceback
        traceback.print_exc()
    
    # Afficher les statistiques
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Compter les playlists classifiées humainement
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM playlist
            WHERE is_human_validated = 1 
               OR classification_source = 'human'
               OR human_verified = 1
            GROUP BY category
        """)
        playlist_count = cursor.fetchall()
        
        # Compter les vidéos classifiées humainement
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM video
            WHERE is_human_validated = 1 
               OR classification_source = 'human'
            GROUP BY category
        """)
        video_count = cursor.fetchall()
        
        print("\n📈 Statistiques des données d'entraînement :")
        print("\nPlaylists classifiées humainement :")
        total_playlists = 0
        for cat, count in playlist_count:
            if cat:
                print(f"  - {cat}: {count} playlists")
                total_playlists += count
        print(f"  Total: {total_playlists} playlists")
        
        print("\nVidéos classifiées humainement :")
        total_videos = 0
        for cat, count in video_count:
            if cat:
                print(f"  - {cat}: {count} vidéos")
                total_videos += count
        print(f"  Total: {total_videos} vidéos")
    finally:
        conn.close()
    
    # Entraîner le modèle
    print("\n🧠 Entraînement du modèle sémantique...")
    trainer.train_semantic_model()
    
    # Afficher les nouveaux prototypes
    print("\n✅ Entraînement terminé !")
    print(f"\nPrototypes finaux par catégorie :")
    for category, examples in classifier.category_prototypes.items():
        print(f"  - {category}: {len(examples)} exemples")
    
    # Tester le modèle sur quelques exemples
    print("\n🧪 Test du modèle sur quelques exemples :")
    test_texts = [
        "Visit Center Parcs - Summer Activities",
        "How to book your holiday",
        "Behind the scenes at our parks",
        "Top 10 family activities"
    ]
    
    for text in test_texts:
        category, confidence = classifier.classify(text)
        print(f"  '{text}' -> {category} (confiance: {confidence:.2f})")
    
    print("\n✨ Modèle prêt à l'emploi !")
    print("Pour utiliser le modèle entraîné, importez AdvancedSemanticClassifier")

if __name__ == "__main__":
    main()