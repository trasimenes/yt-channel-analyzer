"""
Module d'IA pour classifier les vidéos YouTube selon le framework HUB/HERO/HELP
Avec patterns configurables et apprentissage automatique
"""
import re
import json
from typing import Dict, List, Tuple, Optional, Any
import requests
import time

# Patterns par défaut pour chaque catégorie
DEFAULT_HELP_PATTERNS = [
    # Questions / demandes d'aide
    "how to", "how can i", "how do i", "what to do", "what should i do",
    "how does it work", "why is it not working", "i need help", "can someone help",
    "help me", "please help", "emergency help", "what if", "how can we", "who can fix",
    "step by step", "quick help", "fast fix", "need support", "need assistance",
    
    # Problèmes / erreurs  
    "error message", "problem with", "can't open", "won't start", "stuck on",
    "not working", "stopped working", "broken", "won't load", "issue with",
    "system failure", "bug fix", "unexpected error", "crashing", "freezing",
    "doesn't respond", "troubleshooting", "doesn't connect", "cannot access", "not responding",
    
    # Solutions / réparations
    "fix this", "fix it", "repair", "resolve", "patch", "workaround", "solution",
    "solving", "restart guide", "restore", "reinstall", "configuration help",
    "uninstall properly", "reset", "recover", "debug", "how to fix", "quick repair",
    "fixing issue", "full guide",
    
    # Guides / tutos
    "tutorial", "beginner's guide", "how-to", "walkthrough", "manual", "step-by-step",
    "detailed guide", "beginner tutorial", "learn how to", "training video", "help video",
    "setup guide", "installation help", "configuration guide", "usage instructions",
    "fixing tutorial", "ultimate guide", "for dummies", "everything you need to know", "getting started",
    
    # Expressions naturelles
    "i can't", "it won't", "is this normal", "does anyone know", "how i solved",
    "found the fix", "is there a fix", "what happens if", "works in 2025", "easy solution",
    "finally fixed", "does this work", "tested this", "proven method", "resolved!",
    "it worked for me", "please explain", "newbie question", "urgent", "quick tip",
    
    # Français
    "comment faire", "comment réparer", "aide pour", "tutoriel", "guide", "astuce",
    "conseils", "dépannage", "résoudre", "expliquer", "marche à suivre"
]

DEFAULT_HERO_PATTERNS = [
    # Événements et campagnes
    "launch", "lancement", "new", "nouveau", "première", "premier", "reveal", "unveil",
    "exclusive", "exclusif", "limited", "limité", "special", "spécial", "anniversary", "anniversaire",
    "event", "événement", "live", "direct", "breaking", "urgent", "announcement", "annonce",
    "world premiere", "première mondiale", "behind the scenes", "backstage", "making of",
    "campaign", "campagne", "commercial", "pub", "advertising", "publicité",
    
    # Émotions fortes
    "incredible", "incroyable", "amazing", "fantastique", "wow", "epic", "épique",
    "ultimate", "ultime", "best", "meilleur", "top", "greatest", "plus grand",
    "viral", "trending", "buzz", "sensational", "revolutionary", "révolutionnaire",
    
    # Mots temporels d'urgence
    "2024", "2025", "now", "maintenant", "today", "aujourd'hui", "this week", "cette semaine",
    "just released", "vient de sortir", "hot news", "breaking news", "dernière minute"
]

DEFAULT_HUB_PATTERNS = [
    # Séries et contenus réguliers
    "episode", "épisode", "part", "partie", "chapter", "chapitre", "season", "saison",
    "series", "série", "collection", "saga", "journey", "voyage", "adventure", "aventure",
    "discover", "découvrir", "explore", "explorer", "experience", "expérience",
    "destination", "travel", "voyage", "trip", "visit", "visite",
    
    # Contenus de marque réguliers
    "club med", "resort", "complexe", "hotel", "hôtel", "vacation", "vacances",
    "holiday", "séjour", "getaway", "échappée", "paradise", "paradis",
    
    # Formats récurrents
    "weekly", "hebdomadaire", "daily", "quotidien", "monthly", "mensuel",
    "spotlight", "focus", "featured", "mis en avant", "showcase", "présentation"
]

