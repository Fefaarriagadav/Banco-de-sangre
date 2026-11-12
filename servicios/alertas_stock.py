import sqlite3
from datos.configuracion import RUTA_BD
from servicios.vencimientos import DISPONIBLE

def obtener_alertas_sobreabastecimiento():
    """H7-T1: Evalúa el stock disponible vs los umbrales y devuelve las alertas."""
    try:
        conexion = sqlite3.connect(RUTA_BD)
        cursor = conexion.cursor()
        
        # 1. Obtener stock actual de bolsas disponibles
        cursor.execute("""
            SELECT TIPO_SANGRE, FACTOR_RH, COUNT(ID) as STOCK_ACTUAL
            FROM DONACIONES 
            WHERE ESTADO = ?
            GROUP BY TIPO_SANGRE, FACTOR_RH
        """, (DISPONIBLE,))
        stock_agrupado = {f"{fila[0]}{fila[1]}": fila[2] for fila in cursor.fetchall()}
        
        # 2. Obtener umbrales
        cursor.execute("SELECT GRUPO_SANGUINEO, FACTOR_RH, UMBRAL_MAXIMO FROM UMBRALES")
        umbrales = cursor.fetchall()
        
        alertas = []
        for grupo, rh, umbral_max in umbrales:
            if umbral_max is None or umbral_max < 0:
                # Manejo de errores por datos de umbrales inválidos (Criterio de Aceptación 2)
                continue
                
            llave_sangre = f"{grupo}{rh}"
            stock_actual = stock_agrupado.get(llave_sangre, 0)
            
            # Criterio de Aceptación 1 y 3 (Solo alerta si supera el umbral)
            if stock_actual > umbral_max:
                excedente = stock_actual - umbral_max
                alertas.append({
                    "grupo": grupo,
                    "rh": rh,
                    "stock": stock_actual,
                    "umbral": umbral_max,
                    "excedente": excedente
                })
                
        conexion.close()
        return alertas
    except sqlite3.Error as e:
        raise ValueError("Error de base de datos al evaluar abastecimiento.")

def sugerir_redistribucion(grupo, rh):
    """H7-T2: Cruza el tipo de sangre excedente con los hospitales que lo necesitan."""
    try:
        conexion = sqlite3.connect(RUTA_BD)
        cursor = conexion.cursor()
        
        # Busca hospitales que requieran esa sangre y que pidan más de 0
        cursor.execute("""
            SELECT NOMBRE, DIRECCION, CANTIDAD_REQUERIDA 
            FROM HOSPITALES 
            WHERE GRUPO_SANGUINEO_REQUERIDO = ? 
            AND FACTOR_RH_REQUERIDO = ?
            AND CANTIDAD_REQUERIDA > 0
        """, (grupo, rh))
        
        destinos = cursor.fetchall()
        conexion.close()
        
        sugerencias = []
        for dest in destinos:
            sugerencias.append({
                "nombre": dest[0],
                "direccion": dest[1],
                "requiere": dest[2]
            })
            
        return sugerencias
    except sqlite3.Error:
        raise ValueError("Error al buscar sugerencias de destino.")