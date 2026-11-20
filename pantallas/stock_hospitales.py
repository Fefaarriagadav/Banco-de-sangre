import customtkinter as ctk
import sqlite3
from datetime import datetime
from servicios.vencimientos import consultar_stock_detallado

def mostrar_stock_hospitales(pantalla, nombre_centro, volver_login):
    #colores
    FONDO = "#F3F5F9"
    AZUL_OSCURO = "#193653"
    ROJO = "#C62828"
    BLANCO = "#FFFFFF"
    GRIS = "#64748B"
   #pantalla principal donde se muestra el stock de sangre disponible para el hospital o clínica
    frame_stock = ctk.CTkFrame(pantalla,fg_color=FONDO,corner_radius=0)
    frame_stock.place(relx=0,rely=0,relwidth=1,relheight=1)

    # scrollable frame para permitir desplazamiento vertical si el contenido excede la altura de la ventana
    area_scroll = ctk.CTkScrollableFrame(frame_stock,fg_color=FONDO,corner_radius=0)
    area_scroll.pack(fill="both", expand=True)
    # general 
    contenedor = ctk.CTkFrame(area_scroll,fg_color=BLANCO,corner_radius=22,border_width=1,border_color="#E2E8F0")
    contenedor.pack(padx=20, pady=25)

    #encabezado con el nombre del hospital o clínica
    encabezado = ctk.CTkFrame(contenedor,height=145,fg_color=AZUL_OSCURO,corner_radius=18)
    encabezado.pack(fill="x",padx=15,pady=(15, 0))
    encabezado.pack_propagate(False)

    titulo = ctk.CTkLabel(encabezado,text="BANCO DE SANGRE",font=("Arial", 30, "bold"),text_color=BLANCO)
    titulo.pack(pady=(17, 5))

    subtitulo = ctk.CTkLabel(encabezado,text="Consulta de inventario disponible",font=("Arial", 17),text_color="#CBD5E1")
    subtitulo.pack()
    centro_label = ctk.CTkLabel(encabezado,text=f"Hospital / Clínica: {nombre_centro}",font=("Arial", 15, "bold"),text_color=BLANCO,wraplength=900)
    centro_label.pack(pady=(8, 0))

    #titulo
    titulo_stock = ctk.CTkLabel(contenedor,text="Disponibilidad por grupo sanguíneo",font=("Arial", 22, "bold"),text_color=AZUL_OSCURO)
    titulo_stock.pack(pady=(18, 4))
    descripcion = ctk.CTkLabel(contenedor,text="Cantidad de unidades vigentes disponibles para solicitud",font=("Arial", 14),text_color=GRIS)
    descripcion.pack()

    # trajetas para mostrar la cantidad de unidades disponibles por grupo sanguíneo
    frame_tarjetas = ctk.CTkFrame(contenedor,fg_color="transparent")
    frame_tarjetas.pack(padx=20, pady=(12, 8))

    tipos_sangre = [("A", "+"), ("A", "-"),("B", "+"), ("B", "-"),("AB", "+"), ("AB", "-"),("O", "+"), ("O", "-")]
    etiquetas_stock = {}
    #tarjetas
    for indice, (grupo, rh) in enumerate(tipos_sangre):
        fila = indice // 4
        columna = indice % 4
        tarjeta = ctk.CTkFrame(frame_tarjetas,width=225,height=135,fg_color="#F8FAFC",corner_radius=15,border_width=1,border_color="#E2E8F0")
        tarjeta.grid(row=fila,column=columna,padx=9,pady=7)
        tarjeta.pack_propagate(False)
        tipo_label = ctk.CTkLabel(tarjeta,text=f"{grupo}{rh}",font=("Arial", 27, "bold"),text_color=ROJO)
        tipo_label.pack(pady=(10, 2))

        cantidad_label = ctk.CTkLabel(tarjeta,text="—",font=("Arial", 34, "bold"),text_color=AZUL_OSCURO)
        cantidad_label.pack()
        unidad_label = ctk.CTkLabel(tarjeta,text="Unidades disponibles",font=("Arial", 13),text_color=GRIS)
        unidad_label.pack(pady=(0, 5))

        etiquetas_stock[(grupo, rh)] = cantidad_label
    # resumen de unidades disponibles
    resumen = ctk.CTkLabel(contenedor,text="Total disponible: — unidades",font=("Arial", 18, "bold"),text_color=AZUL_OSCURO)
    resumen.pack(pady=(7, 2))
    #mensaje de estado para mostrar la hora de la última actualización o errores
    mensaje_estado = ctk.CTkLabel(contenedor,text="",font=("Arial", 13),text_color=GRIS)
    mensaje_estado.pack(pady=(0, 8))

    #actualización de stock
    def actualizar_stock():
        try:
            datos = consultar_stock_detallado()
            cantidades = {tipo: 0 for tipo in tipos_sangre}
            for total in datos["totales"]:
                clave = (total["grupo"],total["rh"])

                if clave in cantidades:
                    cantidades[clave] = total["unidades"]
            for tipo, etiqueta in etiquetas_stock.items():
                etiqueta.configure(text=str(cantidades[tipo]))

            total_unidades = sum(cantidades.values())
            resumen.configure(text=f"Total disponible: {total_unidades} unidades")
            hora = datetime.now().strftime("%H:%M")
            mensaje_estado.configure(text=f"Última actualización: {hora}",text_color="#15803D")

        except (sqlite3.Error,ValueError,RuntimeError,TypeError,KeyError):
            for etiqueta in etiquetas_stock.values():
                etiqueta.configure(text="—")
            resumen.configure(text="Total disponible: — unidades")
            mensaje_estado.configure(text="No se pudo consultar el inventario.",text_color="#DC2626")

    #volver al incio 
    def volver_inicio():
        frame_stock.destroy()
        volver_login()
        #botones
    frame_botones = ctk.CTkFrame(contenedor,fg_color="transparent")
    frame_botones.pack(pady=(5, 20))

    #boton actualizar
    boton_actualizar = ctk.CTkButton(frame_botones,text="⟳  Actualizar inventario",command=actualizar_stock,width=260,height=48,corner_radius=12,fg_color="#2563EB",hover_color="#1D4ED8",font=("Arial", 16, "bold"))
    boton_actualizar.pack(side="left", padx=8)

    #boton solicitar unidades de sangre (deshabilitado por ahora)
    boton_solicitar = ctk.CTkButton(frame_botones,text="Solicitar unidades de sangre",width=300,height=48,corner_radius=12,fg_color="#16A34A",hover_color="#15803D",font=("Arial", 16, "bold"),state="disabled")
    boton_solicitar.pack(side="left", padx=8)

    #boton de volver
    boton_volver = ctk.CTkButton(frame_botones,text="← Volver al inicio",command=volver_inicio,width=180,height=48,corner_radius=12,fg_color="#64748B",hover_color="#475569",font=("Arial", 16, "bold"))
    boton_volver.pack(side="left", padx=8)
    #llamar a la función de actualizar stock al cargar la pantalla
    actualizar_stock()