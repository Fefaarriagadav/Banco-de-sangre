import sqlite3
from datos.configuracion import RUTA_BD
from servicios.vencimientos import migrar


def inicializar_base(ruta=RUTA_BD):
    conexion = sqlite3.connect(ruta) # conecta con la base de datos "bancoDeSangre" (si no existe, la crea)
    cursor = conexion.cursor()
    
    def existencia_tabla(nombre_tabla):
        cursor.execute('''SELECT COUNT(name) FROM SQLITE_MASTER WHERE TYPE = 'table' AND name = '{}' '''.format(nombre_tabla,))
        if cursor.fetchone()[0] == 1:
            return True
        elif nombre_tabla == "DONANTES": #atributos de la tabla de donantes, todos sus campos y con el tipo de dato que acepta
            cursor.execute(''' CREATE TABLE DONANTES (ID INTEGER PRIMARY KEY AUTOINCREMENT, NOMBRE TEXT NOT NULL, APELLIDO TEXT NOT NULL, EDAD INTEGER NOT NULL, SEXO TEXT NOT NULL CHECK(SEXO IN ('Masculino', 'Femenino')), GRUPO_SANGUINEO TEXT NOT NULL CHECK(GRUPO_SANGUINEO IN ('A','B','AB','O')), FACTOR_RH TEXT NOT NULL CHECK(FACTOR_RH IN ('+', '-')), FECHA_ULTIMA_DONACION TEXT, PESO REAL NOT NULL, EMAIL TEXT NOT NULL, ELEGIBLE TEXT NOT NULL CHECK(ELEGIBLE IN ('Donante apto', 'Donante NO apto temporalmente', 'Donante NO apto PERMANENTEMENTE')), FECHA_DE_NACIMIENTO TEXT NOT NULL)''')
        elif nombre_tabla == "DONACIONES": #atributos de la tabla de donaciones, todos sus campos y con el tipo de dato que acepta
            cursor.execute(''' CREATE TABLE DONACIONES (ID INTEGER PRIMARY KEY AUTOINCREMENT, DONANTE INTEGER, TIPO_SANGRE TEXT CHECK(TIPO_SANGRE IN ('A','B','AB','O')), FACTOR_RH TEXT CHECK(FACTOR_RH IN ('+', '-')), FECHA_EXTRACCIÓN TEXT, FECHA_VENCIMIENTO TEXT, CANTIDAD INTEGER, UBICACION TEXT, FOREIGN KEY(DONANTE) REFERENCES DONANTES(ID))''') #funcion proximo sprint APTA TEXT CHECK(APTA IN ('Si', 'No(Vencida)', 'No(Usada)'))
        elif nombre_tabla == "PERSONAL": #atributos de la tabla de personal, todos sus campos y con el tipo de dato que acepta
            cursor.execute(''' CREATE TABLE PERSONAL (ID_EMPLEADO INTEGER PRIMARY KEY AUTOINCREMENT, RUT TEXT UNIQUE, NOMBRE TEXT, FECHA_NACIMIENTO TEXT, TURNO TEXT, ROL TEXT CHECK(ROL IN ('Entrevistador','Enfermero')), BOX_ATENCION TEXT, REGISTRO_SALUD TEXT)''')
        elif nombre_tabla == "UMBRALES": 
            cursor.execute(''' CREATE TABLE UMBRALES (ID INTEGER PRIMARY KEY AUTOINCREMENT, GRUPO_SANGUINEO TEXT NOT NULL, FACTOR_RH TEXT NOT NULL, UMBRAL_MAXIMO INTEGER NOT NULL)''')
            return False
        elif nombre_tabla == "HOSPITALES": 
            cursor.execute(''' CREATE TABLE HOSPITALES (ID INTEGER PRIMARY KEY AUTOINCREMENT, NOMBRE TEXT NOT NULL, DIRECCION TEXT, GRUPO_SANGUINEO_REQUERIDO TEXT, FACTOR_RH_REQUERIDO TEXT, CANTIDAD_REQUERIDA INTEGER)''')                        # Integer primary key autoincrement, significa que se autocrera un numero y este se autoincrementara mientras se agreguen personas o donaciones
            return False
    
    tabla_donantes = existencia_tabla("DONANTES") # verifica si la tabla "donantes" existe, si no, la crea
    tabla_donaciones = existencia_tabla("DONACIONES") # verifica si la tabla "donaciones" existe, si no, la crea
    tabla_personal = existencia_tabla("PERSONAL") # verifica si la tabla "personal" existe, si no, la crea
    tabla_umbrales = existencia_tabla("UMBRALES")
    tabla_hospitales = existencia_tabla("HOSPITALES")

    # H7: Inyectar datos semilla para UMBRALES si la tabla es nueva
    if not tabla_umbrales:
        grupos = ['A', 'B', 'AB', 'O']
        rhs = ['+', '-']
        for g in grupos:
            for r in rhs:
                # Umbral base fijado en 5 para facilitar la visualización de excedentes
                cursor.execute("INSERT INTO UMBRALES (GRUPO_SANGUINEO, FACTOR_RH, UMBRAL_MAXIMO) VALUES (?, ?, ?)", (g, r, 5))
                
    # H7: Inyectar datos semilla para HOSPITALES si la tabla es nueva
    if not tabla_hospitales:
        cursor.execute("INSERT INTO HOSPITALES (NOMBRE, DIRECCION, GRUPO_SANGUINEO_REQUERIDO, FACTOR_RH_REQUERIDO, CANTIDAD_REQUERIDA) VALUES ('Hospital Guillermo Grant Benavente', 'Concepción', 'O', '+', 10)")
        cursor.execute("INSERT INTO HOSPITALES (NOMBRE, DIRECCION, GRUPO_SANGUINEO_REQUERIDO, FACTOR_RH_REQUERIDO, CANTIDAD_REQUERIDA) VALUES ('Clínica Biobío', 'Talcahuano', 'A', '+', 5)")
        cursor.execute("INSERT INTO HOSPITALES (NOMBRE, DIRECCION, GRUPO_SANGUINEO_REQUERIDO, FACTOR_RH_REQUERIDO, CANTIDAD_REQUERIDA) VALUES ('Hospital Las Higueras', 'Talcahuano', 'O', '-', 3)")
    # H4: período de inhabilitación temporal e historial de cambios
    # agrega las columnas solo si aún no existen (no borra datos).
    columnas = [fila[1] for fila in cursor.execute("PRAGMA table_info(DONANTES)")]
    if "INHABILITACION_INICIO" not in columnas:
        cursor.execute("ALTER TABLE DONANTES ADD COLUMN INHABILITACION_INICIO TEXT")
    if "INHABILITACION_FIN" not in columnas:
        cursor.execute("ALTER TABLE DONANTES ADD COLUMN INHABILITACION_FIN TEXT")
    cursor.execute('''CREATE TABLE IF NOT EXISTS HISTORIAL_HABILITACION (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        DONANTE_ID INTEGER NOT NULL REFERENCES DONANTES(ID),
        ESTADO_ANTERIOR TEXT,
        ESTADO_NUEVO TEXT NOT NULL,
        FECHA_INICIO TEXT,
        FECHA_FIN TEXT,
        EMPLEADO_ID INTEGER NOT NULL REFERENCES PERSONAL(ID_EMPLEADO),
        FECHA_CAMBIO TEXT NOT NULL)''')
    
    migrar(conexion) #H6 agrega ESTADO e índice de vencimiento sin borrar datos previos

    conexion.commit() # guarda los cambios en la base de datos
    conexion.close() # cierra la conexión con la base de datos