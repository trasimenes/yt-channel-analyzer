"""
Configuration pour YT Channel Analyzer
Sépare l'environnement de développement (avec ML) de la production (affichage seul)
"""

import os
from typing import Dict, Any

class Config:
    """Configuration de base"""
    
    # Détection automatique de l'environnement
    ENVIRONMENT = os.getenv('YTA_ENVIRONMENT', 'development')  # development | production
    
    # Configuration des modèles ML
    ENABLE_ML_MODELS = os.getenv('YTA_ENABLE_ML', 'true').lower() == 'true'
    
    # Base de données
    DB_PATH = os.getenv('YTA_DB_PATH', './instance/database.db')
    
    # Configuration spécifique par environnement
    @classmethod
    def is_production(cls) -> bool:
        """Vérifie si on est en production"""
        return cls.ENVIRONMENT == 'production'
    
    @classmethod
    def is_development(cls) -> bool:
        """Vérifie si on est en développement"""
        return cls.ENVIRONMENT == 'development'
    
    @classmethod
    def should_load_ml_models(cls) -> bool:
        """Détermine si on doit charger les modèles ML"""
        # En production : jamais de modèles ML
        if cls.is_production():
            return False
        
        # En développement : selon la variable d'environnement
        return os.getenv('YTA_ENABLE_ML', 'true').lower() == 'true'

class DevelopmentConfig(Config):
    """Configuration pour développement local"""
    ENVIRONMENT = 'development'
    ENABLE_ML_MODELS = True
    DEBUG = True

class ProductionConfig(Config):
    """Configuration pour production"""
    ENVIRONMENT = 'production'
    ENABLE_ML_MODELS = False  # JAMAIS de modèles en production
    DEBUG = False

# Factory pour obtenir la bonne configuration
def get_config() -> Config:
    """Retourne la configuration appropriée selon l'environnement"""
    env = os.getenv('YTA_ENVIRONMENT', 'development')
    
    if env == 'production':
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# Instance globale
config = get_config()