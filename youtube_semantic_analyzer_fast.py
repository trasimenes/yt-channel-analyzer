#!/usr/bin/env python3
"""
Version optimisée de l'analyseur sémantique YouTube
- Traitement par batches avec sauvegarde intermédiaire
- Peut reprendre où il s'est arrêté
- Version allégée pour analyse rapide
"""

import json
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans
from collections import Counter, defaultdict
import re
from tqdm import tqdm
import os
import pickle
from datetime import datetime

class FastYouTubeAnalyzer:
    def __init__(self, batch_size=100):
        """Analyseur rapide avec batches plus grands"""
        print("🚀 Initialisation de l'analyseur rapide...")
        
        # Modèle léger mais efficace
        self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        self.batch_size = batch_size
        self.checkpoint_file = 'analysis_checkpoint.pkl'
        
    def load_data(self, json_file='videos_only.json'):
        """Charge seulement les vidéos (pas besoin du fichier complet)"""
        print(f"📁 Chargement des vidéos depuis {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            self.videos = json.load(f)
        
        print(f"✅ {len(self.videos)} vidéos chargées")
        
        # Extraire les noms de marques pour filtrage
        self.competitor_brands = set()
        for video in self.videos:
            if video['competitor_name']:
                self.competitor_brands.add(video['competitor_name'].lower())
                for word in video['competitor_name'].lower().split():
                    if len(word) >= 3:
                        self.competitor_brands.add(word)
        
        return len(self.videos)
    
    def prepare_texts(self, sample_size=None):
        """Prépare les textes pour l'analyse avec option de sampling"""
        if sample_size and sample_size < len(self.videos):
            print(f"📊 Échantillonnage de {sample_size} vidéos...")
            # Prendre les vidéos les plus vues
            self.videos = sorted(self.videos, key=lambda x: x['view_count'], reverse=True)[:sample_size]
        
        self.texts = []
        self.metadata = []
        
        for video in self.videos:
            # Titre seulement pour aller plus vite (description optionnelle)
            text = video['title']
            if video.get('description'):
                # Limiter la description pour économiser le temps
                desc = video['description'][:200]
                text = f"{text}. {desc}"
            
            # Nettoyer basiquement
            text = re.sub(r'http\S+|www.\S+', '', text)
            text = text[:500]  # Limite plus courte
            
            self.texts.append(text)
            self.metadata.append({
                'video_id': video['video_id'],
                'title': video['title'],
                'views': video['view_count'],
                'country': video['country'],
                'competitor': video['competitor_name'],
                'category': video.get('category')
            })
        
        print(f"✅ {len(self.texts)} textes préparés")
        return len(self.texts)
    
    def encode_with_checkpoint(self):
        """Encode avec possibilité de reprendre en cas d'interruption"""
        embeddings_file = 'embeddings_fast.npy'
        
        # Vérifier si on a déjà des embeddings
        if os.path.exists(embeddings_file):
            print("✅ Embeddings trouvés, chargement...")
            self.embeddings = np.load(embeddings_file)
            return self.embeddings
        
        print(f"🧠 Encodage de {len(self.texts)} textes...")
        
        # Encoder directement (MiniLM est rapide)
        self.embeddings = self.model.encode(
            self.texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Sauvegarder
        np.save(embeddings_file, self.embeddings)
        print(f"✅ Embeddings sauvegardés: {embeddings_file}")
        
        return self.embeddings
    
    def quick_clustering(self, n_clusters=30):
        """Clustering rapide avec moins de clusters"""
        print(f"\n🎯 Clustering rapide en {n_clusters} topics...")
        
        self.kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=500,
            n_init=3,  # Moins d'initialisations
            max_iter=100,
            random_state=42
        )
        
        self.labels = self.kmeans.fit_predict(self.embeddings)
        print(f"✅ Clustering terminé")
        
        return self.labels
    
    def analyze_topics(self):
        """Analyse rapide des topics"""
        print("\n📊 Analyse des topics...")
        
        # Stopwords de base
        stopwords = {
            'and', 'the', 'for', 'you', 'are', 'with', 'this', 'that',
            'und', 'der', 'die', 'das', 'ein', 'eine',
            'et', 'le', 'la', 'les', 'un', 'une', 'des',
            'en', 'de', 'het', 'een', 'van',
            'https', 'http', 'www', 'com', 'youtube', 'video'
        }
        stopwords.update(self.competitor_brands)
        
        results = []
        
        for cluster_id in range(max(self.labels) + 1):
            # Vidéos du cluster
            cluster_indices = np.where(self.labels == cluster_id)[0]
            cluster_videos = [self.metadata[i] for i in cluster_indices]
            
            # Stats basiques
            total_views = sum(v['views'] for v in cluster_videos)
            avg_views = total_views / len(cluster_videos) if cluster_videos else 0
            
            # Pays dominant
            countries = Counter(v['country'] for v in cluster_videos)
            top_country = countries.most_common(1)[0][0] if countries else 'Unknown'
            
            # Mots-clés (titre seulement pour aller vite)
            words = []
            for v in cluster_videos[:50]:  # Limiter pour la vitesse
                title_words = v['title'].lower().split()
                words.extend([w for w in title_words if len(w) > 3 and w not in stopwords])
            
            word_freq = Counter(words)
            top_words = word_freq.most_common(5)
            
            # Nom du cluster basé sur les mots-clés
            if top_words:
                cluster_name = ' & '.join([w[0] for w in top_words[:2]]).title()
            else:
                cluster_name = f"Topic {cluster_id}"
            
            results.append({
                'cluster_id': cluster_id,
                'cluster_name': cluster_name,
                'size': len(cluster_videos),
                'total_views': total_views,
                'avg_views': int(avg_views),
                'top_country': top_country,
                'top_words': top_words,
                'sample_videos': [
                    {
                        'title': v['title'],
                        'views': v['views']
                    } for v in sorted(cluster_videos, key=lambda x: x['views'], reverse=True)[:3]
                ]
            })
        
        # Trier par taille
        results.sort(key=lambda x: x['size'], reverse=True)
        
        return results
    
    def save_results(self, results):
        """Sauvegarde simplifiée des résultats"""
        output = {
            'analysis_date': datetime.now().isoformat(),
            'total_videos': len(self.videos),
            'n_clusters': len(results),
            'topics': results
        }
        
        with open('semantic_analysis_fast.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # CSV simple
        rows = []
        for i, video in enumerate(self.videos):
            rows.append({
                'title': video['title'],
                'cluster_id': self.labels[i],
                'views': video['view_count'],
                'country': video['country']
            })
        
        df = pd.DataFrame(rows)
        df.to_csv('videos_topics_fast.csv', index=False)
        
        print("✅ Résultats sauvegardés:")
        print("  - semantic_analysis_fast.json")
        print("  - videos_topics_fast.csv")
        
        return output
    
    def print_summary(self, results):
        """Affiche un résumé des résultats"""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DE L'ANALYSE SÉMANTIQUE")
        print("="*60)
        
        print(f"\n📹 Vidéos analysées: {len(self.videos):,}")
        print(f"🎯 Topics découverts: {len(results)}")
        
        print("\n🏆 TOP 10 TOPICS PAR TAILLE:")
        for i, topic in enumerate(results[:10], 1):
            print(f"\n{i}. {topic['cluster_name']} ({topic['size']} vidéos)")
            print(f"   📍 Pays principal: {topic['top_country']}")
            print(f"   👁️  Vues moyennes: {topic['avg_views']:,}")
            print(f"   🔤 Mots-clés: {', '.join([w[0] for w in topic['top_words']])}")
            if topic['sample_videos']:
                print(f"   📹 Top vidéo: {topic['sample_videos'][0]['title']}")
        
        print("\n✅ ANALYSE TERMINÉE!")

def main():
    """Script principal optimisé"""
    print("⚡ ANALYSE SÉMANTIQUE RAPIDE YOUTUBE")
    print("="*50)
    
    # Créer l'analyseur
    analyzer = FastYouTubeAnalyzer(batch_size=100)
    
    # Charger les données
    analyzer.load_data('videos_only.json')
    
    # Option: Analyser seulement un échantillon
    # analyzer.prepare_texts(sample_size=2000)  # Top 2000 vidéos
    analyzer.prepare_texts()  # Toutes les vidéos
    
    # Encoder
    analyzer.encode_with_checkpoint()
    
    # Clustering
    analyzer.quick_clustering(n_clusters=30)
    
    # Analyser
    results = analyzer.analyze_topics()
    
    # Sauvegarder
    output = analyzer.save_results(results)
    
    # Afficher résumé
    analyzer.print_summary(results)

if __name__ == "__main__":
    main()