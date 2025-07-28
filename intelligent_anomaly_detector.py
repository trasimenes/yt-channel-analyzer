#!/usr/bin/env python3
"""
INTELLIGENT ANOMALY DETECTOR & FIXER
Scanne tous les concurrents, détecte les problèmes, explique tout et corrige intelligemment

Détections :
- Distribution HHH aberrante (0%, 100%, déséquilibres)
- Durées N/A ou incohérentes  
- Fréquences impossibles
- Dates corrompues
- Classifications manquantes
- Métriques absurdes
"""
import sys
import os
import requests
import json
import time
import sqlite3
import re
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.append(str(Path(__file__).parent))

from yt_channel_analyzer.database import get_db_connection
from services.competitor_service import CompetitorAdvancedMetricsService

class IntelligentAnomalyDetector:
    """Détecteur intelligent d'anomalies avec debug ultra-verbose"""
    
    def __init__(self):
        self.verbose_log = []
        self.anomalies_found = []
        self.fixes_applied = []
        self.api_key = self.get_youtube_api_key()
        
    def log(self, message, level="INFO"):
        """Log avec timestamp et niveau"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        self.verbose_log.append(formatted)
        
    def log_anomaly(self, competitor_name, anomaly_type, details, severity="HIGH"):
        """Enregistrer une anomalie détectée"""
        anomaly = {
            'timestamp': datetime.now().isoformat(),
            'competitor': competitor_name,
            'type': anomaly_type,
            'details': details,
            'severity': severity
        }
        self.anomalies_found.append(anomaly)
        
        severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🔶", "LOW": "ℹ️"}
        self.log(f"{severity_emoji.get(severity, '🔍')} ANOMALY [{competitor_name}] {anomaly_type}: {details}", "ANOMALY")
    
    def log_fix(self, competitor_name, fix_type, details, success=True):
        """Enregistrer une correction appliquée"""
        fix = {
            'timestamp': datetime.now().isoformat(),
            'competitor': competitor_name,
            'type': fix_type,
            'details': details,
            'success': success
        }
        self.fixes_applied.append(fix)
        
        status_emoji = "✅" if success else "❌"
        self.log(f"{status_emoji} FIX [{competitor_name}] {fix_type}: {details}", "FIX")
    
    def get_youtube_api_key(self):
        """Récupérer la clé API YouTube"""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if api_key:
            return api_key
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = 'youtube_api_key'")
            result = cursor.fetchone()
            conn.close()
            if result:
                return result[0]
        except:
            pass
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YouTube API key not found. Please set YOUTUBE_API_KEY in .env file")
        return api_key
    
    def run_complete_analysis(self):
        """Analyse complète de tous les concurrents"""
        
        self.log("🚀 DÉBUT ANALYSE INTELLIGENTE - Détection d'anomalies globale", "START")
        self.log(f"🔑 API Key disponible: {'✅' if self.api_key else '❌'}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer tous les concurrents
        cursor.execute("""
            SELECT id, name, channel_id, channel_url, country
            FROM concurrent 
            WHERE channel_id IS NOT NULL 
            AND channel_id != ''
            ORDER BY name
        """)
        
        competitors = cursor.fetchall()
        total_competitors = len(competitors)
        
        self.log(f"📋 {total_competitors} concurrents à analyser")
        self.log("=" * 80)
        
        # Phase 1: Scan de base pour anomalies générales
        self.log("🔍 PHASE 1: SCAN GÉNÉRAL DES ANOMALIES", "PHASE")
        
        for i, (competitor_id, name, channel_id, channel_url, country) in enumerate(competitors, 1):
            self.log(f"\n📊 [{i}/{total_competitors}] ANALYSE: {name} (Pays: {country or 'Non spécifié'})")
            self.analyze_competitor_basic_anomalies(conn, competitor_id, name)
        
        # Phase 2: Analyse des métriques détaillées
        self.log("\n" + "=" * 80)
        self.log("📈 PHASE 2: ANALYSE DÉTAILLÉE DES MÉTRIQUES", "PHASE")
        
        for i, (competitor_id, name, channel_id, channel_url, country) in enumerate(competitors, 1):
            self.log(f"\n🎯 [{i}/{total_competitors}] MÉTRIQUES: {name}")
            self.analyze_competitor_detailed_metrics(conn, competitor_id, name)
        
        # Phase 3: Corrections intelligentes
        self.log("\n" + "=" * 80)
        self.log("🔧 PHASE 3: CORRECTIONS INTELLIGENTES", "PHASE")
        
        for i, (competitor_id, name, channel_id, channel_url, country) in enumerate(competitors, 1):
            self.log(f"\n⚡ [{i}/{total_competitors}] CORRECTIONS: {name}")
            self.apply_intelligent_fixes(conn, competitor_id, name, channel_id)
        
        # Phase 4: Rapport final
        self.log("\n" + "=" * 80)
        self.log("📋 PHASE 4: RAPPORT FINAL", "PHASE")
        self.generate_final_report()
        
        conn.close()
    
    def analyze_competitor_basic_anomalies(self, conn, competitor_id, name):
        """Analyse de base pour détecter les anomalies évidentes"""
        
        cursor = conn.cursor()
        
        # 1. Compter les vidéos
        cursor.execute("SELECT COUNT(*) FROM video WHERE concurrent_id = ?", (competitor_id,))
        video_count = cursor.fetchone()[0]
        
        if video_count == 0:
            self.log_anomaly(name, "NO_VIDEOS", "Aucune vidéo en base", "CRITICAL")
            return
        
        self.log(f"   📺 {video_count} vidéos trouvées")
        
        # 2. Vérifier la distribution HHH
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
                COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
                COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count,
                COUNT(CASE WHEN category IS NULL OR category = '' OR category = 'uncategorized' THEN 1 END) as uncategorized_count
            FROM video WHERE concurrent_id = ?
        """, (competitor_id,))
        
        hero, hub, help_count, uncategorized = cursor.fetchone()
        classified_total = hero + hub + help_count
        
        self.log(f"   🎯 HHH: {hero} HERO, {hub} HUB, {help_count} HELP ({uncategorized} non classifiées)")
        
        # Détecter les anomalies HHH
        if uncategorized > 0:
            percentage = (uncategorized / video_count) * 100
            self.log_anomaly(name, "UNCATEGORIZED_VIDEOS", f"{uncategorized} vidéos ({percentage:.1f}%) non classifiées", "HIGH")
        
        if classified_total > 0:
            hero_pct = (hero / classified_total) * 100
            hub_pct = (hub / classified_total) * 100
            help_pct = (help_count / classified_total) * 100
            
            # Détection des problèmes de distribution
            if hero_pct == 0:
                self.log_anomaly(name, "ZERO_HERO", f"0% de contenu HERO sur {classified_total} vidéos", "HIGH")
            elif hero_pct > 80:
                self.log_anomaly(name, "TOO_MUCH_HERO", f"{hero_pct:.1f}% HERO (déséquilibré)", "MEDIUM")
            
            if help_pct == 0 and classified_total > 20:
                self.log_anomaly(name, "ZERO_HELP", f"0% de contenu HELP sur {classified_total} vidéos", "HIGH")
            elif help_pct > 80:
                self.log_anomaly(name, "TOO_MUCH_HELP", f"{help_pct:.1f}% HELP (déséquilibré)", "MEDIUM")
            
            if hub_pct > 95:
                self.log_anomaly(name, "TOO_MUCH_HUB", f"{hub_pct:.1f}% HUB (quasi-monopole)", "HIGH")
        
        # 3. Vérifier les durées
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN duration_seconds > 0 THEN 1 END) as valid_durations,
                COUNT(CASE WHEN duration_seconds = 0 OR duration_seconds IS NULL THEN 1 END) as invalid_durations,
                AVG(duration_seconds) as avg_duration,
                MAX(duration_seconds) as max_duration
            FROM video WHERE concurrent_id = ?
        """, (competitor_id,))
        
        valid_durations, invalid_durations, avg_duration, max_duration = cursor.fetchone()
        
        if invalid_durations > 0:
            percentage = (invalid_durations / video_count) * 100
            self.log_anomaly(name, "INVALID_DURATIONS", f"{invalid_durations} vidéos ({percentage:.1f}%) sans durée", "MEDIUM")
        
        if avg_duration and avg_duration > 0:
            avg_minutes = avg_duration / 60
            self.log(f"   ⏱️ Durée moyenne: {avg_minutes:.1f} min")
            
            # Détection de durées aberrantes
            if avg_minutes > 60:
                self.log_anomaly(name, "EXTREMELY_LONG_VIDEOS", f"Durée moyenne {avg_minutes:.1f} min (suspicieusement long)", "MEDIUM")
            elif avg_minutes < 0.5:
                self.log_anomaly(name, "EXTREMELY_SHORT_VIDEOS", f"Durée moyenne {avg_minutes:.1f} min (suspicieusement court)", "MEDIUM")
        else:
            self.log_anomaly(name, "NO_DURATION_DATA", "Aucune donnée de durée valide", "HIGH")
        
        # 4. Vérifier les dates
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT DATE(published_at)) as distinct_dates,
                MIN(published_at) as earliest_date,
                MAX(published_at) as latest_date,
                COUNT(CASE WHEN DATE(published_at) IN ('2025-07-05', '2025-01-07', '2025-07-11') THEN 1 END) as suspicious_dates
            FROM video WHERE concurrent_id = ?
        """, (competitor_id,))
        
        distinct_dates, earliest, latest, suspicious = cursor.fetchone()
        
        if suspicious > 0:
            percentage = (suspicious / video_count) * 100
            self.log_anomaly(name, "CORRUPTED_DATES", f"{suspicious} vidéos ({percentage:.1f}%) avec dates d'import suspectes", "HIGH")
        
        if distinct_dates < 3 and video_count > 10:
            self.log_anomaly(name, "DATE_UNIFORMITY", f"Seulement {distinct_dates} dates distinctes pour {video_count} vidéos", "MEDIUM")
        
        # 5. Vérifier les playlists
        cursor.execute("SELECT COUNT(*) FROM playlist WHERE concurrent_id = ?", (competitor_id,))
        playlist_count = cursor.fetchone()[0]
        
        self.log(f"   📋 {playlist_count} playlists")
        
        if playlist_count == 0:
            self.log_anomaly(name, "NO_PLAYLISTS", "Aucune playlist en base", "MEDIUM")
        elif playlist_count > 100:
            self.log_anomaly(name, "TOO_MANY_PLAYLISTS", f"{playlist_count} playlists (potentiellement excessif)", "LOW")
    
    def analyze_competitor_detailed_metrics(self, conn, competitor_id, name):
        """Analyse détaillée des métriques avec calculs avancés"""
        
        cursor = conn.cursor()
        
        # Récupérer toutes les vidéos
        cursor.execute("""
            SELECT video_id, title, view_count, like_count, comment_count, 
                   duration_seconds, published_at, category
            FROM video 
            WHERE concurrent_id = ?
            ORDER BY view_count DESC
        """, (competitor_id,))
        
        videos = cursor.fetchall()
        
        if not videos:
            return
        
        # Calculs de métriques avancées
        view_counts = [v[2] for v in videos if v[2] and v[2] > 0]
        like_counts = [v[3] for v in videos if v[3] and v[3] > 0]
        durations = [v[5] for v in videos if v[5] and v[5] > 0]
        
        # Analyse des vues
        if view_counts:
            avg_views = sum(view_counts) / len(view_counts)
            max_views = max(view_counts)
            min_views = min(view_counts)
            
            self.log(f"   👁️ Vues: {avg_views:.0f} moy, {max_views:,} max, {min_views:,} min")
            
            # Détection d'anomalies de vues
            if avg_views < 10:
                self.log_anomaly(name, "VERY_LOW_VIEWS", f"Moyenne {avg_views:.0f} vues (très faible)", "MEDIUM")
            elif avg_views > 1000000:
                self.log_anomaly(name, "VERY_HIGH_VIEWS", f"Moyenne {avg_views:.0f} vues (exceptionnellement élevé)", "LOW")
            
            # Ratio min/max suspect
            if max_views > 0 and min_views / max_views < 0.001:
                ratio = min_views / max_views
                self.log_anomaly(name, "EXTREME_VIEW_VARIANCE", f"Ratio min/max: {ratio:.6f} (variance extrême)", "LOW")
        
        # Analyse de l'engagement
        if view_counts and like_counts:
            total_views = sum(view_counts)
            total_likes = sum(like_counts)
            engagement_rate = (total_likes / total_views) * 100 if total_views > 0 else 0
            
            self.log(f"   ❤️ Engagement: {engagement_rate:.3f}% ({total_likes:,} likes sur {total_views:,} vues)")
            
            if engagement_rate < 0.1:
                self.log_anomaly(name, "LOW_ENGAGEMENT", f"Taux d'engagement {engagement_rate:.3f}% très faible", "MEDIUM")
            elif engagement_rate > 10:
                self.log_anomaly(name, "SUSPICIOUSLY_HIGH_ENGAGEMENT", f"Taux d'engagement {engagement_rate:.3f}% suspicieusement élevé", "LOW")
        
        # Analyse des shorts
        if durations:
            shorts_count = len([d for d in durations if d <= 60])
            regular_count = len(durations) - shorts_count
            shorts_percentage = (shorts_count / len(durations)) * 100
            
            self.log(f"   📱 Shorts: {shorts_count} ({shorts_percentage:.1f}%), Réguliers: {regular_count}")
            
            if shorts_percentage == 100 and len(durations) > 5:
                self.log_anomaly(name, "ONLY_SHORTS", "100% de shorts uniquement", "LOW")
            elif shorts_percentage == 0 and len(durations) > 10:
                self.log_anomaly(name, "NO_SHORTS", "Aucun short créé", "LOW")
        
        # Analyse de la fréquence de publication
        dates_with_videos = []
        for video in videos:
            if video[6]:  # published_at
                try:
                    date = datetime.fromisoformat(video[6].replace('Z', '+00:00'))
                    dates_with_videos.append(date)
                except:
                    pass
        
        if len(dates_with_videos) >= 2:
            dates_with_videos.sort()
            date_span = (dates_with_videos[-1] - dates_with_videos[0]).days
            
            if date_span > 0:
                frequency_per_week = (len(dates_with_videos) / date_span) * 7
                self.log(f"   📅 Fréquence: {frequency_per_week:.2f} vidéos/semaine sur {date_span} jours")
                
                if frequency_per_week > 50:
                    self.log_anomaly(name, "IMPOSSIBLE_FREQUENCY", f"{frequency_per_week:.1f} vidéos/semaine (impossible)", "HIGH")
                elif frequency_per_week < 0.1 and len(videos) > 5:
                    self.log_anomaly(name, "VERY_LOW_FREQUENCY", f"{frequency_per_week:.2f} vidéos/semaine (très inactif)", "LOW")
    
    def apply_intelligent_fixes(self, conn, competitor_id, name, channel_id):
        """Appliquer des corrections intelligentes basées sur les anomalies détectées"""
        
        # Récupérer les anomalies pour ce concurrent
        competitor_anomalies = [a for a in self.anomalies_found if a['competitor'] == name]
        
        if not competitor_anomalies:
            self.log(f"   ✅ Aucune anomalie détectée pour {name}")
            return
        
        self.log(f"   🎯 {len(competitor_anomalies)} anomalies à traiter pour {name}")
        
        cursor = conn.cursor()
        
        for anomaly in competitor_anomalies:
            anomaly_type = anomaly['type']
            
            if anomaly_type == "CORRUPTED_DATES":
                self.fix_corrupted_dates(cursor, competitor_id, name)
            
            elif anomaly_type == "INVALID_DURATIONS":
                self.fix_invalid_durations(cursor, competitor_id, name, channel_id)
            
            elif anomaly_type == "ZERO_HERO":
                self.fix_zero_hero_content(cursor, competitor_id, name)
            
            elif anomaly_type == "ZERO_HELP":
                self.fix_zero_help_content(cursor, competitor_id, name)
            
            elif anomaly_type == "UNCATEGORIZED_VIDEOS":
                self.fix_uncategorized_videos(cursor, competitor_id, name)
            
            elif anomaly_type == "NO_PLAYLISTS":
                self.fix_missing_playlists(cursor, competitor_id, name, channel_id)
        
        conn.commit()
    
    def fix_corrupted_dates(self, cursor, competitor_id, name):
        """Corriger les dates corrompues"""
        
        # Utiliser youtube_published_at quand disponible
        cursor.execute("""
            UPDATE video 
            SET published_at = youtube_published_at
            WHERE concurrent_id = ?
            AND DATE(published_at) IN ('2025-07-05', '2025-01-07', '2025-07-11')
            AND youtube_published_at IS NOT NULL
            AND youtube_published_at != ''
        """, (competitor_id,))
        
        fixed_count = cursor.rowcount
        
        if fixed_count > 0:
            self.log_fix(name, "DATE_CORRECTION", f"{fixed_count} dates corrigées via youtube_published_at")
        else:
            self.log_fix(name, "DATE_CORRECTION", "Aucune date alternative trouvée", False)
    
    def fix_invalid_durations(self, cursor, competitor_id, name, channel_id):
        """Corriger les durées invalides via API YouTube"""
        
        # Trouver les vidéos sans durée
        cursor.execute("""
            SELECT video_id FROM video 
            WHERE concurrent_id = ?
            AND (duration_seconds = 0 OR duration_seconds IS NULL)
            LIMIT 50
        """, (competitor_id,))
        
        videos_to_fix = [row[0] for row in cursor.fetchall()]
        
        if not videos_to_fix:
            return
        
        self.log(f"     🔧 Récupération durées via API pour {len(videos_to_fix)} vidéos...")
        
        fixed_count = 0
        
        # Traiter par batch de 50
        for i in range(0, len(videos_to_fix), 50):
            batch = videos_to_fix[i:i+50]
            
            try:
                url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    'part': 'contentDetails',
                    'id': ','.join(batch),
                    'key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                for item in data.get('items', []):
                    video_id = item['id']
                    duration_iso = item['contentDetails']['duration']
                    
                    # Parser la durée ISO 8601
                    duration_seconds = self.parse_iso_duration(duration_iso)
                    duration_text = self.seconds_to_duration_text(duration_seconds)
                    is_short = 1 if duration_seconds <= 60 else 0
                    
                    # Mettre à jour en base
                    cursor.execute("""
                        UPDATE video 
                        SET duration_seconds = ?, duration_text = ?, is_short = ?
                        WHERE video_id = ? AND concurrent_id = ?
                    """, (duration_seconds, duration_text, is_short, video_id, competitor_id))
                    
                    fixed_count += 1
                    
            except Exception as e:
                self.log(f"     ❌ Erreur API pour batch: {e}")
                continue
        
        if fixed_count > 0:
            self.log_fix(name, "DURATION_FIX", f"{fixed_count} durées récupérées via API")
        else:
            self.log_fix(name, "DURATION_FIX", "Échec récupération API", False)
    
    def fix_zero_hero_content(self, cursor, competitor_id, name):
        """Corriger l'absence de contenu HERO"""
        
        # Identifier les vidéos top performance pour reclassification
        cursor.execute("""
            SELECT id, title, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            AND category = 'hub'
            AND (is_human_validated = 0 OR is_human_validated IS NULL)
            ORDER BY view_count DESC
            LIMIT 5
        """, (competitor_id,))
        
        candidates = cursor.fetchall()
        corrections = 0
        
        for video_id, title, view_count, duration in candidates:
            if self.is_hero_worthy_content(title, view_count, name):
                cursor.execute("""
                    UPDATE video 
                    SET category = 'hero',
                        classification_source = 'anomaly_zero_hero_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                corrections += 1
                self.log(f"     🎯 HERO: '{title[:40]}...' ({view_count:,} vues)")
        
        if corrections > 0:
            self.log_fix(name, "ZERO_HERO_FIX", f"{corrections} vidéos reclassifiées en HERO")
        else:
            self.log_fix(name, "ZERO_HERO_FIX", "Aucun contenu approprié trouvé", False)
    
    def fix_zero_help_content(self, cursor, competitor_id, name):
        """Corriger l'absence de contenu HELP"""
        
        # Patterns HELP multilingues
        help_patterns = [
            'guide', 'how to', 'tutorial', 'tip', 'tips', 'advice', 'anleitung',
            'ratgeber', 'hilfe', 'step by step', 'budget', 'cost', 'price',
            'booking', 'reservation', 'packing', 'checklist', 'planning',
            'museum', 'tour', 'visit', 'walk', 'guide', 'discover'
        ]
        
        # Identifier les vidéos HUB qui devraient être HELP
        corrections = 0
        
        for pattern in help_patterns:
            cursor.execute("""
                SELECT id, title FROM video 
                WHERE concurrent_id = ?
                AND category = 'hub'
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
                AND LOWER(title) LIKE ?
                LIMIT 10
            """, (competitor_id, f'%{pattern}%'))
            
            candidates = cursor.fetchall()
            
            for video_id, title in candidates:
                cursor.execute("""
                    UPDATE video 
                    SET category = 'help',
                        classification_source = 'anomaly_zero_help_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                corrections += 1
                self.log(f"     🆘 HELP: '{title[:40]}...' (pattern: {pattern})")
                
                if corrections >= 20:  # Limite pour éviter sur-correction
                    break
            
            if corrections >= 20:
                break
        
        if corrections > 0:
            self.log_fix(name, "ZERO_HELP_FIX", f"{corrections} vidéos reclassifiées en HELP")
        else:
            self.log_fix(name, "ZERO_HELP_FIX", "Aucun contenu HELP détecté", False)
    
    def fix_uncategorized_videos(self, cursor, competitor_id, name):
        """Classifier les vidéos non catégorisées"""
        
        cursor.execute("""
            SELECT id, title, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            AND (category IS NULL OR category = '' OR category = 'uncategorized')
            ORDER BY view_count DESC
            LIMIT 50
        """, (competitor_id,))
        
        uncategorized = cursor.fetchall()
        classified_count = 0
        
        for video_id, title, view_count, duration in uncategorized:
            category = self.smart_classify_video(title, view_count, duration, name)
            
            if category:
                cursor.execute("""
                    UPDATE video 
                    SET category = ?, 
                        classification_source = 'anomaly_classification_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (category, video_id))
                classified_count += 1
                self.log(f"     📂 {category.upper()}: '{title[:40]}...'")
        
        if classified_count > 0:
            self.log_fix(name, "UNCATEGORIZED_FIX", f"{classified_count} vidéos classifiées")
        else:
            self.log_fix(name, "UNCATEGORIZED_FIX", "Aucune classification automatique possible", False)
    
    def fix_missing_playlists(self, cursor, competitor_id, name, channel_id):
        """Importer les playlists manquantes via API"""
        
        if not channel_id:
            self.log_fix(name, "PLAYLIST_IMPORT", "Pas de channel_id disponible", False)
            return
        
        self.log(f"     📡 Import playlists via API pour {channel_id}...")
        
        try:
            playlists = self.get_channel_playlists(channel_id)
            imported_count = 0
            
            for playlist in playlists:
                playlist_id = playlist['id']
                title = playlist['title']
                video_count = int(playlist['video_count'])
                
                # Vérifier si existe déjà
                cursor.execute("SELECT id FROM playlist WHERE playlist_id = ?", (playlist_id,))
                if cursor.fetchone():
                    continue
                
                # Insérer nouvelle playlist
                cursor.execute("""
                    INSERT INTO playlist (
                        concurrent_id, playlist_id, name, description, 
                        thumbnail_url, video_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    competitor_id, playlist_id, title, playlist['description'],
                    playlist['thumbnail_url'], video_count
                ))
                imported_count += 1
                self.log(f"     📋 Playlist: '{title}' ({video_count} vidéos)")
            
            if imported_count > 0:
                self.log_fix(name, "PLAYLIST_IMPORT", f"{imported_count} playlists importées via API")
            else:
                self.log_fix(name, "PLAYLIST_IMPORT", "Aucune nouvelle playlist trouvée", False)
                
        except Exception as e:
            self.log_fix(name, "PLAYLIST_IMPORT", f"Erreur API: {e}", False)
    
    def get_channel_playlists(self, channel_id):
        """Récupérer les playlists via API YouTube"""
        playlists = []
        next_page_token = None
        
        while True:
            url = "https://www.googleapis.com/youtube/v3/playlists"
            params = {
                'part': 'snippet,contentDetails',
                'channelId': channel_id,
                'maxResults': 50,
                'key': self.api_key
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                break
            
            data = response.json()
            
            for item in data.get('items', []):
                playlist_info = {
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet'].get('description', ''),
                    'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                    'video_count': item['contentDetails']['itemCount'],
                    'published_at': item['snippet']['publishedAt']
                }
                playlists.append(playlist_info)
            
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
        
        return playlists
    
    def smart_classify_video(self, title, view_count, duration, competitor_name):
        """Classification intelligente d'une vidéo"""
        
        title_lower = title.lower() if title else ''
        
        # HERO keywords
        hero_keywords = [
            'destination', 'discover', 'entdecken', 'explore', 'journey', 'adventure',
            'beautiful', 'amazing', 'stunning', 'dream', 'paradise', 'luxury',
            'sehnsuchtsorte', 'traumhaft', 'wunderschön', 'breathtaking'
        ]
        
        # HELP keywords
        help_keywords = [
            'how to', 'guide', 'tutorial', 'tip', 'tips', 'advice', 'anleitung',
            'ratgeber', 'hilfe', 'step by step', 'budget', 'cost', 'price',
            'booking', 'reservation', 'packing', 'checklist', 'planning',
            'museum', 'tour', 'visit', 'walk'
        ]
        
        # Classification par priorité
        if any(keyword in title_lower for keyword in hero_keywords):
            return 'hero'
        elif any(keyword in title_lower for keyword in help_keywords):
            return 'help'
        elif view_count and view_count > 100000:
            return 'hero'  # Performance élevée = contenu inspirationnel
        elif duration and duration < 60:
            return 'hero'  # Shorts = souvent contenu marque
        else:
            return 'hub'  # Par défaut
    
    def is_hero_worthy_content(self, title, view_count, competitor_name):
        """Déterminer si le contenu mérite d'être HERO"""
        
        title_lower = title.lower() if title else ''
        
        # Contenu inspirationnel évident
        inspirational_words = [
            'amazing', 'beautiful', 'stunning', 'incredible', 'breathtaking',
            'paradise', 'dream', 'luxury', 'exclusive', 'premium',
            'wunderschön', 'traumhaft', 'fantastisch'
        ]
        
        # Performance élevée
        high_performance = view_count and view_count > 50000
        
        # Contenu inspirationnel
        inspirational_content = any(word in title_lower for word in inspirational_words)
        
        return high_performance or inspirational_content
    
    def parse_iso_duration(self, duration):
        """Parser durée ISO 8601 en secondes"""
        if not duration.startswith('PT'):
            return 0
        
        duration = duration[2:]
        hours = minutes = seconds = 0
        
        if 'H' in duration:
            hours = int(duration.split('H')[0])
            duration = duration.split('H')[1]
        
        if 'M' in duration:
            minutes = int(duration.split('M')[0])
            duration = duration.split('M')[1]
        
        if 'S' in duration:
            seconds = int(duration.split('S')[0])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def seconds_to_duration_text(self, total_seconds):
        """Convertir secondes en format HH:MM:SS"""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def generate_final_report(self):
        """Générer le rapport final complet"""
        
        self.log("\n" + "🎯" * 40)
        self.log("📊 RAPPORT FINAL - INTELLIGENT ANOMALY DETECTOR")
        self.log("🎯" * 40)
        
        # Statistiques globales
        total_anomalies = len(self.anomalies_found)
        total_fixes = len(self.fixes_applied)
        successful_fixes = len([f for f in self.fixes_applied if f['success']])
        
        self.log(f"\n📈 STATISTIQUES GLOBALES:")
        self.log(f"   🔍 Anomalies détectées: {total_anomalies}")
        self.log(f"   🔧 Corrections tentées: {total_fixes}")
        self.log(f"   ✅ Corrections réussies: {successful_fixes}")
        self.log(f"   📊 Taux de succès: {(successful_fixes/total_fixes*100):.1f}%" if total_fixes > 0 else "   📊 Taux de succès: N/A")
        
        # Anomalies par type
        anomaly_types = {}
        for anomaly in self.anomalies_found:
            atype = anomaly['type']
            anomaly_types[atype] = anomaly_types.get(atype, 0) + 1
        
        self.log(f"\n🔍 ANOMALIES PAR TYPE:")
        for atype, count in sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True):
            self.log(f"   {atype}: {count}")
        
        # Corrections par type
        fix_types = {}
        for fix in self.fixes_applied:
            ftype = fix['type']
            fix_types[ftype] = fix_types.get(ftype, 0) + 1
        
        self.log(f"\n🔧 CORRECTIONS PAR TYPE:")
        for ftype, count in sorted(fix_types.items(), key=lambda x: x[1], reverse=True):
            self.log(f"   {ftype}: {count}")
        
        # Concurrents les plus problématiques
        competitor_issues = {}
        for anomaly in self.anomalies_found:
            comp = anomaly['competitor']
            competitor_issues[comp] = competitor_issues.get(comp, 0) + 1
        
        self.log(f"\n🚨 TOP 10 CONCURRENTS AVEC LE PLUS D'ANOMALIES:")
        for comp, count in sorted(competitor_issues.items(), key=lambda x: x[1], reverse=True)[:10]:
            self.log(f"   {comp}: {count} anomalies")
        
        # Sauvegarder le rapport détaillé
        report_data = {
            'analysis_time': datetime.now().isoformat(),
            'summary': {
                'total_anomalies': total_anomalies,
                'total_fixes': total_fixes,
                'successful_fixes': successful_fixes,
                'success_rate': (successful_fixes/total_fixes*100) if total_fixes > 0 else 0
            },
            'anomalies_by_type': anomaly_types,
            'fixes_by_type': fix_types,
            'competitor_issues': competitor_issues,
            'detailed_anomalies': self.anomalies_found,
            'detailed_fixes': self.fixes_applied,
            'verbose_log': self.verbose_log
        }
        
        report_filename = f"intelligent_anomaly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"\n📄 Rapport détaillé sauvegardé: {report_filename}")
        self.log("\n🎯" * 40)
        self.log("✅ ANALYSE INTELLIGENTE TERMINÉE")
        self.log("🎯" * 40)

def main():
    """Point d'entrée principal"""
    
    print("🔍 INTELLIGENT ANOMALY DETECTOR & FIXER")
    print("=" * 50)
    print("Ce script scanne tous les concurrents et détecte intelligemment:")
    print("• Distribution HHH aberrante (0%, 100%, déséquilibres)")
    print("• Durées N/A ou incohérentes")
    print("• Fréquences impossibles") 
    print("• Dates corrompues")
    print("• Classifications manquantes")
    print("• Métriques absurdes")
    print()
    print("⚠️ MODE ULTRA-VERBOSE: Toutes les actions sont expliquées")
    print()
    
    confirm = input("Lancer l'analyse intelligente ? (y/N): ").lower().strip()
    
    if confirm == 'y':
        detector = IntelligentAnomalyDetector()
        detector.run_complete_analysis()
    else:
        print("❌ Analyse annulée")

if __name__ == "__main__":
    main()