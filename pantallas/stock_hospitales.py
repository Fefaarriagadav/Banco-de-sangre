import customtkinter as ctk
import sqlite3
from datetime import datetime
from pantallas.despacho_programado import mostrar_despacho_programado
from servicios.vencimientos import consultar_stock_detallado
from pantallas.despacho_emergencia import mostrar_despacho_emergencia
from pantallas.mis_solicitudes import mostrar_mis_solicitudes

def mostrar_stock_hospitales(pantalla, nombre_centro, volver_login):
    pantalla.title("Banco de sangre - Inventario disponible")
    # colores
    FONDO = "#F3F5F9"
    AZUL_OSCURO = "#193653"
    ROJO = "#C62828"
    BLANCO = "#FFFFFF"
    GRIS = "#64748B"
    # pantalla principal
    frame_stock = ctk.CTkFrame(pantalla,fg_color=FONDO,corner_radius=0)
    frame_stock.place(relx=0,rely=0,relwidth=1,relheight=1)

    #scroll
    area_scroll = ctk.CTkScrollableFrame(frame_stock,fg_color=FONDO,corner_radius=0)
    area_scroll.pack(fill="both", expand=True)

    #central
    contenedor = ctk.CTkFrame(area_scroll,fg_color=BLANCO,corner_radius=22,border_width=1,border_color="#E2E8F0")
    contenedor.pack(padx=20, pady=25)

    #encabezado
    encabezado = ctk.CTkFrame(contenedor,height=145,fg_color=AZUL_OSCURO,corner_radius=18)
    encabezado.pack(fill="x",padx=15,pady=(15, 0))
    encabezado.pack_propagate(False)
    titulo = ctk.CTkLabel(encabezado,text="BANCO DE SANGRE",font=("Arial", 30, "bold"),text_color=BLANCO)
    titulo.pack(pady=(17, 5))
    subtitulo = ctk.CTkLabel(encabezado,text="Consulta de inventario disponible",font=("Arial", 17),text_color="#CBD5E1")
    subtitulo.pack()

    centro_label = ctk.CTkLabel(encabezado,text=f"Hospital / Clínica: {nombre_centro}",font=("Arial", 15, "bold"),text_color=BLANCO,wraplength=900)
    centro_label.pack(pady=(8, 0))

    #inventario
    titulo_stock = ctk.CTkLabel(contenedor,text="Disponibilidad por grupo sanguíneo",font=("Arial", 22, "bold"),text_color=AZUL_OSCURO)
    titulo_stock.pack(pady=(18, 4))
    descripcion = ctk.CTkLabel(contenedor,text="Volumen de sangre vigente disponible para solicitud",font=("Arial", 14),text_color=GRIS)
    descripcion.pack()

    #tarjetas
    frame_tarjetas = ctk.CTkFrame(contenedor,fg_color="transparent")
    frame_tarjetas.pack(padx=20, pady=(12, 8))
    tipos_sangre = [("A", "+"), ("A", "-"),("B", "+"), ("B", "-"),("AB", "+"), ("AB", "-"),("O", "+"), ("O", "-")]
    etiquetas_stock = {}

     #crear las tarjetas para cada tipo de sangre
    for indice, (grupo, rh) in enumerate(tipos_sangre):
        fila = indice // 4
        columna = indice % 4
        tarjeta = ctk.CTkFrame(frame_tarjetas,width=225,height=135,fg_color="#F8FAFC",corner_radius=15,border_width=1,border_color="#E2E8F0")
        tarjeta.grid(row=fila,column=columna,padx=9,pady=7)
        tarjeta.pack_propagate(False)
        tipo_label = ctk.CTkLabel(tarjeta,text=f"{grupo}{rh}",font=("Arial", 27, "bold"),text_color=ROJO)
        tipo_label.pack(pady=(10, 2))

        #litros disponibles
        litros_label = ctk.CTkLabel(tarjeta,text="— L",font=("Arial", 30, "bold"),text_color=AZUL_OSCURO)
        litros_label.pack()
        #cantidad de extracciones disponibles
        bolsas_label = ctk.CTkLabel(tarjeta,text="— bolsas disponibles",font=("Arial", 13),text_color=GRIS)
        bolsas_label.pack(pady=(0, 5))
        # Guardar ambos etiquetas
        etiquetas_stock[(grupo, rh)] = (litros_label,bolsas_label)

    #resumen
    resumen = ctk.CTkLabel(contenedor,text="Total disponible: — L · — bolsas",font=("Arial", 18, "bold"),text_color=AZUL_OSCURO)
    resumen.pack(pady=(7, 2))

    #mensaje
    mensaje_estado = ctk.CTkLabel(contenedor,text="",font=("Arial", 13),text_color=GRIS)
    mensaje_estado.pack(pady=(0, 8))

    #actualiacion de stock
    def actualizar_stock():
        try:
            datos = consultar_stock_detallado()
            #los 8 grupos con cero
            cantidades = {tipo: {"litros": 0.0, "unidades": 0}
                for tipo in tipos_sangre}
            #volumen y cantidad reales
            for total in datos["totales"]:
                clave = (total["grupo"],total["rh"])

                if clave in cantidades:
                    cantidades[clave] = {"litros": float(total["litros"]),"unidades": total["unidades"]}

            #actualizar tarjetas
            for tipo, (etiqueta_litros, etiqueta_bolsas) in etiquetas_stock.items():
                valor = cantidades[tipo]
                etiqueta_litros.configure(text=f'{valor["litros"]:.2f} L')
                etiqueta_bolsas.configure(text=f'{valor["unidades"]} bolsas disponibles')
            #caluclar cantidad
            total_litros = sum(valor["litros"]
                for valor in cantidades.values())
            #total de extracciones
            total_bolsas = sum(valor["unidades"]
                for valor in cantidades.values())

            resumen.configure(text=(f"Total disponible: " f"{total_litros:.2f} L · " f"{total_bolsas} bolsas"))

            #ultima actualización
            hora = datetime.now().strftime("%H:%M")
            mensaje_estado.configure(text=f"Última actualización: {hora}",text_color="#15803D")
        except (sqlite3.Error,ValueError,RuntimeError,TypeError,KeyError):

            #limpiar datos en caso de error
            for etiqueta_litros, etiqueta_bolsas in etiquetas_stock.values():
                etiqueta_litros.configure(text="— L")
                etiqueta_bolsas.configure(text="— bolsas disponibles")
            resumen.configure(text="Total disponible: — L · — bolsas")
            mensaje_estado.configure(text="No se pudo consultar el inventario.",text_color="#DC2626")

    #volver al inicio de sesión
    def volver_inicio():
        frame_stock.destroy()
        volver_login()

    def abrir_mis_solicitudes():
        frame_stock.destroy()
        mostrar_mis_solicitudes(pantalla,nombre_centro,lambda: mostrar_stock_hospitales(pantalla,nombre_centro,volver_login))

    #botones
    frame_botones = ctk.CTkFrame(contenedor,fg_color="transparent")
    frame_botones.pack(pady=(5, 20))
    #actualizar 
    boton_actualizar = ctk.CTkButton(frame_botones,text="⟳  Actualizar inventario",command=actualizar_stock,width=210,height=48,corner_radius=12,fg_color="#2563EB",hover_color="#1D4ED8",font=("Arial", 16, "bold"))
    boton_actualizar.pack(side="left", padx=8)
    #despacho
    def abrir_despacho():
        frame_stock.destroy()
        mostrar_despacho_programado(pantalla,nombre_centro,lambda: mostrar_stock_hospitales(pantalla,nombre_centro,volver_login))

    def abrir_emergencia():
        frame_stock.destroy()
        mostrar_despacho_emergencia(pantalla,nombre_centro,lambda: mostrar_stock_hospitales(pantalla,nombre_centro,volver_login))
    
    #programar despacho
    boton_solicitar = ctk.CTkButton(frame_botones,text="Programar despacho",command=abrir_despacho,width=300,height=48,corner_radius=12,fg_color="#16A34A",hover_color="#15803D",font=("Arial", 16, "bold"))
    boton_solicitar.pack(side="left", padx=8)
    #despacho de emergencia 
    boton_emergencia = ctk.CTkButton(frame_botones,text="Solicitar emergencia",command=abrir_emergencia,width=220,height=48,corner_radius=12,fg_color="#C62828",hover_color="#991B1B",font=("Arial", 16, "bold"))
    boton_emergencia.pack(side="left", padx=8)
    #mis solicitudes
    boton_mis_solicitudes = ctk.CTkButton(frame_botones,text="Mis solicitudes",command=abrir_mis_solicitudes,width=190,height=48,corner_radius=12,fg_color="#193653",hover_color="#284B6D",font=("Arial", 16, "bold"))
    boton_mis_solicitudes.pack(side="left", padx=8)
    #volver al incio
    boton_volver = ctk.CTkButton(contenedor,text="← Volver al inicio",command=volver_inicio,width=220,height=48,corner_radius=12,fg_color="#64748B",hover_color="#475569",font=("Arial", 16, "bold"))
    boton_volver.pack(pady=(0, 20))
    #cargar 
    actualizar_stock()
