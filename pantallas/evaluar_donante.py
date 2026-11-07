import sqlite3
import customtkinter as ctk
from servicios.elegibilidad import RESULTADOS, consultar_donante, guardar_resultado


def mostrar_evaluacion(pantalla, empleado_id):
    # Limpia el contenido anterior antes de mostrar esta pantalla.
    for widget in pantalla.winfo_children():
        widget.destroy()

    # Crea el formulario para buscar al donante y registrar su resultado.
    frame = ctk.CTkScrollableFrame(pantalla)
    frame.pack(fill="both", expand=True, padx=25, pady=20)

    ctk.CTkLabel(frame, text="Registrar resultado médico", font=("Arial", 24, "bold")).pack(pady=15)
    ctk.CTkLabel(frame, text="La evaluación médica se realiza fuera del sistema.\nAquí se registra únicamente su resultado final: Apto o No apto.", wraplength=550).pack(pady=5)

    entrada = ctk.CTkEntry(frame, placeholder_text="Ingrese el ID del donante", placeholder_text_color="gray", width=300)
    entrada.pack(pady=10)

    datos = ctk.CTkLabel(frame, text="Busque un donante por su ID para continuar.", wraplength=550)
    resultado = ctk.CTkOptionMenu(frame, values=list(RESULTADOS), state="disabled")
    resultado.set("Seleccione")
    mensaje = ctk.CTkLabel(frame, text="", wraplength=550)

    # Guarda los datos del donante seleccionado y el ID con el que se buscó.
    donante_actual = None
    id_consultado = None

    def informar(texto, error=True):
        # Muestra mensajes de error en rojo y confirmaciones en verde.
        mensaje.configure(text=texto, text_color="red" if error else "green")

    def mostrar_datos():
        # Actualiza la pantalla con el nombre y el resultado actual del donante.
        valor = donante_actual["RESULTADO"] or "Sin resultado médico registrado"
        datos.configure(text=f"Donante N° {donante_actual['ID']}: {donante_actual['NOMBRE']} {donante_actual['APELLIDO']}\nResultado médico: {valor}")

    def invalidar():
        nonlocal donante_actual, id_consultado
        # Desactiva el guardado para evitar usar datos de una búsqueda anterior.
        donante_actual = None
        id_consultado = None
        guardar.configure(state="disabled")
        resultado.configure(state="disabled")
        resultado.set("Seleccione")
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
        guardar.configure(state="normal")

    def confirmar():
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
            guardar_resultado(donante_actual["ID"], valor, empleado_id)
        except (ValueError, PermissionError) as error:
            informar(str(error))
            return
        except sqlite3.Error:
            informar("No se pudo guardar el resultado. Intente nuevamente.")
            return

        donante_actual["RESULTADO"] = valor
        mostrar_datos()
        informar("Resultado guardado correctamente.", error=False)

    def comprobar_cambio(event):
        # Si se modifica el ID, obliga a buscar nuevamente al donante.
        if donante_actual is not None and entrada.get() != id_consultado:
            invalidar()

    # Agrega los controles del formulario y conecta eventos del campo de ID.
    ctk.CTkButton(frame, text="Buscar donante", command=buscar).pack(pady=10)
    datos.pack(pady=15)
    resultado.pack(pady=10)

    guardar = ctk.CTkButton(frame, text="Guardar resultado", command=confirmar, state="disabled")
    guardar.pack(pady=15)
    mensaje.pack(pady=10)

    entrada.bind("<KeyRelease>", comprobar_cambio)
    entrada.bind("<Return>", lambda event: buscar())
