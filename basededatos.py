import sqlite3 

conexion = sqlite3.connect("BancoDeSangre.db") # conecta con la base de datos "bancoDeSangre" (si no existe, la crea)
cursor = conexion.cursor()

def existencia_tabla(nombre_tabla):
    cursor.execute('''SELECT COUNT(name) FROM SQLITE_MASTER WHERE TYPE = 'table' AND name = '{}' '''.format(nombre_tabla,))
    if cursor.fetchone()[0] == 1:
        return True
    elif nombre_tabla == "DONANTES":
        cursor.execute(''' CREATE TABLE DONANTES (ID INTEGER PRIMARY KEY AUTOINCREMENT, NOMBRE TEXT NOT NULL, APELLIDO TEXT NOT NULL, EDAD INTEGER NOT NULL, SEXO TEXT NOT NULL CHECK(SEXO IN ('Masculino', 'Femenino')), GRUPO_SANGUINEO TEXT NOT NULL CHECK(GRUPO_SANGUINEO IN ('A','B','AB','O')), FACTOR_RH TEXT NOT NULL CHECK(FACTOR_RH IN ('+', '-')), FECHA_ULTIMA_DONACION TEXT, PESO REAL NOT NULL, EMAIL TEXT NOT NULL, ELEGIBLE TEXT NOT NULL CHECK(ELEGIBLE IN ('Donante apto', 'Donante NO apto temporalmente', 'Donante NO apto PERMANENTEMENTE')), FECHA_DE_NACIMIENTO TEXT NOT NULL)''')
    elif nombre_tabla == "DONACIONES":
        cursor.execute(''' CREATE TABLE DONACIONES (ID INTEGER PRIMARY KEY AUTOINCREMENT, DONANTE INTEGER, TIPO_SANGRE TEXT CHECK(TIPO_SANGRE IN ('A','B','AB','O')), FACTOR_RH TEXT CHECK(FACTOR_RH IN ('+', '-')), FECHA_EXTRACCIÓN TEXT, FECHA_VENCIMIENTO TEXT,CANTIDAD INTEGER, UBICACION TEXT, FOREIGN KEY(DONANTE) REFERENCES DONANTES(ID))''')
    elif nombre_tabla == "PERSONAL":
        cursor.execute(''' CREATE TABLE PERSONAL (ID_EMPLEADO INTEGER PRIMARY KEY AUTOINCREMENT, RUT TEXT UNIQUE, NOMBRE TEXT, FECHA_NACIMIENTO TEXT, TURNO TEXT, ROL TEXT CHECK(ROL IN ('Entrevistador','Enfermero')), BOX_ATENCION TEXT, REGISTRO_SALUD TEXT)''')

        return False

tabla_donantes = existencia_tabla("DONANTES") # verifica si la tabla "donantes" existe, si no, la crea
tabla_donaciones = existencia_tabla("DONACIONES") # verifica si la tabla "donaciones" existe, si no, la crea
tabla_personal = existencia_tabla("PERSONAL") # verifica si la tabla "personal" existe, si no, la crea

conexion.commit() # guarda los cambios en la base de datos
conexion.close() # cierra la conexión con la base de datos