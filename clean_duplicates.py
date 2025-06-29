#!/usr/bin/env python3
"""
Script pour nettoyer les doublons de concurrents dans la base de données.
Garde le concurrent avec le plus de vidéos pour chaque nom/channel.
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yt_channel_analyzer.database import clean_duplicate_competitors, get_all_competitors

def main():
    print("🧹 NETTOYAGE DES DOUBLONS DE CONCURRENTS")
    print("=" * 50)
    
    # Afficher l'état actuel
    print("\n📊 État AVANT nettoyage:")
    competitors = get_all_competitors()
    for comp in competitors:
        print(f"  • {comp['name']}: {comp.get('video_count', 0)} vidéos (ID: {comp['id']})")
    
    print(f"\nTotal: {len(competitors)} concurrents dans la base")
    
    # Demander confirmation
    response = input("\n❓ Voulez-vous procéder au nettoyage des doublons ? (y/N): ")
    if response.lower() not in ['y', 'yes', 'oui', 'o']:
        print("❌ Nettoyage annulé.")
        return
    
    # Exécuter le nettoyage
    print("\n🔄 Nettoyage en cours...")
    result = clean_duplicate_competitors()
    
    if result['success']:
        print(f"\n✅ {result['message']}")
        
        # Afficher l'état après nettoyage
        print("\n📊 État APRÈS nettoyage:")
        competitors_after = get_all_competitors()
        for comp in competitors_after:
            print(f"  • {comp['name']}: {comp.get('video_count', 0)} vidéos (ID: {comp['id']})")
        
        print(f"\nTotal final: {len(competitors_after)} concurrents uniques")
        
        if result['deleted_count'] > 0:
            print(f"\n🎯 Résumé:")
            print(f"  • Doublons supprimés: {result['deleted_count']}")
            print(f"  • Concurrents conservés: {result['kept_count']}")
            print(f"  • Économie d'espace: {result['deleted_count']} entrées en moins")
        else:
            print("\n✨ Aucun doublon trouvé - base déjà propre !")
            
    else:
        print(f"❌ Erreur lors du nettoyage: {result.get('error', 'Erreur inconnue')}")

if __name__ == "__main__":
    main() 