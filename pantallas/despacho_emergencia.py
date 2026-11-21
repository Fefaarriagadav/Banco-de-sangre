import customtkinter as ctk
import sqlite3
from servicios.despachos import (GRUPOS,FACTORES_RH,registrar_emergencia,ExcesoVolumenError)

def mostrar_despacho_emergencia(pantalla, centro, volver_stock):
    pantalla.title("Banco de sangre - Despacho de emergencia")
    #colores
    FONDO = "#F3F5F9"
    AZUL_OSCURO = "#193653"
    ROJO = "#C62828"
    BLANCO = "#FFFFFF"
    GRIS = "#64748B"
    #pantalla
    vista = ctk.CTkFrame(pantalla,fg_color=FONDO,corner_radius=0)
    vista.place(relx=0, rely=0, relwidth=1, relheight=1)
    area_scroll = ctk.CTkScrollableFrame(vista,fg_color=FONDO)
    area_scroll.pack(fill="both", expand=True)

    contenedor = ctk.CTkFrame(area_scroll,width=800,fg_color=BLANCO,corner_radius=20)
    contenedor.pack(pady=35, padx=20)
    #encabezado
    encabezado = ctk.CTkFrame(contenedor,fg_color=AZUL_OSCURO,corner_radius=15)
    encabezado.pack(fill="x",padx=20,pady=(20, 10))
    ctk.CTkLabel(encabezado,text="DESPACHO DE EMERGENCIA",font=("Arial", 26, "bold"),text_color=BLANCO).pack(padx=25, pady=(22, 8))
    ctk.CTkLabel(encabezado,text=f"Centro solicitante: {centro}",font=("Arial", 15),text_color="#DFEAF6",wraplength=700).pack(padx=25, pady=(0, 22))

    ctk.CTkLabel(contenedor,text="Nueva solicitud de emergencia",font=("Arial", 21, "bold"),text_color=AZUL_OSCURO).pack(pady=(15, 8))
    ctk.CTkLabel(contenedor,text="Complete los datos para registrar la solicitud.",font=("Arial", 14),text_color=GRIS).pack(pady=(0, 18))
    #grupos de sangre
    ctk.CTkLabel(contenedor,text="Grupo sanguíneo",font=("Arial", 15, "bold"),text_color=AZUL_OSCURO).pack()
    grupo = ctk.CTkOptionMenu(contenedor,values=list(GRUPOS),width=320,height=40)
    grupo.set("Seleccione")
    grupo.pack(pady=(5, 14))
    #factor rh
    ctk.CTkLabel(contenedor,text="Factor Rh",font=("Arial", 15, "bold"),text_color=AZUL_OSCURO).pack()
    rh = ctk.CTkOptionMenu(contenedor,values=list(FACTORES_RH),width=320,height=40)
    rh.set("Seleccione")
    rh.pack(pady=(5, 14))
    #volumen solicitado
    ctk.CTkLabel(contenedor,text="Volumen requerido (mL)",font=("Arial", 15, "bold"),text_color=AZUL_OSCURO).pack()
    volumen = ctk.CTkEntry(contenedor,placeholder_text="Ej. 450",width=320,height=40)
    volumen.pack(pady=(5, 14))

    #motivo
    ctk.CTkLabel(contenedor,text="Motivo de la emergencia",font=("Arial", 15, "bold"),text_color=AZUL_OSCURO).pack()
    motivo = ctk.CTkTextbox(contenedor,width=450,height=115,border_width=1,border_color="#CBD5E1")
    motivo.pack(pady=(5, 18))
    mensaje = ctk.CTkLabel(contenedor,text="",font=("Arial", 14),text_color=ROJO,wraplength=600)
    mensaje.pack(pady=(0, 10))

    #registrar solicitud
    def guardar_emergencia(confirmacion_ml=None):
        try:
            solicitud_id = registrar_emergencia(centro,grupo.get(),rh.get(),volumen.get(),motivo.get("1.0", "end-1c"),confirmar_volumen=confirmacion_ml)

        except ExcesoVolumenError as error:
            volumen_propuesto = error.asignado
            volumen_pedido = error.solicitado
            ventana = ctk.CTkToplevel(vista)
            ventana.title("Confirmar volumen")
            ventana.geometry("470x270")
            ventana.transient(vista.winfo_toplevel())
            ventana.grab_set()

            ctk.CTkLabel(ventana,text="Confirmación de reserva",font=("Arial", 21, "bold")).pack(pady=(25, 15))
            ctk.CTkLabel(ventana,text=(f"Volumen solicitado: {volumen_pedido} mL\n" f"Volumen de las bolsas: {volumen_propuesto} mL\n\n" "Las bolsas se reservan completas.\n" "¿Desea confirmar este volumen?"),
                justify="center",font=("Arial", 14)).pack(pady=10)

            def confirmar():
                ventana.destroy()
                guardar_emergencia(confirmacion_ml=volumen_propuesto)

            ctk.CTkButton(ventana,text="Confirmar reserva",command=confirmar,fg_color="#15803D").pack(pady=5)
            ctk.CTkButton(ventana,text="Cancelar",command=ventana.destroy,fg_color="#64748B").pack(pady=5)
            return
        except (ValueError, PermissionError) as error:
            mensaje.configure(text=str(error),text_color=ROJO)
            return

        except sqlite3.Error:
            mensaje.configure(text="No se pudo reservar la sangre. Intente nuevamente.",text_color=ROJO)
            return

        mensaje.configure(text=(f"Solicitud de emergencia #{solicitud_id} registrada.\n" "Estado: Pendiente de aprobación.\n" "La sangre quedó reservada provisionalmente."),text_color="#15803D")

        grupo.set("Seleccione")
        rh.set("Seleccione")
        volumen.delete(0, "end")
        motivo.delete("1.0", "end")

    #boton registrar
    ctk.CTkButton(contenedor,text="Registrar solicitud de emergencia",command=lambda : guardar_emergencia(),width=340,height=48,fg_color=ROJO,hover_color="#991B1B",font=("Arial", 16, "bold")).pack(pady=(0, 15))
    #volver al inciio
    def volver():
        vista.destroy()
        volver_stock()

    ctk.CTkButton(contenedor,text="← Volver al inventario",command=volver,width=220,height=45,fg_color=GRIS,hover_color="#475569").pack(pady=(0, 25))