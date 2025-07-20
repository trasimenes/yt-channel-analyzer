"""
Module de base de données refactorisé pour YT Channel Analyzer.

Ce module est divisé en plusieurs sous-modules pour une meilleure organisation :
- base.py : Connexions et utilitaires de base
- competitors.py : Gestion des concurrents
- videos.py : Gestion des vidéos
- analytics.py : Analyses et insights
- classification.py : Classification et patterns
"""

# Imports de base
from .base import (
    get_db_connection, DB_PATH, DatabaseConnection, DatabaseUtils, DatabaseSchema,
    extract_video_id_from_url, extract_channel_id_from_url, detect_language,
    update_database_schema as db_update_schema
)

# Fonction d'initialisation
def init_db():
    """Initialiser la base de données"""
    try:
        from .base import DatabaseSchema
        return DatabaseSchema.update_database_schema()
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        return False

# Imports des concurrents
from .competitors import (
    get_all_competitors, get_competitor_by_id, get_competitor_by_url,
    add_competitor, update_competitor, delete_competitor,
    get_all_competitors_urls, update_competitor_country, get_competitors_by_country,
    clean_duplicate_competitors, get_all_competitors_with_videos,
    competitors_to_legacy_format, save_competitor_playlists, get_competitor_playlists,
    save_subscriber_data, get_competitor_subscriber_data
)

# Imports des vidéos
from .videos import (
    get_competitor_videos, save_competitor_and_videos, link_playlist_videos,
    refresh_competitor_data, mark_human_classification, check_human_protection_status
)

# Imports des analyses
from .analytics import (
    generate_country_insights, generate_detailed_country_insights,
    calculate_publication_frequency, analyze_shorts_vs_regular_videos,
    generate_center_parcs_insights, get_country_insights
)

# Imports de classification
from .classification import (
    add_classification_pattern, remove_classification_pattern, normalize_pattern,
    classify_video_with_language, classify_videos_directly_with_keywords,
    reclassify_all_videos_with_multilingual_logic, classify_playlist_with_ai,
    auto_classify_uncategorized_playlists, apply_playlist_categories_to_videos_safe,
    verify_classification_integrity, fix_classification_tracking,
    get_ai_classification_setting, set_ai_classification_setting
)

# Fonctions manquantes à ajouter pour la compatibilité
def apply_playlist_categories_to_videos(competitor_id: int, specific_playlist_id: int = None):
    """Fonction de compatibilité pour apply_playlist_categories_to_videos"""
    return apply_playlist_categories_to_videos_safe(competitor_id, specific_playlist_id, False)

def update_playlist_category(playlist_id: int, category: str):
    """Mettre à jour la catégorie d'une playlist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE playlist 
            SET category = ?, classification_source = 'human', is_human_validated = 1, last_updated = ?
            WHERE id = ?
        ''', (category, __import__('datetime').datetime.now(), playlist_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de la catégorie: {e}")
        return False
    finally:
        conn.close()

def get_last_action_status(action_key: str):
    """Récupérer le statut de la dernière action"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT value FROM settings WHERE key = ?', (f'last_action_{action_key}',))
        result = cursor.fetchone()
        
        if result:
            import json
            return json.loads(result[0])
        else:
            return None
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du statut: {e}")
        return None
    finally:
        conn.close()

