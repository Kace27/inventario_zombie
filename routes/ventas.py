from flask import Blueprint, request, jsonify, current_app
import sqlite3
from database import get_db
from utils.csv_parser import parse_csv, validate_sales_data, parse_receipts_data, format_date
from utils.error_handler import handle_error
import json
import datetime

bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')

@bp.route('/importar', methods=['POST'])
def importar_ventas():
    """
    Import sales data from a CSV file.
    
    Expected request:
    - file: CSV file with sales data in a fixed format
    
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
        
        # Define the fixed column mapping based on the known CSV format
        # The format: Artículo,REF,Categoria,Articulos vendidos,Ventas brutas,Articulos reembolsados,Reembolsos,Descuentos,Ventas netas,Costo de los bienes,Beneficio bruto,Margen,Impuestos
        column_mapping = {
            'articulo': 0,           # Artículo
            'ref': 1,                # REF
            'categoria': 2,          # Categoria
            'articulos_vendidos': 3, # Articulos vendidos
            'ventas_brutas': 4,      # Ventas brutas
            'articulos_reembolsados': 5,  # Articulos reembolsados
            'reembolsos': 6,         # Reembolsos
            'descuentos': 7,         # Descuentos
            'ventas_netas': 8,       # Ventas netas
            'costo_bienes': 9,       # Costo de los bienes
            'beneficio_bruto': 10,   # Beneficio bruto
            'margen': 11,            # Margen
            'impuestos': 12          # Impuestos
        }
        
        # Parse the CSV file
        file_content = file.read()
        parse_result = parse_csv(file_content, column_mapping)
        
        if not parse_result["success"]:
            return jsonify({"success": False, "error": parse_result["error"]}), 400
        
        # Get the raw data
        raw_data = parse_result["data"]
        
        # Process the data to match the database schema
        sales_data = []
        current_date = datetime.datetime.now()
        
        for row in raw_data:
            # Skip header row if accidentally included
            if row.get('articulo') == 'Artículo':
                continue
                
            # Add current date and time to each row
            row['fecha'] = current_date.strftime('%Y-%m-%d')
            row['hora'] = current_date.strftime('%H:%M:%S')
                
            # Clean data and prepare for database
            processed_row = {
                'fecha': current_date.strftime('%Y-%m-%d'),
                'hora': current_date.strftime('%H:%M:%S'),
                'articulo': row.get('articulo', ''),
                'categoria': row.get('categoria', ''),
                'articulos_vendidos': row.get('articulos_vendidos', '0').replace('.', ''),  # Remove thousands separator
                'precio_unitario': float(row.get('ventas_brutas', '0').replace(',', '.')) / float(row.get('articulos_vendidos', '1').replace('.', '')) if float(row.get('articulos_vendidos', '0').replace('.', '')) > 0 else 0,
                'total': row.get('ventas_netas', '0').replace(',', '.'),
                'costo_estimado': row.get('costo_bienes', '0').replace(',', '.'),
                'ganancia_estimada': row.get('beneficio_bruto', '0').replace(',', '.'),
                'porcentaje_ganancia': row.get('margen', '0%').replace('%', ''),
                'iva': row.get('impuestos', '0').replace(',', '.')
            }
            
            sales_data.append(processed_row)
        
        # Custom validation for the processed data
        if not sales_data:
            return jsonify({"success": False, "error": "No valid sales data found in the CSV"}), 400
        
        # Skip the standard validation since we're adding fecha and hora ourselves
        # and directly process the data
        
        # Process and save the data to the database
        db = get_db()
        cursor = db.cursor()
        
        # Initialize counters
        inserted_count = 0
        created_articles_count = 0
        errors = []
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            for row in sales_data:
                try:
                    # Check if the article exists
                    articulo_nombre = row.get('articulo')
                    articulo_categoria = row.get('categoria')
                    precio_unitario = row.get('precio_unitario', 0)
                    
                    cursor.execute(
                        "SELECT id FROM ArticulosVendidos WHERE nombre = ?",
                        (articulo_nombre,)
                    )
                    articulo_result = cursor.fetchone()
                    
                    # If the article doesn't exist, create it
                    if not articulo_result:
                        try:
                            # Insert new article into ArticulosVendidos
                            cursor.execute(
                                """
                                INSERT INTO ArticulosVendidos (nombre, categoria, precio_venta)
                                VALUES (?, ?, ?)
                                """,
                                (articulo_nombre, articulo_categoria, precio_unitario)
                            )
                            articulo_id = cursor.lastrowid
                            created_articles_count += 1
                            
                            # Log article creation
                            current_app.logger.info(f"Created new article: {articulo_nombre} (ID: {articulo_id})")
                            
                        except sqlite3.Error as e:
                            current_app.logger.error(f"Error creating article {articulo_nombre}: {str(e)}")
                            errors.append({
                                "articulo": articulo_nombre,
                                "error": f"Error creating article: {str(e)}"
                            })
                            articulo_id = None
                    else:
                        articulo_id = articulo_result[0]
                    
                    # Prepare the insert statement for the sale
                    columns = ', '.join(row.keys())
                    placeholders = ', '.join(['?'] * len(row))
                    
                    cursor.execute(
                        f"INSERT INTO Ventas ({columns}) VALUES ({placeholders})",
                        tuple(row.values())
                    )
                    inserted_count += 1
                    
                    # If article exists and has composition, update inventory based on composition
                    if articulo_id:
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
                        
                        # If composition exists, update inventory
                        if composition:
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
            success_message = f"Successfully imported {inserted_count} sales records"
            if created_articles_count > 0:
                success_message += f" and created {created_articles_count} new articles"
            
            # Spanish messages for the user interface
            spanish_message = f"Se importaron {inserted_count} registros de ventas"
            if created_articles_count > 0:
                spanish_message += f" y se crearon {created_articles_count} nuevos artículos"
                
            return jsonify({
                "success": True,
                "message": success_message,
                "spanish_message": spanish_message,
                "errors": errors if errors else None
            })
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        return handle_error(str(e))

@bp.route('/importar-recibos', methods=['POST'])
def importar_recibos():
    """
    Import sales data from receipts in a CSV file.
    
    Expected request:
    - file: CSV file with receipts data containing 'Fecha', 'Descripción', and optionally 'Recibo' columns
    
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
        
        # Parse the CSV file
        file_content = file.read()
        parse_result = parse_receipts_data(file_content)
        
        if not parse_result["success"]:
            return jsonify({"success": False, "error": parse_result["error"]}), 400
        
        # Get the parsed sales data by date
        sales_by_date = parse_result["data"]
        
        if not sales_by_date:
            return jsonify({"success": False, "error": "No valid sales data found in the CSV"}), 400
        
        # Get receipt data for duplicate checking
        receipts_data = parse_result.get("receipts", {})
        
        # Debug log
        current_app.logger.info(f"Parsed sales data: {json.dumps(sales_by_date)}")
        if receipts_data:
            current_app.logger.info(f"Parsed receipts: {json.dumps(receipts_data)}")
        
        # Process and save the data to the database
        db = get_db()
        cursor = db.cursor()
        
        # Initialize counters
        inserted_count = 0
        created_articles_count = 0
        skipped_receipts = 0
        errors = []
        dates_imported = []
        existing_receipts = []
        
        # Get current timestamp for receipt import tracking
        current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check for existing receipt numbers using the dedicated RecibosImportados table
        receipt_numbers = list(filter(None, receipts_data.keys()))
        if receipt_numbers:
            placeholders = ', '.join(['?' for _ in receipt_numbers])
            cursor.execute(
                f"SELECT numero_recibo FROM RecibosImportados WHERE numero_recibo IN ({placeholders})",
                receipt_numbers
            )
            existing_receipt_rows = cursor.fetchall()
            existing_receipts = [row['numero_recibo'] for row in existing_receipt_rows] if existing_receipt_rows else []
            
            current_app.logger.info(f"Found existing receipts: {existing_receipts}")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            # Crear un diccionario para rastrear recibos procesados en esta importación
            processed_receipts = {}
            
            for date_str, products in sales_by_date.items():
                # Convert date format from DD/MM/YY to YYYY-MM-DD
                formatted_date = format_date(date_str)
                if formatted_date not in dates_imported:
                    dates_imported.append(formatted_date)
                
                # Debug log
                current_app.logger.info(f"Processing date: {date_str} -> {formatted_date}")
                
                # Set a default time
                default_time = "12:00:00"
                
                for product_key, quantity in products.items():
                    try:
                        # Extract product name and variant
                        if "(" in product_key and ")" in product_key:
                            product_name = product_key.split("(")[0].strip()
                            variant = product_key.split("(")[1].split(")")[0].strip()
                        else:
                            product_name = product_key
                            variant = "Sin variante"
                        
                        # Debug log
                        current_app.logger.info(f"Processing product: {product_name} (variant: {variant}) - quantity: {quantity}")
                        
                        # Find the receipt number for this product if available
                        receipt_number = None
                        if receipts_data:
                            # Find the receipt that contains this product on this date
                            for num, data in receipts_data.items():
                                if data['date'] == date_str and product_key in data['items']:
                                    receipt_number = num
                                    break
                        
                        # Skip if this receipt has already been processed (either previously or in this batch)
                        if receipt_number:
                            if receipt_number in existing_receipts:
                                current_app.logger.info(f"Skipping already processed receipt from previous imports: {receipt_number}")
                                # Solo incrementamos el contador una vez por recibo
                                if receipt_number not in processed_receipts:
                                    skipped_receipts += 1
                                    processed_receipts[receipt_number] = "skipped"
                                continue
                            elif receipt_number in processed_receipts:
                                # Este recibo ya fue procesado en esta importación (otro producto del mismo recibo)
                                current_app.logger.info(f"Continuing with receipt already processed in this batch: {receipt_number}")
                            else:
                                # Primera vez que vemos este recibo en esta importación
                                processed_receipts[receipt_number] = "processing"
                        
                        # Check if the article exists
                        cursor.execute(
                            "SELECT id, precio_venta, categoria FROM ArticulosVendidos WHERE nombre = ?",
                            (product_name,)
                        )
                        articulo_result = cursor.fetchone()
                        
                        # Set default pricing information
                        precio_unitario = 0
                        categoria = None
                        
                        # If the article doesn't exist, create it
                        if not articulo_result:
                            try:
                                # Insert new article into ArticulosVendidos
                                cursor.execute(
                                    """
                                    INSERT INTO ArticulosVendidos (nombre, categoria, precio_venta)
                                    VALUES (?, ?, ?)
                                    """,
                                    (product_name, None, 0)
                                )
                                created_articles_count += 1
                                
                                # Log article creation
                                current_app.logger.info(f"Created new article: {product_name}")
                                
                            except sqlite3.Error as e:
                                current_app.logger.error(f"Error creating article {product_name}: {str(e)}")
                                errors.append({
                                    "product": product_name,
                                    "error": f"Error creating article: {str(e)}"
                                })
                        else:
                            precio_unitario = articulo_result['precio_venta'] or 0
                            categoria = articulo_result['categoria']
                        
                        # Prepare the sales data
                        sale_data = {
                            'fecha': formatted_date,
                            'hora': default_time,
                            'articulo': product_name,
                            'categoria': categoria,
                            'subcategoria': variant if variant != "Sin variante" else None,
                            'articulos_vendidos': quantity,
                            'precio_unitario': precio_unitario,
                            'total': precio_unitario * quantity,
                            'ticket': receipt_number,  # Set the receipt number if available
                            'empleado': None,
                            'mesa': None,
                            'comensales': None,
                            'iva': None,
                            'propina': None,
                            'costo_estimado': None,
                            'ganancia_estimada': None,
                            'porcentaje_ganancia': None
                        }
                        
                        # Debug log
                        current_app.logger.info(f"Inserting sale with data: {json.dumps(sale_data)}")
                        
                        # Insert into Ventas table
                        columns = ', '.join(sale_data.keys())
                        placeholders = ', '.join(['?'] * len(sale_data))
                        
                        cursor.execute(
                            f"INSERT INTO Ventas ({columns}) VALUES ({placeholders})",
                            tuple(sale_data.values())
                        )
                        inserted_count += 1
                    
                    except sqlite3.Error as e:
                        current_app.logger.error(f"Error processing product {product_key}: {str(e)}")
                        errors.append({
                            "product": product_key,
                            "error": f"Error: {str(e)}"
                        })
            
            # Register all successfully processed receipts in the RecibosImportados table
            for receipt_number, status in processed_receipts.items():
                if status == "processing" and receipt_number:
                    # Get the receipt date from the receipts_data
                    receipt_date = None
                    for num, data in receipts_data.items():
                        if num == receipt_number:
                            receipt_date = format_date(data['date'])
                            break
                    
                    if receipt_date:
                        try:
                            cursor.execute(
                                "INSERT INTO RecibosImportados (numero_recibo, fecha_importacion, fecha_recibo) VALUES (?, ?, ?)",
                                (receipt_number, current_timestamp, receipt_date)
                            )
                            current_app.logger.info(f"Registered processed receipt: {receipt_number}")
                        except sqlite3.Error as e:
                            current_app.logger.error(f"Error registering receipt {receipt_number}: {str(e)}")
            
            # Commit the transaction if no errors
            db.commit()
            
            # Verify the insertion
            sales_check = []
            for date in dates_imported:
                cursor.execute("SELECT COUNT(*) as count FROM Ventas WHERE fecha = ?", (date,))
                result = cursor.fetchone()
                sales_check.append({"date": date, "count": result['count']})
            
            current_app.logger.info(f"Sales verification: {json.dumps(sales_check)}")
            
            return jsonify({
                "success": True,
                "message": "Receipts data imported successfully",
                "inserted_count": inserted_count,
                "created_articles_count": created_articles_count,
                "skipped_receipts": skipped_receipts,
                "errors": errors if errors else None,
                "dates_imported": dates_imported,
                "sales_verification": sales_check
            })
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            current_app.logger.error(f"Error importing receipts data: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in import receipts endpoint: {str(e)}")
        return handle_error(e, "Error importing receipts data")

