#!/usr/bin/env python3
"""
Script de debug pour la page concurrents
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_functions():
    print("🔍 TEST DES FONCTIONS DE BASE DE DONNÉES")
    print("=" * 50)
    
    try:
        # Test 1: Connexion à la base
        print("\n1️⃣ Test de connexion à la base...")
        from yt_channel_analyzer.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Tables trouvées: {[table[0] for table in tables]}")
        conn.close()
        
        # Test 2: Compter les concurrents
        print("\n2️⃣ Test de comptage des concurrents...")
        cursor = get_db_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        count = cursor.fetchone()[0]
        print(f"✅ {count} concurrents dans la table concurrent")
        cursor.connection.close()
        
        # Test 3: Lister les concurrents basiques
        print("\n3️⃣ Test de listing des concurrents...")
        from yt_channel_analyzer.database import get_all_competitors
        competitors = get_all_competitors()
        print(f"✅ get_all_competitors() retourne {len(competitors)} concurrents")
        for comp in competitors:
            print(f"  • {comp['name']}: {comp.get('video_count', 'N/A')} vidéos (ID: {comp['id']})")
        
        # Test 4: Fonction complète avec vidéos
        print("\n4️⃣ Test de la fonction complète avec vidéos...")
        from yt_channel_analyzer.database import get_all_competitors_with_videos
        competitors_with_videos = get_all_competitors_with_videos()
        print(f"✅ get_all_competitors_with_videos() retourne {len(competitors_with_videos)} concurrents")
        
        for comp in competitors_with_videos:
            video_count = len(comp.get('videos', []))
            print(f"  • {comp['name']}: {video_count} vidéos chargées (ID: {comp['id']})")
            
            # Afficher quelques vidéos pour vérification
            if video_count > 0:
                for i, video in enumerate(comp['videos'][:3]):  # 3 premières vidéos
                    print(f"    - {video.get('title', 'Sans titre')[:50]}...")
                if video_count > 3:
                    print(f"    ... et {video_count - 3} autres vidéos")
        
        print("\n✅ TOUS LES TESTS RÉUSSIS - La base de données fonctionne correctement !")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_route_simulation():
    print("\n🌐 SIMULATION DE LA ROUTE /concurrents")
    print("=" * 50)
    
    try:
        # Simuler exactement ce que fait la route
        from yt_channel_analyzer.database import get_all_competitors_with_videos
        
        db_competitors = get_all_competitors_with_videos()
        
        # Convertir en format compatible avec le template
        concurrents_with_keys = []
        for competitor in db_competitors:
            competitor_key = str(competitor['id'])
            
            competitor_data = {
                'name': competitor['name'],
                'channel_url': competitor['channel_url'],
                'thumbnail': competitor.get('thumbnail_url', ''),
                'banner': competitor.get('banner_url', ''),
                'description': competitor.get('description', ''),
                'video_count': len(competitor['videos']),
                'subscriber_count': competitor.get('subscriber_count'),
                'view_count': competitor.get('view_count'),
                'country': competitor.get('country', ''),
                'language': competitor.get('language', ''),
                'last_updated': competitor.get('last_updated', ''),
                'videos': competitor['videos']
            }
            
            concurrents_with_keys.append((competitor_key, competitor_data))
        
        # Trier par date de dernière mise à jour
        concurrents_with_keys.sort(key=lambda x: x[1].get('last_updated', ''), reverse=True)
        
        print(f"✅ Simulation réussie - {len(concurrents_with_keys)} concurrents prêts pour le template")
        
        for key, data in concurrents_with_keys:
            print(f"  • Clé: {key} | {data['name']}: {data['video_count']} vidéos")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR lors de la simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_database_functions()
    success2 = test_route_simulation()
    
    if success1 and success2:
        print("\n🎉 DIAGNOSTIC COMPLET: Tout fonctionne correctement !")
        print("Le problème peut être dans le serveur Flask ou le template HTML.")
    else:
        print("\n💥 PROBLÈME IDENTIFIÉ: Voir les erreurs ci-dessus.") 