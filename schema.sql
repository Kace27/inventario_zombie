DROP TABLE IF EXISTS Ingredientes;
DROP TABLE IF EXISTS ArticulosVendidos;
DROP TABLE IF EXISTS ComposicionArticulo;
DROP TABLE IF EXISTS Ventas;
DROP TABLE IF EXISTS RecepcionesCocina;
DROP TABLE IF EXISTS AjustesInventario;
DROP TABLE IF EXISTS Usuarios;
DROP TABLE IF EXISTS LoginAttempts;
DROP TABLE IF EXISTS RecibosImportados;
DROP TABLE IF EXISTS ReglasVariantes;

CREATE TABLE Ingredientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    unidad_medida TEXT NOT NULL,
    precio_compra REAL,
    cantidad_actual REAL NOT NULL DEFAULT 0,
    stock_minimo REAL,
    categoria TEXT
);

CREATE TABLE ArticulosVendidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    subcategoria TEXT,
    precio_venta REAL,
    articulo_padre_id INTEGER,
    es_variante BOOLEAN DEFAULT 0,
    FOREIGN KEY (articulo_padre_id) REFERENCES ArticulosVendidos (id)
);

CREATE TABLE ReglasVariantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patron_principal TEXT NOT NULL,
    patron_variante TEXT NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT 1
);

CREATE TABLE ComposicionArticulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    articulo_id INTEGER NOT NULL,
    ingrediente_id INTEGER NOT NULL,
    cantidad REAL NOT NULL,
    FOREIGN KEY (articulo_id) REFERENCES ArticulosVendidos (id),
    FOREIGN KEY (ingrediente_id) REFERENCES Ingredientes (id)
);

CREATE TABLE Ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    ticket TEXT,
    empleado TEXT,
    mesa TEXT,
    comensales INTEGER,
    articulo TEXT NOT NULL,
    categoria TEXT,
    subcategoria TEXT,
    precio_unitario REAL,
    articulos_vendidos INTEGER NOT NULL,
    iva REAL,
    propina REAL,
    total REAL,
    costo_estimado REAL,
    ganancia_estimada REAL,
    porcentaje_ganancia REAL
);

CREATE TABLE RecibosImportados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_recibo TEXT NOT NULL UNIQUE,
    fecha_importacion TEXT NOT NULL,
    fecha_recibo TEXT NOT NULL
);

CREATE TABLE RecepcionesCocina (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingrediente_id INTEGER NOT NULL,
    cantidad_recibida REAL NOT NULL,
    fecha_recepcion TEXT NOT NULL,
    hora_recepcion TEXT NOT NULL,
    notas TEXT,
    FOREIGN KEY (ingrediente_id) REFERENCES Ingredientes (id)
);

CREATE TABLE AjustesInventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingrediente_id INTEGER NOT NULL,
    cantidad_ajustada REAL NOT NULL,
    motivo TEXT,
    fecha_ajuste TEXT NOT NULL,
    FOREIGN KEY (ingrediente_id) REFERENCES Ingredientes (id)
);

CREATE TABLE Usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    contrasena_hash TEXT NOT NULL,
    pin TEXT,
    rol TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT 1,
    fecha_creacion TEXT NOT NULL,
    ultimo_acceso TEXT,
    intentos_fallidos INTEGER DEFAULT 0
);

CREATE TABLE LoginAttempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT NOT NULL,
    ip_address TEXT,
    timestamp TEXT NOT NULL,
    exito BOOLEAN NOT NULL
); 