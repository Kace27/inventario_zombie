from flask import Flask, render_template, jsonify, request
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os
import sqlite3
import datetime

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
    DATABASE=os.path.join(app.instance_path, 'inventario_zombie.sqlite'),
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    PERMANENT_SESSION_LIFETIME=int(os.environ.get('SESSION_LIFETIME', 3600)),  # 1 hour default
)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Import database module
from database import init_app, get_db
init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from routes.auth import User
    return User.get_by_id(user_id)

# Add now function to templates
@app.template_global()
def now():
    return datetime.datetime.now()

# Import error handler and initialize it
from utils.error_handler import ErrorHandler
error_handler = ErrorHandler(app)

# Enable CORS
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return jsonify({}), 200

# Main route - redirect to login if not authenticated
@app.route('/')
@login_required
def index():
    # Redirect to appropriate page based on role
    if current_user.rol == 'cocina':
        return render_template('index.html', title='Panel de Cocina')
    else:
        return render_template('index.html', title='Panel de Administración')

# Import API routes
import routes.ingredientes
import routes.articulos
import routes.composicion
import routes.ventas
import routes.recepciones
import routes.web
import routes.auth

# Register API blueprints
app.register_blueprint(routes.ingredientes.ingredientes_bp)
app.register_blueprint(routes.articulos.articulos_bp)
app.register_blueprint(routes.composicion.composicion_bp)
app.register_blueprint(routes.ventas.bp)
app.register_blueprint(routes.recepciones.bp)
app.register_blueprint(routes.auth.auth_bp)

# Register web UI blueprints
app.register_blueprint(routes.ingredientes.ingredientes_web_bp)
app.register_blueprint(routes.articulos.articulos_web_bp)
routes.web.register_web_blueprints(app)

def verify_schema():
    """Verify the database schema and add missing columns if needed"""
    with app.app_context():
        db = get_db()
        # Check for categoria column in Ingredientes table
        try:
            cursor = db.execute("PRAGMA table_info(Ingredientes)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'categoria' not in columns:
                print("Adding 'categoria' column to Ingredientes table...")
                db.execute("ALTER TABLE Ingredientes ADD COLUMN categoria TEXT")
                db.commit()
                print("Added 'categoria' column successfully.")
        except sqlite3.Error as e:
            print(f"Schema verification error: {e}")
        
        # Check if Usuarios table exists
        try:
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Usuarios'")
            if not cursor.fetchone():
                print("Usuarios table not found. You should run the migration script.")
                print("Run: python migrate_add_usuarios.py")
        except sqlite3.Error as e:
            print(f"Schema verification error: {e}")

if __name__ == '__main__':
    # Ensure the database is initialized
    with app.app_context():
        try:
            db = get_db()
            # Check if tables exist
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            if not tables or len(tables) < 6:  # Check if we have all our tables
                print("Initializing database tables...")
                with app.open_resource('schema.sql') as f:
                    db.executescript(f.read().decode('utf8'))
                db.commit()
                print("Database initialized successfully!")
            else:
                print(f"Database already initialized with tables: {', '.join(tables)}")
                # Verify schema has the expected columns
                verify_schema()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
    
    app.run(host="0.0.0.0", port=8000, debug=True) 