"""
Classificateur sémantique minimaliste sans dépendances lourdes
Alternative à sentence-transformers pour éviter les conflits
"""
import re
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import sqlite3
import json

class LightweightSemanticClassifier:
    """
    Classificateur sémantique basé sur TF-IDF et similarité cosinus
    Évite les conflits de dépendances avec sentence-transformers
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or 'instance/main.db'
        self.vocabulary = {}
        self.idf_scores = {}
        self.category_profiles = {
            'HUB': defaultdict(float),
            'HERO': defaultdict(float), 
            'HELP': defaultdict(float)
        }
        self.trained = False
        
    def _tokenize(self, text: str) -> List[str]:
        """Tokenise le texte en mots"""
        if not text:
            return []
        
        # Normaliser le texte
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Extraire les mots
        words = text.split()
        
        # Filtrer les mots courts et les mots vides
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'au', 'aux', 'en', 'dans', 'sur', 'avec', 'par', 'pour', 'sans', 'sous', 'vers', 'chez', 'dans', 'ce', 'cette', 'ces', 'son', 'sa', 'ses', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'notre', 'nos', 'votre', 'vos', 'leur', 'leurs', 'que', 'qui', 'quoi', 'où', 'quand', 'comment', 'pourquoi', 'est', 'sont', 'être', 'avoir', 'fait', 'faire', 'dit', 'dire', 'va', 'aller', 'vient', 'venir', 'peut', 'pouvoir', 'doit', 'devoir', 'veut', 'vouloir', 'sait', 'savoir', 'prend', 'prendre', 'donne', 'donner', 'met', 'mettre', 'trouve', 'trouver', 'voit', 'voir', 'part', 'partir', 'sort', 'sortir', 'reste', 'rester', 'passe', 'passer', 'arrive', 'arriver', 'entre', 'entrer', 'monte', 'monter', 'descend', 'descendre', 'tombe', 'tomber', 'porte', 'porter', 'garde', 'garder', 'laisse', 'laisser', 'change', 'changer', 'tourne', 'tourner', 'ouvre', 'ouvrir', 'ferme', 'fermer', 'commence', 'commencer', 'finit', 'finir', 'continue', 'continuer', 'arrête', 'arrêter', 'essaie', 'essayer', 'aide', 'aider', 'cherche', 'chercher', 'attend', 'attendre', 'répond', 'répondre', 'demande', 'demander', 'raconte', 'raconter', 'explique', 'expliquer', 'montre', 'montrer', 'apprend', 'apprendre', 'enseigne', 'enseigner', 'comprend', 'comprendre', 'connaît', 'connaître', 'semble', 'sembler', 'paraît', 'paraître', 'ressemble', 'ressembler', 'sent', 'sentir', 'entend', 'entendre', 'écoute', 'écouter', 'regarde', 'regarder', 'lit', 'lire', 'écrit', 'écrire', 'parle', 'parler', 'chante', 'chanter', 'joue', 'jouer', 'danse', 'danser', 'mange', 'manger', 'boit', 'boire', 'dort', 'dormir', 'se', 'ne', 'pas', 'plus', 'moins', 'très', 'trop', 'assez', 'bien', 'mal', 'mieux', 'pire', 'beaucoup', 'peu', 'encore', 'déjà', 'jamais', 'toujours', 'souvent', 'parfois', 'quelquefois', 'rarement', 'jamais', 'ici', 'là', 'partout', 'nulle', 'part', 'dehors', 'dedans', 'devant', 'derrière', 'dessus', 'dessous', 'à', 'côté', 'près', 'loin', 'aujourd', 'hui', 'hier', 'demain', 'maintenant', 'alors', 'après', 'avant', 'pendant', 'depuis', 'jusqu', 'bientôt', 'tard', 'tôt', 'oui', 'non', 'peut', 'être', 'aussi', 'donc', 'car', 'parce', 'comme', 'si', 'mais', 'ou', 'et', 'ni', 'soit', 'même', 'autre', 'plusieurs', 'tous', 'toutes', 'chaque', 'chacun', 'chacune', 'tout', 'toute', 'quelque', 'quelques', 'certain', 'certaine', 'certains', 'certaines', 'aucun', 'aucune', 'nul', 'nulle', 'tel', 'telle', 'tels', 'telles'}
        
        filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return filtered_words
    
    def _calculate_tf_idf(self, text: str, category_profile: Dict[str, float]) -> Dict[str, float]:
        """Calcule le score TF-IDF pour un texte"""
        words = self._tokenize(text)
        if not words:
            return {}
        
        # Calcul TF (Term Frequency)
        tf = defaultdict(float)
        for word in words:
            tf[word] += 1.0 / len(words)
        
        # Calcul TF-IDF
        tf_idf = {}
        for word, tf_score in tf.items():
            idf_score = self.idf_scores.get(word, 1.0)
            tf_idf[word] = tf_score * idf_score
        
        return tf_idf
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        if not vec1 or not vec2:
            return 0.0
        
        # Intersection des mots
        common_words = set(vec1.keys()) & set(vec2.keys())
        if not common_words:
            return 0.0
        
        # Produit scalaire
        dot_product = sum(vec1[word] * vec2[word] for word in common_words)
        
        # Normes
        norm1 = math.sqrt(sum(score ** 2 for score in vec1.values()))
        norm2 = math.sqrt(sum(score ** 2 for score in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def train_from_database(self) -> bool:
        """Entraîne le classificateur avec les données humaines de la base"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Récupérer les playlists classifiées humainement
            cursor.execute("""
                SELECT title, description, classification 
                FROM playlists 
                WHERE classification_source = 'human' 
                AND human_verified = 1
                AND classification IN ('HUB', 'HERO', 'HELP')
            """)
            
            playlist_data = cursor.fetchall()
            
            # Récupérer les vidéos classifiées humainement
            cursor.execute("""
                SELECT title, description, classification 
                FROM videos 
                WHERE classification_source = 'human' 
                AND human_verified = 1
                AND classification IN ('HUB', 'HERO', 'HELP')
            """)
            
            video_data = cursor.fetchall()
            
            # Récupérer les corrections humaines
            cursor.execute("""
                SELECT title, description, corrected_classification 
                FROM classification_feedback 
                WHERE corrected_classification IN ('HUB', 'HERO', 'HELP')
            """)
            
            feedback_data = cursor.fetchall()
            
            conn.close()
            
            # Combiner toutes les données
            all_data = []
            for title, desc, classification in playlist_data + video_data + feedback_data:
                text = f"{title or ''} {desc or ''}".strip()
                if text:
                    all_data.append((text, classification))
            
            if not all_data:
                print("❌ Aucune donnée d'entraînement trouvée")
                return False
            
            print(f"📊 Entraînement sur {len(all_data)} exemples")
            
            # Construire le vocabulaire et calculer IDF
            all_words = set()
            category_documents = defaultdict(list)
            
            for text, category in all_data:
                words = self._tokenize(text)
                all_words.update(words)
                category_documents[category].append(words)
            
            # Calcul IDF
            total_docs = len(all_data)
            for word in all_words:
                doc_count = sum(1 for text, _ in all_data if word in self._tokenize(text))
                self.idf_scores[word] = math.log(total_docs / (doc_count + 1))
            
            # Construire les profils de catégorie
            for category, documents in category_documents.items():
                word_counts = defaultdict(int)
                total_words = 0
                
                for words in documents:
                    for word in words:
                        word_counts[word] += 1
                        total_words += 1
                
                # Calcul TF-IDF moyen pour chaque mot dans la catégorie
                for word, count in word_counts.items():
                    tf = count / total_words
                    idf = self.idf_scores.get(word, 1.0)
                    self.category_profiles[category][word] = tf * idf
            
            self.trained = True
            print("✅ Entraînement terminé avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'entraînement: {e}")
            return False
    
    def classify_text(self, text: str) -> Tuple[str, float, Dict[str, Any]]:
        """Classifie un texte et retourne la catégorie, confiance et explication"""
        if not self.trained:
            return "INCONNU", 0.0, {"error": "Modèle non entraîné"}
        
        if not text or not text.strip():
            return "INCONNU", 0.0, {"error": "Texte vide"}
        
        # Calculer TF-IDF du texte
        text_vector = self._calculate_tf_idf(text, {})
        
        # Calculer similarité avec chaque catégorie
        similarities = {}
        for category, profile in self.category_profiles.items():
            similarity = self._cosine_similarity(text_vector, profile)
            similarities[category] = similarity
        
        # Trouver la meilleure catégorie
        best_category = max(similarities, key=similarities.get)
        best_score = similarities[best_category]
        
        # Explication
        explanation = {
            "similarities": similarities,
            "key_words": list(text_vector.keys())[:10],
            "method": "TF-IDF + Cosine Similarity"
        }
        
        return best_category, best_score, explanation
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'entraînement"""
        if not self.trained:
            return {"error": "Modèle non entraîné"}
        
        stats = {
            "vocabulary_size": len(self.idf_scores),
            "categories": list(self.category_profiles.keys()),
            "category_profiles": {}
        }
        
        for category, profile in self.category_profiles.items():
            stats["category_profiles"][category] = {
                "words_count": len(profile),
                "top_words": sorted(profile.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        
        return stats

# Fonction d'intégration compatible avec l'existant
def classify_with_lightweight_semantic(text: str, db_path: str = None) -> Tuple[str, float, str]:
    """
    Fonction compatible avec l'interface existante
    Retourne: (classification, confiance, explication)
    """
    classifier = LightweightSemanticClassifier(db_path)
    
    # Entraîner si nécessaire
    if not classifier.trained:
        classifier.train_from_database()
    
    # Classifier
    category, confidence, explanation = classifier.classify_text(text)
    
    # Formater l'explication
    explanation_text = f"Méthode: {explanation.get('method', 'N/A')}\n"
    explanation_text += f"Similarités: {explanation.get('similarities', {})}\n"
    explanation_text += f"Mots clés: {explanation.get('key_words', [])[:5]}"
    
    return category, confidence, explanation_text

# Test simple
if __name__ == "__main__":
    classifier = LightweightSemanticClassifier()
    
    # Test avec des exemples
    test_texts = [
        "Nos GO vous racontent leurs meilleures histoires",
        "Révélation exclusive sur les nouveaux villages",
        "Problème de réservation ? Voici la solution"
    ]
    
    print("🧪 Test du classificateur léger:")
    for text in test_texts:
        category, confidence, explanation = classifier.classify_text(text)
        print(f"📝 '{text}' → {category} ({confidence:.2f})") 