// Simple main.js without any cookie management
// This file provides basic functionality for the YT Channel Analyzer

// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertContainer.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertContainer.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${getAlertIcon(type)} me-2"></i>
            ${message}
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertContainer);
    
    // Auto dismiss after 4 seconds
    setTimeout(() => {
        if (alertContainer.parentNode) {
            alertContainer.remove();
        }
    }, 4000);
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle-fill',
        'danger': 'exclamation-triangle-fill',
        'warning': 'exclamation-triangle-fill',
        'info': 'info-circle-fill'
    };
    return icons[type] || 'info-circle-fill';
}

// Form utilities
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    return form.checkValidity();
}

// Loading states
function setLoadingState(buttonId, loading = true) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    if (loading) {
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Loading...';
    } else {
        button.disabled = false;
        // Restore original text if available
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
        }
    }
}

// Smooth scrolling
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// --- Supervised Learning Category Selection & Toast ---
document.addEventListener('DOMContentLoaded', function() {
    // Gestion de la sélection de catégorie
    document.querySelectorAll('.category-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const videoId = this.getAttribute('data-video-id');
            const category = this.getAttribute('data-category');
            const card = this.closest('.video-card');
            if (!videoId || !category || !card) return;

            // Désactiver tous les boutons de la même carte
            card.querySelectorAll('.category-btn').forEach(function(b) {
                b.classList.remove('active', 'selected-category', 'border-3', 'border-dark');
                // Retirer l'icône de coche si présente
                const icon = b.querySelector('.bi-check-circle-fill');
                if (icon) icon.remove();
            });
            // Activer le bouton sélectionné
            this.classList.add('active', 'selected-category', 'border-3', 'border-dark');
            // Ajouter l'icône de coche si absente
            if (!this.querySelector('.bi-check-circle-fill')) {
                this.insertAdjacentHTML('beforeend', '<i class="bi bi-check-circle-fill ms-1"></i>');
            }

            // Appel AJAX pour mettre à jour la classification
            fetch('/api/supervised/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    video_id: videoId,
                    category: category,
                    feedback_type: 'correction'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Afficher le toast Bootstrap
                    const toastEl = document.getElementById('classificationToast');
                    if (toastEl && typeof bootstrap !== 'undefined') {
                        const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
                        toast.show();
                    } else {
                        showAlert('Classification mise à jour avec succès !', 'success');
                    }
                } else {
                    showAlert(data.message || 'Erreur lors de la mise à jour.', 'danger');
                }
            })
            .catch(() => {
                showAlert('Erreur réseau lors de la mise à jour.', 'danger');
            });
        });
    });
});

// Fonction pour gérer les miniatures YouTube qui ne se chargent pas
function handleThumbnailError(img) {
    const videoId = extractVideoIdFromUrl(img.src);
    
    // Essayer différents formats de miniatures YouTube
    const thumbnailFormats = [
        'hqdefault.jpg',      // Haute qualité (320x180)
        'mqdefault.jpg',      // Qualité moyenne (320x180)  
        'sddefault.jpg',      // Définition standard (640x480)
        'maxresdefault.jpg',  // Résolution maximale (1280x720)
        'default.jpg'         // Miniature par défaut (120x90)
    ];
    
    // Récupérer le format actuel
    const currentFormat = img.src.split('/').pop();
    const currentIndex = thumbnailFormats.indexOf(currentFormat);
    
    // Essayer le format suivant
    if (currentIndex < thumbnailFormats.length - 1) {
        const nextFormat = thumbnailFormats[currentIndex + 1];
        img.src = `https://i.ytimg.com/vi/${videoId}/${nextFormat}`;
        console.log(`[THUMBNAIL] Fallback vers ${nextFormat} pour ${videoId}`);
    } else {
        // Dernier recours : créer une miniature de fallback
        createFallbackThumbnail(img);
    }
}

function extractVideoIdFromUrl(url) {
    const patterns = [
        /(?:v=|\/)([0-9A-Za-z_-]{11})/,
        /(?:embed\/)([0-9A-Za-z_-]{11})/,
        /(?:v\/)([0-9A-Za-z_-]{11})/
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    
    return null;
}

function createFallbackThumbnail(img) {
    // Créer une miniature de fallback avec CSS
    const fallbackDiv = document.createElement('div');
    fallbackDiv.className = 'thumbnail-fallback';
    fallbackDiv.style.cssText = `
        width: ${img.width || 120}px;
        height: ${img.height || 90}px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 24px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    `;
    fallbackDiv.innerHTML = '<i class="bi bi-play-circle"></i>';
    
    // Remplacer l'image par le fallback
    img.parentNode.replaceChild(fallbackDiv, img);
    console.log('[THUMBNAIL] Fallback créé pour image défaillante');
}

// Fonction pour précharger les miniatures
function preloadThumbnails() {
    const thumbnailImages = document.querySelectorAll('img[src*="ytimg.com"], img[src*="youtube.com"]');
    
    thumbnailImages.forEach(img => {
        // Ajouter le gestionnaire d'erreur
        img.onerror = function() {
            handleThumbnailError(this);
        };
        
        // Ajouter un indicateur de chargement
        img.onload = function() {
            this.classList.add('thumbnail-loaded');
        };
        
        // Ajouter une classe pour le style
        img.classList.add('youtube-thumbnail');
    });
}

// Fonction pour réparer les miniatures existantes
function repairThumbnails() {
    const brokenImages = document.querySelectorAll('img[src*="ytimg.com"]:not(.thumbnail-loaded)');
    
    brokenImages.forEach(img => {
        // Forcer le rechargement
        const originalSrc = img.src;
        img.src = '';
        setTimeout(() => {
            img.src = originalSrc;
        }, 100);
    });
    
    console.log(`[THUMBNAIL] Réparation de ${brokenImages.length} miniatures`);
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    preloadThumbnails();
    
    // Réparer les miniatures toutes les 5 secondes si nécessaire
    setInterval(repairThumbnails, 5000);
});

// Réinitialiser les miniatures lors du changement de contenu AJAX
document.addEventListener('ajaxComplete', function() {
    setTimeout(preloadThumbnails, 500);
});

// Styles CSS pour les miniatures
const thumbnailStyles = `
    .youtube-thumbnail {
        transition: all 0.3s ease;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .youtube-thumbnail:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    
    .thumbnail-fallback {
        transition: all 0.3s ease;
    }
    
    .thumbnail-fallback:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    
    .thumbnail-loaded {
        opacity: 1;
    }
    
    .youtube-thumbnail:not(.thumbnail-loaded) {
        opacity: 0.7;
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
    }
`;

// Injecter les styles
const styleSheet = document.createElement('style');
styleSheet.textContent = thumbnailStyles;
document.head.appendChild(styleSheet);

// Export for use in other scripts
window.YTAnalyzer = {
    showAlert,
    validateForm,
    setLoadingState
};