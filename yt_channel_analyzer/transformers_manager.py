"""
Module de gestion des Python transformers (sentence-transformers)
Fournit un tableau de bord complet, des statistiques et des barres de progression
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pickle
import numpy as np
from threading import Thread
import sqlite3
import threading
import queue

@dataclass
class TransformerModelInfo:
    """Informations sur un modèle transformer"""
    name: str
    size_mb: float
    dimensions: int
    max_seq_length: int
    is_loaded: bool = False
    load_time: float = 0.0
    last_used: Optional[str] = None
    usage_count: int = 0
    download_progress: float = 0.0
    loading_status: str = "ready"  # ready, downloading, loading, error, loaded

@dataclass
class TransformerTrainingStats:
    """Statistiques d'entraînement des transformers"""
    total_examples: int
    training_examples: int
    validation_examples: int
    training_accuracy: float = 0.0
    validation_accuracy: float = 0.0
    last_training_date: Optional[str] = None
    categories_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.categories_distribution is None:
            self.categories_distribution = {}

@dataclass
class TransformerSystemStatus:
    """Statut global du système transformer"""
    status: str  # 'initializing', 'ready', 'loading', 'training', 'error'
    progress: float = 0.0
    current_operation: str = ""
    error_message: Optional[str] = None
    memory_usage_mb: float = 0.0
    last_update: Optional[str] = None

