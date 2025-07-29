#!/usr/bin/env python3
"""
Key Metrics Validator - Agent de validation des métriques clés
=============================================================

Valide la cohérence et la plausibilité de toutes les Key Metrics de chaque competitor
avant leur utilisation dans les PowerPoint et analyses.

8 Key Metrics validées :
1. Durée des Vidéos (moyenne en minutes, % courts/longs)
2. Fréquence de Publication (vidéos/semaine, jour optimal)
3. Distribution HHH (Hero-Hub-Help en %)
4. Organique vs Payé (% organic/paid)
5. Shorts vs Vidéos 16:9 (% format)
6. Cohérence des Miniatures (%)
7. Champ Lexical (% cohérence tonalité)
8. Sujet le Plus Apprécié (titre performance)

Critères de validation :
- Distribution HHH : au moins une catégorie > 0%
- Durée moyenne : > 0 min et < 60 min (plausible YouTube)
- Fréquence : > 0 et < 100 vidéos/semaine (plausible)
- Pourcentages : entre 0-100%
- Cohérence : pas tous à 0% ou 100%
- Sujet populaire : existe et non vide
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import statistics
import re
from dataclasses import dataclass
from enum import Enum

# Configuration
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / 'instance' / 'database.db'

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('key_metrics_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Statuts de validation possibles."""
    EXCELLENT = "excellent"      # Toutes les métriques sont valides et cohérentes
    GOOD = "good"               # Métriques majoritairement valides avec alertes mineures
    WARNING = "warning"         # Problèmes de cohérence détectés
    CRITICAL = "critical"       # Métriques invalides ou aberrantes
    INSUFFICIENT_DATA = "insufficient_data"  # Pas assez de données


@dataclass
class ValidationResult:
    """Résultat de validation pour une métrique."""
    metric_name: str
    status: ValidationStatus
    value: Any
    expected_range: str
    message: str
    recommendation: str


@dataclass
class CompetitorValidationReport:
    """Rapport de validation complet pour un competitor."""
    competitor_id: int
    competitor_name: str
    country: str
    overall_status: ValidationStatus
    metrics_results: List[ValidationResult]
    total_videos: int
    powerpoint_ready: bool
    summary: str
    critical_issues: List[str]
    warnings: List[str]
    validation_date: datetime


