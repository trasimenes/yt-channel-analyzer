#!/usr/bin/env python3
"""
Script pour transférer et analyser les commentaires du batch
Transfère de youtube_emotions_fast.db vers youtube_emotions_massive.db
et lance l'analyse émotionnelle
"""
import sqlite3
import logging
from pathlib import Path
from transformers import pipeline
import time
import re

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def detect_language(text):
    """Détection simple de langue basée sur des patterns"""
    text_lower = text.lower()
    
    # Patterns français
    french_patterns = [
        r'\b(le|la|les|de|du|des|un|une|et|ou|est|sont|avec|pour|dans|sur|par|ce|cette|qui|que|nous|vous|ils|elles|très|plus|moins|bien|mal|oui|non|merci|salut|bonjour)\b',
        r'ç', r'é|è|ê|ë', r'à|â', r'ù|û', r'ô', r'î|ï'
    ]
    
    # Patterns anglais
    english_patterns = [
        r'\b(the|and|or|is|are|with|for|in|on|by|this|that|who|what|we|you|they|very|more|less|good|bad|yes|no|thanks|hello|hi)\b',
        r'\b(awesome|amazing|great|cool|nice|love|like|hate|best|worst)\b'
    ]
    
    # Patterns allemands
    german_patterns = [
        r'\b(der|die|das|und|oder|ist|sind|mit|für|in|auf|von|dieser|diese|dieses|wer|was|wir|ihr|sie|sehr|mehr|weniger|gut|schlecht|ja|nein|danke|hallo)\b',
        r'ä|ö|ü|ß'
    ]
    
    # Patterns néerlandais
    dutch_patterns = [
        r'\b(de|het|en|of|is|zijn|met|voor|in|op|van|deze|dit|wie|wat|wij|jullie|zij|zeer|meer|minder|goed|slecht|ja|nee|dank|hallo)\b',
        r'ij|oe|aa|ee|oo|uu'
    ]
    
    # Compter les matches
    french_score = sum(len(re.findall(pattern, text_lower)) for pattern in french_patterns)
    english_score = sum(len(re.findall(pattern, text_lower)) for pattern in english_patterns)
    german_score = sum(len(re.findall(pattern, text_lower)) for pattern in german_patterns)
    dutch_score = sum(len(re.findall(pattern, text_lower)) for pattern in dutch_patterns)
    
    # Déterminer la langue
    scores = {
        'fr': french_score,
        'en': english_score,
        'de': german_score,
        'nl': dutch_score
    }
    
    max_score = max(scores.values())
    if max_score == 0:
        return 'en'  # Default to English if no patterns match
    
    # Retourner la langue avec le score le plus élevé
    return max(scores, key=scores.get)

# Chemins des bases de données
FAST_DB = Path('instance/youtube_emotions_fast.db')
MASSIVE_DB = Path('instance/youtube_emotions_massive.db')

def setup_massive_db():
    """Setup de la base de données massive pour l'analyse"""
    with sqlite3.connect(MASSIVE_DB) as conn:
        # Table pour les commentaires bruts
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comments_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                comment_id TEXT UNIQUE,
                comment_text TEXT NOT NULL,
                author_name TEXT,
                like_count INTEGER DEFAULT 0,
                published_at TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                language TEXT
            )
        ''')
        
        # Table pour les analyses émotionnelles
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comment_emotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                emotion_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                language TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES comments_raw(comment_id)
            )
        ''')
        
        # Index pour les performances
        conn.execute('CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments_raw(video_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_comments_processed ON comments_raw(processed)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_emotions_video_id ON comment_emotions(video_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_emotions_type ON comment_emotions(emotion_type)')
        
        conn.commit()
        logging.info("✅ Base de données massive configurée")

