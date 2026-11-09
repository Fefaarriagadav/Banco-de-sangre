import smtplib #libreria que conecta con el servidor de correo
import os #accede a las credenciales desde .env
from email.message import EmailMessage #crea correo con destinatario, asunto y contenido
from dotenv import load_dotenv #carga las varuiables desde .env
from pathlib import Path


ruta_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ruta_env)

correo = os.getenv("CORREO_REMITENTE")
contrasena = os.getenv("CONTRASENA_APP")

def enviar_correo(destinatario):
    # Crear el mensaje de correo
    mensaje = EmailMessage()


    mensaje["From"] = correo
    mensaje["To"] = destinatario
    mensaje["Subject"] = "Necesitamos tu ayuda - Banco de Sangre"

    mensaje.set_content("Estimado donante," \
    " nos gustaría informarle que necesitamos su ayuda para continuar con nuestro programa de donación de sangre." \
    "Actualmente el banco de sangre necesita donaciones de su tipo de sangre. Su contribución puede salvar vidas y marcar la diferencia en nuestra comunidad." \
    "Si está dispuesto a ayudarnos, por favor considere programar una cita para donar sangre.")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(correo, contrasena)
        servidor.send_message(mensaje)