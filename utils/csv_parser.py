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
    Parse CSV content containing receipt data with items in the format "Cantidad x Articulo (Variante)"
    
    Args:
        file_content (bytes): The CSV file content as bytes
        
    Returns:
        dict: A dictionary with parsing results including success flag and sales data by date
    """
    try:
        # Dictionary to store sales data by date
        sales_by_date = defaultdict(lambda: defaultdict(int))
        
        # Dictionary to track receipt numbers and their data
        receipts_data = {}
        
        # Decode the file content
        content = io.StringIO(file_content.decode('utf-8'))
        
        # Read the CSV file
        reader = csv.DictReader(content)
        
        # Debug para mostrar los encabezados
        headers = None
        for row in reader:
            if not headers:
                headers = list(row.keys())
                current_app.logger.info(f"CSV Headers found: {headers}")
            
            # Check if we have the required columns
            if 'Fecha' not in row or 'Descripción' not in row:
                current_app.logger.error("CSV missing required columns: Fecha and/or Descripción")
                return {"success": False, "error": "CSV debe contener las columnas 'Fecha' y 'Descripción'"}
            
            # Get date string - handle format with or without time
            date_str = row['Fecha']
            if ' ' in date_str:  # Format like "01/05/25 21:38"
                date_str = date_str.split()[0]  # Extract just the date part
            
            description = row['Descripción']
            
            # Try to get receipt number from different possible column names
            receipt_number = None
            if 'Número de recibo' in row:
                receipt_number = row['Número de recibo']
            elif 'Recibo' in row:
                receipt_number = row['Recibo']
                
            current_app.logger.info(f"Processing row with date: {date_str}, receipt: {receipt_number}")
            
            # Skip if no description
            if not description:
                continue
                
            # Extract items using regex
            # Pattern matches: quantity x product (variant)
            items = re.findall(r'(\d+) x ([^(,]+)(?:\s*\(([^)]+)\))?', description)
            
            if not items:
                current_app.logger.warning(f"No items found in description: {description}")
                continue
            
            # Store the receipt data for duplicate checking
            if receipt_number:
                if receipt_number not in receipts_data:
                    receipts_data[receipt_number] = {
                        'date': date_str,
                        'items': {}
                    }
                    current_app.logger.info(f"Created receipt tracking for: {receipt_number}")
            
            for quantity, product, variant in items:
                product = product.strip()
                variant = variant.strip() if variant else "Sin variante"
                
                # Create a key that combines product and variant
                product_key = f"{product} ({variant})"
                
                # Add to the count for this date and product
                sales_by_date[date_str][product_key] += int(quantity)
                
                # Also store in receipts_data if we have a receipt number
                if receipt_number:
                    if product_key not in receipts_data[receipt_number]['items']:
                        receipts_data[receipt_number]['items'][product_key] = 0
                    receipts_data[receipt_number]['items'][product_key] += int(quantity)
        
        # Convert defaultdict to regular dict for JSON serialization
        result_data = {
            date: dict(products) for date, products in sales_by_date.items()
        }
        
        current_app.logger.info(f"Parsed {len(result_data)} dates and {len(receipts_data)} unique receipts")
        
        return {
            "success": True, 
            "data": result_data,
            "receipts": receipts_data  # Include receipt data for duplicate checking
        }
    
    except Exception as e:
        current_app.logger.error(f"Error parsing receipts data: {str(e)}")
        return {"success": False, "error": str(e)}

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