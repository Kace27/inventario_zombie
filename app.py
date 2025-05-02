from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import os
import sqlite3

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
    DATABASE=os.path.join(app.instance_path, 'inventario_zombie.sqlite'),
)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Import database module
from database import init_app, get_db
init_app(app)

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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Import API routes
import routes.ingredientes
import routes.articulos
import routes.composicion
import routes.ventas
import routes.recepciones

# Register API blueprints
app.register_blueprint(routes.ingredientes.ingredientes_bp)
app.register_blueprint(routes.articulos.articulos_bp)
app.register_blueprint(routes.composicion.composicion_bp)
app.register_blueprint(routes.ventas.bp)
app.register_blueprint(routes.recepciones.bp)

# Register web UI blueprints
app.register_blueprint(routes.ingredientes.ingredientes_web_bp)
app.register_blueprint(routes.articulos.articulos_web_bp)

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
        except sqlite3.Error as e:
            print(f"Database error: {e}")
    
    app.run(debug=True) 