class HubHeroHelpClassifier:
    """
    Classifier basé sur des patterns configurables pour catégoriser les vidéos YouTube
    
    DEPRECATED: Cette classe est conservée pour compatibilité mais utilise maintenant
    la nouvelle logique multilingue de database.py
    """
    
    def __init__(self, patterns_file="patterns.json"):
        print("[AI-CLASSIFIER] ⚠️ DEPRECATED: HubHeroHelpClassifier utilise maintenant la logique multilingue")
        self.patterns_file = patterns_file
        self.patterns = self.load_patterns()
        
    def load_patterns(self) -> Dict[str, List[str]]:
        """Charger les patterns depuis le fichier ou utiliser les valeurs par défaut"""
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
                # Vérifier que toutes les clés sont présentes
                if all(key in patterns for key in ['help', 'hero', 'hub']):
                    return patterns
        except (FileNotFoundError, json.JSONDecodeError):
            pass
            
        # Retourner les patterns par défaut
        return {
            'help': DEFAULT_HELP_PATTERNS,
            'hero': DEFAULT_HERO_PATTERNS,
            'hub': DEFAULT_HUB_PATTERNS
        }
    
    def save_patterns(self):
        """Sauvegarder les patterns dans le fichier"""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PATTERNS] Erreur lors de la sauvegarde: {e}")
    
    def add_pattern(self, category: str, pattern: str):
        """Ajouter un nouveau pattern à une catégorie"""
        if category in self.patterns:
            if pattern not in self.patterns[category]:
                self.patterns[category].append(pattern.lower())
                self.save_patterns()
                return True
        return False
    
    def remove_pattern(self, category: str, pattern: str):
        """Supprimer un pattern d'une catégorie"""
        if category in self.patterns and pattern in self.patterns[category]:
            self.patterns[category].remove(pattern)
            self.save_patterns()
            return True
        return False
    
    def learn_from_video(self, title: str, category: str):
        """Apprendre automatiquement depuis une vidéo taggée manuellement"""
        # Extraire des mots-clés significatifs du titre
        words = re.findall(r'\b\w+\b', title.lower())
        # Ajouter des phrases courtes (2-3 mots) comme patterns
        for i in range(len(words) - 1):
            phrase = ' '.join(words[i:i+2])
            if len(phrase) > 3:  # Éviter les mots trop courts
                self.add_pattern(category, phrase)
    
    def is_category_video(self, title: str, description: str, category: str) -> bool:
        """Vérifier si une vidéo correspond à une catégorie donnée"""
        combined_text = f"{title} {description}".lower()
        patterns = self.patterns.get(category, [])
        return any(re.search(rf"\b{re.escape(pattern)}\b", combined_text) for pattern in patterns)
    
    def classify_video(self, title: str, description: str = "", views: int = 0, likes: int = 0) -> Tuple[str, int]:
        """
        Classifie une vidéo selon HUB/HERO/HELP
        
        DEPRECATED: Utilise maintenant la logique multilingue quand possible
        
        Args:
            title: Titre de la vidéo
            description: Description (optionnelle)
            views: Nombre de vues (pour contexte)
            likes: Nombre de likes (pour contexte)
            
        Returns:
            Tuple (catégorie, pourcentage de confiance)
        """
        # Essayer d'abord la nouvelle logique multilingue
        try:
            from yt_channel_analyzer.database import classify_video_with_language
            category, detected_language, confidence = classify_video_with_language(title, description)
            
            print(f"[AI-CLASSIFIER] 🌍 Utilisation de la logique multilingue: {category.upper()} ({detected_language}, {confidence}%)")
            return category, confidence
            
        except Exception as e:
            print(f"[AI-CLASSIFIER] ⚠️ Fallback vers logique legacy: {e}")
            # Fallback vers l'ancienne logique
            pass
        
        # Ancienne logique (conservée pour compatibilité)
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        text_combined = f"{title_lower} {desc_lower}"
        
        # Scores pour chaque catégorie
        hero_score = self._calculate_score(text_combined, self.patterns['hero'])
        hub_score = self._calculate_score(text_combined, self.patterns['hub'])
        help_score = self._calculate_score(text_combined, self.patterns['help'])
        
        # Bonus basés sur les métriques
        if views > 100000:  # Vidéos très vues = potentiel HERO
            hero_score += 15
        if views < 10000:   # Vidéos peu vues = potentiel HELP
            help_score += 10
            
        # Patterns spécifiques dans le titre
        if re.search(r'\b(how|comment|guide|tutorial|tips)\b', title_lower):
            help_score += 25
        if re.search(r'\b(discover|explore|experience)\b', title_lower):
            hub_score += 20
        if re.search(r'\b(new|launch|exclusive|live|premiere)\b', title_lower):
            hero_score += 20
            
        # Numérotation suggère une série (HUB)
        if re.search(r'\b(episode|ep|part|partie|\d+)\b', title_lower):
            hub_score += 15
            
        # Déterminer la catégorie gagnante
        max_score = max(hero_score, hub_score, help_score)
        
        if max_score == 0:
            return "hub", 50  # Par défaut si aucun pattern détecté
            
        if hero_score == max_score:
            confidence = min(95, 60 + hero_score)
            return "hero", confidence
        elif help_score == max_score:
            confidence = min(95, 60 + help_score)
            return "help", confidence
        else:
            confidence = min(95, 60 + hub_score)
            return "hub", confidence
    
    def _calculate_score(self, text: str, keywords: List[str]) -> int:
        """Calcule le score basé sur la présence de mots-clés"""
        score = 0
        for keyword in keywords:
            if keyword in text:
                # Score plus élevé pour des mots plus spécifiques
                score += len(keyword.split()) * 5
        return score
    
    def analyze_channel_strategy(self, videos: List[Dict]) -> Dict:
        """
        Analyse la stratégie globale d'une chaîne
        
        Args:
            videos: Liste des vidéos avec leurs classifications
            
        Returns:
            Dictionnaire avec les insights stratégiques
        """
        if not videos:
            return {}
            
        hero_count = sum(1 for v in videos if v.get('category') == 'hero')
        hub_count = sum(1 for v in videos if v.get('category') == 'hub') 
        help_count = sum(1 for v in videos if v.get('category') == 'help')
        total = len(videos)
        
        # Stratégie dominante
        if hero_count > hub_count and hero_count > help_count:
            strategy = "Stratégie HERO dominante - Focus sur le contenu viral"
        elif hub_count > help_count:
            strategy = "Stratégie HUB dominante - Focus sur l'engagement régulier"
        else:
            strategy = "Stratégie HELP dominante - Focus sur l'utilité"
            
        # Recommandations
        recommendations = []
        hero_ratio = hero_count / total * 100
        hub_ratio = hub_count / total * 100
        help_ratio = help_count / total * 100
        
        if help_ratio < 20:
            recommendations.append("Créer plus de contenu HELP pour répondre aux questions des utilisateurs")
        if hero_ratio < 15:
            recommendations.append("Développer des campagnes HERO pour augmenter la visibilité")
        if hub_ratio < 40:
            recommendations.append("Renforcer le contenu HUB pour fidéliser l'audience")
        if hero_ratio > 50:
            recommendations.append("Équilibrer avec plus de contenu HUB pour maintenir l'engagement")
            
        return {
            'strategy': strategy,
            'hero_ratio': round(hero_ratio, 1),
            'hub_ratio': round(hub_ratio, 1),
            'help_ratio': round(help_ratio, 1),
            'recommendations': recommendations
        }

