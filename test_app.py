#!/usr/bin/env python3
"""
Script de test pour diagnostiquer les problèmes de l'application
"""

try:
    print("🔍 Test 1: Import des modules de base...")
    import os
    import json
    from datetime import datetime
    print("✅ Modules de base OK")

    print("\n🔍 Test 2: Import de Flask...")
    from flask import Flask
    print("✅ Flask OK")

    print("\n🔍 Test 3: Import SQLAlchemy...")
    from flask_sqlalchemy import SQLAlchemy
    print("✅ SQLAlchemy OK")

    print("\n🔍 Test 4: Test de la base de données...")
    from yt_channel_analyzer.database import get_all_competitors
    competitors = get_all_competitors()
    print(f"✅ Base de données OK - {len(competitors)} concurrents trouvés")

    print("\n🔍 Test 5: Import de l'application...")
    # Test d'import sans exécution
    import sys
    if 'app' in sys.modules:
        del sys.modules['app']
    
    import app
    print("✅ Application importée avec succès")
    
    print("\n🔍 Test 6: Vérification des routes...")
    routes = []
    for rule in app.app.url_map.iter_rules():
        routes.append(f"{rule.methods} {rule.rule}")
    
    print(f"✅ {len(routes)} routes trouvées:")
    for route in sorted(routes)[:10]:  # Afficher les 10 premières
        print(f"   {route}")
    if len(routes) > 10:
        print(f"   ... et {len(routes) - 10} autres")

except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc() 