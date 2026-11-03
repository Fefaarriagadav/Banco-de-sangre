import customtkinter as ctk
from agregar_donante import mostrar_registro

def mostrar_principal(pantalla, nombre, rol):
    frame_principal = ctk.CTkFrame(pantalla)
    frame_principal.place(relx=0,rely=0,relheight=1, relwidth=1)

    frame_contenido = ctk.CTkFrame(frame_principal, fg_color="transparent")
    frame_contenido.place(relx=0 ,rely=0.08 ,relwidth= 1, relheight= 0.92)


    menu_lateral = ctk.CTkFrame(frame_principal, width=250, corner_radius=0, fg_color="#E0E0E0")
    def alternar_menu():
        if menu_lateral.winfo_manager() == "place":
            menu_lateral.place_forget()
            
        else:
            menu_lateral.place(x=0, y=75, relheight=0.85)
            menu_lateral.lift()

    boton_menu = ctk.CTkButton(frame_principal,text="☰", width=50, height=45, font=("Arial",28), fg_color="transparent", text_color="#333333", hover_color="#DDDDDD", command=alternar_menu)
    boton_menu.place(x=20, y=20)

    if rol == "Entrevistador":
        boton_donante = ctk.CTkButton(menu_lateral, text="Agregar nuevo donante", width=210, height=45, text_color="#000000", fg_color="#C0F1FF", command=lambda: mostrar_registro(frame_contenido,rol))
        boton_donante.place(x=20, y=40)
    
    tarjeta_bienvenida = ctk.CTkFrame(frame_contenido,width=600, height=250, corner_radius=20,fg_color= "#FFFFFF")
    tarjeta_bienvenida.place(relx=0.5, rely=0.25, anchor = "center")
    titulo = ctk.CTkLabel(tarjeta_bienvenida, text="Banco de Sangre", font=("Arial", 30, "bold"), text_color="#000000")
    titulo_nombre = ctk.CTkLabel(tarjeta_bienvenida, text=f"¡Bienvenid@, {nombre}!", font=("Arial", 30, "bold"), text_color="#000000")
    titulo_rol = ctk.CTkLabel(tarjeta_bienvenida, text=f"Rol : {rol}", font=("Arial", 30, "bold"), text_color="#000000")
    titulo.place(relx=0.5,rely=0.2, anchor = "center")
    titulo_nombre.place(relx=0.5, rely=0.5, anchor ="center")
    titulo_rol.place(relx=0.5, rely=0.8, anchor="center")



    boton_menu.lift()