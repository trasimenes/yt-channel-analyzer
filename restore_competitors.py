#!/usr/bin/env python3
"""
Script de restauration rapide des concurrents perdus
"""

import requests
import json
import time

def restore_competitors():
    """Restaure automatiquement les concurrents perdus"""
    
    # URLs des concurrents identifiés
    competitors = [
        "https://www.youtube.com/@Expedia",
        "https://www.youtube.com/@AccorHotels", 
        "https://www.youtube.com/@CenterParcs",
        "https://www.youtube.com/@ClubMedFr",
        "https://www.youtube.com/@Hilton"
    ]
    
    base_url = "http://127.0.0.1:8081"
    
    print("🔄 Restauration des concurrents perdus...")
    print(f"📋 {len(competitors)} concurrents à restaurer")
    
    for i, channel_url in enumerate(competitors, 1):
        print(f"\n[{i}/{len(competitors)}] 📺 Ajout de {channel_url}")
        
        try:
            # Appel API pour ajouter le concurrent
            response = requests.post(
                f"{base_url}/analyze-channel",
                json={"channel_url": channel_url},
                timeout=300  # 5 minutes max par chaîne
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Succès: {result.get('message', 'Ajouté')}")
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout pour {channel_url} - analyse trop longue")
        except Exception as e:
            print(f"❌ Erreur pour {channel_url}: {e}")
        
        # Pause entre les requêtes
        if i < len(competitors):
            print("⏳ Attente 5 secondes...")
            time.sleep(5)
    
    print("\n🎉 Restauration terminée !")
    print("🔍 Vérifiez sur http://127.0.0.1:8081/concurrents")

if __name__ == "__main__":
    restore_competitors() 