from flask import Blueprint, render_template, jsonify
import json
from utils.auth_middleware import admin_required, cocina_required, any_role_required, role_required

# Para depuración
def get_api_endpoints():
    return {
        "ingredientes": "/api/ingredientes",
        "articulos": "/api/articulos",
        "recepciones": "/api/recepciones",
        "ventas": "/api/ventas"
    }

# Create web route blueprints
ventas_web = Blueprint('ventas_web', __name__, url_prefix='/ventas')
recepciones_web = Blueprint('recepciones_web', __name__, url_prefix='/recepciones')
inventario_web = Blueprint('inventario_web', __name__, url_prefix='/inventario')

# Debug endpoint - mostrar todas las rutas y endpoints
@ventas_web.route('/debug', methods=['GET'])
@recepciones_web.route('/debug', methods=['GET'])
@inventario_web.route('/debug', methods=['GET'])
def debug_endpoints():
    """Show all available API endpoints for debugging"""
    endpoints = get_api_endpoints()
    return jsonify(endpoints)

# Sales web routes
@ventas_web.route('/importar', methods=['GET'])
def importar():
    """Render the sales import page"""
    return render_template('ventas/importar.html')

@ventas_web.route('/importar-recibos', methods=['GET'])
def importar_recibos():
    """Render the receipts import page"""
    return render_template('ventas/importar_recibos.html')

@ventas_web.route('', methods=['GET'])
def lista():
    """Render the sales listing page"""
    return render_template('ventas/lista.html')

# Kitchen receptions web routes
@recepciones_web.route('', methods=['GET'])
@any_role_required
def formulario():
    """Render the kitchen reception form page"""
    return render_template('recepciones/formulario.html')

@recepciones_web.route('/historial', methods=['GET'])
@role_required(['admin', 'cocina'])
def historial():
    """Render the reception history page (accessible by admin and kitchen staff)"""
    return render_template('recepciones/historial.html')

# Inventory web routes
@inventario_web.route('/dashboard', methods=['GET'])
def dashboard():
    """Render the inventory dashboard page"""
    return render_template('ingredientes/dashboard.html')

# Register the blueprints with the app
def register_web_blueprints(app):
    app.register_blueprint(ventas_web)
    app.register_blueprint(recepciones_web)
    app.register_blueprint(inventario_web) 