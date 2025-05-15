import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(app):
    """Configura el sistema de logging para la aplicación."""
    
    # Crear directorio de logs si no existe
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar el logger principal de la aplicación
    app.logger.setLevel(logging.INFO)
    
    # Crear handlers para diferentes tipos de logs
    
    # 1. Log general de la aplicación
    general_log = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    general_log.setLevel(logging.INFO)
    general_log.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    
    # 2. Log específico para operaciones de base de datos
    db_log = RotatingFileHandler(
        os.path.join(log_dir, 'database.log'),
        maxBytes=1024 * 1024,
        backupCount=10
    )
    db_log.setLevel(logging.INFO)
    db_log.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s'
    ))
    
    # 3. Log para errores críticos
    error_log = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=1024 * 1024,
        backupCount=10
    )
    error_log.setLevel(logging.ERROR)
    error_log.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s [in %(pathname)s:%(lineno)d]:\n%(message)s'
    ))
    
    # Agregar los handlers al logger de la aplicación
    app.logger.addHandler(general_log)
    app.logger.addHandler(db_log)
    app.logger.addHandler(error_log)
    
    # Crear loggers específicos
    db_logger = logging.getLogger('database')
    db_logger.setLevel(logging.INFO)
    db_logger.addHandler(db_log)
    
    return {
        'db_logger': db_logger
    }

def log_database_operation(logger, operation, details):
    """
    Registra una operación de base de datos con detalles.
    
    Args:
        logger: Logger instance
        operation: Tipo de operación (INSERT, UPDATE, DELETE, etc.)
        details: Detalles de la operación
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    message = f"{timestamp} - {operation}: {details}"
    logger.info(message) 