# Inventario Zombie
Aplicación web para gestión de inventario y ventas en cocina

## Descripción

Inventario Zombie es una aplicación web diseñada para optimizar la gestión de inventario de ingredientes y el registro de ventas en un entorno de cocina. La aplicación consta de tres módulos principales:

- **Interfaz para Cocina**: Registro de recepción de artículos
- **Interfaz de Administrador (Ventas)**: Importación y análisis de datos de ventas
- **Interfaz de Administrador (Inventario)**: Gestión de ingredientes y productos

## Requisitos

- Python 3.8 o superior
- Pip (gestor de paquetes de Python)
- SQLite 3

## Instalación

1. Clonar el repositorio:
   ```
   git clone <url-del-repositorio>
   cd inventario_zombie
   ```

2. Crear un entorno virtual y activarlo:
   ```
   python -m venv venv
   
   # En Windows
   venv\Scripts\activate
   
   # En macOS/Linux
   source venv/bin/activate
   ```

3. Instalar las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Crear un archivo `.env` basado en `.env-example`:
   ```
   cp .env-example .env
   ```

5. Inicializar la base de datos:
   ```
   flask init-db
   ```

## Ejecución

Para ejecutar la aplicación en modo desarrollo:

```
flask run
```

La aplicación estará disponible en http://127.0.0.1:5000/

## Estructura del Proyecto

```
inventario_zombie/
├── app.py                     # Punto de entrada principal de Flask
├── config.py                  # Configuración de la aplicación
├── database.py                # Utilidades de base de datos
├── schema.sql                 # Esquema de la base de datos SQLite
├── utils/                     # Utilidades generales
│   ├── validators.py          # Validaciones de entrada
│   ├── csv_parser.py          # Funcionalidad de importación CSV
│   └── inventory.py           # Utilidades de cálculo de inventario
├── routes/                    # Rutas de API
│   ├── ingredientes.py        # Endpoints de API de ingredientes
│   ├── articulos.py           # Endpoints de API de productos
│   ├── ventas.py              # Importación y visualización de ventas
│   ├── recepciones.py         # Funcionalidad de recepción en cocina
│   └── reportes.py            # Endpoints de reportes
├── templates/                 # Plantillas HTML
│   ├── layout.html            # Plantilla base
│   ├── index.html             # Página de inicio
│   ├── ingredientes/          # Plantillas de gestión de ingredientes
│   ├── articulos/             # Plantillas de gestión de productos
│   ├── ventas/                # Plantillas de gestión de ventas
│   ├── recepciones/           # Plantillas de recepción en cocina
│   └── reportes/              # Plantillas de reportes
└── static/                    # Archivos estáticos
    ├── css/                   # Hojas de estilo
    │   └── main.css           # Hoja de estilo principal
    └── js/                    # JavaScript
        ├── main.js            # JavaScript principal
        ├── api.js             # Utilidades de comunicación con API
        └── forms.js           # Utilidades de manejo de formularios
```

## Desarrollo

Para contribuir al proyecto, por favor sigue estos pasos:

1. Crea una rama para tu funcionalidad: `git checkout -b feature/nombre-funcionalidad`
2. Realiza los cambios y haz commit: `git commit -m 'Añadir nueva funcionalidad'`
3. Sube los cambios a tu rama: `git push origin feature/nombre-funcionalidad`
4. Envía un Pull Request

## Licencia

[MIT](LICENSE)
