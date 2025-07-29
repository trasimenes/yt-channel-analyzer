/**
 * Système de rafraîchissement global avec barre de progression Ajax
 * Fonctionne sur toutes les pages de l'application
 */

let globalRefreshInterval = null;

function showGlobalProgressBar() {
    // Créer la barre de progression en bas de l'écran
    const existingBar = document.getElementById('global-progress-bar');
    if (existingBar) {
        existingBar.remove();
    }
    
    const progressBar = document.createElement('div');
    progressBar.id = 'global-progress-bar';
    progressBar.innerHTML = `
        <div style="position: fixed; bottom: 0; left: 0; right: 0; z-index: 10000; 
                    background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
                    border-top: 1px solid #e7e7ff; padding: 15px 20px; box-shadow: 0 -4px 20px rgba(0,0,0,0.1);">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm text-primary me-3" role="status"></div>
                    <div>
                        <div class="fw-bold text-primary">🔄 Rafraîchissement Global des Données</div>
                        <small class="text-muted" id="progress-message">Initialisation...</small>
                    </div>
                </div>
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-3" id="progress-percent">0%</span>
                    <button class="btn btn-sm btn-outline-secondary" onclick="hideGlobalProgressBar()" title="Masquer (le processus continue)">
                        <i class="bx bx-x"></i>
                    </button>
                </div>
            </div>
            <div class="progress" style="height: 8px; border-radius: 4px;">
                <div class="progress-bar bg-primary progress-bar-striped progress-bar-animated" 
                     id="progress-fill" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                </div>
            </div>
            <div class="mt-2">
                <small class="text-muted">
                    <i class="bx bx-info-circle me-1"></i>
                    Import API → Création liens → Propagation classifications
                </small>
            </div>
        </div>
    `;
    
    document.body.appendChild(progressBar);
    
    // Décaler le contenu pour ne pas masquer la barre
    document.body.style.paddingBottom = '140px';
}

function hideGlobalProgressBar() {
    const progressBar = document.getElementById('global-progress-bar');
    if (progressBar) {
        progressBar.remove();
    }
    document.body.style.paddingBottom = '0';
    
    if (globalRefreshInterval) {
        clearInterval(globalRefreshInterval);
        globalRefreshInterval = null;
    }
}

function updateGlobalProgress(status) {
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressMessage = document.getElementById('progress-message');
    
    if (progressFill && progressPercent && progressMessage) {
        const percent = status.progress_percent || 0;
        
        progressFill.style.width = percent + '%';
        progressFill.setAttribute('aria-valuenow', percent);
        progressPercent.textContent = Math.round(percent) + '%';
        progressMessage.textContent = status.current_message || 'En cours...';
        
        // Changer la couleur en cas d'erreur
        if (status.error) {
            progressFill.classList.remove('bg-primary');
            progressFill.classList.add('bg-danger');
            progressMessage.textContent = '❌ Erreur: ' + status.error;
        }
    }
}

function monitorGlobalRefresh() {
    // Arrêter la surveillance précédente si elle existe
    if (globalRefreshInterval) {
        clearInterval(globalRefreshInterval);
    }
    
    globalRefreshInterval = setInterval(() => {
        fetch('/api/global-refresh/status', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.status) {
                updateGlobalProgress(data.status);
                
                // Vérifier si terminé
                if (!data.status.is_running) {
                    clearInterval(globalRefreshInterval);
                    globalRefreshInterval = null;
                    
                    setTimeout(() => {
                        hideGlobalProgressBar();
                        
                        if (data.status.error) {
                            showGlobalAlert('Rafraîchissement échoué: ' + data.status.error, 'danger');
                        } else {
                            showGlobalAlert('✅ Rafraîchissement global terminé avec succès!', 'success');
                            
                            // Rafraîchir les données de la page actuelle si possible
                            if (typeof refreshPageData === 'function') {
                                refreshPageData();
                            }
                        }
                        
                        // Supprimer le cookie
                        document.cookie = 'global_refresh_running=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                    }, 1000);
                }
            }
        })
        .catch(error => {
            console.error('Erreur lors de la surveillance:', error);
        });
    }, 2000); // Vérifier toutes les 2 secondes
}

function startGlobalRefresh() {
    if (confirm('🔄 Rafraîchir toutes les playlists, créer les liens et propager les classifications ?\n\nCette opération peut prendre plusieurs minutes et traite tous les concurrents.')) {
        
        // Démarrer le rafraîchissement global
        fetch('/api/global-refresh/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showGlobalAlert('Rafraîchissement global démarré en arrière-plan', 'info');
                
                // Démarrer la barre de progression
                showGlobalProgressBar();
                
                // Surveiller le progrès
                monitorGlobalRefresh();
                
            } else {
                showGlobalAlert('Erreur lors du démarrage: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            showGlobalAlert('Erreur de connexion: ' + error.message, 'danger');
        });
    }
}

function showGlobalAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.15);';
    alert.innerHTML = `
        <i class="bx bx-${type === 'success' ? 'check-circle' : type === 'warning' ? 'error' : type === 'info' ? 'info-circle' : 'x-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Vérifier au chargement de la page s'il y a un refresh en cours
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier le cookie
    const refreshRunning = document.cookie.includes('global_refresh_running=true');
    
    if (refreshRunning) {
        // Vérifier le statut réel
        fetch('/api/global-refresh/status')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.status && data.status.is_running) {
                    showGlobalProgressBar();
                    monitorGlobalRefresh();
                } else {
                    // Supprimer le cookie obsolète
                    document.cookie = 'global_refresh_running=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                }
            })
            .catch(error => {
                console.error('Erreur lors de la vérification du statut:', error);
                // Supprimer le cookie en cas d'erreur
                document.cookie = 'global_refresh_running=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            });
    }
});

// Exposer les fonctions globalement
window.startGlobalRefresh = startGlobalRefresh;
window.showGlobalProgressBar = showGlobalProgressBar;
window.hideGlobalProgressBar = hideGlobalProgressBar;