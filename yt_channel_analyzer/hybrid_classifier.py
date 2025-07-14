"""
Classificateur hybride final intégrant :
1. Classifications humaines (priorité absolue)
2. Classificateur sémantique (compréhension du sens)
3. Patterns traditionnels (mots-clés)
4. Règles personnalisées
5. Apprentissage continu

Ce module remplace progressivement les anciens classificateurs
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json

# Imports des systèmes existants
from .database import (
    classify_video_with_language, 
    get_db_connection,
    mark_human_classification,
    detect_language
)
from .supervised_learning import add_user_feedback, learn_from_feedback

# Import du nouveau système sémantique
try:
    from .semantic_classifier import SemanticHubHeroHelpClassifier
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    print("[HYBRID] ⚠️ Classificateur sémantique non disponible")

class HybridHubHeroHelpClassifier:
    """
    Classificateur hybride final qui combine :
    - Classifications humaines (priorité absolue)
    - Compréhension sémantique (nouveauté)
    - Patterns traditionnels (existant)
    - Apprentissage continu
    """
    
    def __init__(self, 
                 enable_semantic: bool = True,
                 semantic_weight: float = 0.7,
                 pattern_weight: float = 0.3,
                 db_path: str = "instance/main.db"):
        """
        Initialise le classificateur hybride
        
        Args:
            enable_semantic: Active le classificateur sémantique
            semantic_weight: Poids du classificateur sémantique (0.0-1.0)
            pattern_weight: Poids des patterns traditionnels (0.0-1.0)
            db_path: Chemin vers la base de données
        """
        self.db_path = db_path
        self.enable_semantic = enable_semantic and SEMANTIC_AVAILABLE
        self.semantic_weight = semantic_weight
        self.pattern_weight = pattern_weight
        
        # Statistiques d'usage
        self.stats = {
            'total_classifications': 0,
            'human_classifications': 0,
            'semantic_classifications': 0,
            'pattern_classifications': 0,
            'agreements': 0,
            'disagreements': 0
        }
        
        # Initialisation du classificateur sémantique
        if self.enable_semantic:
            try:
                self.semantic_classifier = SemanticHubHeroHelpClassifier()
                
                # Tentative de chargement du modèle entraîné
                model_path = "trained_semantic_model.pkl"
                if os.path.exists(model_path):
                    self.semantic_classifier.load_model(model_path)
                    print("[HYBRID] ✅ Modèle sémantique entraîné chargé")
                else:
                    print("[HYBRID] 📚 Modèle sémantique générique chargé")
                    
            except Exception as e:
                print(f"[HYBRID] ❌ Erreur chargement sémantique: {e}")
                self.enable_semantic = False
        
        print(f"[HYBRID] 🚀 Classificateur hybride initialisé")
        print(f"[HYBRID] 🧠 Sémantique: {'✅' if self.enable_semantic else '❌'}")
        print(f"[HYBRID] ⚖️  Poids sémantique: {semantic_weight:.1%}")
        print(f"[HYBRID] 📋 Poids patterns: {pattern_weight:.1%}")
    
    def classify_content(self, 
                        title: str, 
                        description: str = "",
                        video_id: int = None,
                        playlist_id: int = None,
                        force_method: str = None) -> Dict[str, Any]:
        """
        Classifie un contenu avec l'approche hybride complète
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            video_id: ID de la vidéo (pour vérifier les classifications humaines)
            playlist_id: ID de la playlist (pour vérifier les classifications humaines)
            force_method: Forcer une méthode ('semantic', 'pattern', 'human')
            
        Returns:
            Dict contenant la classification complète avec explications
        """
        self.stats['total_classifications'] += 1
        
        result = {
            'title': title,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'methods_used': [],
            'final_category': None,
            'confidence': 0,
            'classification_source': 'hybrid',
            'details': {
                'human_classification': None,
                'semantic_classification': None,
                'pattern_classification': None,
                'agreement_level': None,
                'explanation': ""
            }
        }
        
        # 1. PRIORITÉ ABSOLUE : Vérifier les classifications humaines
        human_result = self._get_human_classification(video_id, playlist_id)
        if human_result:
            result['methods_used'].append('human')
            result['final_category'] = human_result['category']
            result['confidence'] = 100
            result['classification_source'] = 'human'
            result['details']['human_classification'] = human_result
            result['details']['explanation'] = f"Classification humaine vérifiée : {human_result['category'].upper()}"
            
            self.stats['human_classifications'] += 1
            return result
        
        # 2. Si pas de classification humaine, utiliser l'approche hybride
        if force_method == 'semantic' and self.enable_semantic:
            return self._classify_semantic_only(title, description, result)
        elif force_method == 'pattern':
            return self._classify_pattern_only(title, description, result)
        else:
            return self._classify_hybrid(title, description, result)
    
    def _get_human_classification(self, video_id: int = None, playlist_id: int = None) -> Optional[Dict]:
        """Vérifie s'il existe une classification humaine pour ce contenu"""
        if not video_id and not playlist_id:
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if video_id:
                cursor.execute('''
                    SELECT category, classification_source, human_verified, classification_date
                    FROM video 
                    WHERE id = ? AND classification_source = 'human' AND human_verified = 1
                ''', (video_id,))
            else:
                cursor.execute('''
                    SELECT category, classification_source, human_verified, classification_date
                    FROM playlist 
                    WHERE id = ? AND classification_source = 'human' AND human_verified = 1
                ''', (playlist_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'category': row[0],
                    'source': row[1],
                    'verified': row[2],
                    'date': row[3]
                }
        except Exception as e:
            print(f"[HYBRID] ❌ Erreur vérification humaine: {e}")
        finally:
            conn.close()
        
        return None
    
    def _classify_semantic_only(self, title: str, description: str, result: Dict) -> Dict:
        """Classification sémantique uniquement"""
        if not self.enable_semantic:
            return self._classify_pattern_only(title, description, result)
        
        try:
            semantic_category, semantic_confidence, semantic_details = self.semantic_classifier.classify_text(
                title, description
            )
            
            result['methods_used'].append('semantic')
            result['final_category'] = semantic_category
            result['confidence'] = semantic_confidence
            result['details']['semantic_classification'] = {
                'category': semantic_category,
                'confidence': semantic_confidence,
                'details': semantic_details
            }
            result['details']['explanation'] = f"Classification sémantique : {semantic_category.upper()} (confiance: {semantic_confidence:.1f}%)"
            
            self.stats['semantic_classifications'] += 1
            return result
            
        except Exception as e:
            print(f"[HYBRID] ❌ Erreur classification sémantique: {e}")
            return self._classify_pattern_only(title, description, result)
    
    def _classify_pattern_only(self, title: str, description: str, result: Dict) -> Dict:
        """Classification par patterns uniquement"""
        try:
            pattern_category, detected_language, pattern_confidence = classify_video_with_language(
                title, description
            )
            
            result['methods_used'].append('pattern')
            result['final_category'] = pattern_category
            result['confidence'] = pattern_confidence
            result['details']['pattern_classification'] = {
                'category': pattern_category,
                'confidence': pattern_confidence,
                'language': detected_language
            }
            result['details']['explanation'] = f"Classification par patterns : {pattern_category.upper()} (confiance: {pattern_confidence}%)"
            
            self.stats['pattern_classifications'] += 1
            return result
            
        except Exception as e:
            print(f"[HYBRID] ❌ Erreur classification patterns: {e}")
            # Fallback ultime
            result['methods_used'].append('fallback')
            result['final_category'] = 'hub'
            result['confidence'] = 50
            result['details']['explanation'] = "Classification par défaut : HUB"
            return result
    
    def _classify_hybrid(self, title: str, description: str, result: Dict) -> Dict:
        """Classification hybride combinant sémantique + patterns"""
        semantic_result = None
        pattern_result = None
        
        # Classification sémantique
        if self.enable_semantic:
            try:
                semantic_category, semantic_confidence, semantic_details = self.semantic_classifier.classify_text(
                    title, description
                )
                semantic_result = {
                    'category': semantic_category,
                    'confidence': semantic_confidence,
                    'details': semantic_details
                }
                result['details']['semantic_classification'] = semantic_result
                result['methods_used'].append('semantic')
            except Exception as e:
                print(f"[HYBRID] ⚠️ Erreur sémantique: {e}")
        
        # Classification patterns
        try:
            pattern_category, detected_language, pattern_confidence = classify_video_with_language(
                title, description
            )
            pattern_result = {
                'category': pattern_category,
                'confidence': pattern_confidence,
                'language': detected_language
            }
            result['details']['pattern_classification'] = pattern_result
            result['methods_used'].append('pattern')
        except Exception as e:
            print(f"[HYBRID] ⚠️ Erreur patterns: {e}")
        
        # Combinaison intelligente des résultats
        final_category, final_confidence, explanation = self._combine_results(
            semantic_result, pattern_result
        )
        
        result['final_category'] = final_category
        result['confidence'] = final_confidence
        result['details']['explanation'] = explanation
        
        # Statistiques d'accord/désaccord
        if semantic_result and pattern_result:
            if semantic_result['category'] == pattern_result['category']:
                self.stats['agreements'] += 1
                result['details']['agreement_level'] = 'high'
            else:
                self.stats['disagreements'] += 1
                result['details']['agreement_level'] = 'low'
        
        return result
    
    def _combine_results(self, semantic_result: Optional[Dict], pattern_result: Optional[Dict]) -> Tuple[str, float, str]:
        """Combine intelligemment les résultats sémantique et patterns"""
        
        # Cas 1: Seulement sémantique
        if semantic_result and not pattern_result:
            return (
                semantic_result['category'], 
                semantic_result['confidence'], 
                f"Sémantique uniquement: {semantic_result['category'].upper()}"
            )
        
        # Cas 2: Seulement patterns
        if pattern_result and not semantic_result:
            return (
                pattern_result['category'], 
                pattern_result['confidence'], 
                f"Patterns uniquement: {pattern_result['category'].upper()}"
            )
        
        # Cas 3: Les deux disponibles
        if semantic_result and pattern_result:
            # Si accord parfait -> boost de confiance
            if semantic_result['category'] == pattern_result['category']:
                combined_confidence = min(95, 
                    semantic_result['confidence'] * self.semantic_weight + 
                    pattern_result['confidence'] * self.pattern_weight + 10
                )
                return (
                    semantic_result['category'],
                    combined_confidence,
                    f"Accord parfait sémantique + patterns: {semantic_result['category'].upper()}"
                )
            
            # Si désaccord -> utiliser le plus confiant
            if semantic_result['confidence'] >= pattern_result['confidence']:
                return (
                    semantic_result['category'],
                    semantic_result['confidence'] * self.semantic_weight,
                    f"Désaccord: sémantique prioritaire ({semantic_result['category'].upper()} vs {pattern_result['category'].upper()})"
                )
            else:
                return (
                    pattern_result['category'],
                    pattern_result['confidence'] * self.pattern_weight,
                    f"Désaccord: patterns prioritaires ({pattern_result['category'].upper()} vs {semantic_result['category'].upper()})"
                )
        
        # Cas 4: Fallback
        return ('hub', 50, "Fallback par défaut")
    
    def add_human_feedback(self, 
                          title: str, 
                          description: str, 
                          correct_category: str,
                          video_id: int = None,
                          playlist_id: int = None,
                          user_notes: str = "") -> Dict[str, Any]:
        """
        Ajoute un feedback humain et met à jour les systèmes d'apprentissage
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            correct_category: Catégorie correcte selon l'utilisateur
            video_id: ID de la vidéo (optionnel)
            playlist_id: ID de la playlist (optionnel)
            user_notes: Notes utilisateur
            
        Returns:
            Dict avec le résultat de l'ajout du feedback
        """
        try:
            # 1. Marquer comme classification humaine dans la base
            if video_id or playlist_id:
                success = mark_human_classification(
                    video_id=video_id,
                    playlist_id=playlist_id,
                    category=correct_category,
                    user_notes=user_notes
                )
                
                if not success:
                    return {'status': 'error', 'message': 'Erreur lors du marquage humain'}
            
            # 2. Ajouter feedback pour l'apprentissage supervisé
            if video_id:
                add_user_feedback(
                    video_id=video_id,
                    original_category='unknown',
                    corrected_category=correct_category,
                    confidence_score=100,
                    user_feedback_type='human_correction',
                    user_notes=user_notes
                )
            
            # 3. Entraîner le modèle sémantique si disponible
            if self.enable_semantic:
                try:
                    self.semantic_classifier.add_example(title, correct_category, description)
                    print(f"[HYBRID] ✅ Exemple ajouté au modèle sémantique: {correct_category.upper()}")
                except Exception as e:
                    print(f"[HYBRID] ⚠️ Erreur ajout exemple sémantique: {e}")
            
            return {
                'status': 'success',
                'message': f'Feedback humain ajouté: {correct_category.upper()}',
                'category': correct_category,
                'confidence': 100
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du système"""
        stats = self.stats.copy()
        stats['semantic_enabled'] = self.enable_semantic
        stats['semantic_weight'] = self.semantic_weight
        stats['pattern_weight'] = self.pattern_weight
        
        if stats['total_classifications'] > 0:
            stats['human_percentage'] = (stats['human_classifications'] / stats['total_classifications']) * 100
            stats['semantic_percentage'] = (stats['semantic_classifications'] / stats['total_classifications']) * 100
            stats['pattern_percentage'] = (stats['pattern_classifications'] / stats['total_classifications']) * 100
            
            total_agreements = stats['agreements'] + stats['disagreements']
            if total_agreements > 0:
                stats['agreement_rate'] = (stats['agreements'] / total_agreements) * 100
        
        return stats
    
    def explain_classification(self, title: str, description: str = "") -> Dict[str, Any]:
        """
        Explique en détail pourquoi un contenu a été classifié d'une certaine manière
        
        Args:
            title: Titre du contenu
            description: Description du contenu
            
        Returns:
            Dict avec explication détaillée
        """
        result = self.classify_content(title, description)
        
        explanation = {
            'title': title,
            'description': description,
            'final_decision': {
                'category': result['final_category'],
                'confidence': result['confidence'],
                'source': result['classification_source']
            },
            'methods_analyzed': result['methods_used'],
            'detailed_breakdown': result['details'],
            'reasoning': result['details']['explanation']
        }
        
        # Ajouter explication sémantique détaillée si disponible
        if self.enable_semantic and 'semantic' in result['methods_used']:
            try:
                semantic_explanation = self.semantic_classifier.explain_classification(title, description)
                explanation['semantic_reasoning'] = semantic_explanation
            except Exception as e:
                explanation['semantic_reasoning'] = {'error': str(e)}
        
        return explanation

# Instance globale pour l'application
hybrid_classifier = None

def get_hybrid_classifier() -> HybridHubHeroHelpClassifier:
    """Retourne l'instance globale du classificateur hybride (seulement si activé)"""
    global hybrid_classifier
    
    # Vérifier les paramètres avant l'initialisation
    try:
        from .database.base import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier si la classification sémantique est activée
        cursor.execute('''
            SELECT value FROM settings 
            WHERE key = 'semantic_classification_enabled'
        ''')
        result = cursor.fetchone()
        conn.close()
        
        # Si désactivée, lever une exception
        if not result or result[0].lower() != 'true':
            raise Exception("Classification sémantique désactivée - utiliser uniquement les données de la base")
            
    except Exception as e:
        print(f"[HYBRID] 🔒 Classification sémantique désactivée: {e}")
        raise Exception("Classification sémantique non disponible - mode database_only activé")
    
    # Seulement si activé, initialiser le classificateur
    if hybrid_classifier is None:
        print("[HYBRID] 🚀 Initialisation du classificateur hybride (activé explicitement)")
        hybrid_classifier = HybridHubHeroHelpClassifier()
    
    return hybrid_classifier

def classify_content_hybrid(title: str, description: str = "", **kwargs) -> Dict[str, Any]:
    """
    Fonction utilitaire pour classification hybride
    Compatible avec les interfaces existantes
    """
    classifier = get_hybrid_classifier()
    return classifier.classify_content(title, description, **kwargs)

def add_human_feedback_hybrid(title: str, description: str, correct_category: str, **kwargs) -> Dict[str, Any]:
    """
    Fonction utilitaire pour ajout de feedback humain
    Compatible avec les interfaces existantes
    """
    classifier = get_hybrid_classifier()
    return classifier.add_human_feedback(title, description, correct_category, **kwargs) 