def extract_views_number(views_str):
    """Extraire le nombre de vues depuis une chaîne comme '1.2M' ou '15,000'"""
    if not views_str:
        return 0
        
    views_str = str(views_str).strip().upper()
    
    # Supprimer les espaces et virgules
    views_str = views_str.replace(',', '').replace(' ', '').replace('VUES', '')
    
    # Gérer les suffixes K, M, B
    multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
    
    for suffix, multiplier in multipliers.items():
        if views_str.endswith(suffix):
            try:
                number = float(views_str[:-1])
                return int(number * multiplier)
            except ValueError:
                break
    
    # Essayer de convertir directement en entier
    try:
        return int(views_str)
    except ValueError:
        return 0

def calculate_performance_score(video, category, distribution_type):
    """Calculer un score de performance pour une vidéo selon sa catégorie et son type"""
    views = extract_views_number(video.get('views', '0'))
    likes = extract_views_number(video.get('likes', '0'))
    
    # Score de base basé sur les vues (logarithmique pour éviter les valeurs extrêmes)
    if views > 0:
        base_score = min(views / 50000, 10)  # Score max de 10 pour 500k+ vues
    else:
        base_score = 0
    
    # Bonus pour l'engagement (ratio likes/vues)
    if views > 0 and likes > 0:
        engagement_ratio = likes / views
        engagement_bonus = min(engagement_ratio * 500, 3)  # Bonus max de 3
    else:
        engagement_bonus = 0
    
    # Ajustement selon la catégorie
    category_expectations = {
        'hero': {'min_views': 50000, 'multiplier': 1.3},    # HERO doit avoir plus de visibilité
        'hub': {'min_views': 10000, 'multiplier': 1.0},     # HUB performance standard
        'help': {'min_views': 5000, 'multiplier': 0.9}      # HELP peut avoir moins de vues
    }
    
    category_data = category_expectations.get(category, category_expectations['hub'])
    
    # Bonus si la vidéo dépasse les attentes de sa catégorie
    expectation_bonus = 1.0
    if views > category_data['min_views']:
        expectation_bonus = category_data['multiplier']
    
    # Ajustement selon organic/paid
    distribution_modifier = 1.0
    if distribution_type == 'paid':
        # Le contenu payé devrait performer mieux proportionnellement
        if views > 100000:
            distribution_modifier = 1.2  # Bonus pour les bonnes performances paid
        else:
            distribution_modifier = 0.8  # Malus si le paid ne performe pas
    else:  # organic
        # Bonus pour l'organic qui performe bien
        if views > 50000:
            distribution_modifier = 1.3  # Très bon organic performance
    
    final_score = (base_score + engagement_bonus) * expectation_bonus * distribution_modifier
    
    return round(min(final_score, 10), 2)  # Score entre 0 et 10

