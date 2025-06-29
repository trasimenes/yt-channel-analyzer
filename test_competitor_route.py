#!/usr/bin/env python3
"""
Test simple de la route competitor
"""

import requests
import sys

def test_competitor_route():
    """Test de la route competitor avec session"""
    try:
        # Lire les cookies de session
        with open('cookies.txt', 'r') as f:
            cookies_content = f.read()
        
        # Extraire le cookie de session
        session_cookie = None
        for line in cookies_content.split('\n'):
            if 'session' in line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    session_cookie = parts[6]
                    break
        
        if not session_cookie:
            print("❌ Cookie de session non trouvé")
            return
        
        cookies = {'session': session_cookie}
        
        # Test de la route competitor/7 (Airbnb)
        print("🔍 Test de la route /competitor/7...")
        response = requests.get('http://127.0.0.1:8081/competitor/7', 
                              cookies=cookies, 
                              timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Route accessible")
            print(f"Contenu (premiers 500 chars): {response.text[:500]}...")
        elif response.status_code == 302:
            print(f"🔄 Redirection vers: {response.headers.get('Location')}")
        elif response.status_code == 500:
            print("❌ Erreur serveur 500")
            print(f"Contenu: {response.text}")
        else:
            print(f"❌ Erreur {response.status_code}")
            print(f"Contenu: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout - la route prend trop de temps à répondre")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_competitor_route() 