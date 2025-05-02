import os
import sqlite3

def fix_categoria_column():
    """Fix the categoria column in the Ingredientes table while preserving the data"""
    print("Fixing the categoria column in the Ingredientes table...")
    
    # Get the database path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(os.path.dirname(base_dir), 'instance')
    db_path = os.path.join(instance_dir, 'inventario_zombie.sqlite')
    
    # Create instance directory if it doesn't exist
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        conn.execute('BEGIN TRANSACTION')
        
        # Check if Ingredientes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Ingredientes'")
        if not cursor.fetchone():
            print("Ingredientes table does not exist, nothing to fix")
            conn.rollback()
            return
        
        # Get column info
        cursor.execute("PRAGMA table_info(Ingredientes)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        # Check if categoria column exists
        categoria_exists = 'categoria' in columns
        print(f"Categoria column exists: {categoria_exists}")
        
        # Get existing data
        cursor.execute("SELECT * FROM Ingredientes")
        rows = [dict(row) for row in cursor.fetchall()]
        print(f"Found {len(rows)} existing ingredients")
        
        # Create a backup table
        cursor.execute("CREATE TABLE Ingredientes_backup AS SELECT * FROM Ingredientes")
        print("Created backup table Ingredientes_backup")
        
        # Drop the original table
        cursor.execute("DROP TABLE Ingredientes")
        print("Dropped original Ingredientes table")
        
        # Create the table again with the correct schema
        cursor.execute("""
        CREATE TABLE Ingredientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            unidad_medida TEXT NOT NULL,
            precio_compra REAL,
            cantidad_actual REAL NOT NULL DEFAULT 0,
            stock_minimo REAL,
            categoria TEXT
        )
        """)
        print("Recreated Ingredientes table with proper schema")
        
        # Insert the data back
        for row in rows:
            # Prepare the data for insertion
            params = [
                row['id'],
                row['nombre'],
                row['unidad_medida'],
                row['precio_compra'],
                row['cantidad_actual'],
                row['stock_minimo']
            ]
            
            # Include categoria if it existed
            if categoria_exists and 'categoria' in row:
                query = """
                INSERT INTO Ingredientes (id, nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo, categoria)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                params.append(row.get('categoria'))
            else:
                query = """
                INSERT INTO Ingredientes (id, nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo)
                VALUES (?, ?, ?, ?, ?, ?)
                """
            
            cursor.execute(query, params)
        
        print(f"Reinserted {len(rows)} ingredients into the table")
        
        # Reset the SQLite sequence
        cursor.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM Ingredientes) WHERE name = 'Ingredientes'")
        
        # Commit the transaction
        conn.commit()
        print("Committed changes - fix successful!")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error fixing categoria column: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    fix_categoria_column() 