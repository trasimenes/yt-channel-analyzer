import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
import os

@dataclass
class BackgroundTask:
    """Représente une tâche en arrière-plan"""
    id: str
    channel_url: str
    channel_name: str
    status: str  # 'running', 'completed', 'error', 'paused'
    progress: int  # 0-100
    current_step: str
    videos_found: int
    videos_processed: int
    total_estimated: int
    start_time: str
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    channel_thumbnail: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

class BackgroundTaskManager:
    """Gestionnaire des tâches en arrière-plan"""
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_file = "cache_recherches/background_tasks.json"
        self.stop_flags: Dict[str, bool] = {}  # Flags d'arrêt pour chaque tâche
        self.load_tasks()
    
    def load_tasks(self):
        """Charge les tâches depuis le fichier"""
        try:
            if os.path.exists(self.task_file):
                with open(self.task_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data:
                        task = BackgroundTask(**task_data)
                        # Marquer les tâches "running" comme interrompues au redémarrage
                        if task.status == 'running':
                            task.status = 'paused'
                        self.tasks[task.id] = task
        except Exception as e:
            print(f"[TASKS] Erreur lors du chargement des tâches: {e}")
    
    def save_tasks(self):
        """Sauvegarde les tâches dans le fichier"""
        try:
            os.makedirs(os.path.dirname(self.task_file), exist_ok=True)
            with open(self.task_file, 'w', encoding='utf-8') as f:
                tasks_data = [task.to_dict() for task in self.tasks.values()]
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TASKS] Erreur lors de la sauvegarde des tâches: {e}")
    
    def create_task(self, channel_url: str, channel_name: str) -> str:
        """Crée une nouvelle tâche"""
        task_id = str(uuid.uuid4())
        
        # Essayer de récupérer le thumbnail de la chaîne
        channel_thumbnail = None
        try:
            from .youtube_api_client import create_youtube_client
            youtube = create_youtube_client()
            channel_info = youtube.get_channel_info(channel_url)
            channel_thumbnail = channel_info.get('thumbnail', '')
            # Utiliser le nom officiel de la chaîne si disponible
            if channel_info.get('title'):
                channel_name = channel_info['title']
        except Exception as e:
            print(f"[TASKS] Impossible de récupérer les infos chaîne: {e}")
        
        task = BackgroundTask(
            id=task_id,
            channel_url=channel_url,
            channel_name=channel_name,
            status='running',
            progress=0,
            current_step='Initialisation...',
            videos_found=0,
            videos_processed=0,
            total_estimated=0,
            start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            channel_thumbnail=channel_thumbnail
        )
        self.tasks[task_id] = task
        self.save_tasks()
        return task_id
    
    def update_task(self, task_id: str, **kwargs):
        """Met à jour une tâche"""
        if task_id in self.tasks:
            for key, value in kwargs.items():
                if hasattr(self.tasks[task_id], key):
                    setattr(self.tasks[task_id], key, value)
            self.save_tasks()
    
    def complete_task(self, task_id: str, videos_processed: int):
        """Marque une tâche comme terminée"""
        self.update_task(
            task_id,
            status='completed',
            progress=100,
            current_step='Terminé',
            videos_processed=videos_processed,
            end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
    
    def error_task(self, task_id: str, error_message: str):
        """Marque une tâche comme échouée"""
        self.update_task(
            task_id,
            status='error',
            current_step='Erreur',
            error_message=error_message,
            end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Récupère une tâche par son ID"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[BackgroundTask]:
        """Récupère toutes les tâches"""
        return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[BackgroundTask]:
        """Récupère les tâches en cours"""
        return [task for task in self.tasks.values() if task.status == 'running']
    
    def cancel_task(self, task_id: str):
        """Annule une tâche en forçant l'arrêt"""
        # Déclencher le flag d'arrêt
        self.stop_flags[task_id] = True
        
        # Marquer comme annulée
        self.update_task(task_id, status='paused', current_step='Arrêt en cours...')
        
        # Nettoyer après 3 secondes
        def cleanup():
            time.sleep(3)
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.stop_flags:
                del self.stop_flags[task_id]
        
        threading.Thread(target=cleanup, daemon=True).start()
        print(f"[TASKS] Arrêt forcé demandé pour la tâche {task_id}")
    
    def resume_task(self, task_id: str):
        """Reprend une tâche interrompue depuis son état sauvegardé"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Tâche {task_id} non trouvée")
        
        if task.status == 'running':
            raise ValueError("Tâche déjà en cours")
        
        # Marquer comme en cours et reprendre
        self.update_task(
            task_id,
            status='running',
            current_step='Reprise de la tâche...',
            end_time=None  # Réinitialiser l'heure de fin
        )
        
        # Relancer le scraping
        self.start_background_scraping(task_id, task.channel_url)
        print(f"[TASKS] Tâche {task_id} reprise")
    
    def delete_task(self, task_id: str):
        """Supprime définitivement une tâche et ses données associées"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Tâche {task_id} non trouvée")
        
        # Arrêter la tâche si elle est en cours
        if task_id in self.running_tasks:
            self.cancel_task(task_id)
        
        # Supprimer les données du cache si elles existent
        try:
            from app import load_cache, save_cache, get_channel_key
            cache_data = load_cache()
            channel_key = get_channel_key(task.channel_url)
            
            if channel_key in cache_data:
                del cache_data[channel_key]
                save_cache(cache_data)
                print(f"[TASKS] Données de cache supprimées pour {channel_key}")
        except Exception as e:
            print(f"[TASKS] Erreur lors de la suppression du cache: {e}")
        
        # Supprimer la tâche
        del self.tasks[task_id]
        self.save_tasks()
        print(f"[TASKS] Tâche {task_id} supprimée définitivement")
    
    def clean_duplicate_tasks(self):
        """Nettoie les tâches en double en gardant celle avec le plus de vidéos"""
        print("[TASKS] 🧹 Début du nettoyage des doublons...")
        
        # Grouper les tâches par nom de chaîne ET par channel_id si disponible
        channel_groups = {}
        for task_id, task in self.tasks.items():
            # Utiliser le nom de chaîne comme clé principale
            channel_name = task.channel_name.lower().strip() if task.channel_name else "unknown"
            
            # Nettoyer le nom (enlever espaces multiples, caractères spéciaux)
            import re
            channel_name_clean = re.sub(r'[^\w\s]', '', channel_name).strip()
            channel_name_clean = re.sub(r'\s+', ' ', channel_name_clean)
            
            # Si le nom est trop générique, utiliser l'URL
            if channel_name_clean in ['unknown', 'canal sans nom', 'chaîne inconnue', '']:
                group_key = task.channel_url
            else:
                group_key = channel_name_clean
            
            if group_key not in channel_groups:
                channel_groups[group_key] = []
            channel_groups[group_key].append((task_id, task))
        
        tasks_to_delete = []
        duplicates_found = 0
        
        # Pour chaque groupe de chaînes
        for group_key, tasks_list in channel_groups.items():
            if len(tasks_list) > 1:
                duplicates_found += 1
                print(f"[TASKS] 🔍 Trouvé {len(tasks_list)} doublons pour '{group_key}':")
                
                # Afficher tous les doublons trouvés
                for task_id, task in tasks_list:
                    print(f"    - {task.channel_name} ({task.videos_found} vidéos, {task.start_time})")
                
                # Trier par nombre de vidéos (décroissant) puis par date (plus récent en premier)
                tasks_list.sort(key=lambda x: (
                    -x[1].videos_found,  # Plus de vidéos en premier (négatif pour desc)
                    -int(x[1].start_time.replace('-', '').replace(' ', '').replace(':', ''))  # Plus récent en premier
                ))
                
                # Garder le premier (celui avec le plus de vidéos et le plus récent)
                best_task_id, best_task = tasks_list[0]
                print(f"[TASKS] ✅ Garde: {best_task.channel_name} ({best_task.videos_found} vidéos, {best_task.start_time}) - URL: {best_task.channel_url}")
                
                # Marquer les autres pour suppression
                for task_id, task in tasks_list[1:]:
                    tasks_to_delete.append(task_id)
                    print(f"[TASKS] ❌ Supprime: {task.channel_name} ({task.videos_found} vidéos, {task.start_time}) - URL: {task.channel_url}")
        
        # Supprimer les doublons
        deleted_count = 0
        for task_id in tasks_to_delete:
            try:
                # Supprimer sans toucher au cache (pour préserver les données)
                del self.tasks[task_id]
                deleted_count += 1
            except KeyError:
                print(f"[TASKS] ⚠️ Tâche {task_id} déjà supprimée")
        
        # Sauvegarder les modifications
        if deleted_count > 0:
            self.save_tasks()
            print(f"[TASKS] 🎉 Nettoyage terminé: {deleted_count} doublons supprimés sur {duplicates_found} groupes")
        else:
            print("[TASKS] ✨ Aucun doublon trouvé")
        
        return deleted_count
    
    def start_background_scraping(self, task_id: str, channel_url: str):
        """Lance le scraping en arrière-plan pour une tâche"""
        if task_id in self.running_tasks:
            return  # Déjà en cours
        
        # Réinitialiser le flag d'arrêt
        self.stop_flags[task_id] = False
        
        thread = threading.Thread(
            target=self._background_scraping_worker,
            args=(task_id, channel_url),
            daemon=True
        )
        self.running_tasks[task_id] = thread
        thread.start()
    
    def _background_scraping_worker(self, task_id: str, channel_url: str):
        """Worker pour le scraping en arrière-plan avec API YouTube"""
        try:
            from .youtube_adapter import get_channel_videos_data_api_incremental_background
            from app import load_cache, get_channel_key, save_cache
            
            # Log du changement vers l'API
            print(f"[TASKS] 🚀 Utilisation de l'API YouTube pour la tâche {task_id}")
            
            # Charger les données existantes
            self.update_task(task_id, current_step='Chargement du cache...', progress=5)
            
            cache_data = load_cache()
            channel_key = get_channel_key(channel_url)
            existing_videos = []
            
            if channel_key in cache_data:
                existing_videos = cache_data[channel_key].get('videos', [])
            
            self.update_task(
                task_id, 
                current_step='Récupération via API YouTube...', 
                progress=10,
                videos_found=len(existing_videos)
            )
            
            # Lancer le scraping avec callback de progression
            def progress_callback(step: str, progress: int, videos_found: int, videos_processed: int):
                # Vérifier le flag d'arrêt
                if self.stop_flags.get(task_id, False):
                    self.update_task(task_id, status='paused', current_step='Arrêté par l\'utilisateur')
                    raise InterruptedError("Tâche arrêtée par l'utilisateur")
                
                self.update_task(
                    task_id,
                    current_step=step,
                    progress=progress,
                    videos_found=videos_found,
                    videos_processed=videos_processed
                )
            
            # Scraping complet en mode background avec API YouTube
            all_videos = get_channel_videos_data_api_incremental_background(
                channel_url, 
                existing_videos,
                progress_callback=progress_callback,
                task_id=task_id
            )
            
            # Sauvegarder les résultats (même si c'est partiel)
            self.update_task(task_id, current_step='Sauvegarde...', progress=95)
            
            print(f"[TASKS] 💾 Sauvegarde de {len(all_videos)} vidéos pour {channel_url}")
            
            # Mise à jour du cache avec toutes les vidéos
            from app import save_competitor_data
            try:
                save_competitor_data(channel_url, all_videos)
                print(f"[TASKS] ✅ Sauvegarde réussie pour {channel_url}")
            except Exception as save_error:
                print(f"[TASKS] ❌ Erreur de sauvegarde: {save_error}")
                import traceback
                traceback.print_exc()
            
            # Marquer comme terminé
            self.complete_task(task_id, len(all_videos))
            
            print(f"[TASKS] Tâche {task_id} terminée avec succès: {len(all_videos)} vidéos")
            
        except InterruptedError as e:
            # Tâche arrêtée volontairement
            self.update_task(task_id, status='paused', current_step='Arrêté par l\'utilisateur')
            print(f"[TASKS] Tâche {task_id} arrêtée par l'utilisateur")
        except Exception as e:
            error_msg = str(e)
            self.error_task(task_id, error_msg)
            print(f"[TASKS] Erreur dans la tâche {task_id}: {error_msg}")
        finally:
            # Nettoyer les références
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.stop_flags:
                del self.stop_flags[task_id]

# Instance globale du gestionnaire
task_manager = BackgroundTaskManager() 