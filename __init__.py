import os
from flask import Flask
from . import db
from .utils.logger import setup_logger

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.update(test_config)
    
    # Configurar el sistema de logging
    loggers = setup_logger(app)
    app.config['DB_LOGGER'] = loggers['db_logger']
    
    # Initialize the database
    db.init_app(app)
    
    # Verificar integridad de la base de datos al inicio
    with app.app_context():
        if not db.verify_db_integrity():
            app.logger.error("Se detectó un problema de integridad en la base de datos al iniciar")
            # Intentar restaurar desde el último backup si existe
            try:
                backup_files = os.listdir(os.path.join(app.instance_path, 'backups'))
                if backup_files:
                    latest_backup = max(backup_files)
                    app.logger.info(f"Intentando restaurar desde el backup: {latest_backup}")
                    # Aquí iría la lógica de restauración
            except Exception as e:
                app.logger.error(f"Error al intentar restaurar desde backup: {str(e)}")
    
    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')
    
    return app 