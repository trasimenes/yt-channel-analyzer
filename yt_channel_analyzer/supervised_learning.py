"""
Module d'apprentissage supervisé pour la classification Hero/Hub/Help
Permet d'améliorer la classification en apprenant des corrections de l'utilisateur
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

from .database.base import get_db_connection
from .database.classification import get_classification_patterns, add_classification_pattern, classify_video_with_language
from .database.videos import mark_human_classification


def create_feedback_tables():
    """Crée les tables nécessaires pour le système de feedback et d'apprentissage"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Table pour stocker les feedbacks utilisateur
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id INTEGER PRIMARY KEY,
                video_id INTEGER,
                original_category VARCHAR(10),
                corrected_category VARCHAR(10),
                confidence_score FLOAT,
                user_feedback_type VARCHAR(20), -- 'correction', 'validation', 'uncertain'
                feedback_timestamp DATETIME,
                user_notes TEXT,
                FOREIGN KEY(video_id) REFERENCES video(id)
            )
        ''')
        
        # Table pour stocker les patterns appris automatiquement
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY,
                pattern TEXT,
                category VARCHAR(10),
                language VARCHAR(5),
                confidence_weight FLOAT,
                learned_from_feedback_count INTEGER,
                last_reinforced DATETIME
            )
        ''')
        
        # Table pour stocker les métriques de performance du modèle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY,
                date DATE,
                total_classifications INTEGER,
                correct_predictions INTEGER,
                accuracy_rate FLOAT,
                confidence_distribution TEXT, -- JSON
                category_performance TEXT -- JSON
            )
        ''')
        
        conn.commit()
        print("[SUPERVISED] ✅ Tables de feedback et d'apprentissage créées avec succès")
        
    except Exception as e:
        conn.rollback()
        print(f"[SUPERVISED] ❌ Erreur lors de la création des tables: {e}")
        raise
    finally:
        conn.close()

def add_user_feedback(video_id: int, original_category: str, corrected_category: str, 
                     confidence_score: float, user_feedback_type: str = 'correction',
                     user_notes: str = '') -> bool:
    """
    Ajoute un feedback utilisateur pour une classification
    
    Args:
        video_id: ID de la vidéo dans la base de données
        original_category: Catégorie originale proposée par le système
        corrected_category: Catégorie corrigée par l'utilisateur
        confidence_score: Score de confiance original
        user_feedback_type: Type de feedback ('correction', 'validation', 'uncertain')
        user_notes: Notes additionnelles de l'utilisateur
        
    Returns:
        bool: True si le feedback a été ajouté avec succès
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO classification_feedback (
                video_id, original_category, corrected_category,
                confidence_score, user_feedback_type, feedback_timestamp, user_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_id, original_category, corrected_category,
            confidence_score, user_feedback_type, datetime.now(), user_notes
        ))
        
        conn.commit()
        
        # Déclencher l'apprentissage après chaque feedback
        learn_from_feedback(video_id, original_category, corrected_category)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"[SUPERVISED] ❌ Erreur lors de l'ajout du feedback: {e}")
        return False
    finally:
        conn.close()

def add_playlist_feedback(playlist_id: int, category: str, feedback_type: str = 'correction', user_notes: str = '') -> Dict:
    """
    Ajoute un feedback utilisateur pour une playlist et apprend de nouveaux patterns
    
    Args:
        playlist_id: ID de la playlist
        category: Catégorie corrigée (hero, hub, help)
        feedback_type: Type de feedback (correction, validation, uncertain)
        user_notes: Notes de l'utilisateur
        
    Returns:
        Dict: Résultat avec les patterns appris
    """
    print(f"[SUPERVISED] 📋 Feedback playlist ID {playlist_id}: {category} ({feedback_type})")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Récupérer les informations de la playlist
        cursor.execute('''
            SELECT name, description, category, concurrent_id
            FROM playlist 
            WHERE id = ?
        ''', (playlist_id,))
        
        result = cursor.fetchone()
        if not result:
            return {'status': 'error', 'message': 'Playlist non trouvée'}
        
        playlist_name, description, original_category, concurrent_id = result
        original_category = original_category or 'hub'  # Valeur par défaut
        
        # 2. 🚨 MARQUER LA PLAYLIST COMME CLASSIFIÉE PAR UN HUMAIN (PRIORITÉ ABSOLUE)
        # from yt_channel_analyzer.database import mark_human_classification
        
        success = mark_human_classification(
            playlist_id=playlist_id,
            category=category,
            user_notes=f"Feedback supervisé: {feedback_type} - {user_notes}"
        )
        
        if not success:
            return {'status': 'error', 'message': 'Erreur lors du marquage de la classification humaine'}
        
        # 3. Extraire des patterns d'apprentissage depuis le nom et la description
        text_combined = f"{playlist_name} {description or ''}"
        from .database.base import detect_language
        detected_language = detect_language(text_combined)
        
        patterns_saved = extract_learning_patterns(text_combined, category, detected_language)
        
        # 4. Enregistrer les patterns appris
        patterns_count = 0
        for pattern, weight in patterns_saved:
            # Vérifier si le pattern existe déjà
            cursor.execute('''
                SELECT id, confidence_weight, learned_from_feedback_count
                FROM learned_patterns
                WHERE pattern = ? AND category = ? AND language = ?
            ''', (pattern, category, detected_language))
            
            existing = cursor.fetchone()
            
            if existing:
                # Renforcer le pattern existant
                new_weight = existing[1] + weight
                new_count = existing[2] + 1
                
                cursor.execute('''
                    UPDATE learned_patterns 
                    SET confidence_weight = ?, 
                        learned_from_feedback_count = ?,
                        last_reinforced = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_weight, new_count, existing[0]))
                
                print(f"[SUPERVISED] 📋 Pattern renforcé: '{pattern}' → {category.upper()} (poids: {new_weight})")
            else:
                # Nouveau pattern
                cursor.execute('''
                    INSERT INTO learned_patterns 
                    (pattern, category, language, confidence_weight, learned_from_feedback_count, last_reinforced)
                    VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ''', (pattern, category, detected_language, weight))
                
                patterns_count += 1
                print(f"[SUPERVISED] 📋 Nouveau pattern appris: '{pattern}' → {category.upper()} (poids: {weight})")
        
        # 5. Si c'est une correction, propager automatiquement aux vidéos de cette playlist
        if feedback_type == 'correction' and category != original_category:
            from yt_channel_analyzer.database.classification import apply_playlist_categories_to_videos_safe
            
            propagation_result = apply_playlist_categories_to_videos_safe(
                competitor_id=None, 
                specific_playlist_id=playlist_id,
                force_human_playlists=True # Forcer car c'est une action humaine directe
            )
            
            print(f"[SUPERVISED] 📋 Propagation aux vidéos: {propagation_result.get('videos_updated', 0)} vidéos mises à jour")
        
        conn.commit()
        
        return {
            'status': 'success',
            'message': f'Feedback playlist enregistré et {patterns_count} nouveaux patterns appris',
            'patterns_saved': [pattern for pattern, weight in patterns_saved],
            'learning_result': {
                'patterns_saved': [pattern for pattern, weight in patterns_saved],
                'patterns_count': patterns_count,
                'language': detected_language
            }
        }
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur feedback playlist: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()

