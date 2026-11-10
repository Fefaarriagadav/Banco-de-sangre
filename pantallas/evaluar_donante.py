import sqlite3
import customtkinter as ctk
from datetime import date
from servicios.elegibilidad import (RESULTADOS, TEMPORAL, FORMATO_FECHA, consultar_donante, guardar_resultado, describir_estado)


def mostrar_evaluacion(pantalla, empleado_id):
    # Limpia el contenido anterior antes de mostrar esta pantalla.
    for widget in pantalla.winfo_children():
        widget.destroy()

    # Crea el formulario para buscar al donante y registrar su resultado.
    frame = ctk.CTkScrollableFrame(pantalla)
    frame.pack(fill="both", expand=True, padx=25, pady=20)

    ctk.CTkLabel(frame, text="Actualizar habilitación del donante", font=("Arial", 24, "bold")).pack(pady=15)
    ctk.CTkLabel(frame, text="La evaluación médica se realiza fuera del sistema.\nAquí se registra únicamente la habilitación final del donante. Si es temporal, indique el período.", wraplength=550).pack(pady=5)

    entrada = ctk.CTkEntry(frame, placeholder_text="Ingrese el ID del donante", placeholder_text_color="gray", width=300)
    entrada.pack(pady=10)

    datos = ctk.CTkLabel(frame, text="Busque un donante por su ID para continuar.", wraplength=550)
    resultado = ctk.CTkOptionMenu(frame, values=list(RESULTADOS), state="disabled", command=lambda valor: mostrar_periodo(valor == TEMPORAL))

    # Período de la inhabilitación temporal: solo se muestra cuando se elige "NO apto temporalmente".
    frame_periodo = ctk.CTkFrame(frame, fg_color="transparent")
    ctk.CTkLabel(frame_periodo, text="Inicio de la restricción").grid(row=0, column=0, padx=10)
    ctk.CTkLabel(frame_periodo, text="Fin de la restricción").grid(row=0, column=1, padx=10)
    entrada_inicio = ctk.CTkEntry(frame_periodo, placeholder_text="DD-MM-AAAA", width=140)
    entrada_inicio.grid(row=1, column=0, padx=10, pady=5)
    entrada_fin = ctk.CTkEntry(frame_periodo, placeholder_text="DD-MM-AAAA", width=140)
    entrada_fin.grid(row=1, column=1, padx=10, pady=5)
    resultado.set("Seleccione")
    mensaje = ctk.CTkLabel(frame, text="", wraplength=550)

    # Guarda los datos del donante seleccionado y el ID con el que se buscó.
    donante_actual = None
    id_consultado = None

    def mostrar_periodo(visible):
        # Muestra u oculta los campos de fechas debajo del selector de estado.
        if visible:
            if not entrada_inicio.get().strip():
                entrada_inicio.insert(0, date.today().strftime(FORMATO_FECHA))
            frame_periodo.pack(pady=5, after=resultado)
        else:
            frame_periodo.pack_forget()

    def cargar_periodo(donante):
        # Precarga las fechas guardadas del donante (si las tiene).
        entrada_inicio.delete(0, "end")
        entrada_fin.delete(0, "end")
        if donante["RESULTADO"] == TEMPORAL and donante["INICIO"] and donante["FIN"]:
            entrada_inicio.insert(0, date.fromisoformat(donante["INICIO"]).strftime(FORMATO_FECHA))
            entrada_fin.insert(0, date.fromisoformat(donante["FIN"]).strftime(FORMATO_FECHA))
        mostrar_periodo(donante["RESULTADO"] == TEMPORAL)

    def informar(texto, error=True):
        # Muestra mensajes de error en rojo y confirmaciones en verde.
        mensaje.configure(text=texto, text_color="red" if error else "green")

    def mostrar_datos():
        # Actualiza la pantalla con el nombre y el resultado actual del donante.
        valor = describir_estado(donante_actual["RESULTADO"], donante_actual["INICIO"], donante_actual["FIN"])
        datos.configure(text=f"Donante N° {donante_actual['ID']}: {donante_actual['NOMBRE']} {donante_actual['APELLIDO']}\nHabilitación actual: {valor}")

    def invalidar():
        nonlocal donante_actual, id_consultado
        # Desactiva el guardado para evitar usar datos de una búsqueda anterior.
        donante_actual = None
        id_consultado = None
        guardar.configure(state="disabled")
        resultado.configure(state="disabled")
        resultado.set("Seleccione")
        entrada_inicio.delete(0, "end")
        entrada_fin.delete(0, "end")
        mostrar_periodo(False)
        datos.configure(text="Busque un donante por su ID para continuar.")
        mensaje.configure(text="")

    def buscar():
        nonlocal donante_actual, id_consultado
        invalidar()

        # Busca el donante y muestra un mensaje si ocurre un error.
        try:
            donante = consultar_donante(entrada.get())
        except ValueError as error:
            informar(str(error))
            return
        except sqlite3.Error:
            informar("No se pudo consultar la base de datos. Intente nuevamente.")
            return

        donante_actual = donante
        id_consultado = entrada.get()
        mostrar_datos()
        # Habilita la selección y el guardado cuando el donante existe.
        resultado.configure(state="normal")
        resultado.set(donante["RESULTADO"] or "Seleccione")
        cargar_periodo(donante)
        guardar.configure(state="normal")

    def confirmar():
        nonlocal donante_actual
        # Comprueba que haya una búsqueda válida y que el ID no haya cambiado.
        if donante_actual is None:
            informar("Busque un donante antes de guardar.")
            return

        if entrada.get() != id_consultado:
            invalidar()
            informar("El ID cambió. Busque nuevamente al donante.")
            return

        valor = resultado.get()

        # Guarda el resultado médico asociado al empleado que inició sesión.
        try:
            guardar_resultado(donante_actual["ID"], valor, empleado_id,
                              inicio=entrada_inicio.get(), fin=entrada_fin.get())
        except (ValueError, PermissionError) as error:
            informar(str(error))
            return
        except sqlite3.Error:
            informar("No se pudo guardar la habilitación. Intente nuevamente.")
            return

        # Se vuelve a consultar para mostrar exactamente lo que quedó guardado.
        donante_actual = consultar_donante(donante_actual["ID"])
        mostrar_datos()
        cargar_periodo(donante_actual)
        informar("Habilitación guardada correctamente.", error=False)

    def comprobar_cambio(event):
        # Si se modifica el ID, obliga a buscar nuevamente al donante.
        if donante_actual is not None and entrada.get() != id_consultado:
            invalidar()

    # Agrega los controles del formulario y conecta eventos del campo de ID.
    ctk.CTkButton(frame, text="Buscar donante", command=buscar).pack(pady=10)
    datos.pack(pady=15)
    resultado.pack(pady=10)

    guardar = ctk.CTkButton(frame, text="Guardar habilitación", command=confirmar, state="disabled")
    guardar.pack(pady=15)
    mensaje.pack(pady=10)

    entrada.bind("<KeyRelease>", comprobar_cambio)
    entrada.bind("<Return>", lambda event: buscar())