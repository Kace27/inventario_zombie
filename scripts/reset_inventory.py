#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from database_utils import get_db_connection, get_db_path

def get_db_path():
    """
    Obtiene la ruta correcta de la base de datos.
    """
    # Obtener el directorio raíz del proyecto (dos niveles arriba del directorio scripts)
    root_dir = Path(__file__).parent.parent
    # La base de datos está en inventario_zombie/instance
    db_path = root_dir / 'inventario_zombie' / 'instance' / 'inventario_zombie.sqlite'
    
    # Verificar que la base de datos existe
    if not os.path.exists(db_path):
        raise Exception(f"No se encontró la base de datos en: {db_path}")
    
    return db_path

def reset_inventory():
    """
    Resetea todas las cantidades del inventario a 0 y registra los ajustes.
    """
    try:
        # Obtener la ruta de la base de datos
        db_path = get_db_path()
        
        print("\n=== RESET DE INVENTARIO ===")
        print("Este script pondrá TODAS las cantidades en 0.")
        print(f"Base de datos: {db_path}\n")
        
        confirmacion = input("Escribe 'RESET' para continuar: ")
        if confirmacion != "RESET":
            print("Operación cancelada.")
            return
        
        # Conectar a la base de datos
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar el estado actual del inventario
            cursor.execute("SELECT id, nombre, cantidad_actual, unidad_medida FROM Ingredientes ORDER BY nombre")
            todos_ingredientes = cursor.fetchall()
            
            if not todos_ingredientes:
                print("No hay ingredientes en la base de datos.")
                return
            
            print("\nEstado actual del inventario:")
            for ing in todos_ingredientes:
                print(f"- {ing[1]}: {ing[2]} {ing[3]}")
            
            # Obtener ingredientes con cantidad distinta de 0
            cursor.execute("""
                SELECT id, nombre, cantidad_actual, unidad_medida 
                FROM Ingredientes 
                WHERE cantidad_actual != 0
                ORDER BY nombre
            """)
            ingredientes_a_resetear = cursor.fetchall()
            
            if not ingredientes_a_resetear:
                print("\nNo hay ingredientes para resetear (todos están en 0).")
                return
            
            print(f"\nSe resetearán {len(ingredientes_a_resetear)} ingredientes:")
            for ing in ingredientes_a_resetear:
                print(f"- {ing[1]}: {ing[2]} {ing[3]}")
            
            # Confirmar una última vez
            confirmacion_final = input("\n¿Proceder con el reseteo? (s/N): ")
            if confirmacion_final.lower() != 's':
                print("Operación cancelada.")
                return
            
            # Iniciar la transacción
            conn.execute("BEGIN")
            
            # Registrar los ajustes
            fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            motivo = "Reset manual de inventario"
            
            # Insertar los ajustes para cada ingrediente
            for ing_id, nombre, cantidad_actual, _ in ingredientes_a_resetear:
                cursor.execute("""
                    INSERT INTO AjustesInventario 
                    (ingrediente_id, cantidad_ajustada, motivo, fecha_ajuste)
                    VALUES (?, ?, ?, ?)
                """, (ing_id, -cantidad_actual, motivo, fecha))
            
            # Actualizar todas las cantidades a 0 en una sola operación
            cursor.execute("UPDATE Ingredientes SET cantidad_actual = 0")
            
            # Verificar que todas las cantidades sean 0
            cursor.execute("SELECT COUNT(*) FROM Ingredientes WHERE cantidad_actual != 0")
            remaining = cursor.fetchone()[0]
            
            if remaining > 0:
                raise Exception(f"Error: {remaining} ingredientes no se resetearon correctamente")
            
            # Confirmar los cambios
            conn.commit()
            
            print("\n¡Reseteo completado exitosamente!")
            print(f"Se resetearon {len(ingredientes_a_resetear)} ingredientes.")
            print("Todos los cambios fueron registrados en AjustesInventario.")
            
            # Mostrar estado final
            cursor.execute("SELECT nombre, cantidad_actual, unidad_medida FROM Ingredientes ORDER BY nombre")
            estado_final = cursor.fetchall()
            print("\nEstado final del inventario:")
            for ing in estado_final:
                print(f"- {ing[0]}: {ing[1]} {ing[2]}")
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            if conn:
                conn.rollback()
                print("Se han revertido todos los cambios.")
        finally:
            if conn:
                conn.close()
    except Exception as e:
        print(f"\nERROR: {str(e)}")

if __name__ == "__main__":
    reset_inventory() 