from smtplib import SMTP
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def email_sender(mensajes):
    load_dotenv()

    my_username = os.getenv("MY_USERNAME")
    my_password = os.getenv("SECRET_PASSWORD")
    second_email = os.getenv('ANOTHER_EMAIL')

    try:
        email_server = "smtp.gmail.com"
        port = 587
        server = SMTP(email_server, port)

        server.starttls()

        if my_username and my_password: 
            to_addrs = [my_username, second_email]
            server.login(my_username, my_password)

            from_addr = my_username
            subj = 'Nuevo turno disponible para Padel'

            msg = MIMEMultipart()
            msg['From'] = my_username
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subj

            msg.attach(MIMEText(mensajes, 'plain'))
            

            server.sendmail(from_addr,to_addrs, msg.as_string())

            server.quit()
        else:
            print('Error: Crendeciales no encontradas')
    except Exception as e: 
        print(f'Error al enviar el email {e}')