def learn_from_feedback(video_id: int, original_category: str, corrected_category: str) -> Dict:
    """
    Apprend à partir d'un feedback utilisateur en:
    1. Extrayant de nouveaux patterns potentiels
    2. Renforçant les patterns existants
    3. Créant une règle personnalisée si nécessaire
    
    Args:
        video_id: ID de la vidéo dans la base de données
        original_category: Catégorie originale proposée par le système
        corrected_category: Catégorie corrigée par l'utilisateur
        
    Returns:
        Dict: Résultat de l'apprentissage avec les patterns identifiés
    """
    # Ignorer si la correction correspond à la prédiction originale
    if original_category == corrected_category:
        return {'status': 'ignored', 'reason': 'no correction needed'}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer les détails de la vidéo
        cursor.execute('''
            SELECT title, description FROM video WHERE id = ?
        ''', (video_id,))
        
        video_data = cursor.fetchone()
        if not video_data:
            return {'status': 'error', 'reason': 'video not found'}
            
        title, description = video_data
        text_to_analyze = f"{title} {description or ''}"
        
        # Détecter la langue
        from .database.base import detect_language
        detected_language = detect_language(text_to_analyze)
        
        # Extraire des patterns potentiels
        patterns = extract_learning_patterns(text_to_analyze, corrected_category, detected_language)
        
        # Enregistrer les patterns appris
        saved_patterns = []
        for pattern, weight in patterns:
            cursor.execute('''
                INSERT OR IGNORE INTO learned_patterns (
                    pattern, category, language, confidence_weight, 
                    learned_from_feedback_count, last_reinforced
                ) VALUES (?, ?, ?, ?, 1, ?)
            ''', (pattern, corrected_category, detected_language, weight, datetime.now()))
            
            if cursor.rowcount > 0:
                saved_patterns.append(pattern)
            else:
                # Si le pattern existe déjà, renforcer son poids
                cursor.execute('''
                    UPDATE learned_patterns 
                    SET confidence_weight = confidence_weight + ?,
                        learned_from_feedback_count = learned_from_feedback_count + 1,
                        last_reinforced = ?
                    WHERE pattern = ? AND category = ? AND language = ?
                ''', (weight * 0.5, datetime.now(), pattern, corrected_category, detected_language))
            
        # Si un pattern a un poids très élevé, l'ajouter comme règle personnalisée
        # NOTE: list_custom_rules et add_custom_rule ne semblent pas utilisés ici, je les omets.
        # cursor.execute('''
        #     SELECT pattern, confidence_weight, learned_from_feedback_count
        #     FROM learned_patterns
        #     WHERE category = ? AND language = ? AND confidence_weight > 5.0
        # ''', (corrected_category, detected_language))
        
        # strong_patterns = cursor.fetchall()
        # added_rules = []
        
        # for pattern, weight, count in strong_patterns:
        #     # Vérifier si c'est déjà une règle personnalisée
        #     existing_rules = list_custom_rules(detected_language)
        #     if not any(rule['pattern'] == pattern and rule['category'] == corrected_category 
        #              for rule in existing_rules):
        #         # Ajouter comme règle personnalisée
        #         add_custom_rule(pattern, corrected_category, detected_language)
        #         added_rules.append(pattern)
                
        #         # Mettre à jour les patterns standards aussi
        #         add_classification_pattern(corrected_category, pattern, detected_language)
        
        conn.commit()
        
        # Mettre à jour les métriques de performance
        update_model_performance()
        
        return {
            'status': 'success',
            'language': detected_language,
            'patterns_extracted': len(patterns),
            'patterns_saved': saved_patterns,
            'rules_added': [] # No rules added in this simplified version
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[SUPERVISED] ❌ Erreur lors de l'apprentissage: {e}")
        return {'status': 'error', 'reason': str(e)}
    finally:
        conn.close()

def extract_learning_patterns(text: str, category: str, language: str) -> List[Tuple[str, float]]:
    """
    Extrait des patterns pertinents à partir du texte pour l'apprentissage
    
    Args:
        text: Texte à analyser (titre + description)
        category: Catégorie à laquelle le pattern devrait correspondre
        language: Langue détectée
        
    Returns:
        List[Tuple[str, float]]: Liste de tuples (pattern, poids)
    """
    text = text.lower()
    patterns = []
    
    # 1. Extraire des phrases courtes (2-3 mots consécutifs)
    words = re.findall(r'\b\w+\b', text)
    for n in range(2, 4):  # Phrases de 2 à 3 mots
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) > 5:  # Ignorer les phrases trop courtes
                patterns.append((phrase, 1.0))
    
    # 2. Identifier les mots-clés pertinents (spécifiques à chaque catégorie)
    if category == 'hero':
        keywords = ['new', 'launch', 'exclusive', 'premier', 'announce', 'reveal', 'big', 'special']
        if language == 'fr':
            keywords.extend(['nouveau', 'lancement', 'exclusif', 'première', 'annonce', 'révélation', 'grand', 'spécial'])
    elif category == 'help':
        keywords = ['how', 'guide', 'tutorial', 'solve', 'fix', 'problem', 'help', 'tip', 'advice']
        if language == 'fr':
            keywords.extend(['comment', 'guide', 'tutoriel', 'résoudre', 'réparer', 'problème', 'aide', 'astuce', 'conseil'])
    else:  # hub
        keywords = ['episode', 'series', 'weekly', 'discover', 'explore', 'tour', 'visit', 'experience']
        if language == 'fr':
            keywords.extend(['épisode', 'série', 'hebdomadaire', 'découvrir', 'explorer', 'tour', 'visite', 'expérience'])
    
    # Ajouter les mots-clés trouvés dans le texte
    for keyword in keywords:
        if keyword in text:
            # Donner un poids plus élevé aux mots-clés catégoriels
            patterns.append((keyword, 2.0))
            
            # Extraire des contextes autour de ces mots-clés (5 mots avant/après)
            matches = re.finditer(r'\b' + re.escape(keyword) + r'\b', text)
            for match in matches:
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                # Extraire une phrase contenant le mot-clé
                sentence = re.search(r'[^.!?]*\b' + re.escape(keyword) + r'\b[^.!?]*', context)
                if sentence and 5 < len(sentence.group()) < 50:
                    patterns.append((sentence.group().strip(), 1.5))
    
    # 3. Si le titre commence par un mot-clé, c'est un fort indicateur
    for keyword in keywords:
        if text.startswith(keyword):
            patterns.append((keyword, 3.0))  # Poids plus élevé
    
    # Dédupliquer et normaliser
    unique_patterns = {}
    for pattern, weight in patterns:
        pattern = pattern.strip()
        if pattern in unique_patterns:
            unique_patterns[pattern] = max(unique_patterns[pattern], weight)
        else:
            unique_patterns[pattern] = weight
    
    return list(unique_patterns.items())

