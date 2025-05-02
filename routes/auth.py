from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import functools
import re

from database import get_db_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Custom decorator for admin-only routes
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('No tiene permisos para acceder a esta página.', 'error')
            return redirect(url_for('auth.access_denied'))
        return view(*args, **kwargs)
    return wrapped_view

# User model class for Flask-Login
class User:
    def __init__(self, id, nombre, rol, activo):
        self.id = id
        self.nombre = nombre
        self.rol = rol
        self.activo = activo
        self.is_authenticated = True
        self.is_active = activo == 1
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)
    
    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Usuarios WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if user:
            return User(
                id=user['id'],
                nombre=user['nombre'],
                rol=user['rol'],
                activo=user['activo']
            )
        return None
    
    @staticmethod
    def get_by_nombre(nombre):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Usuarios WHERE nombre = ?', (nombre,)).fetchone()
        conn.close()
        
        if user:
            return User(
                id=user['id'],
                nombre=user['nombre'],
                rol=user['rol'],
                activo=user['activo']
            )
        return None

# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('web.index'))
    
    error = None
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        password = request.form.get('password')
        pin = request.form.get('pin')
        remember = 'remember' in request.form
        
        # Determine if using password or PIN login
        is_using_pin = pin is not None and pin.strip() != ''
        login_with = pin if is_using_pin else password
        
        if not nombre or not login_with:
            error = 'Nombre de usuario y ' + ('PIN' if is_using_pin else 'contraseña') + ' son requeridos.'
        else:
            # Debug: Check if database is accessible
            try:
                conn = get_db_connection()
                # Verificar conexión y contenido
                print("Conexión a la base de datos exitosa")
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row['name'] for row in cursor.fetchall()]
                print(f"Tablas en la base de datos: {', '.join(tables)}")
                
                # Verificar si la tabla Usuarios existe
                if 'Usuarios' not in tables:
                    print("ERROR: ¡La tabla Usuarios no existe!")
                    error = 'Error de configuración: tabla Usuarios no encontrada.'
                    conn.close()
                    return render_template('auth/login.html', error=error)
                
                # Verificar usuarios
                cursor = conn.execute("SELECT COUNT(*) as count FROM Usuarios")
                user_count = cursor.fetchone()['count']
                print(f"Número de usuarios en la base de datos: {user_count}")
                
                user = conn.execute('SELECT * FROM Usuarios WHERE nombre = ?', (nombre,)).fetchone()
                
                # Record login attempt
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ip_address = request.remote_addr
                success = False
                
                if user is None:
                    error = 'Usuario no encontrado.'
                    print(f"Usuario '{nombre}' no encontrado en la base de datos")
                elif user['activo'] == 0:
                    error = 'Esta cuenta está desactivada.'
                else:
                    # Check for too many failed attempts
                    if user['intentos_fallidos'] >= 5:
                        error = 'Cuenta bloqueada por demasiados intentos fallidos. Contacte al administrador.'
                    else:
                        # Verify password or PIN
                        if is_using_pin:
                            print(f"Intentando acceder con PIN: {pin}")
                            if user['pin'] and pin == user['pin']:
                                if user['rol'] != 'cocina':
                                    error = 'Este usuario no puede acceder con PIN.'
                                else:
                                    success = True
                                    print("PIN correcto - Acceso concedido")
                            else:
                                error = 'PIN incorrecto.'
                                print("PIN incorrecto")
                        else:
                            print(f"Intentando acceder con contraseña")
                            if check_password_hash(user['contrasena_hash'], password):
                                success = True
                                print("Contraseña correcta - Acceso concedido")
                            else:
                                error = 'Contraseña incorrecta.'
                                print("Contraseña incorrecta")
            except Exception as e:
                print(f"Error de base de datos: {str(e)}")
                error = f'Error de base de datos: {str(e)}'
                return render_template('auth/login.html', error=error)
                
            if success:
                # Login successful
                user_model = User(
                    id=user['id'],
                    nombre=user['nombre'],
                    rol=user['rol'],
                    activo=user['activo']
                )
                login_user(user_model, remember=remember)
                
                # Reset failed attempts and update last access
                conn.execute(
                    'UPDATE Usuarios SET intentos_fallidos = 0, ultimo_acceso = ? WHERE id = ?',
                    (current_time, user['id'])
                )
                
                # Redirect based on role
                if user['rol'] == 'admin':
                    next_page = request.args.get('next') or url_for('index')
                else:  # cocina role
                    next_page = url_for('recepciones_web.formulario')
                
                try:
                    conn.execute(
                        'INSERT INTO LoginAttempts (nombre_usuario, ip_address, timestamp, exito) VALUES (?, ?, ?, ?)',
                        (nombre, ip_address, current_time, 1)
                    )
                except Exception as e:
                    print(f"Error al registrar intento de login: {str(e)}")
                
                conn.commit()
                conn.close()
                
                return redirect(next_page)
            else:
                # Failed login - increment attempts counter
                if user:
                    try:
                        conn.execute(
                            'UPDATE Usuarios SET intentos_fallidos = intentos_fallidos + 1 WHERE id = ?',
                            (user['id'],)
                        )
                    except Exception as e:
                        print(f"Error al incrementar intentos fallidos: {str(e)}")
                
                try:
                    conn.execute(
                        'INSERT INTO LoginAttempts (nombre_usuario, ip_address, timestamp, exito) VALUES (?, ?, ?, ?)',
                        (nombre, ip_address, current_time, 0)
                    )
                except Exception as e:
                    print(f"Error al registrar intento de login fallido: {str(e)}")
                    
                conn.commit()
                conn.close()
    
    return render_template('auth/login.html', error=error)

# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('auth.login'))

# Access denied page
@auth_bp.route('/access-denied')
@login_required
def access_denied():
    return render_template('auth/access_denied.html')

# User management routes (admin only)
@auth_bp.route('/usuarios')
@login_required
@admin_required
def lista_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM Usuarios ORDER BY nombre').fetchall()
    conn.close()
    return render_template('auth/usuarios.html', usuarios=usuarios)

@auth_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        password = request.form.get('password')
        pin = request.form.get('pin') if request.form.get('pin') else None
        rol = request.form.get('rol')
        
        error = None
        
        # Basic validation
        if not nombre or not password or not rol:
            error = 'Nombre, contraseña y rol son requeridos.'
        elif not re.match(r'^[a-zA-Z0-9_]+$', nombre):
            error = 'Nombre de usuario solo puede contener letras, números y guiones bajos.'
        elif len(password) < 6:
            error = 'La contraseña debe tener al menos 6 caracteres.'
        elif pin and (not pin.isdigit() or len(pin) != 4):
            error = 'El PIN debe ser un número de 4 dígitos.'
        elif rol not in ['admin', 'cocina']:
            error = 'Rol inválido.'
        else:
            conn = get_db_connection()
            # Check if username already exists
            existing_user = conn.execute('SELECT id FROM Usuarios WHERE nombre = ?', (nombre,)).fetchone()
            
            if existing_user:
                error = 'Este nombre de usuario ya existe.'
                conn.close()
            else:
                # If cocina role, PIN is required
                if rol == 'cocina' and not pin:
                    error = 'Para usuarios de cocina, el PIN es requerido.'
                
        if error is None:
            # Create new user
            hashed_password = generate_password_hash(password)
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn.execute(
                'INSERT INTO Usuarios (nombre, contrasena_hash, pin, rol, activo, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?)',
                (nombre, hashed_password, pin, rol, 1, current_time)
            )
            conn.commit()
            conn.close()
            
            flash(f'Usuario {nombre} creado exitosamente.', 'success')
            return redirect(url_for('auth.lista_usuarios'))
        
        flash(error, 'error')
    
    return render_template('auth/usuario_form.html', usuario=None, accion='nuevo')

@auth_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM Usuarios WHERE id = ?', (id,)).fetchone()
    
    if not usuario:
        conn.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('auth.lista_usuarios'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        pin = request.form.get('pin') if request.form.get('pin') else None
        rol = request.form.get('rol')
        activo = 1 if request.form.get('activo') else 0
        
        error = None
        
        # Validate input
        if not rol:
            error = 'El rol es requerido.'
        elif rol not in ['admin', 'cocina']:
            error = 'Rol inválido.'
        elif password and len(password) < 6:
            error = 'La contraseña debe tener al menos 6 caracteres.'
        elif pin and (not pin.isdigit() or len(pin) != 4):
            error = 'El PIN debe ser un número de 4 dígitos.'
        elif rol == 'cocina' and not (pin or usuario['pin']):
            error = 'Para usuarios de cocina, el PIN es requerido.'
            
        if error is None:
            # Update user data
            # If changing password
            if password:
                hashed_password = generate_password_hash(password)
                conn.execute(
                    'UPDATE Usuarios SET contrasena_hash = ?, pin = ?, rol = ?, activo = ?, intentos_fallidos = 0 WHERE id = ?',
                    (hashed_password, pin, rol, activo, id)
                )
            else:
                # Not changing password
                conn.execute(
                    'UPDATE Usuarios SET pin = ?, rol = ?, activo = ? WHERE id = ?',
                    (pin, rol, activo, id)
                )
            
            conn.commit()
            conn.close()
            
            # If deactivating current user, log them out
            if id == current_user.id and activo == 0:
                logout_user()
                flash('Tu cuenta ha sido desactivada.', 'info')
                return redirect(url_for('auth.login'))
            
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('auth.lista_usuarios'))
        
        flash(error, 'error')
    
    conn.close()
    return render_template('auth/usuario_form.html', usuario=usuario, accion='editar')

@auth_bp.route('/usuarios/reset/<int:id>', methods=['POST'])
@login_required
@admin_required
def reset_intentos(id):
    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM Usuarios WHERE id = ?', (id,)).fetchone()
    
    if not usuario:
        conn.close()
        flash('Usuario no encontrado.', 'error')
    else:
        conn.execute('UPDATE Usuarios SET intentos_fallidos = 0 WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Intentos fallidos reiniciados.', 'success')
    
    return redirect(url_for('auth.lista_usuarios')) 