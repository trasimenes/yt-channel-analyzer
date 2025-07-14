"""
Module de classification sémantique pour HUB/HERO/HELP
Utilise des embeddings sémantiques pour une vraie compréhension du contenu
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import pickle
import os
from datetime import datetime

class SemanticHubHeroHelpClassifier:
    """
    Classificateur sémantique basé sur les embeddings de phrases
    Comprend réellement le sens plutôt que de faire du matching de mots-clés
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialise le classificateur sémantique
        
        Args:
            model_name: Nom du modèle sentence-transformers à utiliser
                      - all-MiniLM-L6-v2: Petit, rapide (22MB, 384 dimensions)
                      - all-MiniLM-L12-v2: Plus précis (33MB, 384 dimensions)
                      - paraphrase-MiniLM-L6-v2: Optimisé pour paraphrases
        """
        print(f"[SEMANTIC] 🧠 Initialisation du classificateur sémantique avec {model_name}")
        
        try:
            self.model = SentenceTransformer(model_name)
            print(f"[SEMANTIC] ✅ Modèle {model_name} chargé avec succès")
        except Exception as e:
            print(f"[SEMANTIC] ❌ Erreur lors du chargement du modèle: {e}")
            print("[SEMANTIC] 🔄 Installation automatique de sentence-transformers...")
            import subprocess
            subprocess.run(["pip", "install", "sentence-transformers"], check=True)
            self.model = SentenceTransformer(model_name)
        
        # Définition des exemples prototypes pour chaque catégorie
        self.category_prototypes = {
            'hero': [
                "Nouvelle collection exclusive lancée en avant-première",
                "Événement spécial et lancement de produit révolutionnaire", 
                "Actualité importante et annonce majeure",
                "Première mondiale et révélation exclusive",
                "Campagne marketing de grande envergure",
                "Contenu viral et buzz médiatique",
                "Innovation révolutionnaire et technologie de pointe"
            ],
            'hub': [
                "Série régulière de voyage et découverte de destinations",
                "Contenu hebdomadaire sur les expériences client",
                "Programme récurrent de présentation des services",
                "Collection de témoignages et retours d'expérience",
                "Série documentaire sur les coulisses",
                "Contenu éducatif et informatif régulier",
                "Présentation des équipes et des métiers"
            ],
            'help': [
                "Comment résoudre un problème technique",
                "Guide étape par étape pour utiliser un service",
                "Tutoriel détaillé et mode d'emploi",
                "Réponses aux questions fréquentes",
                "Aide pour configurer et paramétrer",
                "Support technique et dépannage",
                "Instructions détaillées et marche à suivre"
            ]
        }
        
        # Calcul des embeddings pour les prototypes
        self.prototype_embeddings = {}
        for category, prototypes in self.category_prototypes.items():
            embeddings = self.model.encode(prototypes)
            # Moyenne des embeddings des prototypes pour cette catégorie
            self.prototype_embeddings[category] = np.mean(embeddings, axis=0)
            print(f"[SEMANTIC] 📊 Prototypes {category.upper()}: {len(prototypes)} exemples")
    
    def classify_text(self, text: str, description: str = "") -> Tuple[str, float, Dict]:
        """
        Classifie un texte selon HUB/HERO/HELP avec compréhension sémantique
        
        Args:
            text: Texte principal (titre)
            description: Description additionnelle (optionnel)
            
        Returns:
            Tuple[str, float, Dict]: (catégorie, confiance, détails)
        """
        # Combinaison du texte et de la description
        combined_text = f"{text} {description}".strip()
        
        # Génération de l'embedding pour le texte
        text_embedding = self.model.encode([combined_text])[0]
        
        # Calcul de la similarité avec chaque prototype
        similarities = {}
        for category, prototype_embedding in self.prototype_embeddings.items():
            similarity = cosine_similarity(
                [text_embedding], 
                [prototype_embedding]
            )[0][0]
            similarities[category] = similarity
        
        # Détermination de la catégorie avec la plus forte similarité
        best_category = max(similarities, key=similarities.get)
        confidence = similarities[best_category]
        
        # Conversion en pourcentage et ajustement
        confidence_percentage = min(95, max(50, confidence * 100))
        
        details = {
            'similarities': similarities,
            'method': 'semantic_embedding',
            'model': self.model._modules['0'].auto_model.config.name_or_path,
            'embedding_dimension': len(text_embedding),
            'text_length': len(combined_text)
        }
        
        print(f"[SEMANTIC] 🎯 '{text[:50]}...' → {best_category.upper()} ({confidence_percentage:.1f}%)")
        
        return best_category, confidence_percentage, details
    
    def add_example(self, text: str, category: str, description: str = ""):
        """
        Ajoute un nouvel exemple d'apprentissage pour améliorer la classification
        
        Args:
            text: Texte de l'exemple
            category: Catégorie correcte (hero/hub/help)
            description: Description additionnelle
        """
        if category not in self.category_prototypes:
            print(f"[SEMANTIC] ❌ Catégorie invalide: {category}")
            return
        
        combined_text = f"{text} {description}".strip()
        
        # Ajout à la liste des prototypes
        self.category_prototypes[category].append(combined_text)
        
        # Recalcul des embeddings pour cette catégorie
        prototypes = self.category_prototypes[category]
        embeddings = self.model.encode(prototypes)
        self.prototype_embeddings[category] = np.mean(embeddings, axis=0)
        
        print(f"[SEMANTIC] ✅ Exemple ajouté pour {category.upper()}: '{text[:50]}...'")
        print(f"[SEMANTIC] 📊 Total prototypes {category.upper()}: {len(prototypes)}")
    
    def explain_classification(self, text: str, description: str = "") -> Dict:
        """
        Explique pourquoi un texte a été classifié dans une catégorie donnée
        
        Args:
            text: Texte à analyser
            description: Description additionnelle
            
        Returns:
            Dict: Explication détaillée de la classification
        """
        combined_text = f"{text} {description}".strip()
        text_embedding = self.model.encode([combined_text])[0]
        
        # Calcul des similarités avec tous les prototypes individuels
        detailed_similarities = {}
        
        for category, prototypes in self.category_prototypes.items():
            category_similarities = []
            prototype_embeddings = self.model.encode(prototypes)
            
            for i, prototype in enumerate(prototypes):
                similarity = cosine_similarity(
                    [text_embedding], 
                    [prototype_embeddings[i]]
                )[0][0]
                category_similarities.append({
                    'prototype': prototype,
                    'similarity': similarity
                })
            
            # Tri par similarité décroissante
            category_similarities.sort(key=lambda x: x['similarity'], reverse=True)
            detailed_similarities[category] = category_similarities
        
        # Classification finale
        category, confidence, details = self.classify_text(text, description)
        
        return {
            'text': combined_text,
            'predicted_category': category,
            'confidence': confidence,
            'top_matches_per_category': {
                cat: sims[:3] for cat, sims in detailed_similarities.items()
            },
            'reasoning': self._generate_reasoning(category, detailed_similarities)
        }
    
    def _generate_reasoning(self, predicted_category: str, detailed_similarities: Dict) -> str:
        """
        Génère une explication textuelle de la classification
        """
        top_match = detailed_similarities[predicted_category][0]
        reasoning = f"Classifié comme {predicted_category.upper()} car le texte ressemble le plus à: "
        reasoning += f"'{top_match['prototype']}' (similarité: {top_match['similarity']:.3f})"
        
        return reasoning
    
    def save_model(self, filepath: str):
        """
        Sauvegarde le modèle et ses prototypes
        """
        model_data = {
            'category_prototypes': self.category_prototypes,
            'prototype_embeddings': self.prototype_embeddings,
            'model_name': self.model._modules['0'].auto_model.config.name_or_path,
            'created_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"[SEMANTIC] 💾 Modèle sauvegardé: {filepath}")
    
    def load_model(self, filepath: str):
        """
        Charge un modèle sauvegardé
        """
        if not os.path.exists(filepath):
            print(f"[SEMANTIC] ❌ Fichier non trouvé: {filepath}")
            return
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.category_prototypes = model_data['category_prototypes']
        self.prototype_embeddings = model_data['prototype_embeddings']
        
        print(f"[SEMANTIC] 📂 Modèle chargé: {filepath}")
        print(f"[SEMANTIC] 📊 Prototypes chargés: {sum(len(p) for p in self.category_prototypes.values())}")


def test_semantic_classifier():
    """
    Fonction de test pour démontrer l'utilisation du classificateur sémantique
    """
    print("\n" + "="*60)
    print("🧪 TEST DU CLASSIFICATEUR SÉMANTIQUE")
    print("="*60)
    
    # Initialisation
    classifier = SemanticHubHeroHelpClassifier()
    
    # Tests avec différents types de contenus
    test_cases = [
        {
            'text': "Découvrez notre nouvelle collection été 2024",
            'description': "Lancement exclusif de notre gamme estivale avec des modèles inédits",
            'expected': 'hero'
        },
        {
            'text': "Comment bien choisir sa destination de vacances",
            'description': "Guide complet pour sélectionner l'endroit parfait selon vos critères",
            'expected': 'help'
        },
        {
            'text': "Voyage en Toscane - Episode 3",
            'description': "Suite de notre série documentaire sur les régions italiennes",
            'expected': 'hub'
        },
        {
            'text': "Tutoriel réservation en ligne",
            'description': "Étapes détaillées pour réserver votre séjour sur notre site web",
            'expected': 'help'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}:")
        print(f"📝 Texte: {test_case['text']}")
        print(f"📄 Description: {test_case['description']}")
        
        category, confidence, details = classifier.classify_text(
            test_case['text'], 
            test_case['description']
        )
        
        # Explication détaillée
        explanation = classifier.explain_classification(
            test_case['text'], 
            test_case['description']
        )
        
        print(f"🎯 Prédiction: {category.upper()} ({confidence:.1f}%)")
        print(f"✅ Attendu: {test_case['expected'].upper()}")
        print(f"💭 Explication: {explanation['reasoning']}")
        
        if category == test_case['expected']:
            print("✅ SUCCÈS")
        else:
            print("❌ ÉCHEC")
    
    print("\n" + "="*60)
    print("🏁 FIN DES TESTS")
    print("="*60)


if __name__ == "__main__":
    test_semantic_classifier() 