from flask import Blueprint, request, jsonify, current_app
import sqlite3
from datetime import datetime
from database import get_db
from utils.error_handler import handle_error
from utils.validators import validate_required_fields, validate_numeric_value

bp = Blueprint('recepciones', __name__, url_prefix='/api/recepciones')

@bp.route('', methods=['GET'])
def get_recepciones():
    """
    Get kitchen receptions with optional filtering.
    
    Query parameters:
    - fecha_inicio: Start date (YYYY-MM-DD)
    - fecha_fin: End date (YYYY-MM-DD)
    - ingrediente_id: Filter by ingredient ID
    - limit: Maximum number of records to return
    - offset: Number of records to skip
    
    Returns:
    - JSON response with reception data
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Base query with join to get ingredient name
        query = """
            SELECT r.*, i.nombre as ingrediente_nombre, i.unidad_medida
            FROM RecepcionesCocina r
            JOIN Ingredientes i ON r.ingrediente_id = i.id
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if 'fecha_inicio' in request.args:
            query += " AND r.fecha_recepcion >= ?"
            params.append(request.args['fecha_inicio'])
        
        if 'fecha_fin' in request.args:
            query += " AND r.fecha_recepcion <= ?"
            params.append(request.args['fecha_fin'])
        
        if 'ingrediente_id' in request.args:
            query += " AND r.ingrediente_id = ?"
            params.append(int(request.args['ingrediente_id']))
        
        # Add sorting
        query += " ORDER BY r.fecha_recepcion DESC, r.hora_recepcion DESC"
        
        # Add pagination
        if 'limit' in request.args:
            query += " LIMIT ?"
            params.append(int(request.args['limit']))
        
        if 'offset' in request.args:
            query += " OFFSET ?"
            params.append(int(request.args['offset']))
        
        # Execute the query
        cursor.execute(query, params)
        recepciones = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for recepcion in recepciones:
            result.append({
                'id': recepcion['id'],
                'ingrediente_id': recepcion['ingrediente_id'],
                'ingrediente_nombre': recepcion['ingrediente_nombre'],
                'unidad_medida': recepcion['unidad_medida'],
                'cantidad_recibida': recepcion['cantidad_recibida'],
                'fecha_recepcion': recepcion['fecha_recepcion'],
                'hora_recepcion': recepcion['hora_recepcion'],
                'notas': recepcion['notas']
            })
        
        # Get total count for pagination info
        cursor.execute("SELECT COUNT(*) as count FROM RecepcionesCocina")
        total = cursor.fetchone()['count']
        
        return jsonify({
            "success": True,
            "data": result,
            "total": total
        })
        
    except Exception as e:
        return handle_error(str(e))

@bp.route('', methods=['POST'])
def create_recepcion():
    """
    Create a new kitchen reception and update ingredient inventory.
    
    Expected request body:
    {
        "ingrediente_id": integer,
        "cantidad_recibida": float,
        "notas": string (optional)
    }
    
    Returns:
    - JSON response with the created reception
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ingrediente_id', 'cantidad_recibida']
        validation_result = validate_required_fields(data, required_fields)
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['error']}), 400
        
        # Validate numeric values
        numeric_fields = [('cantidad_recibida', 'float', 'Cantidad recibida debe ser un número')]
        for field in numeric_fields:
            validation_result = validate_numeric_value(data, field[0], field[1])
            if not validation_result['valid']:
                return jsonify({"success": False, "error": validation_result['error']}), 400
        
        # Validate that the ingredient exists
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            "SELECT id, nombre FROM Ingredientes WHERE id = ?",
            (data['ingrediente_id'],)
        )
        ingrediente = cursor.fetchone()
        
        if not ingrediente:
            return jsonify({
                "success": False,
                "error": f"No existe el ingrediente con ID {data['ingrediente_id']}"
            }), 404
        
        # Get current date and time
        now = datetime.now()
        fecha_recepcion = now.strftime('%Y-%m-%d')
        hora_recepcion = now.strftime('%H:%M:%S')
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            # Insert reception record
            cursor.execute(
                """
                INSERT INTO RecepcionesCocina 
                (ingrediente_id, cantidad_recibida, fecha_recepcion, hora_recepcion, notas)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data['ingrediente_id'],
                    data['cantidad_recibida'],
                    fecha_recepcion,
                    hora_recepcion,
                    data.get('notas', '')
                )
            )
            
            # Get the ID of the inserted record
            recepcion_id = cursor.lastrowid
            
            # Update ingredient inventory
            cursor.execute(
                """
                UPDATE Ingredientes
                SET cantidad_actual = cantidad_actual + ?
                WHERE id = ?
                """,
                (data['cantidad_recibida'], data['ingrediente_id'])
            )
            
            # Commit the transaction
            db.commit()
            
            # Return the created reception
            return jsonify({
                "success": True,
                "message": f"Recepción registrada correctamente para {ingrediente['nombre']}",
                "data": {
                    "id": recepcion_id,
                    "ingrediente_id": data['ingrediente_id'],
                    "ingrediente_nombre": ingrediente['nombre'],
                    "cantidad_recibida": data['cantidad_recibida'],
                    "fecha_recepcion": fecha_recepcion,
                    "hora_recepcion": hora_recepcion,
                    "notas": data.get('notas', '')
                }
            })
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        return handle_error(str(e))

