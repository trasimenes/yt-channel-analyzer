"""
Module d'entraînement sémantique avec les classifications humaines
Utilise les données classifiées manuellement pour améliorer le modèle
"""

import os
import json
import pickle
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter

from .database import get_db_connection
from .semantic_classifier import SemanticHubHeroHelpClassifier, create_optimized_classifier

class SemanticTrainingManager:
    """
    Gestionnaire d'entraînement du modèle sémantique avec les données humaines
    """
    
    def __init__(self, semantic_classifier = None, use_optimized: bool = True):
        """
        Initialise le gestionnaire d'entraînement
        
        Args:
            semantic_classifier: Instance du classificateur sémantique à entraîner
            use_optimized: Si True, utilise le classificateur optimisé all-mpnet-base-v2
        """
        if semantic_classifier:
            self.classifier = semantic_classifier
        elif use_optimized:
            print("[SEMANTIC-TRAINING] 🚀 Utilisation du classificateur optimisé all-mpnet-base-v2")
            self.classifier = create_optimized_classifier(use_quantization=False)  # Pas de quantification pour training
        else:
            self.classifier = SemanticHubHeroHelpClassifier()
        self.training_data = {
            'hero': [],
            'hub': [],
            'help': []
        }
        self.training_stats = {
            'playlists_extracted': 0,
            'videos_extracted': 0,
            'total_examples': 0,
            'last_training': None,
            'training_history': []
        }
        
        print("[SEMANTIC-TRAINING] 🎓 Gestionnaire d'entraînement initialisé")
    
    def extract_human_classifications(self) -> Dict[str, Any]:
        """
        Extrait toutes les classifications humaines de la base de données
        
        Returns:
            Dict: Statistiques et données extraites
        """
        print("[SEMANTIC-TRAINING] 📊 Extraction des classifications humaines...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Réinitialiser les données d'entraînement
            self.training_data = {'hero': [], 'hub': [], 'help': []}
            
            # 1. Extraire les playlists classifiées manuellement
            print("[SEMANTIC-TRAINING] 📋 Extraction des playlists humaines...")
            
            cursor.execute('''
                SELECT p.name, p.description, p.category, c.name as competitor_name, p.classification_date
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE (p.classification_source = 'human' OR p.human_verified = 1)
                AND p.category IN ('hero', 'hub', 'help')
                AND p.name IS NOT NULL
                ORDER BY p.classification_date DESC
            ''')
            
            playlist_results = cursor.fetchall()
            
            for row in playlist_results:
                name, description, category, competitor, date = row
                
                # Nettoyage et validation
                if name and category:
                    example = {
                        'title': name.strip(),
                        'description': (description or '').strip(),
                        'category': category.lower(),
                        'source': 'playlist_human',
                        'competitor': competitor,
                        'date': date,
                        'confidence': 100  # Classification humaine = confiance max
                    }
                    
                    self.training_data[category.lower()].append(example)
                    self.training_stats['playlists_extracted'] += 1
            
            print(f"[SEMANTIC-TRAINING] ✅ {self.training_stats['playlists_extracted']} playlists extraites")
            
            # 2. Extraire les vidéos classifiées manuellement (corrections)
            print("[SEMANTIC-TRAINING] 🎥 Extraction des vidéos humaines...")
            
            cursor.execute('''
                SELECT v.title, v.description, cf.corrected_category, c.name as competitor_name, cf.feedback_timestamp
                FROM classification_feedback cf
                JOIN video v ON cf.video_id = v.id
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE cf.user_feedback_type IN ('correction', 'human_correction')
                AND cf.corrected_category IN ('hero', 'hub', 'help')
                AND v.title IS NOT NULL
                ORDER BY cf.feedback_timestamp DESC
            ''')
            
            video_results = cursor.fetchall()
            
            for row in video_results:
                title, description, category, competitor, date = row
                
                if title and category:
                    example = {
                        'title': title.strip(),
                        'description': (description or '').strip(),
                        'category': category.lower(),
                        'source': 'video_human_correction',
                        'competitor': competitor,
                        'date': date,
                        'confidence': 100
                    }
                    
                    self.training_data[category.lower()].append(example)
                    self.training_stats['videos_extracted'] += 1
            
            print(f"[SEMANTIC-TRAINING] ✅ {self.training_stats['videos_extracted']} vidéos extraites")
            
            # 3. Extraire les vidéos directement marquées humaines
            cursor.execute('''
                SELECT v.title, v.description, v.category, c.name as competitor_name, v.classification_date
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE (v.classification_source = 'human' OR v.human_verified = 1)
                AND v.category IN ('hero', 'hub', 'help')
                AND v.title IS NOT NULL
                ORDER BY v.classification_date DESC
                LIMIT 500
            ''')
            
            direct_videos = cursor.fetchall()
            videos_direct_count = 0
            
            for row in direct_videos:
                title, description, category, competitor, date = row
                
                if title and category:
                    # Éviter les doublons avec les corrections
                    duplicate = any(
                        ex['title'] == title.strip() and ex['source'].startswith('video')
                        for ex in self.training_data[category.lower()]
                    )
                    
                    if not duplicate:
                        example = {
                            'title': title.strip(),
                            'description': (description or '').strip(),
                            'category': category.lower(),
                            'source': 'video_human_direct',
                            'competitor': competitor,
                            'date': date,
                            'confidence': 100
                        }
                        
                        self.training_data[category.lower()].append(example)
                        videos_direct_count += 1
            
            print(f"[SEMANTIC-TRAINING] ✅ {videos_direct_count} vidéos directes extraites")
            
            # Calcul des statistiques
            self.training_stats['total_examples'] = sum(len(examples) for examples in self.training_data.values())
            self.training_stats['last_extraction'] = datetime.now().isoformat()
            
            # Affichage des statistiques
            print(f"\n[SEMANTIC-TRAINING] 📊 STATISTIQUES D'EXTRACTION:")
            print(f"   🎯 HERO: {len(self.training_data['hero'])} exemples")
            print(f"   🏠 HUB: {len(self.training_data['hub'])} exemples")
            print(f"   🆘 HELP: {len(self.training_data['help'])} exemples")
            print(f"   📊 TOTAL: {self.training_stats['total_examples']} exemples")
            
            return {
                'success': True,
                'stats': self.training_stats,
                'distribution': {cat: len(examples) for cat, examples in self.training_data.items()},
                'examples_by_competitor': self._analyze_by_competitor()
            }
            
        except Exception as e:
            print(f"[SEMANTIC-TRAINING] ❌ Erreur extraction: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def _analyze_by_competitor(self) -> Dict:
        """
        Analyse la distribution des exemples par concurrent
        """
        competitor_stats = defaultdict(lambda: {'hero': 0, 'hub': 0, 'help': 0})
        
        for category, examples in self.training_data.items():
            for example in examples:
                competitor = example.get('competitor', 'Unknown')
                competitor_stats[competitor][category] += 1
        
        return dict(competitor_stats)
    
    def train_semantic_model(self) -> Dict[str, Any]:
        """
        Entraîne le modèle sémantique avec les données extraites
        
        Returns:
            Dict: Résultats de l'entraînement
        """
        if self.training_stats['total_examples'] == 0:
            print("[SEMANTIC-TRAINING] ⚠️ Pas de données d'entraînement. Extraction d'abord...")
            extraction_result = self.extract_human_classifications()
            if not extraction_result['success']:
                return extraction_result
        
        print(f"[SEMANTIC-TRAINING] 🎓 Entraînement avec {self.training_stats['total_examples']} exemples...")
        
        training_results = {
            'examples_added': 0,
            'categories_trained': [],
            'success': True,
            'training_time': datetime.now().isoformat()
        }
        
        try:
            # Ajouter tous les exemples au classificateur
            for category, examples in self.training_data.items():
                if examples:
                    print(f"[SEMANTIC-TRAINING] 📚 Entraînement {category.upper()}: {len(examples)} exemples")
                    
                    for example in examples:
                        # Ajouter l'exemple au classificateur sémantique
                        self.classifier.add_example(
                            text=example['title'],
                            category=category,
                            description=example['description']
                        )
                        training_results['examples_added'] += 1
                    
                    training_results['categories_trained'].append(category)
            
            # Mise à jour des statistiques
            self.training_stats['last_training'] = training_results['training_time']
            self.training_stats['training_history'].append({
                'date': training_results['training_time'],
                'examples_added': training_results['examples_added'],
                'categories': training_results['categories_trained']
            })
            
            print(f"[SEMANTIC-TRAINING] ✅ Entraînement terminé: {training_results['examples_added']} exemples ajoutés")
            
            return training_results
            
        except Exception as e:
            print(f"[SEMANTIC-TRAINING] ❌ Erreur entraînement: {e}")
            return {'success': False, 'error': str(e)}
    
    def validate_training(self, test_size: int = 10) -> Dict[str, Any]:
        """
        Valide l'entraînement en testant sur un échantillon
        
        Args:
            test_size: Nombre d'exemples à tester par catégorie
            
        Returns:
            Dict: Résultats de validation
        """
        print(f"[SEMANTIC-TRAINING] 🧪 Validation avec {test_size} exemples par catégorie...")
        
        validation_results = {
            'accuracy_by_category': {},
            'overall_accuracy': 0,
            'total_tests': 0,
            'correct_predictions': 0,
            'confusion_matrix': defaultdict(lambda: defaultdict(int)),
            'sample_results': []
        }
        
        try:
            for category, examples in self.training_data.items():
                if len(examples) < test_size:
                    print(f"[SEMANTIC-TRAINING] ⚠️ Pas assez d'exemples pour {category}: {len(examples)} < {test_size}")
                    continue
                
                # Prendre un échantillon aléatoire
                import random
                test_examples = random.sample(examples, min(test_size, len(examples)))
                
                correct = 0
                category_results = []
                
                for example in test_examples:
                    predicted_category, confidence, _ = self.classifier.classify_text(
                        example['title'], example['description']
                    )
                    
                    is_correct = predicted_category == category
                    if is_correct:
                        correct += 1
                        validation_results['correct_predictions'] += 1
                    
                    # Matrice de confusion
                    validation_results['confusion_matrix'][category][predicted_category] += 1
                    
                    # Échantillon de résultats
                    category_results.append({
                        'title': example['title'][:50] + '...',
                        'expected': category,
                        'predicted': predicted_category,
                        'confidence': confidence,
                        'correct': is_correct
                    })
                    
                    validation_results['total_tests'] += 1
                
                # Précision par catégorie
                accuracy = correct / len(test_examples) if test_examples else 0
                validation_results['accuracy_by_category'][category] = {
                    'accuracy': accuracy,
                    'correct': correct,
                    'total': len(test_examples),
                    'percentage': f"{accuracy*100:.1f}%"
                }
                
                validation_results['sample_results'].extend(category_results[:3])  # 3 exemples par catégorie
                
                print(f"[SEMANTIC-TRAINING] 📊 {category.upper()}: {correct}/{len(test_examples)} ({accuracy*100:.1f}%)")
            
            # Précision globale
            if validation_results['total_tests'] > 0:
                overall_accuracy = validation_results['correct_predictions'] / validation_results['total_tests']
                validation_results['overall_accuracy'] = overall_accuracy
                
                print(f"[SEMANTIC-TRAINING] 🎯 Précision globale: {validation_results['correct_predictions']}/{validation_results['total_tests']} ({overall_accuracy*100:.1f}%)")
            
            return validation_results
            
        except Exception as e:
            print(f"[SEMANTIC-TRAINING] ❌ Erreur validation: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_training_quality_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de qualité des données d'entraînement
        
        Returns:
            Dict: Rapport détaillé
        """
        print("[SEMANTIC-TRAINING] 📋 Génération du rapport de qualité...")
        
        report = {
            'data_distribution': {},
            'text_quality': {},
            'competitor_coverage': {},
            'temporal_distribution': {},
            'recommendations': []
        }
        
        try:
            # 1. Distribution des données
            total = sum(len(examples) for examples in self.training_data.values())
            if total == 0:
                return {'error': 'Aucune donnée d\'entraînement disponible'}
            
            for category, examples in self.training_data.items():
                count = len(examples)
                percentage = count / total * 100
                report['data_distribution'][category] = {
                    'count': count,
                    'percentage': f"{percentage:.1f}%",
                    'balanced': 20 <= percentage <= 50  # Équilibre acceptable
                }
            
            # 2. Qualité des textes
            all_examples = []
            for examples in self.training_data.values():
                all_examples.extend(examples)
            
            if all_examples:
                titles_lengths = [len(ex['title'].split()) for ex in all_examples]
                descriptions_lengths = [len(ex['description'].split()) for ex in all_examples if ex['description']]
                
                report['text_quality'] = {
                    'total_examples': len(all_examples),
                    'avg_title_length': np.mean(titles_lengths) if titles_lengths else 0,
                    'avg_description_length': np.mean(descriptions_lengths) if descriptions_lengths else 0,
                    'examples_with_description': len(descriptions_lengths),
                    'description_coverage': f"{len(descriptions_lengths)/len(all_examples)*100:.1f}%"
                }
            
            # 3. Couverture par concurrent
            competitor_counts = Counter()
            for examples in self.training_data.values():
                for ex in examples:
                    competitor_counts[ex.get('competitor', 'Unknown')] += 1
            
            report['competitor_coverage'] = dict(competitor_counts.most_common())
            
            # 4. Recommandations
            recommendations = []
            
            # Déséquilibre des classes
            hero_pct = report['data_distribution'].get('hero', {}).get('percentage', '0%')
            hub_pct = report['data_distribution'].get('hub', {}).get('percentage', '0%')
            help_pct = report['data_distribution'].get('help', {}).get('percentage', '0%')
            
            hero_val = float(hero_pct.rstrip('%'))
            hub_val = float(hub_pct.rstrip('%'))
            help_val = float(help_pct.rstrip('%'))
            
            if max(hero_val, hub_val, help_val) > 60:
                recommendations.append("⚠️ Déséquilibre des classes détecté - considérer équilibrer les données")
            
            if report['text_quality'].get('description_coverage', '0%').rstrip('%') and float(report['text_quality']['description_coverage'].rstrip('%')) < 50:
                recommendations.append("📄 Peu de descriptions disponibles - enrichir avec plus de contexte")
            
            if total < 50:
                recommendations.append("📊 Dataset petit - collecter plus de classifications humaines")
            
            if len(competitor_counts) == 1:
                recommendations.append("🏢 Un seul concurrent - diversifier les sources de données")
            
            report['recommendations'] = recommendations
            
            return report
            
        except Exception as e:
            print(f"[SEMANTIC-TRAINING] ❌ Erreur rapport: {e}")
            return {'error': str(e)}
    
    def save_training_data(self, filepath: str):
        """
        Sauvegarde les données d'entraînement
        
        Args:
            filepath: Chemin de sauvegarde
        """
        training_export = {
            'training_data': self.training_data,
            'training_stats': self.training_stats,
            'export_date': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(training_export, f, indent=2, ensure_ascii=False)
        
        print(f"[SEMANTIC-TRAINING] 💾 Données sauvegardées: {filepath}")
    
    def load_training_data(self, filepath: str):
        """
        Charge des données d'entraînement sauvegardées
        
        Args:
            filepath: Chemin de chargement
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.training_data = data['training_data']
            self.training_stats = data['training_stats']
            
            print(f"[SEMANTIC-TRAINING] 📂 Données chargées: {filepath}")
            print(f"[SEMANTIC-TRAINING] 📊 {sum(len(ex) for ex in self.training_data.values())} exemples chargés")
            
        except Exception as e:
            print(f"[SEMANTIC-TRAINING] ❌ Erreur chargement: {e}")


def create_domain_specific_model() -> Dict[str, Any]:
    """
    Fonction principale pour créer un modèle spécialisé sur le domaine utilisateur
    
    Returns:
        Dict: Résultats complets du processus
    """
    print("🎓 CRÉATION D'UN MODÈLE SÉMANTIQUE SPÉCIALISÉ")
    print("=" * 60)
    
    # 1. Initialisation
    trainer = SemanticTrainingManager()
    
    # 2. Extraction des données
    print("\n📊 ÉTAPE 1: Extraction des classifications humaines")
    extraction_result = trainer.extract_human_classifications()
    
    if not extraction_result['success']:
        return extraction_result
    
    # 3. Rapport de qualité
    print("\n📋 ÉTAPE 2: Analyse de la qualité des données")
    quality_report = trainer.get_training_quality_report()
    
    # 4. Entraînement
    print("\n🎓 ÉTAPE 3: Entraînement du modèle")
    training_result = trainer.train_semantic_model()
    
    if not training_result['success']:
        return training_result
    
    # 5. Validation
    print("\n🧪 ÉTAPE 4: Validation du modèle")
    validation_result = trainer.validate_training()
    
    # 6. Sauvegarde
    print("\n💾 ÉTAPE 5: Sauvegarde")
    save_path = "trained_semantic_model.json"
    trainer.save_training_data(save_path)
    
    # Résultats finaux
    final_results = {
        'success': True,
        'extraction': extraction_result,
        'quality_report': quality_report,
        'training': training_result,
        'validation': validation_result,
        'model_path': save_path,
        'trained_classifier': trainer.classifier
    }
    
    print("\n✅ MODÈLE SPÉCIALISÉ CRÉÉ AVEC SUCCÈS!")
    print(f"📊 {extraction_result['stats']['total_examples']} exemples utilisés")
    if 'overall_accuracy' in validation_result:
        print(f"🎯 Précision: {validation_result['overall_accuracy']*100:.1f}%")
    
    return final_results


if __name__ == "__main__":
    # Test du système d'entraînement
    result = create_domain_specific_model()
    
    if result['success']:
        print("\n🎉 Succès! Votre modèle sémantique est maintenant spécialisé")
        print("   sur vos données Club Med et voyage.")
    else:
        print(f"\n❌ Erreur: {result.get('error', 'Erreur inconnue')}") 