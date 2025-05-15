import sqlite3
import click
import os
from flask import current_app, g
from flask.cli import with_appcontext
from contextlib import contextmanager
from datetime import datetime

def get_db():
    """Obtener la conexión a la base de datos."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            os.path.join(current_app.instance_path, 'inventario_zombie.sqlite'),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        
        # Configurar la base de datos para mayor seguridad
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging para mejor concurrencia
        g.db.execute("PRAGMA busy_timeout=5000")  # 5 segundos de timeout
        
    return g.db

def get_db_connection():
    """Get a database connection for use outside the application context."""
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE']
    except RuntimeError:
        # Si no estamos en un contexto de aplicación, usamos la ruta directa
        # Usamos la ruta absoluta para asegurar que siempre se conecte a la misma base de datos
        import os
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(root_dir, 'instance', 'inventario_zombie.sqlite')
        print(f"Connecting to database at: {db_path}")
    
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(e=None):
    """Cerrar la conexión a la base de datos."""
    db = g.pop('db', None)
    
    if db is not None:
        try:
            db.close()
        except Exception as e:
            current_app.logger.error(f"Error al cerrar la conexión: {str(e)}")

@contextmanager
def get_db_cursor():
    """
    Contexto seguro para operaciones con la base de datos.
    Maneja automáticamente las transacciones y el cierre de conexiones.
    """
    connection = get_db()
    cursor = connection.cursor()
    
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        current_app.logger.error(f"Error en la transacción: {str(e)}")
        raise
    finally:
        cursor.close()

def init_db():
    """Inicializar la base de datos."""
    try:
        db = get_db()
        
        # Crear directorio de respaldo si no existe
        backup_dir = os.path.join(current_app.instance_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Hacer backup antes de inicializar
        backup_path = os.path.join(backup_dir, 'pre_init_backup.sqlite')
        with open(backup_path, 'wb') as backup_file:
            for line in db.iterdump():
                backup_file.write(f'{line}\n'.encode('utf-8'))
        
        # Ejecutar el schema
        with current_app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf-8'))
            
        current_app.logger.info("Base de datos inicializada correctamente")
        
    except Exception as e:
        current_app.logger.error(f"Error al inicializar la base de datos: {str(e)}")
        raise

def backup_db():
    """
    Crear un backup de la base de datos.
    Retorna: La ruta del archivo de backup creado.
    """
    try:
        db = get_db()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(current_app.instance_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(backup_dir, f'backup_{timestamp}.sqlite')
        
        # Crear backup
        with open(backup_path, 'wb') as backup_file:
            for line in db.iterdump():
                backup_file.write(f'{line}\n'.encode('utf-8'))
        
        current_app.logger.info(f"Backup creado exitosamente en: {backup_path}")
        return backup_path
        
    except Exception as e:
        current_app.logger.error(f"Error al crear backup: {str(e)}")
        raise

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    """Inicializar la extensión de base de datos."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

def verify_db_integrity():
    """
    Verificar la integridad de la base de datos.
    Retorna: True si la base de datos está íntegra, False en caso contrario.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            current_app.logger.info("Verificación de integridad exitosa")
            return True
        else:
            current_app.logger.error(f"Error de integridad en la base de datos: {result}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error al verificar integridad: {str(e)}")
        return False 