@bp.route('/recibos-importados', methods=['GET'])
def get_recibos_importados():
    """
    Get a list of all imported receipts.
    
    Query parameters:
    - fecha_inicio: Start date (YYYY-MM-DD)
    - fecha_fin: End date (YYYY-MM-DD)
    
    Returns:
    - JSON response with imported receipts data
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Base query
        query = "SELECT * FROM RecibosImportados WHERE 1=1"
        params = []
        
        # Apply filters
        if 'fecha_inicio' in request.args:
            query += " AND fecha_recibo >= ?"
            params.append(request.args['fecha_inicio'])
        
        if 'fecha_fin' in request.args:
            query += " AND fecha_recibo <= ?"
            params.append(request.args['fecha_fin'])
        
        # Add sorting
        query += " ORDER BY fecha_importacion DESC"
        
        # Execute the query
        cursor.execute(query, params)
        recibos = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for recibo in recibos:
            result.append({
                'id': recibo['id'],
                'numero_recibo': recibo['numero_recibo'],
                'fecha_importacion': recibo['fecha_importacion'],
                'fecha_recibo': recibo['fecha_recibo']
            })
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM RecibosImportados")
        total = cursor.fetchone()['count']
        
        return jsonify({
            "success": True,
            "data": result,
            "total": total
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting imported receipts: {str(e)}")
        return handle_error(e, "Error retrieving imported receipts data")

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

@bp.route('/reset', methods=['POST'])
def reset_ventas():
    """
    Resetea todas las ventas en la base de datos.
    Solo para uso en desarrollo y depuración.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Contar registros antes de eliminar
        cursor.execute("SELECT COUNT(*) as count FROM Ventas")
        count = cursor.fetchone()['count']
        
        # Eliminar todos los registros
        cursor.execute("DELETE FROM Ventas")
        
        # Reiniciar el autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ventas'")
        
        # Vaciar cache de SQLite
        cursor.execute("PRAGMA optimize")
        
        # Confirmar cambios
        db.commit()
        
        # Log de la operación
        current_app.logger.info(f"API: Se han eliminado {count} registros de ventas")
        
        return jsonify({
            "success": True,
            "message": f"Se han eliminado {count} registros de ventas.",
            "count": count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al resetear ventas: {str(e)}")
        db.rollback()
        return jsonify({
            "success": False,
            "error": f"Error al resetear ventas: {str(e)}"
        }), 500 