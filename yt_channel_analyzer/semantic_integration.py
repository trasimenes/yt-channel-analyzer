"""
Module d'intégration de la classification sémantique avec l'application Flask
Permet une migration progressive vers la nouvelle approche
"""

from typing import Dict, List, Tuple, Optional, Any
import json
import os
from datetime import datetime
from .enhanced_classifier import EnhancedHubHeroHelpClassifier
from .database import get_db_connection, mark_human_classification

class SemanticIntegrationManager:
    """
    Gestionnaire d'intégration pour la classification sémantique
    Permet de basculer entre ancien et nouveau système
    """
    
    def __init__(self):
        self.classifier = None
        self.enabled = False
        self.config = {
            'semantic_weight': 0.7,
            'enable_semantic': True,
            'auto_learn': True,
            'confidence_threshold': 60
        }
        
        # Tentative d'initialisation du classificateur
        try:
            self._initialize_classifier()
        except Exception as e:
            print(f"[SEMANTIC-INTEGRATION] ❌ Erreur d'initialisation: {e}")
            self.enabled = False
    
    def _initialize_classifier(self):
        """
        Initialise le classificateur sémantique
        """
        try:
            self.classifier = EnhancedHubHeroHelpClassifier(
                semantic_weight=self.config['semantic_weight'],
                enable_semantic=self.config['enable_semantic']
            )
            self.enabled = True
            print("[SEMANTIC-INTEGRATION] ✅ Classificateur sémantique initialisé")
        except Exception as e:
            print(f"[SEMANTIC-INTEGRATION] ❌ Échec initialisation: {e}")
            raise
    
    def classify_video_semantic(self, title: str, description: str = "") -> Dict[str, Any]:
        """
        Classifie une vidéo avec le système sémantique
        Compatible avec l'interface existante
        
        Args:
            title: Titre de la vidéo
            description: Description de la vidéo
            
        Returns:
            Dict: Résultat de classification compatible avec l'existant
        """
        if not self.enabled:
            return self._fallback_classification(title, description)
        
        try:
            # Classification avec le nouveau système
            result = self.classifier.classify_content(title, description)
            
            # Conversion au format compatible
            return {
                'category': result['final_category'],
                'confidence': result['confidence'],
                'method': 'semantic_enhanced',
                'detected_language': 'fr',  # Détection automatique à implémenter
                'details': {
                    'semantic_used': 'semantic' in result['methods_used'],
                    'traditional_used': 'traditional' in result['methods_used'],
                    'hybrid_mode': result['method'] == 'hybrid',
                    'processing_time': result.get('processing_time', 0)
                }
            }
            
        except Exception as e:
            print(f"[SEMANTIC-INTEGRATION] ❌ Erreur classification: {e}")
            return self._fallback_classification(title, description)
    
    def _fallback_classification(self, title: str, description: str) -> Dict[str, Any]:
        """
        Classification de fallback en cas d'erreur
        """
        # Utilisation du système traditionnel
        try:
            from .database import classify_video_with_language
            category, language, confidence = classify_video_with_language(title, description)
            
            return {
                'category': category,
                'confidence': confidence,
                'method': 'traditional_fallback',
                'detected_language': language,
                'details': {
                    'fallback_reason': 'semantic_unavailable',
                    'semantic_used': False,
                    'traditional_used': True,
                    'hybrid_mode': False
                }
            }
        except Exception as e:
            print(f"[SEMANTIC-INTEGRATION] ❌ Erreur fallback: {e}")
            return {
                'category': 'hub',
                'confidence': 50,
                'method': 'default_fallback',
                'detected_language': 'fr',
                'details': {
                    'fallback_reason': 'all_methods_failed',
                    'semantic_used': False,
                    'traditional_used': False,
                    'hybrid_mode': False
                }
            }
    
    def batch_classify_videos(self, videos: List[Dict]) -> List[Dict]:
        """
        Classification en lot avec le système sémantique
        
        Args:
            videos: Liste de vidéos à classifier
            
        Returns:
            List[Dict]: Vidéos avec classifications améliorées
        """
        if not self.enabled:
            print("[SEMANTIC-INTEGRATION] ⚠️ Système sémantique désactivé, utilisation du système traditionnel")
            return videos
        
        classified_videos = []
        
        for video in videos:
            title = video.get('title', '')
            description = video.get('description', '')
            
            if not title:
                classified_videos.append(video)
                continue
            
            # Classification sémantique
            classification = self.classify_video_semantic(title, description)
            
            # Ajout des informations de classification
            video_enhanced = video.copy()
            video_enhanced.update({
                'category': classification['category'],
                'classification_confidence': classification['confidence'],
                'classification_method': classification['method'],
                'semantic_classification': True,
                'classification_details': classification['details']
            })
            
            classified_videos.append(video_enhanced)
        
        return classified_videos
    
    def get_classification_explanation(self, title: str, description: str = "") -> Dict:
        """
        Obtient une explication détaillée de la classification
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            
        Returns:
            Dict: Explication complète
        """
        if not self.enabled:
            return {'error': 'Système sémantique non disponible'}
        
        try:
            return self.classifier.get_explanation(title, description)
        except Exception as e:
            return {'error': f'Erreur lors de l\'explication: {e}'}
    
    def add_learning_feedback(self, title: str, description: str, correct_category: str, user_notes: str = ""):
        """
        Ajoute un feedback d'apprentissage
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            correct_category: Catégorie correcte
            user_notes: Notes utilisateur
        """
        if not self.enabled:
            print("[SEMANTIC-INTEGRATION] ⚠️ Système sémantique désactivé")
            return
        
        if not self.config['auto_learn']:
            print("[SEMANTIC-INTEGRATION] ⚠️ Apprentissage automatique désactivé")
            return
        
        try:
            self.classifier.add_feedback(title, description, correct_category, user_notes)
            print(f"[SEMANTIC-INTEGRATION] ✅ Feedback ajouté: {correct_category.upper()}")
        except Exception as e:
            print(f"[SEMANTIC-INTEGRATION] ❌ Erreur ajout feedback: {e}")
    
    def get_system_stats(self) -> Dict:
        """
        Retourne les statistiques du système
        """
        if not self.enabled:
            return {
                'enabled': False,
                'error': 'Système sémantique non disponible'
            }
        
        try:
            stats = self.classifier.get_stats()
            stats['enabled'] = True
            stats['config'] = self.config
            return stats
        except Exception as e:
            return {
                'enabled': False,
                'error': f'Erreur statistiques: {e}'
            }
    
    def update_config(self, new_config: Dict):
        """
        Met à jour la configuration du système
        
        Args:
            new_config: Nouvelle configuration
        """
        self.config.update(new_config)
        
        # Réinitialisation si nécessaire
        if self.enabled and ('semantic_weight' in new_config or 'enable_semantic' in new_config):
            try:
                self._initialize_classifier()
                print("[SEMANTIC-INTEGRATION] ✅ Configuration mise à jour")
            except Exception as e:
                print(f"[SEMANTIC-INTEGRATION] ❌ Erreur mise à jour config: {e}")
    
    def compare_classifications(self, title: str, description: str = "") -> Dict:
        """
        Compare les classifications traditionnelle et sémantique
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            
        Returns:
            Dict: Comparaison des deux méthodes
        """
        comparison = {
            'title': title,
            'description': description,
            'semantic_result': None,
            'traditional_result': None,
            'agreement': False,
            'confidence_difference': 0
        }
        
        # Classification sémantique
        if self.enabled:
            try:
                semantic_result = self.classify_video_semantic(title, description)
                comparison['semantic_result'] = semantic_result
            except Exception as e:
                comparison['semantic_result'] = {'error': str(e)}
        
        # Classification traditionnelle
        try:
            from .database import classify_video_with_language
            category, language, confidence = classify_video_with_language(title, description)
            comparison['traditional_result'] = {
                'category': category,
                'confidence': confidence,
                'method': 'traditional',
                'detected_language': language
            }
        except Exception as e:
            comparison['traditional_result'] = {'error': str(e)}
        
        # Analyse de l'accord
        if (comparison['semantic_result'] and 'category' in comparison['semantic_result'] and
            comparison['traditional_result'] and 'category' in comparison['traditional_result']):
            
            sem_cat = comparison['semantic_result']['category']
            trad_cat = comparison['traditional_result']['category']
            
            comparison['agreement'] = sem_cat == trad_cat
            comparison['confidence_difference'] = abs(
                comparison['semantic_result']['confidence'] - 
                comparison['traditional_result']['confidence']
            )
        
        return comparison


