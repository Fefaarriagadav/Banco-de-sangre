import customtkinter as ctk
from datetime import date
import math
import re
import sqlite3
from datos.configuracion import RUTA_BD
from datetime import datetime

def mostrar_registro(pantalla, rol):
    if rol != "Entrevistador":
        from tkinter import messagebox
        messagebox.showerror("Acceso denegado", "No tiene autorización para registrar donantes")
        return
    frame_donante = ctk.CTkFrame(pantalla)
    frame_donante.place(relx=0,rely=0,relheight=1, relwidth=1)
    titulo = ctk.CTkLabel(frame_donante, text="Registro nuevo donante", font=("Arial", 20, "bold"), text_color="#000000")
    titulo.place(relx=0.5, rely=0.07, anchor="center")

    frame_formulario = ctk.CTkFrame(frame_donante)
    frame_formulario.place(relx=0.5, rely=0.55, anchor="center")
    titulo_nombre = ctk.CTkLabel(frame_formulario,text="Nombre", text_color="#000000")
    titulo_nombre.grid(row=0, column=0, padx=20, pady=5)
    nombre= ctk.CTkEntry(frame_formulario, placeholder_text="Ingrese el nombre", width=250, height=40)
    nombre.grid(row=1, column=0, padx=20, pady=5)

    titulo_apellido = ctk.CTkLabel(frame_formulario,text="Apellido", text_color="#000000")
    titulo_apellido.grid(row=0, column=1, padx=20, pady=5)
    apellido= ctk.CTkEntry(frame_formulario,placeholder_text="Ingrese el apellido", width=250, height=40)
    apellido.grid(row=1, column=1,padx=20, pady=5)

    titulo_fdn = ctk.CTkLabel(frame_formulario,text="Fecha de nacimiento", text_color="#000000")
    titulo_fdn.grid(row=2, column =0, columnspan=2, padx=20, pady=(8,3))

    frame_fecha = ctk.CTkFrame(frame_formulario,fg_color="transparent")
    frame_fecha.grid(row=3, column=0, columnspan=2, pady=5)

    dias = [str(dia) for dia in range (1,32)]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    años = [str(año) for año in range(1920,2027)]

    titulo_dia = ctk.CTkLabel(frame_fecha, text="Día", text_color="#000000")
    titulo_dia.grid(row= 0, column=0, padx=20, pady=5)

    titulo_mes= ctk.CTkLabel(frame_fecha, text="Mes", text_color="#000000")
    titulo_mes.grid(row=0, column=1, padx=20, pady=5)

    titulo_año= ctk.CTkLabel(frame_fecha, text="Año", text_color="#000000")
    titulo_año.grid(row=0, column=2, padx=20, pady=5)

    menu_dia = ctk.CTkOptionMenu(frame_fecha,values=dias,width=100)
    menu_dia.set("Seleccione")
    menu_dia.grid(row=1, column=0, padx=5)
    menu_mes = ctk.CTkOptionMenu(frame_fecha,values=meses,width=100)
    menu_mes.set("Seleccione")
    menu_mes.grid(row=1, column=1, padx=5)
    menu_año = ctk.CTkOptionMenu(frame_fecha,values=años,width=100)
    menu_año.set("Seleccione")
    menu_año.grid(row=1, column=2, padx=5)

    titulo_ts = ctk.CTkLabel(frame_formulario,text="Tipo de sangre", text_color="#000000")
    titulo_ts.grid(row=4, column=0, padx=20, pady=5)
    sangres= ["A","B","AB","O"]
    ts= ctk.CTkOptionMenu(frame_formulario, values=sangres, width=250, height=40)
    ts.set("Seleccione")
    ts.grid(row=5, column=0, padx=20, pady=5)
    
    titulo_frh = ctk.CTkLabel(frame_formulario,text="Factor Rh", text_color="#000000")
    titulo_frh.grid(row=4, column=1, padx=20, pady=5)
    factor_rh= ctk.CTkOptionMenu(frame_formulario,values=["Positivo", "Negativo"], width=250, height=40)
    factor_rh.set("Seleccione")
    factor_rh.grid(row=5, column=1,padx=20, pady=5)

    titulo_sexo = ctk.CTkLabel(frame_formulario,text="Sexo", text_color="#000000")
    titulo_sexo.grid(row=6, column=0, padx=20, pady=5)
    sexos= ["Femenino","Masculino"]
    sexo= ctk.CTkOptionMenu(frame_formulario, values=sexos, width=250, height=40)
    sexo.set("Seleccione")
    sexo.grid(row=7, column=0, padx=20, pady=5)
        
    titulo_peso = ctk.CTkLabel(frame_formulario,text="Peso", text_color="#000000")
    titulo_peso.grid(row=6, column=1, padx=20, pady=5)
    peso= ctk.CTkEntry(frame_formulario,placeholder_text="Ingrese el peso", width=250, height=40)
    peso.grid(row=7, column=1,padx=20, pady=5)

    titulo_email = ctk.CTkLabel(frame_formulario,text="Email", text_color="#000000")
    titulo_email.grid(row=8, column =0, columnspan=2, padx=20, pady=(20,5))
    email = ctk.CTkEntry(frame_formulario,placeholder_text="Ingrese email@dirección.cl/com",width=300, height=40)
    email.grid(row=9, column=0, columnspan=2, pady=5)

    titulo_elegibilidad = ctk.CTkLabel(frame_formulario,text="Elegibilidad", text_color="#000000")
    titulo_elegibilidad.grid(row=10, column=0, padx=20, pady=5)
    elegibilidad= ctk.CTkOptionMenu(frame_formulario, values=["Donante apto", "Donante NO apto temporalmente", "Donante NO apto PERMANENTEMENTE"], width=250, height=40)
    elegibilidad.set("Seleccione")
    elegibilidad.grid(row=11, column=0, padx=20, pady=5)
            
    titulo_ult_don = ctk.CTkLabel(frame_formulario,text="Ultima donacion", text_color="#000000")
    titulo_ult_don.grid(row=10, column=1, padx=20, pady=5)
    ult_don= ctk.CTkEntry(frame_formulario,placeholder_text="DD-MM-AAAA", width=250, height=40)
    ult_don.grid(row=11, column=1,padx=20, pady=5)

    mensaje_error = ctk.CTkLabel(frame_formulario, text="", text_color="red")
    mensaje_error.grid(row=12, column= 0, columnspan=2, pady=5)

    def agregar_donante():
        nombre_ingresado = nombre.get().strip().capitalize()
        apellido_ingresado = apellido.get().strip().capitalize()
        dia_ingresado = menu_dia.get()
        mes_ingresado = menu_mes.get()
        año_ingresado = menu_año.get()
        ts_ingresado = ts.get()
        rh_ingresado = factor_rh.get()
        sexo_ingresado = sexo.get()
        email_ingresado = email.get().strip()
        elegibilidad_ingresada = elegibilidad.get()
        peso_ingresado = peso.get().strip()
        ult_don_ingresada= ult_don.get()

        #validaciones de datos
        mensaje_error.configure(text="") 
        if not nombre_ingresado:
            mensaje_error.configure(text="Debe ingresra un nombre")
            return
        if not apellido_ingresado:
            mensaje_error.configure(text="Debe ingresar un apellido")
            return
        if (dia_ingresado == "Seleccione" or mes_ingresado == "Seleccione" or año_ingresado == "Seleccione"):
            mensaje_error.configure(text="Debe ingresar la fecha de nacimiento completa")
            return
        dia_ingresado = int(dia_ingresado)
        mes_ingresado = meses.index(mes_ingresado) + 1
        año_ingresado = int(año_ingresado)
        try :
            fecha_de_nacimiento= date(año_ingresado,mes_ingresado,dia_ingresado)
        except ValueError:
            mensaje_error.configure(text="La fecha de nacimiento no es valida")
            return
        hoy = date.today()
        if fecha_de_nacimiento > hoy:
            mensaje_error.configure(text="La fecha de nacimiento no puede ser futura")
            return
        edad_calculada = hoy.year - fecha_de_nacimiento.year
        if (hoy.month, hoy.day) < (fecha_de_nacimiento.month, fecha_de_nacimiento.day):
            edad_calculada -= 1
        if ts_ingresado == "Seleccione":
            mensaje_error.configure(text="Seleccione un tipo de sangre por favor")
            return
        if rh_ingresado == "Seleccione":
            mensaje_error.configure(text="Seleccione un factor Rh por favor")
            return
        rh_ingresado = "+" if rh_ingresado == "Positivo" else "-"
        if sexo_ingresado == "Seleccione":
            mensaje_error.configure(text="Seleccione un sexo por favor")
            return
        if not peso_ingresado:
            mensaje_error.configure(text="Debe ingresar un peso")
            return
        try:
            peso_ingresado = float(peso_ingresado)
        except ValueError:
            mensaje_error.configure(text="Debe ingresar un peso valido")
            return
        if not math.isfinite(peso_ingresado) or peso_ingresado <=0:
            mensaje_error.configure(text="Debe ingresar un peso mayor a 0")
            return
        if not email_ingresado:
            mensaje_error.configure(text="Debe ingressar una dirección de correo electronico")
            return
        patron_email = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.fullmatch(patron_email, email_ingresado):
            mensaje_error.configure(text="Ingrese un correo electrónico válido")
            return
        if elegibilidad_ingresada == "Seleccione":
            mensaje_error.configure(text="Seleccione un tipo de elegibilidad por favor")
            return
        if ult_don_ingresada.strip():
            try:
                ultima_fecha = datetime.strptime(
                ult_don_ingresada.strip(), "%d-%m-%Y").date()
            except ValueError:
                mensaje_error.configure(text="La fecha de última donación no es válida")
                return
            if ultima_fecha > hoy or ultima_fecha < fecha_de_nacimiento:
                mensaje_error.configure(text="Revise la fecha de última donación")
                return

            ultima_donacion_sql = ultima_fecha.isoformat()
        else:
            ultima_donacion_sql = None
        
        fecha_nacimiento_sql = fecha_de_nacimiento.isoformat()

        conexion = sqlite3.connect(RUTA_BD)
        cursor = conexion.cursor()

        cursor.execute("""INSERT INTO DONANTES (NOMBRE, APELLIDO, EDAD, SEXO, GRUPO_SANGUINEO, FACTOR_RH, FECHA_ULTIMA_DONACION, PESO, EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)""", (nombre_ingresado, apellido_ingresado, edad_calculada, sexo_ingresado, ts_ingresado, rh_ingresado,
            ultima_donacion_sql, peso_ingresado, email_ingresado, elegibilidad_ingresada, fecha_nacimiento_sql))

        id_donante = cursor.lastrowid
        conexion.commit()
        conexion.close()
        mensaje_error.configure(
        text=f"Donante registrado correctamente. ID: {id_donante}",text_color="green")
        def mostrar_confirmacion(id_donante, edad, elegibilidad, tipo_sangre):
            frame_confirmacion = ctk.CTkFrame(pantalla)
            frame_confirmacion.place(relx=0, rely=0, relwidth=1, relheight=1)

            titulo = ctk.CTkLabel(frame_confirmacion,text="¡Donante registrado correctamente!",font=("Arial", 26, "bold"))
            titulo.pack(pady=30)

            datos = ctk.CTkLabel(frame_confirmacion,text=f"ID del donante: {id_donante}\n"f"Edad: {edad} años\n"f"Elegibilidad: {elegibilidad}\n"
            f"Tipo de sangre: {tipo_sangre}",font=("Arial", 18),justify="left")
            datos.pack(pady=20)

        tipo_sangre = ts_ingresado + rh_ingresado
        mostrar_confirmacion(id_donante,edad_calculada,elegibilidad_ingresada,tipo_sangre)


    ingresar_donante_boton = ctk.CTkButton(frame_formulario,text="Ingresar donante",command= agregar_donante, fg_color="red", hover_color="dimgray")
    ingresar_donante_boton.grid(row = 13, column=0, columnspan=2, pady =20)