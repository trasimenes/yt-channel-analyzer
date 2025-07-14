#!/usr/bin/env python3
"""
Script de configuration et démonstration du système de classification sémantique
Remplace l'approche par mots-clés par une vraie compréhension sémantique
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def install_requirements():
    """
    Installe les dépendances nécessaires pour la classification sémantique
    """
    print("🔧 Installation des dépendances...")
    
    requirements = [
        "sentence-transformers>=2.2.0",
        "scikit-learn>=1.0.0",
        "numpy>=1.21.0",
        "torch>=1.9.0"
    ]
    
    for req in requirements:
        try:
            print(f"   📦 Installation de {req}...")
            subprocess.run([sys.executable, "-m", "pip", "install", req], check=True, capture_output=True)
            print(f"   ✅ {req} installé avec succès")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erreur lors de l'installation de {req}: {e}")
            return False
    
    print("✅ Toutes les dépendances sont installées")
    return True


def test_semantic_classification():
    """
    Teste le système de classification sémantique
    """
    print("\n🧪 Test du système de classification sémantique...")
    
    # Import des modules
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from yt_channel_analyzer.semantic_integration import semantic_manager, compare_classification_methods
        
        if not semantic_manager.enabled:
            print("❌ Le système sémantique n'est pas disponible")
            return False
        
        print("✅ Système sémantique initialisé")
        
        # Tests de classification
        test_cases = [
            {
                'title': "Découverte exclusive du nouveau Club Med aux Seychelles",
                'description': "Première mondiale : visitez en avant-première notre nouveau resort de luxe",
                'expected_type': 'HERO (nouveau/exclusif)'
            },
            {
                'title': "Les plus belles plages de Maurice - Episode 3",
                'description': "Troisième épisode de notre série sur les destinations paradisiaques",
                'expected_type': 'HUB (série régulière)'
            },
            {
                'title': "Comment réserver votre séjour Club Med",
                'description': "Tutoriel complet pour effectuer votre réservation en ligne",
                'expected_type': 'HELP (tutoriel)'
            }
        ]
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n🎯 Test {i}: {test['title']}")
            
            # Comparaison des méthodes
            comparison = compare_classification_methods(test['title'], test['description'])
            
            if comparison['semantic_result'] and 'category' in comparison['semantic_result']:
                sem_result = comparison['semantic_result']
                print(f"   🧠 Sémantique: {sem_result['category'].upper()} ({sem_result['confidence']:.1f}%)")
            
            if comparison['traditional_result'] and 'category' in comparison['traditional_result']:
                trad_result = comparison['traditional_result']
                print(f"   📝 Traditionnel: {trad_result['category'].upper()} ({trad_result['confidence']:.1f}%)")
            
            if comparison['agreement']:
                print(f"   ✅ Accord entre les méthodes")
            else:
                print(f"   ⚠️  Désaccord entre les méthodes")
            
            print(f"   💡 Attendu: {test['expected_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False


def demonstrate_semantic_understanding():
    """
    Démontre la différence entre compréhension sémantique et matching de mots-clés
    """
    print("\n🎭 Démonstration de la compréhension sémantique vs mots-clés...")
    
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from yt_channel_analyzer.semantic_classifier import SemanticHubHeroHelpClassifier
        
        classifier = SemanticHubHeroHelpClassifier()
        
        # Exemples qui montrent la différence
        examples = [
            {
                'title': "Révélation choc : la destination secrète que personne ne connaît",
                'description': "Découvrez en exclusivité mondiale ce paradis caché",
                'explanation': "Contient des mots comme 'révélation', 'exclusivité', 'secret' qui indiquent du HERO sans utiliser les mots-clés habituels"
            },
            {
                'title': "Nos équipes vous racontent leur quotidien",
                'description': "Rencontrez les personnes qui font la magie Club Med chaque jour",
                'explanation': "Contenu régulier sur les équipes, typique HUB, sans mots-clés évidents"
            },
            {
                'title': "Problème avec votre réservation ? Voici la solution",
                'description': "Résolvez rapidement les difficultés de réservation en ligne",
                'explanation': "Aide pour résoudre un problème, clairement HELP même sans 'tutoriel' ou 'guide'"
            }
        ]
        
        for i, example in enumerate(examples, 1):
            print(f"\n🔍 Exemple {i}:")
            print(f"   📝 Titre: {example['title']}")
            print(f"   📄 Description: {example['description']}")
            
            # Classification sémantique
            category, confidence, details = classifier.classify_text(example['title'], example['description'])
            print(f"   🧠 Classification sémantique: {category.upper()} ({confidence:.1f}%)")
            
            # Explication
            explanation = classifier.explain_classification(example['title'], example['description'])
            print(f"   💭 Raisonnement: {explanation['reasoning']}")
            print(f"   🎯 Pourquoi c'est intéressant: {example['explanation']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la démonstration: {e}")
        return False


def create_configuration_file():
    """
    Crée un fichier de configuration pour le système sémantique
    """
    print("\n⚙️ Création du fichier de configuration...")
    
    config = {
        "semantic_classification": {
            "enabled": True,
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "semantic_weight": 0.7,
            "confidence_threshold": 60,
            "auto_learn": True,
            "fallback_to_traditional": True
        },
        "performance": {
            "batch_size": 32,
            "max_sequence_length": 512,
            "use_gpu": False
        },
        "logging": {
            "log_classifications": True,
            "log_explanations": False,
            "log_comparisons": True
        },
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "config", "semantic_config.json")
    
    # Création du dossier config s'il n'existe pas
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuration créée: {config_path}")
    return config_path


def show_integration_examples():
    """
    Montre des exemples d'intégration avec l'application existante
    """
    print("\n🔌 Exemples d'intégration avec l'application existante...")
    
    integration_code = '''
# Dans votre application Flask existante, remplacez:

# ANCIEN CODE (matching de mots-clés):
from yt_channel_analyzer.database import classify_video_with_language
category, language, confidence = classify_video_with_language(title, description)

# NOUVEAU CODE (compréhension sémantique):
from yt_channel_analyzer.semantic_integration import classify_video_enhanced
category, language, confidence = classify_video_enhanced(title, description)

# Pour une classification en lot:
from yt_channel_analyzer.semantic_integration import batch_classify_enhanced
classified_videos = batch_classify_enhanced(videos)

# Pour ajouter un feedback d'apprentissage:
from yt_channel_analyzer.semantic_integration import add_semantic_feedback
add_semantic_feedback(title, description, correct_category, "Correction utilisateur")

# Pour comparer les méthodes:
from yt_channel_analyzer.semantic_integration import compare_classification_methods
comparison = compare_classification_methods(title, description)
'''
    
    print(integration_code)
    
    # Sauvegarde de l'exemple
    example_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               "examples", "semantic_integration_example.py")
    
    os.makedirs(os.path.dirname(example_path), exist_ok=True)
    
    with open(example_path, 'w', encoding='utf-8') as f:
        f.write(integration_code)
    
    print(f"✅ Exemple sauvegardé: {example_path}")


def main():
    """
    Fonction principale du script de configuration
    """
    print("="*60)
    print("🚀 CONFIGURATION DU SYSTÈME DE CLASSIFICATION SÉMANTIQUE")
    print("="*60)
    print()
    print("Ce script va configurer un système de classification qui COMPREND")
    print("vraiment le sens des textes au lieu de faire du matching de mots-clés.")
    print()
    
    # Étape 1: Installation des dépendances
    if not install_requirements():
        print("❌ Échec de l'installation des dépendances")
        return
    
    # Étape 2: Test du système
    if not test_semantic_classification():
        print("❌ Échec du test du système sémantique")
        return
    
    # Étape 3: Démonstration de la compréhension sémantique
    if not demonstrate_semantic_understanding():
        print("❌ Échec de la démonstration")
        return
    
    # Étape 4: Configuration
    config_path = create_configuration_file()
    
    # Étape 5: Exemples d'intégration
    show_integration_examples()
    
    print("\n" + "="*60)
    print("✅ CONFIGURATION TERMINÉE AVEC SUCCÈS")
    print("="*60)
    print()
    print("🎯 Le système de classification sémantique est maintenant prêt !")
    print()
    print("📋 Prochaines étapes:")
    print("   1. Intégrez le nouveau système dans votre application")
    print("   2. Testez sur vos données réelles")
    print("   3. Ajustez les paramètres selon vos besoins")
    print("   4. Collectez des feedbacks pour améliorer la précision")
    print()
    print("🔗 Pour utiliser le système:")
    print("   - Importez les fonctions depuis semantic_integration")
    print("   - Remplacez les appels existants par les nouvelles fonctions")
    print("   - Surveillez les performances et ajustez si nécessaire")
    print()


if __name__ == "__main__":
    main() 