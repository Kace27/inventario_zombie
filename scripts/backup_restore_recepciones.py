import sqlite3
import json
from datetime import datetime
import os

def get_db_connection(db_path):
    """Crear una conexión a la base de datos."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def backup_recepciones(db_path, output_file):
    """
    Hacer backup de las recepciones y sus detalles a un archivo JSON.
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Obtener todas las recepciones
        cursor.execute("""
            SELECT * FROM RecepcionesCocina
            ORDER BY id
        """)
        recepciones = [dict(row) for row in cursor.fetchall()]
        
        # Para cada recepción, obtener sus detalles
        for recepcion in recepciones:
            cursor.execute("""
                SELECT * FROM RecepcionesDetalles
                WHERE recepcion_id = ?
            """, (recepcion['id'],))
            detalles = [dict(row) for row in cursor.fetchall()]
            recepcion['detalles'] = detalles
        
        # Guardar en archivo JSON
        backup_data = {
            'fecha_backup': datetime.now().isoformat(),
            'recepciones': recepciones
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=4, ensure_ascii=False)
            
        print(f"Backup completado. Se guardaron {len(recepciones)} recepciones en {output_file}")
        
    except Exception as e:
        print(f"Error al hacer backup: {str(e)}")
    finally:
        conn.close()

def restore_recepciones(db_path, input_file):
    """
    Restaurar recepciones desde un archivo JSON a la base de datos.
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(input_file):
            print(f"El archivo {input_file} no existe.")
            return
        
        # Cargar datos del backup
        with open(input_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Comenzar transacción
        conn.execute("BEGIN TRANSACTION")
        
        try:
            for recepcion in backup_data['recepciones']:
                detalles = recepcion.pop('detalles')  # Remover detalles del dict principal
                
                # Insertar recepción
                placeholders = ', '.join(['?'] * len(recepcion))
                columns = ', '.join(recepcion.keys())
                cursor.execute(f"""
                    INSERT OR REPLACE INTO RecepcionesCocina ({columns})
                    VALUES ({placeholders})
                """, list(recepcion.values()))
                
                # Insertar detalles
                for detalle in detalles:
                    placeholders = ', '.join(['?'] * len(detalle))
                    columns = ', '.join(detalle.keys())
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO RecepcionesDetalles ({columns})
                        VALUES ({placeholders})
                    """, list(detalle.values()))
            
            conn.commit()
            print(f"Restauración completada. Se restauraron {len(backup_data['recepciones'])} recepciones.")
            
        except Exception as e:
            conn.rollback()
            print(f"Error durante la restauración: {str(e)}")
            raise
            
    except Exception as e:
        print(f"Error al restaurar: {str(e)}")
    finally:
        conn.close()

def main():
    # Rutas
    db_path = os.path.join('inventario_zombie', 'instance', 'inventario_zombie.sqlite')
    backup_path = os.path.join('backups', 'recepciones_backup.json')
    
    # Crear directorio de backups si no existe
    os.makedirs('backups', exist_ok=True)
    
    # Menú
    while True:
        print("\n1. Hacer backup de recepciones")
        print("2. Restaurar recepciones desde backup")
        print("3. Salir")
        
        opcion = input("\nSeleccione una opción: ")
        
        if opcion == "1":
            backup_recepciones(db_path, backup_path)
        elif opcion == "2":
            restore_recepciones(db_path, backup_path)
        elif opcion == "3":
            break
        else:
            print("Opción no válida")

if __name__ == '__main__':
    main() 