def set_last_action_status(action_key: str, value_dict: dict):
    """Définir le statut de la dernière action"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        import json
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (f'last_action_{action_key}', json.dumps(value_dict), __import__('datetime').datetime.now()))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la définition du statut: {e}")
        return False
    finally:
        conn.close()

def run_global_ai_classification():
    """Lancer la classification IA globale"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def force_manual_classification():
    """Forcer la classification manuelle"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def calculate_frequency_by_country():
    """Calculer la fréquence par pays"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def get_frequency_evolution_data(competitor_id: int, period_weeks: int = 12):
    """Récupérer les données d'évolution de fréquence"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

import sqlite3
from datetime import datetime

# --- Dates correction helpers ---

def _column_exists(table: str, column: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    exists = any(row[1] == column for row in cur.fetchall())
    conn.close()
    return exists


def get_dates_correction_status():
    """Retourne un dict avec l'état d'avancement de la correction des dates."""
    conn = get_db_connection()
    cur = conn.cursor()

    column_exists = _column_exists('video', 'youtube_published_at')
    if not column_exists:
        conn.close()
        return {
            'column_exists': False,
            'total_videos': 0,
            'corrected_videos': 0,
            'pending_videos': 0,
            'correction_percentage': 0.0
        }

    cur.execute("SELECT COUNT(*) FROM video")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM video WHERE youtube_published_at IS NOT NULL AND youtube_published_at != ''")
    corrected = cur.fetchone()[0]
    conn.close()

    pending = total - corrected
    percentage = (corrected / total * 100) if total else 0
    return {
        'column_exists': True,
        'total_videos': total,
        'corrected_videos': corrected,
        'pending_videos': pending,
        'correction_percentage': percentage
    }


def correct_all_video_dates_with_youtube_api(limit: int = 1000):
    """Corrige la colonne youtube_published_at en copiant published_at si vide (placeholder rapide)."""
    status = get_dates_correction_status()
    if not status['column_exists']:
        # créer colonne via update_database_schema
        tmp_conn = get_db_connection()
        DatabaseSchema.update_database_schema(tmp_conn)
        tmp_conn.close()

    conn = get_db_connection()
    cur = conn.cursor()
    # Copier published_at (si non nul) vers youtube_published_at lorsque manquant
    cur.execute("""
        UPDATE video
        SET youtube_published_at = published_at
        WHERE (youtube_published_at IS NULL OR youtube_published_at = '')
          AND published_at IS NOT NULL
        LIMIT ?
    """, (limit,))
    updated = conn.total_changes
    conn.commit()
    conn.close()

    return {
        'success': True,
        'message': f"Dates corrigées pour {updated} vidéos",
        'total_videos': status['total_videos'],
        'updated_videos': updated,
        'failed_videos': 0
    }

def analyze_frequency_impact_on_engagement():
    """Analyser l'impact de la fréquence sur l'engagement"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def analyze_category_frequency_patterns():
    """Analyser les patterns de fréquence par catégorie"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def get_inconsistency_stats():
    """Récupérer les statistiques d'incohérence"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def detect_data_inconsistencies(analysis_type: str = 'all'):
    """Détecter les incohérences dans les données"""
    # Placeholder pour la fonction manquante
    return []

def force_apply_human_playlist_to_videos(playlist_id: int, user_confirmation: bool = False):
    """Forcer l'application d'une playlist humaine aux vidéos"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def generate_shorts_insights_report(competitor_id: int):
    """Générer un rapport d'insights sur les Shorts"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def analyze_shorts_frequency_patterns(competitor_id: int = None):
    """Analyser les patterns de fréquence des Shorts"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def create_settings_table():
    """Créer la table des paramètres"""
    from .base import DatabaseSchema
    return DatabaseSchema.create_settings_table()

def create_custom_rules_table():
    """Créer la table des règles personnalisées"""
    from .base import DatabaseSchema
    return DatabaseSchema.create_custom_rules_table()

def update_competitor_tags(competitor_id: int, tags_data: dict):
    """Mettre à jour les tags d'un concurrent"""
    # Placeholder pour la fonction manquante
    return False

def calculate_publication_frequency_monthly(competitor_id: int = None, start_date=None, end_date=None):
    """Calculer la fréquence de publication mensuelle"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def update_database_schema_for_dates():
    """Mettre à jour le schéma de base de données pour les dates"""
    # Placeholder pour la fonction manquante
    return {'success': False, 'error': 'Fonction non implémentée'}

def add_custom_rule(pattern: str, category: str, language: str = 'all'):
    """Ajouter une règle personnalisée"""
    return add_classification_pattern(category, pattern, language)

def list_custom_rules(language: str = None):
    """Lister les règles personnalisées"""
    # Placeholder pour la fonction manquante
    return []

def remove_custom_rule(pattern: str, category: str, language: str = 'all'):
    """Supprimer une règle personnalisée"""
    return remove_classification_pattern(category, pattern, language) 

# Pour compatibilité : garder le nom historique
update_database_schema = db_update_schema

# Wrapper functions for classification patterns
def get_classification_patterns(language: str = None):
    """Wrapper pour récupérer les patterns de classification"""
    from .classification import ClassificationPatternManager
    manager = ClassificationPatternManager()
    return manager.get_classification_patterns(language)

def get_default_classification_patterns(language: str = 'fr'):
    """Wrapper pour récupérer les patterns par défaut"""
    from .classification import ClassificationPatternManager
    manager = ClassificationPatternManager()
    return manager.get_default_classification_patterns(language) 