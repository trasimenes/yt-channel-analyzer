#!/usr/bin/env python3
"""
Script pour entraîner le modèle sémantique avec vos classifications humaines
Transforme le modèle générique en expert de votre domaine (Club Med, voyages, etc.)
"""

import os
import sys
from datetime import datetime

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_human_data_availability():
    """
    Vérifie la disponibilité des données classifiées manuellement
    """
    print("🔍 VÉRIFICATION DES DONNÉES HUMAINES DISPONIBLES")
    print("=" * 50)
    
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier les playlists humaines
        cursor.execute('''
            SELECT COUNT(*), 
                   SUM(CASE WHEN category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                   SUM(CASE WHEN category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                   SUM(CASE WHEN category = 'help' THEN 1 ELSE 0 END) as help_count
            FROM playlist 
            WHERE (classification_source = 'human' OR human_verified = 1)
            AND category IN ('hero', 'hub', 'help')
        ''')
        
        playlist_stats = cursor.fetchone()
        
        # Vérifier les vidéos corrigées
        cursor.execute('''
            SELECT COUNT(*),
                   SUM(CASE WHEN corrected_category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                   SUM(CASE WHEN corrected_category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                   SUM(CASE WHEN corrected_category = 'help' THEN 1 ELSE 0 END) as help_count
            FROM classification_feedback 
            WHERE user_feedback_type IN ('correction', 'human_correction')
            AND corrected_category IN ('hero', 'hub', 'help')
        ''')
        
        video_stats = cursor.fetchone()
        
        # Vérifier les vidéos directement humaines
        cursor.execute('''
            SELECT COUNT(*),
                   SUM(CASE WHEN category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                   SUM(CASE WHEN category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                   SUM(CASE WHEN category = 'help' THEN 1 ELSE 0 END) as help_count
            FROM video 
            WHERE (classification_source = 'human' OR human_verified = 1)
            AND category IN ('hero', 'hub', 'help')
        ''')
        
        video_direct_stats = cursor.fetchone()
        
        conn.close()
        
        # Affichage des résultats
        print(f"\n📋 PLAYLISTS CLASSIFIÉES MANUELLEMENT:")
        if playlist_stats and playlist_stats[0] > 0:
            print(f"   ✅ Total: {playlist_stats[0]}")
            print(f"   🎯 HERO: {playlist_stats[1]}")
            print(f"   🏠 HUB: {playlist_stats[2]}")
            print(f"   🆘 HELP: {playlist_stats[3]}")
        else:
            print(f"   ⚠️ Aucune playlist classifiée manuellement")
        
        print(f"\n🎥 VIDÉOS CORRIGÉES MANUELLEMENT:")
        if video_stats and video_stats[0] > 0:
            print(f"   ✅ Total: {video_stats[0]}")
            print(f"   🎯 HERO: {video_stats[1]}")
            print(f"   🏠 HUB: {video_stats[2]}")
            print(f"   🆘 HELP: {video_stats[3]}")
        else:
            print(f"   ⚠️ Aucune correction vidéo")
        
        print(f"\n🎬 VIDÉOS DIRECTEMENT HUMAINES:")
        if video_direct_stats and video_direct_stats[0] > 0:
            print(f"   ✅ Total: {video_direct_stats[0]}")
            print(f"   🎯 HERO: {video_direct_stats[1]}")
            print(f"   🏠 HUB: {video_direct_stats[2]}")
            print(f"   🆘 HELP: {video_direct_stats[3]}")
        else:
            print(f"   ⚠️ Aucune vidéo directement humaine")
        
        # Calcul total
        total_examples = (playlist_stats[0] if playlist_stats else 0) + \
                        (video_stats[0] if video_stats else 0) + \
                        (video_direct_stats[0] if video_direct_stats else 0)
        
        print(f"\n📊 RÉSUMÉ:")
        print(f"   🎯 Total d'exemples disponibles: {total_examples}")
        
        if total_examples >= 50:
            print(f"   ✅ Dataset suffisant pour l'entraînement!")
        elif total_examples >= 20:
            print(f"   ⚠️ Dataset petit mais utilisable")
        else:
            print(f"   ❌ Dataset trop petit - il faut plus de classifications manuelles")
        
        return total_examples
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return 0