@bp.route('/<int:id>', methods=['GET'])
def get_recepcion(id):
    """
    Get a specific kitchen reception by ID.
    
    Path parameters:
    - id: Reception ID
    
    Returns:
    - JSON response with reception data
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Query with join to get ingredient name
        cursor.execute(
            """
            SELECT r.*, i.nombre as ingrediente_nombre, i.unidad_medida
            FROM RecepcionesCocina r
            JOIN Ingredientes i ON r.ingrediente_id = i.id
            WHERE r.id = ?
            """,
            (id,)
        )
        recepcion = cursor.fetchone()
        
        if not recepcion:
            return jsonify({
                "success": False,
                "error": f"No existe la recepción con ID {id}"
            }), 404
        
        # Return the reception data
        return jsonify({
            "success": True,
            "data": {
                'id': recepcion['id'],
                'ingrediente_id': recepcion['ingrediente_id'],
                'ingrediente_nombre': recepcion['ingrediente_nombre'],
                'unidad_medida': recepcion['unidad_medida'],
                'cantidad_recibida': recepcion['cantidad_recibida'],
                'fecha_recepcion': recepcion['fecha_recepcion'],
                'hora_recepcion': recepcion['hora_recepcion'],
                'notas': recepcion['notas']
            }
        })
        
    except Exception as e:
        return handle_error(str(e))

@bp.route('/<int:id>', methods=['DELETE'])
def delete_recepcion(id):
    """
    Delete a specific kitchen reception by ID and adjust inventory accordingly.
    
    Path parameters:
    - id: Reception ID
    
    Returns:
    - JSON response with deletion result
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            # First, get the reception details to know what to remove from inventory
            cursor.execute(
                """
                SELECT r.ingrediente_id, r.cantidad_recibida, i.nombre as ingrediente_nombre
                FROM RecepcionesCocina r
                JOIN Ingredientes i ON r.ingrediente_id = i.id
                WHERE r.id = ?
                """,
                (id,)
            )
            recepcion = cursor.fetchone()
            
            if not recepcion:
                db.rollback()
                return jsonify({
                    "success": False,
                    "error": f"No existe la recepción con ID {id}"
                }), 404
            
            # Check if removing this reception would result in negative inventory
            cursor.execute(
                """
                SELECT cantidad_actual 
                FROM Ingredientes 
                WHERE id = ?
                """,
                (recepcion['ingrediente_id'],)
            )
            
            ingrediente = cursor.fetchone()
            
            if not ingrediente:
                db.rollback()
                return jsonify({
                    "success": False,
                    "error": f"No existe el ingrediente con ID {recepcion['ingrediente_id']}"
                }), 404
            
            nueva_cantidad = ingrediente['cantidad_actual'] - recepcion['cantidad_recibida']
            
            if nueva_cantidad < 0:
                db.rollback()
                return jsonify({
                    "success": False,
                    "error": f"No es posible eliminar esta recepción porque resultaría en inventario negativo para {recepcion['ingrediente_nombre']}. Cantidad actual: {ingrediente['cantidad_actual']}, Cantidad a eliminar: {recepcion['cantidad_recibida']}"
                }), 400
            
            # Update ingredient inventory (subtract the received quantity)
            cursor.execute(
                """
                UPDATE Ingredientes
                SET cantidad_actual = cantidad_actual - ?
                WHERE id = ?
                """,
                (recepcion['cantidad_recibida'], recepcion['ingrediente_id'])
            )
            
            # Delete the reception record
            cursor.execute("DELETE FROM RecepcionesCocina WHERE id = ?", (id,))
            
            # Commit the transaction
            db.commit()
            
            # Return success response
            return jsonify({
                "success": True,
                "message": f"Recepción ID {id} eliminada correctamente y inventario actualizado"
            })
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            current_app.logger.error(f"Error al eliminar recepción: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error general al eliminar recepción: {str(e)}")
        return handle_error(str(e)) 