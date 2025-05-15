#!/usr/bin/env python
"""
Script para resetear (eliminar) todas las ventas en la base de datos
de manera completa, asegurándose que tanto la base de datos como el API
estén sincronizados.
"""

import os
import sqlite3
import sys
import json
import requests
import signal
import subprocess
import time
from datetime import datetime
import shutil

# Configuración
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'inventario.db')
API_URL = "http://127.0.0.1:8000/api/ventas"
API_RESET_URL = "http://127.0.0.1:8000/api/ventas/reset"
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')

def signal_handler(sig, frame):
    print("\nOperación cancelada por el usuario.")
    sys.exit(0)

def check_db_path():
    """Verificar si la base de datos existe."""
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontró la base de datos en {DB_PATH}")
        return False
    return True

def create_backup():
    """Crea una copia de seguridad de la base de datos."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backup_before_reset_{timestamp}.db"
    
    try:
        # Crear directorio de backups si no existe
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        backup_path = os.path.join(BACKUP_DIR, backup_path)
        
        # Copiar la base de datos
        with open(DB_PATH, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        return backup_path
    except Exception as e:
        print(f"Error al crear backup: {e}")
        return None

def check_server_running():
    """Verifica si el servidor Flask está corriendo y comprueba la API."""
    try:
        response = requests.get(API_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

def reset_ventas_direct():
    """Elimina directamente todos los registros de la tabla Ventas en SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener el número actual de registros en Ventas
        cursor.execute("SELECT COUNT(*) FROM Ventas")
        count_ventas = cursor.fetchone()[0]
        
        # Obtener el número actual de registros en RecibosImportados
        cursor.execute("SELECT COUNT(*) FROM RecibosImportados")
        count_recibos = cursor.fetchone()[0]
        
        if count_ventas == 0 and count_recibos == 0:
            print("Las tablas Ventas y RecibosImportados ya están vacías en la base de datos.")
            conn.close()
            return True
        
        # Eliminar todos los registros de Ventas
        cursor.execute("DELETE FROM Ventas")
        
        # Eliminar todos los registros de RecibosImportados
        cursor.execute("DELETE FROM RecibosImportados")
        
        # Reiniciar el autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ventas'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='RecibosImportados'")
        
        # Vaciar cache de SQLite
        cursor.execute("PRAGMA optimize")
        
        # Confirmar los cambios
        conn.commit()
        
        print(f"Se han eliminado {count_ventas} registros de ventas y {count_recibos} registros de recibos importados de la base de datos SQLite.")
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
        return False

def reset_via_api():
    """Intenta resetear ventas a través de una llamada API (si existe el endpoint)."""
    try:
        response = requests.post(API_RESET_URL)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"Reset a través de API exitoso: {data.get('message')}")
                return True
        return False
    except:
        print("El endpoint de reset de API no está disponible.")
        return False

def check_after_reset():
    """Verifica que el reset fue exitoso consultando la API."""
    try:
        response = requests.get(API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('data', []))
            if count == 0:
                return True
            else:
                print(f"ADVERTENCIA: La API aún devuelve {count} registros después del reset.")
                return False
    except:
        print("Error al verificar el estado de la API después del reset.")
    return False

def restart_flask_server():
    """Sugiere cómo reiniciar el servidor Flask."""
    print("\n==== REINICIO DEL SERVIDOR ====")
    print("Para asegurar que los cambios surtan efecto, es necesario reiniciar el servidor Flask:")
    print("1. Presiona Ctrl+C en la terminal donde corre el servidor Flask")
    print("2. Luego ejecuta: python -m flask run --port=8000")
    
    input("Presiona Enter cuando hayas reiniciado el servidor...")

def crear_endpoint_reset():
    """Crea un endpoint para resetear ventas si no existe."""
    print("\n==== CREANDO ENDPOINT DE RESET ====")
    print("Para facilitar futuros resets, podemos añadir un endpoint de reset a la API.")
    
    try:
        # Ruta al archivo de rutas de ventas
        routes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routes', 'ventas.py')
        
        if not os.path.exists(routes_file):
            print(f"No se encontró el archivo {routes_file}")
            return False
        
        # Leer el archivo
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar si el endpoint ya existe
        if "@bp.route('/reset', methods=['POST'])" in content:
            print("El endpoint de reset ya existe.")
            return True
        
        # Añadir el endpoint
        reset_code = """

@bp.route('/reset', methods=['POST'])
def reset_ventas():
    \"\"\"
    Resetea todas las ventas y registros de recibos importados en la base de datos.
    Solo para uso en desarrollo y depuración.
    \"\"\"
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
        
        return jsonify({
            "success": True,
            "message": f"Se han eliminado {count_ventas} registros de ventas y {count_recibos} recibos importados."
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al resetear ventas: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error al resetear ventas: {str(e)}"
        }), 500
"""
        
        # Añadir el código al final del archivo
        with open(routes_file, 'a', encoding='utf-8') as f:
            f.write(reset_code)
        
        print("Endpoint de reset creado correctamente.")
        print("Ahora podrás usar: curl -X POST http://127.0.0.1:8000/api/ventas/reset")
        return True
        
    except Exception as e:
        print(f"Error al crear endpoint de reset: {e}")
        return False