def classify_videos_batch(videos: List[Dict], paid_threshold: int = 10000) -> List[Dict]:
    """
    Classifie une liste de vidéos selon HUB/HERO/HELP et Organic/Paid
    Utilise la nouvelle logique multilingue pour une classification plus précise
    
    Args:
        videos: Liste de dictionnaires avec au minimum 'title'
        paid_threshold: Seuil de vues pour considérer qu'une vidéo est "paid"
        
    Returns:
        Liste des vidéos enrichies avec classifications et scores
    """
    classified_videos = []
    
    for video in videos:
        title = video.get('title', '')
        description = video.get('description', '')
        
        # Extraction des métriques numériques
        views_numeric = extract_views_number(video.get('views', 0))
        likes_numeric = extract_views_number(video.get('likes', 0))
        
        # Classification HUB/HERO/HELP avec logique multilingue
        try:
            from yt_channel_analyzer.database import classify_video_with_language
            category, detected_language, confidence = classify_video_with_language(title, description)
            
            print(f"[AI-CLASSIFIER] 🌍 Vidéo '{title[:50]}...' → {category.upper()} ({detected_language}, {confidence}%)")
            
        except Exception as e:
            print(f"[AI-CLASSIFIER] ⚠️ Erreur classification multilingue: {e}")
            # Fallback vers l'ancienne logique
            classifier = HubHeroHelpClassifier()
            category, confidence = classifier.classify_video(title, description, views_numeric, likes_numeric)
            detected_language = 'fr'  # Langue par défaut
        
        # Classification Organic vs Paid
        distribution_type = 'paid' if views_numeric > paid_threshold else 'organic'
        
        # Calcul du score de performance
        performance_score = calculate_performance_score(video, category, distribution_type)
        
        # Création de la vidéo enrichie
        video_classified = video.copy()
        video_classified.update({
            'category': category,
            'confidence': confidence,
            'distribution_type': distribution_type,
            'views_numeric': views_numeric,
            'likes_numeric': likes_numeric,
            'performance_score': performance_score,
            'paid_threshold': paid_threshold,
            'detected_language': detected_language  # Ajouter la langue détectée
        })
        
        classified_videos.append(video_classified)
    
    return classified_videos

