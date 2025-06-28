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

// Export for use in other scripts
window.YTAnalyzer = {
    showAlert,
    validateForm,
    setLoadingState
};