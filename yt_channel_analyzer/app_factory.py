"""
Application factory - Following SOLID principles
Creates and configures the Flask application with proper dependency injection
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import Flask
from flask_session import Session
from flask_caching import Cache
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .core.interfaces.repository import (
    CompetitorRepository, VideoRepository, PlaylistRepository, 
    AnalyticsRepository, CacheRepository
)
from .core.interfaces.services import (
    CompetitorService, VideoService, PlaylistService,
    ClassificationService, AnalyticsService, ValidationService,
    CacheService, YouTubeAPIService
)
from .services.competitor_service import CompetitorServiceImpl
from .controllers.web.competitor_controller import CompetitorWebController


class ApplicationFactory:
    """
    Factory pour créer l'application Flask
    Suit le principe DIP: injection de dépendances
    Suit le principe SRP: responsabilité unique de création d'app
    """
    
    def __init__(self):
        self.app = None
        self.db = None
        self.cache = None
        self.logger = None
        
        # Containers pour les dépendances
        self.repositories = {}
        self.services = {}
        self.controllers = {}
    
    def create_app(self, config: Optional[Dict[str, Any]] = None) -> Flask:
        """Créer et configurer l'application Flask"""
        self.app = Flask(__name__)
        
        # Configuration
        self._configure_app(config)
        
        # Logging
        self._setup_logging()
        
        # Extensions
        self._setup_extensions()
        
        # Dependency injection
        self._setup_dependencies()
        
        # Routes
        self._register_routes()
        
        # Error handlers
        self._setup_error_handlers()
        
        return self.app
    
    def _configure_app(self, config: Optional[Dict[str, Any]] = None):
        """Configurer l'application"""
        # Configuration par défaut
        default_config = {
            'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', 'dev-secret-key'),
            'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///instance/database.db'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': 300,
            'SESSION_TYPE': 'filesystem',
            'WTF_CSRF_ENABLED': True,
            'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            'TESTING': False
        }
        
        # Appliquer la configuration
        if config:
            default_config.update(config)
        
        self.app.config.update(default_config)
    
    def _setup_logging(self):
        """Configurer le logging"""
        logging.basicConfig(
            level=logging.INFO if not self.app.config['DEBUG'] else logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_extensions(self):
        """Configurer les extensions Flask"""
        # Database
        self.db = SQLAlchemy(self.app)
        
        # Cache
        self.cache = Cache(self.app)
        
        # Sessions
        Session(self.app)
        
        # Migrations
        Migrate(self.app, self.db)
    
    def _setup_dependencies(self):
        """Configurer l'injection de dépendances"""
        # Repositories (couche d'accès aux données)
        self._setup_repositories()
        
        # Services (couche métier)
        self._setup_services()
        
        # Controllers (couche présentation)
        self._setup_controllers()
    
    def _setup_repositories(self):
        """Configurer les repositories"""
        # TODO: Implémenter les repositories concrets
        # Pour l'instant, on utilise des mocks ou des implémentations basiques
        
        from .infrastructure.repositories.sqlite_competitor_repository import SQLiteCompetitorRepository
        from .infrastructure.repositories.sqlite_video_repository import SQLiteVideoRepository
        from .infrastructure.repositories.sqlite_playlist_repository import SQLitePlaylistRepository
        from .infrastructure.repositories.sqlite_analytics_repository import SQLiteAnalyticsRepository
        from .infrastructure.repositories.flask_cache_repository import FlaskCacheRepository
        
        self.repositories = {
            'competitor': SQLiteCompetitorRepository(self.db),
            'video': SQLiteVideoRepository(self.db),
            'playlist': SQLitePlaylistRepository(self.db),
            'analytics': SQLiteAnalyticsRepository(self.db),
            'cache': FlaskCacheRepository(self.cache)
        }
    
    def _setup_services(self):
        """Configurer les services métier"""
        # TODO: Implémenter les services concrets
        
        from .services.validation_service import ValidationServiceImpl
        from .services.cache_service import CacheServiceImpl
        
        # Services de base
        validation_service = ValidationServiceImpl(self.logger)
        cache_service = CacheServiceImpl(self.repositories['cache'])
        
        # Service principal des concurrents
        competitor_service = CompetitorServiceImpl(
            competitor_repo=self.repositories['competitor'],
            video_repo=self.repositories['video'],
            playlist_repo=self.repositories['playlist'],
            analytics_repo=self.repositories['analytics'],
            validation_service=validation_service,
            cache_service=cache_service,
            logger=self.logger
        )
        
        self.services = {
            'competitor': competitor_service,
            'validation': validation_service,
            'cache': cache_service
        }
    
    def _setup_controllers(self):
        """Configurer les contrôleurs"""
        # Contrôleur web des concurrents
        competitor_controller = CompetitorWebController(
            competitor_service=self.services['competitor'],
            validation_service=self.services['validation'],
            logger=self.logger
        )
        
        self.controllers = {
            'competitor_web': competitor_controller
        }
    
    def _register_routes(self):
        """Enregistrer les routes"""
        # Routes principales
        self._register_main_routes()
        
        # Routes des contrôleurs
        for controller_name, controller in self.controllers.items():
            if hasattr(controller, 'get_blueprint'):
                self.app.register_blueprint(controller.get_blueprint())
    
    def _register_main_routes(self):
        """Enregistrer les routes principales"""
        @self.app.route('/')
        def index():
            from flask import render_template
            return render_template('index.html')
        
        @self.app.route('/health')
        def health_check():
            from flask import jsonify
            return jsonify({
                'status': 'healthy',
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat()
            })
    
    def _setup_error_handlers(self):
        """Configurer les gestionnaires d'erreurs"""
        @self.app.errorhandler(404)
        def not_found(error):
            from flask import render_template
            return render_template('errors/404.html'), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            from flask import render_template
            self.logger.error(f"Erreur interne: {error}")
            return render_template('errors/500.html'), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            from flask import jsonify, request
            self.logger.error(f"Exception non gérée: {e}")
            
            # Retourner JSON pour les requêtes API
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Erreur interne du serveur'
                }), 500
            
            # Retourner HTML pour les autres requêtes
            from flask import render_template
            return render_template('errors/500.html'), 500
    
    def get_app(self) -> Flask:
        """Récupérer l'application Flask"""
        return self.app
    
    def get_repositories(self) -> Dict[str, Any]:
        """Récupérer les repositories"""
        return self.repositories
    
    def get_services(self) -> Dict[str, Any]:
        """Récupérer les services"""
        return self.services
    
    def get_controllers(self) -> Dict[str, Any]:
        """Récupérer les contrôleurs"""
        return self.controllers


# Factory function pour créer l'application
def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Créer l'application Flask avec la configuration donnée"""
    factory = ApplicationFactory()
    return factory.create_app(config)


# Factory function pour les tests
def create_test_app() -> Flask:
    """Créer une application Flask pour les tests"""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    }
    return create_app(test_config)