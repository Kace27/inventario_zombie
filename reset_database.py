import os
import sqlite3

def reset_database():
    """Reset the database by dropping all tables and recreating them from schema.sql"""
    print("Resetting database...")
    
    # Get paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(os.path.dirname(base_dir), 'instance')
    db_path = os.path.join(instance_dir, 'inventario_zombie.sqlite')
    schema_path = os.path.join(base_dir, 'schema.sql')
    
    # Create instance directory if it doesn't exist
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    # Delete old database file if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}")
        os.remove(db_path)
    
    # Connect to the new database
    print("Creating new database...")
    conn = sqlite3.connect(db_path)
    
    # Read and execute schema.sql
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        conn.executescript(schema_sql)
    
    conn.commit()
    conn.close()
    
    print("Database reset complete!")

if __name__ == '__main__':
    reset_database() 