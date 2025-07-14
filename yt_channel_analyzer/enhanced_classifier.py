"""
Classificateur amélioré combinant approche sémantique et patterns existants
Intégration avec le système existant pour une transition en douceur
"""

from typing import Dict, List, Tuple, Optional, Any
import json
import os
from datetime import datetime

from .semantic_classifier import SemanticHubHeroHelpClassifier
from .database import classify_video_with_language, detect_language

class EnhancedHubHeroHelpClassifier:
    """
    Classificateur hybride combinant:
    1. Compréhension sémantique (embeddings)
    2. Patterns traditionnels (fallback)
    3. Apprentissage continu
    """
    
    def __init__(self, 
                 semantic_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 enable_semantic: bool = True,
                 semantic_weight: float = 0.7):
        """
        Initialise le classificateur hybride
        
        Args:
            semantic_model: Modèle sentence-transformers à utiliser
            enable_semantic: Active/désactive la classification sémantique
            semantic_weight: Poids de la classification sémantique (0.0-1.0)
        """
        self.enable_semantic = enable_semantic
        self.semantic_weight = semantic_weight
        self.traditional_weight = 1.0 - semantic_weight
        
        print(f"[ENHANCED] 🚀 Initialisation du classificateur hybride")
        print(f"[ENHANCED] 🧠 Sémantique: {'✅ Activée' if enable_semantic else '❌ Désactivée'}")
        print(f"[ENHANCED] ⚖️  Poids sémantique: {semantic_weight:.1%}")
        
        # Initialisation du classificateur sémantique
        if self.enable_semantic:
            try:
                self.semantic_classifier = SemanticHubHeroHelpClassifier(semantic_model)
                print(f"[ENHANCED] ✅ Classificateur sémantique initialisé")
            except Exception as e:
                print(f"[ENHANCED] ❌ Erreur classificateur sémantique: {e}")
                print(f"[ENHANCED] 🔄 Basculement vers mode traditionnel uniquement")
                self.enable_semantic = False
        
        # Statistiques d'utilisation
        self.classification_stats = {
            'total_classifications': 0,
            'semantic_used': 0,
            'traditional_used': 0,
            'hybrid_used': 0,
            'accuracy_feedback': []
        }
    
    def classify_content(self, 
                        title: str, 
                        description: str = "",
                        use_traditional_fallback: bool = True) -> Dict[str, Any]:
        """
        Classifie un contenu avec l'approche hybride
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            use_traditional_fallback: Utiliser le système traditionnel en fallback
            
        Returns:
            Dict contenant la classification complète
        """
        result = {
            'title': title,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'methods_used': [],
            'final_category': None,
            'confidence': 0,
            'details': {}
        }
        
        self.classification_stats['total_classifications'] += 1
        
        # 1. Classification sémantique (si activée)
        semantic_result = None
        if self.enable_semantic:
            try:
                category, confidence, details = self.semantic_classifier.classify_text(title, description)
                semantic_result = {
                    'category': category,
                    'confidence': confidence,
                    'details': details
                }
                result['methods_used'].append('semantic')
                result['details']['semantic'] = semantic_result
                self.classification_stats['semantic_used'] += 1
                
                print(f"[ENHANCED] 🧠 Sémantique: {category.upper()} ({confidence:.1f}%)")
                
            except Exception as e:
                print(f"[ENHANCED] ❌ Erreur classification sémantique: {e}")
                semantic_result = None
        
        # 2. Classification traditionnelle (si fallback activé)
        traditional_result = None
        if use_traditional_fallback:
            try:
                category, detected_language, confidence = classify_video_with_language(title, description)
                traditional_result = {
                    'category': category,
                    'confidence': confidence,
                    'language': detected_language
                }
                result['methods_used'].append('traditional')
                result['details']['traditional'] = traditional_result
                self.classification_stats['traditional_used'] += 1
                
                print(f"[ENHANCED] 📝 Traditionnel: {category.upper()} ({confidence:.1f}%)")
                
            except Exception as e:
                print(f"[ENHANCED] ❌ Erreur classification traditionnelle: {e}")
                traditional_result = None
        
        # 3. Combinaison des résultats
        final_category, final_confidence = self._combine_results(semantic_result, traditional_result)
        
        result['final_category'] = final_category
        result['confidence'] = final_confidence
        
        # Détermination de la méthode utilisée
        if semantic_result and traditional_result:
            self.classification_stats['hybrid_used'] += 1
            result['method'] = 'hybrid'
            print(f"[ENHANCED] ⚖️  Hybride: {final_category.upper()} ({final_confidence:.1f}%)")
        elif semantic_result:
            result['method'] = 'semantic_only'
            print(f"[ENHANCED] 🧠 Sémantique seule: {final_category.upper()} ({final_confidence:.1f}%)")
        elif traditional_result:
            result['method'] = 'traditional_only'
            print(f"[ENHANCED] 📝 Traditionnel seul: {final_category.upper()} ({final_confidence:.1f}%)")
        else:
            result['method'] = 'fallback'
            result['final_category'] = 'hub'
            result['confidence'] = 50
            print(f"[ENHANCED] 🔄 Fallback: HUB (50%)")
        
        return result
    
    def _combine_results(self, semantic_result: Optional[Dict], traditional_result: Optional[Dict]) -> Tuple[str, float]:
        """
        Combine les résultats sémantique et traditionnel
        
        Args:
            semantic_result: Résultat de la classification sémantique
            traditional_result: Résultat de la classification traditionnelle
            
        Returns:
            Tuple[str, float]: (catégorie_finale, confiance_finale)
        """
        if semantic_result and traditional_result:
            # Mode hybride: pondération des deux approches
            
            # Si les deux méthodes sont d'accord, boost de confiance
            if semantic_result['category'] == traditional_result['category']:
                return semantic_result['category'], min(95, 
                    (semantic_result['confidence'] * self.semantic_weight + 
                     traditional_result['confidence'] * self.traditional_weight) + 10)
            
            # Si en désaccord, utiliser la méthode avec la plus forte confiance
            if semantic_result['confidence'] >= traditional_result['confidence']:
                return semantic_result['category'], semantic_result['confidence'] * self.semantic_weight
            else:
                return traditional_result['category'], traditional_result['confidence'] * self.traditional_weight
        
        elif semantic_result:
            return semantic_result['category'], semantic_result['confidence']
        
        elif traditional_result:
            return traditional_result['category'], traditional_result['confidence']
        
        else:
            return 'hub', 50  # Fallback par défaut
    
    def add_feedback(self, title: str, description: str, correct_category: str, user_notes: str = ""):
        """
        Ajoute un feedback utilisateur pour améliorer la classification
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            correct_category: Catégorie correcte selon l'utilisateur
            user_notes: Notes additionnelles
        """
        # Ajout à la classification sémantique
        if self.enable_semantic:
            self.semantic_classifier.add_example(title, correct_category, description)
        
        # Enregistrement du feedback
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'title': title,
            'description': description,
            'correct_category': correct_category,
            'user_notes': user_notes
        }
        
        self.classification_stats['accuracy_feedback'].append(feedback)
        
        print(f"[ENHANCED] ✅ Feedback ajouté: {correct_category.upper()} pour '{title[:50]}...'")
    
    def get_explanation(self, title: str, description: str = "") -> Dict:
        """
        Obtient une explication détaillée de la classification
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            
        Returns:
            Dict: Explication complète de la classification
        """
        explanation = {
            'content': {'title': title, 'description': description},
            'semantic_explanation': None,
            'traditional_explanation': None,
            'final_reasoning': None
        }
        
        # Explication sémantique
        if self.enable_semantic:
            try:
                semantic_explanation = self.semantic_classifier.explain_classification(title, description)
                explanation['semantic_explanation'] = semantic_explanation
            except Exception as e:
                explanation['semantic_explanation'] = f"Erreur: {e}"
        
        # Classification traditionnelle pour comparaison
        try:
            category, language, confidence = classify_video_with_language(title, description)
            explanation['traditional_explanation'] = {
                'category': category,
                'confidence': confidence,
                'language': language,
                'method': 'pattern_matching'
            }
        except Exception as e:
            explanation['traditional_explanation'] = f"Erreur: {e}"
        
        # Raisonnement final
        result = self.classify_content(title, description)
        explanation['final_reasoning'] = {
            'final_category': result['final_category'],
            'confidence': result['confidence'],
            'method': result['method'],
            'reasoning': self._generate_final_reasoning(result)
        }
        
        return explanation
    
    def _generate_final_reasoning(self, result: Dict) -> str:
        """
        Génère une explication textuelle du raisonnement final
        """
        method = result['method']
        category = result['final_category']
        confidence = result['confidence']
        
        if method == 'hybrid':
            return f"Classification hybride: combinaison des approches sémantique et traditionnelle → {category.upper()} ({confidence:.1f}%)"
        elif method == 'semantic_only':
            return f"Classification sémantique uniquement: compréhension du sens → {category.upper()} ({confidence:.1f}%)"
        elif method == 'traditional_only':
            return f"Classification traditionnelle uniquement: matching de patterns → {category.upper()} ({confidence:.1f}%)"
        else:
            return f"Classification par défaut: aucune méthode disponible → {category.upper()} ({confidence:.1f}%)"
    
    def get_stats(self) -> Dict:
        """
        Retourne les statistiques d'utilisation du classificateur
        """
        total = self.classification_stats['total_classifications']
        if total == 0:
            return {'message': 'Aucune classification effectuée'}
        
        return {
            'total_classifications': total,
            'method_usage': {
                'semantic': f"{self.classification_stats['semantic_used']} ({self.classification_stats['semantic_used']/total:.1%})",
                'traditional': f"{self.classification_stats['traditional_used']} ({self.classification_stats['traditional_used']/total:.1%})",
                'hybrid': f"{self.classification_stats['hybrid_used']} ({self.classification_stats['hybrid_used']/total:.1%})"
            },
            'configuration': {
                'semantic_enabled': self.enable_semantic,
                'semantic_weight': self.semantic_weight,
                'traditional_weight': self.traditional_weight
            },
            'feedback_received': len(self.classification_stats['accuracy_feedback'])
        }
    
    def save_configuration(self, filepath: str):
        """
        Sauvegarde la configuration et les statistiques
        """
        config = {
            'enable_semantic': self.enable_semantic,
            'semantic_weight': self.semantic_weight,
            'traditional_weight': self.traditional_weight,
            'stats': self.classification_stats,
            'created_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"[ENHANCED] 💾 Configuration sauvegardée: {filepath}")


def demonstrate_enhanced_classifier():
    """
    Démonstration du classificateur amélioré
    """
    print("\n" + "="*60)
    print("🎯 DÉMONSTRATION DU CLASSIFICATEUR AMÉLIORÉ")
    print("="*60)
    
    # Initialisation
    classifier = EnhancedHubHeroHelpClassifier(
        semantic_weight=0.8,  # Favoriser l'approche sémantique
        enable_semantic=True
    )
    
    # Tests de classification
    test_contents = [
        {
            'title': "Nouveau spa exclusif à Club Med Bali",
            'description': "Découvrez en avant-première notre nouveau spa de luxe avec des soins inédits inspirés de la tradition balinaise"
        },
        {
            'title': "Comment réserver votre séjour en ligne",
            'description': "Guide complet pour effectuer votre réservation sur notre site web en quelques clics"
        },
        {
            'title': "Destination France - Episode 5: La Provence",
            'description': "Cinquième épisode de notre série sur les destinations françaises, focus sur la région provençale"
        }
    ]
    
    for i, content in enumerate(test_contents, 1):
        print(f"\n🧪 Test {i}:")
        print(f"📝 Titre: {content['title']}")
        print(f"📄 Description: {content['description']}")
        
        # Classification
        result = classifier.classify_content(content['title'], content['description'])
        
        # Explication
        explanation = classifier.get_explanation(content['title'], content['description'])
        
        print(f"🎯 Résultat: {result['final_category'].upper()} ({result['confidence']:.1f}%)")
        print(f"🔧 Méthode: {result['method']}")
        print(f"💭 Explication: {explanation['final_reasoning']['reasoning']}")
        
        if explanation['semantic_explanation']:
            print(f"🧠 Sémantique: {explanation['semantic_explanation']['reasoning']}")
    
    # Statistiques
    print(f"\n📊 Statistiques:")
    stats = classifier.get_stats()
    print(f"🔢 Total classifications: {stats['total_classifications']}")
    print(f"📈 Utilisation des méthodes: {stats['method_usage']}")
    
    print("\n" + "="*60)
    print("🏁 FIN DE LA DÉMONSTRATION")
    print("="*60)


if __name__ == "__main__":
    demonstrate_enhanced_classifier() 