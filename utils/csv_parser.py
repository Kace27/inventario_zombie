import csv
import io
import re
import datetime
from collections import defaultdict
from flask import current_app

def parse_csv(file_content, columns_mapping=None):
    """
    Parse CSV content and return a list of dictionaries.
    
    Args:
        file_content (bytes): The CSV file content as bytes
        columns_mapping (dict, optional): A mapping of CSV column names to database column names
                                         If None, column names are used as-is
    
    Returns:
        list: A list of dictionaries representing the CSV data
    """
    try:
        # Decode the file content
        content = io.StringIO(file_content.decode('utf-8'))
        
        # Read the CSV file
        reader = csv.DictReader(content)
        
        # Prepare the data
        data = []
        for row in reader:
            # Apply column mapping if provided
            if columns_mapping:
                mapped_row = {}
                for csv_col, db_col in columns_mapping.items():
                    if csv_col in row:
                        mapped_row[db_col] = row[csv_col]
                data.append(mapped_row)
            else:
                data.append(row)
        
        return {"success": True, "data": data}
    
    except Exception as e:
        current_app.logger.error(f"Error parsing CSV: {str(e)}")
        return {"success": False, "error": str(e)}

def validate_sales_data(sales_data):
    """
    Validate the sales data before importing.
    
    Args:
        sales_data (list): A list of dictionaries containing sales data
    
    Returns:
        dict: A dictionary with validation results including success flag and errors if any
    """
    required_fields = ['fecha', 'hora', 'articulo', 'articulos_vendidos']
    errors = []
    
    for index, row in enumerate(sales_data):
        row_errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in row or not row[field]:
                row_errors.append(f"Missing required field: {field}")
        
        # Validate fecha format (should be a valid date)
        if 'fecha' in row and row['fecha']:
            try:
                datetime.datetime.strptime(row['fecha'], '%Y-%m-%d')
            except ValueError:
                row_errors.append("Invalid date format. Expected: YYYY-MM-DD")
        
        # Validate hora format (should be a valid time)
        if 'hora' in row and row['hora']:
            try:
                datetime.datetime.strptime(row['hora'], '%H:%M:%S')
            except ValueError:
                try:
                    # Try alternative format
                    datetime.datetime.strptime(row['hora'], '%H:%M')
                except ValueError:
                    row_errors.append("Invalid time format. Expected: HH:MM:SS or HH:MM")
        
        # Validate numerical fields
        numerical_fields = ['articulos_vendidos', 'precio_unitario', 'total']
        for field in numerical_fields:
            if field in row and row[field]:
                try:
                    float(row[field])
                except ValueError:
                    row_errors.append(f"Invalid numerical value for: {field}")
        
        if row_errors:
            errors.append({
                "row": index + 1,
                "errors": row_errors
            })
    
    if errors:
        return {"success": False, "errors": errors}
    
    return {"success": True}

def parse_receipts_data(file_content):
    """
    Parse receipts data from CSV content. Supports both old and new formats:
    
    Old format columns:
    - Fecha
    - Descripción (with format "X x Product (Variant)")
    - Número de recibo
    
    New format columns:
    - Fecha
    - Número de recibo
    - Artículo
    - Variante
    - Cantidad
    - Ventas brutas
    - Ventas netas
    - Categoria
    - Costo de los bienes
    
    Returns:
    - Dictionary with parsing results
    """
    try:
        # Decode bytes to string if needed
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        
        # Split into lines and remove empty ones
        lines = [line.strip() for line in file_content.split('\n') if line.strip()]
        
        if len(lines) < 2:  # Need at least header and one data row
            return {
                "success": False,
                "error": "CSV file is empty or has no data rows"
            }
        
        # Process header
        header = [col.strip() for col in lines[0].split(',')]
        
        # Detect format type
        is_new_format = 'Artículo' in header and 'Variante' in header and 'Cantidad' in header
        
        if is_new_format:
            return parse_new_format_receipts(lines, header)
        else:
            return parse_old_format_receipts(lines, header)
            
    except Exception as e:
        current_app.logger.error(f"Error parsing receipts data: {str(e)}")
        return {
            "success": False,
            "error": f"Error parsing CSV: {str(e)}"
        }

