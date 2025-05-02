#!/usr/bin/env python
"""
Script to import ingredients from the ingredientes.json file into the database.
This script is meant to be run once to populate the database with initial ingredient data.

Usage:
    python import_ingredientes.py [--dryrun] [--force]
    
Options:
    --dryrun    Show what would be imported without making actual changes
    --force     Force update of all ingredients, even if they already exist
"""

import json
import os
import sqlite3
from flask import Flask
import sys
import argparse

# Add the parent directory to sys.path if running as standalone script
parent_dir = os.path.abspath(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Create a minimal Flask app to use the database functions
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'inventario_zombie.sqlite'),
)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

def get_db():
    """Connect to the application's configured database."""
    return sqlite3.connect(
        app.config['DATABASE'],
        detect_types=sqlite3.PARSE_DECLTYPES
    )

def determine_unit(nombre, cantidad_actual, categoria):
    """
    Determine the appropriate unit of measure based on the ingredient data.
    
    Args:
        nombre (str): Name of the ingredient
        cantidad_actual (float): Current quantity of the ingredient
        categoria (str): Category of the ingredient
        
    Returns:
        str: The inferred unit of measure
    """
    # Set default unit
    unit = 'unidad'
    
    # For decimal quantities less than 100, it's likely kg or l
    if isinstance(cantidad_actual, (int, float)) and cantidad_actual > 0 and cantidad_actual < 100:
        # Check if the name suggests a liquid
        liquids = ['leche', 'aceite', 'agua', 'salsa', 'escencia', 'escesencia', 'crema']
        if any(liquid in nombre.lower() for liquid in liquids):
            unit = 'litro'
        else:
            unit = 'kg'
    
    # For quantities between 100 and 1000, likely ml or g
    elif isinstance(cantidad_actual, (int, float)) and cantidad_actual >= 100 and cantidad_actual < 1000:
        # Check if the name suggests a liquid
        liquids = ['leche', 'aceite', 'agua', 'salsa', 'escencia', 'esencia', 'crema']
        if any(liquid in nombre.lower() for liquid in liquids):
            unit = 'ml'
        else:
            unit = 'g'
    
    # For quantities over 1000, likely ml or g
    elif isinstance(cantidad_actual, (int, float)) and cantidad_actual >= 1000:
        # Check if the name suggests a liquid
        liquids = ['leche', 'aceite', 'agua', 'salsa', 'escencia', 'esencia', 'crema']
        if any(liquid in nombre.lower() for liquid in liquids):
            unit = 'ml'
        else:
            unit = 'g'
    
    # Handle specific categories
    if categoria:
        if categoria.lower() in ['bebidas', 'fuente de sodas']:
            if cantidad_actual and cantidad_actual < 100:
                unit = 'unidad'
        elif categoria.lower() in ['verdura', 'principales']:
            if cantidad_actual and cantidad_actual < 100:
                unit = 'kg'
        elif categoria.lower() == 'empaques':
            unit = 'unidad'
    
    # Special cases based on name
    if 'lata' in nombre.lower():
        unit = 'unidad'
    elif any(word in nombre.lower() for word in ['vaso', 'plato', 'bolsa', 'papel', 'servilleta', 'sanita']):
        unit = 'unidad'
    
    return unit

def estimate_price(nombre, unidad_medida, categoria):
    """
    Estimate a reasonable price for the ingredient based on its name, unit, and category.
    
    Args:
        nombre (str): Name of the ingredient
        unidad_medida (str): Unit of measure
        categoria (str): Category of the ingredient
        
    Returns:
        float or None: Estimated price, or None if no estimate is possible
    """
    # Default prices by category
    default_prices = {
        'Bebidas': {
            'unidad': 15.0,  # Price per unit (can, bottle)
            'litro': 25.0,   # Price per liter
        },
        'Fuente de Sodas': {
            'unidad': 10.0,
            'kg': 100.0,
            'litro': 30.0,
            'g': 0.1,
            'ml': 0.03,
        },
        'Principales': {
            'kg': 120.0,
            'unidad': 5.0,
            'g': 0.12,
        },
        'Verdura': {
            'kg': 30.0,
            'unidad': 8.0,
            'g': 0.03,
        },
        'Salsas': {
            'litro': 50.0,
            'ml': 0.05,
            'kg': 80.0,
            'g': 0.08,
            'unidad': 25.0,
        },
        'Empaques': {
            'unidad': 2.0,
        },
        'Servicio': {
            'unidad': 15.0,
        }
    }
    
    # Get default price from the category and unit
    if categoria and categoria in default_prices and unidad_medida in default_prices[categoria]:
        return default_prices[categoria][unidad_medida]
    
    # Special cases based on name
    if 'lata' in nombre.lower():
        return 15.0  # Standard price for canned drinks
    elif 'helado' in nombre.lower():
        return 60.0 if unidad_medida == 'litro' else 0.06 if unidad_medida == 'ml' else None
    elif 'carne' in nombre.lower() or 'hamb' in nombre.lower():
        return 150.0 if unidad_medida == 'kg' else 0.15 if unidad_medida == 'g' else None
    elif 'queso' in nombre.lower():
        return 120.0 if unidad_medida == 'kg' else 0.12 if unidad_medida == 'g' else None
    
    # Fallback to a general price based on unit
    general_prices = {
        'kg': 100.0,
        'g': 0.1,
        'litro': 40.0,
        'ml': 0.04,
        'unidad': 10.0
    }
    
    return general_prices.get(unidad_medida)

