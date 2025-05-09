from flask import Blueprint, request, jsonify, current_app
import sqlite3
from database import get_db
from utils.csv_parser import parse_csv, validate_sales_data, parse_receipts_data, format_date
from utils.error_handler import handle_error
import json
import datetime
import re

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
        created_variants_count = 0
        errors = []
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            # Get all active variant rules
            cursor.execute("SELECT * FROM ReglasVariantes WHERE activo = 1")
            reglas_variantes = cursor.fetchall()
            
            # Process each sales record
            for row in sales_data:
                try:
                    # Check if the article exists
                    articulo_nombre = row.get('articulo')
                    articulo_categoria = row.get('categoria')
                    precio_unitario = row.get('precio_unitario', 0)
                    
                    cursor.execute(
                        "SELECT id, es_variante, articulo_padre_id FROM ArticulosVendidos WHERE nombre = ?",
                        (articulo_nombre,)
                    )
                    articulo_result = cursor.fetchone()
                    
                    # If the article doesn't exist, create it and check for potential variants
                    if not articulo_result:
                        try:
                            # Check if this article might be a variant of an existing product
                            articulo_padre_id = None
                            es_variante = 0
                            
                            # Check against variant rules
                            for regla in reglas_variantes:
                                patron_principal = regla['patron_principal']
                                patron_variante = regla['patron_variante']
                                
                                # Try to match the current article name against the variant pattern
                                if re.search(patron_variante, articulo_nombre, re.IGNORECASE):
                                    # Extract the base name using the patterns
                                    base_name = re.sub(patron_variante, patron_principal, articulo_nombre, flags=re.IGNORECASE)
                                    
                                    # Check if the base article exists
                                    cursor.execute(
                                        "SELECT id FROM ArticulosVendidos WHERE nombre = ? AND es_variante = 0",
                                        (base_name,)
                                    )
                                    base_article = cursor.fetchone()
                                    
                                    if base_article:
                                        articulo_padre_id = base_article['id']
                                        es_variante = 1
                                        current_app.logger.info(f"Detected variant: {articulo_nombre} of parent: {base_name}")
                                        break
                            
                            # Insert new article into ArticulosVendidos
                            cursor.execute(
                                """
                                INSERT INTO ArticulosVendidos (nombre, categoria, precio_venta, articulo_padre_id, es_variante)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (articulo_nombre, articulo_categoria, precio_unitario, articulo_padre_id, es_variante)
                            )
                            articulo_id = cursor.lastrowid
                            
                            if es_variante:
                                created_variants_count += 1
                                
                                # Copy composition from parent product
                                cursor.execute(
                                    'SELECT ingrediente_id, cantidad FROM ComposicionArticulo WHERE articulo_id = ?',
                                    (articulo_padre_id,)
                                )
                                composicion_padre = cursor.fetchall()
                                
                                # Insert composition for the variant
                                for comp in composicion_padre:
                                    cursor.execute(
                                        'INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad) VALUES (?, ?, ?)',
                                        (articulo_id, comp['ingrediente_id'], comp['cantidad'])
                                    )
                                
                                current_app.logger.info(f"Created variant: {articulo_nombre} (ID: {articulo_id}) of parent ID: {articulo_padre_id}")
                            else:
                                created_articles_count += 1
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
                success_message += f", created {created_articles_count} new articles"
            if created_variants_count > 0:
                success_message += f" and {created_variants_count} article variants"
            
            # Spanish messages for the user interface
            spanish_message = f"Se importaron {inserted_count} registros de ventas"
            if created_articles_count > 0:
                spanish_message += f", se crearon {created_articles_count} nuevos artículos"
            if created_variants_count > 0:
                spanish_message += f" y {created_variants_count} variantes de artículos"
                
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
        
        # Get receipts data
        receipts_data = parse_result.get("receipts", {})
        
        if not receipts_data:
            return jsonify({"success": False, "error": "No valid receipt data found in the CSV"}), 400
        
        # Debug log
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
        
        # Check for existing receipt numbers
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
            # Process receipts individually
            for receipt_number, receipt_data in receipts_data.items():
                # Skip if this receipt has already been processed
                if receipt_number in existing_receipts:
                    current_app.logger.info(f"Skipping already processed receipt: {receipt_number}")
                    skipped_receipts += 1
                    continue
                
                date_str = receipt_data['date']
                time_str = receipt_data.get('time')
                
                # Convert date format from DD/MM/YY to YYYY-MM-DD
                formatted_date = format_date(date_str)
                if formatted_date not in dates_imported:
                    dates_imported.append(formatted_date)
                
                # Format time to ensure HH:MM:SS format
                receipt_time = "12:00:00"  # Default time
                if time_str:
                    time_parts = time_str.split(':')
                    if len(time_parts) == 2:  # HH:MM format
                        receipt_time = f"{time_str}:00"
                    else:
                        receipt_time = time_str
                
                current_app.logger.info(f"Processing receipt: {receipt_number}, date: {formatted_date}, time: {receipt_time}")
                
                # Process all items in this receipt
                for item in receipt_data['items']:
                    try:
                        product_name = item['articulo']
                        variant = item['variante'] if item['variante'] else "Sin variante"
                        quantity = item['cantidad']
                        categoria = item['categoria']
                        precio_unitario = item['precio_unitario']
                        costo = item['costo']
                        
                        current_app.logger.info(f"  Processing product: {product_name} (variant: {variant}) - quantity: {quantity}")
                        
                        # Check if the parent article exists
                        cursor.execute(
                            "SELECT id, precio_venta, categoria FROM ArticulosVendidos WHERE nombre = ? AND es_variante = 0",
                            (product_name,)
                        )
                        parent_result = cursor.fetchone()
                        
                        # If the parent article doesn't exist, create it
                        if not parent_result:
                            try:
                                cursor.execute(
                                    """
                                    INSERT INTO ArticulosVendidos (nombre, categoria, precio_venta, es_variante)
                                    VALUES (?, ?, ?, 0)
                                    """,
                                    (product_name, categoria, precio_unitario)
                                )
                                parent_id = cursor.lastrowid
                                created_articles_count += 1
                                current_app.logger.info(f"Created new parent article: {product_name}")
                                
                                parent_result = {
                                    'id': parent_id,
                                    'precio_venta': precio_unitario,
                                    'categoria': categoria
                                }
                            except sqlite3.Error as e:
                                current_app.logger.error(f"Error creating parent article {product_name}: {str(e)}")
                                errors.append({
                                    "product": product_name,
                                    "error": f"Error creating parent article: {str(e)}"
                                })
                                continue
                        
                        # If we have a variant, check if it exists or create it
                        if variant != "Sin variante":
                            variant_name = f"{product_name} - {variant}"
                            cursor.execute(
                                "SELECT id, precio_venta FROM ArticulosVendidos WHERE nombre = ? AND es_variante = 1",
                                (variant_name,)
                            )
                            variant_result = cursor.fetchone()
                            
                            if not variant_result:
                                try:
                                    cursor.execute(
                                        """
                                        INSERT INTO ArticulosVendidos 
                                        (nombre, categoria, precio_venta, articulo_padre_id, es_variante)
                                        VALUES (?, ?, ?, ?, 1)
                                        """,
                                        (variant_name, categoria, precio_unitario, parent_result['id'])
                                    )
                                    created_articles_count += 1
                                    current_app.logger.info(f"Created new variant: {variant_name}")
                                    
                                    # Use the variant's information for the sale
                                    articulo_nombre = variant_name
                                except sqlite3.Error as e:
                                    current_app.logger.error(f"Error creating variant {variant_name}: {str(e)}")
                                    errors.append({
                                        "product": variant_name,
                                        "error": f"Error creating variant: {str(e)}"
                                    })
                                    continue
                            else:
                                articulo_nombre = variant_name
                        else:
                            articulo_nombre = product_name
                        
                        # Prepare the sales data
                        sale_data = {
                            'fecha': formatted_date,
                            'hora': receipt_time,
                            'articulo': articulo_nombre,
                            'categoria': categoria,
                            'subcategoria': variant if variant != "Sin variante" else None,
                            'articulos_vendidos': quantity,
                            'precio_unitario': precio_unitario,
                            'total': precio_unitario * quantity,
                            'ticket': receipt_number,
                            'empleado': None,
                            'mesa': None,
                            'comensales': None,
                            'iva': None,
                            'propina': None,
                            'costo_estimado': costo * quantity if costo else None,
                            'ganancia_estimada': (precio_unitario - costo) * quantity if costo else None,
                            'porcentaje_ganancia': ((precio_unitario - costo) / precio_unitario * 100) if costo and precio_unitario > 0 else None
                        }
                        
                        # Insert into Ventas table
                        columns = ', '.join(sale_data.keys())
                        placeholders = ', '.join(['?'] * len(sale_data))
                        
                        cursor.execute(
                            f"INSERT INTO Ventas ({columns}) VALUES ({placeholders})",
                            tuple(sale_data.values())
                        )
                        inserted_count += 1
                    
                    except sqlite3.Error as e:
                        current_app.logger.error(f"Error processing product {product_name}: {str(e)}")
                        errors.append({
                            "product": product_name,
                            "error": f"Error: {str(e)}"
                        })
                
                # Register the processed receipt
                try:
                    cursor.execute(
                        "INSERT INTO RecibosImportados (numero_recibo, fecha_importacion, fecha_recibo) VALUES (?, ?, ?)",
                        (receipt_number, current_timestamp, formatted_date)
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
    - tickets: Comma-separated list of ticket numbers
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
            
        if 'tickets' in request.args:
            tickets = request.args['tickets'].split(',')
            placeholders = ','.join(['?' for _ in tickets])
            query += f" AND ticket IN ({placeholders})"
            params.extend(tickets)
        
        # Add sorting
        query += " ORDER BY fecha DESC, hora DESC"
        
        # Add pagination only if not filtering by specific tickets
        if 'tickets' not in request.args:
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
    Resetea todas las ventas y registros de recibos importados en la base de datos.
    Solo para uso en desarrollo y depuración.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Contar registros antes de eliminar
        cursor.execute("SELECT COUNT(*) as count FROM Ventas")
        count_ventas = cursor.fetchone()['count']
        
        # Contar recibos importados
        cursor.execute("SELECT COUNT(*) as count FROM RecibosImportados")
        count_recibos = cursor.fetchone()['count']
        
        # Eliminar todos los registros de ventas
        cursor.execute("DELETE FROM Ventas")
        
        # Eliminar todos los recibos importados
        cursor.execute("DELETE FROM RecibosImportados")
        
        # Reiniciar el autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ventas'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='RecibosImportados'")
        
        # Vaciar cache de SQLite
        cursor.execute("PRAGMA optimize")
        
        # Confirmar cambios
        db.commit()
        
        # Log de la operación
        current_app.logger.info(f"API: Se han eliminado {count_ventas} registros de ventas y {count_recibos} recibos importados")
        
        return jsonify({
            "success": True,
            "message": f"Se han eliminado {count_ventas} registros de ventas y {count_recibos} recibos importados.",
            "count_ventas": count_ventas,
            "count_recibos": count_recibos
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al resetear ventas: {str(e)}")
        db.rollback()
        return jsonify({
            "success": False,
            "error": f"Error al resetear ventas: {str(e)}"
        }), 500

@bp.route('/tickets', methods=['GET'])
def get_tickets():
    """
    Get paginated unique ticket numbers.
    
    Query parameters:
    - limit: Maximum number of tickets to return
    - offset: Number of tickets to skip
    
    Returns:
    - JSON response with ticket numbers and total count
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get total count of unique tickets
        cursor.execute("SELECT COUNT(DISTINCT ticket) as count FROM Ventas WHERE ticket IS NOT NULL")
        total_tickets = cursor.fetchone()['count']
        
        # Base query for unique tickets
        query = """
            SELECT DISTINCT ticket 
            FROM Ventas 
            WHERE ticket IS NOT NULL 
            ORDER BY fecha DESC, hora DESC
        """
        params = []
        
        # Add pagination
        if 'limit' in request.args:
            query += " LIMIT ?"
            params.append(int(request.args['limit']))
        
        if 'offset' in request.args:
            query += " OFFSET ?"
            params.append(int(request.args['offset']))
        
        # Execute the query
        cursor.execute(query, params)
        tickets = [row['ticket'] for row in cursor.fetchall()]
        
        return jsonify({
            "success": True,
            "tickets": tickets,
            "total_tickets": total_tickets
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting tickets: {str(e)}")
        return handle_error(e, "Error retrieving tickets") 