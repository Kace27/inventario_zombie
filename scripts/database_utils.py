#!/usr/bin/env python3
import os
import sys
import sqlite3
from pathlib import Path

def get_db_path():
    """
    Obtiene la ruta correcta de la base de datos.
    Busca en las siguientes ubicaciones en orden:
    1. inventario_zombie/instance/inventario_zombie.sqlite
    2. instance/inventario_zombie.sqlite
    """
    # Obtener el directorio del script actual
    current_dir = Path(__file__).resolve().parent
    
    # Obtener el directorio raíz del proyecto (un nivel arriba de scripts)
    project_root = current_dir.parent
    
    # Intentar las diferentes rutas posibles
    possible_paths = [
        project_root / 'inventario_zombie' / 'instance' / 'inventario_zombie.sqlite',
        project_root / 'instance' / 'inventario_zombie.sqlite',
    ]
    
    for db_path in possible_paths:
        if db_path.exists():
            return str(db_path)
    
    # Si no se encuentra la base de datos, mostrar error con las rutas buscadas
    error_msg = "No se encontró la base de datos. Se buscó en:\n"
    for path in possible_paths:
        error_msg += f"- {path}\n"
    raise FileNotFoundError(error_msg)

def get_db_connection():
    """
    Establece y retorna una conexión a la base de datos.
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
        sys.exit(1)

def check_database_structure(conn):
    """
    Verifica la estructura de la base de datos y muestra información útil.
    """
    try:
        cursor = conn.cursor()
        
        # Obtener todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nTablas encontradas en la base de datos:")
        for table in tables:
            table_name = table[0]
            print(f"\nTabla: {table_name}")
            
            # Obtener estructura de la tabla
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("Columnas:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Obtener cantidad de registros
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Registros: {count}")
        
        return True
    except sqlite3.Error as e:
        print(f"Error al verificar la estructura de la base de datos: {e}")
        return False 