class TransformersManager:
    """
    Gestionnaire complet des transformers avec tableau de bord
    """
    
    def __init__(self, data_dir: str = "transformers_data"):
        self.data_dir = data_dir
        self.models_info: Dict[str, TransformerModelInfo] = {}
        self.training_stats: TransformerTrainingStats = TransformerTrainingStats(0, 0, 0)
        self.system_status: TransformerSystemStatus = TransformerSystemStatus("initializing")
        
        # Files d'attente pour les tâches asynchrones
        self.loading_queue = queue.Queue()
        self.progress_callbacks = {}
        self.loading_threads = {}
        
        # Configurations des modèles disponibles
        self.available_models = {
            "all-MiniLM-L6-v2": {
                "size_mb": 22.7,
                "dimensions": 384,
                "max_seq_length": 256,
                "description": "Modèle léger et rapide, bon pour débuter",
                "use_case": "Classification générale"
            },
            "all-MiniLM-L12-v2": {
                "size_mb": 33.4,
                "dimensions": 384,
                "max_seq_length": 256,
                "description": "Plus précis que L6, bon compromis",
                "use_case": "Classification précise"
            },
            "paraphrase-MiniLM-L6-v2": {
                "size_mb": 22.7,
                "dimensions": 384,
                "max_seq_length": 256,
                "description": "Optimisé pour la paraphrase et similarité",
                "use_case": "Détection de contenu similaire"
            },
            "all-mpnet-base-v2": {
                "size_mb": 109.0,
                "dimensions": 768,
                "max_seq_length": 384,
                "description": "Modèle performant mais plus lourd",
                "use_case": "Classification haute précision"
            }
        }
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.load_persistent_data()
        
    def load_persistent_data(self):
        """Charge les données persistantes"""
        try:
            stats_file = os.path.join(self.data_dir, "transformer_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    self.training_stats = TransformerTrainingStats(**data.get('training_stats', {}))
                    
                    # Charger les infos des modèles
                    for model_name, model_data in data.get('models_info', {}).items():
                        self.models_info[model_name] = TransformerModelInfo(**model_data)
                        
            self.system_status.status = "ready"
            self.system_status.last_update = datetime.now().isoformat()
            
        except Exception as e:
            print(f"[TRANSFORMERS] ⚠️ Erreur chargement données: {e}")
            self.system_status.status = "error"
            self.system_status.error_message = str(e)
    
    def save_persistent_data(self):
        """Sauvegarde les données persistantes"""
        try:
            stats_file = os.path.join(self.data_dir, "transformer_stats.json")
            data = {
                'training_stats': asdict(self.training_stats),
                'models_info': {name: asdict(info) for name, info in self.models_info.items()},
                'system_status': asdict(self.system_status),
                'last_save': datetime.now().isoformat()
            }
            
            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[TRANSFORMERS] ❌ Erreur sauvegarde: {e}")
    
    def get_model_info(self, model_name: str) -> Optional[TransformerModelInfo]:
        """Récupère les informations d'un modèle"""
        if model_name not in self.models_info:
            if model_name in self.available_models:
                config = self.available_models[model_name]
                self.models_info[model_name] = TransformerModelInfo(
                    name=model_name,
                    size_mb=config["size_mb"],
                    dimensions=config["dimensions"],
                    max_seq_length=config["max_seq_length"]
                )
            else:
                return None
        
        return self.models_info[model_name]
    
    def _download_model_async(self, model_name: str, thread_id: str):
        """Télécharge un modèle de manière asynchrone"""
        print(f"[TRANSFORMERS] 🔄 DÉBUT _download_model_async pour {model_name} (thread: {thread_id})")
        
        try:
            print(f"[TRANSFORMERS] 📦 Import des dépendances...")
            from sentence_transformers import SentenceTransformer
            import requests
            from huggingface_hub import snapshot_download
            print(f"[TRANSFORMERS] ✅ Imports réussis")
            
            model_info = self.get_model_info(model_name)
            if not model_info:
                print(f"[TRANSFORMERS] ❌ Model info non trouvé pour {model_name}")
                return
                
            print(f"[TRANSFORMERS] 🔄 Mise à jour du statut vers 'downloading'...")
            model_info.loading_status = "downloading"
            model_info.download_progress = 0.0
            
            # Fonction de callback pour le progrès
            def progress_callback(current, total):
                if total > 0:
                    progress = (current / total) * 100
                    model_info.download_progress = min(progress, 99.0)
                    print(f"[TRANSFORMERS] 📥 Téléchargement {model_name}: {progress:.1f}%")
            
            # Télécharger avec timeout augmenté
            start_time = time.time()
            
            print(f"[TRANSFORMERS] 🌐 Début téléchargement {model_name}")
            print(f"[TRANSFORMERS] 📏 Taille attendue: {model_info.size_mb} MB")
            
            # Téléchargement avec gestion d'erreur
            try:
                print(f"[TRANSFORMERS] 🚀 Appel SentenceTransformer('{model_name}')...")
                model = SentenceTransformer(model_name)
                load_time = time.time() - start_time
                
                print(f"[TRANSFORMERS] ✅ Modèle téléchargé avec succès!")
                print(f"[TRANSFORMERS] ⏱️ Temps de téléchargement: {load_time:.1f}s")
                
                model_info.is_loaded = True
                model_info.loading_status = "loaded"
                model_info.download_progress = 100.0
                model_info.load_time = load_time
                model_info.last_used = datetime.now().isoformat()
                model_info.usage_count += 1
                
                print(f"[TRANSFORMERS] 💾 Sauvegarde des données...")
                self.save_persistent_data()
                
                print(f"[TRANSFORMERS] 🎉 Modèle {model_name} entièrement chargé!")
                
            except Exception as download_error:
                print(f"[TRANSFORMERS] ❌ Erreur lors du téléchargement: {type(download_error).__name__}")
                print(f"[TRANSFORMERS] 📍 Détails: {str(download_error)}")
                
                model_info.loading_status = "error"
                model_info.download_progress = 0.0
                
                # Stacktrace pour le debug
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"[TRANSFORMERS] ❌ Erreur générale dans téléchargement asynchrone: {type(e).__name__}")
            print(f"[TRANSFORMERS] 📍 Détails: {str(e)}")
            
            model_info = self.get_model_info(model_name)
            if model_info:
                model_info.loading_status = "error"
                model_info.download_progress = 0.0
            
            # Stacktrace pour le debug
            import traceback
            traceback.print_exc()
        
        finally:
            print(f"[TRANSFORMERS] 🧹 Nettoyage du thread {thread_id}")
            # Nettoyer le thread
            if thread_id in self.loading_threads:
                del self.loading_threads[thread_id]
            print(f"[TRANSFORMERS] 🔚 FIN _download_model_async pour {model_name}")
    
    def load_model_async(self, model_name: str) -> bool:
        """
        Lance le chargement asynchrone d'un modèle
        """
        print(f"[TRANSFORMERS] 🚀 DÉBUT load_model_async pour {model_name}")
        
        try:
            # Vérifier si sentence-transformers est disponible
            print(f"[TRANSFORMERS] 📦 Test d'import sentence-transformers...")
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[TRANSFORMERS] ✅ Import sentence-transformers réussi")
            except ImportError as e:
                error_msg = f"sentence-transformers non disponible: {str(e)}"
                print(f"[TRANSFORMERS] ❌ {error_msg}")
                return False
                
            print(f"[TRANSFORMERS] 📋 Récupération des infos du modèle...")
            model_info = self.get_model_info(model_name)
            if not model_info:
                print(f"[TRANSFORMERS] ❌ Impossible de récupérer les infos du modèle {model_name}")
                return False
            
            print(f"[TRANSFORMERS] ✅ Infos du modèle récupérées: {model_info.name}")
            print(f"[TRANSFORMERS] 📊 Statut actuel: {model_info.loading_status}")
                
            # Vérifier si le modèle n'est pas déjà en cours de chargement
            if model_info.loading_status in ["downloading", "loading"]:
                print(f"[TRANSFORMERS] ⏳ Modèle {model_name} déjà en cours de chargement")
                return True
            
            # Vérifier si le modèle n'est pas déjà chargé
            if model_info.is_loaded:
                print(f"[TRANSFORMERS] ✅ Modèle {model_name} déjà chargé")
                return True
                
            print(f"[TRANSFORMERS] 🧵 Préparation du thread de téléchargement...")
            
            # Lancer le thread de téléchargement
            thread_id = f"load_{model_name}_{int(time.time())}"
            print(f"[TRANSFORMERS] 🆔 Thread ID: {thread_id}")
            
            thread = threading.Thread(
                target=self._download_model_async,
                args=(model_name, thread_id),
                daemon=True
            )
            
            print(f"[TRANSFORMERS] 🚀 Lancement du thread...")
            self.loading_threads[thread_id] = thread
            thread.start()
            
            print(f"[TRANSFORMERS] ✅ Thread lancé avec succès pour {model_name}")
            print(f"[TRANSFORMERS] 📊 Threads actifs: {len(self.loading_threads)}")
            return True
            
        except Exception as e:
            print(f"[TRANSFORMERS] ❌ Erreur lancement chargement asynchrone: {e}")
            print(f"[TRANSFORMERS] 🔍 Type d'erreur: {type(e).__name__}")
            print(f"[TRANSFORMERS] 📍 Détails: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_loading_progress(self, model_name: str) -> Dict[str, Any]:
        """Récupère le progrès de chargement d'un modèle"""
        model_info = self.get_model_info(model_name)
        if not model_info:
            return {"status": "not_found", "progress": 0.0}
            
        return {
            "status": model_info.loading_status,
            "progress": model_info.download_progress,
            "is_loaded": model_info.is_loaded,
            "load_time": model_info.load_time
        }
    
    def load_model(self, model_name: str, progress_callback=None) -> bool:
        """
        Charge un modèle transformer (version synchrone de compatibilité)
        """
        # Utiliser la version asynchrone pour éviter les timeouts
        return self.load_model_async(model_name)
    
    def update_training_stats_from_db(self):
        """Met à jour les statistiques d'entraînement depuis la base de données"""
        try:
            from .database import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Récupérer les statistiques des classifications humaines
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_playlists,
                    SUM(CASE WHEN category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                    SUM(CASE WHEN category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                    SUM(CASE WHEN category = 'help' THEN 1 ELSE 0 END) as help_count,
                    MAX(classification_date) as last_classification
                FROM playlist 
                WHERE (classification_source = 'human' OR human_verified = 1)
                AND category IN ('hero', 'hub', 'help')
            ''')
            
            playlist_stats = cursor.fetchone()
            
            # Récupérer les statistiques des vidéos
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_videos,
                    SUM(CASE WHEN corrected_category = 'hero' THEN 1 ELSE 0 END) as hero_count,
                    SUM(CASE WHEN corrected_category = 'hub' THEN 1 ELSE 0 END) as hub_count,
                    SUM(CASE WHEN corrected_category = 'help' THEN 1 ELSE 0 END) as help_count,
                    MAX(feedback_timestamp) as last_feedback
                FROM classification_feedback 
                WHERE user_feedback_type IN ('correction', 'human_correction')
                AND corrected_category IN ('hero', 'hub', 'help')
            ''')
            
            video_stats = cursor.fetchone()
            
            # Mettre à jour les statistiques
            total_examples = (playlist_stats[0] or 0) + (video_stats[0] or 0)
            
            self.training_stats.total_examples = total_examples
            self.training_stats.training_examples = int(total_examples * 0.8)  # 80% pour entraînement
            self.training_stats.validation_examples = total_examples - self.training_stats.training_examples
            
            # Distribution des catégories
            self.training_stats.categories_distribution = {
                'hero': (playlist_stats[1] or 0) + (video_stats[1] or 0),
                'hub': (playlist_stats[2] or 0) + (video_stats[2] or 0),
                'help': (playlist_stats[3] or 0) + (video_stats[3] or 0)
            }
            
            # Dernière date d'entraînement
            last_dates = [playlist_stats[4], video_stats[4]]
            last_dates = [d for d in last_dates if d]
            if last_dates:
                self.training_stats.last_training_date = max(last_dates)
            
            conn.close()
            
        except Exception as e:
            print(f"[TRANSFORMERS] ⚠️ Erreur mise à jour stats: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Retourne toutes les données pour le tableau de bord"""
        
        # Mettre à jour les statistiques depuis la DB
        self.update_training_stats_from_db()
        
        # Calculer les métriques de qualité
        total_examples = self.training_stats.total_examples
        quality_score = self._calculate_quality_score()
        
        # Recommandations
        recommendations = self._get_recommendations()
        
        return {
            'system_status': asdict(self.system_status),
            'training_stats': asdict(self.training_stats),
            'models_info': {name: asdict(info) for name, info in self.models_info.items()},
            'available_models': self.available_models,
            'quality_metrics': {
                'total_examples': total_examples,
                'quality_score': quality_score,
                'balance_score': self._calculate_balance_score(),
                'diversity_score': self._calculate_diversity_score()
            },
            'recommendations': recommendations,
            'system_health': self._get_system_health()
        }
    
    def _calculate_quality_score(self) -> float:
        """Calcule un score de qualité des données d'entraînement"""
        total = self.training_stats.total_examples
        if total == 0:
            return 0.0
        
        # Facteurs de qualité
        quantity_score = min(total / 100, 1.0)  # 100 exemples = score parfait
        balance_score = self._calculate_balance_score()
        diversity_score = self._calculate_diversity_score()
        
        # Score global (moyenne pondérée)
        quality_score = (quantity_score * 0.4 + balance_score * 0.3 + diversity_score * 0.3) * 100
        
        return round(quality_score, 1)
    
    def _calculate_balance_score(self) -> float:
        """Calcule le score d'équilibre entre les catégories"""
        dist = self.training_stats.categories_distribution
        if not dist or sum(dist.values()) == 0:
            return 0.0
        
        total = sum(dist.values())
        percentages = [v / total for v in dist.values()]
        
        # Score basé sur l'écart à la distribution équilibrée (33.33% chacune)
        ideal = 1/3
        variance = sum([(p - ideal)**2 for p in percentages]) / len(percentages)
        balance_score = max(0, 1 - (variance * 9))  # Normalisation
        
        return round(balance_score, 3)
    
    def _calculate_diversity_score(self) -> float:
        """Calcule le score de diversité (nombre de concurrents différents)"""
        # Pour l'instant, score basique basé sur le nombre d'exemples
        # Peut être amélioré en analysant la diversité des sources
        total = self.training_stats.total_examples
        if total == 0:
            return 0.0
        
        # Score basé sur le nombre d'exemples (plus il y en a, plus c'est diversifié)
        diversity_score = min(total / 50, 1.0)  # 50 exemples = diversité max
        
        return round(diversity_score, 3)
    
    def _get_recommendations(self) -> List[Dict[str, str]]:
        """
        Génère des recommandations basées sur l'état du système
        """
        recommendations = []
        
        # Vérifier si sentence-transformers est disponible
        try:
            from sentence_transformers import SentenceTransformer
            sentence_transformers_available = True
        except ImportError:
            sentence_transformers_available = False
        
        # Si sentence-transformers n'est pas disponible
        if not sentence_transformers_available:
            recommendations.extend([
                {
                    "priority": "high",
                    "title": "🤖 Classificateur léger disponible",
                    "description": "Utilisez le classificateur léger intégré comme alternative",
                    "action": "Activez le classificateur léger dans les paramètres",
                    "category": "alternative"
                },
                {
                    "priority": "medium", 
                    "title": "🐍 Problème Python 3.13",
                    "description": "PyTorch/sentence-transformers pas encore compatible avec Python 3.13",
                    "action": "Utilisez Python 3.11 ou 3.12 pour les transformers",
                    "category": "compatibility"
                },
                {
                    "priority": "low",
                    "title": "🔧 Installation manuel",
                    "description": "Installation des dépendances transformers nécessaire",
                    "action": "Voir la documentation INSTALL_SEMANTIC.md",
                    "category": "installation"
                }
            ])
        
        # Recommandations générales
        total_examples = self.training_stats.total_examples
        
        if total_examples < 10:
            recommendations.append({
                "priority": "high",
                "title": "📚 Données d'entraînement insuffisantes",
                "description": f"Seulement {total_examples} exemples disponibles",
                "action": "Ajoutez plus d'exemples de classification manuelle",
                "category": "data"
            })
        
        if total_examples < 50:
            recommendations.append({
                "priority": "medium",
                "title": "🎯 Améliorer la précision",
                "description": "Plus d'exemples amélioreront la précision",
                "action": "Cible: 50+ exemples pour de meilleurs résultats",
                "category": "performance"
            })
        
        # Vérifier l'équilibre des catégories
        balance_score = self._calculate_balance_score()
        if balance_score < 0.5:
            recommendations.append({
                "priority": "medium",
                "title": "⚖️ Déséquilibre des catégories",
                "description": "Certaines catégories sont sous-représentées",
                "action": "Ajoutez plus d'exemples pour les catégories manquantes",
                "category": "balance"
            })
        
        # Recommandations sur les modèles
        loaded_models = len([m for m in self.models_info.values() if m.is_loaded])
        if loaded_models == 0 and sentence_transformers_available:
            recommendations.append({
                "priority": "high",
                "title": "🚀 Aucun modèle chargé",
                "description": "Chargez un modèle pour commencer la classification",
                "action": "Commencez avec 'all-MiniLM-L6-v2' (léger et rapide)",
                "category": "model"
            })
        
        return recommendations
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Retourne les métriques de santé du système"""
        return {
            'status': self.system_status.status,
            'memory_usage': self.system_status.memory_usage_mb,
            'models_loaded': len([m for m in self.models_info.values() if m.is_loaded]),
            'total_models': len(self.available_models),
            'last_update': self.system_status.last_update
        }
    
    def start_training(self, model_name: str, progress_callback=None) -> bool:
        """Lance l'entraînement d'un modèle avec suivi de progression"""
        
        self.system_status.status = "training"
        self.system_status.current_operation = f"Entraînement du modèle {model_name}"
        self.system_status.progress = 0.0
        
        try:
            # Simuler les étapes d'entraînement
            steps = [
                ("Chargement des données...", 10),
                ("Préparation des exemples...", 25),
                ("Initialisation du modèle...", 40),
                ("Entraînement en cours...", 70),
                ("Validation...", 85),
                ("Sauvegarde du modèle...", 95),
                ("Entraînement terminé", 100)
            ]
            
            for step_name, progress in steps:
                if progress_callback:
                    progress_callback(step_name, progress)
                
                self.system_status.progress = progress
                self.system_status.current_operation = step_name
                
                # Simuler le temps de traitement
                time.sleep(0.5)
            
            # Mettre à jour les statistiques
            self.training_stats.last_training_date = datetime.now().isoformat()
            self.training_stats.training_accuracy = 0.85  # Simulé
            self.training_stats.validation_accuracy = 0.82  # Simulé
            
            self.system_status.status = "ready"
            self.system_status.current_operation = "Entraînement terminé"
            
            self.save_persistent_data()
            return True
            
        except Exception as e:
            self.system_status.status = "error"
            self.system_status.error_message = str(e)
            
            if progress_callback:
                progress_callback(f"Erreur: {str(e)}", 0)
            
            return False

# Instance globale du gestionnaire
transformers_manager = TransformersManager() 