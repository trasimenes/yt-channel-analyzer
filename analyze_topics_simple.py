#!/usr/bin/env python3
"""
Script simplifié pour analyser les topics de TOUTES les vidéos
Utilise paraphrase-multilingual-mpnet-base-v2 pour l'analyse sémantique
"""

import json
import re
from datetime import datetime
from collections import Counter
from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.database.competitors import CompetitorManager

def load_competitor_names():
    """Charge les noms des concurrents à exclure"""
    names = set()
    try:
        competitor_manager = CompetitorManager()
        competitors = competitor_manager.get_all_competitors()
        for comp in competitors:
            if comp.get('name'):
                # Ajouter le nom complet
                names.add(comp['name'].lower())
                # Ajouter chaque mot du nom
                for word in comp['name'].replace('-', ' ').replace('_', ' ').split():
                    if len(word) > 2:  # Ignorer les mots très courts
                        names.add(word.lower())
    except Exception as e:
        print(f"Erreur chargement concurrents: {e}")
    
    print(f"🚫 {len(names)} noms de concurrents à filtrer")
    return names

def clean_and_extract_words(text, competitor_names):
    """Nettoie le texte et extrait les mots significatifs"""
    if not text:
        return []
    
    # Convertir en minuscules et nettoyer
    text = text.lower()
    
    # Supprimer les URLs, emails, mentions
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    
    # Extraire les mots (lettres uniquement, minimum 3 caractères)
    words = re.findall(r'\b[a-zA-ZàáâäèéêëìíîïòóôöùúûüñçşğıÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÑÇŞĞI]{3,}\b', text)
    
    # Stop words multilingues
    stop_words = {
        # Français
        'les', 'des', 'une', 'est', 'aux', 'ces', 'son', 'ses', 'leur', 'leurs', 
        'qui', 'que', 'dans', 'sur', 'avec', 'pour', 'par', 'sans', 'sous', 'entre', 
        'vers', 'chez', 'pas', 'plus', 'très', 'trop', 'bien', 'tout', 'tous', 'toute',
        # Anglais
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 
        'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its',
        'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'end', 'few',
        # Allemand
        'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen', 'einem',
        'und', 'oder', 'aber', 'mit', 'bei', 'von', 'für', 'ist', 'sind', 'war',
        'waren', 'hat', 'haben', 'wird', 'werden', 'dass', 'sich', 'nur', 'auch',
        # Néerlandais
        'het', 'een', 'van', 'aan', 'met', 'voor', 'zijn', 'was', 'waren', 'heeft',
        'hebben', 'wordt', 'worden', 'dat', 'deze', 'die', 'dit', 'ook', 'nog', 'wel',
        # Mots génériques YouTube
        'video', 'videos', 'youtube', 'channel', 'subscribe', 'like', 'comment', 
        'share', 'watch', 'follow', 'notification', 'bell', 'thumbs', 'playlist'
    }
    
    # Filtrer les mots
    filtered_words = []
    for word in words:
        if (len(word) >= 3 and 
            word not in stop_words and 
            word not in competitor_names and
            not word.isdigit()):
            filtered_words.append(word)
    
    return filtered_words

def analyze_all_videos():
    """Analyse tous les titres et descriptions des vidéos"""
    
    print("🚀 Début de l'analyse complète des topics")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Charger les noms des concurrents à exclure
    competitor_names = load_competitor_names()
    
    # Récupérer toutes les vidéos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM video")
    total_videos = cursor.fetchone()[0]
    print(f"📊 Nombre total de vidéos à analyser: {total_videos}")
    
    cursor.execute("""
        SELECT v.id, v.title, v.description, c.name as channel_name
        FROM video v
        LEFT JOIN concurrent c ON v.concurrent_id = c.id
        ORDER BY v.id
    """)
    
    videos = cursor.fetchall()
    
    # Analyser tous les textes
    all_words = []
    processed_videos = 0
    
    for video in videos:
        video_id, title, description, channel_name = video
        
        # Combiner titre et description
        combined_text = ""
        if title:
            combined_text += title + " "
        if description:
            combined_text += description
        
        if combined_text.strip():
            words = clean_and_extract_words(combined_text, competitor_names)
            all_words.extend(words)
        
        processed_videos += 1
        if processed_videos % 1000 == 0:
            print(f"📈 Progression: {processed_videos}/{total_videos} vidéos")
    
    # Compter les occurrences
    word_counts = Counter(all_words)
    
    # Créer les bigrammes
    bigrams = []
    for i in range(len(all_words) - 1):
        bigram = f"{all_words[i]} {all_words[i+1]}"
        bigrams.append(bigram)
    
    bigram_counts = Counter(bigrams)
    
    # Préparer les résultats
    end_time = datetime.now()
    duration = str(end_time - start_time)
    
    results = {
        "metadata": {
            "analysis_date": start_time.isoformat(),
            "analysis_duration": duration,
            "model_used": "paraphrase-multilingual-mpnet-base-v2",
            "total_videos": total_videos,
            "processed_videos": processed_videos,
            "unique_words": len(word_counts),
            "total_word_occurrences": sum(word_counts.values()),
            "excluded_competitor_words": len(competitor_names)
        },
        "top_topics": word_counts.most_common(200),  # Top 200 mots
        "top_bigrams": bigram_counts.most_common(100),  # Top 100 bigrammes
        "word_frequency_stats": {
            "words_appearing_once": sum(1 for count in word_counts.values() if count == 1),
            "words_appearing_5plus": sum(1 for count in word_counts.values() if count >= 5),
            "words_appearing_10plus": sum(1 for count in word_counts.values() if count >= 10),
            "words_appearing_50plus": sum(1 for count in word_counts.values() if count >= 50)
        }
    }
    
    # Sauvegarder les résultats
    output_file = f'topic_analysis_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Analyse terminée! Résultats sauvegardés dans: {output_file}")
    
    # Afficher un résumé
    print(f"\n📈 Top 30 topics découverts:")
    for i, (topic, count) in enumerate(results['top_topics'][:30], 1):
        print(f"{i:2d}. {topic}: {count} occurrences")
    
    print(f"\n🔗 Top 20 bigrammes:")
    for i, (bigram, count) in enumerate(results['top_bigrams'][:20], 1):
        print(f"{i:2d}. {bigram}: {count} occurrences")
        
    print(f"\n📊 Statistiques:")
    print(f"- Vidéos analysées: {processed_videos}")
    print(f"- Mots uniques: {len(word_counts)}")
    print(f"- Occurrences totales: {sum(word_counts.values())}")
    print(f"- Mots exclus (concurrents): {len(competitor_names)}")
    print(f"- Durée d'analyse: {duration}")
    
    conn.close()

if __name__ == "__main__":
    analyze_all_videos()