import customtkinter as ctk
from datetime import date
import math
import re
import sqlite3
from datos.configuracion import RUTA_BD
from datetime import datetime

from servicios.elegibilidad import consultar_donante, FORMATO_FECHA

def mostrar_adonacion(pantalla, rol):
    if rol != "Entrevistador": #por ahora el personal es entrevistador, deveria ser enfermero
        from tkinter import messagebox
        messagebox.showerror("Acceso denegado", "No tiene autorización para registrar donaciones.")
        return
    frame_adonacion = ctk.CTkFrame(pantalla)
    frame_adonacion.place(relx=0,rely=0,relheight=1, relwidth=1)
    titulo = ctk.CTkLabel(frame_adonacion, text="Registro nueva donación", font=("Arial", 20, "bold"), text_color="#000000")
    titulo.place(relx=0.5, rely=0.07, anchor="center")

    frame_formulario_don = ctk.CTkFrame(frame_adonacion)
    frame_formulario_don.place(relx=0.5, rely=0.55, anchor="center")
    titulo_idDonante = ctk.CTkLabel(frame_formulario_don,text="IdDonante", text_color="#000000")
    titulo_idDonante.grid(row=0, column=0, padx=20, pady=5)
    idDonante= ctk.CTkEntry(frame_formulario_don, placeholder_text="Ingrese el Id del donante", width=250, height=40)
    idDonante.grid(row=1, column=0, padx=20, pady=5)

    titulo_litros = ctk.CTkLabel(frame_formulario_don,text="Litros", text_color="#000000")
    titulo_litros.grid(row=0, column=1, padx=20, pady=5)
    litros= ctk.CTkEntry(frame_formulario_don,placeholder_text="Ingrese el número de litros", width=250, height=40)
    litros.grid(row=1, column=1,padx=20, pady=5)

    mensaje_error = ctk.CTkLabel(frame_formulario_don, text="", text_color="red")
    mensaje_error.grid(row=12, column= 0, columnspan=2, pady=5)

    def agregar_donacion():
        id_ingresado = idDonante.get()
        litros_ingresados = litros.get()

        #validaciones de datos
        mensaje_error.configure(text="") 
        if not id_ingresado:
            mensaje_error.configure(text="Debe ingresar un ID")
            return
        if not litros_ingresados:
            mensaje_error.configure(text="Debe ingresar los litros")
            return
        if not id_ingresado.isdigit():
            mensaje_error.configure(text="El ID debe ser un número")
            return
        if not litros_ingresados.replace('.', '', 1).isdigit():
            mensaje_error.configure(text="Los litros deben ser un número")
            return
        try: # donante existe
            consultar_donante(id_ingresado)
        except ValueError as e:
            mensaje_error.configure(text=str(e))
            return
        
       
        fecha_extraccion_sql = date.today().isoformat()
        fecha_vencimiento_sql = (date.today().replace(day=date.today().day + 20)).isoformat()
        id_ingresado = int(id_ingresado)
        litros_ingresados = float(litros_ingresados)

        conexion = sqlite3.connect(RUTA_BD)
        cursor = conexion.cursor()


        cursor.execute("""INSERT INTO DONACIONES (DONANTE, CANTIDAD, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO)
            VALUES (?, ?, ?, ?)""", (id_ingresado, litros_ingresados, fecha_extraccion_sql, fecha_vencimiento_sql))

        id_donacion = cursor.lastrowid
        conexion.commit()
        conexion.close()
        mensaje_error.configure(
        text=f"Donacion registradq correctamente. ID: {id_donacion}",text_color="green")
        def mostrar_confirmacion(id_ingresado, litros_ingresados, fecha_extraccion_sql):
            frame_confirmacion = ctk.CTkFrame(pantalla)
            frame_confirmacion.place(relx=0, rely=0, relwidth=1, relheight=1)

            titulo = ctk.CTkLabel(frame_confirmacion,text="¡Donancion registrada correctamente!",font=("Arial", 26, "bold"))
            titulo.pack(pady=30)

            datos = ctk.CTkLabel(frame_confirmacion,text=f"ID del donante: {id_ingresado}\n"f"ID de donacion: {id_donacion}\n"f"Litros: {litros_ingresados}\n"f"Fecha: {fecha_extraccion_sql}\n"f"Fecha a vencer: {fecha_vencimiento_sql}",font=("Arial", 18),justify="left")
            datos.pack(pady=20)
        mostrar_confirmacion(id_ingresado,litros_ingresados,fecha_extraccion_sql)


    ingresar_donancion_boton = ctk.CTkButton(frame_formulario_don,text="Ingresar donacion",command= agregar_donacion, fg_color="red", hover_color="dimgray")
    ingresar_donancion_boton.grid(row = 13, column=0, columnspan=2, pady =20)