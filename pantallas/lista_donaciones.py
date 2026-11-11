import customtkinter as ctk
import sqlite3
from datos.configuracion import RUTA_BD
from servicios.elegibilidad import buscar_candidatos

def mostrar_lista_donaciones(pantalla):
    #se crea un frame que contiene todos los elementos de la pantalla para la lista de donaciones
    frame_filtro = ctk.CTkFrame(pantalla)
    frame_filtro.place(relx=0, rely=0, relwidth=1, relheight=1)
    titulo = ctk.CTkLabel(frame_filtro,text="Filtro de donaciones",font=("Arial", 30, "bold"),text_color="#000000")
    titulo.place(relx=0.5, rely=0.05, anchor="center")

    frame_seleccion = ctk.CTkFrame(frame_filtro)
    frame_seleccion.place(relx=0.5,rely=0.15,anchor="n",relwidth=0.6,relheight=0.3)
    frame_seleccion.grid_columnconfigure(0, weight=1)
    frame_seleccion.grid_columnconfigure(1, weight=1)
    frame_seleccion.grid_columnconfigure(2, weight=1)

    titulo_ts = ctk.CTkLabel(frame_seleccion,text="Seleccionar tipo de sangre",font=("Arial", 20, "bold"),text_color="#000000")
    titulo_ts.grid(row=0, column=0, padx=20, pady=5)

    sangres = ["Seleccione", "A", "B", "AB", "O"]
    ts = ctk.CTkOptionMenu(frame_seleccion,values=sangres,width=280,height=55,font=("Arial", 17))
    ts.set("Seleccione")
    ts.grid(row=1, column=0, padx=10, pady=20)

    titulo_rh = ctk.CTkLabel(frame_seleccion,text="Seleccionar factor RH",font=("Arial", 20, "bold"),text_color="#000000")
    titulo_rh.grid(row=0, column=1, padx=20, pady=5)
    factores = ["Seleccione", "Positivo", "Negativo"]
    rh = ctk.CTkOptionMenu(frame_seleccion,values=factores, width=280,height=55,font=("Arial", 17))
    rh.set("Seleccione")
    rh.grid(row=1, column=1, padx=10, pady=20)

    titulo_apto = ctk.CTkLabel(frame_seleccion,text="Seleccionar Validación",font=("Arial", 20, "bold"),text_color="#000000")
    titulo_apto.grid(row=0, column=2, padx=20, pady=5)
    factores = ["Seleccione", "Apta", "Usada", "Vencida"]
    apto = ctk.CTkOptionMenu(frame_seleccion,values=factores, width=280,height=55,font=("Arial", 17))
    apto.set("Seleccione")
    apto.grid(row=1, column=2, padx=10, pady=20)

    

    mensaje_error = ctk.CTkLabel(frame_filtro,text="",text_color="#DC2626",font=("Arial", 16, "bold"))
    mensaje_error.place(relx=0.5, rely=0.47, anchor="center")

    temporizador_mensaje = None
    # Función para mostrar un mensaje temporal en la pantalla
    def mostrar_mensaje(texto, color="#DC2626"):
        nonlocal temporizador_mensaje

        if temporizador_mensaje is not None:
            frame_filtro.after_cancel(temporizador_mensaje)
            temporizador_mensaje = None

        mensaje_error.configure(text=texto, text_color=color)

        if texto:
            temporizador_mensaje = frame_filtro.after(5000,lambda: mensaje_error.configure(text=""))

    #muestra los resultados de la busqueda en un frame scrollable
    frame_resultados = ctk.CTkScrollableFrame(frame_filtro,label_text="Donaciones encontradas")
    frame_resultados.place(relx=0.5,rely=0.50,anchor="n",relwidth=0.6,relheight=0.30)

    for columna in range(3):
        frame_resultados.grid_columnconfigure(columna, weight=1)

    total_donantes = ctk.CTkLabel(frame_filtro,text="Total de donantes aptos: 0",font=("Arial", 20, "bold"))
    total_donantes.place(relx=0.5,rely=0.85,anchor="center")

    donantes_encontrados = []
    filtros_buscados = None

    def limpiar_resultados():
        #en caso de que se cambien los filtros, se limpian los resultados y se deshabilita el boton de enviar correo
        nonlocal donantes_encontrados, filtros_buscados

        donantes_encontrados = []
        filtros_buscados = None

        total_donantes.configure(text="Total de donantes aptos: 0")

        for widget in frame_resultados.winfo_children():
            widget.destroy()

    def invalidar_busqueda(valor=None):
        limpiar_resultados()
        mostrar_mensaje("")

    def buscar_donantes():
        #se buscan los donantes en la base de datos segun los filtros seleccionados y se muestran en el frame de resultados
        nonlocal donantes_encontrados, filtros_buscados

        limpiar_resultados()
        ts_seleccionado = ts.get()
        rh_seleccionado = rh.get()
        if (ts_seleccionado == "Seleccione" or rh_seleccionado == "Seleccione"):
            mostrar_mensaje("Por favor, seleccione ambos filtros.")
            return

        mostrar_mensaje("")
        rh_bd = "+" if rh_seleccionado == "Positivo" else "-"
        try:
            # Excluye a quienes tienen una restricción vigente (temporal o permanente).
            donantes_encontrados = buscar_candidatos(ts_seleccionado, rh_bd)
        except sqlite3.Error:
            mostrar_mensaje("No se pudo consultar la base de datos.")
            return

        filtros_buscados = (ts_seleccionado, rh_bd)

        total_donantes.configure(text=f"Total de donantes aptos: {len(donantes_encontrados)}")
        encabezados = ["ID","Grupo sanguíneo","Factor Rh"]

        for columna, encabezado in enumerate(encabezados):
            etiqueta = ctk.CTkLabel(frame_resultados,text=encabezado,font=("Arial", 15, "bold"))
            etiqueta.grid(row=0,column=columna,padx=15,pady=10)

        for fila, donante in enumerate(donantes_encontrados, start=1):
            for columna, dato in enumerate(donante[:3]):
                etiqueta = ctk.CTkLabel(frame_resultados,text=str(dato),font=("Arial", 14))
                etiqueta.grid(row=fila,column=columna,padx=15,pady=5)

    def limpiar_filtros():
        ts.set("Seleccione")
        rh.set("Seleccione")
        limpiar_resultados()
        mostrar_mensaje("")

    
    ts.configure(command=invalidar_busqueda)
    rh.configure(command=invalidar_busqueda)

    buscar_boton = ctk.CTkButton(frame_seleccion,text="Buscar",command=buscar_donantes,text_color="#FFFFFF",fg_color="#DC2626",width=200,height=45)
    buscar_boton.grid(row=3,column=0,pady=20)

    boton_limpiar = ctk.CTkButton(frame_seleccion,text="Limpiar filtros",command=limpiar_filtros,fg_color="#64748B",text_color="#FFFFFF",width=200,height=45)
    boton_limpiar.grid(row=3,column=1,pady=20)