def analyze_content_performance_matrix(classified_videos: List[Dict]) -> Dict:
    """
    Analyse la matrice de performance HUB/HERO/HELP vs Organic/Paid 
    Comme dans le style de présentation Airbnb
    """
    if not classified_videos:
        return {}
    
    # Initialiser la matrice de performance
    matrix = {
        'hero': {'organic': [], 'paid': []},
        'hub': {'organic': [], 'paid': []},
        'help': {'organic': [], 'paid': []}
    }
    
    # Remplir la matrice avec les données
    for video in classified_videos:
        category = video.get('category', 'hub')
        dist_type = video.get('distribution_type', 'organic')
        views = video.get('views_numeric', 0)
        
        if category in matrix and dist_type in matrix[category]:
            matrix[category][dist_type].append(views)
    
    # Calculer les statistiques pour chaque cellule
    def calculate_cell_stats(views_list):
        if not views_list:
            return {'median': 0, 'count': 0, 'total': 0}
        
        views_list.sort()
        n = len(views_list)
        median = views_list[n//2] if n % 2 == 1 else (views_list[n//2-1] + views_list[n//2]) // 2
        
        return {
            'median': median,
            'count': n,
            'total': sum(views_list)
        }
    
    # Construire les résultats comme dans l'image Airbnb
    results = {}
    for category in ['hero', 'hub', 'help']:
        results[category] = {
            'organic': calculate_cell_stats(matrix[category]['organic']),
            'paid': calculate_cell_stats(matrix[category]['paid'])
        }
    
    # Calculs globaux
    total_videos = len(classified_videos)
    total_organic = sum(1 for v in classified_videos if v.get('distribution_type') == 'organic')
    total_paid = total_videos - total_organic
    
    results['summary'] = {
        'total_videos': total_videos,
        'organic_count': total_organic,
        'paid_count': total_paid,
        'organic_percentage': round(total_organic / total_videos * 100, 1) if total_videos > 0 else 0,
        'paid_percentage': round(total_paid / total_videos * 100, 1) if total_videos > 0 else 0
    }
    
    return results 

class IndustryClassifier:
    """Classificateur intelligent pour détecter automatiquement l'industrie des compétiteurs"""
    
    # Base de données de marques connues avec leurs industries
    KNOWN_BRANDS = {
        # Food & Beverage
        'mcdonalds': 'food', 'mcdonald': 'food', 'burger king': 'food', 'kfc': 'food',
        'starbucks': 'food', 'dominos': 'food', 'pizza hut': 'food', 'subway': 'food',
        'coca cola': 'food', 'pepsi': 'food', 'nestle': 'food', 'unilever': 'food',
        
        # Hospitality & Travel
        'club med': 'hospitality', 'clubmed': 'hospitality', 'club méditerranée': 'hospitality',
        'marriott': 'hospitality', 'marriott bonvoy': 'hospitality', 'bonvoy': 'hospitality',
        'hilton': 'hospitality', 'hyatt': 'hospitality',
        'airbnb': 'hospitality', 'booking': 'hospitality', 'booking.com': 'hospitality',
        'expedia': 'hospitality', 'accor': 'hospitality', 'intercontinental': 'hospitality',
        
        # Technology
        'apple': 'technology', 'microsoft': 'technology', 'google': 'technology',
        'amazon': 'technology', 'facebook': 'technology', 'meta': 'technology',
        'netflix': 'technology', 'spotify': 'technology', 'uber': 'technology',
        'tesla': 'technology', 'samsung': 'technology', 'sony': 'technology',
        
        # Fashion & Beauty
        'nike': 'fashion', 'adidas': 'fashion', 'zara': 'fashion', 'h&m': 'fashion',
        'gucci': 'fashion', 'louis vuitton': 'fashion', 'chanel': 'fashion',
        'loreal': 'beauty', 'sephora': 'beauty', 'maybelline': 'beauty',
        
        # Automotive
        'toyota': 'automotive', 'volkswagen': 'automotive', 'bmw': 'automotive',
        'mercedes': 'automotive', 'audi': 'automotive', 'ford': 'automotive',
        
        # Finance
        'visa': 'finance', 'mastercard': 'finance', 'paypal': 'finance',
        'american express': 'finance', 'jpmorgan': 'finance',
        
        # Health & Wellness
        'johnson': 'health', 'pfizer': 'health', 'abbott': 'health',
        'roche': 'health', 'novartis': 'health',
        
        # Retail
        'walmart': 'retail', 'target': 'retail', 'ikea': 'retail',
        'costco': 'retail', 'carrefour': 'retail',
        
        # Entertainment & Media
        'disney': 'entertainment', 'warner': 'entertainment', 'universal': 'entertainment',
        'paramount': 'entertainment', 'youtube': 'entertainment', 'tiktok': 'entertainment'
    }
    
    # Mots-clés par industrie pour l'analyse de contenu
    INDUSTRY_KEYWORDS = {
        'food': ['restaurant', 'food', 'cuisine', 'recipe', 'cooking', 'chef', 'meal', 'drink', 'cafe', 'bar', 'pizza', 'burger', 'coffee'],
        'hospitality': ['hotel', 'travel', 'vacation', 'booking', 'resort', 'tourism', 'trip', 'destination', 'accommodation', 'hospitality'],
        'technology': ['tech', 'software', 'app', 'digital', 'innovation', 'startup', 'ai', 'programming', 'developer', 'gadget', 'smartphone'],
        'fashion': ['fashion', 'style', 'clothing', 'outfit', 'trend', 'design', 'wear', 'collection', 'brand', 'luxury'],
        'beauty': ['beauty', 'makeup', 'skincare', 'cosmetic', 'hair', 'nail', 'spa', 'wellness', 'treatment'],
        'automotive': ['car', 'auto', 'vehicle', 'driving', 'motor', 'garage', 'mechanic', 'automotive', 'truck', 'motorcycle'],
        'finance': ['bank', 'finance', 'investment', 'money', 'credit', 'loan', 'insurance', 'financial', 'trading'],
        'health': ['health', 'medical', 'doctor', 'hospital', 'medicine', 'care', 'wellness', 'fitness', 'nutrition'],
        'retail': ['shop', 'store', 'retail', 'shopping', 'market', 'sale', 'discount', 'product', 'buy'],
        'entertainment': ['movie', 'film', 'music', 'game', 'entertainment', 'show', 'tv', 'streaming', 'content'],
        'education': ['education', 'school', 'university', 'course', 'learning', 'teacher', 'student', 'tutorial', 'training'],
        'sports': ['sport', 'fitness', 'gym', 'workout', 'athlete', 'team', 'competition', 'exercise', 'training']
    }
    
    def __init__(self):
        self.last_web_search = 0
        self.search_delay = 1  # Délai entre les recherches web
    
    def classify_industry(self, channel_name: str, description: str = "", videos: Optional[List[Dict]] = None) -> Optional[str]:
        """Classifie l'industrie d'une chaîne en utilisant plusieurs méthodes"""
        
        # 1. Vérifier dans la base de marques connues
        industry = self._check_known_brands(channel_name)
        if industry:
            print(f"[CLASSIFIER] 🎯 Industrie détectée via marques connues: {channel_name} → {industry}")
            return industry
        
        # 2. Analyser les mots-clés dans le nom et la description
        industry = self._analyze_keywords(channel_name, description, videos)
        if industry:
            print(f"[CLASSIFIER] 📝 Industrie détectée via mots-clés: {channel_name} → {industry}")
            return industry
        
        # 3. Recherche web en dernier recours
        industry = self._web_search_industry(channel_name)
        if industry:
            print(f"[CLASSIFIER] 🌐 Industrie détectée via recherche web: {channel_name} → {industry}")
            return industry
        
        print(f"[CLASSIFIER] ❓ Impossible de déterminer l'industrie pour: {channel_name}")
        return None
    
    def _check_known_brands(self, channel_name: str) -> Optional[str]:
        """Vérifie si le nom de la chaîne correspond à une marque connue"""
        name_lower = channel_name.lower().strip()
        
        # Recherche exacte
        if name_lower in self.KNOWN_BRANDS:
            return self.KNOWN_BRANDS[name_lower]
        
        # Recherche partielle (pour "McDonald's France" → "mcdonalds")
        for brand, industry in self.KNOWN_BRANDS.items():
            if brand in name_lower or name_lower in brand:
                return industry
        
        return None
    
    def _analyze_keywords(self, channel_name: str, description: str, videos: Optional[List[Dict]]) -> Optional[str]:
        """Analyse les mots-clés dans le nom, description et titres de vidéos"""
        text_to_analyze = f"{channel_name} {description}".lower()
        
        # Ajouter les titres de quelques vidéos récentes
        if videos:
            recent_titles = [v.get('title', '') for v in videos[:10] if v.get('title')]
            text_to_analyze += " " + " ".join(recent_titles).lower()
        
        # Compter les occurrences par industrie
        industry_scores = {}
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                score += text_to_analyze.count(keyword)
            if score > 0:
                industry_scores[industry] = score
        
        # Retourner l'industrie avec le score le plus élevé
        if industry_scores:
            best_industry = max(industry_scores.keys(), key=lambda x: industry_scores[x])
            if industry_scores[best_industry] >= 2:  # Seuil minimum
                return best_industry
        
        return None
    
    def _web_search_industry(self, channel_name: str) -> Optional[str]:
        """Recherche web pour identifier l'industrie"""
        # Limiter les appels pour éviter le spam
        current_time = time.time()
        if current_time - self.last_web_search < self.search_delay:
            time.sleep(self.search_delay)
        
        try:
            # TODO: Implémenter la recherche web quand l'API sera disponible
            # from ..web_search import web_search
            # 
            # query = f"{channel_name} company industry sector business what does"
            # results = web_search(query, f"Recherche industrie pour {channel_name}")
            # 
            # if results and len(results) > 0:
            #     # Analyser les résultats de recherche
            #     search_text = ""
            #     for result in results[:3]:  # Analyser les 3 premiers résultats
            #         search_text += f" {result.get('title', '')} {result.get('snippet', '')}"
            #     
            #     # Utiliser l'analyse de mots-clés sur les résultats
            #     industry = self._analyze_keywords("", search_text.lower(), None)
            #     if industry:
            #         self.last_web_search = time.time()
            #         return industry
            
            # Pour l'instant, retourner None car la recherche web n'est pas disponible
            pass
            
        except Exception as e:
            print(f"[CLASSIFIER] ⚠️ Erreur lors de la recherche web: {e}")
        
        self.last_web_search = time.time()
        return None
    
    def get_region_from_name(self, channel_name: str) -> str:
        """Détecte la région basée sur le nom de la chaîne"""
        name_lower = channel_name.lower()
        
        # Indicateurs géographiques
        region_indicators = {
            'europe': ['france', 'french', 'français', 'europe', 'european', 'belgium', 'belge', 'spain', 'spanish', 'italy', 'italian', 'germany', 'german', 'uk', 'britain', 'british'],
            'north-america': ['usa', 'us', 'america', 'american', 'canada', 'canadian'],
            'asia': ['japan', 'japanese', 'china', 'chinese', 'korea', 'korean', 'india', 'indian', 'asia', 'asian'],
            'worldwide': ['international', 'global', 'world', 'worldwide']
        }
        
        for region, indicators in region_indicators.items():
            for indicator in indicators:
                if indicator in name_lower:
                    return region
        
        # Par défaut, Europe
        return 'Europe'


# Instance globale
industry_classifier = IndustryClassifier() 