# Instance globale pour l'intégration
semantic_manager = SemanticIntegrationManager()


def get_semantic_manager() -> SemanticIntegrationManager:
    """
    Retourne l'instance du gestionnaire sémantique
    """
    return semantic_manager


def classify_video_enhanced(title: str, description: str = "") -> Tuple[str, str, int]:
    """
    Fonction de classification améliorée compatible avec l'interface existante
    
    Args:
        title: Titre de la vidéo
        description: Description de la vidéo
        
    Returns:
        Tuple[str, str, int]: (catégorie, langue, confiance)
    """
    try:
        result = semantic_manager.classify_video_semantic(title, description)
        return result['category'], result['detected_language'], result['confidence']
    except Exception as e:
        print(f"[SEMANTIC-INTEGRATION] ❌ Erreur classification améliorée: {e}")
        # Fallback vers le système traditionnel
        from .database import classify_video_with_language
        return classify_video_with_language(title, description)


def batch_classify_enhanced(videos: List[Dict]) -> List[Dict]:
    """
    Classification en lot améliorée
    
    Args:
        videos: Liste de vidéos à classifier
        
    Returns:
        List[Dict]: Vidéos avec classifications améliorées
    """
    return semantic_manager.batch_classify_videos(videos)


def add_semantic_feedback(title: str, description: str, correct_category: str, user_notes: str = ""):
    """
    Ajoute un feedback pour l'apprentissage sémantique
    
    Args:
        title: Titre du contenu
        description: Description du contenu
        correct_category: Catégorie correcte
        user_notes: Notes utilisateur
    """
    semantic_manager.add_learning_feedback(title, description, correct_category, user_notes)


def get_semantic_stats() -> Dict:
    """
    Retourne les statistiques du système sémantique
    """
    return semantic_manager.get_system_stats()


def compare_classification_methods(title: str, description: str = "") -> Dict:
    """
    Compare les méthodes de classification
    
    Args:
        title: Titre du contenu
        description: Description du contenu
        
    Returns:
        Dict: Comparaison des méthodes
    """
    return semantic_manager.compare_classifications(title, description) 