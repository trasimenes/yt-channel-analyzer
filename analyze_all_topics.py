#!/usr/bin/env python3
"""
Script pour analyser les topics de TOUTES les vidéos (titres + descriptions)
Exclut uniquement les noms des concurrents
"""

import json
from datetime import datetime
from yt_channel_analyzer.topic_analyzer import TopicAnalyzer
from yt_channel_analyzer.database import get_db_connection

def analyze_all_videos():
    """Analyse tous les titres et descriptions des vidéos"""
    
    print("🚀 Début de l'analyse complète des topics")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialiser l'analyseur
    analyzer = TopicAnalyzer()
    
    # Récupérer le nombre total de vidéos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM video")
    total_videos = cursor.fetchone()[0]
    print(f"📊 Nombre total de vidéos à analyser: {total_videos}")
    
    # Lancer l'analyse
    try:
        results = analyzer._analyze_topics()
        
        # Sauvegarder les résultats
        output_file = f'topic_analysis_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Analyse terminée! Résultats sauvegardés dans: {output_file}")
        
        # Afficher un résumé
        if 'topics' in results:
            print(f"\n📈 Top 20 topics découverts:")
            for i, (topic, count) in enumerate(results['topics'][:20], 1):
                print(f"{i:2d}. {topic}: {count} occurrences")
        
        if 'bigrams' in results:
            print(f"\n🔗 Top 20 bigrammes:")
            for i, (bigram, count) in enumerate(results['bigrams'][:20], 1):
                print(f"{i:2d}. {bigram}: {count} occurrences")
                
        if 'metadata' in results:
            meta = results['metadata']
            print(f"\n📊 Statistiques:")
            print(f"- Vidéos analysées: {meta.get('total_videos', 0)}")
            print(f"- Mots uniques: {meta.get('unique_words', 0)}")
            print(f"- Mots exclus (concurrents): {meta.get('excluded_competitor_words', 0)}")
            print(f"- Durée d'analyse: {meta.get('analysis_duration', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'analyse: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_all_videos()