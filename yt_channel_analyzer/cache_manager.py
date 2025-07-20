"""
Gestionnaire de cache Redis optimisé pour les performances
Utilise Redis pour cache, sessions et file d'attente de tâches
"""

import redis
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class RedisManager:
    """Gestionnaire Redis optimisé pour votre infrastructure 64Go RAM + 24 threads"""
    
    def __init__(self):
        # Configuration Redis pour o2switch
        self.redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'password': os.getenv('REDIS_PASSWORD'),
            'decode_responses': False,  # Pour gérer pickle
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'max_connections': 50,  # Pool de connexions
        }
        
        self.redis_client = None
        self.is_available = False
        self._connect()
    
    def _connect(self):
        """Connexion à Redis avec gestion d'erreurs"""
        try:
            self.redis_client = redis.Redis(**self.redis_config)
            # Test de connexion
            self.redis_client.ping()
            self.is_available = True
            logger.info("✅ Redis connecté avec succès")
        except Exception as e:
            logger.warning(f"❌ Redis non disponible: {e}")
            self.is_available = False
    
    def get(self, key: str, default=None) -> Any:
        """Récupère une valeur depuis Redis"""
        if not self.is_available:
            return default
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return default
            
            # Tenter de désérialiser avec pickle d'abord, puis JSON
            try:
                return pickle.loads(value)
            except:
                try:
                    return json.loads(value.decode('utf-8'))
                except:
                    return value.decode('utf-8')
        except Exception as e:
            logger.error(f"Erreur Redis GET {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Stocke une valeur dans Redis avec TTL"""
        if not self.is_available:
            return False
        
        try:
            # Sérialiser avec pickle pour les objets complexes
            if isinstance(value, (dict, list, tuple, set)):
                serialized_value = pickle.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = json.dumps(value).encode('utf-8')
            else:
                serialized_value = pickle.dumps(value)
            
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Erreur Redis SET {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Supprime une clé de Redis"""
        if not self.is_available:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Erreur Redis DELETE {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Supprime toutes les clés correspondant au pattern"""
        if not self.is_available:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Erreur Redis CLEAR PATTERN {pattern}: {e}")
            return 0

# Instance globale
redis_manager = RedisManager()

class CacheManager:
    """Gestionnaire de cache intelligent avec Redis"""
    
    @staticmethod
    def generate_cache_key(*args, **kwargs) -> str:
        """Génère une clé de cache unique"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    @staticmethod
    def cache_result(ttl: int = 3600, key_prefix: str = ""):
        """Décorateur pour cache automatique des résultats de fonction"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Générer clé de cache
                cache_key = f"{key_prefix}:{func.__name__}:{CacheManager.generate_cache_key(*args, **kwargs)}"
                
                # Tenter de récupérer depuis le cache
                cached_result = redis_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_result
                
                # Exécuter la fonction
                result = func(*args, **kwargs)
                
                # Stocker en cache
                redis_manager.set(cache_key, result, ttl)
                logger.debug(f"Cache SET: {cache_key}")
                
                return result
            return wrapper
        return decorator

class SessionManager:
    """Gestionnaire de sessions Redis"""
    
    @staticmethod
    def get_session_data(session_id: str) -> Dict:
        """Récupère les données de session"""
        key = f"session:{session_id}"
        return redis_manager.get(key, {})
    
    @staticmethod
    def set_session_data(session_id: str, data: Dict, ttl: int = 86400):
        """Stocke les données de session (24h par défaut)"""
        key = f"session:{session_id}"
        redis_manager.set(key, data, ttl)
    
    @staticmethod
    def delete_session(session_id: str):
        """Supprime une session"""
        key = f"session:{session_id}"
        redis_manager.delete(key)

class TaskQueue:
    """File d'attente de tâches Redis pour optimiser les 24 threads"""
    
    @staticmethod
    def add_task(task_data: Dict) -> bool:
        """Ajoute une tâche à la file d'attente"""
        if not redis_manager.is_available:
            return False
        
        try:
            task_json = json.dumps(task_data)
            redis_manager.redis_client.lpush("task_queue", task_json)
            return True
        except Exception as e:
            logger.error(f"Erreur ajout tâche: {e}")
            return False
    
    @staticmethod
    def get_next_task() -> Optional[Dict]:
        """Récupère la prochaine tâche"""
        if not redis_manager.is_available:
            return None
        
        try:
            task_json = redis_manager.redis_client.brpop("task_queue", timeout=1)
            if task_json:
                return json.loads(task_json[1])
            return None
        except Exception as e:
            logger.error(f"Erreur récupération tâche: {e}")
            return None
    
    @staticmethod
    def get_queue_size() -> int:
        """Retourne la taille de la file d'attente"""
        if not redis_manager.is_available:
            return 0
        
        try:
            return redis_manager.redis_client.llen("task_queue")
        except:
            return 0

# Cache spécialisés avec TTL optimisés pour vos 64Go RAM
class SpecializedCaches:
    """Caches spécialisés pour différents types de données"""
    
    # Cache vidéos (plus long car données stables)
    @staticmethod
    @CacheManager.cache_result(ttl=7200, key_prefix="videos")  # 2h
    def get_top_videos(limit=100, category=None, sort_by="view_count"):
        """Cache pour top vidéos - sera implémenté dans database"""
        pass
    
    # Cache concurrent (moyennement long)
    @staticmethod
    @CacheManager.cache_result(ttl=3600, key_prefix="competitors")  # 1h
    def get_competitors_stats():
        """Cache pour stats concurrents"""
        pass
    
    # Cache insights (court car données calculées)
    @staticmethod
    @CacheManager.cache_result(ttl=1800, key_prefix="insights")  # 30min
    def get_country_insights(country):
        """Cache pour insights pays"""
        pass
    
    # Cache API YouTube (très long car limité)
    @staticmethod
    @CacheManager.cache_result(ttl=86400, key_prefix="youtube_api")  # 24h
    def get_channel_info(channel_url):
        """Cache pour info chaîne YouTube"""
        pass

def clear_all_cache():
    """Vide tout le cache - utile pour maintenance"""
    patterns = ["videos:*", "competitors:*", "insights:*", "youtube_api:*"]
    total_cleared = 0
    
    for pattern in patterns:
        cleared = redis_manager.clear_pattern(pattern)
        total_cleared += cleared
        logger.info(f"Cache pattern {pattern}: {cleared} clés supprimées")
    
    return total_cleared

def get_cache_stats() -> Dict:
    """Statistiques du cache"""
    if not redis_manager.is_available:
        return {"status": "unavailable"}
    
    try:
        info = redis_manager.redis_client.info()
        return {
            "status": "connected",
            "used_memory": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": round(info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}