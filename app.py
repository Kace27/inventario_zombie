from flask import Flask, render_template
from dotenv import load_dotenv
import os

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
from database import init_app
init_app(app)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Register blueprints for different modules
# from routes import ingredientes_bp, articulos_bp, ventas_bp, recepciones_bp
# app.register_blueprint(ingredientes_bp)
# app.register_blueprint(articulos_bp)
# app.register_blueprint(ventas_bp)
# app.register_blueprint(recepciones_bp)

if __name__ == '__main__':
    app.run(debug=True) 