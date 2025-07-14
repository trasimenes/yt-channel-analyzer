"""
Module de classification des vidéos et playlists.

Ce module contient toutes les fonctions liées à la classification :
- Classification automatique par patterns
- Classification par IA
- Gestion des règles personnalisées
- Validation humaine
- Intégrité des classifications
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .base import get_db_connection, DatabaseUtils


class ClassificationPatternManager:
    """Gestionnaire des patterns de classification."""
    
    def __init__(self):
        self.db_utils = DatabaseUtils()
    
    def get_classification_patterns(self, language: str = None) -> Dict:
        """Récupérer les patterns de classification pour une langue donnée"""
        patterns = self.get_default_classification_patterns(language or 'fr')
        
        # Ajouter les patterns personnalisés
        custom_patterns = self._get_custom_patterns(language)
        for category, custom_list in custom_patterns.items():
            if category in patterns:
                patterns[category].extend(custom_list)
            else:
                patterns[category] = custom_list
        
        return patterns
    
    def get_default_classification_patterns(self, language: str = 'fr') -> Dict:
        """Récupérer les patterns par défaut pour une langue"""
        patterns = {
            'fr': {
                'hero': [
                    'nouveau', 'nouveauté', 'lancement', 'première', 'exclusif', 'sortie',
                    'annonce', 'révélation', 'découverte', 'inédit', 'breaking', 'news',
                    'événement', 'festival', 'concert', 'spectacle', 'ouverture',
                    'inauguration', 'célébration', 'fête', 'anniversaire'
                ],
                'hub': [
                    'visite', 'découvrir', 'explorer', 'présentation', 'tour',
                    'destination', 'voyage', 'séjour', 'vacances', 'nature',
                    'parc', 'center parcs', 'village', 'cottage', 'hébergement',
                    'activité', 'loisir', 'détente', 'bien-être', 'spa',
                    'restaurant', 'gastronomie', 'cuisine', 'aqua mundo'
                ],
                'help': [
                    'comment', 'tuto', 'tutoriel', 'guide', 'conseil', 'astuce',
                    'aide', 'explication', 'mode d\'emploi', 'étape', 'procédure',
                    'réserver', 'réservation', 'booking', 'planifier', 'organiser',
                    'préparer', 'checklist', 'tips', 'faq', 'questions',
                    'problème', 'solution', 'dépannage', 'assistance'
                ]
            },
            'en': {
                'hero': [
                    'new', 'launch', 'first', 'exclusive', 'release', 'announcement',
                    'reveal', 'discovery', 'unprecedented', 'breaking', 'news',
                    'event', 'festival', 'concert', 'show', 'opening',
                    'inauguration', 'celebration', 'party', 'anniversary'
                ],
                'hub': [
                    'visit', 'discover', 'explore', 'presentation', 'tour',
                    'destination', 'travel', 'stay', 'vacation', 'nature',
                    'park', 'center parcs', 'village', 'cottage', 'accommodation',
                    'activity', 'leisure', 'relaxation', 'wellness', 'spa',
                    'restaurant', 'gastronomy', 'cuisine', 'aqua mundo'
                ],
                'help': [
                    'how', 'tutorial', 'guide', 'advice', 'tip', 'help',
                    'explanation', 'manual', 'step', 'procedure', 'book',
                    'booking', 'plan', 'organize', 'prepare', 'checklist',
                    'tips', 'faq', 'questions', 'problem', 'solution',
                    'troubleshooting', 'assistance'
                ]
            },
            'de': {
                'hero': [
                    'neu', 'start', 'erste', 'exklusiv', 'veröffentlichung',
                    'ankündigung', 'enthüllung', 'entdeckung', 'einmalig',
                    'breaking', 'news', 'ereignis', 'festival', 'konzert',
                    'show', 'eröffnung', 'einweihung', 'feier', 'jahrestag'
                ],
                'hub': [
                    'besuch', 'entdecken', 'erkunden', 'präsentation', 'tour',
                    'destination', 'reise', 'aufenthalt', 'urlaub', 'natur',
                    'park', 'center parcs', 'dorf', 'cottage', 'unterkunft',
                    'aktivität', 'freizeit', 'entspannung', 'wellness', 'spa',
                    'restaurant', 'gastronomie', 'küche', 'aqua mundo'
                ],
                'help': [
                    'wie', 'tutorial', 'anleitung', 'ratschlag', 'tipp',
                    'hilfe', 'erklärung', 'handbuch', 'schritt', 'verfahren',
                    'buchen', 'buchung', 'planen', 'organisieren', 'vorbereiten',
                    'checkliste', 'tipps', 'faq', 'fragen', 'problem',
                    'lösung', 'fehlerbehebung', 'unterstützung'
                ]
            },
            'nl': {
                'hero': [
                    'nieuw', 'lancering', 'eerste', 'exclusief', 'release',
                    'aankondiging', 'onthulling', 'ontdekking', 'uniek',
                    'breaking', 'nieuws', 'evenement', 'festival', 'concert',
                    'show', 'opening', 'inwijding', 'viering', 'verjaardag'
                ],
                'hub': [
                    'bezoek', 'ontdekken', 'verkennen', 'presentatie', 'tour',
                    'bestemming', 'reis', 'verblijf', 'vakantie', 'natuur',
                    'park', 'center parcs', 'dorp', 'cottage', 'accommodatie',
                    'activiteit', 'vrije tijd', 'ontspanning', 'wellness', 'spa',
                    'restaurant', 'gastronomie', 'keuken', 'aqua mundo'
                ],
                'help': [
                    'hoe', 'tutorial', 'gids', 'advies', 'tip', 'hulp',
                    'uitleg', 'handleiding', 'stap', 'procedure', 'boeken',
                    'boeking', 'plannen', 'organiseren', 'voorbereiden',
                    'checklist', 'tips', 'faq', 'vragen', 'probleem',
                    'oplossing', 'probleemoplossing', 'ondersteuning'
                ]
            }
        }
        
        return patterns.get(language, patterns['fr'])
    
    def _get_custom_patterns(self, language: str = None) -> Dict:
        """Récupérer les patterns personnalisés"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT category, pattern FROM custom_classification_rules'
        params = []
        
        if language:
            query += ' WHERE language = ? OR language = "all"'
            params.append(language)
        
        cursor.execute(query, params)
        
        patterns = defaultdict(list)
        for row in cursor.fetchall():
            patterns[row[0]].append(row[1])
        
        conn.close()
        return dict(patterns)
    
    def add_classification_pattern(self, category: str, pattern: str, language: str = 'fr') -> bool:
        """Ajouter un pattern de classification"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO custom_classification_rules (category, pattern, language)
                VALUES (?, ?, ?)
            ''', (category, pattern, language))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Pattern déjà existant
            return False
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout du pattern: {e}")
            return False
        finally:
            conn.close()
    
    def remove_classification_pattern(self, category: str, pattern: str, language: str = 'fr') -> bool:
        """Supprimer un pattern de classification"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM custom_classification_rules 
                WHERE category = ? AND pattern = ? AND language = ?
            ''', (category, pattern, language))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Erreur lors de la suppression du pattern: {e}")
            return False
        finally:
            conn.close()
    
    def normalize_pattern(self, pattern: str) -> str:
        """Normaliser un pattern pour la recherche"""
        # Transforme un pattern en regex souple : espaces/tirets/points interchangeables
        # Ex: 'how to' => r'h[o0]w[\s\-\._]*to'
        # On remplace chaque espace par [\s\-\._]*
        normalized = re.sub(r'\s+', r'[\\s\\-\\._]*', pattern.lower())
        return normalized


class VideoClassifier:
    """Classificateur de vidéos."""
    
    def __init__(self):
        self.pattern_manager = ClassificationPatternManager()
        self.db_utils = DatabaseUtils()
    
    def classify_video_with_language(self, title: str, description: str = "") -> Tuple[str, str, int]:
        """Classifier une vidéo avec détection automatique de langue"""
        # Détecter la langue
        language = self.db_utils.detect_language(title + " " + description)
        
        # Obtenir les patterns pour cette langue
        patterns = self.pattern_manager.get_classification_patterns(language)
        
        # Fonction interne pour calculer un score pondéré
        def calculate_weighted_score(text: str, pattern_list: list) -> float:
            score = 0
            text_lower = text.lower()
            
            for pattern in pattern_list:
                # Compter les occurrences du pattern
                pattern_normalized = self.pattern_manager.normalize_pattern(pattern)
                matches = len(re.findall(pattern_normalized, text_lower))
                
                # Pondérer selon la longueur du pattern (plus long = plus spécifique)
                weight = len(pattern.split())
                score += matches * weight
            
            return score
        
        # Calculer les scores pour chaque catégorie
        category_scores = {}
        full_text = f"{title} {description}"
        
        for category, pattern_list in patterns.items():
            title_score = calculate_weighted_score(title, pattern_list)
            desc_score = calculate_weighted_score(description, pattern_list)
            
            # Pondérer le titre plus fortement que la description
            total_score = title_score * 2 + desc_score
            category_scores[category] = total_score
        
        # Trouver la catégorie avec le meilleur score
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]
            
            # Seuil minimum pour considérer une classification comme valide
            if best_score >= 1:
                return best_category, language, int(best_score)
        
        # Aucune classification trouvée
        return 'uncategorized', language, 0
    
    def classify_videos_directly_with_keywords(self, competitor_id: int) -> Dict:
        """Classifier directement les vidéos avec des mots-clés"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer les vidéos non classifiées
            cursor.execute('''
                SELECT id, title, description, category
                FROM video 
                WHERE concurrent_id = ? AND (category IS NULL OR category = '' OR category = 'uncategorized')
            ''', (competitor_id,))
            
            videos = cursor.fetchall()
            
            if not videos:
                return {
                    'success': True,
                    'message': 'Aucune vidéo à classifier',
                    'classified_count': 0
                }
            
            classified_count = 0
            
            for video in videos:
                video_id, title, description, current_category = video
                
                # Classifier la vidéo
                category, language, confidence = self.classify_video_with_language(title, description or "")
                
                # Mettre à jour si une classification valide a été trouvée
                if category != 'uncategorized' and confidence > 0:
                    cursor.execute('''
                        UPDATE video 
                        SET category = ?, classification_source = 'keyword', last_updated = ?
                        WHERE id = ?
                    ''', (category, datetime.now(), video_id))
                    classified_count += 1
            
            conn.commit()
            
            return {
                'success': True,
                'message': f'{classified_count} vidéos classifiées sur {len(videos)}',
                'classified_count': classified_count,
                'total_videos': len(videos)
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def reclassify_all_videos_with_multilingual_logic(self) -> Dict:
        """Reclassifier toutes les vidéos avec la logique multilingue"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer toutes les vidéos non protégées par validation humaine
            cursor.execute('''
                SELECT id, title, description, category, is_human_validated
                FROM video 
                WHERE is_human_validated = 0 OR is_human_validated IS NULL
            ''')
            
            videos = cursor.fetchall()
            
            if not videos:
                return {
                    'success': True,
                    'message': 'Aucune vidéo à reclassifier',
                    'reclassified_count': 0
                }
            
            reclassified_count = 0
            category_changes = defaultdict(int)
            
            for video in videos:
                video_id, title, description, old_category, is_human_validated = video
                
                # Skip si validé par un humain
                if is_human_validated:
                    continue
                
                # Classifier la vidéo
                new_category, language, confidence = self.classify_video_with_language(title, description or "")
                
                # Mettre à jour si la classification a changé
                if new_category != old_category:
                    cursor.execute('''
                        UPDATE video 
                        SET category = ?, classification_source = 'multilingual', last_updated = ?
                        WHERE id = ?
                    ''', (new_category, datetime.now(), video_id))
                    
                    reclassified_count += 1
                    category_changes[f"{old_category} → {new_category}"] += 1
            
            conn.commit()
            
            return {
                'success': True,
                'message': f'{reclassified_count} vidéos reclassifiées sur {len(videos)}',
                'reclassified_count': reclassified_count,
                'total_videos': len(videos),
                'category_changes': dict(category_changes)
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()


class PlaylistClassifier:
    """Classificateur de playlists."""
    
    def __init__(self):
        self.pattern_manager = ClassificationPatternManager()
        self.db_utils = DatabaseUtils()
    
    def classify_playlist_with_ai(self, name: str, description: str = "") -> str:
        """Classifier une playlist avec IA (utilise les patterns pour l'instant)"""
        # Utilise la même logique que les vidéos pour l'instant
        category, language, confidence = self.classify_video_with_language(name, description)
        return category
    
    def auto_classify_uncategorized_playlists(self, competitor_id: int) -> Dict:
        """Classifier automatiquement les playlists non classifiées"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Récupérer les playlists non classifiées
            cursor.execute('''
                SELECT id, title, description, category
                FROM playlist 
                WHERE concurrent_id = ? AND (category IS NULL OR category = '' OR category = 'uncategorized')
            ''', (competitor_id,))
            
            playlists = cursor.fetchall()
            
            if not playlists:
                return {
                    'success': True,
                    'message': 'Aucune playlist à classifier',
                    'classified_count': 0
                }
            
            classified_count = 0
            
            for playlist in playlists:
                playlist_id, title, description, current_category = playlist
                
                # Classifier la playlist
                category = self.classify_playlist_with_ai(title, description or "")
                
                # Mettre à jour si une classification valide a été trouvée
                if category != 'uncategorized':
                    cursor.execute('''
                        UPDATE playlist 
                        SET category = ?, classification_source = 'ai', last_updated = ?
                        WHERE id = ?
                    ''', (category, datetime.now(), playlist_id))
                    classified_count += 1
            
            conn.commit()
            
            return {
                'success': True,
                'message': f'{classified_count} playlists classifiées sur {len(playlists)}',
                'classified_count': classified_count,
                'total_playlists': len(playlists)
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def apply_playlist_categories_to_videos_safe(self, competitor_id: int, 
                                               specific_playlist_id: int = None, 
                                               force_human_playlists: bool = False):
        """Appliquer les catégories de playlist aux vidéos de manière sécurisée"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Construire la requête pour récupérer les playlists
            query = '''
                SELECT p.id, p.category, p.is_human_validated, p.classification_source
                FROM playlist p
                WHERE p.concurrent_id = ? 
                AND p.category IS NOT NULL 
                AND p.category != ''
                AND p.category != 'uncategorized'
            '''
            
            params = [competitor_id]
            
            if specific_playlist_id:
                query += ' AND p.id = ?'
                params.append(specific_playlist_id)
            
            if not force_human_playlists:
                query += ' AND (p.is_human_validated = 0 OR p.is_human_validated IS NULL)'
            
            cursor.execute(query, params)
            playlists = cursor.fetchall()
            
            applied_count = 0
            
            for playlist in playlists:
                playlist_id, category, is_human_validated, classification_source = playlist
                
                # Appliquer la catégorie aux vidéos de la playlist
                cursor.execute('''
                    UPDATE video 
                    SET category = ?, classification_source = 'playlist', last_updated = ?
                    WHERE id IN (
                        SELECT v.id 
                        FROM video v
                        JOIN playlist_video pv ON v.id = pv.video_id
                        WHERE pv.playlist_id = ?
                        AND (v.is_human_validated = 0 OR v.is_human_validated IS NULL)
                    )
                ''', (category, datetime.now(), playlist_id))
                
                applied_count += cursor.rowcount
            
            conn.commit()
            
            return {
                'success': True,
                'message': f'Catégories appliquées à {applied_count} vidéos',
                'applied_count': applied_count,
                'playlists_processed': len(playlists)
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()


class ClassificationIntegrityManager:
    """Gestionnaire d'intégrité des classifications."""
    
    def verify_classification_integrity(self) -> Dict:
        """Vérifier l'intégrité des classifications"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            issues = []
            
            # Vérifier les vidéos sans catégorie
            cursor.execute('''
                SELECT COUNT(*) FROM video 
                WHERE category IS NULL OR category = '' OR category = 'uncategorized'
            ''')
            uncategorized_videos = cursor.fetchone()[0]
            
            if uncategorized_videos > 0:
                issues.append(f"{uncategorized_videos} vidéos sans catégorie")
            
            # Vérifier les playlists sans catégorie
            cursor.execute('''
                SELECT COUNT(*) FROM playlist 
                WHERE category IS NULL OR category = '' OR category = 'uncategorized'
            ''')
            uncategorized_playlists = cursor.fetchone()[0]
            
            if uncategorized_playlists > 0:
                issues.append(f"{uncategorized_playlists} playlists sans catégorie")
            
            # Vérifier les incohérences de source
            cursor.execute('''
                SELECT COUNT(*) FROM video 
                WHERE classification_source IS NULL OR classification_source = ''
            ''')
            no_source_videos = cursor.fetchone()[0]
            
            if no_source_videos > 0:
                issues.append(f"{no_source_videos} vidéos sans source de classification")
            
            # Vérifier les conflits potentiels
            cursor.execute('''
                SELECT COUNT(*) FROM video 
                WHERE is_human_validated = 1 AND classification_source != 'human'
            ''')
            conflicting_validations = cursor.fetchone()[0]
            
            if conflicting_validations > 0:
                issues.append(f"{conflicting_validations} vidéos avec validation humaine incohérente")
            
            return {
                'success': True,
                'issues': issues,
                'total_issues': len(issues),
                'is_healthy': len(issues) == 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def fix_classification_tracking(self):
        """Corriger le tracking des classifications"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Corriger les sources de classification manquantes
            cursor.execute('''
                UPDATE video 
                SET classification_source = 'auto'
                WHERE classification_source IS NULL OR classification_source = ''
            ''')
            
            # Corriger les flags de validation humaine
            cursor.execute('''
                UPDATE video 
                SET is_human_validated = 0
                WHERE is_human_validated IS NULL
            ''')
            
            # Même chose pour les playlists
            cursor.execute('''
                UPDATE playlist 
                SET classification_source = 'auto'
                WHERE classification_source IS NULL OR classification_source = ''
            ''')
            
            cursor.execute('''
                UPDATE playlist 
                SET is_human_validated = 0
                WHERE is_human_validated IS NULL
            ''')
            
            conn.commit()
            print("✅ Tracking des classifications corrigé")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la correction du tracking: {e}")
        finally:
            conn.close()


class ClassificationSettingsManager:
    """Gestionnaire des paramètres de classification."""
    
    def get_ai_classification_setting(self) -> bool:
        """Récupérer le paramètre d'activation de la classification IA"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT value FROM settings WHERE key = "ai_classification_enabled"')
            result = cursor.fetchone()
            
            if result:
                return result[0].lower() == 'true'
            else:
                # Valeur par défaut
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors de la récupération du paramètre IA: {e}")
            return True
        finally:
            conn.close()
    
    def set_ai_classification_setting(self, enabled: bool) -> bool:
        """Définir le paramètre d'activation de la classification IA"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ("ai_classification_enabled", ?, ?)
            ''', (str(enabled).lower(), datetime.now()))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la définition du paramètre IA: {e}")
            return False
        finally:
            conn.close()


