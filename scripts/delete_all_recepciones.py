import sqlite3
import sys
import os
from pathlib import Path
from database_utils import get_db_connection, get_db_path

def delete_all_recepciones():
    try:
        # Connect to the database
        db_path = get_db_path()
        if not os.path.exists(db_path):
            print(f"Error: Database file not found at {db_path}")
            return False

        print(f"Using database at: {db_path}")  # Debug line
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if there are any receptions
        cursor.execute("SELECT COUNT(*) as count FROM RecepcionesCocina")
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("No hay recepciones para eliminar.")
            return True

        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")

        try:
            # Get all receptions with ingredient details
            cursor.execute("""
                SELECT r.id, r.ingrediente_id, r.cantidad_recibida, i.nombre as ingrediente_nombre,
                       r.fecha_recepcion, r.hora_recepcion
                FROM RecepcionesCocina r
                JOIN Ingredientes i ON r.ingrediente_id = i.id
                ORDER BY r.fecha_recepcion DESC, r.hora_recepcion DESC
            """)
            recepciones = cursor.fetchall()

            print(f"\nEncontradas {len(recepciones)} recepciones para eliminar:")
            for recepcion in recepciones:
                print(f"ID: {recepcion['id']} - {recepcion['fecha_recepcion']} {recepcion['hora_recepcion']} - "
                      f"{recepcion['ingrediente_nombre']}: {recepcion['cantidad_recibida']}")

            # Update inventory for each ingredient
            for recepcion in recepciones:
                cursor.execute("""
                    UPDATE Ingredientes
                    SET cantidad_actual = cantidad_actual - ?
                    WHERE id = ?
                """, (recepcion['cantidad_recibida'], recepcion['ingrediente_id']))

                print(f"\nActualizando inventario para {recepcion['ingrediente_nombre']}: "
                      f"restando {recepcion['cantidad_recibida']}")

            # Delete all receptions
            cursor.execute("DELETE FROM RecepcionesCocina")
            deleted_count = cursor.rowcount

            # Commit the transaction
            conn.commit()
            print(f"\nSe eliminaron {deleted_count} recepciones exitosamente.")
            return True

        except Exception as e:
            conn.rollback()
            print(f"Error durante la eliminación: {str(e)}")
            return False

        finally:
            conn.close()

    except Exception as e:
        print(f"Error de conexión a la base de datos: {str(e)}")
        return False

if __name__ == "__main__":
    print("¡ADVERTENCIA! Este script eliminará TODAS las recepciones de la base de datos.")
    print("Esta acción no se puede deshacer.")
    response = input("¿Está seguro que desea continuar? (s/N): ")

    if response.lower() == 's':
        if delete_all_recepciones():
            print("\nProceso completado exitosamente.")
            
            # Verificar que se hayan eliminado todas las recepciones
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM RecepcionesCocina")
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                print("Verificación exitosa: No quedan recepciones en la base de datos.")
            else:
                print(f"¡Advertencia! Aún quedan {remaining} recepciones en la base de datos.")
            conn.close()
        else:
            print("\nEl proceso falló.")
            sys.exit(1)
    else:
        print("\nOperación cancelada.") 