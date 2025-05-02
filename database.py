import sqlite3
import click
import os
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """Connect to the application's configured database."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

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
    """Close the database connection."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    """Clear existing data and create new tables."""
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command) 