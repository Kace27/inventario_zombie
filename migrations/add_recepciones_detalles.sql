-- Migration script to add RecepcionesDetalles table
PRAGMA foreign_keys=off;

-- Create the new table
CREATE TABLE IF NOT EXISTS RecepcionesDetalles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recepcion_id INTEGER NOT NULL,
    ingrediente_id INTEGER NOT NULL,
    cantidad_recibida REAL NOT NULL,
    FOREIGN KEY (recepcion_id) REFERENCES RecepcionesCocina (id) ON DELETE CASCADE,
    FOREIGN KEY (ingrediente_id) REFERENCES Ingredientes (id)
);

-- Create temporary table with new structure
CREATE TABLE RecepcionesCocina_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_recepcion TEXT NOT NULL,
    hora_recepcion TEXT NOT NULL,
    notas TEXT
);

-- Copy data to new table
INSERT INTO RecepcionesCocina_new (id, fecha_recepcion, hora_recepcion, notas)
SELECT id, fecha_recepcion, hora_recepcion, notas
FROM RecepcionesCocina;

-- Migrate existing data to RecepcionesDetalles
INSERT INTO RecepcionesDetalles (recepcion_id, ingrediente_id, cantidad_recibida)
SELECT id, ingrediente_id, cantidad_recibida
FROM RecepcionesCocina
WHERE ingrediente_id IS NOT NULL AND cantidad_recibida IS NOT NULL;

-- Drop old table
DROP TABLE RecepcionesCocina;

-- Rename new table
ALTER TABLE RecepcionesCocina_new RENAME TO RecepcionesCocina;

PRAGMA foreign_keys=on; 