def demonstrate_training_process():
    """
    Démontre le processus d'entraînement avec les données humaines
    """
    print("\n🎓 DÉMONSTRATION DU PROCESSUS D'ENTRAÎNEMENT")
    print("=" * 50)
    
    try:
        from yt_channel_analyzer.semantic_training import SemanticTrainingManager
        from yt_channel_analyzer.semantic_classifier import SemanticHubHeroHelpClassifier
        
        # 1. Créer le classificateur de base
        print("\n🧠 ÉTAPE 1: Initialisation du classificateur sémantique")
        base_classifier = SemanticHubHeroHelpClassifier()
        trainer = SemanticTrainingManager(base_classifier)
        
        # 2. Extraction des données
        print("\n📊 ÉTAPE 2: Extraction des classifications humaines")
        extraction_result = trainer.extract_human_classifications()
        
        if not extraction_result['success']:
            print(f"❌ Erreur extraction: {extraction_result.get('error')}")
            return False
        
        # 3. Rapport de qualité
        print("\n📋 ÉTAPE 3: Analyse de la qualité des données")
        quality_report = trainer.get_training_quality_report()
        
        if 'error' in quality_report:
            print(f"❌ Erreur analyse qualité: {quality_report['error']}")
            return False
        
        # Affichage du rapport
        print(f"\n   📊 Distribution des données:")
        for category, info in quality_report['data_distribution'].items():
            print(f"      {category.upper()}: {info['count']} exemples ({info['percentage']})")
        
        print(f"\n   📝 Qualité des textes:")
        tq = quality_report['text_quality']
        print(f"      Longueur moyenne titre: {tq.get('avg_title_length', 0):.1f} mots")
        print(f"      Couverture descriptions: {tq.get('description_coverage', '0%')}")
        
        print(f"\n   🏢 Couverture par concurrent:")
        for competitor, count in list(quality_report['competitor_coverage'].items())[:5]:
            print(f"      {competitor}: {count} exemples")
        
        if quality_report['recommendations']:
            print(f"\n   💡 Recommandations:")
            for rec in quality_report['recommendations']:
                print(f"      {rec}")
        
        # 4. Entraînement
        print("\n🎓 ÉTAPE 4: Entraînement du modèle")
        training_result = trainer.train_semantic_model()
        
        if not training_result['success']:
            print(f"❌ Erreur entraînement: {training_result.get('error')}")
            return False
        
        print(f"   ✅ {training_result['examples_added']} exemples ajoutés au modèle")
        print(f"   📚 Catégories entraînées: {', '.join(training_result['categories_trained'])}")
        
        # 5. Validation
        print("\n🧪 ÉTAPE 5: Validation du modèle entraîné")
        validation_result = trainer.validate_training(test_size=5)
        
        if 'error' in validation_result:
            print(f"❌ Erreur validation: {validation_result.get('error')}")
        else:
            print(f"   🎯 Précision globale: {validation_result['overall_accuracy']*100:.1f}%")
            
            for category, results in validation_result['accuracy_by_category'].items():
                print(f"   {category.upper()}: {results['percentage']} ({results['correct']}/{results['total']})")
        
        # 6. Test comparatif
        print("\n⚖️ ÉTAPE 6: Comparaison avant/après entraînement")
        test_examples = [
            {
                'title': "Révélation exclusive : nouveau Club Med aux Seychelles",
                'description': "Découvrez en avant-première notre tout nouveau resort"
            },
            {
                'title': "Nos équipes vous racontent leur quotidien",
                'description': "Rencontrez les personnes qui font la magie de vos vacances"
            },
            {
                'title': "Problème de réservation ? Voici la solution",
                'description': "Résolvez rapidement vos difficultés de réservation"
            }
        ]
        
        # Classificateur de base (sans entraînement spécialisé)
        base_classifier_fresh = SemanticHubHeroHelpClassifier()
        
        for i, example in enumerate(test_examples, 1):
            print(f"\n   Test {i}: {example['title'][:40]}...")
            
            # Avant entraînement
            cat_before, conf_before, _ = base_classifier_fresh.classify_text(
                example['title'], example['description']
            )
            
            # Après entraînement
            cat_after, conf_after, _ = trainer.classifier.classify_text(
                example['title'], example['description']
            )
            
            print(f"      Avant: {cat_before.upper()} ({conf_before:.1f}%)")
            print(f"      Après: {cat_after.upper()} ({conf_after:.1f}%)")
            
            if cat_before != cat_after:
                print(f"      🔄 Classification modifiée par l'entraînement!")
            elif abs(conf_after - conf_before) > 10:
                print(f"      📈 Confiance améliorée de {conf_after - conf_before:+.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur démonstration: {e}")
        return False


def create_production_model():
    """
    Crée le modèle de production entraîné avec toutes les données humaines
    """
    print("\n🏭 CRÉATION DU MODÈLE DE PRODUCTION")
    print("=" * 50)
    
    try:
        from yt_channel_analyzer.semantic_training import create_domain_specific_model
        
        # Création du modèle complet
        result = create_domain_specific_model()
        
        if result['success']:
            print(f"\n✅ MODÈLE DE PRODUCTION CRÉÉ!")
            print(f"   📊 {result['extraction']['stats']['total_examples']} exemples utilisés")
            print(f"   🎯 Précision: {result['validation']['overall_accuracy']*100:.1f}%")
            print(f"   💾 Sauvegardé: {result['model_path']}")
            
            # --- NOUVEAU: Sauvegarde des métadonnées pour le tableau de bord ---
            metadata_path = "ai_training_metadata.json"
            metadata = {
                "last_trained_at": datetime.now().isoformat(),
                "examples_used": result['extraction']['stats']['total_examples'],
                "accuracy": result['validation']['overall_accuracy'],
                "model_path": result['model_path']
            }
            try:
                import json
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                print(f"   📈 Métadonnées sauvegardées: {metadata_path}")
            except Exception as e:
                print(f"   ❌ Erreur sauvegarde métadonnées: {e}")
            # --- FIN NOUVEAU ---

            # Recommandations d'utilisation
            print(f"\n📋 PROCHAINES ÉTAPES:")
            print(f"   1. Intégrer le modèle dans votre application")
            print(f"   2. Tester sur vos nouvelles vidéos/playlists")
            print(f"   3. Collecter plus de feedbacks pour améliorer")
            print(f"   4. Re-entraîner périodiquement avec nouvelles données")
            
            return result
        else:
            print(f"❌ Erreur création modèle: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur création modèle de production: {e}")
        return None


