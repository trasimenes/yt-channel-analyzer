import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
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
    task_type: str = 'channel_analysis'  # 'channel_analysis', 'sentiment_analysis', etc.
    description: str = ''
    extra_data: dict = field(default_factory=dict)
    
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
    
    def start_generic_task(self, task_id: str, task_type: str, description: str, total_estimated: int = 0, extra_data: dict = None) -> str:
        """Crée une tâche générique (non-YouTube)"""
        
        task = BackgroundTask(
            id=task_id,
            channel_url=task_type,  # Utilise task_type comme identifiant
            channel_name=description,
            status='running',
            progress=0,
            current_step='Initialisation...',
            videos_found=0,
            videos_processed=0,
            total_estimated=total_estimated,
            start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            task_type=task_type,
            description=description,
            extra_data=extra_data or {}
        )
        self.tasks[task_id] = task
        self.save_tasks()
        return task_id
    
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
        
        # Permettre la reprise de plusieurs statuts
        allowed_statuses = ['paused', 'error', 'stopped', 'completed', 'failed']
        if task.status not in allowed_statuses:
            raise ValueError(f"Impossible de reprendre une tâche avec le statut '{task.status}'")
        
        print(f"[TASKS] Reprise de la tâche {task_id} depuis le statut '{task.status}'")
        
        # Marquer comme en cours et reprendre
        self.update_task(
            task_id,
            status='running',
            current_step='Reprise de la tâche...',
            end_time=None  # Réinitialiser l'heure de fin
        )
        
        # Relancer le scraping
        self.start_background_scraping(task_id, task.channel_url)
        print(f"[TASKS] Tâche {task_id} relancée avec succès")
    
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
            from .cache_utils import load_cache, save_cache, get_channel_key
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
    
    def start_background_scraping(self, task_id: str, channel_url: str, **kwargs):
        """Lance le scraping en arrière-plan pour une tâche
        
        Args:
            task_id: ID de la tâche
            channel_url: URL de la chaîne YouTube
            **kwargs: Paramètres supplémentaires (max_videos, etc.)
        """
        # 🚀 ACCEPTER les paramètres pour import complet
        max_videos = kwargs.get('max_videos', 1000)
        print(f"[TASKS] 📊 Paramètres reçus: max_videos={max_videos}")
            
        if task_id in self.running_tasks:
            return  # Déjà en cours
        
        # Réinitialiser le flag d'arrêt
        self.stop_flags[task_id] = False
        
        thread = threading.Thread(
            target=self._background_scraping_worker,
            args=(task_id, channel_url, max_videos),
            daemon=True
        )
        self.running_tasks[task_id] = thread
        thread.start()
    
    def _background_scraping_worker(self, task_id: str, channel_url: str, max_videos: int = 1000):
        """Worker pour le scraping en arrière-plan avec API YouTube"""
        try:
            from .youtube_adapter import get_channel_videos_data_api
            from .cache_utils import load_cache, get_channel_key, save_cache
            
            # Log du changement vers l'API
            print(f"[TASKS] 🚀 Utilisation de l'API YouTube pour la tâche {task_id}")
            self.update_task(task_id, current_step='🚀 Démarrage API YouTube...', progress=1)
            
            print(f"[TASKS] 📦 Import des modules terminé pour {task_id}")
            self.update_task(task_id, current_step='📦 Modules chargés...', progress=3)
            
            # Charger les données existantes
            print(f"[TASKS] 💾 Chargement du cache pour {task_id}")
            self.update_task(task_id, current_step='💾 Chargement du cache...', progress=5)
            
            cache_data = load_cache()
            print(f"[TASKS] 🔑 Génération clé channel pour {task_id}: {channel_url}")
            channel_key = get_channel_key(channel_url)
            existing_videos = []
            
            if channel_key in cache_data:
                existing_videos = cache_data[channel_key].get('videos', [])
                print(f"[TASKS] 📹 Vidéos existantes trouvées: {len(existing_videos)}")
            else:
                print(f"[TASKS] 🆕 Nouveau channel, aucune vidéo en cache")
            
            self.update_task(
                task_id, 
                current_step='🔍 Préparation API YouTube...', 
                progress=10,
                videos_found=len(existing_videos)
            )
            
            # Vérifier la clé API avant de continuer
            import os
            api_key = os.getenv('YOUTUBE_API_KEY')
            if not api_key:
                raise ValueError("❌ Clé API YouTube non configurée (YOUTUBE_API_KEY)")
            
            print(f"[TASKS] 🔑 Clé API trouvée: {api_key[:10]}...")
            print(f"[TASKS] 🎯 Lancement de l'API pour {channel_url}")
            self.update_task(task_id, current_step='🎯 Connexion API YouTube...', progress=15)
            
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
            print(f"[TASKS] ⚡ Appel get_channel_videos_data_api pour {task_id}")
            self.update_task(task_id, current_step='⚡ Récupération vidéos via API...', progress=20)
            
            try:
                # 🚀 UTILISER la limite reçue (0 = illimité)
                video_limit = max_videos if max_videos > 0 else 10000  # 0 = illimité = 10000 max pour sécurité
                print(f"[TASKS] 🎯 Limite vidéos: {video_limit} (max_videos={max_videos})")
                
                all_videos = get_channel_videos_data_api(
                    channel_url, 
                    video_limit=video_limit
                )
                print(f"[TASKS] ✅ API terminée, {len(all_videos) if all_videos else 0} vidéos récupérées")
                self.update_task(task_id, current_step='✅ Vidéos récupérées...', progress=60)
            except Exception as api_error:
                print(f"[TASKS] ❌ Erreur API: {api_error}")
                self.update_task(task_id, current_step=f'❌ Erreur API: {str(api_error)[:50]}...', progress=20)
                raise api_error
            
            # Mettre à jour le progress après récupération
            if all_videos:
                videos_found = len(all_videos)
                self.update_task(task_id, 
                    current_step=f'Processing {videos_found} videos...', 
                    progress=80,
                    videos_found=videos_found,
                    videos_processed=0
                )
            
            # Sauvegarder les résultats (même si c'est partiel)
            self.update_task(task_id, current_step='Sauvegarde...', progress=95)
            
            print(f"[TASKS] 💾 Sauvegarde de {len(all_videos)} vidéos pour {channel_url}")
            
            # Mise à jour du cache avec toutes les vidéos
            from .cache_utils import save_competitor_data
            try:
                competitor_id = save_competitor_data(channel_url, all_videos)
                print(f"[TASKS] ✅ Sauvegarde réussie pour {channel_url}")
                
                # 🚀 WORKFLOW AUTOMATIQUE COMPLET POST-IMPORT
                if competitor_id:
                    print(f"[TASKS] 🚀 Lancement du workflow automatique pour competitor_id: {competitor_id}")
                    try:
                        from .import_workflow import workflow_manager
                        
                        self.update_task(task_id, current_step='🚀 Workflow post-import...', progress=97)
                        
                        # Exécuter le workflow complet
                        workflow_results = workflow_manager.run_post_import_workflow(
                            competitor_id, channel_url
                        )
                        
                        # Afficher les résultats
                        print(f"[TASKS] ✅ Workflow terminé:")
                        for step_name, step_result in workflow_results['steps'].items():
                            status = step_result.get('status', 'unknown')
                            print(f"[TASKS]    - {step_name}: {status}")
                        
                    except Exception as workflow_error:
                        print(f"[TASKS] ⚠️ Erreur workflow (non critique): {workflow_error}")
                        import traceback
                        traceback.print_exc()
                    
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
            print(f"[TASKS] ❌ Erreur dans la tâche {task_id}: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Message d'erreur plus informatif selon le type
            if "YOUTUBE_API_KEY" in error_msg:
                user_error = "❌ Clé API YouTube manquante - Contactez l'admin"
            elif "quota" in error_msg.lower():
                user_error = "⚠️ Quota API dépassé - Réessayez demain"
            elif "forbidden" in error_msg.lower() or "403" in error_msg:
                user_error = "🚫 Accès refusé par YouTube"
            elif "not found" in error_msg.lower() or "404" in error_msg:
                user_error = "❓ Chaîne YouTube introuvable"
            else:
                user_error = f"❌ Erreur: {error_msg[:100]}..."
            
            self.error_task(task_id, user_error)
        finally:
            # Nettoyer les références
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.stop_flags:
                del self.stop_flags[task_id]

    def check_orphaned_tasks(self):
        """Vérifie les tâches dont les concurrents n'existent plus en base de données"""
        try:
            from .database import get_all_competitors_urls
            
            # Récupérer toutes les URLs des concurrents en base
            db_urls = set(get_all_competitors_urls())
            
            orphaned_tasks = []
            for task_id, task in self.tasks.items():
                # Vérifier si l'URL de la tâche existe en base
                if task.channel_url not in db_urls:
                    orphaned_tasks.append(task)
            
            return orphaned_tasks
            
        except Exception as e:
            print(f"[TASKS] Erreur lors de la vérification des tâches orphelines: {e}")
            return []
    
    def get_all_tasks_with_warnings(self):
        """Récupère toutes les tâches avec des avertissements pour les concurrents manquants"""
        tasks = self.get_all_tasks()
        orphaned_tasks = self.check_orphaned_tasks()
        orphaned_ids = {task.id for task in orphaned_tasks}
        
        # Pour chaque tâche orpheline, essayer d'ajouter le concurrent automatiquement
        for task in tasks:
            if task.id in orphaned_ids:
                # Vérifier d'abord si le concurrent existe maintenant
                try:
                    from .database import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM concurrent WHERE channel_url = ?", (task.channel_url,))
                    exists = cursor.fetchone()[0] > 0
                    conn.close()
                    
                    if exists:
                        # Le concurrent existe maintenant, plus besoin d'afficher l'avertissement
                        task.warning = None
                        continue
                        
                except Exception as e:
                    print(f"[TASKS] Erreur lors de la vérification du concurrent: {e}")
                
                # Essayer d'ajouter le concurrent automatiquement seulement s'il n'existe pas
                try:
                    from .database import add_competitor
                    
                    # Extraire le nom depuis l'URL ou utiliser le nom de la tâche
                    channel_name = task.channel_name or task.channel_url.split('/')[-1]
                    
                    # Ne pas traiter automatiquement certains concurrents connus
                    known_competitors = ['hilton', 'marriott', 'hyatt', 'tui deutschland']
                    if any(known in channel_name.lower() for known in known_competitors):
                        # Ne pas afficher de warning pour les concurrents connus qui sont déjà analysés
                        task.warning = None
                        continue
                    
                    # Déterminer le pays en fonction du nom
                    country = 'International'  # Par défaut
                    if any(word in channel_name.upper() for word in ['ARD', 'REISEN', 'DEUTSCHLAND', 'GERMAN']):
                        country = 'Germany'
                    elif any(word in channel_name.upper() for word in ['HILTON', 'MARRIOTT', 'HYATT']):
                        country = 'International'
                    
                    # Ajouter le concurrent
                    competitor_data = {
                        'name': channel_name,
                        'channel_url': task.channel_url,
                        'country': country
                    }
                    result = add_competitor(competitor_data)
                    if result:
                        print(f"[TASKS] ✅ Concurrent '{channel_name}' ajouté automatiquement en base de données")
                        
                        # Lancer automatiquement l'analyse complète
                        try:
                            from .scraper import scrape_and_classify_channel
                            from .semantic_classifier import AdvancedSemanticClassifier
                            
                            print(f"[TASKS] 🔄 Lancement de l'analyse complète pour '{channel_name}'...")
                            
                            # Récupérer les playlists et vidéos
                            playlists_data = scrape_and_classify_channel(task.channel_url)
                            
                            # Classifier avec l'IA
                            classifier = AdvancedSemanticClassifier()
                            classifier.classify_all_unclassified()
                            
                            # Calculer les statistiques du concurrent
                            from .database import get_db_connection
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            
                            # Obtenir l'ID du concurrent ajouté
                            cursor.execute("SELECT id FROM concurrent WHERE channel_url = ?", (task.channel_url,))
                            competitor_id = cursor.fetchone()[0]
                            
                            # Calculer et insérer les statistiques
                            from scripts.update_competitor_stats import update_competitor_stats
                            update_competitor_stats(competitor_id)
                            
                            conn.close()
                            
                            print(f"[TASKS] ✅ Analyse complète terminée pour '{channel_name}'")
                            task.warning = f"✅ Concurrent ajouté et analysé ({country})"
                            
                        except Exception as e:
                            print(f"[TASKS] ⚠️ Concurrent ajouté mais erreur lors de l'analyse: {e}")
                            task.warning = f"✅ Concurrent ajouté ({country}) - Analyse manuelle requise"
                    else:
                        task.warning = None  # Ne plus afficher le message d'erreur pour éviter la pollution
                except Exception as e:
                    print(f"[TASKS] ❌ Erreur lors de l'ajout automatique du concurrent: {e}")
                    task.warning = None  # Ne plus afficher le message d'erreur pour éviter la pollution
            else:
                task.warning = None
        
        return tasks

# Instance globale du gestionnaire
task_manager = BackgroundTaskManager() 