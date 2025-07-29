#!/usr/bin/env python3
"""
Script pour exporter les top 5 topics les plus engageants par concurrent en CSV
Format optimisé pour copier-coller dans PowerPoint
"""

import csv
from datetime import datetime
from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.engagement_analyzer import EngagementAnalyzer

def export_top_topics_csv():
    """Exporte les top 5 topics par concurrent en CSV"""
    
    print("🚀 Export des top 5 topics par concurrent")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialiser l'analyseur
    analyzer = EngagementAnalyzer()
    
    # Récupérer tous les concurrents
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            c.name,
            c.country,
            COUNT(v.id) as video_count
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        GROUP BY c.id, c.name, c.country
        HAVING video_count > 0
        ORDER BY c.name
    """)
    
    competitors = cursor.fetchall()
    conn.close()
    
    print(f"📊 {len(competitors)} concurrents trouvés avec des vidéos")
    
    # Préparer les données pour CSV - Format: une ligne par topic
    csv_data = []
    
    # Headers simplifiés
    headers = [
        'Concurrent',
        'Topic'
    ]
    
    csv_data.append(headers)
    
    # Analyser chaque concurrent
    for i, competitor in enumerate(competitors, 1):
        competitor_id, name, country, video_count = competitor
        
        print(f"📈 Analyse {i}/{len(competitors)}: {name}")
        
        # Récupérer les top 5 vidéos engageantes
        top_videos = analyzer.get_top_engaging_videos(competitor_id, 5)
        
        # Créer une ligne par topic (5 lignes par concurrent)
        for j, video in enumerate(top_videos[:5], 1):
            # Titre du topic (tronqué à 60 caractères pour plus de lisibilité)
            topic_title = video['title'][:60] + '...' if len(video['title']) > 60 else video['title']
            
            # Ajouter la ligne
            csv_data.append([
                name,
                topic_title
            ])
        
        # Si moins de 5 vidéos, compléter avec des lignes vides pour maintenir la structure
        for j in range(len(top_videos), 5):
            csv_data.append([
                name,
                ''
            ])
    
    # Sauvegarder le CSV
    filename = f'top_topics_by_competitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:  # utf-8-sig pour Excel
        writer = csv.writer(csvfile, delimiter=';')  # Point-virgule pour Excel français
        writer.writerows(csv_data)
    
    print(f"\n✅ Export terminé!")
    print(f"📄 Fichier créé: {filename}")
    print(f"📊 {len(competitors)} concurrents exportés")
    
    # Afficher un aperçu
    print(f"\n📋 Aperçu des données (15 premières lignes):")
    print("-" * 80)
    print(f"{'Concurrent':<25} | {'Topic'}")
    print("-" * 80)
    
    for i, row in enumerate(csv_data[1:16]):  # Skip headers, show 15 lines
        competitor_name = row[0]
        topic = row[1][:50] + '...' if len(row[1]) > 50 else row[1]
        print(f"{competitor_name:<25} | {topic}")
    
    total_lines = len(csv_data) - 1  # Excluding header
    print(f"\n📊 Total: {total_lines} lignes ({len(competitors)} concurrents × 5 topics)")
    print(f"📈 Structure: 5 lignes consécutives par concurrent")
    
    print(f"\n💡 Instructions pour PowerPoint:")
    print(f"   1. Ouvrir {filename} dans Excel")
    print(f"   2. Sélectionner la colonne A (concurrents) → Copier")
    print(f"   3. Coller dans PowerPoint colonne A")
    print(f"   4. Sélectionner la colonne B (topics) → Copier") 
    print(f"   5. Coller dans PowerPoint colonne B")
    print(f"   6. Format: 5 lignes par concurrent (topics 1-5)")
    
    print(f"\n🎯 Exemple de structure:")
    print(f"   ARD Reisen    | Topic 1")
    print(f"   ARD Reisen    | Topic 2") 
    print(f"   ARD Reisen    | Topic 3")
    print(f"   ARD Reisen    | Topic 4")
    print(f"   ARD Reisen    | Topic 5")
    print(f"   Airbnb        | Topic 1")
    print(f"   Airbnb        | Topic 2")
    print(f"   ...")

if __name__ == "__main__":
    export_top_topics_csv()