def show_integration_instructions():
    """
    Affiche les instructions d'intégration dans l'application
    """
    print("\n🔌 INSTRUCTIONS D'INTÉGRATION")
    print("=" * 50)
    
    instructions = """
Pour utiliser votre modèle entraîné dans l'application:

1. 📝 Remplacer la classification existante:

   # ANCIEN CODE:
   from yt_channel_analyzer.database import classify_video_with_language
   category, language, confidence = classify_video_with_language(title, description)

   # NOUVEAU CODE (avec votre modèle entraîné):
   from yt_channel_analyzer.semantic_integration import semantic_manager
   
   # Charger votre modèle entraîné
   semantic_manager.classifier.load_model("trained_semantic_model.pkl")
   
   # Utiliser le modèle spécialisé
   result = semantic_manager.classify_video_semantic(title, description)
   category, confidence = result['category'], result['confidence']

2. 🔄 Mise à jour automatique:

   # Ajouter ce code pour continuer l'apprentissage
   def add_human_feedback(title, description, correct_category):
       semantic_manager.add_learning_feedback(title, description, correct_category)
       
       # Re-entraîner périodiquement (ex: tous les 100 feedbacks)
       if feedback_count % 100 == 0:
           trainer = SemanticTrainingManager(semantic_manager.classifier)
           trainer.extract_human_classifications()
           trainer.train_semantic_model()

3. 📊 Monitoring:

   # Surveiller les performances
   stats = semantic_manager.get_system_stats()
   print(f"Précision: {stats['accuracy']}%")
   print(f"Utilisations: {stats['total_classifications']}")

4. 🎯 Optimisation continue:

   # Comparer les méthodes
   comparison = semantic_manager.compare_classifications(title, description)
   if not comparison['agreement']:
       # Analyser les désaccords pour améliorer le modèle
       pass
"""
    
    print(instructions)


def main():
    """
    Fonction principale du script d'entraînement
    """
    # --- NOUVEAU: Gestion du mode non-interactif ---
    is_interactive = '--non-interactive' not in sys.argv
    # --- FIN NOUVEAU ---

    print("🎓 ENTRAÎNEMENT DU MODÈLE SÉMANTIQUE AVEC VOS DONNÉES")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Ce script va transformer le modèle sémantique générique")
    print("en expert spécialisé sur VOS données (Club Med, voyages, etc.)")
    print()
    
    # 1. Vérification des données disponibles
    total_examples = check_human_data_availability()
    
    if total_examples < 10:
        print("\n❌ DONNÉES INSUFFISANTES")
        print("Vous devez d'abord classifier plus de contenus manuellement.")
        print("Recommandation: Classifiez au moins 20-50 playlists/vidéos avant l'entraînement.")
        return
    
    # 2. Démonstration du processus
    print(f"\n✅ {total_examples} exemples trouvés - Suffisant pour l'entraînement!")
    
    run_demo = False
    if is_interactive:
        user_input = input("\nVoulez-vous voir une démonstration du processus d'entraînement? (o/N): ")
        if user_input.lower() in ['o', 'oui', 'y', 'yes']:
            run_demo = True
    
    if run_demo:
        success = demonstrate_training_process()
        if not success:
            print("\n❌ Erreur durant la démonstration")
            return
    
    # 3. Création du modèle de production
    create_model = False
    if is_interactive:
        user_input = input("\nVoulez-vous créer le modèle de production complet? (o/N): ")
        if user_input.lower() in ['o', 'oui', 'y', 'yes']:
            create_model = True
    else:
        create_model = True # Toujours créer en mode non-interactif

    if create_model:
        result = create_production_model()
        if not result:
            print("\n❌ Erreur durant la création du modèle")
            return
        
        # 4. Instructions d'intégration
        if is_interactive:
            show_integration_instructions()
    
    print("\n🎉 PROCESSUS TERMINÉ!")
    print()
    print("Votre modèle sémantique est maintenant spécialisé sur votre domaine.")
    print("Il comprend vos spécificités métier et donnera des classifications")
    print("bien plus précises que le système générique!")


if __name__ == "__main__":
    main() 