from flask import Blueprint, jsonify, request, g, render_template
from database import get_db
from utils.validators import validate_request_json, validate_id, validate_numeric, validate_string

# Create a blueprint for ingredient API routes
ingredientes_bp = Blueprint('ingredientes', __name__, url_prefix='/api/ingredientes')

# Create a blueprint for ingredient web routes
ingredientes_web_bp = Blueprint('ingredientes_web', __name__, url_prefix='/ingredientes')

@ingredientes_web_bp.route('/', methods=['GET'])
def index():
    """Render the ingredients list page"""
    db = get_db()
    cursor = db.execute('SELECT * FROM Ingredientes')
    ingredientes = []
    for row in cursor.fetchall():
        ingrediente = dict(
            id=row['id'],
            nombre=row['nombre'],
            unidad_medida=row['unidad_medida'],
            precio_compra=row['precio_compra'],
            cantidad_actual=row['cantidad_actual'],
            stock_minimo=row['stock_minimo']
        )
        # Safely handle categoria which might not exist in older records
        try:
            ingrediente['categoria'] = row['categoria']
        except (IndexError, KeyError):
            ingrediente['categoria'] = None
        
        ingredientes.append(ingrediente)
    
    return render_template('ingredientes/lista.html', ingredientes=ingredientes)

@ingredientes_web_bp.route('/nuevo', methods=['GET'])
def nuevo():
    """Render the new ingredient form"""
    return render_template('ingredientes/formulario.html')

@ingredientes_web_bp.route('/editar/<int:id>', methods=['GET'])
def editar(id):
    """Render the edit ingredient form"""
    db = get_db()
    cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (id,))
    row = cursor.fetchone()
    if row is None:
        # Handle not found
        return render_template('error.html', message='Ingrediente no encontrado'), 404
    
    # Convert row to dictionary and safely handle categoria
    ingrediente = dict(
        id=row['id'],
        nombre=row['nombre'],
        unidad_medida=row['unidad_medida'],
        precio_compra=row['precio_compra'],
        cantidad_actual=row['cantidad_actual'],
        stock_minimo=row['stock_minimo']
    )
    
    # Safely handle categoria which might not exist in older records
    try:
        ingrediente['categoria'] = row['categoria']
    except (IndexError, KeyError):
        ingrediente['categoria'] = None
    
    return render_template('ingredientes/formulario.html', ingrediente=ingrediente)

@ingredientes_bp.route('', methods=['GET'])
def get_ingredientes():
    """Get all ingredients"""
    db = get_db()
    cursor = db.execute('SELECT * FROM Ingredientes')
    ingredientes = []
    for row in cursor.fetchall():
        ingrediente = dict(
            id=row['id'],
            nombre=row['nombre'],
            unidad_medida=row['unidad_medida'],
            precio_compra=row['precio_compra'],
            cantidad_actual=row['cantidad_actual'],
            stock_minimo=row['stock_minimo']
        )
        # Safely handle categoria which might not exist in older records
        try:
            ingrediente['categoria'] = row['categoria']
        except (IndexError, KeyError):
            ingrediente['categoria'] = None
        
        ingredientes.append(ingrediente)
    
    return jsonify(ingredientes)