def update_model_performance():
    """Met à jour les métriques de performance du modèle d'apprentissage"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculer les métriques de base
        cursor.execute('''
            SELECT COUNT(*) FROM classification_feedback
        ''')
        total_feedbacks = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM classification_feedback
            WHERE original_category = corrected_category
        ''')
        correct_predictions = cursor.fetchone()[0]
        
        accuracy_rate = correct_predictions / total_feedbacks if total_feedbacks > 0 else 0
        
        # Distribution des scores de confiance
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN confidence_score < 60 THEN 'low'
                    WHEN confidence_score < 80 THEN 'medium'
                    ELSE 'high'
                END as confidence_level,
                COUNT(*) as count,
                SUM(CASE WHEN original_category = corrected_category THEN 1 ELSE 0 END) as correct
            FROM classification_feedback
            GROUP BY confidence_level
        ''')
        
        confidence_distribution = {}
        for row in cursor.fetchall():
            level, count, correct = row
            confidence_distribution[level] = {
                'count': count,
                'correct': correct,
                'accuracy': correct / count if count > 0 else 0
            }
        
        # Performance par catégorie
        cursor.execute('''
            SELECT 
                original_category,
                COUNT(*) as count,
                SUM(CASE WHEN original_category = corrected_category THEN 1 ELSE 0 END) as correct
            FROM classification_feedback
            GROUP BY original_category
        ''')
        
        category_performance = {}
        for row in cursor.fetchall():
            category, count, correct = row
            category_performance[category] = {
                'count': count,
                'correct': correct,
                'accuracy': correct / count if count > 0 else 0
            }
        
        # Sauvegarder les métriques
        cursor.execute('''
            INSERT INTO model_performance (
                date, total_classifications, correct_predictions,
                accuracy_rate, confidence_distribution, category_performance
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().date(), total_feedbacks, correct_predictions,
            accuracy_rate, json.dumps(confidence_distribution), json.dumps(category_performance)
        ))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"[SUPERVISED] ❌ Erreur lors de la mise à jour des métriques: {e}")
    finally:
        conn.close()

def get_model_performance() -> Dict:
    """Récupère les dernières métriques de performance du modèle"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM model_performance
            ORDER BY date DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        if not row:
            return {
                'status': 'no_data',
                'message': 'Aucune donnée de performance disponible'
            }
            
        performance = dict(row)
        
        # Convertir les JSON en objets Python
        performance['confidence_distribution'] = json.loads(performance['confidence_distribution'])
        performance['category_performance'] = json.loads(performance['category_performance'])
        
        # Ajouter des métriques d'évolution
        cursor.execute('''
            SELECT accuracy_rate FROM model_performance
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 1
        ''', (performance['date'],))
        
        prev_row = cursor.fetchone()
        if prev_row:
            prev_accuracy = prev_row[0]
            performance['accuracy_change'] = performance['accuracy_rate'] - prev_accuracy
        
        return performance
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la récupération des métriques: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()

