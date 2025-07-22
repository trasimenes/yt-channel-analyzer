#!/usr/bin/env python3
"""
Analyseur sémantique YouTube pour l'extraction de topics et analyse du ton de voix
Utilise le modèle E5-Large pour une analyse sémantique avancée des vidéos et playlists
"""

import json
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter, defaultdict
import time
from tqdm import tqdm
import re
from pathlib import Path


class YouTubeSemanticAnalyzer:
    """Analyseur sémantique pour YouTube avec modèle E5-Large"""
    
    def __init__(self, db_path='instance/database.db'):
        self.db_path = db_path
        self.model = None
        self.embeddings = None
        self.texts = None
        self.video_data = None
        self.playlist_data = None
        
    def load_model(self):
        """Charger le modèle multilingue optimisé"""
        print("🚀 Chargement du modèle all-mpnet-base-v2...")
        start_time = time.time()
        self.model = SentenceTransformer('all-mpnet-base-v2')
        print(f"✅ Modèle chargé en {time.time() - start_time:.1f}s")
        
    def extract_data(self, top_videos_per_competitor=50, top_playlists_per_competitor=50):
        """Extraire les top vidéos et playlists par concurrent"""
        print(f"📊 Extraction des top {top_videos_per_competitor} vidéos + {top_playlists_per_competitor} playlists par concurrent...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer les concurrents actifs
        cursor.execute("""
            SELECT DISTINCT id, name, country 
            FROM concurrent 
            WHERE name IS NOT NULL AND name != ''
            ORDER BY name
        """)
        competitors = cursor.fetchall()
        print(f"📈 {len(competitors)} concurrents trouvés")
        
        all_videos = []
        all_playlists = []
        
        for competitor_id, competitor_name, country in competitors:
            # Top vidéos par concurrent (par vues)
            cursor.execute("""
                SELECT 
                    v.id, v.title, v.description, v.view_count, v.like_count,
                    v.comment_count, v.published_at, v.category, c.name as competitor_name
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.concurrent_id = ? 
                    AND v.title IS NOT NULL 
                    AND v.title != ''
                    AND v.view_count IS NOT NULL
                ORDER BY v.view_count DESC
                LIMIT ?
            """, (competitor_id, top_videos_per_competitor))
            
            videos = cursor.fetchall()
            for video in videos:
                all_videos.append({
                    'id': video[0],
                    'title': video[1] or '',
                    'description': video[2] or '',
                    'view_count': video[3] or 0,
                    'like_count': video[4] or 0,
                    'comment_count': video[5] or 0,
                    'published_at': video[6] or '',
                    'category': video[7] or 'uncategorized',
                    'competitor_name': video[8],
                    'competitor_id': competitor_id,
                    'country': country
                })
            
            # Top playlists par concurrent (par nombre de vidéos)
            cursor.execute("""
                SELECT 
                    p.id, p.name, p.description, p.video_count, p.category,
                    c.name as competitor_name
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE p.concurrent_id = ?
                    AND p.name IS NOT NULL 
                    AND p.name != ''
                    AND p.video_count IS NOT NULL
                ORDER BY p.video_count DESC
                LIMIT ?
            """, (competitor_id, top_playlists_per_competitor))
            
            playlists = cursor.fetchall()
            for playlist in playlists:
                all_playlists.append({
                    'id': playlist[0],
                    'name': playlist[1] or '',
                    'description': playlist[2] or '',
                    'video_count': playlist[3] or 0,
                    'category': playlist[4] or 'uncategorized',
                    'competitor_name': playlist[5],
                    'competitor_id': competitor_id,
                    'country': country
                })
        
        conn.close()
        
        self.video_data = all_videos
        self.playlist_data = all_playlists
        
        print(f"✅ Extraction terminée: {len(all_videos)} vidéos + {len(all_playlists)} playlists")
        return all_videos, all_playlists
    
    def prepare_texts(self):
        """Préparer les textes pour l'analyse sémantique"""
        print("📝 Préparation des textes pour analyse sémantique...")
        
        texts = []
        metadata = []
        
        # Textes des vidéos
        for video in self.video_data:
            # Combiner titre et description
            text = f"{video['title']}. {video['description'][:1500]}"  # Limiter description
            texts.append(text)
            metadata.append({
                'type': 'video',
                'id': video['id'],
                'title': video['title'],
                'competitor': video['competitor_name'],
                'country': video['country'],
                'category': video['category'],
                'views': video['view_count'],
                'engagement': (video['like_count'] + video['comment_count']) / max(1, video['view_count'])
            })
        
        # Textes des playlists
        for playlist in self.playlist_data:
            # Combiner nom et description
            text = f"{playlist['name']}. {playlist['description'][:1500]}"
            texts.append(text)
            metadata.append({
                'type': 'playlist',
                'id': playlist['id'],
                'title': playlist['name'],
                'competitor': playlist['competitor_name'],
                'country': playlist['country'],
                'category': playlist['category'],
                'video_count': playlist['video_count']
            })
        
        self.texts = texts
        self.metadata = metadata
        
        print(f"✅ {len(texts)} textes préparés pour l'encodage")
        return texts, metadata
    
    def encode_texts(self, batch_size=16):
        """Encoder les textes avec le modèle E5-Large"""
        print("🔄 Encodage des textes avec E5-Large...")
        print("⏱️  Estimation: 30-60 minutes selon votre machine...")
        
        start_time = time.time()
        embeddings_list = []
        
        # Encoder par batches pour éviter les problèmes de mémoire
        for i in tqdm(range(0, len(self.texts), batch_size), desc="Encodage"):
            batch = self.texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            embeddings_list.append(batch_embeddings)
        
        # Combiner tous les embeddings
        self.embeddings = np.vstack(embeddings_list)
        
        duration = time.time() - start_time
        print(f"✅ Encodage terminé en {duration/60:.1f} minutes")
        print(f"📊 Shape des embeddings: {self.embeddings.shape}")
        
        # Sauvegarder les embeddings pour réutilisation
        np.save('embeddings_e5_large.npy', self.embeddings)
        print("💾 Embeddings sauvegardés dans 'embeddings_e5_large.npy'")
        
        return self.embeddings
    
    def cluster_topics(self, n_clusters=50):
        """Clustering des topics avec MiniBatchKMeans"""
        print(f"🎯 Clustering en {n_clusters} topics...")
        
        # Clustering avec MiniBatchKMeans pour la performance
        kmeans = MiniBatchKMeans(
            n_clusters=n_clusters, 
            random_state=42, 
            batch_size=1000,
            n_init=10
        )
        labels = kmeans.fit_predict(self.embeddings)
        
        print("✅ Clustering terminé")
        return labels, kmeans
    
    def analyze_tone_of_voice(self):
        """Analyser le ton de voix et les champs sémantiques"""
        print("🎭 Analyse du ton de voix et des champs sémantiques...")
        
        # Extraire tous les titres et descriptions
        all_text = []
        for video in self.video_data:
            all_text.extend([video['title'], video['description']])
        for playlist in self.playlist_data:
            all_text.extend([playlist['name'], playlist['description']])
        
        # Nettoyer et joindre les textes
        combined_text = ' '.join([text for text in all_text if text]).lower()
        
        # Analyse lexicale avec patterns français/anglais
        patterns = {
            'verbs_action': r'\b(découvr\w+|explor\w+|visit\w+|profitez|enjoy\w+|experienc\w+|discover\w+)\b',
            'verbs_emotion': r'\b(ador\w+|aim\w+|love\w+|passion\w+|émerveil\w+|amazing)\b',
            'adjectives_quality': r'\b(magnifique|beautiful|incroyable|amazing|exceptionnel|unique|authentique|genuine)\b',
            'family_terms': r'\b(famille|family|enfant\w+|children|kids|parents?)\b',
            'luxury_terms': r'\b(luxe|luxury|premium|exclusive|prestige|élégant|elegant)\b',
            'nature_terms': r'\b(nature|paysage|landscape|montagne|mountain|mer|sea|forêt|forest)\b',
        }
        
        tone_analysis = {}
        for category, pattern in patterns.items():
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            tone_analysis[category] = {
                'count': len(matches),
                'examples': list(set(matches))[:10]  # Top 10 exemples uniques
            }
        
        # Analyse TF-IDF pour les mots-clés importants
        vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words='english',  # Basique, améliorer avec stop words FR/EN
            min_df=2
        )
        
        # Préparer textes nettoyés
        clean_texts = [' '.join([m['title'] for m in self.metadata if m['title']])]
        if clean_texts[0]:  # Si on a des textes
            tfidf_matrix = vectorizer.fit_transform(clean_texts)
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Top mots-clés TF-IDF
            top_keywords = [(feature_names[i], tfidf_scores[i]) 
                           for i in tfidf_scores.argsort()[-20:][::-1]]
        else:
            top_keywords = []
        
        return tone_analysis, top_keywords
    
    def generate_report(self, labels, kmeans, tone_analysis, keywords):
        """Générer le rapport d'analyse complet"""
        print("📋 Génération du rapport d'analyse...")
        
        # Analyser les clusters
        cluster_analysis = defaultdict(lambda: {
            'videos': [],
            'playlists': [],
            'countries': Counter(),
            'categories': Counter(),
            'competitors': Counter(),
            'total_views': 0,
            'total_engagement': 0
        })
        
        # Associer chaque élément à son cluster
        for i, (label, meta) in enumerate(zip(labels, self.metadata)):
            cluster = cluster_analysis[int(label)]
            
            if meta['type'] == 'video':
                cluster['videos'].append(meta)
                cluster['total_views'] += meta['views']
                cluster['total_engagement'] += meta['engagement']
            else:  # playlist
                cluster['playlists'].append(meta)
            
            cluster['countries'][meta['country']] += 1
            cluster['categories'][meta['category']] += 1
            cluster['competitors'][meta['competitor']] += 1
        
        # Générer résumé par cluster
        cluster_summary = []
        for cluster_id, data in cluster_analysis.items():
            # Trouver le contenu le plus représentatif (plus de vues)
            top_content = None
            if data['videos']:
                top_content = max(data['videos'], key=lambda x: x['views'])
            elif data['playlists']:
                top_content = max(data['playlists'], key=lambda x: x['video_count'])
            
            cluster_summary.append({
                'cluster_id': cluster_id,
                'size': len(data['videos']) + len(data['playlists']),
                'videos_count': len(data['videos']),
                'playlists_count': len(data['playlists']),
                'top_countries': dict(data['countries'].most_common(3)),
                'top_categories': dict(data['categories'].most_common(3)),
                'top_competitors': dict(data['competitors'].most_common(3)),
                'representative_content': {
                    'title': top_content['title'] if top_content else 'N/A',
                    'type': top_content['type'] if top_content else 'N/A',
                    'competitor': top_content['competitor'] if top_content else 'N/A'
                },
                'total_views': data['total_views'],
                'avg_engagement': data['total_engagement'] / max(1, len(data['videos']))
            })
        
        # Trier par taille
        cluster_summary.sort(key=lambda x: x['size'], reverse=True)
        
        # Rapport complet
        report = {
            'status': 'completed',
            'timestamp': time.time(),
            'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_used': 'all-mpnet-base-v2',
            'data_summary': {
                'total_videos': len(self.video_data),
                'total_playlists': len(self.playlist_data),
                'total_competitors': len(set(m['competitor'] for m in self.metadata)),
                'total_countries': len(set(m['country'] for m in self.metadata)),
                'total_clusters': len(cluster_summary)
            },
            'clusters': cluster_summary[:50],  # Top 50 clusters
            'tone_of_voice': tone_analysis,
            'top_keywords': keywords,
            'semantic_insights': {
                'dominant_themes': [c['representative_content']['title'] for c in cluster_summary[:10]],
                'content_distribution': {
                    'videos_percentage': len(self.video_data) / (len(self.video_data) + len(self.playlist_data)) * 100,
                    'playlists_percentage': len(self.playlist_data) / (len(self.video_data) + len(self.playlist_data)) * 100
                }
            }
        }
        
        return report
    
    def run_full_analysis(self, top_videos=50, top_playlists=50, n_clusters=50):
        """Exécuter l'analyse complète"""
        print("🚀 Démarrage de l'analyse sémantique YouTube complète")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. Charger le modèle
            self.load_model()
            
            # 2. Extraire les données
            self.extract_data(top_videos, top_playlists)
            
            # 3. Préparer les textes
            self.prepare_texts()
            
            # 4. Encoder les textes
            self.encode_texts()
            
            # 5. Clustering
            labels, kmeans = self.cluster_topics(n_clusters)
            
            # 6. Analyse du ton de voix
            tone_analysis, keywords = self.analyze_tone_of_voice()
            
            # 7. Générer le rapport
            report = self.generate_report(labels, kmeans, tone_analysis, keywords)
            
            # 8. Sauvegarder les résultats
            output_file = 'youtube_semantic_analysis.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            total_time = time.time() - start_time
            print("=" * 60)
            print(f"✅ ANALYSE TERMINÉE en {total_time/60:.1f} minutes")
            print(f"📊 Résultats sauvegardés dans '{output_file}'")
            print(f"🎯 {len(report['clusters'])} clusters identifiés")
            print(f"🎭 Ton de voix analysé avec {len(report['tone_of_voice'])} dimensions")
            
            return report
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse: {e}")
            import traceback
            traceback.print_exc()
            return None



def main():
    """Fonction principale pour exécuter l'analyse"""
    analyzer = YouTubeSemanticAnalyzer()
    
    # Configuration
    TOP_VIDEOS_PER_COMPETITOR = 50
    TOP_PLAYLISTS_PER_COMPETITOR = 50
    N_CLUSTERS = 50
    
    print(f"Configuration:")
    print(f"  - Top vidéos par concurrent: {TOP_VIDEOS_PER_COMPETITOR}")
    print(f"  - Top playlists par concurrent: {TOP_PLAYLISTS_PER_COMPETITOR}")
    print(f"  - Nombre de clusters: {N_CLUSTERS}")
    print(f"  - Modèle: all-mpnet-base-v2")
    print()
    
    # Exécuter l'analyse
    report = analyzer.run_full_analysis(
        top_videos=TOP_VIDEOS_PER_COMPETITOR,
        top_playlists=TOP_PLAYLISTS_PER_COMPETITOR,
        n_clusters=N_CLUSTERS
    )
    
    if report:
        print("\n🎉 Analyse réussie! Consultez 'youtube_semantic_analysis.json'")
    else:
        print("\n💥 Échec de l'analyse")


if __name__ == "__main__":
    main()