def parse_new_format_receipts(lines, header):
    """Parse receipts data in the new format (one product per line)"""
    try:
        # Find column indices
        required_columns = {
            'Fecha': None,
            'Número de recibo': None,
            'Artículo': None,
            'Cantidad': None,
            'Ventas brutas': None
        }
        
        for i, col in enumerate(header):
            if col in required_columns:
                required_columns[col] = i
        
        # Verify required columns
        missing_columns = [col for col, idx in required_columns.items() if idx is None]
        if missing_columns:
            return {
                "success": False,
                "error": f"Missing required columns: {', '.join(missing_columns)}"
            }
        
        # Find optional column indices
        variante_idx = header.index('Variante') if 'Variante' in header else None
        categoria_idx = header.index('Categoria') if 'Categoria' in header else None
        ventas_netas_idx = header.index('Ventas netas') if 'Ventas netas' in header else None
        costo_idx = header.index('Costo de los bienes') if 'Costo de los bienes' in header else None
        
        # Process data rows
        receipts = {}
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Split the line and handle quoted fields
            row = line.split(',')
            
            # Extract data using found indices
            fecha = row[required_columns['Fecha']].strip()
            numero_recibo = row[required_columns['Número de recibo']].strip()
            articulo = row[required_columns['Artículo']].strip()
            cantidad = float(row[required_columns['Cantidad']].replace(',', '.'))
            ventas_brutas = float(row[required_columns['Ventas brutas']].replace(',', '.'))
            
            # Get optional fields
            variante = row[variante_idx].strip() if variante_idx is not None and variante_idx < len(row) else None
            categoria = row[categoria_idx].strip() if categoria_idx is not None and categoria_idx < len(row) else None
            ventas_netas = float(row[ventas_netas_idx].replace(',', '.')) if ventas_netas_idx is not None and ventas_netas_idx < len(row) and row[ventas_netas_idx].strip() else ventas_brutas
            costo = float(row[costo_idx].replace(',', '.')) if costo_idx is not None and costo_idx < len(row) and row[costo_idx].strip() else 0.0
            
            # Extract date and time from fecha (format: DD/MM/YY HH:MM)
            fecha_parts = fecha.split(' ')
            date = fecha_parts[0]
            time = fecha_parts[1] if len(fecha_parts) > 1 else None
            
            # Initialize receipt if not exists
            if numero_recibo not in receipts:
                receipts[numero_recibo] = {
                    'date': date,
                    'time': time,
                    'items': []
                }
            
            # Add item to receipt
            receipts[numero_recibo]['items'].append({
                'articulo': articulo,
                'variante': variante,
                'cantidad': cantidad,
                'precio_unitario': ventas_brutas / cantidad if cantidad > 0 else 0,
                'precio_neto': ventas_netas / cantidad if cantidad > 0 else 0,
                'categoria': categoria,
                'costo': costo
            })
        
        return {
            "success": True,
            "receipts": receipts
        }
    
    except Exception as e:
        current_app.logger.error(f"Error parsing new format receipts: {str(e)}")
        return {
            "success": False,
            "error": f"Error parsing new format CSV: {str(e)}"
        }