def transfer_comments():
    """Transférer les commentaires de fast vers massive"""
    setup_massive_db()
    
    # Lire les commentaires de la base fast
    with sqlite3.connect(FAST_DB) as fast_conn:
        cursor = fast_conn.execute('''
            SELECT video_id, comment_id, comment_text, author_name, like_count, published_at
            FROM fast_comments
        ''')
        comments = cursor.fetchall()
    
    logging.info(f"📊 Trouvé {len(comments)} commentaires à transférer")
    
    # Transférer vers la base massive
    with sqlite3.connect(MASSIVE_DB) as massive_conn:
        transferred = 0
        for comment in comments:
            try:
                massive_conn.execute('''
                    INSERT OR IGNORE INTO comments_raw 
                    (video_id, comment_id, comment_text, author_name, like_count, published_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', comment)
                transferred += 1
            except Exception as e:
                logging.warning(f"Erreur transfert commentaire {comment[1]}: {e}")
        
        massive_conn.commit()
        logging.info(f"✅ {transferred} commentaires transférés")
        return transferred

def analyze_emotions():
    """Analyser les émotions des commentaires avec XLM-RoBERTa multilingue (3 sentiments)"""
    logging.info("🤖 Chargement du modèle XLM-RoBERTa multilingue (3 sentiments: positive, negative, neutral)...")
    
    # Charger le modèle multilingue avec 3 sentiments
    try:
        emotion_analyzer = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
            device=-1  # CPU
        )
        logging.info("✅ Modèle XLM-RoBERTa multilingue chargé avec succès (3 sentiments)")
    except Exception as e:
        logging.error(f"❌ Erreur chargement modèle: {e}")
        return
    
    # Lire les commentaires non traités avec métadonnées
    with sqlite3.connect(MASSIVE_DB) as conn:
        cursor = conn.execute('''
            SELECT id, comment_id, video_id, comment_text, like_count, author_name, published_at
            FROM comments_raw 
            WHERE processed = FALSE
            ORDER BY id
        ''')
        comments = cursor.fetchall()
    
    logging.info(f"🚀 Analyse de {len(comments)} commentaires avec 3 sentiments multilingues (positive/negative/neutral)...")
    
    analyzed_count = 0
    batch_size = 10
    
    with sqlite3.connect(MASSIVE_DB) as conn:
        for i, (row_id, comment_id, video_id, text, like_count, author_name, published_at) in enumerate(comments):
            try:
                # Skip très courts commentaires
                if len(text.strip()) < 10:
                    continue
                    
                # Détecter la langue
                detected_language = detect_language(text)
                
                # Analyser l'émotion avec le modèle XLM-RoBERTa multilingue
                result = emotion_analyzer(text[:512])  # Limiter la taille
                
                # Le modèle retourne une liste avec un dict
                if isinstance(result, list) and len(result) > 0:
                    emotion_data = result[0]
                else:
                    emotion_data = result
                    
                emotion_type = emotion_data['label'].lower()
                confidence = emotion_data['score']
                
                # Log pour debug (seulement pour les 10 premiers)
                if analyzed_count < 10:
                    logging.info(f"💭 Commentaire: '{text[:50]}...' → Émotion: {emotion_type} ({confidence:.2f})")
                
                # Calculer le score pondéré par les likes
                like_count = like_count or 0
                weight = 1 + like_count * 0.1
                weighted_score = confidence * weight
                
                # Sauvegarder l'analyse détaillée
                conn.execute('''
                    INSERT INTO comment_emotions 
                    (comment_id, video_id, emotion_type, confidence, language, 
                     like_count, author_name, published_at, weighted_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (comment_id, video_id, emotion_type, confidence, detected_language,
                      like_count, author_name, published_at, weighted_score))
                
                # Marquer comme traité
                conn.execute('''
                    UPDATE comments_raw 
                    SET processed = TRUE 
                    WHERE id = ?
                ''', (row_id,))
                
                analyzed_count += 1
                
                # Commit par batch et affichage progrès
                if analyzed_count % batch_size == 0:
                    conn.commit()
                    progress = (analyzed_count / len(comments)) * 100
                    logging.info(f"📊 Progrès: {analyzed_count}/{len(comments)} ({progress:.1f}%)")
                    time.sleep(0.1)  # Petite pause
                
            except Exception as e:
                logging.error(f"❌ Erreur analyse commentaire {comment_id}: {e}")
                # Marquer comme traité même en cas d'erreur
                conn.execute('''
                    UPDATE comments_raw 
                    SET processed = TRUE 
                    WHERE id = ?
                ''', (row_id,))
        
        conn.commit()
    
    logging.info(f"🎉 Analyse terminée: {analyzed_count} commentaires analysés")
    return analyzed_count

def create_summary_views():
    """Créer les vues pour les statistiques avec 27 émotions"""
    with sqlite3.connect(MASSIVE_DB) as conn:
        # Vue globale des statistiques par émotion
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_global_stats AS
            SELECT 
                COUNT(*) as total_comments,
                AVG(confidence) as avg_confidence,
                AVG(weighted_score) as avg_weighted_score,
                COUNT(DISTINCT video_id) as videos_analyzed,
                COUNT(DISTINCT language) as languages_detected,
                COUNT(DISTINCT emotion_type) as emotions_detected
            FROM comment_emotions
        ''')
        
        # Vue détaillée par émotion
        conn.execute('''
            CREATE VIEW IF NOT EXISTS emotion_detailed_stats AS
            SELECT 
                emotion_type,
                COUNT(*) as count,
                (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM comment_emotions)) as percentage,
                AVG(confidence) as avg_confidence,
                AVG(weighted_score) as avg_weighted_score,
                SUM(like_count) as total_likes
            FROM comment_emotions
            GROUP BY emotion_type
            ORDER BY count DESC
        ''')
        
        # Vue par vidéo avec émotions dominantes
        conn.execute('''
            CREATE VIEW IF NOT EXISTS video_emotion_summary AS
            SELECT 
                ce.video_id,
                COUNT(*) as total_comments,
                AVG(ce.confidence) as avg_confidence,
                AVG(ce.weighted_score) as avg_weighted_score,
                SUM(ce.like_count) as total_likes,
                (
                    SELECT emotion_type 
                    FROM comment_emotions ce2 
                    WHERE ce2.video_id = ce.video_id 
                    GROUP BY emotion_type 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 1
                ) as dominant_emotion,
                (
                    SELECT COUNT(*) * 100.0 / COUNT(ce3.id)
                    FROM comment_emotions ce3
                    WHERE ce3.video_id = ce.video_id
                    AND ce3.emotion_type = (
                        SELECT emotion_type 
                        FROM comment_emotions ce4
                        WHERE ce4.video_id = ce.video_id 
                        GROUP BY emotion_type 
                        ORDER BY COUNT(*) DESC 
                        LIMIT 1
                    )
                ) as dominant_emotion_percentage
            FROM comment_emotions ce
            GROUP BY ce.video_id
        ''')
        
        conn.commit()
        logging.info("✅ Vues de statistiques créées")

def show_results():
    """Afficher les résultats avec 27 émotions détaillées"""
    with sqlite3.connect(MASSIVE_DB) as conn:
        # Statistiques globales
        cursor = conn.execute('SELECT * FROM emotion_global_stats')
        stats = cursor.fetchone()
        
        if stats:
            if len(stats) == 6:
                total, confidence, weighted_score, videos, languages, emotions = stats
            else:
                # Fallback pour gérer différents nombres de colonnes
                total = stats[0] if len(stats) > 0 else 0
                confidence = stats[1] if len(stats) > 1 else 0
                weighted_score = stats[2] if len(stats) > 2 else 0
                videos = stats[3] if len(stats) > 3 else 0
                languages = stats[4] if len(stats) > 4 else 0
                emotions = stats[5] if len(stats) > 5 else 0
            logging.info(f"""
🎉 RÉSULTATS DE L'ANALYSE SENTIMENTALE MULTILINGUE (3 SENTIMENTS):
├── Total commentaires: {total:,}
├── Confiance moyenne: {confidence:.2f}
├── Score pondéré moyen: {weighted_score:.2f}
├── Vidéos analysées: {videos:,}
├── Langues détectées: {languages}
└── Sentiments détectés: {emotions}/3
            """)
        
        # Top 3 sentiments les plus fréquents
        cursor = conn.execute('''
            SELECT emotion_type, count, percentage, avg_confidence
            FROM emotion_detailed_stats
            LIMIT 3
        ''')
        
        top_emotions = cursor.fetchall()
        if top_emotions:
            logging.info("🎭 RÉPARTITION DES 3 SENTIMENTS MULTILINGUES:")
            for i, (emotion, count, percentage, conf) in enumerate(top_emotions, 1):
                logging.info(f"  {i}. {emotion.upper()}: {count} ({percentage:.1f}%) - confiance: {conf:.2f}")
        
        # Top des vidéos par émotion dominante
        cursor = conn.execute('''
            SELECT video_id, total_comments, dominant_emotion, dominant_emotion_percentage
            FROM video_emotion_summary
            ORDER BY total_comments DESC
            LIMIT 5
        ''')
        
        top_videos = cursor.fetchall()
        if top_videos:
            logging.info("🏆 TOP 5 VIDÉOS AVEC LE PLUS DE COMMENTAIRES:")
            for i, (video_id, comments, emotion, percentage) in enumerate(top_videos, 1):
                logging.info(f"  {i}. {video_id}: {comments} commentaires, émotion dominante: {emotion.upper()} ({percentage:.1f}%)")

def main():
    """Fonction principale"""
    logging.info("🚀 Démarrage du transfert et analyse des commentaires")
    
    # Vérifier que la base fast existe
    if not FAST_DB.exists():
        logging.error(f"❌ Base de données {FAST_DB} introuvable")
        return
    
    try:
        # Étape 1: Transférer les commentaires
        transferred = transfer_comments()
        if transferred == 0:
            logging.warning("⚠️ Aucun commentaire transféré")
            return
        
        # Étape 2: Analyser les émotions
        analyzed = analyze_emotions()
        if analyzed == 0:
            logging.warning("⚠️ Aucun commentaire analysé")
            return
        
        # Étape 3: Créer les vues de statistiques
        create_summary_views()
        
        # Étape 4: Afficher les résultats
        show_results()
        
        logging.info("✅ Processus terminé avec succès!")
        logging.info("🌐 Rendez-vous sur http://localhost:8082/sentiment-analysis pour voir vos visualisations!")
        
    except Exception as e:
        logging.error(f"❌ Erreur générale: {e}")

if __name__ == "__main__":
    main()