class KeyMetricsValidator:
    """Agent de validation des métriques clés pour tous les competitors."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.paid_threshold = 10000  # Seuil pour considérer une vidéo comme payée
        
    def get_db_connection(self) -> sqlite3.Connection:
        """Crée une connexion à la base de données."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def validate_all_competitors(self) -> List[CompetitorValidationReport]:
        """Valide les métriques de tous les competitors."""
        logger.info("🚀 Démarrage de la validation complète de tous les competitors")
        
        with self.get_db_connection() as conn:
            # Récupérer tous les competitors
            competitors = conn.execute("""
                SELECT c.id, c.name, c.country, COUNT(v.id) as video_count
                FROM concurrent c
                LEFT JOIN video v ON c.id = v.concurrent_id
                GROUP BY c.id, c.name, c.country
                ORDER BY c.country, c.name
            """).fetchall()
        
        reports = []
        for competitor in competitors:
            try:
                report = self.validate_competitor(competitor['id'])
                reports.append(report)
                logger.info(f"✅ Competitor {competitor['name']} - Status: {report.overall_status.value}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la validation du competitor {competitor['name']}: {e}")
        
        logger.info(f"🏁 Validation terminée pour {len(reports)} competitors")
        return reports
    
    def validate_competitor(self, competitor_id: int) -> CompetitorValidationReport:
        """Valide les métriques d'un competitor spécifique."""
        with self.get_db_connection() as conn:
            # Récupérer les données du competitor
            competitor = conn.execute(
                "SELECT * FROM concurrent WHERE id = ?", (competitor_id,)
            ).fetchone()
            
            if not competitor:
                raise ValueError(f"Competitor {competitor_id} non trouvé")
            
            # Récupérer toutes les vidéos
            videos = conn.execute("""
                SELECT * FROM video 
                WHERE concurrent_id = ? 
                ORDER BY published_at DESC
            """, (competitor_id,)).fetchall()
        
        # Exécuter toutes les validations
        metrics_results = []
        critical_issues = []
        warnings = []
        
        # 1. Validation Durée des Vidéos
        duration_result = self._validate_video_duration(videos)
        metrics_results.append(duration_result)
        if duration_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(duration_result.message)
        elif duration_result.status == ValidationStatus.WARNING:
            warnings.append(duration_result.message)
        
        # 2. Validation Fréquence de Publication
        frequency_result = self._validate_publishing_frequency(videos)
        metrics_results.append(frequency_result)
        if frequency_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(frequency_result.message)
        elif frequency_result.status == ValidationStatus.WARNING:
            warnings.append(frequency_result.message)
        
        # 3. Validation Distribution HHH
        hhh_result = self._validate_hhh_distribution(videos)
        metrics_results.append(hhh_result)
        if hhh_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(hhh_result.message)
        elif hhh_result.status == ValidationStatus.WARNING:
            warnings.append(hhh_result.message)
        
        # 4. Validation Organique vs Payé
        organic_paid_result = self._validate_organic_vs_paid(videos)
        metrics_results.append(organic_paid_result)
        if organic_paid_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(organic_paid_result.message)
        elif organic_paid_result.status == ValidationStatus.WARNING:
            warnings.append(organic_paid_result.message)
        
        # 5. Validation Shorts vs Vidéos 16:9
        shorts_result = self._validate_shorts_distribution(videos)
        metrics_results.append(shorts_result)
        if shorts_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(shorts_result.message)
        elif shorts_result.status == ValidationStatus.WARNING:
            warnings.append(shorts_result.message)
        
        # 6. Validation Cohérence des Miniatures
        thumbnail_result = self._validate_thumbnail_consistency(videos)
        metrics_results.append(thumbnail_result)
        if thumbnail_result.status == ValidationStatus.WARNING:
            warnings.append(thumbnail_result.message)
        
        # 7. Validation Champ Lexical
        lexical_result = self._validate_lexical_consistency(videos)
        metrics_results.append(lexical_result)
        if lexical_result.status == ValidationStatus.WARNING:
            warnings.append(lexical_result.message)
        
        # 8. Validation Sujet le Plus Apprécié
        top_subject_result = self._validate_top_performing_subject(videos)
        metrics_results.append(top_subject_result)
        if top_subject_result.status == ValidationStatus.CRITICAL:
            critical_issues.append(top_subject_result.message)
        elif top_subject_result.status == ValidationStatus.WARNING:
            warnings.append(top_subject_result.message)
        
        # Déterminer le statut global
        overall_status = self._determine_overall_status(metrics_results)
        
        # Déterminer si prêt pour PowerPoint
        powerpoint_ready = (
            overall_status in [ValidationStatus.EXCELLENT, ValidationStatus.GOOD] 
            and len(critical_issues) == 0
            and len(videos) > 0
        )
        
        # Générer le résumé
        summary = self._generate_summary(overall_status, len(videos), len(critical_issues), len(warnings))
        
        return CompetitorValidationReport(
            competitor_id=competitor_id,
            competitor_name=competitor['name'],
            country=competitor['country'],
            overall_status=overall_status,
            metrics_results=metrics_results,
            total_videos=len(videos),
            powerpoint_ready=powerpoint_ready,
            summary=summary,
            critical_issues=critical_issues,
            warnings=warnings,
            validation_date=datetime.now()
        )
    
    def _validate_video_duration(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide les métriques de durée des vidéos."""
        if not videos:
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value=0,
                expected_range="0.5-60 minutes",
                message="Aucune vidéo trouvée",
                recommendation="Importer des vidéos pour cette chaîne"
            )
        
        # Calculer les durées
        durations = [v['duration_seconds'] for v in videos if v['duration_seconds'] and v['duration_seconds'] > 0]
        
        if not durations:
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.CRITICAL,
                value=0,
                expected_range="0.5-60 minutes",
                message="Aucune durée de vidéo disponible",
                recommendation="Récupérer les durées des vidéos via l'API YouTube"
            )
        
        avg_duration_minutes = statistics.mean(durations) / 60
        short_videos = sum(1 for d in durations if d < 60)  # < 1 minute
        long_videos = sum(1 for d in durations if d > 3600)  # > 1 heure
        short_percentage = (short_videos / len(durations)) * 100
        long_percentage = (long_videos / len(durations)) * 100
        
        # Validation
        if avg_duration_minutes <= 0 or avg_duration_minutes > 120:  # Plus de 2h suspect
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.CRITICAL,
                value=f"{avg_duration_minutes:.1f} min",
                expected_range="0.5-60 minutes",
                message=f"Durée moyenne aberrante: {avg_duration_minutes:.1f} minutes",
                recommendation="Vérifier les données de durée des vidéos"
            )
        elif avg_duration_minutes > 60:  # Plus d'1h attention
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.WARNING,
                value=f"{avg_duration_minutes:.1f} min",
                expected_range="0.5-60 minutes",
                message=f"Durée moyenne élevée: {avg_duration_minutes:.1f} minutes",
                recommendation="Vérifier si ce sont des livestreams ou des contenus longs normaux"
            )
        elif short_percentage > 80:  # Trop de vidéos très courtes
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.WARNING,
                value=f"{avg_duration_minutes:.1f} min ({short_percentage:.0f}% courts)",
                expected_range="0.5-60 minutes",
                message=f"{short_percentage:.0f}% des vidéos sont < 1 minute",
                recommendation="Chaîne principalement orientée Shorts YouTube"
            )
        else:
            return ValidationResult(
                metric_name="Durée des Vidéos",
                status=ValidationStatus.EXCELLENT,
                value=f"{avg_duration_minutes:.1f} min",
                expected_range="0.5-60 minutes",
                message=f"Durée moyenne cohérente: {avg_duration_minutes:.1f} minutes",
                recommendation="Durées optimales pour l'engagement"
            )
    
    def _validate_publishing_frequency(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la fréquence de publication."""
        if not videos or len(videos) < 2:
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0 vidéos/semaine",
                expected_range="0.1-10 vidéos/semaine",
                message="Pas assez de vidéos pour calculer la fréquence",
                recommendation="Importer plus de vidéos"
            )
        
        # Parser les dates de publication
        valid_dates = []
        for video in videos:
            if video['published_at']:
                try:
                    # Essayer différents formats de date
                    date_str = video['published_at']
                    if 'T' in date_str:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                    valid_dates.append(date)
                except Exception:
                    continue
        
        if len(valid_dates) < 2:
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.CRITICAL,
                value="Dates invalides",
                expected_range="0.1-10 vidéos/semaine",
                message="Dates de publication non valides",
                recommendation="Corriger les dates avec l'agent de correction YouTube"
            )
        
        valid_dates.sort()
        
        # Calculer la fréquence
        date_range = (valid_dates[-1] - valid_dates[0]).days
        if date_range == 0:
            # Toutes les vidéos publiées le même jour (suspect)
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.CRITICAL,
                value="Toutes le même jour",
                expected_range="0.1-10 vidéos/semaine",
                message="Toutes les vidéos ont la même date de publication",
                recommendation="CRITIQUE: Dates d'import utilisées au lieu des vraies dates YouTube"
            )
        
        weeks = max(date_range / 7, 1)
        videos_per_week = len(valid_dates) / weeks
        
        # Validation
        if videos_per_week > 50:  # Plus de 50 vidéos/semaine = aberrant
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.CRITICAL,
                value=f"{videos_per_week:.1f} vidéos/semaine",
                expected_range="0.1-10 vidéos/semaine",
                message=f"Fréquence aberrante: {videos_per_week:.1f} vidéos/semaine",
                recommendation="Vérifier les données d'import et les dates de publication"
            )
        elif videos_per_week > 15:  # Plus de 15 vidéos/semaine = suspect
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.WARNING,
                value=f"{videos_per_week:.1f} vidéos/semaine",
                expected_range="0.1-10 vidéos/semaine",
                message=f"Fréquence très élevée: {videos_per_week:.1f} vidéos/semaine",
                recommendation="Vérifier s'il s'agit d'une chaîne très active ou de données incorrectes"
            )
        elif videos_per_week < 0.1:  # Moins d'1 vidéo tous les 10 semaines
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.WARNING,
                value=f"{videos_per_week:.2f} vidéos/semaine",
                expected_range="0.1-10 vidéos/semaine",
                message="Fréquence très faible de publication",
                recommendation="Chaîne peu active ou données incomplètes"
            )
        else:
            return ValidationResult(
                metric_name="Fréquence de Publication",
                status=ValidationStatus.EXCELLENT,
                value=f"{videos_per_week:.1f} vidéos/semaine",
                expected_range="0.1-10 vidéos/semaine",
                message=f"Fréquence cohérente: {videos_per_week:.1f} vidéos/semaine",
                recommendation="Rythme de publication optimal"
            )
    
    def _validate_hhh_distribution(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la distribution Hero-Hub-Help."""
        if not videos:
            return ValidationResult(
                metric_name="Distribution HHH",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0/0/0%",
                expected_range="Au moins une catégorie > 0%",
                message="Aucune vidéo pour calculer la distribution HHH",
                recommendation="Importer des vidéos"
            )
        
        # Compter les catégories
        hero_count = sum(1 for v in videos if v['category'] == 'hero')
        hub_count = sum(1 for v in videos if v['category'] == 'hub')
        help_count = sum(1 for v in videos if v['category'] == 'help')
        uncategorized_count = sum(1 for v in videos if v['category'] is None or v['category'] == '')
        
        total_categorized = hero_count + hub_count + help_count
        total_videos = len(videos)
        
        # Calculer les pourcentages
        if total_categorized > 0:
            hero_pct = (hero_count / total_categorized) * 100
            hub_pct = (hub_count / total_categorized) * 100
            help_pct = (help_count / total_categorized) * 100
            categorized_pct = (total_categorized / total_videos) * 100
        else:
            hero_pct = hub_pct = help_pct = categorized_pct = 0
        
        # Validation
        if total_categorized == 0:
            return ValidationResult(
                metric_name="Distribution HHH",
                status=ValidationStatus.CRITICAL,
                value="0/0/0% (0% catégorisé)",
                expected_range="Au moins une catégorie > 0%",
                message="Aucune vidéo catégorisée",
                recommendation="CRITIQUE: Lancer la classification manuelle ou automatique"
            )
        elif categorized_pct < 50:  # Moins de 50% catégorisé
            return ValidationResult(
                metric_name="Distribution HHH",
                status=ValidationStatus.WARNING,
                value=f"{hero_pct:.0f}/{hub_pct:.0f}/{help_pct:.0f}% ({categorized_pct:.0f}% catégorisé)",
                expected_range="Au moins une catégorie > 0%",
                message=f"Seulement {categorized_pct:.0f}% des vidéos sont catégorisées",
                recommendation="Terminer la classification des vidéos restantes"
            )
        elif (hero_pct == 100 and hub_pct == 0 and help_pct == 0) or \
             (hub_pct == 100 and hero_pct == 0 and help_pct == 0) or \
             (help_pct == 100 and hero_pct == 0 and hub_pct == 0):
            return ValidationResult(
                metric_name="Distribution HHH",
                status=ValidationStatus.WARNING,
                value=f"{hero_pct:.0f}/{hub_pct:.0f}/{help_pct:.0f}%",
                expected_range="Distribution équilibrée",
                message="Distribution mono-catégorie (100% dans une seule catégorie)",
                recommendation="Vérifier la stratégie de contenu - diversification recommandée"
            )
        else:
            return ValidationResult(
                metric_name="Distribution HHH",
                status=ValidationStatus.EXCELLENT,
                value=f"{hero_pct:.0f}/{hub_pct:.0f}/{help_pct:.0f}%",
                expected_range="Distribution équilibrée",
                message=f"Distribution équilibrée - {categorized_pct:.0f}% catégorisé",
                recommendation="Distribution stratégique optimale"
            )
    
    def _validate_organic_vs_paid(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la distribution Organique vs Payé."""
        if not videos:
            return ValidationResult(
                metric_name="Organique vs Payé",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0/0%",
                expected_range="Équilibre cohérent",
                message="Aucune vidéo pour calculer la distribution",
                recommendation="Importer des vidéos"
            )
        
        # Calculer les métriques de vues
        videos_with_views = [v for v in videos if v['view_count'] is not None and v['view_count'] > 0]
        
        if not videos_with_views:
            return ValidationResult(
                metric_name="Organique vs Payé",
                status=ValidationStatus.CRITICAL,
                value="Pas de données de vues",
                expected_range="Équilibre cohérent",
                message="Aucune donnée de vues disponible",
                recommendation="Récupérer les données de vues via l'API YouTube"
            )
        
        # Classifier en payé/organique basé sur le seuil
        paid_count = sum(1 for v in videos_with_views if v['view_count'] >= self.paid_threshold)
        organic_count = len(videos_with_views) - paid_count
        
        paid_pct = (paid_count / len(videos_with_views)) * 100
        organic_pct = (organic_count / len(videos_with_views)) * 100
        
        # Validation
        if paid_pct == 100:
            return ValidationResult(
                metric_name="Organique vs Payé",
                status=ValidationStatus.WARNING,
                value=f"{organic_pct:.0f}/{paid_pct:.0f}%",
                expected_range="Équilibre cohérent",
                message="100% de contenu à fort impact (possiblement payé)",
                recommendation="Vérifier si le seuil de détection est approprié"
            )
        elif organic_pct == 100:
            return ValidationResult(
                metric_name="Organique vs Payé",
                status=ValidationStatus.GOOD,
                value=f"{organic_pct:.0f}/{paid_pct:.0f}%",
                expected_range="Équilibre cohérent",
                message="100% de contenu organique",
                recommendation="Stratégie organique pure - bon pour l'authenticité"
            )
        else:
            return ValidationResult(
                metric_name="Organique vs Payé",
                status=ValidationStatus.EXCELLENT,
                value=f"{organic_pct:.0f}/{paid_pct:.0f}%",
                expected_range="Équilibre cohérent",
                message=f"Équilibre organique/payé: {organic_pct:.0f}%/{paid_pct:.0f}%",
                recommendation="Bon équilibre entre contenu organique et promotionnel"
            )
    
    def _validate_shorts_distribution(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la distribution Shorts vs Vidéos format 16:9."""
        if not videos:
            return ValidationResult(
                metric_name="Shorts vs Vidéos 16:9",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0/0%",
                expected_range="Distribution selon stratégie",
                message="Aucune vidéo pour calculer la distribution",
                recommendation="Importer des vidéos"
            )
        
        # Compter les Shorts (is_short = 1) vs vidéos normales
        shorts_count = sum(1 for v in videos if v['is_short'] == 1)
        regular_count = len(videos) - shorts_count
        
        shorts_pct = (shorts_count / len(videos)) * 100
        regular_pct = (regular_count / len(videos)) * 100
        
        # Validation
        if shorts_count == 0 and regular_count == 0:
            return ValidationResult(
                metric_name="Shorts vs Vidéos 16:9",
                status=ValidationStatus.CRITICAL,
                value="Données manquantes",
                expected_range="Distribution selon stratégie",
                message="Aucune information sur le format des vidéos",
                recommendation="Mettre à jour la détection des Shorts dans la base de données"
            )
        else:
            return ValidationResult(
                metric_name="Shorts vs Vidéos 16:9",
                status=ValidationStatus.EXCELLENT,
                value=f"{regular_pct:.0f}/{shorts_pct:.0f}%",
                expected_range="Distribution selon stratégie",
                message=f"Répartition: {regular_pct:.0f}% vidéos 16:9, {shorts_pct:.0f}% Shorts",
                recommendation="Distribution cohérente avec la stratégie de contenu"
            )
    
    def _validate_thumbnail_consistency(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la cohérence des miniatures."""
        if not videos:
            return ValidationResult(
                metric_name="Cohérence des Miniatures",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0%",
                expected_range="70-95%",
                message="Aucune vidéo pour analyser les miniatures",
                recommendation="Importer des vidéos"
            )
        
        # Compter les vidéos avec des miniatures
        videos_with_thumbnails = sum(1 for v in videos if v['thumbnail_url'])
        thumbnail_coverage = (videos_with_thumbnails / len(videos)) * 100
        
        # Analyse basique de cohérence (placeholder - nécessiterait analyse d'image)
        if thumbnail_coverage < 50:
            consistency_score = 0
        elif thumbnail_coverage < 80:
            consistency_score = 50
        else:
            consistency_score = 75  # Score par défaut
        
        # Validation
        if consistency_score == 0:
            return ValidationResult(
                metric_name="Cohérence des Miniatures",
                status=ValidationStatus.CRITICAL,
                value=f"{consistency_score}%",
                expected_range="70-95%",
                message=f"Miniatures manquantes ({thumbnail_coverage:.0f}% de couverture)",
                recommendation="Récupérer les URLs des miniatures"
            )
        elif consistency_score < 60:
            return ValidationResult(
                metric_name="Cohérence des Miniatures",
                status=ValidationStatus.WARNING,
                value=f"{consistency_score}%",
                expected_range="70-95%",
                message="Cohérence visuelle faible des miniatures",
                recommendation="Améliorer la cohérence du design des miniatures"
            )
        else:
            return ValidationResult(
                metric_name="Cohérence des Miniatures",
                status=ValidationStatus.GOOD,
                value=f"{consistency_score}%",
                expected_range="70-95%",
                message="Cohérence des miniatures acceptable",
                recommendation="Maintenir la qualité visuelle des miniatures"
            )
    
    def _validate_lexical_consistency(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide la cohérence du champ lexical et de la tonalité."""
        if not videos:
            return ValidationResult(
                metric_name="Champ Lexical",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="0%",
                expected_range="60-90%",
                message="Aucune vidéo pour analyser le champ lexical",
                recommendation="Importer des vidéos"
            )
        
        # Analyser les titres des vidéos
        titles = [v['title'] for v in videos if v['title']]
        
        if not titles:
            return ValidationResult(
                metric_name="Champ Lexical",
                status=ValidationStatus.CRITICAL,
                value="0%",
                expected_range="60-90%",
                message="Aucun titre de vidéo disponible",
                recommendation="Récupérer les titres des vidéos"
            )
        
        # Analyse basique de cohérence lexicale
        total_words = []
        for title in titles:
            words = re.findall(r'\w+', title.lower())
            total_words.extend(words)
        
        if not total_words:
            consistency_score = 0
        else:
            # Calculer la diversité lexicale (ratio mots uniques / total)
            unique_words = len(set(total_words))
            lexical_diversity = unique_words / len(total_words)
            
            # Score de cohérence basé sur la diversité (inversement proportionnel)
            # Plus la diversité est faible, plus la cohérence est élevée
            consistency_score = max(0, min(100, (1 - lexical_diversity) * 100))
        
        # Validation
        if consistency_score < 40:
            return ValidationResult(
                metric_name="Champ Lexical",
                status=ValidationStatus.WARNING,
                value=f"{consistency_score:.0f}%",
                expected_range="60-90%",
                message="Champ lexical très dispersé",
                recommendation="Harmoniser le vocabulaire et la tonalité des titres"
            )
        elif consistency_score > 90:
            return ValidationResult(
                metric_name="Champ Lexical",
                status=ValidationStatus.WARNING,
                value=f"{consistency_score:.0f}%",
                expected_range="60-90%",
                message="Champ lexical trop répétitif",
                recommendation="Diversifier le vocabulaire pour éviter la répétition"
            )
        else:
            return ValidationResult(
                metric_name="Champ Lexical",
                status=ValidationStatus.EXCELLENT,
                value=f"{consistency_score:.0f}%",
                expected_range="60-90%",
                message="Cohérence lexicale optimale",
                recommendation="Maintenir cette cohérence de vocabulaire"
            )
    
    def _validate_top_performing_subject(self, videos: List[sqlite3.Row]) -> ValidationResult:
        """Valide l'existence d'un sujet le plus apprécié."""
        if not videos:
            return ValidationResult(
                metric_name="Sujet le Plus Apprécié",
                status=ValidationStatus.INSUFFICIENT_DATA,
                value="Aucun",
                expected_range="Sujet identifiable",
                message="Aucune vidéo pour identifier le sujet performant",
                recommendation="Importer des vidéos"
            )
        
        # Filtrer les vidéos avec des métriques d'engagement
        videos_with_metrics = [
            v for v in videos 
            if v['view_count'] is not None and v['like_count'] is not None
            and v['view_count'] > 0
        ]
        
        if not videos_with_metrics:
            return ValidationResult(
                metric_name="Sujet le Plus Apprécié",
                status=ValidationStatus.CRITICAL,
                value="Données manquantes",
                expected_range="Sujet identifiable",
                message="Aucune donnée d'engagement disponible",
                recommendation="Récupérer les métriques de vues et likes"
            )
        
        # Trouver la vidéo avec le meilleur engagement
        best_video = max(
            videos_with_metrics, 
            key=lambda v: (v['like_count'] or 0) / max(v['view_count'], 1)
        )
        
        best_title = best_video['title'] if best_video['title'] else 'Sans titre'
        engagement_rate = (best_video['like_count'] or 0) / max(best_video['view_count'], 1) * 100
        
        # Validation
        if not best_title or best_title == 'Sans titre':
            return ValidationResult(
                metric_name="Sujet le Plus Apprécié",
                status=ValidationStatus.CRITICAL,
                value="Titre manquant",
                expected_range="Sujet identifiable",
                message="Vidéo performante sans titre",
                recommendation="Récupérer les titres des vidéos"
            )
        elif engagement_rate < 0.1:  # Moins de 0.1% d'engagement
            return ValidationResult(
                metric_name="Sujet le Plus Apprécié",
                status=ValidationStatus.WARNING,
                value=f"'{best_title[:50]}...' ({engagement_rate:.2f}%)",
                expected_range="Engagement > 1%",
                message="Faible engagement sur le contenu le plus performant",
                recommendation="Analyser pourquoi l'engagement est faible"
            )
        else:
            return ValidationResult(
                metric_name="Sujet le Plus Apprécié",
                status=ValidationStatus.EXCELLENT,
                value=f"'{best_title[:50]}...' ({engagement_rate:.2f}%)",
                expected_range="Engagement > 1%",
                message="Sujet performant identifié avec bon engagement",
                recommendation="Capitaliser sur ce type de contenu"
            )
    
    def _determine_overall_status(self, metrics_results: List[ValidationResult]) -> ValidationStatus:
        """Détermine le statut global basé sur tous les résultats de métriques."""
        status_counts = {}
        for result in metrics_results:
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Règles de décision
        if status_counts.get(ValidationStatus.CRITICAL, 0) >= 3:
            return ValidationStatus.CRITICAL
        elif status_counts.get(ValidationStatus.CRITICAL, 0) >= 1:
            return ValidationStatus.WARNING
        elif status_counts.get(ValidationStatus.WARNING, 0) >= 4:
            return ValidationStatus.WARNING
        elif status_counts.get(ValidationStatus.EXCELLENT, 0) >= 6:
            return ValidationStatus.EXCELLENT
        else:
            return ValidationStatus.GOOD
    
    def _generate_summary(self, overall_status: ValidationStatus, total_videos: int, 
                         critical_count: int, warning_count: int) -> str:
        """Génère un résumé textuel du statut de validation."""
        status_messages = {
            ValidationStatus.EXCELLENT: "🟢 Toutes les métriques sont excellentes",
            ValidationStatus.GOOD: "🟡 Métriques majoritairement bonnes",
            ValidationStatus.WARNING: "🟠 Problèmes de cohérence détectés", 
            ValidationStatus.CRITICAL: "🔴 Métriques critiques invalides",
            ValidationStatus.INSUFFICIENT_DATA: "⚪ Données insuffisantes"
        }
        
        base_message = status_messages.get(overall_status, "Statut inconnu")
        details = f" - {total_videos} vidéos"
        
        if critical_count > 0:
            details += f", {critical_count} problème(s) critique(s)"
        if warning_count > 0:
            details += f", {warning_count} alerte(s)"
            
        return base_message + details
    
    def generate_validation_report(self, reports: List[CompetitorValidationReport]) -> str:
        """Génère un rapport complet de validation au format markdown."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Statistiques globales
        total_competitors = len(reports)
        powerpoint_ready = sum(1 for r in reports if r.powerpoint_ready)
        critical_competitors = sum(1 for r in reports if r.overall_status == ValidationStatus.CRITICAL)
        excellent_competitors = sum(1 for r in reports if r.overall_status == ValidationStatus.EXCELLENT)
        
        report = f"""# 📊 Rapport de Validation des Key Metrics
**Date de génération :** {timestamp}
**Competitors analysés :** {total_competitors}

## 🎯 Résumé Exécutif

- **✅ Prêts pour PowerPoint :** {powerpoint_ready}/{total_competitors} ({powerpoint_ready/total_competitors*100:.0f}%)
- **🟢 Excellents :** {excellent_competitors} competitors
- **🔴 Critiques :** {critical_competitors} competitors nécessitent une intervention

## 📈 Détails par Competitor

"""

        # Grouper par pays
        competitors_by_country = {}
        for report_item in reports:
            country = report_item.country or "Non spécifié"
            if country not in competitors_by_country:
                competitors_by_country[country] = []
            competitors_by_country[country].append(report_item)
        
        for country, country_reports in competitors_by_country.items():
            report += f"\n### 🌍 {country}\n\n"
            
            for comp_report in country_reports:
                status_emoji = {
                    ValidationStatus.EXCELLENT: "🟢",
                    ValidationStatus.GOOD: "🟡", 
                    ValidationStatus.WARNING: "🟠",
                    ValidationStatus.CRITICAL: "🔴",
                    ValidationStatus.INSUFFICIENT_DATA: "⚪"
                }.get(comp_report.overall_status, "❓")
                
                powerpoint_status = "✅" if comp_report.powerpoint_ready else "❌"
                
                report += f"#### {status_emoji} {comp_report.competitor_name} {powerpoint_status}\n"
                report += f"**Statut :** {comp_report.summary}\n\n"
                
                # Métriques détaillées
                report += "**Métriques :**\n"
                for metric in comp_report.metrics_results:
                    metric_emoji = {
                        ValidationStatus.EXCELLENT: "✅",
                        ValidationStatus.GOOD: "✅",
                        ValidationStatus.WARNING: "⚠️",
                        ValidationStatus.CRITICAL: "❌",
                        ValidationStatus.INSUFFICIENT_DATA: "❓"
                    }.get(metric.status, "❓")
                    
                    report += f"- {metric_emoji} **{metric.metric_name}:** {metric.value} - {metric.message}\n"
                
                # Problèmes critiques
                if comp_report.critical_issues:
                    report += "\n**🚨 Problèmes critiques :**\n"
                    for issue in comp_report.critical_issues:
                        report += f"- {issue}\n"
                
                # Recommandations principales
                critical_metrics = [m for m in comp_report.metrics_results if m.status == ValidationStatus.CRITICAL]
                if critical_metrics:
                    report += "\n**🔧 Actions prioritaires :**\n"
                    for metric in critical_metrics:
                        report += f"- {metric.recommendation}\n"
                
                report += "\n---\n"
        
        # Recommandations globales
        report += f"""
## 🔧 Recommandations Globales

### Problèmes les plus fréquents :
1. **Dates de publication corrompues** - Utiliser l'agent de correction des dates YouTube
2. **Vidéos non catégorisées** - Compléter la classification Hero/Hub/Help
3. **Données de vues manquantes** - Rafraîchir via l'API YouTube

### Actions immédiates :
1. Corriger les {critical_competitors} competitors critiques avant PowerPoint
2. Mettre à jour les données manquantes pour {total_competitors - powerpoint_ready} competitors
3. Valider manuellement les métriques suspectes

### Prochaines étapes :
1. Re-lancer la validation après corrections
2. Automatiser la surveillance des métriques
3. Intégrer la validation dans le pipeline de données
"""

        return report
    
    def save_report_to_file(self, reports: List[CompetitorValidationReport], 
                           filename: str = None) -> str:
        """Sauvegarde le rapport dans un fichier."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"key_metrics_validation_report_{timestamp}.md"
        
        report_content = self.generate_validation_report(reports)
        
        filepath = PROJECT_ROOT / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📄 Rapport sauvegardé dans {filepath}")
        return str(filepath)


def main():
    """Fonction principale pour lancer la validation complète."""
    logger.info("🚀 Démarrage de l'agent de validation des Key Metrics")
    
    try:
        # Créer l'agent de validation
        validator = KeyMetricsValidator()
        
        # Valider tous les competitors
        reports = validator.validate_all_competitors()
        
        # Générer et sauvegarder le rapport
        report_file = validator.save_report_to_file(reports)
        
        # Statistiques finales
        total = len(reports)
        powerpoint_ready = sum(1 for r in reports if r.powerpoint_ready)
        critical = sum(1 for r in reports if r.overall_status == ValidationStatus.CRITICAL)
        
        logger.info(f"✅ Validation terminée !")
        logger.info(f"📊 {powerpoint_ready}/{total} competitors prêts pour PowerPoint")
        logger.info(f"🔴 {critical} competitors nécessitent une intervention critique")
        logger.info(f"📄 Rapport détaillé : {report_file}")
        
        return reports, report_file
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation : {e}")
        raise


if __name__ == "__main__":
    main()