import csv
import io
import datetime
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