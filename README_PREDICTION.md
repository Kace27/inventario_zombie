# Módulo de Predicción de Ventas

Este módulo implementa una funcionalidad de predicción de ventas basada en datos históricos, analizando patrones por día de la semana.

## Funcionamiento

El sistema de predicción analiza el historial de ventas para un día de la semana específico (por ejemplo, para predecir las ventas de un martes, analiza los datos de ventas de martes anteriores). La predicción se basa en calcular el promedio de ventas para cada artículo en días similares.

## Componentes principales

1. **SalesPredictor**: Clase principal que implementa la lógica de predicción (`utils/sales_predictor.py`)
2. **API Endpoints**: Rutas para acceder a las predicciones (`routes/ventas.py`)
3. **Script de prueba**: Herramienta para probar la funcionalidad (`test_sales_prediction.py`)

## API Endpoints

### 1. Predicción Básica

```
GET /api/ventas/prediccion
```

Parámetros de consulta:
- `fecha`: Fecha objetivo para la predicción (YYYY-MM-DD). Por defecto es mañana.
- `num_semanas`: Número de semanas anteriores a analizar. Por defecto es 4.
- `categoria`: Filtro opcional por categoría.
- `articulo`: Filtro opcional por artículo.

Ejemplo de respuesta:
```json
{
  "success": true,
  "data": {
    "target_date": "2023-07-15",
    "weekday": 5,
    "weekday_name": "Sábado",
    "predictions": {
      "Café americano": {
        "predicted_sales": 45.25,
        "historical_data": [42, 46, 48, 45],
        "num_weeks": 4
      },
      "Pastel de chocolate": {
        "predicted_sales": 23.75,
        "historical_data": [22, 25, 24, 24],
        "num_weeks": 4
      }
    },
    "total_predicted": 69.0,
    "num_weeks_analyzed": 4
  }
}
```

### 2. Predicción Avanzada

```
POST /api/ventas/prediccion-avanzada
```

Cuerpo de la petición:
```json
{
  "fechas": ["2023-07-15", "2023-07-16"],
  "dias_semana": [0, 1, 2],
  "num_semanas": 4,
  "categorias": ["Bebidas", "Postres"],
  "articulos": ["Café americano", "Pastel de chocolate"],
  "agrupar_por": "categoria"
}
```

Parámetros:
- `fechas`: Lista de fechas objetivo para predicción (YYYY-MM-DD).
- `dias_semana`: Lista de días de la semana (0=Lunes, 6=Domingo).
- `num_semanas`: Número de semanas anteriores a analizar.
- `categorias`: Lista de categorías para filtrar.
- `articulos`: Lista de artículos para filtrar.
- `agrupar_por`: Agrupar resultados por "categoria", "dia" o "articulo".

Ejemplo de respuesta (agrupada por categoría):
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_predicted": 520.5,
      "dates_analyzed": 2,
      "num_weeks_analyzed": 4
    },
    "grouped_by": "categoria",
    "predictions": [
      {
        "categoria": "Bebidas",
        "total_predecido": 350.75,
        "articulos": {
          "Café americano": 120.5,
          "Té verde": 89.25,
          "Agua mineral": 141.0
        }
      },
      {
        "categoria": "Postres",
        "total_predecido": 169.75,
        "articulos": {
          "Pastel de chocolate": 85.25,
          "Flan": 84.5
        }
      }
    ]
  }
}
```

## Uso desde código

```python
from utils.sales_predictor import SalesPredictor

# Crear instancia
predictor = SalesPredictor()

# Predecir ventas para una fecha específica
prediction = predictor.predict_sales_for_date('2023-07-15')

# Predecir ventas para un día de la semana específico
prediction = predictor.predict_sales_for_weekday(5)  # 5 = Sábado

# Cerrar la conexión cuando haya terminado
predictor.close()
```

## Script de prueba

Para probar la funcionalidad, ejecute:

```bash
python test_sales_prediction.py
```

Este script realiza predicciones para diferentes escenarios y muestra los resultados.

## Consideraciones

- La precisión de las predicciones depende de la cantidad y calidad de los datos históricos disponibles.
- Se recomienda tener al menos 4 semanas de datos históricos para obtener predicciones más precisas.
- El sistema puede mejorarse en el futuro incorporando factores adicionales como eventos especiales, temporadas, clima, etc. 