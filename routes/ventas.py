from flask import Blueprint, request, jsonify, current_app
import sqlite3
from database import get_db
from utils.csv_parser import parse_csv, validate_sales_data
from utils.error_handler import handle_error
import json

bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')

@bp.route('/importar', methods=['POST'])
def importar_ventas():
    """
    Import sales data from a CSV file.
    
    Expected request:
    - file: CSV file with sales data
    - column_mapping: JSON string with mapping of CSV columns to database columns (optional)
    
    Returns:
    - JSON response with import results
    """
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Check file extension
        if not file.filename.endswith('.csv'):
            return jsonify({"success": False, "error": "File must be a CSV"}), 400
        
        # Get column mapping if provided
        column_mapping = None
        if 'column_mapping' in request.form:
            try:
                column_mapping = json.loads(request.form['column_mapping'])
            except json.JSONDecodeError:
                return jsonify({"success": False, "error": "Invalid column mapping format"}), 400
        
        # Parse the CSV file
        file_content = file.read()
        parse_result = parse_csv(file_content, column_mapping)
        
        if not parse_result["success"]:
            return jsonify({"success": False, "error": parse_result["error"]}), 400
        
        # Validate the sales data
        sales_data = parse_result["data"]
        validation_result = validate_sales_data(sales_data)
        
        if not validation_result["success"]:
            return jsonify({"success": False, "errors": validation_result["errors"]}), 400
        
        # Process and save the data to the database
        db = get_db()
        cursor = db.cursor()
        
        # Initialize counters
        inserted_count = 0
        errors = []
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            for row in sales_data:
                try:
                    # Check if the article exists
                    articulo_nombre = row.get('articulo')
                    cursor.execute(
                        "SELECT id FROM ArticulosVendidos WHERE nombre = ?",
                        (articulo_nombre,)
                    )
                    articulo_result = cursor.fetchone()
                    
                    # If the article doesn't exist, we still save the sale but log a warning
                    articulo_id = articulo_result[0] if articulo_result else None
                    
                    # Prepare the insert statement
                    columns = ', '.join(row.keys())
                    placeholders = ', '.join(['?'] * len(row))
                    
                    cursor.execute(
                        f"INSERT INTO Ventas ({columns}) VALUES ({placeholders})",
                        tuple(row.values())
                    )
                    inserted_count += 1
                    
                    # If article exists, update inventory based on composition
                    if articulo_id:
                        # Get the composition of the article
                        cursor.execute(
                            """
                            SELECT ca.ingrediente_id, ca.cantidad, i.nombre
                            FROM ComposicionArticulo ca
                            JOIN Ingredientes i ON ca.ingrediente_id = i.id
                            WHERE ca.articulo_id = ?
                            """,
                            (articulo_id,)
                        )
                        composition = cursor.fetchall()
                        
                        # Calculate quantity sold
                        cantidad_vendida = int(row.get('articulos_vendidos', 0))
                        
                        # Update inventory for each ingredient
                        for comp_row in composition:
                            ingrediente_id = comp_row[0]
                            cantidad_por_unidad = comp_row[1]
                            ingrediente_nombre = comp_row[2]
                            
                            # Calculate total quantity to reduce
                            cantidad_reducir = cantidad_por_unidad * cantidad_vendida
                            
                            # Update the ingredient quantity
                            cursor.execute(
                                """
                                UPDATE Ingredientes
                                SET cantidad_actual = cantidad_actual - ?
                                WHERE id = ?
                                """,
                                (cantidad_reducir, ingrediente_id)
                            )
                
                except Exception as e:
                    errors.append({
                        "articulo": row.get('articulo', 'Unknown'),
                        "error": str(e)
                    })
            
            # Commit the transaction
            db.commit()
            
            # Return the results
            return jsonify({
                "success": True,
                "message": f"Successfully imported {inserted_count} sales records",
                "errors": errors if errors else None
            })
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        return handle_error(str(e))

@bp.route('', methods=['GET'])
def get_ventas():
    """
    Get sales data with optional filtering.
    
    Query parameters:
    - fecha_inicio: Start date (YYYY-MM-DD)
    - fecha_fin: End date (YYYY-MM-DD)
    - articulo: Filter by article name
    - categoria: Filter by category
    - limit: Maximum number of records to return
    - offset: Number of records to skip
    
    Returns:
    - JSON response with sales data
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Base query
        query = "SELECT * FROM Ventas WHERE 1=1"
        params = []
        
        # Apply filters
        if 'fecha_inicio' in request.args:
            query += " AND fecha >= ?"
            params.append(request.args['fecha_inicio'])
        
        if 'fecha_fin' in request.args:
            query += " AND fecha <= ?"
            params.append(request.args['fecha_fin'])
        
        if 'articulo' in request.args:
            query += " AND articulo LIKE ?"
            params.append(f"%{request.args['articulo']}%")
        
        if 'categoria' in request.args:
            query += " AND categoria LIKE ?"
            params.append(f"%{request.args['categoria']}%")
        
        # Add sorting
        query += " ORDER BY fecha DESC, hora DESC"
        
        # Add pagination
        if 'limit' in request.args:
            query += " LIMIT ?"
            params.append(int(request.args['limit']))
        
        if 'offset' in request.args:
            query += " OFFSET ?"
            params.append(int(request.args['offset']))
        
        # Execute the query
        cursor.execute(query, params)
        ventas = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for venta in ventas:
            result.append({
                'id': venta['id'],
                'fecha': venta['fecha'],
                'hora': venta['hora'],
                'ticket': venta['ticket'],
                'empleado': venta['empleado'],
                'mesa': venta['mesa'],
                'comensales': venta['comensales'],
                'articulo': venta['articulo'],
                'categoria': venta['categoria'],
                'subcategoria': venta['subcategoria'],
                'precio_unitario': venta['precio_unitario'],
                'articulos_vendidos': venta['articulos_vendidos'],
                'iva': venta['iva'],
                'propina': venta['propina'],
                'total': venta['total'],
                'costo_estimado': venta['costo_estimado'],
                'ganancia_estimada': venta['ganancia_estimada'],
                'porcentaje_ganancia': venta['porcentaje_ganancia']
            })
        
        # Get total count for pagination info
        cursor.execute("SELECT COUNT(*) as count FROM Ventas")
        total = cursor.fetchone()['count']
        
        return jsonify({
            "success": True,
            "data": result,
            "total": total
        })
        
    except Exception as e:
        return handle_error(str(e)) 