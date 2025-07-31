#!/usr/bin/env python3
"""
🔧 Mise à jour du template sentiment analysis pour support production
"""

import os
import sys
from pathlib import Path

def update_sentiment_template():
    """Met à jour le template pour supporter les données JSON en production"""
    
    template_path = Path('templates/sentiment_analysis_sneat_pro.html')
    
    if not template_path.exists():
        print(f"❌ Template non trouvé: {template_path}")
        return False
    
    # Lire le contenu actuel
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modifications pour la compatibilité production
    updates = [
        # Rendre la détection d'environnement plus robuste
        ('let emotionData = {', '''// Production mode: charger depuis JSON statique ou variables Python
let emotionData = (typeof window.productionSentimentData !== 'undefined') ? 
    window.productionSentimentData : {'''),
        
        # Modifier l'API export pour utiliser le fallback en production
        ("fetch('/api/emotions/export')", """fetch('/api/emotions/export')
        .catch(() => {
            // Fallback: utiliser les données déjà chargées
            return { 
                ok: true, 
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        stats: emotionData,
                        videos: []
                    }
                })
            };
        })"""),
        
        # Ajouter un système de fallback pour les charts
        ('initializeCharts();', '''try {
            initializeCharts();
        } catch (error) {
            console.log('Charts initialization failed, using fallback:', error);
            showChartsUnavailable();
        }'''),
        
        # Désactiver les fonctions de développement en production
        ('{% if config.DEV_MODE %}', '''{% if config.get('DEV_MODE', False) and not config.get('FORCE_PROD_MODE', False) %}''')
    ]
    
    # Appliquer les modifications
    for old, new in updates:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Mis à jour: {old[:50]}...")
        else:
            print(f"⚠️  Non trouvé: {old[:50]}...")
    
    # Ajouter du code JavaScript pour le support production
    js_addition = '''
// Production mode helpers
function showChartsUnavailable() {
    const chartContainers = [
        'globalEmotionChart',
        'emotionHeatmapChart', 
        'competitorRadarChart',
        'emotionTimelineChart',
        'emotionEngagementChart'
    ];
    
    chartContainers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            const parent = container.parentElement;
            parent.innerHTML = `
                <div class="d-flex align-items-center justify-content-center" style="height: 200px;">
                    <div class="text-center">
                        <i class="bx bx-bar-chart fs-1 text-muted mb-2"></i>
                        <p class="text-muted">Graphique disponible en mode développement</p>
                    </div>
                </div>
            `;
        }
    });
}

// Initialiser les données pour la production si disponibles
if (typeof window.productionSentimentData === 'undefined' && typeof emotionData !== 'undefined') {
    window.productionSentimentData = emotionData;
}
'''
    
    # Insérer le code JS avant la balise de fermeture du script
    script_end = '</script>\n{% endblock %}'
    if script_end in content:
        content = content.replace(script_end, js_addition + '\n' + script_end)
    
    # Sauvegarder le fichier modifié
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Template mis à jour: {template_path}")
    return True

if __name__ == '__main__':
    update_sentiment_template()