"""
Module d'analyse sémantique des topics avec extraction de fréquences
Utilise paraphrase-multilingual-mpnet-base-v2 pour analyser les vidéos
"""

import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Set, Tuple
import threading

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[TOPIC-ANALYZER] ⚠️ sentence-transformers non disponible")

try:
    import spacy
    SPACY_AVAILABLE = True
    
    # Modèles multilingues optimisés (Large pour maximum de précision)
    spacy_models = {
        "en": "en_core_web_lg",
        "fr": "fr_core_news_lg", 
        "de": "de_core_news_lg",
        "nl": "nl_core_news_lg"
    }
    
    # Charger tous les modèles disponibles
    nlps = {}
    for lang, model_name in spacy_models.items():
        try:
            nlps[lang] = spacy.load(model_name)
            print(f"[TOPIC-ANALYZER] ✅ Modèle spaCy chargé: {model_name}")
        except OSError:
            # Fallback vers les modèles md puis sm
            try:
                fallback_model = model_name.replace("_lg", "_md")
                nlps[lang] = spacy.load(fallback_model)
                print(f"[TOPIC-ANALYZER] ✅ Modèle spaCy fallback (md): {fallback_model}")
            except OSError:
                try:
                    fallback_model = model_name.replace("_lg", "_sm")
                    nlps[lang] = spacy.load(fallback_model)
                    print(f"[TOPIC-ANALYZER] ✅ Modèle spaCy fallback (sm): {fallback_model}")
                except OSError:
                    print(f"[TOPIC-ANALYZER] ❌ Aucun modèle spaCy disponible pour {lang}")
    
    if not nlps:
        SPACY_AVAILABLE = False
        print("[TOPIC-ANALYZER] ⚠️ Aucun modèle spaCy disponible")
    else:
        print(f"[TOPIC-ANALYZER] 🌍 {len(nlps)} modèles spaCy chargés: {list(nlps.keys())}")
        
except ImportError:
    SPACY_AVAILABLE = False
    nlps = {}
    print("[TOPIC-ANALYZER] ⚠️ spaCy non disponible")

from .database.base import get_db_connection
from .database.videos import VideoManager
from .database.competitors import CompetitorManager


