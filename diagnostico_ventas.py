#!/usr/bin/env python
"""
Script de diagnóstico para las ventas en Inventario Zombie.
Este script verificará por qué las ventas siguen apareciendo después de resetear la base de datos.
"""

import os
import sqlite3
import json
import requests
from flask import Flask, jsonify
from database import get_db

# Configuración
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'inventario.db')
API_URL = "http://localhost:5000/api/ventas"

def check_sales_db():
    """Verifica los registros en la tabla Ventas."""
    print("\n=== Verificando base de datos de ventas ===")
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: La base de datos no existe en {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar si la tabla Ventas existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Ventas'")
        if not cursor.fetchone():
            print("ERROR: La tabla Ventas no existe en la base de datos")
            return False
        
        # Obtener conteo de registros
        cursor.execute("SELECT COUNT(*) as count FROM Ventas")
        count = cursor.fetchone()['count']
        print(f"Registros en la tabla Ventas: {count}")
        
        # Verificar estructura de la tabla
        cursor.execute("PRAGMA table_info(Ventas)")
        columns = cursor.fetchall()
        print(f"Número de columnas en la tabla Ventas: {len(columns)}")
        print("Columnas:")
        for col in columns:
            print(f"  - {col['name']} ({col['type']})")
        
        # Comprobar si hay datos en caché o memoria
        if count > 0:
            cursor.execute("SELECT * FROM Ventas LIMIT 3")
            ventas = cursor.fetchall()
            print("\nEjemplos de registros existentes:")
            for venta in ventas:
                print(f"  - ID: {venta['id']}, Fecha: {venta['fecha']}, Artículo: {venta['articulo']}")
        
        return True
    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
        return False
    finally:
        if conn:
            conn.close()

def check_api_response():
    """Intenta obtener datos de ventas de la API."""
    print("\n=== Verificando respuesta de la API ===")
    
    try:
        # Verificar si la API responde
        response = requests.get(API_URL, timeout=5)
        
        print(f"Código de estado HTTP: {response.status_code}")
        print(f"Tamaño de la respuesta: {len(response.content)} bytes")
        
        # Intentar parsear la respuesta como JSON
        try:
            data = response.json()
            print(f"Respuesta JSON válida: {'success' in data}")
            
            if 'success' in data and data['success']:
                print(f"Total de ventas en la respuesta: {data.get('total', 'No disponible')}")
                print(f"Cantidad de registros devueltos: {len(data.get('data', []))}")
                
                if len(data.get('data', [])) > 0:
                    print("\nEjemplos de ventas devueltas por la API:")
                    for i, venta in enumerate(data.get('data', [])[:3]):
                        print(f"  {i+1}. {venta.get('articulo', 'N/A')} - {venta.get('fecha', 'N/A')}")
            else:
                print(f"La API respondió con un error: {data.get('error', 'Error desconocido')}")
                
        except json.JSONDecodeError:
            print("La respuesta no es un JSON válido")
            print(f"Primeros 100 caracteres de la respuesta: {response.text[:100]}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API: {e}")
        print("¿Está corriendo el servidor Flask?")

def check_frontend_template():
    """Analiza la plantilla frontend para buscar posibles problemas."""
    print("\n=== Analizando la plantilla frontend ===")
    
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               'templates', 'ventas', 'lista.html')
    
    if not os.path.exists(template_path):
        print(f"ERROR: La plantilla no existe en {template_path}")
        return
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Verificar comportamiento cuando no hay datos
        if "noResultsMessage" in content:
            print("✓ La plantilla tiene un mensaje para 'sin resultados'")
        else:
            print("⚠️ La plantilla no tiene un mensaje visible para 'sin resultados'")
        
        # Verificar carga de datos del API
        if "/api/ventas" in content:
            print("✓ La plantilla hace referencia a la API de ventas")
            # Buscar el fetch específico a la API
            if "fetch(`/api/ventas" in content:
                print("✓ La plantilla usa fetch para cargar datos de la API")
            else:
                print("⚠️ No se encuentra la llamada fetch exacta a la API de ventas")
        else:
            print("⚠️ No se encuentra referencia a la API de ventas")
        
        # Verificar manejo del estado de carga
        if "loadingIndicator" in content:
            print("✓ La plantilla tiene un indicador de carga")
        else:
            print("⚠️ No se encuentra indicador de carga")
        
        # Verificar si tiene cachés o datos estáticos
        if "let salesData = []" in content:
            print("✓ La plantilla inicializa salesData como arreglo vacío")
        else:
            print("⚠️ No se encuentra inicialización de salesData o puede tener datos precargados")
            
        # Verificar filtros que podrían afectar la visualización
        filters = [
            "salesData = salesData.filter(sale => sale.subcategoria !== null)",
            "filter("
        ]
        
        for filter_text in filters:
            if filter_text in content:
                print(f"⚠️ FILTRO ENCONTRADO: '{filter_text}'")
                print("   Este filtro podría estar ocultando ventas o afectando la visualización")
        
    except Exception as e:
        print(f"Error al analizar la plantilla: {e}")

def main():
    """Función principal del diagnóstico."""
    print("======================================================")
    print("     DIAGNÓSTICO DE VENTAS - INVENTARIO ZOMBIE        ")
    print("======================================================")
    
    # Verificar base de datos
    db_ok = check_sales_db()
    
    # Verificar API
    check_api_response()
    
    # Verificar plantilla frontend
    check_frontend_template()
    
    print("\n=== RESUMEN DEL DIAGNÓSTICO ===")
    if not db_ok:
        print("❌ Hay problemas con la base de datos. Verifica los errores reportados arriba.")
    else:
        print("✓ La base de datos parece estar configurada correctamente.")
    
    print("\n=== POSIBLES SOLUCIONES ===")
    print("1. Si ves '⚠️ FILTRO ENCONTRADO: salesData = salesData.filter(sale => sale.subcategoria !== null)':")
    print("   - Este filtro está mostrando SOLO ventas de recibos (con variante).")
    print("   - Modifica la plantilla para mostrar todas las ventas, eliminando este filtro.")
    
    print("\n2. Verifica si hay datos en caché del navegador:")
    print("   - Limpia la caché del navegador o usa modo incógnito.")
    print("   - Presiona Ctrl+F5 para forzar una recarga completa de la página.")
    
    print("\n3. Reinicia el servidor Flask para asegurar que no haya datos en memoria.")
    
    print("\n4. Si la tabla Ventas está vacía pero siguen apareciendo ventas:")
    print("   - Puede ser un problema en la lógica de renderizado en el frontend.")
    print("   - Verifica si hay datos de ejemplo o test hardcodeados en el JavaScript.")

if __name__ == "__main__":
    main() 