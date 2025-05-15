#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from database_utils import get_db_connection, check_database_structure

def export_articulos(conn, output_file=None):
    """Exporta los artículos y sus composiciones a un archivo JSON."""
    try:
        # Primero verificamos la estructura de la base de datos
        print("\nVerificando estructura de la base de datos...")
        check_database_structure(conn)
        
        # Obtener todos los artículos
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, categoria, subcategoria, precio_venta, 
                   es_variante, articulo_padre_id
            FROM ArticulosVendidos
        """)
        articulos = cursor.fetchall()
        
        # Crear diccionario para almacenar los datos
        data = {
            'fecha_exportacion': datetime.now().isoformat(),
            'articulos': []
        }
        
        # Procesar cada artículo y su composición
        for articulo in articulos:
            articulo_dict = {
                'id': articulo[0],
                'nombre': articulo[1],
                'categoria': articulo[2],
                'subcategoria': articulo[3],
                'precio_venta': articulo[4],
                'es_variante': bool(articulo[5]),
                'articulo_padre_id': articulo[6],
                'composicion': []
            }
            
            # Obtener la composición del artículo
            cursor.execute("""
                SELECT ingrediente_id, cantidad
                FROM ComposicionArticulo
                WHERE articulo_id = ?
            """, (articulo[0],))
            
            composiciones = cursor.fetchall()
            for comp in composiciones:
                articulo_dict['composicion'].append({
                    'ingrediente_id': comp[0],
                    'cantidad': comp[1]
                })
            
            data['articulos'].append(articulo_dict)
        
        # Generar nombre de archivo si no se proporcionó uno
        if output_file is None:
            output_file = f"articulos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Guardar en archivo JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\nExportación completada. Se exportaron {len(articulos)} artículos a {output_file}")
        return True
        
    except Exception as e:
        print(f"Error durante la exportación: {e}")
        return False

def restore_articulos(conn, input_file):
    """Restaura los artículos y sus composiciones desde un archivo JSON."""
    try:
        # Leer el archivo JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cursor = conn.cursor()
        
        # Iniciar transacción
        conn.execute("BEGIN TRANSACTION")
        
        # Limpiar tablas existentes
        cursor.execute("DELETE FROM ComposicionArticulo")
        cursor.execute("DELETE FROM ArticulosVendidos")
        
        # Restaurar artículos
        for articulo in data['articulos']:
            cursor.execute("""
                INSERT INTO ArticulosVendidos (id, nombre, categoria, subcategoria, 
                                     precio_venta, es_variante, articulo_padre_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                articulo['id'],
                articulo['nombre'],
                articulo['categoria'],
                articulo['subcategoria'],
                articulo['precio_venta'],
                1 if articulo['es_variante'] else 0,
                articulo['articulo_padre_id']
            ))
            
            # Restaurar composiciones
            for comp in articulo['composicion']:
                cursor.execute("""
                    INSERT INTO ComposicionArticulo (articulo_id, ingrediente_id, cantidad)
                    VALUES (?, ?, ?)
                """, (
                    articulo['id'],
                    comp['ingrediente_id'],
                    comp['cantidad']
                ))
        
        # Confirmar transacción
        conn.commit()
        print(f"Restauración completada. Se importaron {len(data['articulos'])} artículos.")
        return True
        
    except Exception as e:
        # Revertir cambios en caso de error
        conn.rollback()
        print(f"Error durante la restauración: {e}")
        return False

def main():
    """Función principal del script."""
    if len(sys.argv) < 2 or sys.argv[1] not in ['export', 'restore', 'check']:
        print("Uso:")
        print("  Para verificar BD:  python backup_restore_articulos.py check")
        print("  Para exportar:      python backup_restore_articulos.py export [archivo_salida.json]")
        print("  Para restaurar:     python backup_restore_articulos.py restore archivo_entrada.json")
        sys.exit(1)
    
    conn = get_db_connection()
    
    try:
        action = sys.argv[1]

        if action == 'check':
            check_database_structure(conn)
        
        elif action == 'export':
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
            export_articulos(conn, output_file)
            
        elif action == 'restore':
            if len(sys.argv) < 3:
                print("Error: Debe especificar el archivo JSON de entrada para restaurar")
                sys.exit(1)
            
            input_file = sys.argv[2]
            if not os.path.exists(input_file):
                print(f"Error: El archivo {input_file} no existe")
                sys.exit(1)
            
            restore_articulos(conn, input_file)
    
    finally:
        conn.close()

if __name__ == '__main__':
    main() 