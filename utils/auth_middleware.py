from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

def role_required(roles):
    """
    Decorator to check if user has one of the required roles
    
    Args:
        roles: A list of role names or a single role name string
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            
            # Convert single role string to list
            required_roles = roles if isinstance(roles, list) else [roles]
            
            if current_user.rol not in required_roles:
                flash('No tiene permisos para acceder a esta página.', 'error')
                if current_user.rol == 'cocina':
                    return redirect(url_for('recepciones_web.formulario'))
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Specific role decorators for convenience
def admin_required(f):
    """Decorator to ensure the user has admin role"""
    return role_required('admin')(f)

def cocina_required(f):
    """Decorator to ensure the user has cocina role"""
    return role_required('cocina')(f)

def any_role_required(f):
    """Decorator to ensure the user is authenticated with any role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function 