def parse_old_format_receipts(lines, header):
    """Parse receipts data in the old format (products in Description column)"""
    try:
        # Find required columns
        fecha_idx = header.index('Fecha')
        descripcion_idx = header.index('Descripción')
        numero_recibo_idx = -1
        
        # Look for receipt number column with different possible names
        for possible_name in ['Número de recibo', 'Recibo', 'Numero de recibo']:
            try:
                numero_recibo_idx = header.index(possible_name)
                break
            except ValueError:
                continue
        
        if numero_recibo_idx == -1:
            return {
                "success": False,
                "error": "Missing required column: Número de recibo"
            }
        
        # Process data rows
        receipts = {}
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Split the line
            row = line.split(',')
            
            # Get basic info
            fecha = row[fecha_idx].strip()
            descripcion = row[descripcion_idx].strip()
            numero_recibo = row[numero_recibo_idx].strip()
            
            # Extract date and time
            fecha_parts = fecha.split(' ')
            date = fecha_parts[0]
            time = fecha_parts[1] if len(fecha_parts) > 1 else None
            
            # Initialize receipt
            if numero_recibo not in receipts:
                receipts[numero_recibo] = {
                    'date': date,
                    'time': time,
                    'items': []
                }
            
            # Process description
            items = descripcion.split(',')
            for item in items:
                item = item.strip()
                if not item:
                    continue
                
                # Match format: "XX x Product" or "XX x Product (Variant)"
                match = re.match(r'(\d+)\s*x\s*([^(]+)(?:\s*\(([^)]+)\))?', item)
                if not match:
                    current_app.logger.warning(f"Could not parse product entry: '{item}'")
                    continue
                
                quantity_str, product, variant = match.groups()
                quantity = float(quantity_str.strip())
                product = product.strip()
                variant = variant.strip() if variant else None
                
                # Add item to receipt
                receipts[numero_recibo]['items'].append({
                    'articulo': product,
                    'variante': variant,
                    'cantidad': quantity,
                    'precio_unitario': 0,  # Price not available in old format
                    'precio_neto': 0,
                    'categoria': None,
                    'costo': 0
                })
        
        return {
            "success": True,
            "receipts": receipts
        }
    
    except Exception as e:
        current_app.logger.error(f"Error parsing old format receipts: {str(e)}")
        return {
            "success": False,
            "error": f"Error parsing old format CSV: {str(e)}"
        }

def format_date(date_str):
    """
    Convert date string to YYYY-MM-DD format
    
    Args:
        date_str (str): Date string in various possible formats (DD/MM/YY, DD/MM/YYYY, etc.)
        
    Returns:
        str: Date string in format YYYY-MM-DD
    """
    try:
        # Clean the input string
        date_str = date_str.strip()
        
        # Handle different separators
        if '/' in date_str:
            parts = date_str.split('/')
        elif '-' in date_str:
            parts = date_str.split('-')
        elif '.' in date_str:
            parts = date_str.split('.')
        else:
            current_app.logger.error(f"Unknown date format: {date_str}")
            return datetime.datetime.now().strftime('%Y-%m-%d')  # Fallback to today's date
        
        # We expect either DD/MM/YY or DD/MM/YYYY
        if len(parts) == 3:
            day, month, year = parts
            
            # Ensure day and month are two digits
            day = day.zfill(2)
            month = month.zfill(2)
            
            # Handle two digit years
            if len(year) == 2:
                year = f"20{year}"
                
            # Validate parts
            if not (day.isdigit() and month.isdigit() and year.isdigit()):
                raise ValueError(f"Date parts not numeric: {date_str}")
                
            # Basic validation
            day_int = int(day)
            month_int = int(month)
            year_int = int(year)
            
            if not (1 <= day_int <= 31 and 1 <= month_int <= 12 and year_int >= 2000):
                raise ValueError(f"Date values out of range: {date_str}")
                
            return f"{year}-{month}-{day}"
        else:
            current_app.logger.error(f"Date string has wrong number of parts: {date_str}")
            return datetime.datetime.now().strftime('%Y-%m-%d')  # Fallback to today's date
            
    except Exception as e:
        current_app.logger.error(f"Error formatting date {date_str}: {str(e)}")
        return datetime.datetime.now().strftime('%Y-%m-%d')  # Fallback to today's date 