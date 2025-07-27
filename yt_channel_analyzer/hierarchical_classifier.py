"""
Hierarchical Classification System
Implements HUMAIN > SENTENCE TRANSFORMER > PATTERN priority hierarchy
"""
import sqlite3
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class HierarchicalClassifier:
    """
    Classification system with strict hierarchy enforcement:
    🥇 HUMAIN (Priorité absolue - JAMAIS écrasé)
    🥈 SENTENCE TRANSFORMER (IA sémantique avancée)  
    🥉 PATTERN (Fallback par mots-clés multilingues)
    """
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.semantic_classifier = None
        self.pattern_classifier = None
        
        # Charger les classificateurs
        self._load_classifiers()
    
    def _load_classifiers(self):
        """Charger les classificateurs sémantiques et patterns"""
        try:
            from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier
            self.semantic_classifier = AdvancedSemanticClassifier()
            print("🧠 [HIERARCHY] Classificateur sémantique chargé")
        except Exception as e:
            print(f"⚠️ [HIERARCHY] Erreur chargement semantic: {e}")
        
        try:
            from yt_channel_analyzer.database.classification import classify_video_with_language
            self.pattern_classifier = classify_video_with_language
            print("📝 [HIERARCHY] Classificateur patterns chargé")
        except Exception as e:
            print(f"⚠️ [HIERARCHY] Erreur chargement patterns: {e}")
    
    def get_classification_priority(self, video_id: int = None, playlist_id: int = None) -> Dict[str, Any]:
        """
        Récupérer la classification selon la hiérarchie stricte
        🥇 HUMAIN > 🥈 SEMANTIC > 🥉 PATTERN
        """
        # 🥇 NIVEAU 1: Vérifier HUMAIN d'abord (PRIORITÉ ABSOLUE)
        human_result = self._get_human_classification(video_id, playlist_id)
        if human_result:
            print(f"🥇 [HIERARCHY] Classification HUMAINE trouvée: {human_result['category']}")
            return human_result
        
        # 🥈 NIVEAU 2: Vérifier SEMANTIC 
        semantic_result = self._get_semantic_classification(video_id, playlist_id)
        if semantic_result and semantic_result['confidence'] >= 60:  # Seuil confiance
            print(f"🥈 [HIERARCHY] Classification SEMANTIC: {semantic_result['category']} ({semantic_result['confidence']}%)")
            return semantic_result
        
        # 🥉 NIVEAU 3: Fallback PATTERN
        pattern_result = self._get_pattern_classification(video_id, playlist_id)
        if pattern_result:
            print(f"🥉 [HIERARCHY] Classification PATTERN: {pattern_result['category']}")
            return pattern_result
        
        # Aucune classification trouvée
        return {
            'category': 'uncategorized',
            'source': 'none',
            'confidence': 0,
            'priority_level': 0
        }
    
    def _get_human_classification(self, video_id: int = None, playlist_id: int = None) -> Optional[Dict[str, Any]]:
        """🥇 NIVEAU 1: Récupérer classification HUMAINE (INTOUCHABLE)"""
        if video_id:
            self.cursor.execute('''
                SELECT category, classification_source, is_human_validated, classification_date
                FROM video 
                WHERE id = ? 
                AND (is_human_validated = 1 OR classification_source = 'human')
            ''', (video_id,))
        elif playlist_id:
            self.cursor.execute('''
                SELECT category, classification_source, human_verified, classification_date
                FROM playlist 
                WHERE id = ? 
                AND (human_verified = 1 OR classification_source = 'human')
            ''', (playlist_id,))
        else:
            return None
        
        row = self.cursor.fetchone()
        if row and row[0]:  # category exists
            return {
                'category': row[0],
                'source': 'human',
                'confidence': 100,  # Confiance absolue pour humain
                'priority_level': 1,
                'validated': True,
                'date': row[3]
            }
        return None
    
    def _get_semantic_classification(self, video_id: int = None, playlist_id: int = None) -> Optional[Dict[str, Any]]:
        """🥈 NIVEAU 2: Récupérer/calculer classification SEMANTIC"""
        # Vérifier d'abord si une classification semantic existe déjà
        if video_id:
            self.cursor.execute('''
                SELECT category, classification_confidence, classification_date
                FROM video 
                WHERE id = ? 
                AND classification_source = 'semantic'
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
            ''', (video_id,))
            
            row = self.cursor.fetchone()
            if row and row[0]:
                return {
                    'category': row[0],
                    'source': 'semantic',
                    'confidence': int(row[1] or 0),
                    'priority_level': 2,
                    'date': row[2]
                }
            
            # Si pas de classification semantic, calculer
            self.cursor.execute('SELECT title, description FROM video WHERE id = ?', (video_id,))
            video_data = self.cursor.fetchone()
            if video_data and self.semantic_classifier:
                title, description = video_data
                try:
                    category, confidence, details = self.semantic_classifier.classify_text(title or '', description or '')
                    return {
                        'category': category,
                        'source': 'semantic',
                        'confidence': int(confidence),
                        'priority_level': 2,
                        'details': details
                    }
                except Exception as e:
                    print(f"⚠️ [HIERARCHY] Erreur semantic classification: {e}")
        
        elif playlist_id:
            self.cursor.execute('''
                SELECT category, classification_confidence, classification_date
                FROM playlist 
                WHERE id = ? 
                AND classification_source = 'semantic'
                AND (human_verified = 0 OR human_verified IS NULL)
            ''', (playlist_id,))
            
            row = self.cursor.fetchone()
            if row and row[0]:
                return {
                    'category': row[0],
                    'source': 'semantic', 
                    'confidence': int(row[1] or 0),
                    'priority_level': 2,
                    'date': row[2]
                }
        
        return None
    
    def _get_pattern_classification(self, video_id: int = None, playlist_id: int = None) -> Optional[Dict[str, Any]]:
        """🥉 NIVEAU 3: Récupérer/calculer classification PATTERN"""
        if video_id:
            # Vérifier si pattern existe
            self.cursor.execute('''
                SELECT category, classification_confidence, classification_date
                FROM video 
                WHERE id = ? 
                AND classification_source IN ('keyword', 'auto', 'pattern')
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
            ''', (video_id,))
            
            row = self.cursor.fetchone()
            if row and row[0]:
                return {
                    'category': row[0],
                    'source': 'pattern',
                    'confidence': int(row[1] or 0),
                    'priority_level': 3,
                    'date': row[2]
                }
            
            # Calculer pattern si pas existant
            self.cursor.execute('SELECT title, description FROM video WHERE id = ?', (video_id,))
            video_data = self.cursor.fetchone()
            if video_data and self.pattern_classifier:
                title, description = video_data
                try:
                    category, language, confidence = self.pattern_classifier(title or '', description or '')
                    if confidence > 0:
                        return {
                            'category': category,
                            'source': 'pattern',
                            'confidence': confidence,
                            'priority_level': 3,
                            'language': language
                        }
                except Exception as e:
                    print(f"⚠️ [HIERARCHY] Erreur pattern classification: {e}")
        
        return None
    
    def mark_human_classification(self, video_id: int = None, playlist_id: int = None, 
                                category: str = None, user_notes: str = '') -> bool:
        """
        🥇 MARQUER COMME CLASSIFICATION HUMAINE (PRIORITÉ ABSOLUE - INTOUCHABLE)
        """
        timestamp = datetime.now().isoformat()
        
        try:
            if video_id and category:
                self.cursor.execute('''
                    UPDATE video 
                    SET category = ?,
                        classification_source = 'human',
                        is_human_validated = 1,
                        classification_date = ?,
                        classification_confidence = 100
                    WHERE id = ?
                ''', (category, timestamp, video_id))
                
                print(f"🥇 [HIERARCHY] ✅ Vidéo {video_id} → {category.upper()} (HUMAIN - INTOUCHABLE)")
                
            elif playlist_id and category:
                self.cursor.execute('''
                    UPDATE playlist 
                    SET category = ?,
                        classification_source = 'human',
                        human_verified = 1,
                        is_human_validated = 1,
                        classification_date = ?
                    WHERE id = ?
                ''', (category, timestamp, playlist_id))
                
                print(f"🥇 [HIERARCHY] ✅ Playlist {playlist_id} → {category.upper()} (HUMAIN - INTOUCHABLE)")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ [HIERARCHY] Erreur marking human: {e}")
            return False
    
    def is_human_protected(self, video_id: int = None, playlist_id: int = None) -> bool:
        """Vérifier si l'élément est protégé par classification humaine"""
        human_result = self._get_human_classification(video_id, playlist_id)
        return human_result is not None
    
    def propagate_playlist_to_videos(self, playlist_id: int, force_human_authority: bool = False) -> int:
        """
        Propager la classification playlist vers ses vidéos en respectant la hiérarchie
        """
        # Récupérer la classification de la playlist
        playlist_classification = self.get_classification_priority(playlist_id=playlist_id)
        
        if not playlist_classification or playlist_classification['category'] == 'uncategorized':
            print(f"⚠️ [HIERARCHY] Playlist {playlist_id} non classifiée, pas de propagation")
            return 0
        
        # Récupérer les vidéos de cette playlist
        self.cursor.execute('''
            SELECT DISTINCT v.id 
            FROM video v 
            JOIN playlist_video pv ON v.id = pv.video_id 
            JOIN playlist p ON pv.playlist_id = p.playlist_id
            WHERE p.id = ?
        ''', (playlist_id,))
        
        video_ids = [row[0] for row in self.cursor.fetchall()]
        
        if not video_ids:
            print(f"⚠️ [HIERARCHY] Aucune vidéo liée à la playlist {playlist_id}")
            return 0
        
        videos_updated = 0
        category = playlist_classification['category']
        source_priority = playlist_classification['priority_level']
        
        for video_id in video_ids:
            # Vérifier la protection humaine
            if self.is_human_protected(video_id=video_id):
                print(f"🔒 [HIERARCHY] Vidéo {video_id} protégée par classification HUMAINE - SKIP")
                continue
            
            # Récupérer classification actuelle de la vidéo
            current_classification = self.get_classification_priority(video_id=video_id)
            current_priority = current_classification.get('priority_level', 99)
            
            # Appliquer seulement si priorité supérieure ou égale
            if source_priority <= current_priority or force_human_authority:
                # Déterminer la source de propagation
                if force_human_authority and playlist_classification['source'] == 'human':
                    propagation_source = 'propagated_from_human_playlist'
                    is_human_validated = 1
                else:
                    propagation_source = f"propagated_from_playlist_{playlist_classification['source']}"
                    is_human_validated = 0
                
                self.cursor.execute('''
                    UPDATE video 
                    SET category = ?,
                        classification_source = ?,
                        is_human_validated = ?,
                        classification_date = ?
                    WHERE id = ?
                ''', (category, propagation_source, is_human_validated, datetime.now().isoformat(), video_id))
                
                videos_updated += 1
                print(f"📺 [HIERARCHY] Vidéo {video_id} → {category.upper()} (source: {propagation_source})")
        
        self.conn.commit()
        print(f"✅ [HIERARCHY] Propagation terminée: {videos_updated} vidéos mises à jour")
        return videos_updated
    
    def classify_content_with_hierarchy(self, video_id: int = None, playlist_id: int = None, 
                                      force_reclassify: bool = False) -> Dict[str, Any]:
        """
        Classifier le contenu en respectant la hiérarchie complète
        """
        # Vérifier protection humaine
        if not force_reclassify and self.is_human_protected(video_id, playlist_id):
            human_result = self._get_human_classification(video_id, playlist_id)
            print(f"🔒 [HIERARCHY] Contenu protégé par classification HUMAINE: {human_result['category']}")
            return human_result
        
        # Tenter classification semantic
        semantic_result = self._get_semantic_classification(video_id, playlist_id)
        if semantic_result and semantic_result['confidence'] >= 60:
            # Sauvegarder si nouvelle classification
            self._save_classification(semantic_result, video_id, playlist_id)
            return semantic_result
        
        # Fallback pattern
        pattern_result = self._get_pattern_classification(video_id, playlist_id)
        if pattern_result and pattern_result['confidence'] > 0:
            # Sauvegarder si nouvelle classification
            self._save_classification(pattern_result, video_id, playlist_id)
            return pattern_result
        
        # Aucune classification possible
        return {
            'category': 'uncategorized',
            'source': 'none',
            'confidence': 0,
            'priority_level': 0
        }
    
    def _save_classification(self, classification: Dict[str, Any], video_id: int = None, playlist_id: int = None) -> bool:
        """Sauvegarder une classification en base"""
        try:
            timestamp = datetime.now().isoformat()
            
            if video_id:
                self.cursor.execute('''
                    UPDATE video 
                    SET category = ?,
                        classification_source = ?,
                        classification_confidence = ?,
                        classification_date = ?
                    WHERE id = ?
                    AND (is_human_validated = 0 OR is_human_validated IS NULL)
                ''', (
                    classification['category'],
                    classification['source'],
                    classification['confidence'],
                    timestamp,
                    video_id
                ))
            elif playlist_id:
                self.cursor.execute('''
                    UPDATE playlist 
                    SET category = ?,
                        classification_source = ?,
                        classification_confidence = ?,
                        classification_date = ?
                    WHERE id = ?
                    AND (human_verified = 0 OR human_verified IS NULL)
                ''', (
                    classification['category'],
                    classification['source'],
                    classification['confidence'],
                    timestamp,
                    playlist_id
                ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ [HIERARCHY] Erreur sauvegarde: {e}")
            return False
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques de classification par niveau hiérarchique"""
        stats = {}
        
        # Stats vidéos
        self.cursor.execute('''
            SELECT 
                classification_source,
                COUNT(*) as count,
                COUNT(CASE WHEN is_human_validated = 1 THEN 1 END) as human_validated
            FROM video 
            WHERE category IS NOT NULL AND category != 'uncategorized'
            GROUP BY classification_source
        ''')
        
        video_stats = {}
        for row in self.cursor.fetchall():
            source, count, human_validated = row
            priority = 1 if source == 'human' else (2 if source == 'semantic' else 3)
            video_stats[source] = {
                'count': count,
                'human_validated': human_validated,
                'priority_level': priority
            }
        
        # Stats playlists
        self.cursor.execute('''
            SELECT 
                classification_source,
                COUNT(*) as count,
                COUNT(CASE WHEN human_verified = 1 THEN 1 END) as human_verified
            FROM playlist 
            WHERE category IS NOT NULL AND category != 'uncategorized'
            GROUP BY classification_source
        ''')
        
        playlist_stats = {}
        for row in self.cursor.fetchall():
            source, count, human_verified = row
            priority = 1 if source == 'human' else (2 if source == 'semantic' else 3)
            playlist_stats[source] = {
                'count': count,
                'human_verified': human_verified,
                'priority_level': priority
            }
        
        return {
            'videos': video_stats,
            'playlists': playlist_stats,
            'hierarchy_levels': {
                1: 'HUMAIN (Intouchable)',
                2: 'SEMANTIC (IA Avancée)', 
                3: 'PATTERN (Fallback)'
            }
        }