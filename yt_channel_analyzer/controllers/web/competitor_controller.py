"""
Web controller for competitor management
Following SRP: handles only competitor-related web requests
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from typing import Dict, Any
import logging

from ...core.interfaces.services import CompetitorService, ValidationService
from ...core.models import Competitor, CompetitorStatus


class CompetitorWebController:
    """
    Contrôleur web pour la gestion des concurrents
    Suit le principe SRP: gestion des requêtes web concurrents uniquement
    Suit le principe DIP: dépend des services abstraits
    """
    
    def __init__(
        self,
        competitor_service: CompetitorService,
        validation_service: ValidationService,
        logger: logging.Logger = None
    ):
        self.competitor_service = competitor_service
        self.validation_service = validation_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Créer le blueprint Flask
        self.blueprint = Blueprint('competitor_web', __name__, url_prefix='/competitor')
        self._register_routes()
    
    def _register_routes(self):
        """Enregistrer les routes Flask"""
        self.blueprint.add_url_rule('/', 'list', self.list_competitors, methods=['GET'])
        self.blueprint.add_url_rule('/<int:competitor_id>', 'detail', self.competitor_detail, methods=['GET'])
        self.blueprint.add_url_rule('/create', 'create', self.create_competitor, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/<int:competitor_id>/edit', 'edit', self.edit_competitor, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/<int:competitor_id>/delete', 'delete', self.delete_competitor, methods=['POST'])
        self.blueprint.add_url_rule('/<int:competitor_id>/performance', 'performance', self.performance_report, methods=['GET'])
        self.blueprint.add_url_rule('/<int:competitor_id>/update_metrics', 'update_metrics', self.update_metrics, methods=['POST'])
    
    def list_competitors(self):
        """Afficher la liste des concurrents"""
        try:
            # Récupérer les concurrents actifs
            competitors = self.competitor_service.get_active_competitors()
            
            # Préparer les données pour la vue
            competitors_data = []
            for competitor in competitors:
                competitor_dict = competitor.to_dict()
                competitor_dict['performance_score'] = competitor.get_performance_score()
                competitors_data.append(competitor_dict)
            
            # Trier par score de performance décroissant
            competitors_data.sort(key=lambda x: x['performance_score'], reverse=True)
            
            return render_template('competitors/list.html', competitors=competitors_data)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'affichage des concurrents: {e}")
            flash('Erreur lors du chargement des concurrents', 'error')
            return render_template('competitors/list.html', competitors=[])
    
    def competitor_detail(self, competitor_id: int):
        """Afficher les détails d'un concurrent"""
        try:
            competitor = self.competitor_service.get_competitor_details(competitor_id)
            if not competitor:
                flash('Concurrent non trouvé', 'error')
                return redirect(url_for('competitor_web.list'))
            
            # Générer le rapport de performance
            performance_report = self.competitor_service.get_performance_report(competitor_id)
            
            return render_template(
                'competitors/detail.html',
                competitor=competitor.to_dict(),
                performance_report=performance_report
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'affichage du concurrent {competitor_id}: {e}")
            flash('Erreur lors du chargement du concurrent', 'error')
            return redirect(url_for('competitor_web.list'))
    
    def create_competitor(self):
        """Créer un nouveau concurrent"""
        if request.method == 'GET':
            return render_template('competitors/create.html')
        
        try:
            # Récupérer les données du formulaire
            competitor_data = {
                'name': request.form.get('name', '').strip(),
                'channel_id': request.form.get('channel_id', '').strip(),
                'channel_url': request.form.get('channel_url', '').strip(),
                'description': request.form.get('description', '').strip(),
                'custom_url': request.form.get('custom_url', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            
            # Valider les données requises
            if not competitor_data['name']:
                flash('Le nom est requis', 'error')
                return render_template('competitors/create.html', data=competitor_data)
            
            if not competitor_data['channel_id']:
                flash('Le Channel ID est requis', 'error')
                return render_template('competitors/create.html', data=competitor_data)
            
            # Créer le concurrent
            competitor = self.competitor_service.create_competitor(competitor_data)
            
            flash(f'Concurrent "{competitor.name}" créé avec succès', 'success')
            return redirect(url_for('competitor_web.detail', competitor_id=competitor.id))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('competitors/create.html', data=request.form)
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du concurrent: {e}")
            flash('Erreur lors de la création du concurrent', 'error')
            return render_template('competitors/create.html', data=request.form)
    
    def edit_competitor(self, competitor_id: int):
        """Éditer un concurrent existant"""
        competitor = self.competitor_service.get_competitor_details(competitor_id)
        if not competitor:
            flash('Concurrent non trouvé', 'error')
            return redirect(url_for('competitor_web.list'))
        
        if request.method == 'GET':
            return render_template('competitors/edit.html', competitor=competitor.to_dict())
        
        try:
            # Récupérer les mises à jour
            updates = {
                'name': request.form.get('name', '').strip(),
                'channel_url': request.form.get('channel_url', '').strip(),
                'description': request.form.get('description', '').strip(),
                'custom_url': request.form.get('custom_url', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            
            # Gestion du statut
            status = request.form.get('status')
            if status:
                updates['status'] = CompetitorStatus(status)
            
            # Filtrer les valeurs vides
            updates = {k: v for k, v in updates.items() if v}
            
            # Mettre à jour
            updated_competitor = self.competitor_service.update_competitor(competitor_id, updates)
            
            flash(f'Concurrent "{updated_competitor.name}" mis à jour avec succès', 'success')
            return redirect(url_for('competitor_web.detail', competitor_id=competitor_id))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('competitors/edit.html', competitor=competitor.to_dict())
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour du concurrent {competitor_id}: {e}")
            flash('Erreur lors de la mise à jour du concurrent', 'error')
            return render_template('competitors/edit.html', competitor=competitor.to_dict())
    
    def delete_competitor(self, competitor_id: int):
        """Supprimer un concurrent"""
        try:
            competitor = self.competitor_service.get_competitor_details(competitor_id)
            if not competitor:
                flash('Concurrent non trouvé', 'error')
                return redirect(url_for('competitor_web.list'))
            
            # Supprimer
            success = self.competitor_service.delete_competitor(competitor_id)
            
            if success:
                flash(f'Concurrent "{competitor.name}" supprimé avec succès', 'success')
            else:
                flash('Erreur lors de la suppression du concurrent', 'error')
            
            return redirect(url_for('competitor_web.list'))
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression du concurrent {competitor_id}: {e}")
            flash('Erreur lors de la suppression du concurrent', 'error')
            return redirect(url_for('competitor_web.list'))
    
    def performance_report(self, competitor_id: int):
        """Afficher le rapport de performance d'un concurrent"""
        try:
            competitor = self.competitor_service.get_competitor_details(competitor_id)
            if not competitor:
                flash('Concurrent non trouvé', 'error')
                return redirect(url_for('competitor_web.list'))
            
            # Générer le rapport détaillé
            report = self.competitor_service.get_performance_report(competitor_id)
            
            return render_template(
                'competitors/performance.html',
                competitor=competitor.to_dict(),
                report=report
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du rapport pour {competitor_id}: {e}")
            flash('Erreur lors de la génération du rapport', 'error')
            return redirect(url_for('competitor_web.detail', competitor_id=competitor_id))
    
    def update_metrics(self, competitor_id: int):
        """Mettre à jour les métriques d'un concurrent (AJAX)"""
        try:
            competitor = self.competitor_service.get_competitor_details(competitor_id)
            if not competitor:
                return jsonify({'success': False, 'error': 'Concurrent non trouvé'}), 404
            
            # Recalculer les métriques
            metrics = self.competitor_service.calculate_metrics(competitor_id)
            
            return jsonify({
                'success': True,
                'message': 'Métriques mises à jour avec succès',
                'metrics': metrics
            })
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des métriques pour {competitor_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la mise à jour des métriques'
            }), 500
    
    def get_blueprint(self):
        """Récupérer le blueprint Flask"""
        return self.blueprint