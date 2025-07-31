"""
Module de base pour les connexions et utilitaires de base de données.
"""

import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path

# Obtenir le chemin absolu du projet
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_ROOT / 'instance'
DB_PATH = DB_DIR / 'database.db'


class DatabaseConnection:
    """Gestionnaire de connexions à la base de données."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_connection(self):
        """Créer une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
        return conn
    
    def __enter__(self):
        self.conn = self.get_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()


def get_db_connection(update_schema=True):
    """Crée une connexion à la base de données SQLite."""
    # S'assurer que le répertoire 'instance' existe
    if not DB_DIR.exists():
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Mettre à jour le schéma si nécessaire
    if update_schema:
        try:
            DatabaseSchema.update_database_schema(conn)
        except Exception as e:
            print(f"⚠️  Erreur lors de la mise à jour du schéma: {e}")
        
    return conn


class DatabaseUtils:
    """Utilitaires pour la base de données."""
    
    @staticmethod
    def extract_video_id_from_url(video_url: str) -> str:
        """Extraire l'ID vidéo depuis l'URL YouTube"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:v\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)
        
        # Fallback: utiliser l'URL complète comme ID
        return video_url.replace('/', '_').replace(':', '_')[:50]
    
    @staticmethod
    def extract_channel_id_from_url(channel_url: str) -> str:
        """Extraire l'ID de chaîne depuis l'URL YouTube"""
        if '/channel/' in channel_url:
            return channel_url.split('/channel/')[-1].split('/')[0].split('?')[0]
        elif '/@' in channel_url:
            return channel_url.split('/@')[-1].split('/')[0].split('?')[0]
        elif '/c/' in channel_url:
            return channel_url.split('/c/')[-1].split('/')[0].split('?')[0]
        elif '/user/' in channel_url:
            return channel_url.split('/user/')[-1].split('/')[0].split('?')[0]
        else:
            return channel_url.replace('/', '_').replace(':', '_')[:100]
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Détection très légère de la langue pour éviter une dépendance externe.
        Analyse quelques marqueurs courants FR / EN / DE / NL.
        """
        if not text:
            return 'en'

        text_lower = text.lower()
        # Mots très fréquents par langue
        french_markers = ['le ', 'la ', 'les ', 'des ', 'un ', 'une ', 'comment ', 'pour ', 'avec ']
        german_markers = ['der ', 'die ', 'das ', 'und ', 'mit ', 'eine ', 'ein ', 'wie ']
        dutch_markers = ['de ', 'het ', 'een ', 'hoe ', 'met ', 'en ']

        score_fr = sum(text_lower.count(m) for m in french_markers)
        score_de = sum(text_lower.count(m) for m in german_markers)
        score_nl = sum(text_lower.count(m) for m in dutch_markers)

        # Par défaut anglais si aucun score dominant
        if max(score_fr, score_de, score_nl) == 0:
            return 'en'

        if score_fr >= score_de and score_fr >= score_nl:
            return 'fr'
        if score_de >= score_fr and score_de >= score_nl:
            return 'de'
        return 'nl'
    
    @staticmethod
    def parse_duration_to_seconds(duration_text: str) -> Optional[int]:
        """Convertir une durée texte en secondes"""
        if not duration_text:
            return None
        
        try:
            # Convertir "2:45" en secondes
            parts = duration_text.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
        
        return None
    
    @staticmethod
    def parse_view_count(view_count) -> int:
        """Convertir un nombre de vues en entier"""
        if isinstance(view_count, str):
            view_count = int(re.sub(r'[^\d]', '', view_count)) if re.sub(r'[^\d]', '', view_count) else 0
        return view_count or 0
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parser une date depuis différents formats"""
        if not date_str:
            return None
        
        try:
            # Essayer de parser différents formats de date
            if 'il y a' in date_str:
                # Pour les dates relatives, utiliser la date actuelle
                return datetime.now()
            
            # Format ISO 8601 avec Z (timezone UTC) - convertir en naive
            if 'T' in date_str and date_str.endswith('Z'):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None)  # Convertir en naive pour compatibilité
            
            # Format ISO 8601 standard - convertir en naive si timezone présente
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            
            # Format date simple YYYY-MM-DD
            if '-' in date_str and len(date_str) == 10:
                return datetime.strptime(date_str, '%Y-%m-%d')
                
            # Autres formats possibles
            for fmt in ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
                    
        except Exception as e:
            print(f"[WARNING] Impossible de parser la date '{date_str}': {e}")
            
        # Ne PAS retourner datetime.now() - retourner None pour indiquer l'échec
        return None


class DatabaseSchema:
    """Gestion du schéma de la base de données."""
    
    @staticmethod
    def create_settings_table():
        """Créer la table des paramètres si elle n'existe pas"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def create_custom_rules_table():
        """Créer la table des règles personnalisées"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_classification_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                language TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern, category, language)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_database_schema(conn):
        """Mettre à jour le schéma de la base de données"""
        cursor = conn.cursor()
        
        try:
            # Créer les tables essentielles si elles n'existent pas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_classification_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    category TEXT NOT NULL,
                    language TEXT DEFAULT 'all',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pattern, category, language)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS background_tasks (
                    id TEXT PRIMARY KEY,
                    channel_url TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    current_step TEXT,
                    videos_found INTEGER DEFAULT 0,
                    videos_processed INTEGER DEFAULT 0,
                    total_estimated INTEGER DEFAULT 0,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    error_message TEXT,
                    channel_thumbnail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Ajouter des colonnes manquantes si nécessaire
            cursor.execute("PRAGMA table_info(video)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Ajouter la colonne is_short si elle n'existe pas
            if 'is_short' not in columns:
                cursor.execute('ALTER TABLE video ADD COLUMN is_short INTEGER DEFAULT 0')
                print("✅ Colonne 'is_short' ajoutée à la table video")
            
            # Ajouter la colonne youtube_published_at si elle n'existe pas
            if 'youtube_published_at' not in columns:
                cursor.execute('ALTER TABLE video ADD COLUMN youtube_published_at TEXT')
                print("✅ Colonne 'youtube_published_at' ajoutée à la table video")
            
            # Ajouter d'autres colonnes si nécessaire
            if 'classification_source' not in columns:
                cursor.execute('ALTER TABLE video ADD COLUMN classification_source TEXT DEFAULT "auto"')
                print("✅ Colonne 'classification_source' ajoutée à la table video")
            
            if 'is_human_validated' not in columns:
                cursor.execute('ALTER TABLE video ADD COLUMN is_human_validated INTEGER DEFAULT 0')
                print("✅ Colonne 'is_human_validated' ajoutée à la table video")
            
            # === PLAYLIST TABLE Upgrades ===
            cursor.execute("PRAGMA table_info(playlist)")
            playlist_cols = [col[1] for col in cursor.fetchall()]

            if 'classification_source' not in playlist_cols:
                cursor.execute('ALTER TABLE playlist ADD COLUMN classification_source TEXT')
                print("✅ Colonne 'classification_source' ajoutée à la table playlist")

            if 'is_human_validated' not in playlist_cols:
                cursor.execute('ALTER TABLE playlist ADD COLUMN is_human_validated INTEGER DEFAULT 0')
                print("✅ Colonne 'is_human_validated' ajoutée à la table playlist")

            if 'last_updated' not in playlist_cols:
                cursor.execute('ALTER TABLE playlist ADD COLUMN last_updated TIMESTAMP')
                print("✅ Colonne 'last_updated' ajoutée à la table playlist")

            if 'created_at' not in playlist_cols:
                cursor.execute('ALTER TABLE playlist ADD COLUMN created_at TIMESTAMP')
                print("✅ Colonne 'created_at' ajoutée à la table playlist")
            
            conn.commit()
            print("✅ Schéma de base de données mis à jour")
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du schéma: {e}")
            conn.rollback()


# Instances globales pour la compatibilité
db_utils = DatabaseUtils()
db_schema = DatabaseSchema()

# Fonctions de compatibilité
extract_video_id_from_url = db_utils.extract_video_id_from_url
extract_channel_id_from_url = db_utils.extract_channel_id_from_url
detect_language = db_utils.detect_language
update_database_schema = db_schema.update_database_schema 