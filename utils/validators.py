from flask import request, jsonify

def validate_request_json(required_fields=None):
    """
    Validate that the request contains valid JSON and required fields.
    
    Args:
        required_fields (list): List of required field names
        
    Returns:
        tuple: (is_valid, data, error_response)
            - is_valid (bool): Whether the request is valid
            - data (dict): The request data if valid, otherwise None
            - error_response: JSON response with error message if invalid, otherwise None
    """
    # Check if request has JSON data
    if not request.is_json:
        return False, None, (jsonify({'error': 'Content-Type must be application/json'}), 415)
    
    # Get the request data
    data = request.get_json()
    
    # Validate required fields if specified
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return False, None, (jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400)
    
    return True, data, None

def validate_id(id_value):
    """
    Validate that the ID is a positive integer.
    
    Args:
        id_value: The ID value to validate
        
    Returns:
        bool: Whether the ID is valid
    """
    try:
        id_int = int(id_value)
        return id_int > 0
    except (ValueError, TypeError):
        return False

def validate_numeric(value, min_value=None, max_value=None, allow_zero=True, allow_negative=False):
    """
    Validate that a value is numeric and within range.
    
    Args:
        value: The value to validate
        min_value (float, optional): Minimum allowed value
        max_value (float, optional): Maximum allowed value
        allow_zero (bool): Whether zero is allowed
        allow_negative (bool): Whether negative values are allowed
        
    Returns:
        bool: Whether the value is valid
    """
    try:
        num = float(value)
        
        if not allow_negative and num < 0:
            return False
            
        if not allow_zero and num == 0:
            return False
            
        if min_value is not None and num < min_value:
            return False
            
        if max_value is not None and num > max_value:
            return False
            
        return True
    except (ValueError, TypeError):
        return False

def validate_string(value, min_length=1, max_length=None):
    """
    Validate that a value is a string within length constraints.
    
    Args:
        value: The value to validate
        min_length (int): Minimum allowed length
        max_length (int, optional): Maximum allowed length
        
    Returns:
        bool: Whether the value is valid
    """
    if not isinstance(value, str):
        return False
        
    length = len(value.strip())
    
    if length < min_length:
        return False
        
    if max_length is not None and length > max_length:
        return False
        
    return True

def validate_required_fields(data, required_fields):
    """
    Validate that the data contains all required fields.
    
    Args:
        data (dict): The data to validate
        required_fields (list): List of required field names
        
    Returns:
        dict: Validation result with 'valid' flag and 'error' message if invalid
    """
    if not data:
        return {'valid': False, 'error': 'No data provided'}
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        return {
            'valid': False, 
            'error': f'Missing required fields: {", ".join(missing_fields)}'
        }
    
    return {'valid': True}

def validate_numeric_value(data, field_name, expected_type='float', error_message=None):
    """
    Validate that a field in the data is a numeric value of the expected type.
    
    Args:
        data (dict): The data containing the field
        field_name (str): The name of the field to validate
        expected_type (str): The expected numeric type ('int' or 'float')
        error_message (str, optional): Custom error message
        
    Returns:
        dict: Validation result with 'valid' flag and 'error' message if invalid
    """
    if field_name not in data:
        return {'valid': True}  # Skip validation if field is not present
    
    value = data[field_name]
    
    if value is None or value == '':
        return {'valid': True}  # Skip validation if field is empty
    
    try:
        if expected_type == 'int':
            int(value)
        else:  # float
            float(value)
        return {'valid': True}
    except (ValueError, TypeError):
        if error_message:
            return {'valid': False, 'error': error_message}
        else:
            return {
                'valid': False, 
                'error': f'Field "{field_name}" must be a valid {expected_type}'
            } 