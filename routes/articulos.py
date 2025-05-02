from flask import Blueprint, jsonify, request, render_template
from database import get_db
from utils.validators import validate_request_json, validate_id, validate_numeric, validate_string

# Create a blueprint for product API routes
articulos_bp = Blueprint('articulos', __name__, url_prefix='/api/articulos')

# Create a blueprint for product web routes
articulos_web_bp = Blueprint('articulos_web', __name__, url_prefix='/articulos')

@articulos_web_bp.route('/', methods=['GET'])
def index():
    """Render the products list page"""
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos')
    articulos = [dict(id=row['id'], 
                     nombre=row['nombre'], 
                     categoria=row['categoria'],
                     subcategoria=row['subcategoria'],
                     precio_venta=row['precio_venta']) 
                 for row in cursor.fetchall()]
    return render_template('articulos/lista.html', articulos=articulos)

@articulos_web_bp.route('/nuevo', methods=['GET'])
def nuevo():
    """Render the new product form"""
    return render_template('articulos/formulario.html')

@articulos_web_bp.route('/editar/<int:id>', methods=['GET'])
def editar(id):
    """Render the edit product form"""
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
    articulo = cursor.fetchone()
    if articulo is None:
        # Handle not found
        return render_template('error.html', message='Artículo no encontrado'), 404
    return render_template('articulos/formulario.html', articulo=articulo)

@articulos_web_bp.route('/composicion/<int:id>', methods=['GET'])
def composicion(id):
    """Render the product composition page"""
    db = get_db()
    
    # Get the product
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
    articulo = cursor.fetchone()
    if articulo is None:
        # Handle not found
        return render_template('error.html', message='Artículo no encontrado'), 404
    
    # Get the composition
    cursor = db.execute('''
        SELECT c.id, c.articulo_id, c.ingrediente_id, c.cantidad, 
               i.nombre as ingrediente_nombre, i.unidad_medida, i.precio_compra
        FROM ComposicionArticulo c
        JOIN Ingredientes i ON c.ingrediente_id = i.id
        WHERE c.articulo_id = ?
    ''', (id,))
    composicion = [dict(id=row['id'],
                       articulo_id=row['articulo_id'],
                       ingrediente_id=row['ingrediente_id'],
                       cantidad=row['cantidad'],
                       ingrediente_nombre=row['ingrediente_nombre'],
                       unidad_medida=row['unidad_medida'],
                       precio_compra=row['precio_compra'])
                  for row in cursor.fetchall()]
    
    # Get all ingredients for the dropdown
    cursor = db.execute('SELECT * FROM Ingredientes')
    ingredientes = [dict(id=row['id'],
                        nombre=row['nombre'],
                        unidad_medida=row['unidad_medida'])
                   for row in cursor.fetchall()]
    
    # Calculate the total cost
    costo_total = sum(comp['precio_compra'] * comp['cantidad'] for comp in composicion)
    
    return render_template('articulos/composicion.html', 
                          articulo=articulo, 
                          composicion=composicion, 
                          ingredientes=ingredientes,
                          costo_total=costo_total)

@articulos_bp.route('', methods=['GET'])
def get_articulos():
    """Get all products"""
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos')
    articulos = [dict(id=row['id'], 
                     nombre=row['nombre'], 
                     categoria=row['categoria'],
                     subcategoria=row['subcategoria'],
                     precio_venta=row['precio_venta']) 
                 for row in cursor.fetchall()]
    return jsonify(articulos)