@ingredientes_bp.route('', methods=['POST'])
def create_ingrediente():
    """Create a new ingredient"""
    try:
        # Validate request
        is_valid, data, error_response = validate_request_json(['nombre', 'unidad_medida'])
        if not is_valid:
            return error_response
        
        # Validate fields
        if not validate_string(data['nombre'], min_length=1, max_length=100):
            return jsonify({'error': 'Invalid name'}), 400
        
        if not validate_string(data['unidad_medida'], min_length=1, max_length=20):
            return jsonify({'error': 'Invalid unit of measure'}), 400
        
        # Validate optional fields if provided
        if 'precio_compra' in data and data['precio_compra'] is not None:
            if not validate_numeric(data['precio_compra'], min_value=0):
                return jsonify({'error': 'Invalid purchase price'}), 400
        
        if 'cantidad_actual' in data and data['cantidad_actual'] is not None:
            if not validate_numeric(data['cantidad_actual'], allow_negative=False):
                return jsonify({'error': 'Invalid current quantity'}), 400
        
        if 'stock_minimo' in data and data['stock_minimo'] is not None:
            if not validate_numeric(data['stock_minimo'], min_value=0):
                return jsonify({'error': 'Invalid minimum stock'}), 400
                
        if 'categoria' in data and data['categoria'] is not None:
            if not validate_string(data['categoria'], min_length=1, max_length=50):
                return jsonify({'error': 'Invalid category'}), 400
        
        # Prepare the data
        precio_compra = data.get('precio_compra')
        cantidad_actual = data.get('cantidad_actual', 0)
        stock_minimo = data.get('stock_minimo')
        categoria = data.get('categoria')
        
        db = get_db()
        try:
            # First, try to insert only the required fields and the fields that definitely exist
            cursor = db.execute(
                'INSERT INTO Ingredientes (nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo) '
                'VALUES (?, ?, ?, ?, ?)',
                (data['nombre'], data['unidad_medida'], precio_compra, cantidad_actual, stock_minimo)
            )
            
            # Get the created ingredient ID
            ingrediente_id = cursor.lastrowid
            
            # Then try to update the categoria field if it was provided
            if categoria is not None:
                try:
                    db.execute(
                        'UPDATE Ingredientes SET categoria = ? WHERE id = ?',
                        (categoria, ingrediente_id)
                    )
                except Exception as e:
                    # If updating the categoria field fails, log but continue
                    print(f"Warning: Failed to update categoria field: {e}")
                    
            db.commit()
            
            # Get the created ingredient
            cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (ingrediente_id,))
            row = cursor.fetchone()
            
            # Convert row to dictionary
            ingrediente = {
                'id': row['id'],
                'nombre': row['nombre'],
                'unidad_medida': row['unidad_medida'],
                'precio_compra': row['precio_compra'],
                'cantidad_actual': row['cantidad_actual'],
                'stock_minimo': row['stock_minimo']
            }
            
            # Safely try to add the categoria field
            try:
                ingrediente['categoria'] = row['categoria']
            except (IndexError, KeyError):
                ingrediente['categoria'] = None
            
            return jsonify(ingrediente), 201
        except db.IntegrityError:
            db.rollback()
            return jsonify({'error': 'Ingredient name already exists'}), 409
        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        # Catch any unexpected exceptions that might occur
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

@ingredientes_bp.route('/<int:id>', methods=['GET'])
def get_ingrediente(id):
    """Get a specific ingredient by ID"""
    if not validate_id(id):
        return jsonify({'error': 'Invalid ID format'}), 400
    
    db = get_db()
    cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (id,))
    row = cursor.fetchone()
    
    if row is None:
        return jsonify({'error': 'Ingredient not found'}), 404
    
    # Convert row to dictionary and safely handle categoria
    ingrediente = {
        'id': row['id'],
        'nombre': row['nombre'],
        'unidad_medida': row['unidad_medida'],
        'precio_compra': row['precio_compra'],
        'cantidad_actual': row['cantidad_actual'],
        'stock_minimo': row['stock_minimo']
    }
    
    # Safely handle categoria which might not exist in older records
    try:
        ingrediente['categoria'] = row['categoria']
    except (IndexError, KeyError):
        ingrediente['categoria'] = None
    
    return jsonify(ingrediente)