class TopicAnalyzer:
    """Analyseur de topics pour les vidéos YouTube"""
    
    def __init__(self):
        self.model = None
        self.video_manager = VideoManager()
        self.competitor_manager = CompetitorManager()
        self.analysis_status = {
            "status": "idle",
            "progress": 0,
            "total": 0,
            "current_step": "",
            "start_time": None,
            "error": None
        }
        
        # Stop words multilingues
        self.stop_words = self._load_stop_words()
        
        # Noms de concurrents à exclure
        self.competitor_names = self._load_competitor_names()
        
    def _load_stop_words(self) -> Set[str]:
        """Charge les stop words pour plusieurs langues"""
        stop_words = {
            # Français
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'est', 'à', 'au', 'aux',
            'ce', 'ces', 'son', 'sa', 'ses', 'leur', 'leurs', 'qui', 'que', 'ou', 'où',
            'dans', 'sur', 'avec', 'pour', 'par', 'sans', 'sous', 'entre', 'vers', 'chez',
            'si', 'ne', 'pas', 'plus', 'très', 'trop', 'bien', 'tout', 'tous', 'toute',
            # Anglais
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            # Allemand
            'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen', 'einem',
            'und', 'oder', 'aber', 'in', 'an', 'auf', 'mit', 'bei', 'zu', 'von', 'für',
            'ist', 'sind', 'war', 'waren', 'hat', 'haben', 'wird', 'werden',
            # Néerlandais
            'de', 'het', 'een', 'van', 'en', 'in', 'op', 'aan', 'met', 'voor', 'is',
            'zijn', 'was', 'waren', 'heeft', 'hebben', 'wordt', 'worden',
            # Mots courts et ponctuation
            '-', '|', '&', '+', '!', '?', '.', ',', ':', ';', '(', ')', '[', ']',
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
        }
        return stop_words
        
    def _load_competitor_names(self) -> Set[str]:
        """Charge TOUS les noms de marques et concurrents à exclure"""
        names = set()
        try:
            competitors = self.competitor_manager.get_all_competitors()
            for comp in competitors:
                if comp.get('name'):
                    # Ajouter le nom complet
                    names.add(comp['name'].lower())
                    # Ajouter chaque mot du nom
                    for word in comp['name'].replace('-', ' ').replace('_', ' ').split():
                        if len(word) > 2:  # Ignorer les mots très courts
                            names.add(word.lower())
        except Exception as e:
            print(f"[TOPIC-ANALYZER] Erreur chargement concurrents: {e}")
        
        print(f"[TOPIC-ANALYZER] 🚫 {len(names)} noms de concurrents à filtrer")
        return names
        
    def _clean_text(self, text: str) -> List[str]:
        """Nettoie et tokenize le texte"""
        if not text:
            return []
            
        # Convertir en minuscules
        text = text.lower()
        
        # Supprimer les URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Supprimer les emails
        text = re.sub(r'\S+@\S+', '', text)
        
        # Supprimer les caractères spéciaux mais garder les espaces
        text = re.sub(r'[^\w\s\'-]', ' ', text)
        
        # Séparer les mots
        words = text.split()
        
        # Filtrer les mots
        filtered_words = []
        for word in words:
            # Supprimer les mots trop courts
            if len(word) <= 2:
                continue
            # Supprimer les stop words
            if word in self.stop_words:
                continue
            # Supprimer les noms de concurrents
            if word in self.competitor_names:
                continue
            # Supprimer les mots qui sont juste des chiffres
            if word.isdigit():
                continue
            filtered_words.append(word)
            
        return filtered_words
        
    def _extract_ngrams(self, words: List[str], n: int) -> List[str]:
        """Extrait les n-grammes d'une liste de mots"""
        if len(words) < n:
            return []
        return [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]
        
    def _detect_language_advanced(self, text: str) -> str:
        """Détection de langue améliorée"""
        if not text:
            return 'en'
        
        text_lower = text.lower()
        
        # Marqueurs spécifiques par langue
        markers = {
            'fr': ['le ', 'la ', 'les ', 'des ', 'une ', 'avec ', 'pour ', 'dans ', 'sur ', 'est ', 'sont ', 'être ', 'avoir '],
            'de': ['der ', 'die ', 'das ', 'ein ', 'eine ', 'und ', 'mit ', 'für ', 'ist ', 'sind ', 'haben ', 'werden ', 'wie '],
            'nl': ['de ', 'het ', 'een ', 'van ', 'in ', 'op ', 'met ', 'voor ', 'is ', 'zijn ', 'heeft ', 'worden ', 'hoe '],
            'en': ['the ', 'and ', 'for ', 'with ', 'have ', 'this ', 'that ', 'from ', 'they ', 'will ', 'can ', 'are ']
        }
        
        scores = {}
        for lang, lang_markers in markers.items():
            scores[lang] = sum(text_lower.count(marker) for marker in lang_markers)
        
        # Retourner la langue avec le score le plus élevé
        detected_lang = max(scores, key=scores.get) if max(scores.values()) > 0 else 'en'
        return detected_lang
    
    def _analyze_grammar(self, texts: List[str]) -> Dict[str, List[Tuple[str, int]]]:
        """Analyse grammaticale multilingue des textes pour extraire verbes, adjectifs, noms"""
        if not SPACY_AVAILABLE or not nlps:
            print("[TOPIC-ANALYZER] ⚠️ Analyse grammaticale désactivée (spaCy non disponible)")
            return {'verbs': [], 'adjectives': [], 'nouns': []}
        
        verbs = []
        adjectives = []
        nouns = []
        lang_stats = {'fr': 0, 'en': 0, 'de': 0, 'nl': 0, 'other': 0}
        
        print(f"[TOPIC-ANALYZER] 🔍 Analyse grammaticale multilingue de {len(texts)} textes...")
        
        for i, text in enumerate(texts):
            if i % 500 == 0:
                print(f"[TOPIC-ANALYZER] Progression grammaticale: {i}/{len(texts)}")
                
            if not text or len(text) > 1000000:
                continue
                
            try:
                # Détecter la langue du texte
                detected_lang = self._detect_language_advanced(text)
                
                # Choisir le modèle spaCy approprié
                if detected_lang in nlps:
                    nlp_model = nlps[detected_lang]
                    lang_stats[detected_lang] += 1
                else:
                    # Fallback vers anglais
                    nlp_model = nlps.get('en', list(nlps.values())[0])
                    lang_stats['other'] += 1
                
                # Limiter la taille du texte
                text_sample = text[:3000] if len(text) > 3000 else text
                doc = nlp_model(text_sample)
                
                for token in doc:
                    lemma = token.lemma_.lower().strip()
                    
                    # Filtres de base (moins stricts pour les adjectifs et noms)
                    if (len(lemma) < 2 or 
                        lemma in self.stop_words or 
                        lemma in self.competitor_names or
                        not lemma.isalpha() or
                        lemma.isdigit() or
                        token.is_punct or
                        token.like_url or
                        token.like_email):
                        continue
                    
                    # Classification grammaticale simplifiée mais efficace
                    if token.pos_ == 'VERB':
                        # Exclure les auxiliaires les plus courants
                        if lemma not in ['être', 'avoir', 'be', 'have', 'do', 'will', 'shall', 'sein', 'haben', 'werden', 'zijn', 'hebben', 'worden']:
                            verbs.append(lemma)
                        
                    elif token.pos_ == 'ADJ':
                        # Plus permissif pour les adjectifs
                        if len(lemma) >= 3 and not token.is_stop:
                            adjectives.append(lemma)
                        
                    elif token.pos_ == 'NOUN':
                        # Plus permissif pour les noms, juste éviter les entités nommées obvies
                        if (len(lemma) >= 3 and 
                            not token.is_stop and
                            token.ent_type_ not in ['PERSON', 'ORG', 'GPE']):  # Éviter personnes, organisations, lieux
                            nouns.append(lemma)
                        
            except Exception as e:
                if i < 5:
                    print(f"[TOPIC-ANALYZER] Erreur analyse grammaticale: {e}")
                continue
        
        # Compter les fréquences
        from collections import Counter
        
        verb_freq = Counter(verbs).most_common(200)
        adj_freq = Counter(adjectives).most_common(200)  
        noun_freq = Counter(nouns).most_common(200)
        
        print(f"[TOPIC-ANALYZER] ✅ Analyse grammaticale terminée:")
        print(f"  - {len(verb_freq)} verbes uniques ({len(verbs)} total)")
        print(f"  - {len(adj_freq)} adjectifs uniques ({len(adjectives)} total)")
        print(f"  - {len(noun_freq)} noms uniques ({len(nouns)} total)")
        print(f"  - Langues détectées: {lang_stats}")
        print(f"  - Modèles spaCy utilisés: {list(nlps.keys())}")
        
        return {
            'verbs': verb_freq,
            'adjectives': adj_freq,
            'nouns': noun_freq,
            'language_stats': lang_stats,
            'models_used': {lang: str(model) for lang, model in nlps.items()},
            'total_words_analyzed': len(verbs) + len(adjectives) + len(nouns)
        }
        
    def analyze_topics_async(self):
        """Lance l'analyse en arrière-plan"""
        thread = threading.Thread(target=self._analyze_topics)
        thread.daemon = True
        thread.start()
        
    def _analyze_topics(self):
        """Analyse principale des topics"""
        try:
            self.analysis_status = {
                "status": "running",
                "progress": 0,
                "total": 0,
                "current_step": "Initialisation",
                "start_time": datetime.now().isoformat(),
                "error": None
            }
            
            # Charger le modèle
            if TRANSFORMERS_AVAILABLE and not self.model:
                self.analysis_status["current_step"] = "Chargement du modèle multilingual"
                self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2', device='cpu')
            
            # Récupérer toutes les vidéos
            self.analysis_status["current_step"] = "Récupération des vidéos"
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT v.id, v.title, v.description, c.name as channel_name
                FROM video v
                LEFT JOIN concurrent c ON v.concurrent_id = c.id
                ORDER BY v.id
            """)
            
            videos = cursor.fetchall()
            self.analysis_status["total"] = len(videos)
            
            print(f"[TOPIC-ANALYZER] 📊 TOTAL VIDÉOS RÉCUPÉRÉES: {len(videos)}")
            
            # Compter les vidéos avec titres et descriptions pour vérification
            cursor.execute("SELECT COUNT(*) FROM video WHERE title IS NOT NULL AND title != ''")
            videos_with_titles = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM video WHERE description IS NOT NULL AND description != ''")
            videos_with_descriptions = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM video")
            total_videos_in_db = cursor.fetchone()[0]
            
            print(f"[TOPIC-ANALYZER] 📈 STATISTIQUES DB:")
            print(f"  - Total vidéos en base: {total_videos_in_db}")
            print(f"  - Vidéos avec titres: {videos_with_titles}")
            print(f"  - Vidéos avec descriptions: {videos_with_descriptions}")
            
            # Récupérer TOUTES les playlists
            cursor.execute("""
                SELECT id, name, description
                FROM playlist
                ORDER BY id
            """)
            playlists = cursor.fetchall()
            
            # Compter les playlists avec descriptions
            cursor.execute("SELECT COUNT(*) FROM playlist WHERE description IS NOT NULL AND description != ''")
            playlists_with_descriptions = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM playlist")
            total_playlists_in_db = cursor.fetchone()[0]
            
            print(f"[TOPIC-ANALYZER] 📋 STATISTIQUES PLAYLISTS:")
            print(f"  - Total playlists en base: {total_playlists_in_db}")
            print(f"  - Playlists avec descriptions: {playlists_with_descriptions}")
            
            conn.close()
            
            # Analyser les données
            all_titles = []
            all_descriptions = []
            title_words = []
            description_words = []
            
            self.analysis_status["current_step"] = "Analyse des vidéos"
            
            for i, video in enumerate(videos):
                if i % 100 == 0:
                    self.analysis_status["progress"] = int((i / len(videos)) * 70)
                    self.analysis_status["current_step"] = f"Analyse des vidéos ({i}/{len(videos)})"
                    print(f"[TOPIC-ANALYZER] Progress: {i}/{len(videos)} vidéos analysées")
                    
                # Titre
                if video['title']:
                    all_titles.append({
                        'id': video['id'],
                        'title': video['title'],
                        'channel': video['channel_name']
                    })
                    words = self._clean_text(video['title'])
                    title_words.extend(words)
                    
                # Description
                if video['description']:
                    all_descriptions.append({
                        'id': video['id'],
                        'description': video['description'][:500],  # Limiter la taille
                        'channel': video['channel_name']
                    })
                    words = self._clean_text(video['description'])
                    description_words.extend(words)
            
            # Analyser les playlists
            self.analysis_status["current_step"] = "Analyse des playlists"
            playlist_data = []
            
            for playlist in playlists:
                playlist_entry = {
                    'id': playlist['id'],
                    'name': playlist['name']
                }
                if playlist['description']:
                    playlist_entry['description'] = playlist['description'][:500]
                    words = self._clean_text(playlist['description'])
                    description_words.extend(words)
                playlist_data.append(playlist_entry)
            
            # Calculer les fréquences
            self.analysis_status["current_step"] = "Calcul des fréquences"
            self.analysis_status["progress"] = 80
            
            # Mots simples
            title_freq = Counter(title_words).most_common(500)
            desc_freq = Counter(description_words).most_common(500)
            
            # Bigrammes
            title_bigrams = []
            desc_bigrams = []
            
            for video in videos:
                if video['title']:
                    words = self._clean_text(video['title'])
                    title_bigrams.extend(self._extract_ngrams(words, 2))
                if video['description']:
                    words = self._clean_text(video['description'])
                    desc_bigrams.extend(self._extract_ngrams(words, 2))
            
            title_bigram_freq = Counter(title_bigrams).most_common(200)
            desc_bigram_freq = Counter(desc_bigrams).most_common(200)
            
            # Analyse grammaticale des titres et descriptions
            self.analysis_status["current_step"] = "Analyse grammaticale (verbes, adjectifs, noms)"
            self.analysis_status["progress"] = 80
            
            all_texts_for_grammar = []
            
            # Préparer tous les textes pour l'analyse grammaticale
            for video in videos:
                if video['title']:
                    all_texts_for_grammar.append(video['title'])
                if video['description']:
                    all_texts_for_grammar.append(video['description'][:500])  # Limiter les descriptions
            
            grammar_results = self._analyze_grammar(all_texts_for_grammar)
            
            # Générer les embeddings pour les top mots (optionnel)
            embeddings_data = {}
            if TRANSFORMERS_AVAILABLE and self.model:
                self.analysis_status["current_step"] = "Génération des embeddings"
                self.analysis_status["progress"] = 90
                
                # Top 100 mots des titres
                top_words = [word for word, _ in title_freq[:100]]
                if top_words:
                    embeddings = self.model.encode(top_words, batch_size=64, show_progress_bar=False)
                    embeddings_data['top_title_words'] = {
                        'words': top_words,
                        'embeddings': embeddings.tolist()
                    }
            
            # Sauvegarder les résultats
            self.analysis_status["current_step"] = "Sauvegarde des résultats"
            self.analysis_status["progress"] = 95
            
            output_dir = "./topic_analysis_results"
            os.makedirs(output_dir, exist_ok=True)
            
            # Sauvegarder tous les titres
            with open(os.path.join(output_dir, "all_titles.json"), "w", encoding="utf-8") as f:
                json.dump({
                    'count': len(all_titles),
                    'titles': all_titles
                }, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder toutes les descriptions
            with open(os.path.join(output_dir, "all_descriptions.json"), "w", encoding="utf-8") as f:
                json.dump({
                    'count': len(all_descriptions),
                    'descriptions': all_descriptions
                }, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les playlists
            with open(os.path.join(output_dir, "playlist_data.json"), "w", encoding="utf-8") as f:
                json.dump({
                    'count': len(playlist_data),
                    'playlists': playlist_data
                }, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les fréquences
            with open(os.path.join(output_dir, "word_frequencies.json"), "w", encoding="utf-8") as f:
                json.dump({
                    'title_words': {
                        'total_words': len(title_words),
                        'unique_words': len(set(title_words)),
                        'top_500': [{'word': w, 'count': c} for w, c in title_freq]
                    },
                    'description_words': {
                        'total_words': len(description_words),
                        'unique_words': len(set(description_words)),
                        'top_500': [{'word': w, 'count': c} for w, c in desc_freq]
                    },
                    'title_bigrams': {
                        'top_200': [{'bigram': b, 'count': c} for b, c in title_bigram_freq]
                    },
                    'description_bigrams': {
                        'top_200': [{'bigram': b, 'count': c} for b, c in desc_bigram_freq]
                    }
                }, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder l'analyse grammaticale
            with open(os.path.join(output_dir, "grammar_analysis.json"), "w", encoding="utf-8") as f:
                json.dump({
                    'verbs': {
                        'total_count': len([v for v, c in grammar_results['verbs']]),
                        'unique_count': len(grammar_results['verbs']),
                        'top_200': [{'word': v, 'count': c} for v, c in grammar_results['verbs']]
                    },
                    'adjectives': {
                        'total_count': len([a for a, c in grammar_results['adjectives']]),
                        'unique_count': len(grammar_results['adjectives']),
                        'top_200': [{'word': a, 'count': c} for a, c in grammar_results['adjectives']]
                    },
                    'nouns': {
                        'total_count': len([n for n, c in grammar_results['nouns']]),
                        'unique_count': len(grammar_results['nouns']),
                        'top_200': [{'word': n, 'count': c} for n, c in grammar_results['nouns']]
                    },
                    'spacy_available': SPACY_AVAILABLE,
                    'models_used': grammar_results.get('models_used', {}),
                    'language_stats': grammar_results.get('language_stats', {}),
                    'total_words_analyzed': grammar_results.get('total_words_analyzed', 0),
                    'analysis_date': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les embeddings si disponibles
            if embeddings_data:
                with open(os.path.join(output_dir, "embeddings.json"), "w", encoding="utf-8") as f:
                    json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
            
            # Résumé consolidé
            summary = {
                'analysis_date': datetime.now().isoformat(),
                'total_videos': len(videos),
                'total_videos_in_db': total_videos_in_db,
                'videos_with_titles': videos_with_titles,
                'videos_with_descriptions': videos_with_descriptions,
                'videos_processed_titles': len(all_titles),
                'videos_processed_descriptions': len(all_descriptions),
                'total_playlists': len(playlists),
                'total_playlists_in_db': total_playlists_in_db,
                'playlists_with_descriptions': playlists_with_descriptions,
                'total_title_words_extracted': len(title_words),
                'unique_title_words': len(set(title_words)),
                'total_description_words_extracted': len(description_words),
                'unique_description_words': len(set(description_words)),
                'top_20_title_words': [{'word': w, 'count': c} for w, c in title_freq[:20]],
                'top_20_description_words': [{'word': w, 'count': c} for w, c in desc_freq[:20]],
                'top_10_title_bigrams': [{'bigram': b, 'count': c} for b, c in title_bigram_freq[:10]],
                'top_10_description_bigrams': [{'bigram': b, 'count': c} for b, c in desc_bigram_freq[:10]],
                'top_20_verbs': [{'word': w, 'count': c} for w, c in grammar_results['verbs'][:20]],
                'top_20_adjectives': [{'word': w, 'count': c} for w, c in grammar_results['adjectives'][:20]],
                'top_20_nouns': [{'word': w, 'count': c} for w, c in grammar_results['nouns'][:20]],
                'grammar_stats': grammar_results.get('language_stats', {}),
                'model_used': 'paraphrase-multilingual-mpnet-base-v2' if TRANSFORMERS_AVAILABLE else 'none',
                'spacy_available': SPACY_AVAILABLE,
                'coverage_report': {
                    'titles_coverage': f"{len(all_titles)}/{videos_with_titles} ({(len(all_titles)/videos_with_titles*100):.1f}%)" if videos_with_titles > 0 else "0/0 (0%)",
                    'descriptions_coverage': f"{len(all_descriptions)}/{videos_with_descriptions} ({(len(all_descriptions)/videos_with_descriptions*100):.1f}%)" if videos_with_descriptions > 0 else "0/0 (0%)",
                    'total_coverage': f"{len(videos)}/{total_videos_in_db} ({(len(videos)/total_videos_in_db*100):.1f}%)" if total_videos_in_db > 0 else "0/0 (0%)"
                }
            }
            
            with open(os.path.join(output_dir, "analysis_summary.json"), "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            self.analysis_status = {
                "status": "completed",
                "progress": 100,
                "total": len(videos),
                "current_step": "Analyse terminée",
                "start_time": self.analysis_status["start_time"],
                "end_time": datetime.now().isoformat(),
                "error": None,
                "results": summary
            }
            
        except Exception as e:
            self.analysis_status = {
                "status": "error",
                "progress": self.analysis_status["progress"],
                "total": self.analysis_status["total"],
                "current_step": "Erreur",
                "start_time": self.analysis_status["start_time"],
                "error": str(e)
            }
            print(f"[TOPIC-ANALYZER] Erreur: {e}")
            
    def get_status(self) -> Dict:
        """Retourne le statut de l'analyse"""
        return self.analysis_status
        
    def get_latest_results(self) -> Dict:
        """Récupère les derniers résultats d'analyse"""
        try:
            summary_path = "./topic_analysis_results/analysis_summary.json"
            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[TOPIC-ANALYZER] Erreur lecture résultats: {e}")
        return None