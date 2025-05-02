import sqlite3
import os

def migrate_add_categoria():
    """Add categoria column to Ingredientes table if it doesn't exist"""
    print("Migrando base de datos para agregar campo 'categoria' a la tabla Ingredientes...")
    
    # Get the database path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(os.path.dirname(base_dir), 'instance')
    db_path = os.path.join(instance_dir, 'inventario_zombie.sqlite')
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if categoria column exists
        cursor.execute("PRAGMA table_info(Ingredientes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'categoria' not in columns:
            print("Agregando columna 'categoria' a la tabla Ingredientes...")
            cursor.execute("ALTER TABLE Ingredientes ADD COLUMN categoria TEXT")
            conn.commit()
            print("Columna añadida correctamente.")
        else:
            print("La columna 'categoria' ya existe. No se requiere migración.")
            
        # Close connection
        conn.close()
        print("Migración completada.")
        
    except sqlite3.Error as e:
        print(f"Error durante la migración: {e}")

if __name__ == '__main__':
    migrate_add_categoria() 