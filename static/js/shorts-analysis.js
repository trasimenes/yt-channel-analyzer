// ========================================
// FONCTIONS YOUTUBE SHORTS ANALYSIS
// ========================================

// Charger l'analyse des Shorts au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    loadShortsAnalysis();
});

async function loadShortsAnalysis() {
    const competitorId = window.location.pathname.split('/').pop();
    
    // Afficher le loading
    const shortsLoading = document.getElementById('shortsLoading');
    const shortsMetrics = document.getElementById('shortsMetrics');
    const shortsFrequency = document.getElementById('shortsFrequency');
    const shortsRecommendations = document.getElementById('shortsRecommendations');
    
    if (!shortsLoading) return; // Pas sur la page des concurrents
    
    shortsLoading.style.display = 'block';
    shortsMetrics.style.display = 'none';
    shortsFrequency.style.display = 'none';
    shortsRecommendations.style.display = 'none';
    
    try {
        // Récupérer le rapport complet des Shorts
        const response = await fetch(`/api/shorts/report/${competitorId}`);
        const result = await response.json();
        
        if (result.success && result.report) {
            const report = result.report;
            
            // Masquer le loading
            shortsLoading.style.display = 'none';
            
            // Afficher les sections
            shortsMetrics.style.display = 'block';
            shortsFrequency.style.display = 'block';
            shortsRecommendations.style.display = 'block';
            
            // Mettre à jour les métriques de comparaison
            const comparison = report.comparison;
            if (comparison) {
                // Mettre à jour les métriques de base
                const shortsCount = comparison.shorts_stats ? comparison.shorts_stats.count || 0 : 0;
                const shortsRatio = comparison.shorts_ratio || 0;
                const shortsAvgViews = comparison.shorts_stats ? comparison.shorts_stats.avg_views || 0 : 0;
                const regularAvgViews = comparison.regular_stats ? comparison.regular_stats.avg_views || 0 : 0;
                
                updateElementText('shortsCount', shortsCount);
                updateElementText('shortsRatio', shortsRatio + '%');
                updateElementText('shortsAvgViews', formatNumber(shortsAvgViews));
                updateElementText('regularAvgViews', formatNumber(regularAvgViews));
                
                // Performance relative
                const perfComp = comparison.performance_comparison;
                if (perfComp && perfComp.views_ratio) {
                    const ratio = perfComp.views_ratio;
                    let perfText = '';
                    let perfColor = '';
                    
                    if (ratio > 1.5) {
                        perfText = `+${Math.round((ratio - 1) * 100)}%`;
                        perfColor = 'text-success';
                    } else if (ratio < 0.5) {
                        perfText = `-${Math.round((1 - ratio) * 100)}%`;
                        perfColor = 'text-danger';
                    } else {
                        perfText = `${ratio > 1 ? '+' : ''}${Math.round((ratio - 1) * 100)}%`;
                        perfColor = 'text-warning';
                    }
                    
                    updateElementHTML('shortsPerformance', `<span class="${perfColor}">${perfText}</span>`);
                } else {
                    updateElementText('shortsPerformance', 'N/A');
                }
            }
            
            // Mettre à jour les métriques de fréquence
            const frequency = report.frequency_patterns;
            if (frequency) {
                updateElementText('shortsPerWeek', frequency.avg_shorts_per_week || 0);
                updateElementText('shortsPerMonth', frequency.monthly_shorts || 0);
                updateElementText('shortsPercentage', frequency.shorts_percentage + '%');
            }
            
            // Mettre à jour les recommandations
            const recommendations = report.recommendations;
            if (recommendations && recommendations.length > 0) {
                const recommendationsList = document.getElementById('recommendationsList');
                if (recommendationsList) {
                    recommendationsList.innerHTML = recommendations.map(rec => `<li>${rec}</li>`).join('');
                }
            } else {
                const recommendationsList = document.getElementById('recommendationsList');
                if (recommendationsList) {
                    recommendationsList.innerHTML = '<li>✅ Stratégie Shorts optimale détectée</li>';
                }
            }
            
        } else {
            // Erreur dans la réponse
            shortsLoading.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                    <p class="mt-2">Erreur lors du chargement des données Shorts</p>
                    <button class="btn btn-light btn-sm" onclick="loadShortsAnalysis()">
                        <i class="bi bi-arrow-repeat me-1"></i>
                        Réessayer
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur lors du chargement de l\'analyse Shorts:', error);
        
        shortsLoading.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-wifi-off text-danger" style="font-size: 2rem;"></i>
                <p class="mt-2">Erreur de connexion</p>
                <button class="btn btn-light btn-sm" onclick="loadShortsAnalysis()">
                    <i class="bi bi-arrow-repeat me-1"></i>
                    Réessayer
                </button>
            </div>
        `;
    }
}

// Fonctions utilitaires
function updateElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

function updateElementHTML(elementId, html) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = html;
    }
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    } else {
        return num.toString();
    }
}

// Fonction pour actualiser les données Shorts
function refreshShortsData() {
    loadShortsAnalysis();
} 