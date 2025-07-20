"""
API controller for unified problem fixing
Following SRP: handles only fix-all-problems API requests
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
import logging

from ...core.interfaces.services import ValidationService
from ...services.unified_fix_service import UnifiedFixService


class FixProblemsAPIController:
    """
    Contrôleur API pour la correction unifiée des problèmes
    Suit le principe SRP: gestion des requêtes API de correction uniquement
    """
    
    def __init__(
        self,
        unified_fix_service: UnifiedFixService,
        validation_service: ValidationService,
        logger: logging.Logger = None
    ):
        self.unified_fix_service = unified_fix_service
        self.validation_service = validation_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Créer le blueprint Flask
        self.blueprint = Blueprint('fix_problems_api', __name__, url_prefix='/api')
        self._register_routes()
    
    def _register_routes(self):
        """Enregistrer les routes API"""
        self.blueprint.add_url_rule('/fix-all-problems', 'fix_all_problems', self.fix_all_problems, methods=['POST'])
        self.blueprint.add_url_rule('/fix-problems-status', 'fix_problems_status', self.get_fix_status, methods=['GET'])
        self.blueprint.add_url_rule('/validate-data-integrity', 'validate_data_integrity', self.validate_data_integrity, methods=['POST'])
    
    def fix_all_problems(self):
        """Corriger tous les problèmes sélectionnés"""
        try:
            # Récupérer les données de la requête
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Données JSON requises'
                }), 400
            
            # Extraire les paramètres
            selected_fixes = data.get('selected_fixes', [])
            api_limit = data.get('api_limit', 100)
            batch_size = data.get('batch_size', 50)
            
            # Valider les paramètres
            if not selected_fixes:
                return jsonify({
                    'success': False,
                    'error': 'Aucun problème sélectionné'
                }), 400
            
            # Valider les fixes sélectionnés
            valid_fixes = [
                'data_integrity', 'youtube_dates', 'missing_data', 'orphan_data',
                'human_propagation', 'reclassify_videos', 'classify_playlists',
                'classification_tracking', 'auto_fix_errors', 'final_validation'
            ]
            
            invalid_fixes = [fix for fix in selected_fixes if fix not in valid_fixes]
            if invalid_fixes:
                return jsonify({
                    'success': False,
                    'error': f'Corrections invalides: {", ".join(invalid_fixes)}'
                }), 400
            
            # Créer les options de correction
            fix_options = {
                'selected_fixes': selected_fixes,
                'api_limit': max(10, min(1000, api_limit)),
                'batch_size': max(10, min(100, batch_size)),
                'auto_fix_errors': 'auto_fix_errors' in selected_fixes,
                'final_validation': 'final_validation' in selected_fixes
            }
            
            self.logger.info(f"Démarrage correction unifiée avec options: {fix_options}")
            
            # Lancer la correction unifiée
            result = self.unified_fix_service.run_unified_fix(fix_options)
            
            # Retourner le résultat
            if result['success']:
                self.logger.info(f"Correction terminée avec succès: {len(result['issues_fixed'])} problèmes résolus")
                return jsonify(result)
            else:
                self.logger.error(f"Erreur lors de la correction: {result.get('error', 'Erreur inconnue')}")
                return jsonify(result), 500
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la correction unifiée: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Erreur interne du serveur',
                'details': str(e)
            }), 500
    
    def get_fix_status(self):
        """Obtenir le statut des corrections possibles"""
        try:
            # Analyser les problèmes détectés
            integrity_report = self.validation_service.validate_data_integrity()
            
            # Préparer le statut
            status = {
                'success': True,
                'available_fixes': {
                    'data_integrity': {
                        'name': 'Validation d\'intégrité des données',
                        'description': 'Vérifier et corriger les incohérences',
                        'issues_count': integrity_report.get('stats', {}).get('errors_found', 0),
                        'critical_issues': integrity_report.get('stats', {}).get('critical_errors', 0),
                        'recommended': integrity_report.get('stats', {}).get('critical_errors', 0) > 0
                    },
                    'youtube_dates': {
                        'name': 'Correction des dates YouTube',
                        'description': 'Récupérer les vraies dates depuis l\'API',
                        'issues_count': self._count_fake_dates(),
                        'recommended': self._count_fake_dates() > 0
                    },
                    'missing_data': {
                        'name': 'Données manquantes',
                        'description': 'Calculer les métriques manquantes',
                        'issues_count': self._count_missing_data(),
                        'recommended': self._count_missing_data() > 0
                    },
                    'human_propagation': {
                        'name': 'Propagation classifications humaines',
                        'description': 'Propager les validations humaines',
                        'issues_count': self._count_human_classifications(),
                        'recommended': True
                    },
                    'reclassify_videos': {
                        'name': 'Re-classification automatique',
                        'description': 'Reclassifier avec logique multilingue',
                        'issues_count': self._count_unclassified_videos(),
                        'recommended': self._count_unclassified_videos() > 0
                    },
                    'classify_playlists': {
                        'name': 'Classification des playlists',
                        'description': 'Classifier les playlists non classifiées',
                        'issues_count': self._count_unclassified_playlists(),
                        'recommended': self._count_unclassified_playlists() > 0
                    }
                },
                'system_health': integrity_report.get('health_status', 'unknown'),
                'total_issues': sum(
                    fix_info['issues_count'] for fix_info in status['available_fixes'].values()
                )
            }
            
            return jsonify(status)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'obtention du statut: {e}")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'analyse du statut'
            }), 500
    
    def validate_data_integrity(self):
        """Valider l'intégrité des données"""
        try:
            # Lancer la validation
            fix_errors = request.get_json().get('fix_errors', False) if request.get_json() else False
            
            result = self.validation_service.validate_data_integrity(fix_errors=fix_errors)
            
            return jsonify(result)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {e}")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la validation'
            }), 500
    
    def _count_fake_dates(self) -> int:
        """Compter les vidéos avec de fausses dates"""
        try:
            # TODO: Implémenter le comptage réel
            return 0
        except Exception:
            return 0
    
    def _count_missing_data(self) -> int:
        """Compter les données manquantes"""
        try:
            # TODO: Implémenter le comptage réel
            return 0
        except Exception:
            return 0
    
    def _count_human_classifications(self) -> int:
        """Compter les classifications humaines à propager"""
        try:
            # TODO: Implémenter le comptage réel
            return 0
        except Exception:
            return 0
    
    def _count_unclassified_videos(self) -> int:
        """Compter les vidéos non classifiées"""
        try:
            # TODO: Implémenter le comptage réel
            return 0
        except Exception:
            return 0
    
    def _count_unclassified_playlists(self) -> int:
        """Compter les playlists non classifiées"""
        try:
            # TODO: Implémenter le comptage réel
            return 0
        except Exception:
            return 0
    
    def get_blueprint(self):
        """Récupérer le blueprint Flask"""
        return self.blueprint