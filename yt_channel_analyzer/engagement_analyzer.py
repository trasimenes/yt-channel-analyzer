"""
Analyseur d'engagement pour extraire les vidéos les plus performantes
et analyser leurs thèmes principaux
"""

import re
from collections import Counter
from typing import List, Dict, Tuple
from .database import get_db_connection

class EngagementAnalyzer:
    """Analyse l'engagement des vidéos et extrait les thèmes"""
    
    def __init__(self):
        self.stop_words = self._load_stop_words()
        self.competitor_names = self._load_competitor_names()
        
    def _load_stop_words(self) -> set:
        """Charge les stop words multilingues"""
        return {
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
    
    def _load_competitor_names(self) -> set:
        """Charge les noms des concurrents à exclure"""
        names = set()
        try:
            from .database.competitors import CompetitorManager
            competitor_manager = CompetitorManager()
            competitors = competitor_manager.get_all_competitors()
            for comp in competitors:
                if comp.get('name'):
                    names.add(comp['name'].lower())
                    for word in comp['name'].replace('-', ' ').replace('_', ' ').split():
                        if len(word) > 2:
                            names.add(word.lower())
        except Exception as e:
            print(f"Erreur chargement concurrents: {e}")
        return names
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extrait les thèmes principaux d'un texte"""
        if not text:
            return []
        
        # Nettoyer le texte
        text = text.lower()
        text = re.sub(r'http[s]?://\S+', '', text)  # URLs
        text = re.sub(r'\S+@\S+', '', text)  # Emails
        text = re.sub(r'@\w+', '', text)  # Mentions
        text = re.sub(r'#\w+', '', text)  # Hashtags
        
        # Extraire les mots significatifs (3+ caractères, lettres uniquement)
        words = re.findall(r'\b[a-zA-ZàáâäèéêëìíîïòóôöùúûüñçşğıÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÑÇŞĞI]{3,}\b', text)
        
        # Filtrer les mots
        filtered_words = []
        for word in words:
            if (len(word) >= 3 and 
                word not in self.stop_words and 
                word not in self.competitor_names and
                not word.isdigit()):
                filtered_words.append(word)
        
        # Retourner les 5 mots les plus fréquents
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(5)]
    
    def get_top_engaging_videos(self, competitor_id: int, limit: int = 5) -> List[Dict]:
        """
        Récupère les vidéos les plus engageantes d'un concurrent
        
        Args:
            competitor_id: ID du concurrent
            limit: Nombre de vidéos à retourner (défaut: 5)
            
        Returns:
            Liste des vidéos avec leurs thèmes
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les vidéos avec calcul d'engagement (likes + commentaires)
        cursor.execute("""
            SELECT 
                v.id,
                v.title,
                v.description,
                v.view_count,
                v.like_count,
                v.comment_count,
                v.published_at,
                v.duration_text,
                v.thumbnail_url,
                (COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) as engagement_score,
                CASE 
                    WHEN v.view_count > 0 THEN 
                        ((COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) * 100.0 / v.view_count)
                    ELSE 0 
                END as engagement_rate
            FROM video v
            WHERE v.concurrent_id = ?
            AND v.view_count > 0
            ORDER BY engagement_score DESC, engagement_rate DESC
            LIMIT ?
        """, (competitor_id, limit))
        
        videos = cursor.fetchall()
        conn.close()
        
        # Analyser les thèmes pour chaque vidéo
        results = []
        for i, video in enumerate(videos, 1):
            (video_id, title, description, view_count, like_count, comment_count, 
             published_at, duration_text, thumbnail_url, engagement_score, engagement_rate) = video
            
            # Combiner titre et description pour l'analyse des thèmes
            combined_text = ""
            if title:
                combined_text += title + " "
            if description:
                combined_text += description
            
            themes = self._extract_themes(combined_text)
            
            results.append({
                'rank': i,
                'id': video_id,
                'title': title or 'Sans titre',
                'description': (description[:200] + '...') if description and len(description) > 200 else description,
                'view_count': view_count or 0,
                'like_count': like_count or 0,
                'comment_count': comment_count or 0,
                'engagement_score': engagement_score,
                'engagement_rate': round(engagement_rate, 2) if engagement_rate else 0,
                'published_at': published_at,
                'duration_text': duration_text,
                'thumbnail_url': thumbnail_url,
                'themes': themes[:3],  # Top 3 thèmes
                'theme_summary': ', '.join(themes[:3]) if themes else 'Aucun thème identifié'
            })
        
        return results
    
    def get_competitor_engagement_overview(self, competitor_id: int) -> Dict:
        """
        Récupère un aperçu général de l'engagement du concurrent
        
        Args:
            competitor_id: ID du concurrent
            
        Returns:
            Dictionnaire avec les statistiques d'engagement
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                AVG(COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) as avg_engagement,
                MAX(COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) as max_engagement,
                AVG(CASE 
                    WHEN v.view_count > 0 THEN 
                        ((COALESCE(v.like_count, 0) + COALESCE(v.comment_count, 0)) * 100.0 / v.view_count)
                    ELSE 0 
                END) as avg_engagement_rate,
                SUM(COALESCE(v.view_count, 0)) as total_views,
                SUM(COALESCE(v.like_count, 0)) as total_likes,
                SUM(COALESCE(v.comment_count, 0)) as total_comments
            FROM video v
            WHERE v.concurrent_id = ?
            AND v.view_count > 0
        """, (competitor_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_videos': result[0] or 0,
                'avg_engagement': round(result[1] or 0, 1),
                'max_engagement': result[2] or 0,
                'avg_engagement_rate': round(result[3] or 0, 2),
                'total_views': result[4] or 0,
                'total_likes': result[5] or 0,
                'total_comments': result[6] or 0
            }
        
        return {
            'total_videos': 0,
            'avg_engagement': 0,
            'max_engagement': 0,
            'avg_engagement_rate': 0,
            'total_views': 0,
            'total_likes': 0,
            'total_comments': 0
        }