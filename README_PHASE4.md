# Fase 4: Backend - Ventas y Cocina

Esta fase implementa las funcionalidades backend para el manejo de ventas y recepciones de cocina.

## Funcionalidad implementada

### Ventas
- **API de importación de ventas** 
   - POST `/api/ventas/importar`: Permite importar datos de ventas desde archivos CSV
   - Procesamiento de mapeo de columnas
   - Validación de datos
   - Reducción automática de inventario basada en la composición de los productos

- **API de consulta de ventas**
   - GET `/api/ventas`: Permite obtener el listado de ventas con filtrado y paginación

### Recepciones de Cocina
- **API de recepciones**
   - GET `/api/recepciones`: Permite obtener el listado de recepciones con filtrado y paginación
   - POST `/api/recepciones`: Permite registrar nuevas recepciones de ingredientes
   - GET `/api/recepciones/<id>`: Permite obtener detalles de una recepción específica
   - Actualización automática de inventario al registrar recepciones

## Cómo probar

### Requisitos previos
- Asegurarse de tener los módulos requeridos: `pip install requests`
- La aplicación debe estar corriendo
- Se necesitan datos en la base de datos para las pruebas

### Preparar datos de prueba
1. Si la base de datos está vacía o no tiene los datos necesarios, ejecuta:
   ```
   python populate_test_data.py
   ```
   Este script creará tablas, ingredientes, productos y sus composiciones si no existen.

### Ejecutar pruebas automáticas
1. Inicia la aplicación en una terminal:
   ```
   python app.py
   ```

2. En otra terminal, ejecuta el script de pruebas:
   ```
   python test_phase4.py
   ```

### Solución de problemas
Si encuentras errores durante las pruebas:
1. Asegúrate de que la aplicación esté corriendo en http://127.0.0.1:5000
2. Verifica que la base de datos tenga los datos necesarios ejecutando `populate_test_data.py`
3. Si el problema persiste, revisa los logs de error generados durante las pruebas

### Pruebas manuales con Postman o cURL

#### Importar ventas
```bash
curl -X POST -F "file=@test_data/test_sales.csv" http://127.0.0.1:5000/api/ventas/importar
```

#### Crear recepción
```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "ingrediente_id": 1,
  "cantidad_recibida": 5,
  "notas": "Prueba de recepción"
}' http://127.0.0.1:5000/api/recepciones
```

## Notas de implementación

- La importación de ventas actualiza automáticamente el inventario, reduciendo las cantidades de ingredientes según la composición de los productos vendidos.
- Las recepciones de cocina actualizan automáticamente el inventario, aumentando las cantidades de ingredientes recibidos.
- Todas las operaciones que afectan el inventario se realizan en transacciones para garantizar la integridad de los datos. 