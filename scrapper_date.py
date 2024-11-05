import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import TypedDict, List
from telegram_sender import enviar_mensaje_telegram
from dotenv import load_dotenv
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

my_username = os.getenv("MY_USERNAME")
my_password = os.getenv("MY_PASSWORD")

url_login = "https://login.buenosaires.gob.ar/"
url_reserva = (
    "https://formulario-sigeci.buenosaires.gob.ar/InicioTramiteComun?idPrestacion=5206"
)


class Turnos(TypedDict):
    dia: str
    horarios: List[str]


class Browser:
    browser: webdriver.Chrome
    turnos: List[Turnos] = []

    def __init__(self):
        # Usar webdriver_manager para manejar el driver
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )

    def open_page(self, url: str):
        self.browser.get(url)

    def close_browser(self):
        self.browser.close()

    def add_inputs(self, by: By, value: str, text: str):
        field = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((by, value))
        )
        field.send_keys(text)

    def click_button(self, by: By, value: str):
        button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((by, value))
        )
        button.click()

    def login_linkedin(self, username: str, password: str):
        self.add_inputs(by=By.ID, value="email", text=username)
        self.add_inputs(by=By.ID, value="password-text-field", text=password)
        self.click_button(by=By.ID, value="login")

    def get_info_selector(self, by: By, value: str):
        horarios: List[str] = []
        element = self.browser.find_element(by=by, value=value)
        spans = element.find_elements(By.TAG_NAME, "span")

        for span in spans:
            horarios.append(span.text)

        return horarios

    def get_info_test(self, by: By, value: str):
        try:
            div = self.browser.find_element(by=by, value=value)
            divButton = self.browser.find_element(
                By.CSS_SELECTOR, "div.container-button"
            )
            save_button = divButton.find_element(By.ID, "save")

            inputs = div.find_elements(By.CSS_SELECTOR, "div > div > h4")

            for input in inputs:
                try:
                    dia = input.get_attribute("data-date")
                    if dia != "":
                        input.click()
                        time.sleep(1)

                        if save_button.is_displayed() and save_button.is_enabled():
                            save_button.click()
                            time.sleep(1)

                            horarios = self.browser.find_element(
                                By.ID, "hoursBody"
                            ).text

                            turno = {"dia": dia, "horarios": horarios}
                            if dia:
                                self.turnos.append(turno)

                            edit_button = WebDriverWait(self.browser, 10).until(
                                EC.element_to_be_clickable((By.ID, "edit"))
                            )
                            edit_button.click()
                            time.sleep(1)
                        else:
                            continue
                except Exception as e:
                    print(f"Error al procesar input con data-date {dia}: {str(e)}")
                    continue

                time.sleep(1)

            print(self.turnos)

        except Exception as e:
            print(f"Error al procesar la información: {str(e)}")

    def filter_turns(self, hours: List[str]):
        def has_hour(turno: Turnos) -> bool:
            # Verifica si alguna de las horas seleccionadas está presente en el turno
            return any(hour in turno["horarios"] for hour in hours)

        filtered_turns = list(filter(has_hour, self.turnos))
        return filtered_turns



if __name__ == "__main__":
    # medir duración de script
    start_time = time.time()

    browser = Browser()

    browser.open_page(url_login)

    WebDriverWait(browser.browser, 10).until(
        EC.presence_of_element_located((By.ID, "zocial-mail"))
    )

    browser.click_button(by=By.ID, value="zocial-mail")

    WebDriverWait(browser.browser, 10).until(
        EC.presence_of_element_located((By.ID, "password-text-field"))
    )

    browser.login_linkedin(username=my_username, password=my_password)

    browser.open_page(url_reserva)

    WebDriverWait(browser.browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-start="fecha"]'))
    )

    browser.click_button(by=By.CSS_SELECTOR, value='[data-start="fecha"]')

    WebDriverWait(browser.browser, 20).until(
        EC.presence_of_element_located((By.ID, "calendar"))
    )

    browser.get_info_test(By.ID, "calendar")

    selected_hours = ["15:00 hs", "19:00 hs"]  # Lista de horas a filtrar
    dias_formateados = []

    # Inicializa diccionarios para almacenar días filtrados
turnos_por_hora = {hour: [] for hour in selected_hours}

# Filtra los turnos utilizando la nueva lista de horas
filtrados = browser.filter_turns(hours=selected_hours)

# Formatear los días obtenidos y llenar el diccionario
for filtrado in filtrados:
    dia_formateado = datetime.strptime(filtrado["dia"], "%Y-%m-%d").strftime("%d/%m")
    for hour in selected_hours:
        if hour in filtrado["horarios"]:
            turnos_por_hora[hour].append(dia_formateado)

# Construir el mensaje
token = os.getenv("TOKEN")
chat_id = os.getenv("CHAT_ID")

mensajes = []
for hour, dias in turnos_por_hora.items():
    if dias:
        dias_texto = ", ".join(dias)
        mensajes.append(f"Turnos disponibles a las {hour}: {dias_texto}")

# Verificar si hay mensajes que enviar
if mensajes:
    mensaje = "¡Se han encontrado turnos disponibles!\n" + "\n".join(mensajes) + f"\nPara reservar, accede al siguiente link {url_reserva}"
else:
    mensaje = "¡No se han encontrado turnos disponibles en esos horarios!"

# Enviar el mensaje por Telegram
enviar_mensaje_telegram(mensaje, chat_id, token)

end_time = time.time()
duration = end_time - start_time
print(f"Duración del script: {duration:.2f} segundos")