# Instances globales des gestionnaires
pattern_manager = ClassificationPatternManager()
video_classifier = VideoClassifier()
playlist_classifier = PlaylistClassifier()
integrity_manager = ClassificationIntegrityManager()
settings_manager = ClassificationSettingsManager()

# Fonctions de compatibilité
get_classification_patterns = pattern_manager.get_classification_patterns
get_default_classification_patterns = pattern_manager.get_default_classification_patterns
add_classification_pattern = pattern_manager.add_classification_pattern
remove_classification_pattern = pattern_manager.remove_classification_pattern
normalize_pattern = pattern_manager.normalize_pattern

classify_video_with_language = video_classifier.classify_video_with_language
classify_videos_directly_with_keywords = video_classifier.classify_videos_directly_with_keywords
reclassify_all_videos_with_multilingual_logic = video_classifier.reclassify_all_videos_with_multilingual_logic

classify_playlist_with_ai = playlist_classifier.classify_playlist_with_ai
auto_classify_uncategorized_playlists = playlist_classifier.auto_classify_uncategorized_playlists
apply_playlist_categories_to_videos_safe = playlist_classifier.apply_playlist_categories_to_videos_safe

verify_classification_integrity = integrity_manager.verify_classification_integrity
fix_classification_tracking = integrity_manager.fix_classification_tracking

get_ai_classification_setting = settings_manager.get_ai_classification_setting
set_ai_classification_setting = settings_manager.set_ai_classification_setting 