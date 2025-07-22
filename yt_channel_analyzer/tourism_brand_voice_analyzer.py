"""
Tourism Brand Voice Analyzer - Analyse sémantique sophistiquée pour YouTube
Utilise sentence-transformers avec le modèle all-mpnet-base-v2 pour analyser
la voix de marque dans le contenu touristique multilingue.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict, Counter
import pandas as pd
import re
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime


class TourismBrandVoiceAnalyzer:
    """Analyseur sémantique de voix de marque pour le tourisme"""
    
    def __init__(self):
        # Modèle all-mpnet-base-v2 pour une meilleure précision
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        # Lexique tourisme étendu (100+ mots par catégorie, multilingue)
        self.tourism_lexicon = {
            'invitation_voyage': {
                'fr': [
                    # Verbes d'invitation
                    'découvrez', 'explorez', 'visitez', 'partez', 'voyagez', 'embarquez', 
                    'évadez-vous', 'envolez-vous', 'plongez', 'vivez', 'osez', 'laissez-vous',
                    'succombez', 'craquez', 'aventurez-vous', 'parcourez', 'arpentez',
                    'sillonnez', 'naviguez', 'flânez', 'promenez-vous', 'baladez-vous',
                    # Noms évocateurs
                    'aventure', 'découverte', 'exploration', 'voyage', 'escapade', 'périple',
                    'odyssée', 'expédition', 'croisière', 'excursion', 'virée', 'épopée',
                    'randonnée', 'trek', 'safari', 'road-trip', 'circuit', 'itinéraire',
                    # Adjectifs inspirants
                    'inoubliable', 'unique', 'exceptionnel', 'authentique', 'magique',
                    'époustouflant', 'grandiose', 'spectaculaire', 'fascinant', 'enchanteur'
                ],
                'en': [
                    # Action verbs
                    'discover', 'explore', 'visit', 'travel', 'journey', 'embark', 'escape',
                    'fly', 'dive', 'experience', 'dare', 'wander', 'roam', 'venture',
                    'uncover', 'immerse', 'indulge', 'embrace', 'navigate', 'traverse',
                    'trek', 'cruise', 'sail', 'soar', 'stroll', 'meander', 'expedition',
                    # Evocative nouns
                    'adventure', 'discovery', 'exploration', 'journey', 'getaway', 'trip',
                    'odyssey', 'expedition', 'cruise', 'excursion', 'escapade', 'voyage',
                    'wanderlust', 'destination', 'paradise', 'haven', 'oasis', 'retreat',
                    # Inspiring adjectives
                    'unforgettable', 'unique', 'exceptional', 'authentic', 'magical',
                    'breathtaking', 'stunning', 'spectacular', 'fascinating', 'enchanting'
                ],
                'de': [
                    # Aktionsverben
                    'entdecken', 'erkunden', 'besuchen', 'reisen', 'erleben', 'genießen',
                    'aufbrechen', 'fliegen', 'tauchen', 'wandern', 'erobern', 'erforschen',
                    'durchqueren', 'bereisen', 'besichtigen', 'bestaunen', 'schwelgen',
                    'flanieren', 'bummeln', 'spazieren', 'kreuzen', 'segeln', 'navigieren',
                    # Substantive
                    'Abenteuer', 'Entdeckung', 'Erkundung', 'Reise', 'Ausflug', 'Fahrt',
                    'Expedition', 'Kreuzfahrt', 'Wanderung', 'Safari', 'Roadtrip', 'Tour',
                    'Erlebnis', 'Eskapade', 'Odyssee', 'Traumreise', 'Weltreise', 'Rundreise',
                    # Adjektive
                    'unvergesslich', 'einzigartig', 'außergewöhnlich', 'authentisch', 'magisch',
                    'atemberaubend', 'spektakulär', 'faszinierend', 'bezaubernd', 'traumhaft'
                ],
                'nl': [
                    # Actiewerkwoorden
                    'ontdek', 'verken', 'bezoek', 'reis', 'beleef', 'geniet', 'vertrek',
                    'vlieg', 'duik', 'wandel', 'vaar', 'ervaar', 'proef', 'bewonder',
                    'doorkruis', 'bereis', 'bezichtig', 'flaneer', 'kuier', 'dwaal',
                    'trek', 'navigeer', 'zeilen', 'cruise', 'rondreizen', 'trekken',
                    # Zelfstandige naamwoorden
                    'avontuur', 'ontdekking', 'verkenning', 'reis', 'uitstap', 'tocht',
                    'expeditie', 'cruise', 'wandeling', 'safari', 'roadtrip', 'rondrei',
                    'beleving', 'escapade', 'odyssee', 'droomreis', 'wereldreis', 'vakantie',
                    # Bijvoeglijke naamwoorden
                    'onvergetelijk', 'uniek', 'uitzonderlijk', 'authentiek', 'magisch',
                    'adembenemend', 'spectaculair', 'fascinerend', 'betoverend', 'dromerig'
                ]
            },
            
            'emotions_positives': {
                'fr': [
                    # Émotions
                    'bonheur', 'joie', 'plaisir', 'émerveillement', 'enchantement', 'ravissement',
                    'béatitude', 'extase', 'euphorie', 'enthousiasme', 'passion', 'fascination',
                    'admiration', 'contemplation', 'sérénité', 'paix', 'tranquillité', 'zenitude',
                    'liberté', 'légèreté', 'insouciance', 'délice', 'régal', 'félicité',
                    # Sensations
                    'frisson', 'vertige', 'ivresse', 'griserie', 'sensation', 'émotion',
                    'sentiment', 'impression', 'ressenti', 'vécu', 'expérience', 'moment',
                    # Qualificatifs émotionnels
                    'heureux', 'joyeux', 'radieux', 'épanoui', 'comblé', 'ravi', 'enchanté',
                    'émerveillé', 'ébloui', 'fasciné', 'captivé', 'subjugué', 'transporté'
                ],
                'en': [
                    # Emotions
                    'happiness', 'joy', 'pleasure', 'wonder', 'delight', 'bliss', 'ecstasy',
                    'euphoria', 'enthusiasm', 'passion', 'fascination', 'admiration', 'awe',
                    'serenity', 'peace', 'tranquility', 'freedom', 'liberation', 'elation',
                    'contentment', 'fulfillment', 'satisfaction', 'rapture', 'enchantment',
                    # Sensations
                    'thrill', 'excitement', 'rush', 'sensation', 'feeling', 'emotion',
                    'experience', 'moment', 'memory', 'impression', 'vibe', 'atmosphere',
                    # Emotional qualifiers
                    'happy', 'joyful', 'delighted', 'thrilled', 'excited', 'amazed',
                    'mesmerized', 'captivated', 'enthralled', 'enchanted', 'spellbound'
                ],
                'de': [
                    # Emotionen
                    'Glück', 'Freude', 'Vergnügen', 'Begeisterung', 'Verzauberung', 'Entzücken',
                    'Seligkeit', 'Ekstase', 'Euphorie', 'Leidenschaft', 'Faszination', 'Bewunderung',
                    'Gelassenheit', 'Frieden', 'Ruhe', 'Freiheit', 'Leichtigkeit', 'Sorglosigkeit',
                    'Genuss', 'Wonne', 'Glückseligkeit', 'Zufriedenheit', 'Erfüllung', 'Hochgefühl',
                    # Empfindungen
                    'Gefühl', 'Emotion', 'Empfindung', 'Eindruck', 'Erlebnis', 'Moment',
                    'Erinnerung', 'Stimmung', 'Atmosphäre', 'Schwingung', 'Rausch', 'Kick',
                    # Emotionale Qualifikatoren
                    'glücklich', 'freudig', 'begeistert', 'verzaubert', 'fasziniert', 'hingerissen',
                    'überwältigt', 'ergriffen', 'bewegt', 'erfüllt', 'selig', 'euphorisch'
                ],
                'nl': [
                    # Emoties
                    'geluk', 'vreugde', 'plezier', 'verwondering', 'betovering', 'verrukking',
                    'zaligheid', 'extase', 'euforie', 'enthousiasme', 'passie', 'fascinatie',
                    'bewondering', 'sereniteit', 'vrede', 'rust', 'vrijheid', 'lichtheid',
                    'zorgeloosheid', 'genot', 'verrukking', 'gelukzaligheid', 'tevredenheid',
                    # Sensaties
                    'gevoel', 'emotie', 'gewaarwording', 'indruk', 'beleving', 'moment',
                    'herinnering', 'stemming', 'sfeer', 'vibratie', 'roes', 'kick',
                    # Emotionele kwalificaties
                    'gelukkig', 'blij', 'verheugd', 'enthousiast', 'betoverd', 'gefascineerd',
                    'overweldigd', 'ontroerd', 'vervuld', 'zalig', 'euforisch', 'opgetogen'
                ]
            },
            
            'urgence_exclusivite': {
                'fr': [
                    # Urgence temporelle
                    'maintenant', 'immédiatement', 'aujourd\'hui', 'dernière minute', 'vite',
                    'rapidement', 'sans attendre', 'dès maintenant', 'tout de suite', 'urgent',
                    'derniers jours', 'dernière chance', 'plus que', 'seulement', 'limité',
                    # Exclusivité
                    'exclusif', 'unique', 'privilège', 'VIP', 'premium', 'exceptionnel',
                    'rare', 'inédit', 'première', 'avant-première', 'accès privé', 'sur-mesure',
                    'personnalisé', 'intimiste', 'confidentiel', 'secret', 'réservé', 'sélect',
                    # Incitations temporelles
                    'profitez', 'saisissez', 'ne manquez pas', 'réservez', 'anticipez',
                    'bloquez', 'garantissez', 'assurez-vous', 'dépêchez-vous', 'hâtez-vous'
                ],
                'en': [
                    # Time urgency
                    'now', 'immediately', 'today', 'last minute', 'quick', 'fast', 'hurry',
                    'don\'t wait', 'right now', 'urgent', 'final days', 'last chance',
                    'limited time', 'only', 'exclusive', 'ending soon', 'flash', 'deadline',
                    # Exclusivity
                    'exclusive', 'unique', 'privilege', 'VIP', 'premium', 'exceptional',
                    'rare', 'first', 'premiere', 'private access', 'bespoke', 'tailored',
                    'personalized', 'intimate', 'confidential', 'secret', 'reserved', 'select',
                    # Time-based CTAs
                    'book now', 'reserve', 'secure', 'grab', 'seize', 'don\'t miss',
                    'act fast', 'claim', 'lock in', 'guarantee', 'ensure', 'rush'
                ],
                'de': [
                    # Zeitdringlichkeit
                    'jetzt', 'sofort', 'heute', 'letzte Minute', 'schnell', 'rasch',
                    'unverzüglich', 'gleich', 'dringend', 'letzte Tage', 'letzte Chance',
                    'begrenzt', 'nur noch', 'limitiert', 'befristet', 'eilig', 'Frist',
                    # Exklusivität
                    'exklusiv', 'einzigartig', 'Privileg', 'VIP', 'Premium', 'außergewöhnlich',
                    'selten', 'erstmalig', 'Premiere', 'privater Zugang', 'maßgeschneidert',
                    'personalisiert', 'intim', 'vertraulich', 'geheim', 'reserviert', 'erlesen',
                    # Zeitbasierte CTAs
                    'jetzt buchen', 'reservieren', 'sichern', 'ergreifen', 'verpassen Sie nicht',
                    'handeln Sie schnell', 'beanspruchen', 'festlegen', 'garantieren', 'beeilen'
                ],
                'nl': [
                    # Tijdsurgentie
                    'nu', 'onmiddellijk', 'vandaag', 'laatste moment', 'snel', 'vlug',
                    'direct', 'meteen', 'dringend', 'laatste dagen', 'laatste kans',
                    'beperkt', 'alleen nog', 'gelimiteerd', 'tijdelijk', 'haast', 'deadline',
                    # Exclusiviteit
                    'exclusief', 'uniek', 'privilege', 'VIP', 'premium', 'uitzonderlijk',
                    'zeldzaam', 'primeur', 'première', 'privé toegang', 'op maat', 'maatwerk',
                    'gepersonaliseerd', 'intiem', 'vertrouwelijk', 'geheim', 'gereserveerd',
                    # Tijdgebonden CTAs
                    'boek nu', 'reserveer', 'verzeker', 'grijp', 'pak', 'mis niet',
                    'wees snel', 'claim', 'leg vast', 'garandeer', 'zorg voor', 'haast je'
                ]
            },
            
            'authenticite_local': {
                'fr': [
                    # Authenticité
                    'authentique', 'véritable', 'vrai', 'traditionnel', 'ancestral', 'originel',
                    'typique', 'caractéristique', 'emblématique', 'légendaire', 'historique',
                    'patrimonial', 'culturel', 'identitaire', 'racines', 'héritage', 'tradition',
                    # Local/Terroir
                    'local', 'terroir', 'régional', 'artisanal', 'fait-main', 'homemade',
                    'producteur', 'autochtone', 'indigène', 'natif', 'endémique', 'vernaculaire',
                    'pays', 'territoire', 'région', 'coin', 'quartier', 'village', 'communauté',
                    # Immersion
                    'immersion', 'rencontre', 'échange', 'partage', 'convivialité', 'hospitalité',
                    'accueil', 'chaleureux', 'généreux', 'bienveillant', 'sincère', 'spontané'
                ],
                'en': [
                    # Authenticity
                    'authentic', 'genuine', 'real', 'traditional', 'ancestral', 'original',
                    'typical', 'characteristic', 'iconic', 'legendary', 'historical', 'heritage',
                    'cultural', 'roots', 'legacy', 'tradition', 'timeless', 'indigenous',
                    # Local/Terroir
                    'local', 'regional', 'artisanal', 'handmade', 'homemade', 'craft',
                    'producer', 'native', 'endemic', 'vernacular', 'territory', 'community',
                    'neighborhood', 'village', 'hometown', 'grassroots', 'farm-to-table',
                    # Immersion
                    'immersion', 'encounter', 'exchange', 'sharing', 'hospitality', 'welcome',
                    'warmth', 'generous', 'heartfelt', 'sincere', 'spontaneous', 'connection'
                ],
                'de': [
                    # Authentizität
                    'authentisch', 'echt', 'wahr', 'traditionell', 'ursprünglich', 'original',
                    'typisch', 'charakteristisch', 'emblematisch', 'legendär', 'historisch',
                    'kulturell', 'Erbe', 'Tradition', 'Wurzeln', 'zeitlos', 'einheimisch',
                    # Lokal/Terroir
                    'lokal', 'regional', 'handwerklich', 'handgemacht', 'hausgemacht',
                    'Erzeuger', 'einheimisch', 'heimisch', 'Terroir', 'Gebiet', 'Gemeinde',
                    'Nachbarschaft', 'Dorf', 'Heimat', 'bodenständig', 'verwurzelt',
                    # Immersion
                    'Eintauchen', 'Begegnung', 'Austausch', 'Teilen', 'Gastfreundschaft',
                    'Empfang', 'Wärme', 'großzügig', 'herzlich', 'aufrichtig', 'spontan'
                ],
                'nl': [
                    # Authenticiteit
                    'authentiek', 'echt', 'waar', 'traditioneel', 'oorspronkelijk', 'origineel',
                    'typisch', 'kenmerkend', 'emblematisch', 'legendarisch', 'historisch',
                    'cultureel', 'erfgoed', 'traditie', 'wortels', 'tijdloos', 'inheems',
                    # Lokaal/Terroir
                    'lokaal', 'regionaal', 'ambachtelijk', 'handgemaakt', 'huisgemaakt',
                    'producent', 'autochtoon', 'inheems', 'streek', 'gebied', 'gemeenschap',
                    'buurt', 'dorp', 'thuishaven', 'geworteld', 'verankerd',
                    # Immersie
                    'onderdompeling', 'ontmoeting', 'uitwisseling', 'delen', 'gastvrijheid',
                    'ontvangst', 'warmte', 'genereus', 'hartelijk', 'oprecht', 'spontaan'
                ]
            }
        }
        
        # Créer les embeddings de référence
        self._create_reference_embeddings()
        
    def _create_reference_embeddings(self):
        """Créer des embeddings de référence pour chaque catégorie"""
        self.category_embeddings = {}
        
        for category, languages in self.tourism_lexicon.items():
            # Collecter tous les mots de la catégorie
            all_words = []
            for lang, words in languages.items():
                all_words.extend(words)
            
            # Créer l'embedding moyen de la catégorie
            if all_words:
                embeddings = self.model.encode(all_words)
                self.category_embeddings[category] = np.mean(embeddings, axis=0)
    
    def analyze_brand_voice(self, text: str, min_similarity: float = 0.25) -> Dict[str, Any]:
        """Analyser la voix de marque dans un texte"""
        # Nettoyer le texte
        text_clean = re.sub(r'http[s]?://\S+', '', text)
        text_clean = re.sub(r'www\.\S+', '', text_clean)
        
        # Filtrer les marques de tourisme connues
        tourism_brands = [
            'expedia', 'booking', 'airbnb', 'tripadvisor', 'agoda', 'kayak', 'skyscanner',
            'hotels', 'priceline', 'orbitz', 'travelocity', 'vrbo', 'homeaway',
            'youtube', 'video', 'channel', 'subscribe', 'like', 'comment', 'share'
        ]
        for brand in tourism_brands:
            text_clean = re.sub(rf'\b{re.escape(brand)}\b', '', text_clean, flags=re.IGNORECASE)
        
        # Découper en segments pour une analyse plus fine
        segments = re.split(r'[.!?]+', text_clean)
        segments = [s.strip() for s in segments if len(s.strip()) > 10]
        
        results = {
            'scores': defaultdict(float),
            'matched_words': defaultdict(list),
            'strong_segments': defaultdict(list),
            'brand_voice_profile': {}
        }
        
        # Analyser chaque segment
        for segment in segments:
            segment_embedding = self.model.encode(segment)
            
            for category, ref_embedding in self.category_embeddings.items():
                similarity = cosine_similarity(
                    [segment_embedding], 
                    [ref_embedding]
                )[0][0]
                
                if similarity > min_similarity:
                    results['scores'][category] += similarity
                    
                    # Chercher les mots spécifiques
                    segment_lower = segment.lower()
                    for lang, words in self.tourism_lexicon[category].items():
                        for word in words:
                            if word.lower() in segment_lower:
                                results['matched_words'][category].append({
                                    'word': word,
                                    'language': lang,
                                    'context': segment[:100]
                                })
                    
                    # Garder les segments forts
                    if similarity > 0.4:
                        results['strong_segments'][category].append({
                            'segment': segment[:150],
                            'score': float(similarity)
                        })
        
        # Créer le profil de voix de marque
        total_score = sum(results['scores'].values())
        if total_score > 0:
            results['brand_voice_profile'] = {
                cat: score/total_score for cat, score in results['scores'].items()
            }
        
        return results
    
    def analyze_corpus(self, texts: List[str], output_format: str = 'detailed') -> Dict[str, Any]:
        """Analyser un corpus de textes touristiques"""
        corpus_results = {
            'category_frequency': defaultdict(int),
            'word_frequency': defaultdict(Counter),
            'language_distribution': Counter(),
            'brand_profiles': [],
            'top_performing_content': defaultdict(list)
        }
        
        for i, text in enumerate(texts):
            # Analyser chaque texte
            analysis = self.analyze_brand_voice(text)
            
            # Agréger les résultats
            for category, score in analysis['scores'].items():
                corpus_results['category_frequency'][category] += 1 if score > 0 else 0
                
                # Compter les mots
                for match in analysis['matched_words'][category]:
                    corpus_results['word_frequency'][category][match['word']] += 1
                    corpus_results['language_distribution'][match['language']] += 1
            
            # Sauvegarder le profil
            if analysis['brand_voice_profile']:
                corpus_results['brand_profiles'].append({
                    'text_id': i,
                    'profile': analysis['brand_voice_profile'],
                    'dominant_category': max(analysis['brand_voice_profile'], 
                                           key=analysis['brand_voice_profile'].get)
                })
                
                # Garder les meilleurs exemples
                for cat, segments in analysis['strong_segments'].items():
                    for seg in segments[:2]:  # Top 2 segments
                        corpus_results['top_performing_content'][cat].append({
                            'text_id': i,
                            'segment': seg['segment'],
                            'score': seg['score']
                        })
        
        # Créer le rapport final
        if output_format == 'summary':
            return self._create_summary_report(corpus_results)
        else:
            return corpus_results
    
    def _create_summary_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Créer un rapport synthétique"""
        report = {
            'dominant_voice': {},
            'top_words_by_category': {},
            'language_mix': dict(results['language_distribution']),
            'recommendations': []
        }
        
        # Calculer la voix dominante
        total_texts = len(results['brand_profiles'])
        if total_texts > 0:
            category_dominance = defaultdict(float)
            for profile in results['brand_profiles']:
                for cat, score in profile['profile'].items():
                    category_dominance[cat] += score
            
            report['dominant_voice'] = {
                cat: score/total_texts 
                for cat, score in category_dominance.items()
            }
        
        # Top mots par catégorie
        for category, word_counter in results['word_frequency'].items():
            report['top_words_by_category'][category] = word_counter.most_common(10)
        
        # Recommandations basées sur l'analyse
        if report['dominant_voice']:
            dominant = max(report['dominant_voice'], key=report['dominant_voice'].get)
            if dominant == 'invitation_voyage':
                report['recommendations'].append(
                    "Votre contenu est fort sur l'invitation au voyage. "
                    "Considérez ajouter plus d'authenticité locale pour équilibrer."
                )
            elif dominant == 'urgence_exclusivite':
                report['recommendations'].append(
                    "Beaucoup d'urgence dans vos messages. "
                    "Ajoutez des éléments d'authenticité pour créer de la confiance."
                )
            elif dominant == 'emotions_positives':
                report['recommendations'].append(
                    "Excellent focus sur les émotions positives. "
                    "Pensez à inclure des éléments d'invitation au voyage concrets."
                )
            elif dominant == 'authenticite_local':
                report['recommendations'].append(
                    "Forte authenticité locale dans votre contenu. "
                    "Ajoutez des éléments d'invitation au voyage pour inspirer l'action."
                )
        
        return report

    def analyze_youtube_data_with_progress(self, videos_data: List[Dict]) -> Dict[str, Any]:
        """Analyser spécifiquement des données YouTube avec suivi de progression"""
        global semantic_analysis_progress
        
        # Préparer les textes pour l'analyse
        texts = []
        metadata = []
        
        semantic_analysis_progress['current_step'] = 'Préparation des données...'
        semantic_analysis_progress['progress'] = 20
        
        for i, video in enumerate(videos_data):
            # Combiner titre et description
            text = f"{video.get('title', '')} {video.get('description', '')}"
            texts.append(text)
            
            # Garder les métadonnées
            metadata.append({
                'video_id': video.get('id'),
                'title': video.get('title'),
                'competitor': video.get('competitor_name'),
                'country': video.get('country'),
                'views': video.get('view_count', 0),
                'likes': video.get('like_count', 0),
                'category': video.get('category')
            })
            
            # Mettre à jour progression
            if i % 10 == 0:
                progress = 20 + (i / len(videos_data)) * 20
                semantic_analysis_progress['progress'] = int(progress)
        
        # Analyser le corpus
        semantic_analysis_progress['current_step'] = 'Analyse sémantique des textes...'
        semantic_analysis_progress['progress'] = 40
        
        analysis = self.analyze_corpus(texts, output_format='detailed')
        
        semantic_analysis_progress['current_step'] = 'Enrichissement avec métadonnées...'
        semantic_analysis_progress['progress'] = 70
        
        # Enrichir avec les métadonnées YouTube
        enriched_results = {
            'summary': self._create_summary_report(analysis),
            'top_videos_by_voice': self._get_top_videos_by_voice(analysis, metadata),
            'voice_by_country': self._analyze_voice_by_country(analysis, metadata),
            'voice_by_category': self._analyze_voice_by_category(analysis, metadata),
            'raw_analysis': analysis
        }
        
        semantic_analysis_progress['current_step'] = 'Finalisation...'
        semantic_analysis_progress['progress'] = 90
        
        return enriched_results
    
    def analyze_youtube_data(self, videos_data: List[Dict]) -> Dict[str, Any]:
        """Analyser spécifiquement des données YouTube avec métadonnées"""
        # Préparer les textes pour l'analyse
        texts = []
        metadata = []
        
        for video in videos_data:
            # Combiner titre et description
            text = f"{video.get('title', '')} {video.get('description', '')}"
            texts.append(text)
            
            # Garder les métadonnées
            metadata.append({
                'video_id': video.get('id'),
                'title': video.get('title'),
                'competitor': video.get('competitor_name'),
                'country': video.get('country'),
                'views': video.get('view_count', 0),
                'likes': video.get('like_count', 0),
                'category': video.get('category')
            })
        
        # Analyser le corpus
        analysis = self.analyze_corpus(texts, output_format='detailed')
        
        # Enrichir avec les métadonnées YouTube
        enriched_results = {
            'summary': self._create_summary_report(analysis),
            'top_videos_by_voice': self._get_top_videos_by_voice(analysis, metadata),
            'voice_by_country': self._analyze_voice_by_country(analysis, metadata),
            'voice_by_category': self._analyze_voice_by_category(analysis, metadata),
            'raw_analysis': analysis
        }
        
        return enriched_results
    
    def _get_top_videos_by_voice(self, analysis: Dict, metadata: List[Dict]) -> Dict[str, List]:
        """Identifier les top vidéos par catégorie de voix"""
        top_videos = defaultdict(list)
        
        for profile in analysis['brand_profiles']:
            text_id = profile['text_id']
            video_meta = metadata[text_id]
            
            # Pour chaque catégorie dominante
            for category, score in profile['profile'].items():
                if score > 0.2:  # Seuil de pertinence
                    top_videos[category].append({
                        'title': video_meta['title'],
                        'competitor': video_meta['competitor'],
                        'views': video_meta['views'],
                        'voice_score': score,
                        'engagement': (video_meta['likes'] / video_meta['views'] * 100) if video_meta['views'] > 0 else 0
                    })
        
        # Trier par score de voix et garder top 10
        for category in top_videos:
            top_videos[category] = sorted(
                top_videos[category], 
                key=lambda x: x['voice_score'], 
                reverse=True
            )[:10]
        
        return dict(top_videos)
    
    def _analyze_voice_by_country(self, analysis: Dict, metadata: List[Dict]) -> Dict[str, Dict]:
        """Analyser la voix de marque par pays"""
        country_voices = defaultdict(lambda: defaultdict(float))
        country_counts = defaultdict(int)
        
        for profile in analysis['brand_profiles']:
            text_id = profile['text_id']
            country = metadata[text_id]['country']
            
            if country:
                country_counts[country] += 1
                for category, score in profile['profile'].items():
                    country_voices[country][category] += score
        
        # Normaliser par nombre de vidéos
        normalized_voices = {}
        for country, voices in country_voices.items():
            if country_counts[country] > 0:
                normalized_voices[country] = {
                    cat: score / country_counts[country]
                    for cat, score in voices.items()
                }
        
        return normalized_voices
    
    def _analyze_voice_by_category(self, analysis: Dict, metadata: List[Dict]) -> Dict[str, Dict]:
        """Analyser la voix de marque par catégorie Hero/Hub/Help"""
        category_voices = defaultdict(lambda: defaultdict(float))
        category_counts = defaultdict(int)
        
        for profile in analysis['brand_profiles']:
            text_id = profile['text_id']
            hhh_category = metadata[text_id]['category']
            
            if hhh_category:
                category_counts[hhh_category] += 1
                for voice_cat, score in profile['profile'].items():
                    category_voices[hhh_category][voice_cat] += score
        
        # Normaliser
        normalized_voices = {}
        for hhh_cat, voices in category_voices.items():
            if category_counts[hhh_cat] > 0:
                normalized_voices[hhh_cat] = {
                    cat: score / category_counts[hhh_cat]
                    for cat, score in voices.items()
                }
        
        return normalized_voices


def test_analyzer():
    """Fonction de test de l'analyseur"""
    analyzer = TourismBrandVoiceAnalyzer()
    
    # Test sur un texte simple
    test_text = "Découvrez les merveilles cachées de Bali ! Réservez maintenant votre escapade exclusive dans ce paradis authentique. Vivez une expérience inoubliable au cœur de la culture locale."
    
    result = analyzer.analyze_brand_voice(test_text)
    
    print(f"Analyse du texte test:")
    print(f"Profil de voix: {result['brand_voice_profile']}")
    print(f"Mots détectés: {dict(result['matched_words'])}")
    
    return result


if __name__ == "__main__":
    test_analyzer()