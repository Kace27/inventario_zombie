from flask import Blueprint, jsonify, request
from database import get_db
from utils.validators import validate_request_json, validate_id, validate_numeric

# Create a blueprint for product composition routes
composicion_bp = Blueprint('composicion', __name__)

@composicion_bp.route('/api/articulos/<int:articulo_id>/composicion', methods=['GET'])
def get_composicion(articulo_id):
    """Get the composition of a specific product"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid article ID format'}), 400
    
    db = get_db()
    
    # Verify the product exists
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (articulo_id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    # Get the composition
    cursor = db.execute(
        '''
        SELECT c.id, c.articulo_id, c.ingrediente_id, c.cantidad, 
               i.nombre as ingrediente_nombre, i.unidad_medida
        FROM ComposicionArticulo c
        JOIN Ingredientes i ON c.ingrediente_id = i.id
        WHERE c.articulo_id = ?
        ''',
        (articulo_id,)
    )
    
    composicion = [dict(
        id=row['id'],
        articulo_id=row['articulo_id'],
        ingrediente_id=row['ingrediente_id'],
        cantidad=row['cantidad'],
        ingrediente_nombre=row['ingrediente_nombre'],
        unidad_medida=row['unidad_medida']
    ) for row in cursor.fetchall()]
    
    return jsonify({
        'articulo_id': articulo_id,
        'articulo_nombre': articulo['nombre'],
        'composicion': composicion
    })

@composicion_bp.route('/api/articulos/<int:articulo_id>/composicion', methods=['POST'])
def add_ingrediente_to_composicion(articulo_id):
    """Add an ingredient to a product's composition"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid article ID format'}), 400
    
    # Validate request
    is_valid, data, error_response = validate_request_json(['ingrediente_id', 'cantidad'])
    if not is_valid:
        return error_response
    
    # Validate data
    if not validate_id(data['ingrediente_id']):
        return jsonify({'error': 'Invalid ingredient ID format'}), 400
    
    if not validate_numeric(data['cantidad'], min_value=0, allow_zero=False):
        return jsonify({'error': 'Invalid quantity'}), 400
    
    db = get_db()
    
    # Verify the product exists
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (articulo_id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    # Verify the ingredient exists
    cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (data['ingrediente_id'],))
    ingrediente = cursor.fetchone()
    
    if ingrediente is None:
        return jsonify({'error': 'Ingredient not found'}), 404
    
    # Check if the ingredient is already in the composition
    cursor = db.execute(
        'SELECT * FROM ComposicionArticulo WHERE articulo_id = ? AND ingrediente_id = ?',
        (articulo_id, data['ingrediente_id'])
    )
    existing = cursor.fetchone()
    
    if existing:
        return jsonify({
            'error': 'Ingredient is already in the product composition',
            'composition_id': existing['id']
        }), 409
    
    try:
        # Add the ingredient to the composition
        cursor = db.execute(
            'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
            (articulo_id, data['ingrediente_id'], data['cantidad'])
        )
        db.commit()
        
        # Get the created composition
        composition_id = cursor.lastrowid
        cursor = db.execute(
            '''
            SELECT c.id, c.articulo_id, c.ingrediente_id, c.cantidad,
                   i.nombre as ingrediente_nombre, i.unidad_medida
            FROM ComposicionArticulo c
            JOIN Ingredientes i ON c.ingrediente_id = i.id
            WHERE c.id = ?
            ''',
            (composition_id,)
        )
        composicion = cursor.fetchone()
        
        return jsonify({
            'id': composicion['id'],
            'articulo_id': composicion['articulo_id'],
            'ingrediente_id': composicion['ingrediente_id'],
            'cantidad': composicion['cantidad'],
            'ingrediente_nombre': composicion['ingrediente_nombre'],
            'unidad_medida': composicion['unidad_medida']
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@composicion_bp.route('/api/composicion/<int:id>', methods=['DELETE'])
def delete_composicion(id):
    """Delete a specific composition entry by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    
    # Check if the composition exists
    cursor = db.execute('SELECT * FROM ComposicionArticulo WHERE id = ?', (id,))
    composicion = cursor.fetchone()
    
    if composicion is None:
        return jsonify({'error': 'Composition entry not found'}), 404
    
    try:
        # Delete the composition entry
        db.execute('DELETE FROM ComposicionArticulo WHERE id = ?', (id,))
        db.commit()
        
        return jsonify({'message': 'Composition entry deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@composicion_bp.route('/api/composicion/<int:id>', methods=['PUT'])
def update_composicion(id):
    """Update a specific composition entry by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    # Validate request
    is_valid, data, error_response = validate_request_json(['cantidad'])
    if not is_valid:
        return error_response
    
    # Validate quantity
    if not validate_numeric(data['cantidad'], min_value=0, allow_zero=False):
        return jsonify({'error': 'Invalid quantity'}), 400
    
    db = get_db()
    
    # Check if the composition exists
    cursor = db.execute('SELECT * FROM ComposicionArticulo WHERE id = ?', (id,))
    composicion = cursor.fetchone()
    
    if composicion is None:
        return jsonify({'error': 'Composition entry not found'}), 404
    
    try:
        # Update the composition
        db.execute(
            'UPDATE ComposicionArticulo SET cantidad = ? WHERE id = ?',
            (data['cantidad'], id)
        )
        db.commit()
        
        # Get the updated composition
        cursor = db.execute(
            '''
            SELECT c.id, c.articulo_id, c.ingrediente_id, c.cantidad,
                   i.nombre as ingrediente_nombre, i.unidad_medida,
                   a.nombre as articulo_nombre
            FROM ComposicionArticulo c
            JOIN Ingredientes i ON c.ingrediente_id = i.id
            JOIN ArticulosVendidos a ON c.articulo_id = a.id
            WHERE c.id = ?
            ''',
            (id,)
        )
        updated = cursor.fetchone()
        
        return jsonify({
            'id': updated['id'],
            'articulo_id': updated['articulo_id'],
            'articulo_nombre': updated['articulo_nombre'],
            'ingrediente_id': updated['ingrediente_id'],
            'ingrediente_nombre': updated['ingrediente_nombre'],
            'cantidad': updated['cantidad'],
            'unidad_medida': updated['unidad_medida']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 