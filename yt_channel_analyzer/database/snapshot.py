"""
Module de snapshot pour sauvegarder l'état complet de la base de données
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
from .base import get_db_connection

class DatabaseSnapshot:
    """Gestionnaire de snapshots de base de données"""
    
    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)
    
    def create_snapshot(self) -> Dict[str, Any]:
        """
        Crée un snapshot complet de toutes les données
        
        Returns:
            Dict contenant toutes les données et métadonnées
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        snapshot = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "tables": {}
            },
            "data": {}
        }
        
        # Tables à sauvegarder
        tables = [
            "concurrent",
            "playlist", 
            "video",
            "playlist_video",
            "classification_feedback",
            "classification_patterns",
            "custom_classification_rules",
            "learned_patterns",
            "competitor_stats",
            "competitor_frequency_stats",
            "competitor_detailed_stats",
            "model_performance"
        ]
        
        for table in tables:
            try:
                # Récupérer le schéma
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Récupérer les données
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                # Convertir en dictionnaires
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convertir les dates en ISO format si nécessaire
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        row_dict[col] = value
                    data.append(row_dict)
                
                snapshot["data"][table] = data
                snapshot["metadata"]["tables"][table] = {
                    "count": len(data),
                    "columns": columns
                }
                
            except Exception as e:
                print(f"⚠️ Erreur lors du snapshot de {table}: {e}")
                snapshot["metadata"]["tables"][table] = {"error": str(e)}
        
        conn.close()
        
        # Sauvegarder le snapshot
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.snapshot_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        
        snapshot["metadata"]["filename"] = filename
        snapshot["metadata"]["filepath"] = filepath
        
        return snapshot
    
    def list_snapshots(self) -> list:
        """Liste tous les snapshots disponibles"""
        snapshots = []
        for filename in os.listdir(self.snapshot_dir):
            if filename.startswith("snapshot_") and filename.endswith(".json"):
                filepath = os.path.join(self.snapshot_dir, filename)
                # Extraire la date du nom de fichier
                date_str = filename.replace("snapshot_", "").replace(".json", "")
                try:
                    date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                    snapshots.append({
                        "filename": filename,
                        "date": date.isoformat(),
                        "size": os.path.getsize(filepath)
                    })
                except:
                    pass
        
        return sorted(snapshots, key=lambda x: x["date"], reverse=True)
    
    def restore_snapshot(self, filename: str) -> bool:
        """
        Restaure un snapshot (à implémenter avec précaution)
        
        Args:
            filename: Nom du fichier snapshot
            
        Returns:
            True si succès, False sinon
        """
        # TODO: Implémenter la restauration avec confirmation
        # Pour l'instant, juste retourner le contenu
        filepath = os.path.join(self.snapshot_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_snapshot_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'état actuel de la base"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "statistics": {}
        }
        
        # Statistiques principales
        queries = {
            "total_concurrents": "SELECT COUNT(*) FROM concurrent",
            "total_playlists": "SELECT COUNT(*) FROM playlist",
            "total_videos": "SELECT COUNT(*) FROM video",
            "classified_playlists": "SELECT COUNT(*) FROM playlist WHERE category IS NOT NULL",
            "human_validated_playlists": "SELECT COUNT(*) FROM playlist WHERE is_human_validated = 1",
            "classified_videos": "SELECT COUNT(*) FROM video WHERE category IS NOT NULL",
            "human_validated_videos": "SELECT COUNT(*) FROM video WHERE is_human_validated = 1"
        }
        
        for key, query in queries.items():
            cursor.execute(query)
            summary["statistics"][key] = cursor.fetchone()[0]
        
        # Distribution par catégorie
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM playlist 
            WHERE category IS NOT NULL 
            GROUP BY category
        """)
        summary["playlist_distribution"] = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM video 
            WHERE category IS NOT NULL 
            GROUP BY category
        """)
        summary["video_distribution"] = dict(cursor.fetchall())
        
        conn.close()
        return summary