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
    
    # Get the variant information if this is a variant
    parent_info = None
    if articulo['es_variante'] and articulo['articulo_padre_id']:
        cursor = db.execute('SELECT id, nombre FROM ArticulosVendidos WHERE id = ?', (articulo['articulo_padre_id'],))
        parent = cursor.fetchone()
        if parent:
            parent_info = {
                'id': parent['id'],
                'nombre': parent['nombre']
            }
    
    # Get all variants if this is a parent product
    variants_info = []
    cursor = db.execute('SELECT id, nombre FROM ArticulosVendidos WHERE articulo_padre_id = ?', (articulo_id,))
    variants = cursor.fetchall()
    if variants:
        variants_info = [dict(id=v['id'], nombre=v['nombre']) for v in variants]
    
    return jsonify({
        'articulo_id': articulo_id,
        'articulo_nombre': articulo['nombre'],
        'es_variante': articulo['es_variante'],
        'articulo_padre': parent_info,
        'variantes': variants_info,
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
    
    # Check if we should apply to variants
    aplicar_a_variantes = data.get('aplicar_a_variantes', False)
    
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
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        # Add the ingredient to the composition
        cursor = db.execute(
            'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
            (articulo_id, data['ingrediente_id'], data['cantidad'])
        )
        composition_id = cursor.lastrowid
        
        # If requested, apply to variants
        variant_compositions = []
        if aplicar_a_variantes and articulo['es_variante'] == 0:
            # Get all variants of this product
            cursor = db.execute('SELECT id FROM ArticulosVendidos WHERE articulo_padre_id = ?', (articulo_id,))
            variants = cursor.fetchall()
            
            # Add the ingredient to all variants
            for variant in variants:
                variant_id = variant['id']
                
                # Check if the ingredient is already in the variant's composition
                cursor = db.execute(
                    'SELECT * FROM ComposicionArticulo WHERE articulo_id = ? AND ingrediente_id = ?',
                    (variant_id, data['ingrediente_id'])
                )
                if cursor.fetchone() is None:
                    # Add the ingredient to the variant
                    cursor = db.execute(
                        'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
                        (variant_id, data['ingrediente_id'], data['cantidad'])
                    )
                    variant_comp_id = cursor.lastrowid
                    variant_compositions.append({
                        'id': variant_comp_id,
                        'articulo_id': variant_id
                    })
        
        db.commit()
        
        # Get the created composition
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
            'unidad_medida': composicion['unidad_medida'],
            'variant_compositions': variant_compositions
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@composicion_bp.route('/api/composicion/<int:id>', methods=['DELETE'])
def delete_composicion(id):
    """Delete a specific composition entry by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    # Check if we should delete from variants too
    aplicar_a_variantes = request.args.get('aplicar_a_variantes', 'false').lower() == 'true'
    
    db = get_db()
    
    # Check if the composition exists
    cursor = db.execute('''
        SELECT c.*, a.id as articulo_id, a.es_variante
        FROM ComposicionArticulo c
        JOIN ArticulosVendidos a ON c.articulo_id = a.id
        WHERE c.id = ?
    ''', (id,))
    composicion = cursor.fetchone()
    
    if composicion is None:
        return jsonify({'error': 'Composition entry not found'}), 404
    
    try:
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        # Delete the composition entry
        db.execute('DELETE FROM ComposicionArticulo WHERE id = ?', (id,))
        
        # If aplicar_a_variantes is true and the product is not a variant itself,
        # delete the same ingredient from all variants
        deleted_from_variants = []
        if aplicar_a_variantes and not composicion['es_variante']:
            # Get all variants
            cursor = db.execute('SELECT id FROM ArticulosVendidos WHERE articulo_padre_id = ?', (composicion['articulo_id'],))
            variants = cursor.fetchall()
            
            # Delete the same ingredient from all variants
            for variant in variants:
                cursor = db.execute(
                    'DELETE FROM ComposicionArticulo WHERE articulo_id = ? AND ingrediente_id = ?',
                    (variant['id'], composicion['ingrediente_id'])
                )
                if cursor.rowcount > 0:
                    deleted_from_variants.append(variant['id'])
        
        db.commit()
        
        return jsonify({
            'message': 'Composition entry deleted successfully',
            'deleted_from_variants': deleted_from_variants
        }), 200
    except Exception as e:
        db.rollback()
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
    
    # Check if we should apply to variants too
    aplicar_a_variantes = data.get('aplicar_a_variantes', False)
    
    db = get_db()
    
    # Check if the composition exists
    cursor = db.execute('''
        SELECT c.*, a.id as articulo_id, a.es_variante
        FROM ComposicionArticulo c
        JOIN ArticulosVendidos a ON c.articulo_id = a.id
        WHERE c.id = ?
    ''', (id,))
    composicion = cursor.fetchone()
    
    if composicion is None:
        return jsonify({'error': 'Composition entry not found'}), 404
    
    try:
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        # Update the composition
        db.execute(
            'UPDATE ComposicionArticulo SET cantidad = ? WHERE id = ?',
            (data['cantidad'], id)
        )
        
        # If aplicar_a_variantes is true and the product is not a variant itself,
        # update the same ingredient in all variants
        updated_variants = []
        if aplicar_a_variantes and not composicion['es_variante']:
            # Get all variants
            cursor = db.execute('SELECT id FROM ArticulosVendidos WHERE articulo_padre_id = ?', (composicion['articulo_id'],))
            variants = cursor.fetchall()
            
            # Update the same ingredient in all variants
            for variant in variants:
                cursor = db.execute(
                    '''
                    UPDATE ComposicionArticulo 
                    SET cantidad = ? 
                    WHERE articulo_id = ? AND ingrediente_id = ?
                    ''',
                    (data['cantidad'], variant['id'], composicion['ingrediente_id'])
                )
                if cursor.rowcount > 0:
                    updated_variants.append(variant['id'])
        
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
            'unidad_medida': updated['unidad_medida'],
            'updated_variants': updated_variants
        })
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@composicion_bp.route('/api/articulos/<int:articulo_id>/sincronizar-variantes', methods=['POST'])
def sincronizar_composicion_variantes(articulo_id):
    """Synchronize the composition of all variants with the parent product"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid article ID format'}), 400
    
    db = get_db()
    
    # Verify the parent product exists and is not a variant
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ? AND es_variante = 0', (articulo_id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Parent product not found or product is a variant'}), 404
    
    try:
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        # Get all variants of this product
        cursor = db.execute('SELECT id, nombre FROM ArticulosVendidos WHERE articulo_padre_id = ?', (articulo_id,))
        variants = cursor.fetchall()
        
        if not variants:
            return jsonify({'message': 'No variants found for this product'}), 200
        
        # Get the parent product's composition
        cursor = db.execute(
            'SELECT ingrediente_id, cantidad FROM ComposicionArticulo WHERE articulo_id = ?',
            (articulo_id,)
        )
        parent_composition = cursor.fetchall()
        
        if not parent_composition:
            return jsonify({'message': 'Parent product has no composition to synchronize'}), 200
        
        # Track changes for each variant
        changes = []
        
        # Process each variant
        for variant in variants:
            variant_id = variant['id']
            variant_changes = {
                'variant_id': variant_id,
                'variant_name': variant['nombre'],
                'added': [],
                'updated': [],
                'deleted': []
            }
            
            # Get the variant's current composition
            cursor = db.execute(
                'SELECT id, ingrediente_id, cantidad FROM ComposicionArticulo WHERE articulo_id = ?',
                (variant_id,)
            )
            variant_composition = {row['ingrediente_id']: {'id': row['id'], 'cantidad': row['cantidad']} for row in cursor.fetchall()}
            
            # Process parent composition ingredients
            parent_ingredientes = {row['ingrediente_id']: row['cantidad'] for row in parent_composition}
            
            # Add or update ingredients from parent
            for ingrediente_id, cantidad in parent_ingredientes.items():
                if ingrediente_id in variant_composition:
                    # Update existing ingredient if quantity differs
                    if variant_composition[ingrediente_id]['cantidad'] != cantidad:
                        cursor = db.execute(
                            'UPDATE ComposicionArticulo SET cantidad = ? WHERE id = ?',
                            (cantidad, variant_composition[ingrediente_id]['id'])
                        )
                        variant_changes['updated'].append({
                            'ingrediente_id': ingrediente_id,
                            'cantidad': cantidad
                        })
                else:
                    # Add new ingredient
                    cursor = db.execute(
                        'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
                        (variant_id, ingrediente_id, cantidad)
                    )
                    variant_changes['added'].append({
                        'ingrediente_id': ingrediente_id,
                        'cantidad': cantidad
                    })
            
            # Remove ingredients not in parent
            for ingrediente_id, comp_data in variant_composition.items():
                if ingrediente_id not in parent_ingredientes:
                    cursor = db.execute(
                        'DELETE FROM ComposicionArticulo WHERE id = ?',
                        (comp_data['id'],)
                    )
                    variant_changes['deleted'].append({
                        'ingrediente_id': ingrediente_id
                    })
            
            # Add to changes if any were made
            if variant_changes['added'] or variant_changes['updated'] or variant_changes['deleted']:
                changes.append(variant_changes)
        
        db.commit()
        
        return jsonify({
            'message': f'Successfully synchronized composition for {len(changes)} variants',
            'changes': changes
        })
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500 