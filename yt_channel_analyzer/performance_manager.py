"""
Gestionnaire de performance optimisé pour infrastructure haute performance
24 threads CPU + 64Go RAM + Redis
"""

import threading
import concurrent.futures
import queue
import time
import psutil
import os
from typing import List, Dict, Callable, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass
from .cache_manager import redis_manager, TaskQueue

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métriques de performance"""
    cpu_usage: float
    memory_usage: float
    active_threads: int
    queue_size: int
    cache_hit_rate: float
    timestamp: datetime

class ThreadPoolManager:
    """Gestionnaire optimisé de pool de threads pour 24 cores"""
    
    def __init__(self, max_workers: int = 20):  # Garde 4 threads pour l'OS
        self.max_workers = min(max_workers, 20)  # Sécurité
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="YTAnalyzer"
        )
        self.active_tasks = {}
        self.completed_tasks = 0
        self.failed_tasks = 0
        self._lock = threading.Lock()
        
        logger.info(f"🚀 ThreadPool initialisé avec {self.max_workers} workers")
    
    def submit_task(self, func: Callable, *args, task_id: str = None, **kwargs) -> str:
        """Soumet une tâche au pool de threads"""
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"
        
        future = self.executor.submit(self._execute_with_metrics, func, task_id, *args, **kwargs)
        
        with self._lock:
            self.active_tasks[task_id] = {
                'future': future,
                'start_time': datetime.now(),
                'function': func.__name__
            }
        
        return task_id
    
    def _execute_with_metrics(self, func: Callable, task_id: str, *args, **kwargs):
        """Exécute une fonction avec métriques"""
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                self.completed_tasks += 1
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            
            execution_time = time.time() - start_time
            logger.debug(f"✅ Tâche {task_id} terminée en {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            with self._lock:
                self.failed_tasks += 1
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            
            logger.error(f"❌ Tâche {task_id} échouée: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Récupère le statut d'une tâche"""
        with self._lock:
            if task_id not in self.active_tasks:
                return None
            
            task = self.active_tasks[task_id]
            future = task['future']
            
            return {
                'task_id': task_id,
                'status': 'done' if future.done() else 'running',
                'start_time': task['start_time'],
                'function': task['function'],
                'result': future.result() if future.done() and not future.exception() else None,
                'error': str(future.exception()) if future.done() and future.exception() else None
            }
    
    def get_stats(self) -> Dict:
        """Statistiques du pool de threads"""
        with self._lock:
            return {
                'max_workers': self.max_workers,
                'active_tasks': len(self.active_tasks),
                'completed_tasks': self.completed_tasks,
                'failed_tasks': self.failed_tasks,
                'success_rate': round(self.completed_tasks / max(self.completed_tasks + self.failed_tasks, 1) * 100, 2)
            }

class BatchProcessor:
    """Processeur de batch optimisé pour les grosses opérations"""
    
    def __init__(self, thread_pool: ThreadPoolManager):
        self.thread_pool = thread_pool
    
    def process_competitors_batch(self, competitor_ids: List[int], batch_size: int = 5) -> List[str]:
        """Traite un batch de concurrents en parallèle"""
        task_ids = []
        
        # Diviser en lots pour éviter la surcharge
        for i in range(0, len(competitor_ids), batch_size):
            batch = competitor_ids[i:i + batch_size]
            
            for competitor_id in batch:
                task_id = self.thread_pool.submit_task(
                    self._process_single_competitor,
                    competitor_id,
                    task_id=f"competitor_{competitor_id}"
                )
                task_ids.append(task_id)
        
        return task_ids
    
    def _process_single_competitor(self, competitor_id: int):
        """Traite un concurrent (à implémenter selon vos besoins)"""
        # Placeholder - sera implémenté avec votre logique
        from .database import refresh_competitor_data
        return refresh_competitor_data(competitor_id)
    
    def process_videos_classification_batch(self, video_ids: List[int], batch_size: int = 10) -> List[str]:
        """Classifie un batch de vidéos en parallèle"""
        task_ids = []
        
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            
            task_id = self.thread_pool.submit_task(
                self._classify_videos_batch,
                batch,
                task_id=f"classify_batch_{i}"
            )
            task_ids.append(task_id)
        
        return task_ids
    
    def _classify_videos_batch(self, video_ids: List[int]):
        """Classifie un lot de vidéos"""
        # Placeholder - sera implémenté avec votre classificateur
        from .semantic_classifier import classify_videos_batch
        return classify_videos_batch(video_ids)

