# Importador de Ingredientes para Inventario Zombie

Este script importa datos de ingredientes desde un archivo JSON al sistema de base de datos de Inventario Zombie.

## Características

- Importa ingredientes desde el archivo `ingredientes.json` a la base de datos SQLite
- Inicializa todas las cantidades de ingredientes a 0 (ignorando los valores del JSON)
- Determina automáticamente la unidad de medida apropiada basada en el tipo de ingrediente
- Estima precios razonables basados en la categoría del ingrediente y la unidad de medida
- Opcional: modo de prueba para verificar cambios sin modificar la base de datos
- Opcional: modo de forzar actualización de todos los ingredientes existentes

## Requisitos

- Python 3.6 o superior
- Flask (instalado en el entorno virtual)
- SQLite3
- Base de datos de Inventario Zombie ya inicializada

## Uso

```bash
# Activar el entorno virtual (si aplica)
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate     # En Windows

# Ver qué cambios se realizarían sin modificar la base de datos
python import_ingredientes.py --dryrun

# Importar los ingredientes (solo insertará nuevos y actualizará existentes)
python import_ingredientes.py

# Importar y forzar la actualización de todos los ingredientes
python import_ingredientes.py --force
```

## Opciones

- `--dryrun`: Muestra los cambios que se realizarían sin modificar la base de datos
- `--force`: Fuerza la actualización de todos los ingredientes, incluso si ya existen

## Estructura de datos esperada

El script espera un archivo JSON con la siguiente estructura:

```json
[
  {
    "name": "Nombre del Ingrediente",
    "quantity": 10.5,  // Este valor se ignora, siempre se inicializa a 0
    "minimum_stock": 5,
    "category": "Categoría"
  },
  ...
]
```

> **Nota importante**: Aunque el campo `quantity` en el JSON se utiliza para determinar la unidad de medida más apropiada, **todas las cantidades se inicializan a 0** en la base de datos. Esto permite un inventario inicial "limpio" que luego puede actualizarse manualmente o mediante recepción de ingredientes.

## Lógica para determinar unidades de medida

- Para ingredientes con nombres de líquidos (leche, aceite, agua, etc.):
  - Cantidades < 100: litros
  - Cantidades >= 100: mililitros
- Para otros ingredientes:
  - Cantidades < 100: kilogramos
  - Cantidades >= 100: gramos
- Casos especiales:
  - Bebidas en lata: unidades
  - Productos empaquetados (vasos, platos, etc.): unidades

## Lógica para estimar precios

Los precios se estiman basados en:
1. La categoría del ingrediente
2. La unidad de medida
3. Casos especiales basados en el nombre del ingrediente

Esto proporciona valores razonables para iniciar, que pueden ajustarse posteriormente en la interfaz de administración.

## Solución de problemas

Si el script no encuentra el archivo JSON, asegúrese de que `ingredientes.json` esté colocado en el directorio raíz del proyecto o en el mismo directorio que el script.

Si hay errores de conexión a la base de datos, verifique que la aplicación esté correctamente configurada y que la base de datos haya sido inicializada con `flask init-db`. 