"""
🚀 Sentiment Analysis - Production Mode
Route pour afficher l'analyse sentiment en mode production avec fallback JSON
"""

from flask import Blueprint, render_template, jsonify, request
from functools import wraps
import json
import os
from pathlib import Path
from datetime import datetime

# Créer le blueprint
sentiment_bp = Blueprint('sentiment_production', __name__)

def prod_mode_only(f):
    """Décorateur pour limiter aux modes production"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # En production, toujours autoriser
        # En développement, vérifier la config
        return f(*args, **kwargs)
    return decorated_function

@sentiment_bp.route('/sentiment-analysis')
def sentiment_analysis_production():
    """Page sentiment analysis optimisée pour production avec fallback JSON"""
    
    # Charger les données depuis le JSON statique
    json_file = Path('static/sentiment_analysis_production.json')
    
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extraire les données pour le template
            stats = data.get('stats', {})
            videos = data.get('videos', [])
            charts_data = data.get('charts_data', {})
            
            # Pagination simple
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 25))
            sentiment_filter = request.args.get('sentiment', 'all')
            sort_by = request.args.get('sort_by', 'positive_count')
            order = request.args.get('order', 'desc')
            
            # Filtrer par sentiment
            if sentiment_filter != 'all':
                videos = [v for v in videos if v.get('dominant_sentiment') == sentiment_filter]
            
            # Trier
            reverse = (order == 'desc')
            if sort_by in ['positive_count', 'negative_count', 'total_comments', 'positive_percentage']:
                videos = sorted(videos, key=lambda x: x.get(sort_by, 0), reverse=reverse)
            
            # Pagination
            total_videos = len(videos)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_videos = videos[start_idx:end_idx]
            
            total_pages = (total_videos + per_page - 1) // per_page
            
            return render_template('sentiment_analysis_sneat_pro.html',
                stats=stats,
                all_videos=paginated_videos,
                current_page=page,
                total_pages=total_pages,
                per_page=per_page,
                total_videos=total_videos,
                sentiment_filter=sentiment_filter,
                sort_by=sort_by,
                order=order,
                # Données pour les graphiques JavaScript
                config={'DEV_MODE': False},  # Force production mode
                charts_data=charts_data
            )
            
        except Exception as e:
            print(f"Erreur lecture JSON: {e}")
            return render_fallback_sentiment()
    else:
        return render_fallback_sentiment()

def render_fallback_sentiment():
    """Rendu de fallback quand pas de données"""
    
    # Données minimales de fallback
    stats = {
        'total_videos_analyzed': 0,
        'total_comments_analyzed': 0,
        'positive_count': 0,
        'negative_count': 0,
        'neutral_count': 0,
        'positive_percentage': 0,
        'negative_percentage': 0,
        'neutral_percentage': 0,
        'avg_confidence': 0,
        'engagement_correlation': 0
    }
    
    return render_template('sentiment_analysis_sneat_pro.html',
        stats=stats,
        all_videos=[],
        current_page=1,
        total_pages=1,
        per_page=25,
        total_videos=0,
        sentiment_filter='all',
        sort_by='positive_count',
        order='desc',
        config={'DEV_MODE': False},
        charts_data={}
    )

@sentiment_bp.route('/api/emotions/export')
def export_sentiment_production():
    """API d'export pour compatibilité avec l'interface existante"""
    
    json_file = Path('static/sentiment_analysis_production.json')
    
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Erreur lecture données: {str(e)}'
            }), 500
    else:
        return jsonify({
            'success': False,
            'error': 'Fichier de données non trouvé. Exécutez export_sentiment_production.py'
        }), 404

@sentiment_bp.route('/api/sentiment-analysis/refresh', methods=['POST'])
def refresh_sentiment_data():
    """API pour rafraîchir les données (désactivée en production)"""
    
    # En production, ne pas permettre le refresh
    return jsonify({
        'success': False,
        'error': 'Refresh désactivé en mode production',
        'message': 'Utilisez export_sentiment_production.py pour mettre à jour les données'
    }), 403