import sqlite3
import os
from pathlib import Path

def get_db_path():
    """Get the path to the SQLite database file."""
    instance_path = Path(__file__).parent.parent / 'instance'
    return instance_path / 'inventario_zombie.sqlite'

def run_migration():
    """Execute the migration to add RecepcionesDetalles table."""
    try:
        # Get database path
        db_path = get_db_path()
        if not os.path.exists(db_path):
            print(f"Error: Database file not found at {db_path}")
            return False

        print(f"Using database at: {db_path}")
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Read migration script
        migration_script_path = Path(__file__).parent / 'add_recepciones_detalles.sql'
        with open(migration_script_path, 'r') as f:
            migration_sql = f.read()

        # Execute the entire script
        try:
            conn.executescript(migration_sql)
            conn.commit()
            print("Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            return False
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False

if __name__ == '__main__':
    run_migration() 