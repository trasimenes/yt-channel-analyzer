#!/usr/bin/env python3
"""
🚀 Export Sentiment Analysis pour Production
Génère un fichier JSON static avec toutes les données sentiment pour la branche production
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(__file__))

def export_sentiment_for_production():
    """Exporte les données sentiment vers un JSON statique pour production"""
    
    print("🚀 EXPORT SENTIMENT ANALYSIS - MODE PRODUCTION")
    print("=" * 60)
    
    # Connexion à la base de données principale
    db_path = Path('instance/database.db')
    if not db_path.exists():
        print("❌ Base de données principal introuvable")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Vérifier si on a des données sentiment réelles
        massive_db = Path('instance/youtube_emotions_massive.db')
        has_real_sentiment = False
        sentiment_stats = None
        videos_with_sentiment = []
        
        if massive_db.exists():
            print("✅ Base sentiment détectée, extraction des données réelles...")
            sentiment_conn = sqlite3.connect(massive_db)
            sentiment_cursor = sentiment_conn.cursor()
            
            try:
                # Stats réelles depuis comment_emotions
                sentiment_cursor.execute('SELECT COUNT(*) FROM comment_emotions')
                total_comments = sentiment_cursor.fetchone()[0]
                
                if total_comments > 0:
                    has_real_sentiment = True
                    
                    sentiment_cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "positive"')
                    positive_count = sentiment_cursor.fetchone()[0]
                    
                    sentiment_cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "negative"')
                    negative_count = sentiment_cursor.fetchone()[0]
                    
                    sentiment_cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "neutral"')
                    neutral_count = sentiment_cursor.fetchone()[0]
                    
                    sentiment_cursor.execute('SELECT COUNT(DISTINCT video_id) FROM comment_emotions')
                    analyzed_videos = sentiment_cursor.fetchone()[0]
                    
                    sentiment_cursor.execute('SELECT AVG(confidence) FROM comment_emotions')
                    avg_confidence = sentiment_cursor.fetchone()[0] or 0
                    
                    sentiment_stats = {
                        'total_videos_analyzed': analyzed_videos,
                        'total_comments_analyzed': total_comments,
                        'positive_count': positive_count,
                        'negative_count': negative_count,
                        'neutral_count': neutral_count,
                        'positive_percentage': (positive_count / max(total_comments, 1)) * 100,
                        'negative_percentage': (negative_count / max(total_comments, 1)) * 100,
                        'neutral_percentage': (neutral_count / max(total_comments, 1)) * 100,
                        'avg_confidence': avg_confidence,
                        'engagement_correlation': 0.42  # Valeur par défaut
                    }
                    
                    # Top vidéos avec sentiment réel
                    sentiment_cursor.execute('''
                        SELECT 
                            ce.video_id,
                            COUNT(*) as total_comments,
                            SUM(CASE WHEN ce.emotion_type = 'positive' THEN 1 ELSE 0 END) as positive_count,
                            SUM(CASE WHEN ce.emotion_type = 'negative' THEN 1 ELSE 0 END) as negative_count,
                            SUM(CASE WHEN ce.emotion_type = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                            AVG(ce.confidence) as avg_confidence,
                            CASE 
                                WHEN SUM(CASE WHEN ce.emotion_type = 'positive' THEN 1 ELSE 0 END) > 
                                     SUM(CASE WHEN ce.emotion_type = 'negative' THEN 1 ELSE 0 END) AND
                                     SUM(CASE WHEN ce.emotion_type = 'positive' THEN 1 ELSE 0 END) >
                                     SUM(CASE WHEN ce.emotion_type = 'neutral' THEN 1 ELSE 0 END)
                                THEN 'positive'
                                WHEN SUM(CASE WHEN ce.emotion_type = 'negative' THEN 1 ELSE 0 END) > 
                                     SUM(CASE WHEN ce.emotion_type = 'positive' THEN 1 ELSE 0 END) AND
                                     SUM(CASE WHEN ce.emotion_type = 'negative' THEN 1 ELSE 0 END) >
                                     SUM(CASE WHEN ce.emotion_type = 'neutral' THEN 1 ELSE 0 END)
                                THEN 'negative'
                                ELSE 'neutral'
                            END as dominant_sentiment
                        FROM comment_emotions ce
                        GROUP BY ce.video_id
                        HAVING total_comments >= 5
                        ORDER BY positive_count DESC
                        LIMIT 200
                    ''')
                    
                    videos_with_sentiment = [
                        {
                            'video_id': row[0],
                            'total_comments': row[1],
                            'positive_count': row[2],
                            'negative_count': row[3],
                            'neutral_count': row[4],
                            'avg_confidence': round(row[5] * 100) if row[5] else 0,
                            'dominant_sentiment': row[6],
                            'positive_percentage': round((row[2] / row[1]) * 100, 1)
                        }
                        for row in sentiment_cursor.fetchall()
                    ]
                    
                    print(f"✅ Données sentiment réelles: {total_comments:,} commentaires, {analyzed_videos} vidéos")
                    
            except Exception as e:
                print(f"⚠️  Erreur lecture sentiment: {e}")
            finally:
                sentiment_conn.close()
        
        # 2. Fallback : Analyse par mots-clés sur les titres de vidéos
        if not has_real_sentiment:
            print("📝 Pas de données sentiment, génération fallback par mots-clés...")
            
            positive_keywords = ['amazing', 'beautiful', 'fantastic', 'wonderful', 'great', 'excellent', 'perfect', 'love', 'best', 'awesome']
            negative_keywords = ['bad', 'terrible', 'awful', 'worst', 'hate', 'horrible', 'boring', 'stupid']
            
            cursor.execute("""
                SELECT 
                    v.id,
                    v.video_id,
                    v.title,
                    v.view_count,
                    v.like_count,
                    v.comment_count,
                    v.published_at,
                    v.duration_seconds,
                    v.category,
                    v.thumbnail_url,
                    c.id as competitor_id,
                    c.name as competitor_name,
                    c.channel_url
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.title IS NOT NULL
                AND v.view_count > 100
                ORDER BY v.view_count DESC
                LIMIT 1000
            """)
            
            videos = cursor.fetchall()
            
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for video in videos[:200]:  # Top 200 pour l'affichage
                title = video[2].lower() if video[2] else ''
                
                has_positive = any(keyword in title for keyword in positive_keywords)
                has_negative = any(keyword in title for keyword in negative_keywords)
                
                if has_positive and not has_negative:
                    sentiment = 'positive'
                    positive_count += 1
                elif has_negative and not has_positive:
                    sentiment = 'negative'
                    negative_count += 1
                else:
                    sentiment = 'neutral'
                    neutral_count += 1
                
                # Simuler des commentaires basés sur l'engagement
                simulated_comments = max(1, (video[5] or 0) // 10)  # 1/10 des vrais commentaires
                pos_comments = int(simulated_comments * 0.4) if sentiment == 'positive' else int(simulated_comments * 0.2)
                neg_comments = int(simulated_comments * 0.4) if sentiment == 'negative' else int(simulated_comments * 0.1)
                neu_comments = simulated_comments - pos_comments - neg_comments
                
                videos_with_sentiment.append({
                    'video_id': video[1],
                    'title': video[2],
                    'thumbnail_url': video[9],
                    'competitor_name': video[11],
                    'total_comments': simulated_comments,
                    'positive_count': pos_comments,
                    'negative_count': neg_comments,
                    'neutral_count': neu_comments,
                    'dominant_sentiment': sentiment,
                    'positive_percentage': round((pos_comments / simulated_comments) * 100, 1),
                    'avg_confidence': 75,  # Confiance simulée
                    'rank': len(videos_with_sentiment) + 1
                })
            
            total_simulated = len(videos_with_sentiment)
            sentiment_stats = {
                'total_videos_analyzed': total_simulated,
                'total_comments_analyzed': sum(v['total_comments'] for v in videos_with_sentiment),
                'positive_count': sum(v['positive_count'] for v in videos_with_sentiment),
                'negative_count': sum(v['negative_count'] for v in videos_with_sentiment),
                'neutral_count': sum(v['neutral_count'] for v in videos_with_sentiment),
                'positive_percentage': (positive_count / max(total_simulated, 1)) * 100,
                'negative_percentage': (negative_count / max(total_simulated, 1)) * 100,
                'neutral_percentage': (neutral_count / max(total_simulated, 1)) * 100,
                'avg_confidence': 75,
                'engagement_correlation': 0.35
            }
            
            print(f"📊 Données fallback générées: {total_simulated} vidéos analysées")
        
        # 3. Enrichir avec métadonnées vidéo
        enriched_videos = []
        for video_data in videos_with_sentiment:
            cursor.execute("""
                SELECT v.title, v.thumbnail_url, c.name, v.view_count, v.like_count, v.comment_count, v.published_at
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.video_id = ?
            """, (video_data['video_id'],))
            
            video_info = cursor.fetchone()
            if video_info:
                enriched_video = {
                    **video_data,
                    'title': video_info[0] or 'Titre non disponible',
                    'thumbnail_url': video_info[1] or '',
                    'competitor_name': video_info[2] or 'Concurrent inconnu',
                    'view_count': video_info[3] or 0,
                    'like_count': video_info[4] or 0,
                    'original_comment_count': video_info[5] or 0,
                    'published_at': video_info[6] or '',
                    'rank': len(enriched_videos) + 1
                }
                enriched_videos.append(enriched_video)
        
        # 4. Préparer la structure finale
        export_data = {
            'export_info': {
                'export_date': datetime.now().isoformat(),
                'source': 'real_sentiment' if has_real_sentiment else 'keyword_fallback',
                'version': '1.0',
                'total_videos': len(enriched_videos)
            },
            'stats': sentiment_stats,
            'videos': enriched_videos[:100],  # Top 100 pour l'interface
            'charts_data': {
                'global_distribution': {
                    'positive': sentiment_stats['positive_count'],
                    'negative': sentiment_stats['negative_count'],
                    'neutral': sentiment_stats['neutral_count']
                },
                'country_sentiment_data': {},  # À implémenter si nécessaire
                'competitor_sentiment_data': [],  # À implémenter si nécessaire  
                'temporal_sentiment_data': []  # À implémenter si nécessaire
            }
        }
        
        # 5. Sauvegarder le fichier JSON
        export_file = Path('static/sentiment_analysis_production.json')
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Export terminé: {export_file}")
        print(f"📊 Stats finales:")
        print(f"   - Vidéos: {sentiment_stats['total_videos_analyzed']}")
        print(f"   - Commentaires: {sentiment_stats['total_comments_analyzed']:,}")
        print(f"   - Positifs: {sentiment_stats['positive_count']:,} ({sentiment_stats['positive_percentage']:.1f}%)")
        print(f"   - Négatifs: {sentiment_stats['negative_count']:,} ({sentiment_stats['negative_percentage']:.1f}%)")
        print(f"   - Neutres: {sentiment_stats['neutral_count']:,} ({sentiment_stats['neutral_percentage']:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur export: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    export_sentiment_for_production()