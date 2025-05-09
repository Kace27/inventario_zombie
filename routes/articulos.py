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
    
    # Primero verificamos si la columna existe
    cursor = db.execute("PRAGMA table_info(ArticulosVendidos)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'articulo_padre_id' not in columns:
        # Si la columna no existe, agregamos la columna
        db.execute("ALTER TABLE ArticulosVendidos ADD COLUMN articulo_padre_id INTEGER REFERENCES ArticulosVendidos(id)")
        db.execute("ALTER TABLE ArticulosVendidos ADD COLUMN es_variante BOOLEAN DEFAULT 0")
        db.commit()
    
    # Ahora ejecutamos la consulta normal
    cursor = db.execute('''
        SELECT 
            a.id,
            a.nombre,
            a.categoria,
            a.subcategoria,
            a.precio_venta,
            COALESCE(a.es_variante, 0) as es_variante,
            a.articulo_padre_id,
            p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
    ''')
    
    articulos = [dict(id=row['id'], 
                     nombre=row['nombre'], 
                     categoria=row['categoria'],
                     subcategoria=row['subcategoria'],
                     precio_venta=row['precio_venta'],
                     es_variante=row['es_variante'],
                     articulo_padre_id=row['articulo_padre_id'],
                     articulo_padre_nombre=row['articulo_padre_nombre']) 
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
    
    # Get the article with parent info
    cursor = db.execute('''
        SELECT a.*, p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
        WHERE a.id = ?
    ''', (id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        # Handle not found
        return render_template('error.html', message='Artículo no encontrado'), 404
    
    # Get variants if this is a parent product
    variantes = []
    if not articulo['es_variante']:
        cursor = db.execute('''
            SELECT id, nombre, precio_venta 
            FROM ArticulosVendidos 
            WHERE articulo_padre_id = ?
        ''', (id,))
        variantes = cursor.fetchall()
    
    # Get potential parent products (for making this a variant)
    cursor = db.execute('''
        SELECT id, nombre 
        FROM ArticulosVendidos 
        WHERE es_variante = 0 AND id != ?
    ''', (id,))
    productos_padre = cursor.fetchall()
    
    return render_template('articulos/formulario.html', 
                         articulo=articulo,
                         variantes=variantes,
                         productos_padre=productos_padre)

@articulos_web_bp.route('/composicion/<int:id>', methods=['GET'])
def composicion(id):
    """Render the product composition page"""
    db = get_db()
    
    # Get the product with parent info
    cursor = db.execute('''
        SELECT a.*, p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
        WHERE a.id = ?
    ''', (id,))
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
    
    # Si es una variante y no tiene composición propia, heredar del padre
    if articulo['es_variante'] and not composicion and articulo['articulo_padre_id']:
        cursor = db.execute('''
            SELECT c.id, c.articulo_id, c.ingrediente_id, c.cantidad, 
                   i.nombre as ingrediente_nombre, i.unidad_medida, i.precio_compra
            FROM ComposicionArticulo c
            JOIN Ingredientes i ON c.ingrediente_id = i.id
            WHERE c.articulo_id = ?
        ''', (articulo['articulo_padre_id'],))
        composicion = [dict(id=None,  # ID nulo para indicar que es heredado
                           articulo_id=id,  # Usamos el ID de la variante
                           ingrediente_id=row['ingrediente_id'],
                           cantidad=row['cantidad'],
                           ingrediente_nombre=row['ingrediente_nombre'],
                           unidad_medida=row['unidad_medida'],
                           precio_compra=row['precio_compra'],
                           heredado=True)  # Indicador de que es heredado
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
    cursor = db.execute('''
        SELECT a.*, p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
    ''')
    articulos = [dict(id=row['id'], 
                     nombre=row['nombre'], 
                     categoria=row['categoria'],
                     subcategoria=row['subcategoria'],
                     precio_venta=row['precio_venta'],
                     es_variante=row['es_variante'],
                     articulo_padre_id=row['articulo_padre_id'],
                     articulo_padre_nombre=row['articulo_padre_nombre']) 
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
            '''
            INSERT INTO ArticulosVendidos 
            (nombre, categoria, subcategoria, precio_venta, articulo_padre_id, es_variante) 
            VALUES (?, ?, ?, ?, NULL, 0)
            ''',
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
            'precio_venta': articulo['precio_venta'],
            'articulo_padre_id': articulo['articulo_padre_id'],
            'es_variante': articulo['es_variante']
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
    cursor = db.execute('''
        SELECT a.*, p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
        WHERE a.id = ?
    ''', (id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Product not found'}), 404
    
    # Get variants if this is a parent product
    variants = []
    if not articulo['es_variante']:
        cursor = db.execute(
            'SELECT id, nombre FROM ArticulosVendidos WHERE articulo_padre_id = ?',
            (id,)
        )
        variants = [dict(id=row['id'], nombre=row['nombre']) for row in cursor.fetchall()]
    
    return jsonify({
        'id': articulo['id'],
        'nombre': articulo['nombre'],
        'categoria': articulo['categoria'],
        'subcategoria': articulo['subcategoria'],
        'precio_venta': articulo['precio_venta'],
        'es_variante': articulo['es_variante'],
        'articulo_padre_id': articulo['articulo_padre_id'],
        'articulo_padre_nombre': articulo['articulo_padre_nombre'],
        'variantes': variants
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
    
    # Manejar campos de variantes
    if 'articulo_padre_id' in data:
        updates.append('articulo_padre_id = ?')
        params.append(data['articulo_padre_id'] or None)
        
        # Si se establece un artículo padre, es una variante
        if data['articulo_padre_id']:
            updates.append('es_variante = 1')
        else:
            updates.append('es_variante = 0')
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Execute the update
    try:
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        params.append(id)
        db.execute(
            f'UPDATE ArticulosVendidos SET {", ".join(updates)} WHERE id = ?',
            params
        )
        
        # If this is a parent article (not a variant), update all its variants with the same changes
        # but preserve their specific variant names and any variant-specific pricing
        if articulo['es_variante'] == 0:
            # Get all variants of this parent article
            cursor = db.execute('SELECT id, nombre FROM ArticulosVendidos WHERE articulo_padre_id = ?', (id,))
            variants = cursor.fetchall()
            
            # Update each variant if we have variants
            if variants:
                variant_updates = []
                variant_params = []
                
                # Only propagate category and subcategory updates to variants
                # Don't update the name because variants have their own names
                # Don't update the precio_venta by default to preserve variant-specific pricing
                if 'categoria' in data:
                    variant_updates.append('categoria = ?')
                    variant_params.append(data['categoria'])
                
                if 'subcategoria' in data:
                    variant_updates.append('subcategoria = ?')
                    variant_params.append(data['subcategoria'])
                
                # Only apply precio_venta update if specifically requested by adding a parameter
                # This could be controlled via a checkbox in the UI
                propagate_price = request.args.get('propagate_price', 'false').lower() == 'true'
                if 'precio_venta' in data and propagate_price:
                    variant_updates.append('precio_venta = ?')
                    variant_params.append(data['precio_venta'])
                
                # Update variants if there are any changes to apply
                if variant_updates:
                    # For each variant, update with the parent's changes
                    for variant in variants:
                        # If the parent name changed and the variant name includes the parent name, update it
                        if 'nombre' in data and data['nombre'] is not None:
                            # Get the current variant name
                            variant_name = variant['nombre']
                            
                            # Check if the variant name contains the parent name
                            if articulo['nombre'] in variant_name:
                                # Replace the old parent name with the new one
                                new_variant_name = variant_name.replace(articulo['nombre'], data['nombre'])
                                
                                # Add name update for this variant
                                db.execute(
                                    'UPDATE ArticulosVendidos SET nombre = ? WHERE id = ?',
                                    (new_variant_name, variant['id'])
                                )
                        
                        # Apply the other updates to the variant
                        if variant_updates:
                            variant_update_params = variant_params.copy()
                            variant_update_params.append(variant['id'])
                            db.execute(
                                f'UPDATE ArticulosVendidos SET {", ".join(variant_updates)} WHERE id = ?',
                                variant_update_params
                            )
        
        # Commit all changes
        db.commit()
        
        # Get the updated product with parent info
        cursor = db.execute('''
            SELECT a.*, p.nombre as articulo_padre_nombre 
            FROM ArticulosVendidos a
            LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
            WHERE a.id = ?
        ''', (id,))
        updated_articulo = cursor.fetchone()
        
        return jsonify({
            'id': updated_articulo['id'],
            'nombre': updated_articulo['nombre'],
            'categoria': updated_articulo['categoria'],
            'subcategoria': updated_articulo['subcategoria'],
            'precio_venta': updated_articulo['precio_venta'],
            'es_variante': updated_articulo['es_variante'],
            'articulo_padre_id': updated_articulo['articulo_padre_id'],
            'articulo_padre_nombre': updated_articulo['articulo_padre_nombre']
        })
    except db.IntegrityError:
        # Rollback in case of error
        db.execute('ROLLBACK')
        return jsonify({'error': 'Product name already exists'}), 409
    except Exception as e:
        # Rollback in case of error
        db.execute('ROLLBACK')
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

@articulos_bp.route('/variantes/<int:articulo_id>', methods=['GET'])
def get_variantes(articulo_id):
    """Get all variants of a specific product by ID"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    cursor = db.execute(
        'SELECT * FROM ArticulosVendidos WHERE articulo_padre_id = ?',
        (articulo_id,)
    )
    variantes = [dict(id=row['id'], 
                     nombre=row['nombre'], 
                     categoria=row['categoria'],
                     subcategoria=row['subcategoria'],
                     precio_venta=row['precio_venta'],
                     es_variante=row['es_variante'],
                     articulo_padre_id=row['articulo_padre_id'])
                 for row in cursor.fetchall()]
    
    return jsonify(variantes)

@articulos_bp.route('/<int:articulo_id>/agregar-variante', methods=['POST'])
def agregar_variante(articulo_id):
    """Add a variant to a specific product by ID"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    # Validate request
    is_valid, data, error_response = validate_request_json(['nombre'])
    if not is_valid:
        return error_response
    
    # Validate fields
    if not validate_string(data['nombre'], min_length=1, max_length=100):
        return jsonify({'error': 'Invalid name'}), 400
    
    # Validate optional fields if provided
    if 'precio_venta' in data and data['precio_venta'] is not None:
        if not validate_numeric(data['precio_venta'], min_value=0):
            return jsonify({'error': 'Invalid sale price'}), 400
    
    # Check if the parent product exists
    db = get_db()
    cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (articulo_id,))
    articulo_padre = cursor.fetchone()
    
    if articulo_padre is None:
        return jsonify({'error': 'Parent product not found'}), 404
    
    # Crear el nombre completo de la variante: "Nombre Padre - Nombre Variante"
    nombre_completo = f"{articulo_padre['nombre']} - {data['nombre']}"
    
    # Check if the variant name already exists
    cursor = db.execute('SELECT id FROM ArticulosVendidos WHERE nombre = ?', (nombre_completo,))
    if cursor.fetchone() is not None:
        return jsonify({'error': 'Product name already exists'}), 409
    
    try:
        # Prepare the data
        precio_venta = data.get('precio_venta', articulo_padre['precio_venta'])
        
        # Create the variant
        cursor = db.execute(
            '''
            INSERT INTO ArticulosVendidos 
            (nombre, categoria, subcategoria, precio_venta, articulo_padre_id, es_variante) 
            VALUES (?, ?, ?, ?, ?, 1)
            ''',
            (nombre_completo, articulo_padre['categoria'], articulo_padre['subcategoria'], 
             precio_venta, articulo_id)
        )
        db.commit()
        
        # Get the created variant
        variante_id = cursor.lastrowid
        cursor = db.execute('SELECT * FROM ArticulosVendidos WHERE id = ?', (variante_id,))
        variante = cursor.fetchone()
        
        # Copy composition from parent product
        cursor = db.execute(
            'SELECT ingrediente_id, cantidad FROM ComposicionArticulo WHERE articulo_id = ?',
            (articulo_id,)
        )
        composicion_padre = cursor.fetchall()
        
        # Insert composition for the variant
        for comp in composicion_padre:
            db.execute(
                'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
                (variante_id, comp['ingrediente_id'], comp['cantidad'])
            )
        db.commit()
        
        return jsonify({
            'id': variante['id'],
            'nombre': variante['nombre'],
            'categoria': variante['categoria'],
            'subcategoria': variante['subcategoria'],
            'precio_venta': variante['precio_venta'],
            'articulo_padre_id': variante['articulo_padre_id'],
            'es_variante': variante['es_variante']
        }), 201
    except db.IntegrityError:
        return jsonify({'error': 'Product name already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/reglas-variantes', methods=['GET'])
def get_reglas_variantes():
    """Get all variant rules"""
    db = get_db()
    cursor = db.execute('SELECT * FROM ReglasVariantes')
    reglas = [dict(id=row['id'],
                  patron_principal=row['patron_principal'],
                  patron_variante=row['patron_variante'],
                  descripcion=row['descripcion'],
                  activo=row['activo'])
              for row in cursor.fetchall()]
    return jsonify(reglas)

@articulos_bp.route('/reglas-variantes', methods=['POST'])
def crear_regla_variante():
    """Create a new variant rule"""
    # Validate request
    is_valid, data, error_response = validate_request_json(['patron_principal', 'patron_variante'])
    if not is_valid:
        return error_response
    
    # Validate fields
    if not validate_string(data['patron_principal'], min_length=1, max_length=100):
        return jsonify({'error': 'Invalid main pattern'}), 400
    
    if not validate_string(data['patron_variante'], min_length=1, max_length=100):
        return jsonify({'error': 'Invalid variant pattern'}), 400
    
    # Optional description
    descripcion = data.get('descripcion', '')
    
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO ReglasVariantes (patron_principal, patron_variante, descripcion) VALUES (?, ?, ?)',
            (data['patron_principal'], data['patron_variante'], descripcion)
        )
        db.commit()
        
        # Get the created rule
        regla_id = cursor.lastrowid
        cursor = db.execute('SELECT * FROM ReglasVariantes WHERE id = ?', (regla_id,))
        regla = cursor.fetchone()
        
        return jsonify({
            'id': regla['id'],
            'patron_principal': regla['patron_principal'],
            'patron_variante': regla['patron_variante'],
            'descripcion': regla['descripcion'],
            'activo': regla['activo']
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/reglas-variantes/<int:regla_id>', methods=['PUT'])
def actualizar_regla_variante(regla_id):
    """Update a specific variant rule by ID"""
    if not validate_id(regla_id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    # Validate request
    is_valid, data, error_response = validate_request_json()
    if not is_valid:
        return error_response
    
    # Check if the rule exists
    db = get_db()
    cursor = db.execute('SELECT * FROM ReglasVariantes WHERE id = ?', (regla_id,))
    regla = cursor.fetchone()
    
    if regla is None:
        return jsonify({'error': 'Rule not found'}), 404
    
    # Prepare the update
    updates = []
    params = []
    
    if 'patron_principal' in data and data['patron_principal'] is not None:
        if not validate_string(data['patron_principal'], min_length=1, max_length=100):
            return jsonify({'error': 'Invalid main pattern'}), 400
        updates.append('patron_principal = ?')
        params.append(data['patron_principal'])
    
    if 'patron_variante' in data and data['patron_variante'] is not None:
        if not validate_string(data['patron_variante'], min_length=1, max_length=100):
            return jsonify({'error': 'Invalid variant pattern'}), 400
        updates.append('patron_variante = ?')
        params.append(data['patron_variante'])
    
    if 'descripcion' in data:
        updates.append('descripcion = ?')
        params.append(data['descripcion'])
    
    if 'activo' in data and data['activo'] is not None:
        updates.append('activo = ?')
        params.append(1 if data['activo'] else 0)
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    try:
        params.append(regla_id)
        db.execute(
            f'UPDATE ReglasVariantes SET {", ".join(updates)} WHERE id = ?',
            params
        )
        db.commit()
        
        # Get the updated rule
        cursor = db.execute('SELECT * FROM ReglasVariantes WHERE id = ?', (regla_id,))
        updated_regla = cursor.fetchone()
        
        return jsonify({
            'id': updated_regla['id'],
            'patron_principal': updated_regla['patron_principal'],
            'patron_variante': updated_regla['patron_variante'],
            'descripcion': updated_regla['descripcion'],
            'activo': updated_regla['activo']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/reglas-variantes/<int:regla_id>', methods=['DELETE'])
def eliminar_regla_variante(regla_id):
    """Delete a specific variant rule by ID"""
    if not validate_id(regla_id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    cursor = db.execute('SELECT * FROM ReglasVariantes WHERE id = ?', (regla_id,))
    regla = cursor.fetchone()
    
    if regla is None:
        return jsonify({'error': 'Rule not found'}), 404
    
    try:
        db.execute('DELETE FROM ReglasVariantes WHERE id = ?', (regla_id,))
        db.commit()
        return jsonify({'message': 'Rule deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articulos_bp.route('/<int:articulo_id>/personalizar-composicion', methods=['POST'])
def personalizar_composicion(articulo_id):
    """Personaliza la composición de una variante copiando la del producto padre"""
    if not validate_id(articulo_id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    
    # Verificar que el artículo existe y es una variante
    cursor = db.execute('''
        SELECT a.*, p.nombre as articulo_padre_nombre 
        FROM ArticulosVendidos a
        LEFT JOIN ArticulosVendidos p ON a.articulo_padre_id = p.id
        WHERE a.id = ?
    ''', (articulo_id,))
    articulo = cursor.fetchone()
    
    if articulo is None:
        return jsonify({'error': 'Article not found'}), 404
    
    if not articulo['es_variante'] or not articulo['articulo_padre_id']:
        return jsonify({'error': 'Article is not a variant'}), 400
    
    try:
        # Obtener la composición del producto padre
        cursor = db.execute('''
            SELECT ingrediente_id, cantidad
            FROM ComposicionArticulo
            WHERE articulo_id = ?
        ''', (articulo['articulo_padre_id'],))
        composicion_padre = cursor.fetchall()
        
        # Copiar cada ingrediente a la variante
        for comp in composicion_padre:
            db.execute('''
                INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad)
                VALUES (?, ?, ?)
            ''', (articulo_id, comp['ingrediente_id'], comp['cantidad']))
        
        db.commit()
        return jsonify({'message': 'Composition personalized successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 