@articulos_bp.route('', methods=['POST'])
def create_articulo():
    """Create a new product"""
    # Validate request
    is_valid, data, error_response = validate_request_json(['nombre'])
    if not is_valid:
        return error_response
    
    # Validate fields
    if not validate_string(data['nombre'], min_length=1, max_length=100):
        return jsonify({'error': 'Invalid name'}), 400
    
    # Validate optional fields if provided
    if 'categoria' in data and data['categoria'] is not None:
        if not validate_string(data['categoria'], max_length=50):
            return jsonify({'error': 'Invalid category'}), 400
    
    if 'subcategoria' in data and data['subcategoria'] is not None:
        if not validate_string(data['subcategoria'], max_length=50):
            return jsonify({'error': 'Invalid subcategory'}), 400
    
    if 'precio_venta' in data and data['precio_venta'] is not None:
        if not validate_numeric(data['precio_venta'], min_value=0):
            return jsonify({'error': 'Invalid sale price'}), 400
    
    # Prepare the data
    categoria = data.get('categoria')
    subcategoria = data.get('subcategoria')
    precio_venta = data.get('precio_venta')
    
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO ArticulosVendidos (nombre, categoria, subcategoria, precio_venta) '
            'VALUES (?, ?, ?, ?)',
            (data['nombre'], categoria, subcategoria, precio_venta)
        )
        db.commit()
        
        # Get the created product
        articulo_id = cursor.lastrowid
        cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (articulo_id,))
        articulo = cursor.fetchone()
        
        return jsonify({
            'id': articulo['id'],
            'nombre': articulo['nombre'],
            'categoria': articulo['categoria'],
            'subcategoria': articulo['subcategoria'],
            'precio_venta': articulo['precio_venta']
        }), 201
    except db.IntegrityError:
        return jsonify({'error': 'Product name already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/<int:id>', methods=['GET'])
def get_articulo(id):
    """Get a specific product by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'id': articulo['id'],
        'nombre': articulo['nombre'],
        'categoria': articulo['categoria'],
        'subcategoria': articulo['subcategoria'],
        'precio_venta': articulo['precio_venta']
    })

@articulos_bp.route('/<int:id>', methods=['PUT'])
def update_articulo(id):
    """Update a specific product by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    # Validate request
    is_valid, data, error_response = validate_request_json()
    if not is_valid:
        return error_response
    
    # Check if the product exists
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    # Validate fields if provided
    if 'nombre' in data and data['nombre'] is not None:
        if not validate_string(data['nombre'], min_length=1, max_length=100):
            return jsonify({'error': 'Invalid name'}), 400
    
    if 'categoria' in data and data['categoria'] is not None:
        if not validate_string(data['categoria'], max_length=50):
            return jsonify({'error': 'Invalid category'}), 400
    
    if 'subcategoria' in data and data['subcategoria'] is not None:
        if not validate_string(data['subcategoria'], max_length=50):
            return jsonify({'error': 'Invalid subcategory'}), 400
    
    if 'precio_venta' in data and data['precio_venta'] is not None:
        if not validate_numeric(data['precio_venta'], min_value=0):
            return jsonify({'error': 'Invalid sale price'}), 400
    
    # Prepare the update
    updates = []
    params = []
    
    if 'nombre' in data and data['nombre'] is not None:
        updates.append('nombre = ?')
        params.append(data['nombre'])
    
    if 'categoria' in data:
        updates.append('categoria = ?')
        params.append(data['categoria'])
    
    if 'subcategoria' in data:
        updates.append('subcategoria = ?')
        params.append(data['subcategoria'])
    
    if 'precio_venta' in data:
        updates.append('precio_venta = ?')
        params.append(data['precio_venta'])
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Execute the update
    try:
        params.append(id)
        db.execute(
            f'UPDATE ArticulosVendidos SET {", ".join(updates)} WHERE id = ?',
            params
        )
        db.commit()
        
        # Get the updated product
        cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
        updated_articulo = cursor.fetchone()
        
        return jsonify({
            'id': updated_articulo['id'],
            'nombre': updated_articulo['nombre'],
            'categoria': updated_articulo['categoria'],
            'subcategoria': updated_articulo['subcategoria'],
            'precio_venta': updated_articulo['precio_venta']
        })
    except db.IntegrityError:
        return jsonify({'error': 'Product name already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/<int:id>', methods=['DELETE'])
def delete_articulo(id):
    """Delete a specific product by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    
    # Check if the product exists
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        # First, check if there are compositions that use this product
        cursor = db.execute('SELECT COUNT(*) as count FROM ComposicionArticulo WHERE articulo_id = ?', (id,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            # First, delete all compositions for this product
            db.execute('DELETE FROM ComposicionArticulo WHERE articulo_id = ?', (id,))
        
        # Then, delete the product
        db.execute('DELETE FROM ArticulosVendidos WHERE id = ?', (id,))
        db.commit()
        
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500 