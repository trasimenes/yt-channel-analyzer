#!/usr/bin/env python3
"""
Script de migration vers l'architecture modulaire
Remplace le monolithe app.py de 10,122 lignes par une architecture en blueprints
"""
import os
import shutil
from datetime import datetime

def backup_original():
    """Sauvegarder l'app.py original"""
    print("📦 Sauvegarde de l'app.py original...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"app_original_{timestamp}.py"
    shutil.copy2("app.py", backup_name)
    print(f"✅ Sauvegardé sous: {backup_name}")

def switch_to_modular():
    """Basculer vers l'architecture modulaire"""
    print("🔄 Basculement vers l'architecture modulaire...")
    
    # Sauvegarder l'original
    backup_original()
    
    # Remplacer par la version modulaire
    shutil.copy2("app_modular.py", "app.py")
    print("✅ app.py remplacé par la version modulaire")

def verify_blueprints():
    """Vérifier que tous les blueprints sont présents"""
    print("🔍 Vérification des blueprints...")
    
    required_blueprints = [
        "blueprints/__init__.py",
        "blueprints/auth.py",
        "blueprints/main.py", 
        "blueprints/api.py",
        "blueprints/competitors.py",
        "blueprints/insights.py",
        "blueprints/admin.py",
        "blueprints/utils.py"
    ]
    
    missing = []
    for blueprint in required_blueprints:
        if not os.path.exists(blueprint):
            missing.append(blueprint)
    
    if missing:
        print(f"❌ Blueprints manquants: {missing}")
        return False
    
    print("✅ Tous les blueprints sont présents")
    return True

def show_architecture_comparison():
    """Afficher la comparaison d'architecture"""
    print("\n" + "="*60)
    print("📊 COMPARAISON D'ARCHITECTURE")
    print("="*60)
    
    print("❌ AVANT (Monolithe):")
    print("   app.py                    10,122 lignes")
    print("   ├── Authentication        ~15 routes")
    print("   ├── Main/Dashboard        ~10 routes") 
    print("   ├── API endpoints         ~50 routes")
    print("   ├── Competitors           ~30 routes")
    print("   ├── Insights/Analytics    ~25 routes")
    print("   ├── Admin/Settings        ~20 routes")
    print("   └── Utilities             ~100 fonctions")
    print()
    
    print("✅ APRÈS (Modulaire):")
    print("   app.py                    ~200 lignes")
    print("   blueprints/")
    print("   ├── auth.py               ~152 lignes")
    print("   ├── main.py               ~172 lignes")
    print("   ├── api.py                ~418 lignes")
    print("   ├── competitors.py        ~346 lignes") 
    print("   ├── insights.py           ~416 lignes")
    print("   ├── admin.py              ~550 lignes")
    print("   └── utils.py              ~300 lignes")
    print()
    
    print("🎯 BÉNÉFICES:")
    print("   ✅ Séparation des responsabilités")
    print("   ✅ Code plus maintenable") 
    print("   ✅ Tests unitaires facilités")
    print("   ✅ Développement en équipe simplifié")
    print("   ✅ Chargement conditionnel des modules")
    print("   ✅ Architecture scalable")
    print("="*60)

def main():
    """Point d'entrée principal"""
    print("🚀 MIGRATION VERS ARCHITECTURE MODULAIRE")
    print("Transformation du monolithe de 10,122 lignes")
    print()
    
    # Vérifier les prérequis
    if not verify_blueprints():
        print("❌ Migration annulée - blueprints manquants")
        return
    
    # Afficher l'architecture
    show_architecture_comparison()
    
    # Demander confirmation
    print()
    response = input("🤔 Procéder à la migration ? (o/N): ").lower()
    
    if response in ['o', 'oui', 'y', 'yes']:
        switch_to_modular()
        print()
        print("🎉 MIGRATION RÉUSSIE !")
        print("📝 Prochaines étapes:")
        print("   1. Tester l'application: python app.py")
        print("   2. Vérifier toutes les routes")
        print("   3. Supprimer app_modular.py si tout fonctionne")
        print("   4. Commit des changements")
    else:
        print("❌ Migration annulée")

if __name__ == "__main__":
    main()