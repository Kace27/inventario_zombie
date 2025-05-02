from flask import jsonify

class ErrorHandler:
    """Error handling middleware for Flask application."""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize the error handler with the Flask app."""
        
        @app.errorhandler(400)
        def bad_request(e):
            return jsonify({'error': 'Bad request', 'message': str(e)}), 400
            
        @app.errorhandler(404)
        def not_found(e):
            return jsonify({'error': 'Resource not found', 'message': str(e)}), 404
            
        @app.errorhandler(405)
        def method_not_allowed(e):
            return jsonify({'error': 'Method not allowed', 'message': str(e)}), 405
            
        @app.errorhandler(409)
        def conflict(e):
            return jsonify({'error': 'Conflict', 'message': str(e)}), 409
            
        @app.errorhandler(500)
        def server_error(e):
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
            
        @app.errorhandler(Exception)
        def handle_exception(e):
            # Log the exception
            app.logger.error(f"Unhandled exception: {str(e)}")
            return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

def handle_error(error_message, status_code=500):
    """
    Generic error handler to use in route functions.
    
    Args:
        error_message (str): The error message
        status_code (int): HTTP status code (default: 500)
    
    Returns:
        Flask response with JSON error message and status code
    """
    from flask import current_app
    current_app.logger.error(f"API Error: {error_message}")
    return jsonify({
        "success": False,
        "error": error_message
    }), status_code 