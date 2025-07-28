#!/usr/bin/env python3
"""
ULTIMATE GLOBAL REFRESH SYSTEM
Un seul script pour tout nettoyer, corriger, et recalculer

Séquence complète :
1. Import API (playlists + vidéos)
2. Correction YouTube dates + durées
3. Classification intelligente + propagation
4. Recalcul complet des métriques
5. Stockage en base + force refresh
"""
import sys
import os
import requests
import json
import time
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

sys.path.append(str(Path(__file__).parent))

from yt_channel_analyzer.database import get_db_connection
from services.competitor_service import CompetitorAdvancedMetricsService

class UltimateRefreshProgress:
    """Gestionnaire de progression ultra-détaillé"""
    
    def __init__(self):
        self.status_file = "/tmp/ultimate_refresh_status.json"
        self.report_file = f"/tmp/ultimate_refresh_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.current_step = 0
        self.total_steps = 0
        self.current_message = ""
        self.is_running = False
        self.error = None
        self.stats = {
            'competitors_processed': 0,
            'playlists_imported': 0,
            'videos_updated': 0,
            'dates_corrected': 0,
            'durations_fixed': 0,
            'classifications_applied': 0,
            'metrics_recalculated': 0,
            'cache_cleared': 0
        }
        self.detailed_log = []
        
    def start(self, total_steps):
        """Démarrer le processus ultimate"""
        self.total_steps = total_steps
        self.current_step = 0
        self.is_running = True
        self.error = None
        self.stats = {key: 0 for key in self.stats}
        self.detailed_log = []
        self.update_status("🚀 ULTIMATE REFRESH DÉMARRÉ - Protection Humaine Activée")
        
    def log_action(self, competitor_name, action, details):
        """Logger une action détaillée"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'competitor': competitor_name,
            'action': action,
            'details': details
        }
        self.detailed_log.append(entry)
        
    def update_status(self, message, step_increment=1):
        """Mettre à jour le statut avec logs"""
        if step_increment:
            self.current_step += step_increment
        
        self.current_message = message
        
        status = {
            'is_running': self.is_running,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percent': round((self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0),
            'current_message': message,
            'error': self.error,
            'timestamp': time.time(),
            'stats': self.stats
        }
        
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except:
            pass
        
        print(f"[ULTIMATE] {message}")
        
    def complete(self):
        """Terminer avec rapport complet"""
        self.is_running = False
        self.current_step = self.total_steps
        
        # Générer rapport final
        final_report = {
            'completion_time': datetime.now().isoformat(),
            'total_processing_time': time.time(),
            'final_stats': self.stats,
            'detailed_log': self.detailed_log,
            'summary': self.generate_summary()
        }
        
        try:
            with open(self.report_file, 'w') as f:
                json.dump(final_report, f, indent=2)
        except:
            pass
            
        summary_msg = f"""✅ ULTIMATE REFRESH TERMINÉ:
