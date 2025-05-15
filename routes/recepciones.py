from flask import Blueprint, request, jsonify, current_app
import sqlite3
from datetime import datetime
from database import get_db, get_db_cursor, backup_db, verify_db_integrity
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
        
        # Base query with join to get ingredient details
        query = """
            SELECT 
                r.id, r.fecha_recepcion, r.hora_recepcion, r.notas,
                rd.ingrediente_id, rd.cantidad_recibida,
                i.nombre as ingrediente_nombre, i.unidad_medida
            FROM RecepcionesCocina r
            JOIN RecepcionesDetalles rd ON r.id = rd.recepcion_id
            JOIN Ingredientes i ON rd.ingrediente_id = i.id
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
            query += " AND rd.ingrediente_id = ?"
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
        recepciones_raw = cursor.fetchall()
        
        # Group by reception
        recepciones_dict = {}
        for row in recepciones_raw:
            recepcion_id = row['id']
            if recepcion_id not in recepciones_dict:
                recepciones_dict[recepcion_id] = {
                    'id': recepcion_id,
                    'fecha_recepcion': row['fecha_recepcion'],
                    'hora_recepcion': row['hora_recepcion'],
                    'notas': row['notas'],
                    'ingredientes': []
                }
            
            recepciones_dict[recepcion_id]['ingredientes'].append({
                'ingrediente_id': row['ingrediente_id'],
                'ingrediente_nombre': row['ingrediente_nombre'],
                'unidad_medida': row['unidad_medida'],
                'cantidad_recibida': row['cantidad_recibida']
            })
        
        # Convert to list
        result = list(recepciones_dict.values())
        
        # Get total count for pagination info
        cursor.execute("SELECT COUNT(DISTINCT r.id) as count FROM RecepcionesCocina r")
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
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if 'ingredientes' not in data or not data['ingredientes']:
            return jsonify({
                "success": False,
                "error": "Se requiere al menos un ingrediente"
            }), 400
        
        # Validate each ingredient entry
        for ingrediente in data['ingredientes']:
            if not isinstance(ingrediente, dict) or \
               'ingrediente_id' not in ingrediente or \
               'cantidad_recibida' not in ingrediente:
                return jsonify({
                    "success": False,
                    "error": "Cada ingrediente debe tener ingrediente_id y cantidad_recibida"
                }), 400
            
            # Validate numeric values
            validation_result = validate_numeric_value(
                ingrediente, 'cantidad_recibida', 'float'
            )
            if not validation_result['valid']:
                return jsonify({
                    "success": False,
                    "error": validation_result['error']
                }), 400

        # Verificar integridad de la base de datos antes de proceder
        if not verify_db_integrity():
            current_app.logger.error("Se detectó un problema de integridad en la base de datos")
            return jsonify({
                "success": False,
                "error": "Error de integridad en la base de datos"
            }), 500

        # Crear backup antes de la operación
        try:
            backup_path = backup_db()
            current_app.logger.info(f"Backup creado en: {backup_path}")
        except Exception as e:
            current_app.logger.error(f"Error al crear backup: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Error al crear backup de seguridad"
            }), 500
        
        with get_db_cursor() as cursor:
            # Validate that all ingredients exist
            for ingrediente in data['ingredientes']:
                cursor.execute(
                    "SELECT id, nombre FROM Ingredientes WHERE id = ?",
                    (ingrediente['ingrediente_id'],)
                )
                if not cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "error": f"No existe el ingrediente con ID {ingrediente['ingrediente_id']}"
                    }), 404
            
            # Get current date and time
            now = datetime.now()
            fecha_recepcion = now.strftime('%Y-%m-%d')
            hora_recepcion = now.strftime('%H:%M:%S')
            
            # Insert reception record
            cursor.execute(
                """
                INSERT INTO RecepcionesCocina 
                (fecha_recepcion, hora_recepcion, notas)
                VALUES (?, ?, ?)
                """,
                (fecha_recepcion, hora_recepcion, data.get('notas', ''))
            )
            
            # Log the reception creation
            current_app.logger.info(
                f"Nueva recepción creada - ID: {cursor.lastrowid}, "
                f"Fecha: {fecha_recepcion}, Hora: {hora_recepcion}"
            )
            
            # Get the ID of the inserted reception
            recepcion_id = cursor.lastrowid
            
            # Insert reception details and update inventory for each ingredient
            ingredientes_info = []
            for ingrediente in data['ingredientes']:
                try:
                    # Get ingredient info
                    cursor.execute(
                        "SELECT nombre, unidad_medida FROM Ingredientes WHERE id = ?",
                        (ingrediente['ingrediente_id'],)
                    )
                    ing_info = cursor.fetchone()
                    
                    # Insert reception detail
                    cursor.execute(
                        """
                        INSERT INTO RecepcionesDetalles 
                        (recepcion_id, ingrediente_id, cantidad_recibida)
                        VALUES (?, ?, ?)
                        """,
                        (
                            recepcion_id,
                            ingrediente['ingrediente_id'],
                            ingrediente['cantidad_recibida']
                        )
                    )
                    
                    # Update ingredient inventory
                    cursor.execute(
                        """
                        UPDATE Ingredientes
                        SET cantidad_actual = cantidad_actual + ?
                        WHERE id = ?
                        """,
                        (ingrediente['cantidad_recibida'], ingrediente['ingrediente_id'])
                    )
                    
                    # Log the ingredient update
                    current_app.logger.info(
                        f"Actualizado ingrediente {ing_info['nombre']} - "
                        f"Cantidad recibida: {ingrediente['cantidad_recibida']}"
                    )
                    
                    # Store ingredient info for response
                    ingredientes_info.append({
                        'ingrediente_id': ingrediente['ingrediente_id'],
                        'ingrediente_nombre': ing_info['nombre'],
                        'unidad_medida': ing_info['unidad_medida'],
                        'cantidad_recibida': ingrediente['cantidad_recibida']
                    })
                    
                except Exception as e:
                    current_app.logger.error(
                        f"Error al procesar ingrediente {ingrediente['ingrediente_id']}: {str(e)}"
                    )
                    raise
            
            # Verificar integridad después de la operación
            if not verify_db_integrity():
                current_app.logger.error("Se detectó un problema de integridad después de la operación")
                raise Exception("Error de integridad después de la operación")
            
            # Return the created reception
            return jsonify({
                "success": True,
                "message": "Recepción registrada correctamente",
                "data": {
                    "id": recepcion_id,
                    "fecha_recepcion": fecha_recepcion,
                    "hora_recepcion": hora_recepcion,
                    "notas": data.get('notas', ''),
                    "ingredientes": ingredientes_info
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Error al crear recepción: {str(e)}")
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
        
        # Query with joins to get all details
        cursor.execute(
            """
            SELECT 
                r.id, r.fecha_recepcion, r.hora_recepcion, r.notas,
                rd.ingrediente_id, rd.cantidad_recibida,
                i.nombre as ingrediente_nombre, i.unidad_medida
            FROM RecepcionesCocina r
            JOIN RecepcionesDetalles rd ON r.id = rd.recepcion_id
            JOIN Ingredientes i ON rd.ingrediente_id = i.id
            WHERE r.id = ?
            """,
            (id,)
        )
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({
                "success": False,
                "error": f"No existe la recepción con ID {id}"
            }), 404
        
        # Build the response
        result = {
            'id': rows[0]['id'],
            'fecha_recepcion': rows[0]['fecha_recepcion'],
            'hora_recepcion': rows[0]['hora_recepcion'],
            'notas': rows[0]['notas'],
            'ingredientes': []
        }
        
        for row in rows:
            result['ingredientes'].append({
                'ingrediente_id': row['ingrediente_id'],
                'ingrediente_nombre': row['ingrediente_nombre'],
                'unidad_medida': row['unidad_medida'],
                'cantidad_recibida': row['cantidad_recibida']
            })
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        return handle_error(str(e))

@bp.route('/<int:id>', methods=['DELETE'])
def delete_recepcion(id):
    """
    Delete a specific kitchen reception and adjust inventory accordingly.
    If removing ingredients would result in negative inventory, set to 0 instead.
    
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
            # First, get all the reception details
            cursor.execute(
                """
                SELECT rd.ingrediente_id, rd.cantidad_recibida, i.nombre as ingrediente_nombre
                FROM RecepcionesDetalles rd
                JOIN Ingredientes i ON rd.ingrediente_id = i.id
                WHERE rd.recepcion_id = ?
                """,
                (id,)
            )
            detalles = cursor.fetchall()
            
            if not detalles:
                db.rollback()
                return jsonify({
                    "success": False,
                    "error": f"No existe la recepción con ID {id}"
                }), 404
            
            # Update inventory for each ingredient
            for detalle in detalles:
                cursor.execute(
                    """
                    SELECT cantidad_actual 
                    FROM Ingredientes 
                    WHERE id = ?
                    """,
                    (detalle['ingrediente_id'],)
                )
                
                ingrediente = cursor.fetchone()
                
                if not ingrediente:
                    db.rollback()
                    return jsonify({
                        "success": False,
                        "error": f"No existe el ingrediente con ID {detalle['ingrediente_id']}"
                    }), 404
                
                # Calculate new quantity, but don't let it go below 0
                nueva_cantidad = max(0, ingrediente['cantidad_actual'] - detalle['cantidad_recibida'])
                
                cursor.execute(
                    """
                    UPDATE Ingredientes
                    SET cantidad_actual = ?
                    WHERE id = ?
                    """,
                    (nueva_cantidad, detalle['ingrediente_id'])
                )
            
            # Delete the reception (this will cascade delete the details due to ON DELETE CASCADE)
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