@ingredientes_bp.route('/<int:id>', methods=['PUT'])
def update_ingrediente(id):
    """Update a specific ingredient by ID"""
    try:
        if not validate_id(id):
            return jsonify({'error': 'Invalid ID format'}), 400
        
        # Validate request
        is_valid, data, error_response = validate_request_json()
        if not is_valid:
            return error_response
        
        # Check if the ingredient exists
        db = get_db()
        cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (id,))
        row = cursor.fetchone()
        
        if row is None:
            return jsonify({'error': 'Ingredient not found'}), 404
        
        # Validate fields if provided
        if 'nombre' in data and data['nombre'] is not None:
            if not validate_string(data['nombre'], min_length=1, max_length=100):
                return jsonify({'error': 'Invalid name'}), 400
        
        if 'unidad_medida' in data and data['unidad_medida'] is not None:
            if not validate_string(data['unidad_medida'], min_length=1, max_length=20):
                return jsonify({'error': 'Invalid unit of measure'}), 400
        
        if 'precio_compra' in data and data['precio_compra'] is not None:
            if not validate_numeric(data['precio_compra'], min_value=0):
                return jsonify({'error': 'Invalid purchase price'}), 400
        
        if 'cantidad_actual' in data and data['cantidad_actual'] is not None:
            if not validate_numeric(data['cantidad_actual'], allow_negative=False):
                return jsonify({'error': 'Invalid current quantity'}), 400
        
        if 'stock_minimo' in data and data['stock_minimo'] is not None:
            if not validate_numeric(data['stock_minimo'], min_value=0):
                return jsonify({'error': 'Invalid minimum stock'}), 400
                
        if 'categoria' in data and data['categoria'] is not None:
            if not validate_string(data['categoria'], min_length=1, max_length=50):
                return jsonify({'error': 'Invalid category'}), 400
        
        # Prepare the update for standard fields
        updates = []
        params = []
        
        if 'nombre' in data and data['nombre'] is not None:
            updates.append('nombre = ?')
            params.append(data['nombre'])
        
        if 'unidad_medida' in data and data['unidad_medida'] is not None:
            updates.append('unidad_medida = ?')
            params.append(data['unidad_medida'])
        
        if 'precio_compra' in data:
            updates.append('precio_compra = ?')
            params.append(data['precio_compra'])
        
        if 'cantidad_actual' in data and data['cantidad_actual'] is not None:
            updates.append('cantidad_actual = ?')
            params.append(data['cantidad_actual'])
        
        if 'stock_minimo' in data:
            updates.append('stock_minimo = ?')
            params.append(data['stock_minimo'])
        
        # Execute the update with standard fields
        try:
            if updates:
                params.append(id)
                db.execute(
                    f'UPDATE Ingredientes SET {", ".join(updates)} WHERE id = ?',
                    params
                )
            
            # Separately handle the categoria field if provided
            if 'categoria' in data:
                try:
                    db.execute(
                        'UPDATE Ingredientes SET categoria = ? WHERE id = ?',
                        (data['categoria'], id)
                    )
                except Exception as e:
                    # If updating the categoria field fails, log but continue
                    print(f"Warning: Failed to update categoria field: {e}")
            
            db.commit()
            
            # Get the updated ingredient
            cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (id,))
            row = cursor.fetchone()
            
            # Convert row to dictionary
            updated_ingrediente = {
                'id': row['id'],
                'nombre': row['nombre'],
                'unidad_medida': row['unidad_medida'],
                'precio_compra': row['precio_compra'],
                'cantidad_actual': row['cantidad_actual'],
                'stock_minimo': row['stock_minimo']
            }
            
            # Safely try to add the categoria field
            try:
                updated_ingrediente['categoria'] = row['categoria']
            except (IndexError, KeyError):
                updated_ingrediente['categoria'] = None
            
            return jsonify(updated_ingrediente)
        except db.IntegrityError:
            db.rollback()
            return jsonify({'error': 'Ingredient name already exists'}), 409
        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        # Catch any unexpected exceptions that might occur
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

@ingredientes_bp.route('/<int:id>', methods=['DELETE'])
def delete_ingrediente(id):
    """Delete a specific ingredient by ID"""
    try:
        if not validate_id(id):
            return jsonify({'error': 'Invalid ID format'}), 400
        
        db = get_db()
        
        # Check if the ingredient exists
        cursor = db.execute('SELECT * FROM Ingredientes WHERE id = ?', (id,))
        ingrediente = cursor.fetchone()
        
        if ingrediente is None:
            return jsonify({'error': 'Ingredient not found'}), 404
        
        # Check if the ingredient is being used in any product composition
        cursor = db.execute('SELECT COUNT(*) as count FROM ComposicionArticulo WHERE ingrediente_id = ?', (id,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            return jsonify({
                'error': 'Cannot delete ingredient because it is used in product compositions',
                'used_count': result['count']
            }), 409
        
        try:
            db.execute('DELETE FROM Ingredientes WHERE id = ?', (id,))
            db.commit()
            return jsonify({'message': 'Ingredient deleted successfully'}), 200
        except Exception as e:
            db.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        # Catch any unexpected exceptions that might occur
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500 