#!/usr/bin/env python
"""
Script to populate the database with test data for API testing.
Run this script before running test_phase4.py if your database is empty.
"""

import sqlite3
import os
import sys
from datetime import datetime
import json

# Database setup
DB_PATH = os.path.join('instance', 'inventario_zombie.sqlite')

def connect_db():
    """Connect to the SQLite database"""
    if not os.path.exists('instance'):
        os.makedirs('instance')
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    """Close the database connection"""
    if conn:
        conn.close()

def check_tables_exist(conn):
    """Check if the required tables exist"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    
    required_tables = [
        'Ingredientes', 
        'ArticulosVendidos', 
        'ComposicionArticulo',
        'Ventas',
        'RecepcionesCocina'
    ]
    
    missing_tables = [table for table in required_tables if table not in tables]
    return not missing_tables, missing_tables

def create_tables(conn):
    """Create database tables if they don't exist"""
    with open('schema.sql', 'r') as f:
        schema_sql = f.read()
        conn.executescript(schema_sql)
    conn.commit()
    print("✅ Created database tables")

def check_and_create_ingredients(conn):
    """Check if ingredients exist, create them if needed"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM Ingredientes")
    count = cursor.fetchone()['count']
    
    if count == 0:
        print("No ingredients found, creating test ingredients...")
        
        # First ingredient should have ID=1 for consistent testing
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ingredientes'")
        
        test_ingredients = [
            ('Harina', 'kg', 15.0, 100.0, 20.0),
            ('Azúcar', 'kg', 20.0, 80.0, 15.0),
            ('Huevos', 'unidad', 2.5, 50.0, 12.0),
            ('Leche', 'litro', 18.0, 30.0, 5.0),
            ('Mantequilla', 'kg', 85.0, 25.0, 3.0),
            ('Chocolate', 'kg', 120.0, 10.0, 2.0),
            ('Sal', 'kg', 8.0, 15.0, 2.0),
            ('Levadura', 'kg', 45.0, 5.0, 1.0)
        ]
        
        cursor.executemany(
            """
            INSERT INTO Ingredientes (nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo)
            VALUES (?, ?, ?, ?, ?)
            """, 
            test_ingredients
        )
        conn.commit()
        print(f"✅ Created {len(test_ingredients)} test ingredients")
    else:
        print(f"✅ Found {count} existing ingredients")
        
        # Verify if ingredient with id=1 exists
        cursor.execute("SELECT id FROM Ingredientes WHERE id = 1")
        ing_1 = cursor.fetchone()
        
        if not ing_1:
            print("⚠️ No ingredient with ID=1 found, creating one for consistent testing")
            try:
                cursor.execute(
                    """
                    INSERT INTO Ingredientes (id, nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo)
                    VALUES (1, 'Test Ingredient ID1', 'kg', 10.0, 100.0, 10.0)
                    """
                )
                conn.commit()
                print("✅ Created ingredient with ID=1")
            except sqlite3.IntegrityError as e:
                print(f"⚠️ Could not create ingredient with ID=1: {str(e)}")
                # Try a different approach if there's a constraint error
                try:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ingredientes'")
                    cursor.execute("INSERT INTO Ingredientes (nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo) VALUES ('Test Ingredient Reset', 'kg', 10.0, 100.0, 10.0)")
                    conn.commit()
                    print("✅ Reset autoincrement sequence and created new ingredient")
                except Exception as e:
                    print(f"❌ Error resetting sequence: {str(e)}")
        
    # Return ingredients
    cursor.execute("SELECT * FROM Ingredientes")
    return cursor.fetchall()

def check_and_create_products(conn, ingredients):
    """Check if products exist, create them if needed"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM ArticulosVendidos")
    count = cursor.fetchone()['count']
    
    if count == 0 and ingredients:
        print("No products found, creating test products...")
        
        test_products = [
            ('Pastel de Chocolate', 'Pasteles', 'Chocolate', 150.0),
            ('Pan de Trigo', 'Panadería', 'Panes', 25.0),
            ('Galletas de Mantequilla', 'Galletas', 'Mantequilla', 35.0),
            ('Cupcake de Vainilla', 'Pasteles', 'Vainilla', 40.0)
        ]
        
        product_ids = []
        for product in test_products:
            cursor.execute(
                """
                INSERT INTO ArticulosVendidos (nombre, categoria, subcategoria, precio_venta)
                VALUES (?, ?, ?, ?)
                """, 
                product
            )
            product_ids.append(cursor.lastrowid)
        
        conn.commit()
        print(f"✅ Created {len(test_products)} test products")
        
        # Create product compositions
        print("Creating test product compositions...")
        
        test_compositions = [
            # Pastel de Chocolate
            (product_ids[0], ingredients[0]['id'], 0.5),  # Harina
            (product_ids[0], ingredients[1]['id'], 0.3),  # Azúcar
            (product_ids[0], ingredients[2]['id'], 4.0),  # Huevos
            (product_ids[0], ingredients[3]['id'], 0.25),  # Leche
            (product_ids[0], ingredients[4]['id'], 0.2),  # Mantequilla
            (product_ids[0], ingredients[5]['id'], 0.3),  # Chocolate
            
            # Pan de Trigo
            (product_ids[1], ingredients[0]['id'], 1.0),  # Harina
            (product_ids[1], ingredients[6]['id'], 0.02),  # Sal
            (product_ids[1], ingredients[7]['id'], 0.05),  # Levadura
            (product_ids[1], ingredients[3]['id'], 0.2),  # Leche
            
            # Galletas de Mantequilla
            (product_ids[2], ingredients[0]['id'], 0.3),  # Harina
            (product_ids[2], ingredients[1]['id'], 0.15),  # Azúcar
            (product_ids[2], ingredients[4]['id'], 0.15),  # Mantequilla
            (product_ids[2], ingredients[2]['id'], 1.0),  # Huevos
            
            # Cupcake de Vainilla
            (product_ids[3], ingredients[0]['id'], 0.25),  # Harina
            (product_ids[3], ingredients[1]['id'], 0.2),  # Azúcar
            (product_ids[3], ingredients[2]['id'], 2.0),  # Huevos
            (product_ids[3], ingredients[3]['id'], 0.1),  # Leche
            (product_ids[3], ingredients[4]['id'], 0.1)   # Mantequilla
        ]
        
        cursor.executemany(
            """
            INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad)
            VALUES (?, ?, ?)
            """, 
            test_compositions
        )
        conn.commit()
        print(f"✅ Created {len(test_compositions)} test product compositions")
    else:
        print(f"✅ Found {count} existing products")
        
    # Return products
    cursor.execute("SELECT * FROM ArticulosVendidos")
    return cursor.fetchall()

def print_database_summary(conn):
    """Print a summary of the database contents"""
    cursor = conn.cursor()
    
    print("\n----- Database Summary -----")
    
    tables = ["Ingredientes", "ArticulosVendidos", "ComposicionArticulo", "Ventas", "RecepcionesCocina"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"{table}: {count} records")
    
    print("--------------------------\n")

def main():
    """Main function to populate the database with test data"""
    print("===== Database Population Script =====")
    
    # Connect to the database
    conn = None
    try:
        conn = connect_db()
        
        # Check if tables exist
        tables_exist, missing_tables = check_tables_exist(conn)
        if not tables_exist:
            print(f"Missing tables: {', '.join(missing_tables)}")
            create_tables(conn)
        else:
            print("✅ Database tables already exist")
        
        # Check and create ingredients if needed
        ingredients = check_and_create_ingredients(conn)
        
        # Check and create products if needed
        products = check_and_create_products(conn, ingredients)
        
        # Print database summary
        print_database_summary(conn)
        
        print("✅ Database setup complete")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        close_db(conn)

if __name__ == "__main__":
    main() 