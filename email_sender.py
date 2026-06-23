"""
Módulo de envío de alertas por email vía Gmail SMTP.

Expone la función email_sender, que se encarga de autenticarse
en el servidor SMTP de Gmail y enviar el mensaje de notificación
a las cuentas configuradas en las variables de entorno.
"""

from smtplib import SMTP
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def email_sender(mensajes: str) -> None:
    """Envía un email de alerta a las cuentas configuradas en el entorno.

    Se conecta al servidor SMTP de Gmail usando STARTTLS, se autentica
    con las credenciales de entorno y despacha el mensaje a una lista
    de destinatarios. Si las credenciales no están disponibles o falla
    la conexión, imprime el error sin relanzar la excepción.

    Args:
        mensajes: Cuerpo del email en texto plano con los turnos disponibles
                  encontrados por el scraper.

    Environment Variables:
        MY_USERNAME: Email del remitente y primer destinatario.
        SECRET_PASSWORD: App Password de Gmail del remitente.
        ANOTHER_EMAIL: Email del segundo destinatario (puede ser el mismo que MY_USERNAME).
    """
    load_dotenv()

    my_username = os.getenv("MY_USERNAME")
    my_password = os.getenv("SECRET_PASSWORD")
    second_email = os.getenv("ANOTHER_EMAIL")

    try:
        email_server = "smtp.gmail.com"
        port = 587
        server = SMTP(email_server, port)

        server.starttls()

        if my_username and my_password:
            to_addrs = [my_username, second_email]
            server.login(my_username, my_password)

            from_addr = my_username
            subj = "Nuevo turno disponible para Padel"

            msg = MIMEMultipart()
            msg["From"] = my_username
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subj

            msg.attach(MIMEText(mensajes, "plain"))

            server.sendmail(from_addr, to_addrs, msg.as_string())

            server.quit()
        else:
            print("Error: Credenciales no encontradas")
    except Exception as e:
        print(f"Error al enviar el email: {e}")