def vaciar_db_completo():
    """Crea una base de datos completamente nueva si todo lo demás falla."""
    try:
        # Hacer un backup
        backup_path = create_backup()
        if backup_path:
            print(f"Backup creado en: {backup_path}")
        
        # Crear un nombre temporal para la base de datos
        temp_db = DB_PATH + ".new"
        
        # Crear una base de datos nueva y solo copiar la estructura
        conn_orig = sqlite3.connect(DB_PATH)
        conn_new = sqlite3.connect(temp_db)
        
        # Obtener el esquema de todas las tablas excepto Ventas y RecibosImportados
        cursor = conn_orig.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT IN ('Ventas', 'RecibosImportados')")
        tables = cursor.fetchall()
        
        # Obtener el esquema de la tabla Ventas (para crearla vacía)
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Ventas'")
        ventas_schema = cursor.fetchone()[0]
        
        # Obtener el esquema de la tabla RecibosImportados (para crearla vacía)
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='RecibosImportados'")
        recibos_schema = cursor.fetchone()[0]
        
        # Crear todas las tablas en la nueva base de datos
        cursor_new = conn_new.cursor()
        for table_name, table_sql in tables:
            cursor_new.execute(table_sql)
            
            # Copiar datos de todas las tablas excepto Ventas y RecibosImportados
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                # Obtener nombres de columnas
                column_names = [description[0] for description in cursor.description]
                placeholders = ', '.join(['?'] * len(column_names))
                columns = ', '.join(column_names)
                
                # Insertar datos
                for row in rows:
                    cursor_new.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", row)
        
        # Crear la tabla Ventas vacía
        cursor_new.execute(ventas_schema)
        
        # Crear la tabla RecibosImportados vacía
        cursor_new.execute(recibos_schema)
        
        # Guardar cambios
        conn_new.commit()
        
        # Cerrar conexiones
        conn_orig.close()
        conn_new.close()
        
        # Reemplazar la base de datos original
        os.remove(DB_PATH)
        os.rename(temp_db, DB_PATH)
        
        print("Base de datos recreada exitosamente con tablas Ventas y RecibosImportados vacías.")
        return True
        
    except Exception as e:
        print(f"Error al recrear la base de datos: {e}")
        return False

def main():
    """Función principal."""
    signal.signal(signal.SIGINT, signal_handler)
    
    print("===================================================")
    print("  RESET COMPLETO DE VENTAS - INVENTARIO ZOMBIE")
    print("===================================================")
    
    print("\n¡ADVERTENCIA! Este script eliminará TODAS las ventas de la base de datos.")
    print("Esta operación NO SE PUEDE DESHACER (excepto con el respaldo automático).")
    
    confirmation = input("\nEscribe 'RESET' para confirmar la eliminación de todas las ventas: ")
    
    if confirmation.upper() != "RESET":
        print("Operación cancelada.")
        return
    
    print("\n===== INICIANDO PROCESO DE RESET =====")
    
    # Verificar ruta de la base de datos
    if not check_db_path():
        return
    
    # Crear respaldo
    backup_path = create_backup()
    if backup_path:
        print(f"Respaldo creado en: {backup_path}")
    
    # Comprobar si el servidor está corriendo
    if check_server_running():
        print("El servidor Flask está activo.")
        
        # Intentar reset vía API si existe
        if reset_via_api():
            print("Reset vía API completado.")
            
            # Verificar después del reset
            if check_after_reset():
                print("Verificación exitosa: La API ya no devuelve registros de ventas.")
                return
        
        print("Creando endpoint de reset para facilitar futuros resets...")
        crear_endpoint_reset()
        
        print("Realizando reset directo en la base de datos...")
    else:
        print("El servidor Flask no está corriendo o no es accesible.")
    
    # Reset directo en la base de datos
    if reset_ventas_direct():
        print("Reset directo en la base de datos completado.")
    else:
        print("El reset directo falló. Intentando recrear la base de datos...")
        
        # Solución más drástica: recrear base de datos
        if vaciar_db_completo():
            print("Base de datos recreada exitosamente con tablas Ventas y RecibosImportados vacías.")
        else:
            print("ERROR: Todos los métodos de reset han fallado.")
            print("Por favor, contacta al administrador del sistema.")
            return
    
    if check_server_running():
        print("\nPara que los cambios surtan efecto completamente, es recomendable reiniciar el servidor Flask.")
        restart_option = input("¿Deseas reiniciar el servidor Flask ahora? (s/n): ")
        if restart_option.lower() == 's':
            restart_flask_server()
    
    print("\n===== RESET COMPLETADO =====")
    print("Todas las ventas han sido eliminadas de la base de datos.")
    print("Recarga la página de ventas para ver los cambios.")

if __name__ == "__main__":
    main() 