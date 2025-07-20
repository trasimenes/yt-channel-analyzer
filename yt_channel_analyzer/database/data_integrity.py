"""
Module de validation et contrôle d'intégrité des données
Système ultra-robuste pour garantir la cohérence des stats européennes
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .base import get_db_connection, DatabaseUtils

class SeverityLevel(Enum):
    """Niveaux de sévérité pour les erreurs de cohérence"""
    CRITICAL = "critical"    # Données complètement incohérentes
    HIGH = "high"           # Données suspectes mais utilisables
    MEDIUM = "medium"       # Données approximatives
    LOW = "low"             # Données mineures à corriger
    INFO = "info"           # Informations de validation

@dataclass
class ValidationError:
    """Erreur de validation détectée"""
    table: str
    field: str
    record_id: int
    severity: SeverityLevel
    message: str
    current_value: Any
    expected_value: Optional[Any] = None
    auto_fixable: bool = False
    
class DataIntegrityValidator:
    """Validateur d'intégrité des données ultra-robuste"""
    
    def __init__(self):
        self.db_utils = DatabaseUtils()
        self.errors = []
        self.stats = {
            'total_checks': 0,
            'errors_found': 0,
            'critical_errors': 0,
            'auto_fixes_applied': 0
        }
        
        # Seuils de cohérence
        self.COHERENCE_THRESHOLDS = {
            'min_video_duration': 1,           # Durée minimale en secondes
            'max_video_duration': 86400,       # 24h max
            'min_views_per_subscriber': 0.01,  # 1% des abonnés minimum
            'max_views_per_subscriber': 100,   # 100x les abonnés maximum
            'min_engagement_rate': 0.001,      # 0.1% minimum
            'max_engagement_rate': 0.5,        # 50% maximum
            'shorts_duration_threshold': 60,   # Shorts = <= 60s
            'organic_threshold_min': 1000,     # Seuil minimum pour organic
            'date_range_years': 20,            # Plage de dates acceptable
            'subscriber_growth_max': 10.0,     # Croissance max 1000% par mois
            'view_count_consistency': 0.1      # 10% de tolérance
        }
    
    def validate_complete_dataset(self, fix_errors: bool = False) -> Dict:
        """Validation complète de l'intégrité des données"""
        print("🔍 Démarrage de la validation complète d'intégrité")
        print("=" * 60)
        
        self.errors = []
        self.stats = {'total_checks': 0, 'errors_found': 0, 'critical_errors': 0, 'auto_fixes_applied': 0}
        
        try:
            conn = get_db_connection()
            
            # 1. Validation des concurrents
            print("\n1️⃣ Validation des concurrents...")
            self._validate_competitors(conn)
            
            # 2. Validation des vidéos
            print("\n2️⃣ Validation des vidéos...")
            self._validate_videos(conn)
            
            # 3. Validation des playlists
            print("\n3️⃣ Validation des playlists...")
            self._validate_playlists(conn)
            
            # 4. Validation des relations
            print("\n4️⃣ Validation des relations...")
            self._validate_relationships(conn)
            
            # 5. Validation des calculs dérivés
            print("\n5️⃣ Validation des calculs dérivés...")
            self._validate_calculated_fields(conn)
            
            # 6. Validation des dates
            print("\n6️⃣ Validation des dates...")
            self._validate_dates(conn)
            
            # 7. Validation des classifications
            print("\n7️⃣ Validation des classifications...")
            self._validate_classifications(conn)
            
            # 8. Correction automatique si demandée
            if fix_errors:
                print("\n8️⃣ Correction automatique des erreurs...")
                self._auto_fix_errors(conn)
            
            conn.close()
            
            # Générer le rapport final
            return self._generate_validation_report()
            
        except Exception as e:
            print(f"❌ Erreur lors de la validation: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    def _validate_competitors(self, conn: sqlite3.Connection):
        """Valider la cohérence des données de concurrents"""
        cursor = conn.cursor()
        
        # Vérifier les données de base
        cursor.execute("""
            SELECT id, name, channel_id, subscriber_count, video_count, total_views, avg_views
            FROM concurrent
        """)
        
        competitors = cursor.fetchall()
        self.stats['total_checks'] += len(competitors)
        
        for comp in competitors:
            comp_id, name, channel_id, sub_count, video_count, total_views, avg_views = comp
            
            # Vérification 1: Nom non vide
            if not name or name.strip() == '':
                self._add_error('concurrent', 'name', comp_id, SeverityLevel.CRITICAL,
                              "Nom du concurrent vide", name, auto_fixable=True)
            
            # Vérification 2: Channel ID format
            if channel_id and not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id):
                self._add_error('concurrent', 'channel_id', comp_id, SeverityLevel.HIGH,
                              "Format de channel_id invalide", channel_id)
            
            # Vérification 3: Nombre d'abonnés cohérent
            if sub_count is not None and sub_count < 0:
                self._add_error('concurrent', 'subscriber_count', comp_id, SeverityLevel.CRITICAL,
                              "Nombre d'abonnés négatif", sub_count, 0, auto_fixable=True)
            
            # Vérification 4: Nombre de vidéos cohérent
            if video_count is not None and video_count < 0:
                self._add_error('concurrent', 'video_count', comp_id, SeverityLevel.CRITICAL,
                              "Nombre de vidéos négatif", video_count, 0, auto_fixable=True)
            
            # Vérification 5: Vues totales cohérentes
            if total_views is not None and total_views < 0:
                self._add_error('concurrent', 'total_views', comp_id, SeverityLevel.CRITICAL,
                              "Vues totales négatives", total_views, 0, auto_fixable=True)
            
            # Vérification 6: Cohérence entre total_views et avg_views
            if (total_views is not None and avg_views is not None and 
                video_count is not None and video_count > 0):
                calculated_avg = total_views / video_count
                if abs(calculated_avg - avg_views) > (calculated_avg * 0.1):  # 10% de tolérance
                    self._add_error('concurrent', 'avg_views', comp_id, SeverityLevel.MEDIUM,
                                  f"Incohérence avg_views: calculé={calculated_avg:.0f}, stocké={avg_views:.0f}",
                                  avg_views, calculated_avg, auto_fixable=True)
    
    def _validate_videos(self, conn: sqlite3.Connection):
        """Valider la cohérence des données de vidéos"""
        cursor = conn.cursor()
        
        # Vérifier les données de base
        cursor.execute("""
            SELECT id, video_id, title, view_count, duration_seconds, is_short, 
                   published_at, youtube_published_at, concurrent_id
            FROM video
        """)
        
        videos = cursor.fetchall()
        self.stats['total_checks'] += len(videos)
        
        for video in videos:
            (vid_id, video_id, title, view_count, duration, is_short, 
             published_at, youtube_published_at, concurrent_id) = video
            
            # Vérification 1: Video ID format YouTube
            if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                self._add_error('video', 'video_id', vid_id, SeverityLevel.CRITICAL,
                              "Format video_id invalide", video_id)
            
            # Vérification 2: Titre non vide
            if not title or title.strip() == '':
                self._add_error('video', 'title', vid_id, SeverityLevel.HIGH,
                              "Titre de vidéo vide", title, auto_fixable=True)
            
            # Vérification 3: Nombre de vues cohérent
            if view_count is not None and view_count < 0:
                self._add_error('video', 'view_count', vid_id, SeverityLevel.CRITICAL,
                              "Nombre de vues négatif", view_count, 0, auto_fixable=True)
            
            # Vérification 4: Durée cohérente
            if duration is not None:
                if duration < self.COHERENCE_THRESHOLDS['min_video_duration']:
                    self._add_error('video', 'duration_seconds', vid_id, SeverityLevel.HIGH,
                                  "Durée vidéo trop courte", duration)
                elif duration > self.COHERENCE_THRESHOLDS['max_video_duration']:
                    self._add_error('video', 'duration_seconds', vid_id, SeverityLevel.HIGH,
                                  "Durée vidéo trop longue", duration)
            
            # Vérification 5: Cohérence is_short / duration
            if duration is not None and is_short is not None:
                expected_is_short = duration <= self.COHERENCE_THRESHOLDS['shorts_duration_threshold']
                if bool(is_short) != expected_is_short:
                    self._add_error('video', 'is_short', vid_id, SeverityLevel.MEDIUM,
                                  f"Incohérence is_short: durée={duration}s, is_short={is_short}",
                                  is_short, expected_is_short, auto_fixable=True)
            
            # Vérification 6: Dates de publication
            if published_at and youtube_published_at:
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    yt_date = datetime.fromisoformat(youtube_published_at.replace('Z', '+00:00'))
                    
                    # Si les dates sont identiques, c'est suspect (import date)
                    if pub_date.date() == yt_date.date():
                        self._add_error('video', 'published_at', vid_id, SeverityLevel.MEDIUM,
                                      "Dates de publication identiques (possiblement fausse date)",
                                      published_at, auto_fixable=True)
                except Exception:
                    self._add_error('video', 'published_at', vid_id, SeverityLevel.HIGH,
                                  "Format de date invalide", published_at)
    
    def _validate_playlists(self, conn: sqlite3.Connection):
        """Valider la cohérence des données de playlists"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, video_count, concurrent_id
            FROM playlist
        """)
        
        playlists = cursor.fetchall()
        self.stats['total_checks'] += len(playlists)
        
        for playlist in playlists:
            playlist_id, name, description, video_count, concurrent_id = playlist
            
            # Vérification 1: Nom non vide
            if not name or name.strip() == '':
                self._add_error('playlist', 'name', playlist_id, SeverityLevel.HIGH,
                              "Nom de playlist vide", name, auto_fixable=True)
            
            # Vérification 2: Video count cohérent
            if video_count is not None and video_count < 0:
                self._add_error('playlist', 'video_count', playlist_id, SeverityLevel.CRITICAL,
                              "Nombre de vidéos négatif", video_count, 0, auto_fixable=True)
            
            # Vérification 3: Cohérence avec les relations playlist_video
            cursor.execute("""
                SELECT COUNT(*) FROM playlist_video WHERE playlist_id = ?
            """, (playlist_id,))
            actual_count = cursor.fetchone()[0]
            
            if video_count is not None and actual_count != video_count:
                self._add_error('playlist', 'video_count', playlist_id, SeverityLevel.MEDIUM,
                              f"Incohérence video_count: attendu={actual_count}, stocké={video_count}",
                              video_count, actual_count, auto_fixable=True)
    
    def _validate_relationships(self, conn: sqlite3.Connection):
        """Valider la cohérence des relations entre tables"""
        cursor = conn.cursor()
        
        # Vérifier les orphelins
        print("   🔍 Vérification des orphelins...")
        
        # Vidéos sans concurrent
        cursor.execute("""
            SELECT COUNT(*) FROM video v 
            LEFT JOIN concurrent c ON v.concurrent_id = c.id 
            WHERE c.id IS NULL
        """)
        orphan_videos = cursor.fetchone()[0]
        if orphan_videos > 0:
            self._add_error('video', 'concurrent_id', 0, SeverityLevel.CRITICAL,
                          f"{orphan_videos} vidéos orphelines sans concurrent", orphan_videos)
        
        # Playlists sans concurrent
        cursor.execute("""
            SELECT COUNT(*) FROM playlist p 
            LEFT JOIN concurrent c ON p.concurrent_id = c.id 
            WHERE c.id IS NULL
        """)
        orphan_playlists = cursor.fetchone()[0]
        if orphan_playlists > 0:
            self._add_error('playlist', 'concurrent_id', 0, SeverityLevel.CRITICAL,
                          f"{orphan_playlists} playlists orphelines sans concurrent", orphan_playlists)
        
        # Relations playlist_video avec vidéos inexistantes
        cursor.execute("""
            SELECT COUNT(*) FROM playlist_video pv 
            LEFT JOIN video v ON pv.video_id = v.id 
            WHERE v.id IS NULL
        """)
        invalid_relations = cursor.fetchone()[0]
        if invalid_relations > 0:
            self._add_error('playlist_video', 'video_id', 0, SeverityLevel.HIGH,
                          f"{invalid_relations} relations vers vidéos inexistantes", invalid_relations)
        
        self.stats['total_checks'] += 3
    
    def _validate_calculated_fields(self, conn: sqlite3.Connection):
        """Valider les champs calculés et dérivés"""
        cursor = conn.cursor()
        
        # Vérifier les statistiques de concurrents
        cursor.execute("""
            SELECT c.id, c.name, c.video_count, c.total_views, c.avg_views,
                   COUNT(v.id) as actual_video_count,
                   SUM(v.view_count) as actual_total_views,
                   AVG(v.view_count) as actual_avg_views
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id, c.name, c.video_count, c.total_views, c.avg_views
        """)
        
        for row in cursor.fetchall():
            (comp_id, name, stored_video_count, stored_total_views, stored_avg_views,
             actual_video_count, actual_total_views, actual_avg_views) = row
            
            # Vérifier video_count
            if stored_video_count != actual_video_count:
                self._add_error('concurrent', 'video_count', comp_id, SeverityLevel.MEDIUM,
                              f"Video count incorrect: {stored_video_count} vs {actual_video_count}",
                              stored_video_count, actual_video_count, auto_fixable=True)
            
            # Vérifier total_views
            if (stored_total_views is not None and actual_total_views is not None and 
                abs(stored_total_views - actual_total_views) > (actual_total_views * 0.05)):
                self._add_error('concurrent', 'total_views', comp_id, SeverityLevel.MEDIUM,
                              f"Total views incorrect: {stored_total_views} vs {actual_total_views}",
                              stored_total_views, actual_total_views, auto_fixable=True)
            
            # Vérifier avg_views
            if (stored_avg_views is not None and actual_avg_views is not None and 
                abs(stored_avg_views - actual_avg_views) > (actual_avg_views * 0.05)):
                self._add_error('concurrent', 'avg_views', comp_id, SeverityLevel.MEDIUM,
                              f"Avg views incorrect: {stored_avg_views:.0f} vs {actual_avg_views:.0f}",
                              stored_avg_views, actual_avg_views, auto_fixable=True)
        
        self.stats['total_checks'] += len(cursor.fetchall())
    
    def _validate_dates(self, conn: sqlite3.Connection):
        """Valider la cohérence des dates"""
        cursor = conn.cursor()
        
        current_year = datetime.now().year
        min_year = current_year - self.COHERENCE_THRESHOLDS['date_range_years']
        max_year = current_year + 1
        
        # Vérifier les dates de vidéos
        cursor.execute("""
            SELECT id, video_id, published_at, youtube_published_at
            FROM video
            WHERE published_at IS NOT NULL OR youtube_published_at IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            video_id, vid_id, published_at, youtube_published_at = row
            
            # Vérifier published_at
            if published_at:
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    if pub_date.year < min_year or pub_date.year > max_year:
                        self._add_error('video', 'published_at', video_id, SeverityLevel.HIGH,
                                      f"Date de publication hors plage acceptable: {pub_date.year}",
                                      published_at)
                except Exception:
                    self._add_error('video', 'published_at', video_id, SeverityLevel.CRITICAL,
                                  "Format de date invalide", published_at)
            
            # Vérifier youtube_published_at
            if youtube_published_at:
                try:
                    yt_date = datetime.fromisoformat(youtube_published_at.replace('Z', '+00:00'))
                    if yt_date.year < min_year or yt_date.year > max_year:
                        self._add_error('video', 'youtube_published_at', video_id, SeverityLevel.HIGH,
                                      f"Date YouTube hors plage acceptable: {yt_date.year}",
                                      youtube_published_at)
                except Exception:
                    self._add_error('video', 'youtube_published_at', video_id, SeverityLevel.CRITICAL,
                                  "Format de date YouTube invalide", youtube_published_at)
        
        self.stats['total_checks'] += len(cursor.fetchall())
    
    def _validate_classifications(self, conn: sqlite3.Connection):
        """Valider la cohérence des classifications"""
        cursor = conn.cursor()
        
        # Vérifier les classifications de vidéos
        cursor.execute("""
            SELECT id, category, classification_source, is_human_validated
            FROM video
            WHERE category IS NOT NULL
        """)
        
        valid_categories = ['hero', 'hub', 'help', 'uncategorized']
        valid_sources = ['human', 'ai', 'playlist', 'keyword', 'multilingual', 'auto']
        
        for row in cursor.fetchall():
            video_id, category, classification_source, is_human_validated = row
            
            # Vérifier catégorie valide
            if category not in valid_categories:
                self._add_error('video', 'category', video_id, SeverityLevel.HIGH,
                              f"Catégorie invalide: {category}", category, auto_fixable=True)
            
            # Vérifier source valide
            if classification_source not in valid_sources:
                self._add_error('video', 'classification_source', video_id, SeverityLevel.MEDIUM,
                              f"Source de classification invalide: {classification_source}",
                              classification_source, auto_fixable=True)
            
            # Vérifier cohérence human validation
            if is_human_validated and classification_source != 'human':
                self._add_error('video', 'is_human_validated', video_id, SeverityLevel.HIGH,
                              f"Validation humaine incohérente avec source: {classification_source}",
                              is_human_validated, auto_fixable=True)
        
        self.stats['total_checks'] += len(cursor.fetchall())
    
    def _auto_fix_errors(self, conn: sqlite3.Connection):
        """Corriger automatiquement les erreurs réparables"""
        cursor = conn.cursor()
        
        for error in self.errors:
            if not error.auto_fixable:
                continue
            
            try:
                if error.table == 'concurrent':
                    if error.field == 'name' and not error.current_value:
                        cursor.execute("UPDATE concurrent SET name = ? WHERE id = ?",
                                     (f"Concurrent {error.record_id}", error.record_id))
                    elif error.field in ['subscriber_count', 'video_count', 'total_views'] and error.current_value < 0:
                        cursor.execute(f"UPDATE concurrent SET {error.field} = 0 WHERE id = ?",
                                     (error.record_id,))
                    elif error.field == 'avg_views' and error.expected_value is not None:
                        cursor.execute("UPDATE concurrent SET avg_views = ? WHERE id = ?",
                                     (error.expected_value, error.record_id))
                
                elif error.table == 'video':
                    if error.field == 'title' and not error.current_value:
                        cursor.execute("UPDATE video SET title = ? WHERE id = ?",
                                     (f"Video {error.record_id}", error.record_id))
                    elif error.field == 'view_count' and error.current_value < 0:
                        cursor.execute("UPDATE video SET view_count = 0 WHERE id = ?",
                                     (error.record_id,))
                    elif error.field == 'is_short' and error.expected_value is not None:
                        cursor.execute("UPDATE video SET is_short = ? WHERE id = ?",
                                     (error.expected_value, error.record_id))
                
                elif error.table == 'playlist':
                    if error.field == 'name' and not error.current_value:
                        cursor.execute("UPDATE playlist SET name = ? WHERE id = ?",
                                     (f"Playlist {error.record_id}", error.record_id))
                    elif error.field == 'video_count' and error.expected_value is not None:
                        cursor.execute("UPDATE playlist SET video_count = ? WHERE id = ?",
                                     (error.expected_value, error.record_id))
                
                self.stats['auto_fixes_applied'] += 1
                
            except Exception as e:
                print(f"   ⚠️  Erreur lors de la correction automatique: {e}")
        
        conn.commit()
    
    def _add_error(self, table: str, field: str, record_id: int, severity: SeverityLevel,
                   message: str, current_value: Any, expected_value: Any = None, auto_fixable: bool = False):
        """Ajouter une erreur de validation"""
        error = ValidationError(
            table=table,
            field=field,
            record_id=record_id,
            severity=severity,
            message=message,
            current_value=current_value,
            expected_value=expected_value,
            auto_fixable=auto_fixable
        )
        
        self.errors.append(error)
        self.stats['errors_found'] += 1
        
        if severity == SeverityLevel.CRITICAL:
            self.stats['critical_errors'] += 1
            print(f"   ❌ CRITIQUE: {message}")
        elif severity == SeverityLevel.HIGH:
            print(f"   ⚠️  ÉLEVÉ: {message}")
    
    def _generate_validation_report(self) -> Dict:
        """Générer le rapport de validation final"""
        errors_by_severity = {}
        for severity in SeverityLevel:
            errors_by_severity[severity.value] = [
                error for error in self.errors if error.severity == severity
            ]
        
        errors_by_table = {}
        for error in self.errors:
            if error.table not in errors_by_table:
                errors_by_table[error.table] = []
            errors_by_table[error.table].append(error)
        
        # Déterminer le niveau de santé global
        health_status = "excellent"
        if self.stats['critical_errors'] > 0:
            health_status = "critical"
        elif self.stats['errors_found'] > 10:
            health_status = "poor"
        elif self.stats['errors_found'] > 0:
            health_status = "warning"
        
        return {
            'success': True,
            'health_status': health_status,
            'stats': self.stats,
            'errors_by_severity': {
                severity: len(errors) for severity, errors in errors_by_severity.items()
            },
            'errors_by_table': {
                table: len(errors) for table, errors in errors_by_table.items()
            },
            'critical_errors': [
                {
                    'table': error.table,
                    'field': error.field,
                    'record_id': error.record_id,
                    'message': error.message,
                    'current_value': error.current_value,
                    'expected_value': error.expected_value,
                    'auto_fixable': error.auto_fixable
                }
                for error in self.errors if error.severity == SeverityLevel.CRITICAL
            ],
            'summary': self._generate_summary(health_status),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_summary(self, health_status: str) -> str:
        """Générer un résumé textuel"""
        if health_status == "excellent":
            return "✅ Système parfaitement cohérent - Prêt pour l'Europe"
        elif health_status == "warning":
            return "⚠️ Quelques incohérences mineures détectées - Correction recommandée"
        elif health_status == "poor":
            return "🔴 Incohérences importantes détectées - Correction nécessaire"
        else:
            return "🚨 ERREURS CRITIQUES - Correction immédiate requise"
    
    def _generate_recommendations(self) -> List[str]:
        """Générer des recommandations d'amélioration"""
        recommendations = []
        
        if self.stats['critical_errors'] > 0:
            recommendations.append("🚨 Corriger immédiatement les erreurs critiques")
        
        if self.stats['auto_fixes_applied'] > 0:
            recommendations.append(f"✅ {self.stats['auto_fixes_applied']} corrections automatiques appliquées")
        
        auto_fixable_count = sum(1 for error in self.errors if error.auto_fixable and error.severity != SeverityLevel.CRITICAL)
        if auto_fixable_count > 0:
            recommendations.append(f"🔧 {auto_fixable_count} erreurs peuvent être corrigées automatiquement")
        
        if self.stats['errors_found'] == 0:
            recommendations.append("🎉 Aucune erreur détectée - Système optimal")
        
        return recommendations


# Instance globale
data_validator = DataIntegrityValidator()

# Fonctions d'interface
def validate_data_integrity(fix_errors: bool = False) -> Dict:
    """Valider l'intégrité complète des données"""
    return data_validator.validate_complete_dataset(fix_errors=fix_errors)

def get_data_health_status() -> Dict:
    """Obtenir rapidement le statut de santé des données"""
    try:
        result = data_validator.validate_complete_dataset(fix_errors=False)
        return {
            'success': True,
            'health_status': result['health_status'],
            'critical_errors': result['stats']['critical_errors'],
            'total_errors': result['stats']['errors_found'],
            'total_checks': result['stats']['total_checks']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'health_status': 'unknown'
        }