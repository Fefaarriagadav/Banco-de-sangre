import customtkinter as ctk
import sqlite3
from datos.configuracion import RUTA_BD

from servicios.donaciones import registrar_donacion
from servicios.vencimientos import fecha_actual

def mostrar_adonacion(pantalla, rol, empleado_id):
    if rol != "Enfermero":
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

    titulo_cc = ctk.CTkLabel(frame_formulario_don,text="CC", text_color="#000000")
    titulo_cc.grid(row=0, column=1, padx=20, pady=5)
    cc= ctk.CTkEntry(frame_formulario_don,placeholder_text="Ingrese la cantidad de sangre(cc)", width=250, height=40)
    cc.grid(row=1, column=1,padx=20, pady=5)

    mensaje_error = ctk.CTkLabel(frame_formulario_don, text="", text_color="red")
    mensaje_error.grid(row=12, column= 0, columnspan=2, pady=5)

    def agregar_donacion():
        id_ingresado = idDonante.get()
        cc_ingresados = cc.get()

        #validaciones de datos
        mensaje_error.configure(text="") 
        if not id_ingresado:
            mensaje_error.configure(text="Debe ingresar un ID")
            return
        if not cc_ingresados:
            mensaje_error.configure(text="Debe ingresar la cantidad")
            return
        if not id_ingresado.isdigit():
            mensaje_error.configure(text="El ID debe ser un número")
            return
        if not cc_ingresados.replace('.', '', 1).isdigit():
            mensaje_error.configure(text="La cantidad deben ser un número")
            return
        if float(cc_ingresados) < 0.1 or float(cc_ingresados) > 450:
            mensaje_error.configure(text="La cantidad debe estar entre 0.1 y 450 cc")
            return
        try:
            donacion = registrar_donacion(id_ingresado, cc_ingresados, empleado_id,
                                          ruta=RUTA_BD, hoy=fecha_actual())
        except (ValueError, PermissionError) as e:
            mensaje_error.configure(text=str(e))
            return
        except sqlite3.Error:
            mensaje_error.configure(text="No se pudo registrar la donación. Intente nuevamente.")
            return
        id_donacion = donacion["ID"]
        id_ingresado = donacion["DONANTE"]
        cc_ingresados = donacion["CANTIDAD"]
        fecha_extraccion_sql = donacion["FECHA_EXTRACCION"]
        fecha_vencimiento_sql = donacion["FECHA_VENCIMIENTO"]
        rh_donacion = donacion["FACTOR_RH"]
        tipo_donacion = donacion["GRUPO_SANGUINEO"]
        ubicacion_asignada = donacion["UBICACION"]
        mensaje_error.configure(
        text=f"Donacion registrada correctamente. ID: {id_donacion}",text_color="green")
        def mostrar_confirmacion(id_ingresado, cc_ingresados, fecha_extraccion_sql):
            frame_confirmacion = ctk.CTkFrame(pantalla)
            frame_confirmacion.place(relx=0, rely=0, relwidth=1, relheight=1)

            titulo = ctk.CTkLabel(frame_confirmacion,text="¡Donancion registrada correctamente!",font=("Arial", 26, "bold"))
            titulo.pack(pady=30)

            datos = ctk.CTkLabel(frame_confirmacion,text=f"ID del donante: {id_ingresado}\n"f"ID de donacion: {id_donacion}\n"f"CC: {cc_ingresados}\n"f"Fecha: {fecha_extraccion_sql}\n"f"Fecha a vencer: {fecha_vencimiento_sql}\n"f"Rh: {rh_donacion}\n"f"Grupo: {tipo_donacion}\n"f"Guardar en: {ubicacion_asignada}",font=("Arial", 18),justify="left")
            datos.pack(pady=20)
            ctk.CTkLabel(frame_confirmacion,
                         text="Donante NO apto temporalmente.\nFecha de habilitación: "
                              + donacion["FECHA_HABILITACION"],
                         font=("Arial", 18)).pack(pady=10)
        mostrar_confirmacion(id_ingresado,cc_ingresados,fecha_extraccion_sql)


    ingresar_donancion_boton = ctk.CTkButton(frame_formulario_don,text="Ingresar donacion",command= agregar_donacion, fg_color="red", hover_color="dimgray")
    ingresar_donancion_boton.grid(row = 13, column=0, columnspan=2, pady =20)