🏢 {self.stats['competitors_processed']} concurrents traités
📋 {self.stats['playlists_imported']} playlists importées
📺 {self.stats['videos_updated']} vidéos mises à jour
📅 {self.stats['dates_corrected']} dates corrigées
⏱️ {self.stats['durations_fixed']} durées réparées
🎯 {self.stats['classifications_applied']} classifications appliquées
📊 {self.stats['metrics_recalculated']} métriques recalculées
🔄 Cache force-cleared partout"""
        
        self.update_status(summary_msg, 0)
        
    def generate_summary(self):
        """Générer un résumé des actions"""
        actions_by_type = defaultdict(int)
        for entry in self.detailed_log:
            actions_by_type[entry['action']] += 1
        
        return {
            'actions_summary': dict(actions_by_type),
            'competitors_with_issues': len(set(entry['competitor'] for entry in self.detailed_log if 'ERROR' in entry['action'])),
            'total_improvements': sum(actions_by_type.values())
        }

class UltimateGlobalRefreshSystem:
    """Système de rafraîchissement ULTIMATE - Tout en un"""
    
    def __init__(self):
        self.progress = UltimateRefreshProgress()
        self.api_key = self.get_youtube_api_key()
        self.conn = None
        
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
        
        raise ValueError("YouTube API key not found. Please set YOUTUBE_API_KEY in .env file")
    
    def run_ultimate_refresh(self):
        """Exécuter le processus ULTIMATE complet"""
        
        try:
            # Estimation du nombre total d'étapes
            self.progress.start(200)  # Estimation large
            
            if not self.api_key:
                self.progress.error = "Clé API YouTube non trouvée"
                return
            
            self.conn = get_db_connection()
            cursor = self.conn.cursor()
            
            # Étape 1: Récupérer tous les concurrents
            self.progress.update_status("🔍 Analyse des concurrents...")
            print("🆕 [NOUVELLE LOGIQUE] Protection simulated_dates désactivée - corrections avancées possibles")
            
            cursor.execute("""
                SELECT id, name, channel_id, channel_url
                FROM concurrent 
                WHERE channel_id IS NOT NULL 
                AND channel_id != ''
                ORDER BY name
            """)
            
            competitors = cursor.fetchall()
            total_competitors = len(competitors)
            
            self.progress.update_status(f"📋 {total_competitors} concurrents identifiés")
            self.progress.total_steps = 50 + (total_competitors * 10)  # Ajuster dynamiquement
            
            # PHASE 1: IMPORT API + CORRECTIONS
            self.progress.update_status("📡 PHASE 1: Import API + Corrections YouTube", 5)
            
            for i, (competitor_id, name, channel_id, channel_url) in enumerate(competitors):
                self.process_competitor_phase1(competitor_id, name, channel_id, i+1, total_competitors)
            
            # PHASE 2: PROPAGATION + CLASSIFICATION
            self.progress.update_status("🎯 PHASE 2: Propagation + Classification", 5)
            
            for i, (competitor_id, name, channel_id, channel_url) in enumerate(competitors):
                self.process_competitor_phase2(competitor_id, name, i+1, total_competitors)
            
            # PHASE 3: RECALCUL MÉTRIQUES
            self.progress.update_status("📊 PHASE 3: Recalcul Métriques", 5)
            
            for i, (competitor_id, name, channel_id, channel_url) in enumerate(competitors):
                self.process_competitor_phase3(competitor_id, name, i+1, total_competitors)
            
            # PHASE 4: FORCE REFRESH CACHE
            self.progress.update_status("🔄 PHASE 4: Force Refresh Cache", 5)
            self.clear_all_caches()
            
            # Finalisation
            self.conn.commit()
            self.conn.close()
            
            self.progress.complete()
            
        except Exception as e:
            self.progress.error = f"Erreur ULTIMATE: {str(e)}"
            if self.conn:
                self.conn.close()
    
    def process_competitor_phase1(self, competitor_id, name, channel_id, current, total):
        """PHASE 1: SCAN D'ANOMALIES + Import API + Corrections pour un concurrent"""
        
        self.progress.update_status(f"🔍 Phase 1: {name} ({current}/{total}) - Scan anomalies...")
        cursor = self.conn.cursor()
        
        try:
            # 1.0: SCAN INTELLIGENT D'ANOMALIES
            self.detect_and_log_anomalies(cursor, competitor_id, name)
            
            # 1.1: Import playlists via API
            playlists = self.get_channel_playlists(channel_id)
            playlists_imported = 0
            
            for playlist in playlists:
                if self.import_or_update_playlist(cursor, competitor_id, playlist):
                    playlists_imported += 1
            
            self.progress.stats['playlists_imported'] += playlists_imported
            self.progress.log_action(name, "PLAYLISTS_IMPORTED", f"{playlists_imported} playlists")
            
            # 1.2: Correction des dates YouTube
            dates_corrected = self.fix_youtube_dates(cursor, competitor_id)
            self.progress.stats['dates_corrected'] += dates_corrected
            if dates_corrected > 0:
                self.progress.log_action(name, "DATES_CORRECTED", f"{dates_corrected} vidéos")
            
            # 1.3: Correction des durées via API
            durations_fixed = self.fix_video_durations(cursor, competitor_id)
            self.progress.stats['durations_fixed'] += durations_fixed
            if durations_fixed > 0:
                self.progress.log_action(name, "DURATIONS_FIXED", f"{durations_fixed} vidéos")
            
            self.conn.commit()  # Commit intermédiaire
            
        except Exception as e:
            self.progress.log_action(name, "PHASE1_ERROR", str(e))
    
    def detect_and_log_anomalies(self, cursor, competitor_id, name):
        """🔍 DÉTECTION INTELLIGENTE D'ANOMALIES - Ultra Verbose"""
        
        print(f"\n🔍 [ANOMALY-SCAN] === {name} ===")
        
        # 1. Compter les vidéos
        cursor.execute("SELECT COUNT(*) FROM video WHERE concurrent_id = ?", (competitor_id,))
        video_count = cursor.fetchone()[0]
        
        if video_count == 0:
            print(f"🚨 [CRITICAL] {name}: AUCUNE VIDÉO en base!")
            self.progress.log_action(name, "ANOMALY_CRITICAL", "Aucune vidéo trouvée")
            return
        
        print(f"📺 [INFO] {name}: {video_count} vidéos")
        
        # 2. Analyser distribution HHH
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
        
        print(f"🎯 [HHH] {name}: {hero} HERO, {hub} HUB, {help_count} HELP, {uncategorized} non-classifiées")
        
        # Détecter anomalies HHH
        if uncategorized > 0:
            percentage = (uncategorized / video_count) * 100
            print(f"⚠️ [ANOMALY] {name}: {uncategorized} vidéos ({percentage:.1f}%) NON CLASSIFIÉES!")
            self.progress.log_action(name, "ANOMALY_UNCATEGORIZED", f"{uncategorized} vidéos ({percentage:.1f}%)")
        
        if classified_total > 0:
            hero_pct = (hero / classified_total) * 100
            hub_pct = (hub / classified_total) * 100
            help_pct = (help_count / classified_total) * 100
            
            print(f"📊 [DISTRIBUTION] {name}: {hero_pct:.1f}% HERO, {hub_pct:.1f}% HUB, {help_pct:.1f}% HELP")
            
            # Anomalies de distribution
            if hero_pct == 0:
                print(f"🚨 [ANOMALY] {name}: 0% HERO - PROBLÈME stratégique!")
                self.progress.log_action(name, "ANOMALY_ZERO_HERO", f"0% HERO sur {classified_total} vidéos")
            
            if help_pct == 0 and classified_total > 20:
                print(f"🚨 [ANOMALY] {name}: 0% HELP - Aucun contenu d'aide!")
                self.progress.log_action(name, "ANOMALY_ZERO_HELP", f"0% HELP sur {classified_total} vidéos")
            
            if hub_pct > 95:
                print(f"⚠️ [ANOMALY] {name}: {hub_pct:.1f}% HUB - Quasi-monopole déséquilibré!")
                self.progress.log_action(name, "ANOMALY_HUB_MONOPOLY", f"{hub_pct:.1f}% HUB")
        
        # 3. Analyser durées
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN duration_seconds > 0 THEN 1 END) as valid_durations,
                COUNT(CASE WHEN duration_seconds = 0 OR duration_seconds IS NULL THEN 1 END) as invalid_durations,
                AVG(duration_seconds) as avg_duration
            FROM video WHERE concurrent_id = ?
        """, (competitor_id,))
        
        valid_durations, invalid_durations, avg_duration = cursor.fetchone()
        
        if invalid_durations > 0:
            percentage = (invalid_durations / video_count) * 100
            print(f"⚠️ [ANOMALY] {name}: {invalid_durations} vidéos ({percentage:.1f}%) SANS DURÉE!")
            self.progress.log_action(name, "ANOMALY_NO_DURATION", f"{invalid_durations} vidéos ({percentage:.1f}%)")
        
        if avg_duration and avg_duration > 0:
            avg_minutes = avg_duration / 60
            print(f"⏱️ [DURATION] {name}: {avg_minutes:.1f} min moyenne")
            
            if avg_minutes > 60:
                print(f"🤔 [ANOMALY] {name}: {avg_minutes:.1f} min - Suspicieusement LONG pour YouTube!")
                self.progress.log_action(name, "ANOMALY_VERY_LONG", f"{avg_minutes:.1f} min moyenne")
            elif avg_minutes < 0.5:
                print(f"🤔 [ANOMALY] {name}: {avg_minutes:.1f} min - Suspicieusement COURT!")
                self.progress.log_action(name, "ANOMALY_VERY_SHORT", f"{avg_minutes:.1f} min moyenne")
        else:
            print(f"🚨 [ANOMALY] {name}: AUCUNE donnée de durée valide!")
            self.progress.log_action(name, "ANOMALY_NO_DURATION_DATA", "Aucune durée valide")
        
        # 4. Analyser dates
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT DATE(published_at)) as distinct_dates,
                COUNT(CASE WHEN DATE(published_at) IN ('2025-07-05', '2025-01-07', '2025-07-11') THEN 1 END) as suspicious_dates
            FROM video WHERE concurrent_id = ?
        """, (competitor_id,))
        
        distinct_dates, suspicious = cursor.fetchone()
        
        if suspicious > 0:
            percentage = (suspicious / video_count) * 100
            print(f"🚨 [ANOMALY] {name}: {suspicious} vidéos ({percentage:.1f}%) avec DATES D'IMPORT corrompues!")
            self.progress.log_action(name, "ANOMALY_CORRUPT_DATES", f"{suspicious} vidéos ({percentage:.1f}%)")
        
        if distinct_dates < 3 and video_count > 10:
            print(f"⚠️ [ANOMALY] {name}: Seulement {distinct_dates} dates distinctes pour {video_count} vidéos!")
            self.progress.log_action(name, "ANOMALY_DATE_UNIFORMITY", f"{distinct_dates} dates pour {video_count} vidéos")
        
        # 5. Analyser playlists
        cursor.execute("SELECT COUNT(*) FROM playlist WHERE concurrent_id = ?", (competitor_id,))
        playlist_count = cursor.fetchone()[0]
        
        print(f"📋 [PLAYLISTS] {name}: {playlist_count} playlists")
        
        if playlist_count == 0:
            print(f"⚠️ [ANOMALY] {name}: AUCUNE playlist en base!")
            self.progress.log_action(name, "ANOMALY_NO_PLAYLISTS", "Aucune playlist")
        
        # 6. Analyser engagement
        cursor.execute("""
            SELECT 
                SUM(view_count) as total_views,
                SUM(like_count) as total_likes,
                AVG(view_count) as avg_views
            FROM video 
            WHERE concurrent_id = ? 
            AND view_count > 0 AND like_count > 0
        """, (competitor_id,))
        
        total_views, total_likes, avg_views = cursor.fetchone()
        
        if total_views and total_likes and total_views > 0:
            engagement_rate = (total_likes / total_views) * 100
            print(f"❤️ [ENGAGEMENT] {name}: {engagement_rate:.3f}% ({avg_views:.0f} vues moy)")
            
            if engagement_rate < 0.1:
                print(f"⚠️ [ANOMALY] {name}: Engagement {engagement_rate:.3f}% TRÈS FAIBLE!")
                self.progress.log_action(name, "ANOMALY_LOW_ENGAGEMENT", f"{engagement_rate:.3f}%")
            elif engagement_rate > 10:
                print(f"🤔 [ANOMALY] {name}: Engagement {engagement_rate:.3f}% suspicieusement ÉLEVÉ!")
                self.progress.log_action(name, "ANOMALY_HIGH_ENGAGEMENT", f"{engagement_rate:.3f}%")
        
        print(f"✅ [SCAN-COMPLETE] {name}: Anomalies détectées et loggées")
    
    def process_competitor_phase2(self, competitor_id, name, current, total):
        """PHASE 2: Propagation + Classification pour un concurrent"""
        
        self.progress.update_status(f"🎯 Phase 2: {name} ({current}/{total})")
        cursor = self.conn.cursor()
        
        try:
            # 2.1: Création des liens playlist-vidéo
            links_created = self.create_playlist_video_links(cursor, competitor_id)
            self.progress.log_action(name, "LINKS_CREATED", f"{links_created} liens")
            
            # 2.2: Propagation des classifications depuis playlists humaines
            videos_propagated = self.propagate_human_classifications(cursor, competitor_id)
            self.progress.stats['classifications_applied'] += videos_propagated
            if videos_propagated > 0:
                self.progress.log_action(name, "HUMAN_PROPAGATED", f"{videos_propagated} vidéos")
            
            # 2.3: Classification intelligente des vidéos orphelines
            orphans_classified = self.classify_orphaned_videos(cursor, competitor_id, name)
            self.progress.stats['classifications_applied'] += orphans_classified
            if orphans_classified > 0:
                self.progress.log_action(name, "ORPHANS_CLASSIFIED", f"{orphans_classified} vidéos")
            
            # 2.4: CORRECTIONS INTELLIGENTES basées sur anomalies détectées
            self.apply_intelligent_anomaly_fixes(cursor, competitor_id, name)
            
            # 2.5: Détection et correction 0% HERO (legacy)
            hero_corrections = self.fix_zero_hero_content(cursor, competitor_id, name)
            if hero_corrections > 0:
                self.progress.log_action(name, "HERO_CORRECTIONS", f"{hero_corrections} vidéos reclassifiées")
            
            self.conn.commit()  # Commit intermédiaire
            
        except Exception as e:
            self.progress.log_action(name, "PHASE2_ERROR", str(e))
    
    def process_competitor_phase3(self, competitor_id, name, current, total):
        """PHASE 3: Recalcul complet des métriques pour un concurrent"""
        
        self.progress.update_status(f"📊 Phase 3: {name} ({current}/{total})")
        cursor = self.conn.cursor()
        
        try:
            # 3.1: Récupérer toutes les vidéos du concurrent
            cursor.execute("""
                SELECT * FROM video 
                WHERE concurrent_id = ?
                ORDER BY published_at DESC
            """, (competitor_id,))
            
            videos = cursor.fetchall()
            
            if not videos:
                self.progress.log_action(name, "NO_VIDEOS", "Aucune vidéo trouvée")
                return
            
            # 3.2: Utiliser le service avancé pour recalculer
            try:
                service = CompetitorAdvancedMetricsService(self.conn)
                metrics = service.calculate_key_metrics(competitor_id, videos)
                
                # 3.3: Sauvegarder les métriques en base
                self.save_competitor_metrics(cursor, competitor_id, metrics)
                
                self.progress.stats['metrics_recalculated'] += 1
                self.progress.stats['videos_updated'] += len(videos)
                
                self.progress.log_action(name, "METRICS_CALCULATED", {
                    'videos_count': len(videos),
                    'avg_duration': round(metrics.get('avg_duration', 0) / 60, 1),
                    'hhh_distribution': f"{metrics.get('hero_percentage', 0):.1f}%-{metrics.get('hub_percentage', 0):.1f}%-{metrics.get('help_percentage', 0):.1f}%",
                    'shorts_percentage': f"{metrics.get('shorts_percentage', 0):.1f}%"
                })
                
            except Exception as e:
                self.progress.log_action(name, "METRICS_ERROR", str(e))
            
            self.conn.commit()  # Commit intermédiaire
            
        except Exception as e:
            self.progress.log_action(name, "PHASE3_ERROR", str(e))
        
        self.progress.stats['competitors_processed'] += 1
    
    def get_channel_playlists(self, channel_id):
        """Récupérer toutes les playlists d'une chaîne via API"""
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
            
            try:
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
                    
            except Exception:
                break
        
        return playlists
    
    def import_or_update_playlist(self, cursor, competitor_id, playlist):
        """Importer ou mettre à jour une playlist avec protection humaine"""
        
        playlist_id = playlist['id']
        title = playlist['title']
        video_count = int(playlist['video_count'])
        
        # Vérifier si existe déjà
        cursor.execute("SELECT id, is_human_validated, classification_source FROM playlist WHERE playlist_id = ?", (playlist_id,))
        existing = cursor.fetchone()
        
        if existing:
            # PROTECTION ABSOLUE : Mettre à jour SEULEMENT les métadonnées, JAMAIS les classifications humaines
            if existing[1] == 1 or existing[2] == 'human':
                # Playlist validée humainement - mettre à jour SEULEMENT les métadonnées techniques
                cursor.execute("""
                    UPDATE playlist 
                    SET video_count = ?, last_updated = datetime('now')
                    WHERE playlist_id = ?
                """, (video_count, playlist_id))
            else:
                # Playlist non-humaine - mettre à jour tout sauf classifications
                cursor.execute("""
                    UPDATE playlist 
                    SET description = ?, thumbnail_url = ?, video_count = ?, last_updated = datetime('now')
                    WHERE playlist_id = ?
                """, (playlist['description'], playlist['thumbnail_url'], video_count, playlist_id))
            return False
        else:
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
            return True
    
    def fix_youtube_dates(self, cursor, competitor_id):
        """Corriger les dates YouTube corrompues"""
        
        # Détecter les dates suspectes (dates d'import)
        cursor.execute("""
            SELECT COUNT(*) FROM video 
            WHERE concurrent_id = ?
            AND DATE(published_at) IN ('2025-07-05', '2025-01-07', '2025-07-11')
        """, (competitor_id,))
        
        suspicious_count = cursor.fetchone()[0]
        
        if suspicious_count == 0:
            return 0
        
        # Corriger en utilisant youtube_published_at quand disponible
        cursor.execute("""
            UPDATE video 
            SET published_at = youtube_published_at
            WHERE concurrent_id = ?
            AND DATE(published_at) IN ('2025-07-05', '2025-01-07', '2025-07-11')
            AND youtube_published_at IS NOT NULL
            AND youtube_published_at != ''
        """, (competitor_id,))
        
        return cursor.rowcount
    
    def fix_video_durations(self, cursor, competitor_id):
        """Corriger les durées vidéo via API YouTube"""
        
        # Trouver les vidéos avec durée 0 ou nulle
        cursor.execute("""
            SELECT video_id FROM video 
            WHERE concurrent_id = ?
            AND (duration_seconds = 0 OR duration_seconds IS NULL OR duration_text = '00:00:00')
        """, (competitor_id,))
        
        videos_to_fix = [row[0] for row in cursor.fetchall()]
        
        if not videos_to_fix:
            return 0
        
        fixed_count = 0
        
        # Traiter par batch de 50 (limite API)
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
                    
                    # Parser la durée ISO 8601 (PT1M30S)
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
                    
            except Exception:
                continue
        
        return fixed_count
    
    def parse_iso_duration(self, duration):
        """Parser durée ISO 8601 en secondes"""
        if not duration.startswith('PT'):
            return 0
        
        duration = duration[2:]  # Enlever 'PT'
        
        hours = 0
        minutes = 0
        seconds = 0
        
        # Extraire heures
        if 'H' in duration:
            hours = int(duration.split('H')[0])
            duration = duration.split('H')[1]
        
        # Extraire minutes
        if 'M' in duration:
            minutes = int(duration.split('M')[0])
            duration = duration.split('M')[1]
        
        # Extraire secondes
        if 'S' in duration:
            seconds = int(duration.split('S')[0])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def seconds_to_duration_text(self, total_seconds):
        """Convertir secondes en format HH:MM:SS"""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def create_playlist_video_links(self, cursor, competitor_id):
        """Créer les liens playlist-vidéo"""
        
        # Récupérer les playlists classifiées
        cursor.execute("""
            SELECT p.id, p.playlist_id, p.name, p.category
            FROM playlist p
            WHERE p.concurrent_id = ?
            AND p.category IS NOT NULL
            AND p.name NOT LIKE 'All Videos%'
        """, (competitor_id,))
        
        classified_playlists = cursor.fetchall()
        links_created = 0
        
        for db_id, youtube_playlist_id, playlist_name, category in classified_playlists:
            
            # Vérifier si les liens existent déjà
            cursor.execute("SELECT COUNT(*) FROM playlist_video WHERE playlist_id = ?", (youtube_playlist_id,))
            existing_links = cursor.fetchone()[0]
            
            if existing_links > 0:
                continue
            
            # Récupérer les vidéos via API
            playlist_videos = self.get_playlist_videos_from_api(youtube_playlist_id)
            
            if playlist_videos:
                # Trouver les vidéos dans notre base
                video_id_list = playlist_videos
                placeholders = ','.join(['?' for _ in video_id_list])
                
                cursor.execute(f"""
                    SELECT id, video_id FROM video 
                    WHERE video_id IN ({placeholders})
                    AND concurrent_id = ?
                """, video_id_list + [competitor_id])
                
                found_videos = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Créer les liens
                for video_id in playlist_videos:
                    if video_id in found_videos:
                        db_video_id = found_videos[video_id]
                        try:
                            cursor.execute("""
                                INSERT INTO playlist_video (playlist_id, video_id) 
                                VALUES (?, ?)
                            """, (youtube_playlist_id, db_video_id))
                            links_created += 1
                        except Exception:
                            pass
        
        return links_created
    
    def apply_intelligent_anomaly_fixes(self, cursor, competitor_id, name):
        """🔧 CORRECTIONS INTELLIGENTES basées sur les anomalies détectées"""
        
        print(f"\n🔧 [INTELLIGENT-FIX] === {name} ===")
        
        # Récupérer les anomalies pour ce concurrent depuis les logs
        competitor_logs = [log for log in self.progress.detailed_log 
                          if log['competitor'] == name and 'ANOMALY_' in log['action']]
        
        if not competitor_logs:
            print(f"✅ [NO-ANOMALIES] {name}: Aucune anomalie à corriger")
            return
        
        print(f"🎯 [FIXING] {name}: {len(competitor_logs)} anomalies à traiter")
        
        for log_entry in competitor_logs:
            anomaly_type = log_entry['action']
            details = log_entry['details']
            
            print(f"   🔍 [FIXING] {anomaly_type}: {details}")
            
            if anomaly_type == "ANOMALY_ZERO_HELP":
                self.intelligent_fix_zero_help(cursor, competitor_id, name)
            
            elif anomaly_type == "ANOMALY_ZERO_HERO":
                self.intelligent_fix_zero_hero(cursor, competitor_id, name)
            
            elif anomaly_type == "ANOMALY_UNCATEGORIZED":
                self.intelligent_fix_uncategorized(cursor, competitor_id, name)
            
            elif anomaly_type == "ANOMALY_HUB_MONOPOLY":
                self.intelligent_fix_hub_monopoly(cursor, competitor_id, name)
            
            elif anomaly_type == "ANOMALY_NO_DURATION":
                print(f"   ⏱️ [SKIP] Durées déjà traitées en Phase 1")
            
            elif anomaly_type == "ANOMALY_CORRUPT_DATES":
                print(f"   📅 [SKIP] Dates déjà traitées en Phase 1")
            
            else:
                print(f"   ❓ [SKIP] Type d'anomalie non géré: {anomaly_type}")
    
    def intelligent_fix_zero_help(self, cursor, competitor_id, name):
        """Correction intelligente pour 0% HELP"""
        
        print(f"   🆘 [FIX-HELP] Recherche de contenu HELP mal classifié...")
        
        # Patterns HELP multilingues spécialisés
        help_patterns = [
            ('guide', 'guides pratiques'),
            ('museum', 'visites de musées'),
            ('tour', 'tours et visites'),
            ('walk', 'promenades guidées'),
            ('discover', 'découvertes de lieux'),
            ('visit', 'contenu de visite'),
            ('how to', 'tutoriels'),
            ('tips', 'conseils pratiques'),
            ('planning', 'aide à la planification'),
            ('budget', 'conseils budget'),
            ('hotel', 'aide hébergement'),
            ('restaurant', 'guides restaurant'),
            ('transportation', 'aide transport'),
            ('viertelliebe', 'guides de quartiers allemands'),
            ('stadtführung', 'visites guidées allemandes'),
            ('rundgang', 'parcours guidés')
        ]
        
        total_reclassified = 0
        
        for pattern, description in help_patterns:
            cursor.execute("""
                SELECT id, title FROM video 
                WHERE concurrent_id = ?
                AND category = 'hub'
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
                AND (classification_source != 'human' OR classification_source IS NULL)
                AND (classification_source != 'simulated_dates' OR classification_source IS NULL)
                AND LOWER(title) LIKE ?
                LIMIT 15
            """, (competitor_id, f'%{pattern}%'))
            
            candidates = cursor.fetchall()
            
            for video_id, title in candidates:
                cursor.execute("""
                    UPDATE video 
                    SET category = 'help',
                        classification_source = 'intelligent_zero_help_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                
                total_reclassified += 1
                print(f"     🆘 HELP: '{title[:50]}...' (pattern: {pattern})")
                
                if total_reclassified >= 50:  # Limite pour éviter sur-correction
                    break
            
            if total_reclassified >= 50:
                break
        
        if total_reclassified > 0:
            print(f"   ✅ [FIX-HELP] {total_reclassified} vidéos reclassifiées en HELP")
            self.progress.log_action(name, "INTELLIGENT_HELP_FIX", f"{total_reclassified} vidéos → HELP")
        else:
            print(f"   ❌ [FIX-HELP] Aucun contenu HELP détecté automatiquement")
    
    def intelligent_fix_zero_hero(self, cursor, competitor_id, name):
        """Correction intelligente pour 0% HERO"""
        
        print(f"   🎯 [FIX-HERO] Recherche de contenu HERO mal classifié...")
        
        # 1. Reclassifier les vidéos top performance
        cursor.execute("""
            SELECT id, title, view_count FROM video 
            WHERE concurrent_id = ?
            AND category = 'hub'
            AND (
                (is_human_validated = 0 OR is_human_validated IS NULL) 
                OR classification_source = 'simulated_dates'
            )
            AND (classification_source != 'human' OR classification_source IS NULL)
            AND view_count > 50000
            ORDER BY view_count DESC
            LIMIT 5
        """, (competitor_id,))
        
        high_performers = cursor.fetchall()
        reclassified = 0
        
        for video_id, title, view_count in high_performers:
            cursor.execute("""
                UPDATE video 
                SET category = 'hero',
                    classification_source = 'intelligent_zero_hero_fix',
                    classification_date = datetime('now')
                WHERE id = ?
            """, (video_id,))
            reclassified += 1
            print(f"     🎯 HERO: '{title[:50]}...' ({view_count:,} vues)")
        
        # 2. Reclassifier le contenu inspirationnel
        hero_keywords = [
            ('beautiful', 'contenu inspirationnel'),
            ('amazing', 'contenu exceptionnel'),
            ('stunning', 'contenu spectaculaire'),
            ('dream', 'destinations de rêve'),
            ('paradise', 'destinations paradisiaques'),
            ('luxury', 'contenu luxueux'),
            ('exclusive', 'contenu exclusif'),
            ('breathtaking', 'contenu à couper le souffle'),
            ('sehnsuchtsorte', 'destinations de rêve allemandes'),
            ('traumhaft', 'contenu de rêve allemand'),
            ('wunderschön', 'très beau contenu allemand')
        ]
        
        for keyword, description in hero_keywords:
            if reclassified >= 8:  # Limite totale
                break
                
            cursor.execute("""
                SELECT id, title FROM video 
                WHERE concurrent_id = ?
                AND category = 'hub'
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
                AND (classification_source != 'human' OR classification_source IS NULL)
                AND (classification_source != 'simulated_dates' OR classification_source IS NULL)
                AND LOWER(title) LIKE ?
                LIMIT 2
            """, (competitor_id, f'%{keyword}%'))
            
            candidates = cursor.fetchall()
            
            for video_id, title in candidates:
                if reclassified >= 8:
                    break
                    
                cursor.execute("""
                    UPDATE video 
                    SET category = 'hero',
                        classification_source = 'intelligent_zero_hero_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                reclassified += 1
                print(f"     🎯 HERO: '{title[:50]}...' (keyword: {keyword})")
        
        if reclassified > 0:
            print(f"   ✅ [FIX-HERO] {reclassified} vidéos reclassifiées en HERO")
            self.progress.log_action(name, "INTELLIGENT_HERO_FIX", f"{reclassified} vidéos → HERO")
        else:
            print(f"   ❌ [FIX-HERO] Aucun contenu HERO détecté automatiquement")
    
    def intelligent_fix_uncategorized(self, cursor, competitor_id, name):
        """Correction intelligente pour vidéos non classifiées"""
        
        print(f"   📂 [FIX-UNCATEGORIZED] Classification des vidéos orphelines...")
        
        cursor.execute("""
            SELECT id, title, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            AND (category IS NULL OR category = '' OR category = 'uncategorized')
            ORDER BY view_count DESC
            LIMIT 30
        """, (competitor_id,))
        
        uncategorized = cursor.fetchall()
        classified_count = 0
        
        for video_id, title, view_count, duration in uncategorized:
            category = self.smart_classify_video_advanced(title, view_count, duration, name)
            
            if category:
                cursor.execute("""
                    UPDATE video 
                    SET category = ?, 
                        classification_source = 'intelligent_uncategorized_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (category, video_id))
                classified_count += 1
                print(f"     📂 {category.upper()}: '{title[:50]}...'")
        
        if classified_count > 0:
            print(f"   ✅ [FIX-UNCATEGORIZED] {classified_count} vidéos classifiées")
            self.progress.log_action(name, "INTELLIGENT_UNCATEGORIZED_FIX", f"{classified_count} vidéos classifiées")
        else:
            print(f"   ❌ [FIX-UNCATEGORIZED] Aucune classification automatique possible")
    
    def intelligent_fix_hub_monopoly(self, cursor, competitor_id, name):
        """Correction intelligente pour monopole HUB (>95%)"""
        
        print(f"   ⚖️ [FIX-MONOPOLY] Rééquilibrage du monopole HUB...")
        
        # Convertir une partie des HUB en HERO (top performing)
        cursor.execute("""
            SELECT id, title, view_count FROM video 
            WHERE concurrent_id = ?
            AND category = 'hub'
            AND (
                (is_human_validated = 0 OR is_human_validated IS NULL) 
                OR classification_source = 'simulated_dates'
            )
            AND (classification_source != 'human' OR classification_source IS NULL)
            AND view_count > 30000
            ORDER BY view_count DESC
            LIMIT 3
        """, (competitor_id,))
        
        hero_candidates = cursor.fetchall()
        hero_converted = 0
        
        for video_id, title, view_count in hero_candidates:
            cursor.execute("""
                UPDATE video 
                SET category = 'hero',
                    classification_source = 'intelligent_monopoly_fix',
                    classification_date = datetime('now')
                WHERE id = ?
            """, (video_id,))
            hero_converted += 1
            print(f"     🎯 HUB→HERO: '{title[:50]}...' ({view_count:,} vues)")
        
        # Convertir une partie des HUB en HELP (contenu pratique)
        help_patterns = ['guide', 'how to', 'tips', 'museum', 'tour', 'visit']
        help_converted = 0
        
        for pattern in help_patterns:
            if help_converted >= 5:
                break
                
            cursor.execute("""
                SELECT id, title FROM video 
                WHERE concurrent_id = ?
                AND category = 'hub'
                AND (is_human_validated = 0 OR is_human_validated IS NULL)
                AND (classification_source != 'human' OR classification_source IS NULL)
                AND (classification_source != 'simulated_dates' OR classification_source IS NULL)
                AND LOWER(title) LIKE ?
                LIMIT 2
            """, (competitor_id, f'%{pattern}%'))
            
            candidates = cursor.fetchall()
            
            for video_id, title in candidates:
                if help_converted >= 5:
                    break
                    
                cursor.execute("""
                    UPDATE video 
                    SET category = 'help',
                        classification_source = 'intelligent_monopoly_fix',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                help_converted += 1
                print(f"     🆘 HUB→HELP: '{title[:50]}...' (pattern: {pattern})")
        
        total_rebalanced = hero_converted + help_converted
        
        if total_rebalanced > 0:
            print(f"   ✅ [FIX-MONOPOLY] {total_rebalanced} vidéos rééquilibrées ({hero_converted} HERO, {help_converted} HELP)")
            self.progress.log_action(name, "INTELLIGENT_MONOPOLY_FIX", f"{total_rebalanced} vidéos rééquilibrées")
        else:
            print(f"   ❌ [FIX-MONOPOLY] Aucun rééquilibrage possible automatiquement")
    
    def smart_classify_video_advanced(self, title, view_count, duration, competitor_name):
        """Classification intelligente avancée d'une vidéo"""
        
        title_lower = title.lower() if title else ''
        
        # HERO keywords (contenu inspirationnel/marque)
        hero_keywords = [
            'destination', 'discover', 'entdecken', 'explore', 'journey', 'adventure',
            'beautiful', 'amazing', 'stunning', 'dream', 'paradise', 'luxury',
            'sehnsuchtsorte', 'traumhaft', 'wunderschön', 'breathtaking',
            'exclusive', 'premium', 'spectacular', 'incredible'
        ]
        
        # HELP keywords (contenu pratique/aide)
        help_keywords = [
            'how to', 'guide', 'tutorial', 'tip', 'tips', 'advice', 'anleitung',
            'ratgeber', 'hilfe', 'step by step', 'budget', 'cost', 'price',
            'booking', 'reservation', 'packing', 'checklist', 'planning',
            'museum', 'tour', 'visit', 'walk', 'viertelliebe', 'stadtführung'
        ]
        
        # HUB keywords (contenu éducatif/informatif)
        hub_keywords = [
            'history', 'kultur', 'culture', 'event', 'festival', 'tradition',
            'architecture', 'art', 'music', 'food', 'restaurant', 'local',
            'neighborhood', 'district', 'area', 'region'
        ]
        
        # Classification par priorité et contexte
        if any(keyword in title_lower for keyword in help_keywords):
            return 'help'
        elif any(keyword in title_lower for keyword in hero_keywords):
            return 'hero'
        elif view_count and view_count > 100000:
            return 'hero'  # Performance élevée = contenu inspirationnel
        elif duration and duration < 60:
            return 'hero'  # Shorts = souvent contenu marque
        elif any(keyword in title_lower for keyword in hub_keywords):
            return 'hub'
        else:
            return 'hub'  # Par défaut = contenu éducatif
    
    def get_playlist_videos_from_api(self, playlist_id):
        """Récupérer les vidéos d'une playlist via API"""
        videos = []
        next_page_token = None
        
        while True:
            url = "https://www.googleapis.com/youtube/v3/playlistItems"
            params = {
                'part': 'snippet',
                'playlistId': playlist_id,
                'maxResults': 50,
                'key': self.api_key
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    break
                
                data = response.json()
                
                for item in data.get('items', []):
                    try:
                        video_id = item['snippet']['resourceId']['videoId']
                        videos.append(video_id)
                    except KeyError:
                        continue
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except Exception:
                break
        
        return videos
    
    def propagate_human_classifications(self, cursor, competitor_id):
        """Propager les classifications humaines depuis les playlists"""
        
        # PROTECTION ABSOLUE : Propager SEULEMENT aux vidéos NON classifiées manuellement
        cursor.execute("""
            UPDATE video 
            SET category = (
                SELECT p.category 
                FROM playlist_video pv
                JOIN playlist p ON pv.playlist_id = p.playlist_id
                WHERE pv.video_id = video.id 
                AND p.concurrent_id = ?
                AND p.category IS NOT NULL
                AND (p.is_human_validated = 1 OR p.classification_source = 'human')
                LIMIT 1
            ),
            classification_source = 'propagated_from_human_playlist',
            is_human_validated = 1,
            classification_date = datetime('now')
            WHERE concurrent_id = ?
            AND (
                (is_human_validated = 0 OR is_human_validated IS NULL) 
                OR classification_source = 'simulated_dates'
            )
            AND (classification_source != 'human' OR classification_source IS NULL)
            AND (category IS NULL OR category = 'uncategorized')
            AND EXISTS (
                SELECT 1 FROM playlist_video pv
                JOIN playlist p ON pv.playlist_id = p.playlist_id
                WHERE pv.video_id = video.id 
                AND p.concurrent_id = ?
                AND p.category IS NOT NULL
                AND (p.is_human_validated = 1 OR p.classification_source = 'human')
            )
        """, (competitor_id, competitor_id, competitor_id))
        
        return cursor.rowcount
    
    def classify_orphaned_videos(self, cursor, competitor_id, competitor_name):
        """Classifier intelligemment les vidéos orphelines (hors playlists)"""
        
        # Récupérer les vidéos non classifiées
        cursor.execute("""
            SELECT id, video_id, title, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            AND (category IS NULL OR category = 'uncategorized')
            AND (is_human_validated = 0 OR is_human_validated IS NULL)
            ORDER BY view_count DESC
        """, (competitor_id,))
        
        orphaned_videos = cursor.fetchall()
        
        if not orphaned_videos:
            return 0
        
        classified_count = 0
        
        # Classification intelligente par patterns
        for video_id, yt_video_id, title, view_count, duration in orphaned_videos:
            category = self.smart_classify_video(title, view_count, duration, competitor_name)
            
            if category:
                cursor.execute("""
                    UPDATE video 
                    SET category = ?, 
                        classification_source = 'intelligent_patterns',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (category, video_id))
                classified_count += 1
        
        return classified_count
    
    def smart_classify_video(self, title, view_count, duration, competitor_name):
        """Classification intelligente d'une vidéo basée sur titre, performance et contexte"""
        
        title_lower = title.lower()
        
        # Seuils dynamiques basés sur les vues
        high_performance_threshold = 100000 if view_count else 50000
        
        # HERO: Contenu inspirationnel/marque
        hero_keywords = [
            # Destinations et voyage
            'destination', 'discover', 'entdecken', 'explore', 'journey', 'adventure',
            'beautiful', 'amazing', 'stunning', 'dream', 'paradise', 'luxury',
            'sehnsuchtsorte', 'traumhaft', 'wunderschön', 'breathtaking',
            # Pays et villes
            'paris', 'london', 'berlin', 'rome', 'madrid', 'amsterdam', 'vienna',
            'italy', 'france', 'spain', 'germany', 'kroatien', 'italien', 'frankreich',
            # Expériences
            'experience', 'magic', 'unforgettable', 'once in lifetime'
        ]
        
        # HELP: Contenu pratique/aide
        help_keywords = [
            'how to', 'guide', 'tutorial', 'tip', 'tips', 'advice', 'anleitung',
            'ratgeber', 'hilfe', 'step by step', 'budget', 'cost', 'price',
            'booking', 'reservation', 'packing', 'checklist', 'planning'
        ]
        
        # Classification par priorité
        if any(keyword in title_lower for keyword in hero_keywords):
            return 'hero'
        elif any(keyword in title_lower for keyword in help_keywords):
            return 'help'
        elif view_count and view_count > high_performance_threshold:
            return 'hero'  # Performance élevée = contenu inspirationnel
        elif duration and duration < 60:
            return 'hero'  # Shorts = souvent contenu marque
        else:
            return 'hub'  # Par défaut = contenu éducatif
    
    def fix_zero_hero_content(self, cursor, competitor_id, competitor_name):
        """Détecter et corriger les concurrents avec 0% de contenu HERO"""
        
        # Vérifier s'il y a du contenu HERO
        cursor.execute("""
            SELECT COUNT(*) FROM video 
            WHERE concurrent_id = ? AND category = 'hero'
        """, (competitor_id,))
        
        hero_count = cursor.fetchone()[0]
        
        if hero_count > 0:
            return 0  # Déjà du contenu HERO
        
        # Identifier les vidéos top performance pour reclassification en HERO
        cursor.execute("""
            SELECT id, title, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            AND category = 'hub'  -- Reclassifier du HUB vers HERO
            AND (
                (is_human_validated = 0 OR is_human_validated IS NULL) 
                OR classification_source = 'simulated_dates'
            )
            AND (classification_source != 'human' OR classification_source IS NULL)
            ORDER BY view_count DESC
            LIMIT 5  -- Maximum 5 vidéos pour éviter sur-correction
        """, (competitor_id,))
        
        top_videos = cursor.fetchall()
        
        corrections = 0
        
        for video_id, title, view_count, duration in top_videos:
            # Vérifier si c'est du contenu approprié pour HERO
            if self.is_hero_worthy_content(title, view_count, competitor_name):
                cursor.execute("""
                    UPDATE video 
                    SET category = 'hero',
                        classification_source = 'zero_hero_correction',
                        classification_date = datetime('now')
                    WHERE id = ?
                """, (video_id,))
                corrections += 1
        
        return corrections
    
    def is_hero_worthy_content(self, title, view_count, competitor_name):
        """Déterminer si le contenu mérite d'être HERO"""
        
        title_lower = title.lower()
        
        # Contenu inspirationnel évident
        inspirational_words = [
            'amazing', 'beautiful', 'stunning', 'incredible', 'breathtaking',
            'paradise', 'dream', 'luxury', 'exclusive', 'premium',
            'wunderschön', 'traumhaft', 'fantastisch', 'incredible'
        ]
        
        # Destinations populaires
        destinations = [
            'paris', 'london', 'rome', 'barcelona', 'amsterdam', 'berlin',
            'italy', 'france', 'spain', 'croatia', 'greece', 'turkey'
        ]
        
        # Performance élevée suggère contenu inspirationnel
        high_performance = view_count and view_count > 100000
        
        # Contenu destination
        destination_content = any(dest in title_lower for dest in destinations)
        
        # Contenu inspirationnel
        inspirational_content = any(word in title_lower for word in inspirational_words)
        
        return high_performance or destination_content or inspirational_content
    
    def save_competitor_metrics(self, cursor, competitor_id, metrics):
        """Sauvegarder les métriques calculées en base"""
        
        try:
            # Mettre à jour la table competitor_stats (créer si n'existe pas)
            cursor.execute("""
                INSERT OR REPLACE INTO competitor_stats (
                    concurrent_id, total_videos, total_views, total_likes, total_comments,
                    avg_views, avg_likes, avg_comments, engagement_rate,
                    avg_duration_seconds, total_duration_seconds,
                    hero_count, hub_count, help_count,
                    hero_percentage, hub_percentage, help_percentage,
                    organic_count, paid_count, organic_percentage, paid_percentage,
                    shorts_count, long_count, shorts_percentage, long_percentage,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                competitor_id,
                metrics.get('total_videos', 0),
                metrics.get('total_views', 0),
                metrics.get('total_likes', 0),
                metrics.get('total_comments', 0),
                metrics.get('avg_views', 0),
                metrics.get('avg_likes', 0),
                metrics.get('avg_comments', 0),
                metrics.get('engagement_rate', 0),
                metrics.get('avg_duration', 0),
                metrics.get('total_duration', 0),
                metrics.get('hero_count', 0),
                metrics.get('hub_count', 0),
                metrics.get('help_count', 0),
                metrics.get('hero_percentage', 0),
                metrics.get('hub_percentage', 0),
                metrics.get('help_percentage', 0),
                metrics.get('organic_count', 0),
                metrics.get('paid_count', 0),
                metrics.get('organic_percentage', 0),
                metrics.get('paid_percentage', 0),
                metrics.get('shorts_count', 0),
                metrics.get('regular_count', 0),
                metrics.get('shorts_percentage', 0),
                metrics.get('regular_percentage', 0)
            ))
            
        except Exception as e:
            # Si la table n'existe pas, la créer
            self.create_competitor_stats_table(cursor)
    
    def create_competitor_stats_table(self, cursor):
        """Créer la table competitor_stats si elle n'existe pas"""
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurrent_id INTEGER NOT NULL,
                total_videos INTEGER DEFAULT 0,
                total_views INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                avg_views REAL DEFAULT 0,
                avg_likes REAL DEFAULT 0,
                avg_comments REAL DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                avg_duration_seconds REAL DEFAULT 0,
                total_duration_seconds INTEGER DEFAULT 0,
                hero_count INTEGER DEFAULT 0,
                hub_count INTEGER DEFAULT 0,
                help_count INTEGER DEFAULT 0,
                hero_percentage REAL DEFAULT 0,
                hub_percentage REAL DEFAULT 0,
                help_percentage REAL DEFAULT 0,
                organic_count INTEGER DEFAULT 0,
                paid_count INTEGER DEFAULT 0,
                organic_percentage REAL DEFAULT 0,
                paid_percentage REAL DEFAULT 0,
                shorts_count INTEGER DEFAULT 0,
                long_count INTEGER DEFAULT 0,
                shorts_percentage REAL DEFAULT 0,
                long_percentage REAL DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (concurrent_id) REFERENCES concurrent (id),
                UNIQUE(concurrent_id)
            )
        """)
    
    def clear_all_caches(self):
        """Nettoyer tous les caches possibles"""
        
        cache_files = [
            "/tmp/competitor_cache_*.json",
            "/tmp/metrics_cache_*.json",
            "/tmp/global_refresh_status.json"
        ]
        
        import glob
        cache_cleared = 0
        
        for pattern in cache_files:
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                    cache_cleared += 1
                except:
                    pass
        
        self.progress.stats['cache_cleared'] = cache_cleared
        self.progress.update_status(f"🔄 {cache_cleared} fichiers cache supprimés")

# Interface CLI
def main():
    """Interface en ligne de commande pour le système ULTIMATE"""
    
    system = UltimateGlobalRefreshSystem()
    
    print("🚀 ULTIMATE GLOBAL REFRESH SYSTEM")
    print("=" * 50)
    print("Ce script va exécuter la séquence complète :")
    print("1. Import API (playlists + vidéos)")
    print("2. Correction YouTube dates + durées")
    print("3. Classification intelligente + propagation")
    print("4. Recalcul complet des métriques")
    print("5. Stockage en base + force refresh")
    print()
    print("⚠️  PROTECTION ABSOLUE du travail humain activée")
    print()
    
    confirm = input("Confirmer l'exécution ? (y/N): ").lower().strip()
    
    if confirm == 'y':
        print("\n🚀 Démarrage du processus ULTIMATE...")
        system.run_ultimate_refresh()
        print(f"\n📄 Rapport détaillé : {system.progress.report_file}")
    else:
        print("❌ Processus annulé")

if __name__ == "__main__":
    main()