def import_ingredientes(json_file, dry_run=False, force_update=False):
    """
    Import ingredients from a JSON file into the database.
    
    Args:
        json_file (str): Path to the JSON file
        dry_run (bool): If True, show what would be imported without making changes
        force_update (bool): If True, update all ingredients even if they already exist
        
    Returns:
        dict: Statistics about the import process
    """
    try:
        # Load the JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            ingredientes_data = json.load(f)
        
        print(f"Loaded {len(ingredientes_data)} ingredients from {json_file}")
        print("NOTE: All ingredient quantities will be initialized to 0 regardless of JSON values")
        
        if dry_run:
            print("DRY RUN MODE - No changes will be made to the database")
        
        # Connect to the database (unless in dry run mode)
        db = None if dry_run else get_db()
        
        # Track statistics
        stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Process each ingredient
        for ingrediente in ingredientes_data:
            try:
                # Extract data from the JSON
                nombre = ingrediente.get('name')
                # Always set quantity to 0 regardless of JSON value
                cantidad_actual = 0
                stock_minimo = ingrediente.get('minimum_stock', 0)
                categoria = ingrediente.get('category')
                
                # Determine appropriate unit of measure
                # For unit determination, use the original quantity from JSON for better inference
                original_quantity = ingrediente.get('quantity', 0)
                unidad_medida = determine_unit(nombre, original_quantity, categoria)
                
                # Estimate price
                precio_compra = estimate_price(nombre, unidad_medida, categoria)
                
                if dry_run:
                    print(f"Would {'insert' if not force_update else 'update'}: {nombre} (0 {unidad_medida}) - "
                          f"Price: {precio_compra if precio_compra else 'None'}, Category: {categoria}")
                    continue
                
                # Check if the ingredient already exists in the database
                cursor = db.execute('SELECT id FROM Ingredientes WHERE nombre = ?', (nombre,))
                existing = cursor.fetchone()
                
                if existing and not force_update:
                    # Update the existing ingredient but force quantity to 0
                    db.execute(
                        'UPDATE Ingredientes SET unidad_medida = ?, precio_compra = ?, '
                        'cantidad_actual = ?, stock_minimo = ?, categoria = ? WHERE nombre = ?',
                        (unidad_medida, precio_compra, cantidad_actual, stock_minimo, categoria, nombre)
                    )
                    stats['updated'] += 1
                    print(f"Updated: {nombre} (0 {unidad_medida}) - "
                          f"Price: {precio_compra if precio_compra else 'None'}")
                elif not existing:
                    # Insert the new ingredient with quantity 0
                    db.execute(
                        'INSERT INTO Ingredientes (nombre, unidad_medida, precio_compra, '
                        'cantidad_actual, stock_minimo, categoria) VALUES (?, ?, ?, ?, ?, ?)',
                        (nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo, categoria)
                    )
                    stats['inserted'] += 1
                    print(f"Inserted: {nombre} (0 {unidad_medida}) - "
                          f"Price: {precio_compra if precio_compra else 'None'}")
                else:
                    stats['skipped'] += 1
                    print(f"Skipped: {nombre} (already exists)")
            
            except Exception as e:
                print(f"Error processing ingredient {ingrediente.get('name')}: {str(e)}")
                stats['errors'] += 1
        
        # Commit changes if not in dry run mode
        if not dry_run:
            db.commit()
            db.close()
        
        # Print summary
        print("\nImport Summary:")
        print(f"Inserted: {stats['inserted']}")
        print(f"Updated: {stats['updated']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Total: {len(ingredientes_data)}")
        
        return stats
        
    except Exception as e:
        print(f"Error importing ingredients: {str(e)}")
        return None

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Import ingredients from JSON into the database')
    parser.add_argument('--dryrun', action='store_true', help='Show what would be imported without making changes')
    parser.add_argument('--force', action='store_true', help='Force update of all ingredients, even if they already exist')
    args = parser.parse_args()
    
    # Define path to the JSON file
    json_file = os.path.join(parent_dir, '..', 'ingredientes.json')
    
    # Check if the file exists
    if not os.path.exists(json_file):
        # Try alternative location
        json_file = os.path.join(parent_dir, 'ingredientes.json')
        if not os.path.exists(json_file):
            print(f"Error: ingredientes.json file not found")
            sys.exit(1)
    
    # Import the ingredients
    stats = import_ingredientes(json_file, dry_run=args.dryrun, force_update=args.force)
    
    if stats:
        print("Import completed successfully!")
    else:
        print("Import failed!")
        sys.exit(1) 