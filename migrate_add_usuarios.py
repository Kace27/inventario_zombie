import sqlite3
import os
import hashlib
import datetime
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to the database
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'inventario_zombie.sqlite')
conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check if tables already exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Usuarios'")
if cursor.fetchone() is None:
    print("Creating Usuarios table...")
    cursor.execute('''
    CREATE TABLE Usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        contrasena_hash TEXT NOT NULL,
        pin TEXT,
        rol TEXT NOT NULL,
        activo BOOLEAN NOT NULL DEFAULT 1,
        fecha_creacion TEXT NOT NULL,
        ultimo_acceso TEXT,
        intentos_fallidos INTEGER DEFAULT 0
    )
    ''')
    
    # Create default admin user with password 'admin123'
    admin_password = generate_password_hash('admin123')
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
    INSERT INTO Usuarios (nombre, contrasena_hash, rol, activo, fecha_creacion)
    VALUES (?, ?, ?, ?, ?)
    ''', ('admin', admin_password, 'admin', 1, current_time))
    
    print("Created default admin user (username: admin, password: admin123)")
else:
    print("Usuarios table already exists")

# Check if login attempts table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='LoginAttempts'")
if cursor.fetchone() is None:
    print("Creating LoginAttempts table...")
    cursor.execute('''
    CREATE TABLE LoginAttempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_usuario TEXT NOT NULL,
        ip_address TEXT,
        timestamp TEXT NOT NULL,
        exito BOOLEAN NOT NULL
    )
    ''')
else:
    print("LoginAttempts table already exists")

# Commit changes and close connection
conn.commit()
conn.close()

print("Migration completed successfully") 