def get_videos_for_validation(limit: int = 50, offset: int = 0, strategy: str = 'global_top') -> List[Dict]:
    """
    Récupère les vidéos à valider selon la stratégie choisie
    
    Args:
        limit: Nombre maximum de vidéos à retourner
        offset: Décalage pour la pagination
        strategy: Stratégie de priorisation
            - 'global_top': Top vidéos globales par vues/likes/commentaires
            - 'competitor_top': Top vidéos par concurrent
            - 'low_confidence': Vidéos avec confiance faible
            - 'balanced': Combinaison des stratégies
            
    Returns:
        List[Dict]: Liste des vidéos à valider avec leurs métadonnées
    """
    print(f"[SUPERVISED] 🔍 get_videos_for_validation appelée avec limit={limit}, offset={offset}, strategy={strategy}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Debug: vérifier les tables existantes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"[SUPERVISED] 📊 Tables disponibles: {tables}")
    
    # Debug: vérifier le nombre de vidéos total
    try:
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        print(f"[SUPERVISED] 📈 Total vidéos dans la base: {total_videos}")
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur comptage vidéos: {e}")
        return []
    
    # Debug: vérifier le nombre de concurrents
    try:
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        total_competitors = cursor.fetchone()[0]
        print(f"[SUPERVISED] 🏢 Total concurrents: {total_competitors}")
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur comptage concurrents: {e}")
        return []
    
    videos = []
    
    try:
        if strategy == 'global_top':
            # Top vidéos globales par vues/likes/commentaires
            print(f"[SUPERVISED] 🎯 Stratégie: {strategy}")
            cursor.execute('''
                SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count, 
                       v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                       CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                WHERE v.view_count > 0
                GROUP BY v.id
                HAVING has_feedback = 0
                ORDER BY v.view_count DESC, v.like_count DESC, v.comment_count DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            videos = [dict(row) for row in cursor.fetchall()]
            print(f"[SUPERVISED] ✅ Vidéos trouvées avec strategy {strategy}: {len(videos)}")
            
        elif strategy == 'competitor_top':
            # Top vidéos par concurrent
            cursor.execute('''
                WITH top_competitors AS (
                    SELECT c.id, c.name
                    FROM concurrent c
                    JOIN video v ON c.id = v.concurrent_id
                    GROUP BY c.id
                    ORDER BY SUM(v.view_count) DESC
                    LIMIT 20
                ),
                top_videos AS (
                    SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count,
                           v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                           CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback,
                           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY v.view_count DESC) as rank
                    FROM video v
                    JOIN concurrent c ON v.concurrent_id = c.id
                    JOIN top_competitors tc ON c.id = tc.id
                    LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                    WHERE v.view_count > 0
                )
                SELECT id, title, video_id, view_count, like_count, comment_count,
                       category, thumbnail_url, competitor_name, competitor_id, has_feedback
                FROM top_videos
                WHERE rank <= 10 AND has_feedback = 0
                ORDER BY competitor_id, rank
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
        elif strategy == 'low_confidence':
            # Vidéos avec une faible confiance de classification
            # Pour simuler cela sans colonne de confiance, on utilise un ratio likes/vues inhabituel
            cursor.execute('''
                SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count, 
                       v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                       CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback,
                       ABS((v.like_count * 1.0 / NULLIF(v.view_count, 0)) - 0.01) as confidence_proxy
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                WHERE v.view_count > 1000
                GROUP BY v.id
                HAVING has_feedback = 0
                ORDER BY confidence_proxy ASC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
        else:  # balanced
            # Pour la stratégie balanced, on récupère plus de données pour pouvoir appliquer l'offset
            total_needed = limit + offset
            per_strategy = total_needed // 3
            
            # 1. Top global
            cursor.execute('''
                SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count, 
                       v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                       CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback,
                       'global_top' as source
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                WHERE v.view_count > 0
                GROUP BY v.id
                HAVING has_feedback = 0
                ORDER BY v.view_count DESC
                LIMIT ?
            ''', (per_strategy,))
            
            videos.extend([dict(row) for row in cursor.fetchall()])
            
            # 2. Top par concurrent
            cursor.execute('''
                WITH top_competitors AS (
                    SELECT c.id
                    FROM concurrent c
                    JOIN video v ON c.id = v.concurrent_id
                    GROUP BY c.id
                    ORDER BY SUM(v.view_count) DESC
                    LIMIT 10
                ),
                top_videos AS (
                    SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count,
                           v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                           CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback,
                           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY v.view_count DESC) as rank,
                           'competitor_top' as source
                    FROM video v
                    JOIN concurrent c ON v.concurrent_id = c.id
                    JOIN top_competitors tc ON c.id = tc.id
                    LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                    WHERE v.view_count > 0
                )
                SELECT id, title, video_id, view_count, like_count, comment_count,
                       category, thumbnail_url, competitor_name, competitor_id, has_feedback, source
                FROM top_videos
                WHERE rank <= 5 AND has_feedback = 0
                ORDER BY competitor_id, rank
                LIMIT ?
            ''', (per_strategy,))
            
            videos.extend([dict(row) for row in cursor.fetchall()])
            
            # 3. Confiance faible (simulée)
            cursor.execute('''
                SELECT v.id, v.title, v.video_id, v.view_count, v.like_count, v.comment_count, 
                       v.category, v.thumbnail_url, c.name as competitor_name, c.id as competitor_id,
                       CASE WHEN cf.id IS NULL THEN 0 ELSE 1 END as has_feedback,
                       'low_confidence' as source,
                       ABS((v.like_count * 1.0 / NULLIF(v.view_count, 0)) - 0.01) as confidence_proxy
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                LEFT JOIN classification_feedback cf ON v.id = cf.video_id
                WHERE v.view_count > 1000
                GROUP BY v.id
                HAVING has_feedback = 0
                ORDER BY confidence_proxy ASC
                LIMIT ?
            ''', (per_strategy,))
            
            videos.extend([dict(row) for row in cursor.fetchall()])
            
            # Mélanger pour éviter les biais
            import random
            random.shuffle(videos)
            
            # Appliquer l'offset et la limite
            videos = videos[offset:offset + limit]
            
            # Retourner directement pour éviter la boucle ci-dessous
            return videos
        
        # Pour les stratégies non-balanced
        if strategy != 'balanced':
            videos = [dict(row) for row in cursor.fetchall()]
        
        return videos
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la récupération des vidéos à valider: {e}")
        return []
    finally:
        conn.close()

def get_playlists_for_validation(limit: int = 20, offset: int = 0, strategy: str = 'global_top') -> List[Dict]:
    """
    Récupère les playlists à valider selon la stratégie choisie
    
    Args:
        limit: Nombre maximum de playlists à retourner
        offset: Décalage pour la pagination
        strategy: Stratégie de priorisation
            - 'global_top': Top playlists globales par nombre de vidéos/vues
            - 'competitor_top': Top playlists par concurrent
            - 'low_confidence': Playlists non catégorisées ou avec confiance faible
            - 'balanced': Combinaison des stratégies
            
    Returns:
        List[Dict]: Liste des playlists à valider avec leurs métadonnées
    """
    print(f"[SUPERVISED] 🔍 get_playlists_for_validation appelée avec limit={limit}, offset={offset}, strategy={strategy}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier si la table playlist existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlist'")
    if not cursor.fetchone():
        print(f"[SUPERVISED] ⚠️ Table playlist non trouvée")
        return []
    
    # Vérifier le nombre total de playlists
    try:
        cursor.execute("SELECT COUNT(*) FROM playlist")
        total_playlists = cursor.fetchone()[0]
        print(f"[SUPERVISED] 📈 Total playlists dans la base: {total_playlists}")
        
        if total_playlists == 0:
            return []
            
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur comptage playlists: {e}")
        return []
    
    playlists = []
    
    try:
        if strategy == 'global_top':
            # Top playlists globales par nombre de vidéos et vues totales
            print(f"[SUPERVISED] 🎯 Stratégie playlists: {strategy}")
            cursor.execute('''
                SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                       p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                       COALESCE(p.classification_source, 'unknown') as source,
                       COALESCE(p.classification_confidence, 0) as confidence,
                       CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE p.video_count > 0
                AND p.human_verified != 1  -- Exclure les playlists déjà validées par un humain
                ORDER BY p.video_count DESC, p.name ASC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            playlists = [dict(row) for row in cursor.fetchall()]
            print(f"[SUPERVISED] ✅ Playlists trouvées avec strategy {strategy}: {len(playlists)}")
            
            # Retourner directement pour éviter la double exécution cursor.fetchall()
            return playlists
            
        elif strategy == 'competitor_top':
            # Top playlists par concurrent (les plus importantes de chaque concurrent)
            cursor.execute('''
                WITH ranked_playlists AS (
                    SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                           p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                           COALESCE(p.classification_source, 'unknown') as source,
                           COALESCE(p.classification_confidence, 0) as confidence,
                           CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated,
                           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY p.video_count DESC) as rank
                    FROM playlist p
                    JOIN concurrent c ON p.concurrent_id = c.id
                    WHERE p.video_count > 0
                    AND p.human_verified != 1
                )
                SELECT id, name, description, video_count, thumbnail_url,
                       category, playlist_id, competitor_name, competitor_id,
                       source, confidence, is_human_validated
                FROM ranked_playlists
                WHERE rank <= 3  -- Top 3 par concurrent
                ORDER BY competitor_id, rank
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            playlists = [dict(row) for row in cursor.fetchall()]
            return playlists
            
        elif strategy == 'low_confidence':
            # Playlists non catégorisées ou avec une confiance faible
            cursor.execute('''
                SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                       p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                       COALESCE(p.classification_source, 'unknown') as source,
                       COALESCE(p.classification_confidence, 0) as confidence,
                       CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE p.video_count > 0
                AND p.human_verified != 1
                AND (p.category IS NULL OR p.category = '' OR p.classification_confidence < 70)
                ORDER BY p.classification_confidence ASC, p.video_count DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            playlists = [dict(row) for row in cursor.fetchall()]
            return playlists
            
        else:  # balanced
            # Pour la stratégie balanced, on récupère plus de données pour pouvoir appliquer l'offset
            total_needed = limit + offset
            per_strategy = total_needed // 3
            
            # 1. Top global (playlists avec le plus de vidéos)
            cursor.execute('''
                SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                       p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                       COALESCE(p.classification_source, 'unknown') as source,
                       COALESCE(p.classification_confidence, 0) as confidence,
                       CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated,
                       'global_top' as validation_source
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE p.video_count > 0
                AND p.human_verified != 1
                ORDER BY p.video_count DESC
                LIMIT ?
            ''', (per_strategy,))
            
            playlists.extend([dict(row) for row in cursor.fetchall()])
            
            # 2. Top par concurrent
            cursor.execute('''
                WITH ranked_playlists AS (
                    SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                           p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                           COALESCE(p.classification_source, 'unknown') as source,
                           COALESCE(p.classification_confidence, 0) as confidence,
                           CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated,
                           'competitor_top' as validation_source,
                           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY p.video_count DESC) as rank
                    FROM playlist p
                    JOIN concurrent c ON p.concurrent_id = c.id
                    WHERE p.video_count > 0
                    AND p.human_verified != 1
                )
                SELECT id, name, description, video_count, thumbnail_url,
                       category, playlist_id, competitor_name, competitor_id,
                       source, confidence, is_human_validated, validation_source
                FROM ranked_playlists
                WHERE rank <= 2
                ORDER BY competitor_id, rank
                LIMIT ?
            ''', (per_strategy,))
            
            playlists.extend([dict(row) for row in cursor.fetchall()])
            
            # 3. Confiance faible (non catégorisées)
            cursor.execute('''
                SELECT p.id, p.name, p.description, p.video_count, p.thumbnail_url,
                       p.category, p.playlist_id, c.name as competitor_name, c.id as competitor_id,
                       COALESCE(p.classification_source, 'unknown') as source,
                       COALESCE(p.classification_confidence, 0) as confidence,
                       CASE WHEN p.human_verified = 1 THEN 1 ELSE 0 END as is_human_validated,
                       'low_confidence' as validation_source
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE p.video_count > 0
                AND p.human_verified != 1
                AND (p.category IS NULL OR p.category = '')
                ORDER BY p.video_count DESC
                LIMIT ?
            ''', (per_strategy,))
            
            playlists.extend([dict(row) for row in cursor.fetchall()])
            
            # Mélanger pour éviter les biais
            import random
            random.shuffle(playlists)
            
            # Appliquer l'offset et la limite
            playlists = playlists[offset:offset + limit]
            
            # Retourner directement pour éviter la boucle ci-dessous
            return playlists
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la récupération des playlists à valider: {e}")
        return []
    finally:
        conn.close()

def classify_with_supervised_learning(title: str, description: str = "") -> Tuple[str, str, int]:
    """
    Classifie une vidéo en utilisant l'apprentissage supervisé
    Ajoute les patterns appris au processus de classification standard
    
    Args:
        title: Titre de la vidéo
        description: Description de la vidéo
        
    Returns:
        Tuple[str, str, int]: (catégorie, langue, confiance)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Utiliser d'abord la méthode standard
        category, detected_language, confidence = classify_video_with_language(title, description)
        
        # 2. Vérifier les patterns appris
        text_lower = f"{title} {description}".lower()
        
        cursor.execute('''
            SELECT pattern, category, confidence_weight
            FROM learned_patterns
            WHERE language = ?
            ORDER BY confidence_weight DESC
        ''', (detected_language,))
        
        learned_patterns = cursor.fetchall()
        
        # Si aucun pattern appris, retourner la classification standard
        if not learned_patterns:
            return category, detected_language, confidence
            
        # 3. Appliquer les patterns appris et recalculer le score
        hero_score = 0.0
        hub_score = 0.0 
        help_score = 0.0
        
        for pattern, learned_category, weight in learned_patterns:
            if pattern in text_lower:
                if learned_category == 'hero':
                    hero_score += weight
                elif learned_category == 'hub':
                    hub_score += weight
                elif learned_category == 'help':
                    help_score += weight
        
        # Si aucun pattern appris ne correspond, retourner la classification standard
        if hero_score == 0 and hub_score == 0 and help_score == 0:
            return category, detected_language, confidence
            
        # 4. Combiner avec le score de confiance original (pondération 70/30)
        original_scores = {
            'hero': 0.0,
            'hub': 0.0,
            'help': 0.0
        }
        original_scores[category] = confidence / 100.0
        
        # Normaliser les scores appris
        learned_sum = hero_score + hub_score + help_score
        if learned_sum > 0:
            learned_scores = {
                'hero': hero_score / learned_sum,
                'hub': hub_score / learned_sum,
                'help': help_score / learned_sum
            }
            
            # Combiner les scores (70% original, 30% appris)
            combined_scores = {
                cat: original_scores[cat] * 0.7 + learned_scores[cat] * 0.3
                for cat in ['hero', 'hub', 'help']
            }
            
            # Déterminer la nouvelle catégorie
            new_category = max(combined_scores.keys(), key=lambda k: combined_scores[k])
            new_confidence = int(combined_scores[new_category] * 100)
            
            if new_category != category:
                print(f"[SUPERVISED] 🔄 Classification modifiée: {category.upper()} → {new_category.upper()} (confiance: {new_confidence}%)")
            else:
                print(f"[SUPERVISED] ✅ Classification confirmée: {category.upper()} (confiance: {new_confidence}%)")
                
            return new_category, detected_language, new_confidence
            
        return category, detected_language, confidence
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la classification supervisée: {e}")
        # Fallback vers la classification standard
        return classify_video_with_language(title, description)
    finally:
        conn.close()

def get_feedback_history(video_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
    """
    Récupère l'historique des feedbacks utilisateur
    
    Args:
        video_id: ID de la vidéo (optionnel, si None retourne tous les feedbacks)
        limit: Nombre maximum de feedbacks à retourner
        
    Returns:
        List[Dict]: Liste des feedbacks
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if video_id:
            cursor.execute('''
                SELECT cf.*, v.title, v.video_id as youtube_id, c.name as competitor_name
                FROM classification_feedback cf
                JOIN video v ON cf.video_id = v.id
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE cf.video_id = ?
                ORDER BY cf.feedback_timestamp DESC
                LIMIT ?
            ''', (video_id, limit))
        else:
            cursor.execute('''
                SELECT cf.*, v.title, v.video_id as youtube_id, c.name as competitor_name
                FROM classification_feedback cf
                JOIN video v ON cf.video_id = v.id
                JOIN concurrent c ON v.concurrent_id = c.id
                ORDER BY cf.feedback_timestamp DESC
                LIMIT ?
            ''', (limit,))
            
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la récupération de l'historique: {e}")
        return []
    finally:
        conn.close()

def get_learning_statistics() -> Dict:
    """
    Récupère les statistiques d'apprentissage
    
    Returns:
        Dict: Statistiques d'apprentissage
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Nombre total de feedbacks
        cursor.execute('SELECT COUNT(*) FROM classification_feedback')
        total_feedbacks = cursor.fetchone()[0]
        
        # Nombre de corrections vs validations
        cursor.execute('''
            SELECT user_feedback_type, COUNT(*) 
            FROM classification_feedback 
            GROUP BY user_feedback_type
        ''')
        feedback_types = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Nombre de patterns appris
        cursor.execute('SELECT COUNT(*) FROM learned_patterns')
        total_learned_patterns = cursor.fetchone()[0]
        
        # Patterns par langue
        cursor.execute('''
            SELECT language, COUNT(*) 
            FROM learned_patterns 
            GROUP BY language
        ''')
        patterns_by_language = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Patterns par catégorie
        cursor.execute('''
            SELECT category, COUNT(*) 
            FROM learned_patterns 
            GROUP BY category
        ''')
        patterns_by_category = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Top patterns (les plus renforcés)
        cursor.execute('''
            SELECT pattern, category, language, confidence_weight, learned_from_feedback_count
            FROM learned_patterns
            ORDER BY learned_from_feedback_count DESC, confidence_weight DESC
            LIMIT 10
        ''')
        top_patterns = [dict(row) for row in cursor.fetchall()]
        
        # Evolution de la précision
        cursor.execute('''
            SELECT date, accuracy_rate
            FROM model_performance
            ORDER BY date
            LIMIT 10
        ''')
        accuracy_evolution = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_feedbacks': total_feedbacks,
            'feedback_types': feedback_types,
            'total_learned_patterns': total_learned_patterns,
            'patterns_by_language': patterns_by_language,
            'patterns_by_category': patterns_by_category,
            'top_patterns': top_patterns,
            'accuracy_evolution': accuracy_evolution,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de la récupération des statistiques: {e}")
        return {'error': str(e)}
    finally:
        conn.close()

def get_human_classifications(limit: int = 100, offset: int = 0) -> Dict:
    """
    Récupère les vidéos ET playlists reclassifiées par l'humain avec comparaison IA vs Humain
    
    Args:
        limit: Nombre maximum d'éléments à retourner
        offset: Décalage pour la pagination
        
    Returns:
        Dict: Dictionnaire contenant les vidéos, playlists reclassifiées et les statistiques
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. RÉCUPÉRER LES VIDÉOS RECLASSIFIÉES (via table classification_feedback)
        cursor.execute('''
            SELECT 
                'video' as type,
                v.id,
                v.title as name,
                v.video_id,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.thumbnail_url,
                c.name as competitor_name,
                c.id as competitor_id,
                cf.original_category as ia_classification,
                cf.corrected_category as human_classification,
                cf.confidence_score,
                cf.feedback_timestamp,
                cf.user_feedback_type,
                cf.user_notes,
                null as video_count_field
            FROM classification_feedback cf
            JOIN video v ON cf.video_id = v.id
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE cf.user_feedback_type = 'correction'
            ORDER BY cf.feedback_timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit // 2, offset // 2))  # Diviser pour faire de la place aux playlists
        
        video_classifications_direct = []
        for row in cursor.fetchall():
            # Formater le timestamp pour l'affichage
            feedback_timestamp = row[13]
            if feedback_timestamp:
                try:
                    from datetime import datetime
                    if isinstance(feedback_timestamp, str):
                        dt = datetime.strptime(feedback_timestamp, '%Y-%m-%d %H:%M:%S')
                        feedback_timestamp = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
            
            video_classifications_direct.append({
                'type': 'video',
                'id': row[1],
                'name': row[2],
                'title': row[2],  # Alias pour compatibilité
                'video_id': row[3],
                'view_count': row[4],
                'like_count': row[5],
                'comment_count': row[6],
                'thumbnail_url': row[7],
                'competitor_name': row[8],
                'competitor_id': row[9],
                'ia_classification': row[10],
                'human_classification': row[11],
                'confidence_score': row[12],
                'feedback_timestamp': feedback_timestamp,
                'user_feedback_type': row[14],
                'user_notes': row[15],
                'video_count': None
            })

        # 2. RÉCUPÉRER LES VIDÉOS CLASSIFIÉES PAR PROPAGATION DE PLAYLIST HUMAINE
        cursor.execute('''
            SELECT
                'video' as type,
                v.id,
                v.title as name,
                v.video_id,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.thumbnail_url,
                c.name as competitor_name,
                c.id as competitor_id,
                'propagated' as ia_classification, -- Source IA non pertinente ici
                v.category as human_classification,
                v.classification_confidence,
                v.classification_date,
                'playlist_propagation' as user_feedback_type,
                'Classification via playlist humaine' as user_notes,
                null as video_count_field
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.classification_source = 'playlist_propagation'
        ''')

        video_classifications_propagated = []
        for row in cursor.fetchall():
            classification_date = row[13]
            if classification_date:
                try:
                    from datetime import datetime
                    if isinstance(classification_date, str):
                        dt = datetime.fromisoformat(classification_date.replace('Z', '+00:00'))
                        classification_date = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
            
            video_classifications_propagated.append({
                'type': 'video',
                'id': row[1],
                'name': row[2],
                'title': row[2],
                'video_id': row[3],
                'view_count': row[4],
                'like_count': row[5],
                'comment_count': row[6],
                'thumbnail_url': row[7],
                'competitor_name': row[8],
                'competitor_id': row[9],
                'ia_classification': row[10],
                'human_classification': row[11],
                'confidence_score': row[12],
                'feedback_timestamp': classification_date,
                'user_feedback_type': row[14],
                'user_notes': row[15],
                'video_count': None
            })
        
        # Combiner les classifications de vidéos
        video_classifications = video_classifications_direct + video_classifications_propagated

        # 3. RÉCUPÉRER LES PLAYLISTS CLASSIFIÉES MANUELLEMENT (via champs de tracking)
        # Vérifier d'abord si les colonnes de tracking existent
        cursor.execute("PRAGMA table_info(playlist)")
        playlist_columns = [column[1] for column in cursor.fetchall()]
        
        has_tracking_columns = all(col in playlist_columns for col in ['classification_source', 'classification_confidence', 'classification_date', 'human_verified'])
        
        if has_tracking_columns:
            cursor.execute('''
                SELECT 
                    'playlist' as type,
                    p.id,
                    p.name,
                    p.playlist_id,
                    p.video_count,
                    null as like_count,
                    null as comment_count,
                    p.thumbnail_url,
                    c.name as competitor_name,
                    c.id as competitor_id,
                    'unknown' as ia_classification,
                    p.category as human_classification,
                    p.classification_confidence,
                    p.classification_date,
                    'manual_classification' as user_feedback_type,
                    'Classification manuelle via interface' as user_notes
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE (p.classification_source = 'human' OR p.human_verified = 1)
                AND p.category IS NOT NULL
                ORDER BY p.classification_date DESC
                LIMIT ? OFFSET ?
            ''', (limit // 2, offset // 2))
        else:
            # Si les colonnes n'existent pas, retourner une liste vide
            print("[SUPERVISED] ⚠️ Colonnes de tracking non trouvées - mettre à jour le schéma")
            cursor.execute("SELECT 1 WHERE 0")  # Requête vide pour avoir la même structure
        
        playlist_classifications = []
        for row in cursor.fetchall():
            # Formater le timestamp pour l'affichage
            classification_date = row[13]
            if classification_date:
                try:
                    from datetime import datetime
                    if isinstance(classification_date, str):
                        # Essayer différents formats
                        try:
                            dt = datetime.strptime(classification_date, '%Y-%m-%d %H:%M:%S')
                        except:
                            dt = datetime.fromisoformat(classification_date.replace('Z', '+00:00'))
                        classification_date = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
            
            playlist_classifications.append({
                'type': 'playlist',
                'id': row[1],
                'name': row[2],
                'title': row[2],  # Alias pour compatibilité template
                'playlist_id': row[3],
                'video_count': row[4],
                'view_count': None,  # Playlists n'ont pas de vues directes
                'like_count': row[5],
                'comment_count': row[6],
                'thumbnail_url': row[7],
                'competitor_name': row[8],
                'competitor_id': row[9],
                'ia_classification': row[10],
                'human_classification': row[11],
                'confidence_score': row[12],
                'feedback_timestamp': classification_date,
                'user_feedback_type': row[14],
                'user_notes': row[15]
            })
        
        # 4. COMBINER ET TRIER TOUTES LES CLASSIFICATIONS
        all_classifications = video_classifications + playlist_classifications
        
        # Éviter les doublons (une vidéo peut être dans feedback ET propagée)
        seen_ids = set()
        unique_classifications = []
        for item in all_classifications:
            # Créer une clé unique pour chaque élément
            item_key = (item['type'], item['id'])
            if item_key not in seen_ids:
                unique_classifications.append(item)
                seen_ids.add(item_key)

        # Trier par date de classification (plus récent en premier)
        unique_classifications.sort(key=lambda x: x['feedback_timestamp'] or '', reverse=True)
        
        # Appliquer la limite finale
        paginated_classifications = unique_classifications[offset:offset + limit] if limit > 0 else unique_classifications

        # 5. STATISTIQUES GLOBALES MISES À JOUR
        # Statistiques vidéos
        cursor.execute('''
            SELECT 
                COUNT(*) as total_video_reclassifications,
                COUNT(DISTINCT cf.video_id) as unique_videos,
                COUNT(DISTINCT c.id) as affected_competitors_videos
            FROM classification_feedback cf
            JOIN video v ON cf.video_id = v.id
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE cf.user_feedback_type = 'correction'
        ''')
        video_stats = cursor.fetchone()
        
        # Statistiques playlists
        if has_tracking_columns:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_playlist_classifications,
                    COUNT(DISTINCT p.id) as unique_playlists,
                    COUNT(DISTINCT c.id) as affected_competitors_playlists
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE (p.classification_source = 'human' OR p.human_verified = 1)
                AND p.category IS NOT NULL
            ''')
            playlist_stats = cursor.fetchone()
        else:
            playlist_stats = (0, 0, 0)  # Valeurs par défaut si les colonnes n'existent pas
        
        # 6. RÉPARTITION PAR TYPE DE CLASSIFICATION (vidéos)
        cursor.execute('''
            SELECT 
                original_category,
                corrected_category,
                COUNT(*) as count
            FROM classification_feedback
            WHERE user_feedback_type = 'correction'
            GROUP BY original_category, corrected_category
            ORDER BY count DESC
        ''')
        
        video_reclassification_matrix = {}
        for row in cursor.fetchall():
            original, corrected, count = row
            if original not in video_reclassification_matrix:
                video_reclassification_matrix[original] = {}
            video_reclassification_matrix[original][corrected] = count
        
        # 7. RÉPARTITION PAR CATÉGORIE (playlists)
        if has_tracking_columns:
            cursor.execute('''
                SELECT 
                    p.category,
                    COUNT(*) as count
                FROM playlist p
                WHERE (p.classification_source = 'human' OR p.human_verified = 1)
                AND p.category IS NOT NULL
                GROUP BY p.category
                ORDER BY count DESC
            ''')
            playlist_category_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        else:
            playlist_category_distribution = {}
        
        # 8. RÉPARTITION PAR CONCURRENT (combinée)
        cursor.execute('''
            SELECT 
                c.id,
                c.name,
                COUNT(DISTINCT v.id) as video_reclassifications
            FROM classification_feedback cf
            JOIN video v ON cf.video_id = v.id
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE cf.user_feedback_type = 'correction'
            GROUP BY c.id, c.name
        ''')
        video_competitor_stats = {row[1]: {'id': row[0], 'videos': row[2], 'playlists': 0} for row in cursor.fetchall()}

        # Ajouter les stats des vidéos propagées
        cursor.execute('''
            SELECT
                c.id,
                c.name,
                COUNT(v.id) as propagated_count
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.classification_source = 'playlist_propagation'
            GROUP BY c.id, c.name
        ''')
        for row in cursor.fetchall():
            competitor_id, competitor_name, propagated_count = row
            if competitor_name not in video_competitor_stats:
                video_competitor_stats[competitor_name] = {'id': competitor_id, 'videos': 0, 'playlists': 0}
            video_competitor_stats[competitor_name]['videos'] += propagated_count

        if has_tracking_columns:
            cursor.execute('''
                SELECT 
                    c.id,
                    c.name,
                    COUNT(*) as playlist_classifications
                FROM playlist p
                JOIN concurrent c ON p.concurrent_id = c.id
                WHERE (p.classification_source = 'human' OR p.human_verified = 1)
                AND p.category IS NOT NULL
                GROUP BY c.id, c.name
            ''')
            
            for row in cursor.fetchall():
                competitor_id, competitor_name, playlist_count = row
                if competitor_name not in video_competitor_stats:
                    video_competitor_stats[competitor_name] = {'id': competitor_id, 'videos': 0, 'playlists': 0}
                video_competitor_stats[competitor_name]['playlists'] = playlist_count
        
        # Convertir en liste avec total
        competitor_stats = []
        for name, stats_data in video_competitor_stats.items():
            total = stats_data['videos'] + stats_data['playlists']
            competitor_stats.append({
                'id': stats_data.get('id'),
                'name': name,
                'video_count': stats_data['videos'],
                'playlist_count': stats_data['playlists'],
                'total_count': total
            })
        competitor_stats.sort(key=lambda x: x['total_count'], reverse=True)
        
        # 6. STATISTIQUES GLOBALES - NOUVELLE VERSION
        total_human_count = video_stats[0] + playlist_stats[0]
        all_competitor_ids = set()
        
        # Récupérer les concurrents affectés
        for competitor_name in video_competitor_stats.keys():
            all_competitor_ids.add(competitor_name)

        # Récupérer les totaux globaux
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM playlist")
        total_playlists = cursor.fetchone()[0]

        return {
            'classifications': paginated_classifications,
            'video_classifications': video_classifications,
            'playlist_classifications': playlist_classifications,
            'total_count': total_human_count,
            'video_count': video_stats[0],
            'playlist_count': playlist_stats[0],
            'unique_videos': video_stats[1],
            'unique_playlists': playlist_stats[1],
            'affected_competitors': len(all_competitor_ids),
            'total_videos': total_videos,
            'total_playlists': total_playlists,
            'video_reclassification_matrix': video_reclassification_matrix,
            'playlist_category_distribution': playlist_category_distribution,
            'competitor_stats': competitor_stats
        }
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur récupération classifications humaines: {e}")
        return {
            'classifications': [],
            'video_classifications': [],
            'playlist_classifications': [],
            'total_count': 0,
            'video_count': 0,
            'playlist_count': 0,
            'unique_videos': 0,
            'unique_playlists': 0,
            'affected_competitors': 0,
            'total_videos': 0,  # Ajout de la clé manquante
            'total_playlists': 0, # Ajout de la clé manquante
            'video_reclassification_matrix': {},
            'playlist_category_distribution': {},
            'competitor_stats': [],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': False
            }
        }
    finally:
        conn.close()

def initialize_system():
    """Initialise le système d'apprentissage supervisé"""
    try:
        # Créer les tables nécessaires
        create_feedback_tables()
        
        # Vérifier si des données existent déjà
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM classification_feedback')
        feedback_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM learned_patterns')
        patterns_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"[SUPERVISED] 📊 Système initialisé avec {feedback_count} feedbacks et {patterns_count} patterns appris")
        
        return {
            'status': 'success',
            'feedback_count': feedback_count,
            'patterns_count': patterns_count
        }
        
    except Exception as e:
        print(f"[SUPERVISED] ❌ Erreur lors de l'initialisation: {e}")
        return {'status': 'error', 'message': str(e)}

# Initialiser le système lors du chargement du module
# initialize_system()