class PerformanceMonitor:
    """Moniteur de performance système"""
    
    def __init__(self):
        self.metrics_history = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: int = 30):
        """Démarre le monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"📊 Monitoring démarré (intervalle: {interval}s)")
    
    def stop_monitoring(self):
        """Arrête le monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval: int):
        """Boucle de monitoring"""
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Garder seulement les 100 dernières métriques
                if len(self.metrics_history) > 100:
                    self.metrics_history.pop(0)
                
                # Log d'alerte si ressources élevées
                if metrics.cpu_usage > 80:
                    logger.warning(f"🔥 CPU usage élevé: {metrics.cpu_usage}%")
                
                if metrics.memory_usage > 85:
                    logger.warning(f"🔥 Memory usage élevé: {metrics.memory_usage}%")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Erreur monitoring: {e}")
                time.sleep(interval)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Récupère les métriques actuelles"""
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Compter les threads actifs de l'application
        current_process = psutil.Process()
        active_threads = current_process.num_threads()
        
        # Taille de la file d'attente Redis
        queue_size = TaskQueue.get_queue_size()
        
        # Taux de hit du cache
        from .cache_manager import get_cache_stats
        cache_stats = get_cache_stats()
        cache_hit_rate = cache_stats.get('hit_rate', 0)
        
        return PerformanceMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            active_threads=active_threads,
            queue_size=queue_size,
            cache_hit_rate=cache_hit_rate,
            timestamp=datetime.now()
        )
    
    def get_performance_report(self) -> Dict:
        """Génère un rapport de performance"""
        if not self.metrics_history:
            return {"error": "Aucune métrique disponible"}
        
        recent_metrics = self.metrics_history[-10:]  # 10 dernières mesures
        
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            "current": self.get_current_metrics().__dict__,
            "averages": {
                "cpu_usage": round(avg_cpu, 2),
                "memory_usage": round(avg_memory, 2),
                "cache_hit_rate": round(avg_cache_hit, 2)
            },
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_memory_gb": round(psutil.virtual_memory().available / (1024**3), 2)
            }
        }

class OptimizedDatabaseManager:
    """Gestionnaire de base de données optimisé"""
    
    def __init__(self, thread_pool: ThreadPoolManager):
        self.thread_pool = thread_pool
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialise un pool de connexions à la base"""
        from .database import get_db_connection
        
        # Créer 5 connexions en pool pour éviter les conflits
        for i in range(5):
            try:
                conn = get_db_connection()
                self.connection_pool.append(conn)
            except Exception as e:
                logger.error(f"Erreur création connexion pool: {e}")
    
    def get_connection(self):
        """Récupère une connexion du pool"""
        with self.pool_lock:
            if self.connection_pool:
                return self.connection_pool.pop()
            else:
                # Fallback: créer une nouvelle connexion
                from .database import get_db_connection
                return get_db_connection()
    
    def return_connection(self, conn):
        """Remet une connexion dans le pool"""
        with self.pool_lock:
            if len(self.connection_pool) < 5:
                self.connection_pool.append(conn)
            else:
                conn.close()

# Instances globales optimisées pour votre infrastructure
thread_pool_manager = ThreadPoolManager(max_workers=20)  # 20 sur 24 threads
batch_processor = BatchProcessor(thread_pool_manager)
performance_monitor = PerformanceMonitor()
database_manager = OptimizedDatabaseManager(thread_pool_manager)

# Démarrer le monitoring automatiquement
performance_monitor.start_monitoring(interval=60)  # Toutes les minutes

def get_optimization_status() -> Dict:
    """Retourne le statut d'optimisation général"""
    return {
        "thread_pool": thread_pool_manager.get_stats(),
        "performance": performance_monitor.get_performance_report(),
        "redis": redis_manager.is_available,
        "cache_stats": get_cache_stats() if redis_manager.is_available else {},
        "timestamp": datetime.now().isoformat()
    }

def optimize_for_production():
    """Optimisations spécifiques pour la production"""
    logger.info("🚀 Activation des optimisations production...")
    
    # Augmenter les workers si en production
    if os.getenv('ENVIRONMENT') == 'production':
        global thread_pool_manager
        thread_pool_manager = ThreadPoolManager(max_workers=22)  # Plus agressif en prod
        logger.info("📈 Thread pool étendu à 22 workers pour la production")
    
    # Précharger les caches critiques
    _preload_critical_caches()
    
    logger.info("✅ Optimisations production activées")

def _preload_critical_caches():
    """Précharge les caches les plus utilisés"""
    try:
        # Lancer le préchargement en arrière-plan
        thread_pool_manager.submit_task(_preload_competitors_cache, task_id="preload_competitors")
        thread_pool_manager.submit_task(_preload_top_videos_cache, task_id="preload_videos")
        logger.info("🔄 Préchargement des caches lancé")
    except Exception as e:
        logger.error(f"Erreur préchargement caches: {e}")

def _preload_competitors_cache():
    """Précharge le cache des concurrents"""
    from .database.competitors import get_all_competitors_with_stats
    get_all_competitors_with_stats()

def _preload_top_videos_cache():
    """Précharge le cache des top vidéos"""
    from .database.videos import get_top_videos
    get_top_videos(limit=100)