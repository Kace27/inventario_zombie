import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'inventario_zombie.sqlite')
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'test_inventario_zombie.sqlite')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Use stronger secret key in production
    SECRET_KEY = os.environ.get('SECRET_KEY')

# Dictionary to map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 