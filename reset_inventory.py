# reset_inventory.py

import sqlite3
from datetime import datetime
import sys
import os

def get_db_path():
    # Asumiendo que el script está en el directorio raíz del proyecto
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'inventario.db')

def reset_inventory():
    print("\n¡ADVERTENCIA! Este script reseteará TODAS las cantidades del inventario a 0.")
    print("Este es un script de DEBUG y NO debe usarse en producción.")
    print("Se registrará cada cambio en la tabla AjustesInventario para mantener el historial.\n")
    
    confirmation = input("Escribe 'RESET' para confirmar el reseteo del inventario: ")
    
    if confirmation != "RESET":
        print("Operación cancelada.")
        return
    
    try:
        # Conectar a la base de datos
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener todos los ingredientes con cantidad > 0
        cursor.execute("""
            SELECT id, nombre, cantidad_actual, unidad_medida 
            FROM Ingredientes 
            WHERE cantidad_actual > 0
        """)
        ingredientes = cursor.fetchall()
        
        if not ingredientes:
            print("No hay ingredientes con cantidades mayores a 0.")
            return
        
        print(f"\nSe encontraron {len(ingredientes)} ingredientes para resetear:")
        for ing in ingredientes:
            print(f"- {ing[1]}: {ing[2]} {ing[3]}")
        
        final_confirmation = input("\n¿Proceder con el reseteo? (s/N): ")
        if final_confirmation.lower() != 's':
            print("Operación cancelada.")
            return
        
        # Iniciar transacción
        cursor.execute("BEGIN TRANSACTION")
        
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        motivo = "Reset de debug - Reseteo manual de inventario"
        
        # Resetear cada ingrediente y registrar el ajuste
        for ing_id, nombre, cantidad_actual, _ in ingredientes:
            # Registrar el ajuste
            cursor.execute("""
                INSERT INTO AjustesInventario 
                (ingrediente_id, cantidad_ajustada, motivo, fecha_ajuste)
                VALUES (?, ?, ?, ?)
            """, (ing_id, -cantidad_actual, motivo, fecha_actual))
            
            # Actualizar la cantidad a 0
            cursor.execute("""
                UPDATE Ingredientes 
                SET cantidad_actual = 0 
                WHERE id = ?
            """, (ing_id,))
        
        # Confirmar transacción
        conn.commit()
        print("\n¡Reseteo completado!")
        print(f"Se resetearon {len(ingredientes)} ingredientes.")
        print("Todos los cambios fueron registrados en la tabla AjustesInventario.")
        
    except sqlite3.Error as e:
        print(f"\nError en la base de datos: {e}")
        print("Se ha revertido la operación.")
        conn.rollback()
    except Exception as e:
        print(f"\nError inesperado: {e}")
        print("Se ha revertido la operación.")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_inventory()