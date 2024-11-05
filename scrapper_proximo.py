import os
import time
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
        self.service = Service(ChromeDriverManager().install())
        self.browser = webdriver.Chrome(service=self.service)

    def open_page(self, url: str):
        self.browser.get(url)

    def close_browser(self):
        self.browser.quit()

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
        div = self.browser.find_element(by=by, value=value)
        inputs = div.find_elements(By.CSS_SELECTOR, "div > input")

        for input in inputs:
            dia = input.get_attribute("data-date")
            input.click()
            time.sleep(1)
            horarios = self.get_info_selector(by=By.ID, value="hoursBody")
            time.sleep(1)
            turno: Turnos = {"dia": dia, "horarios": horarios}
            self.turnos.append(turno)

        print(self.turnos)

    def filter_turns(self, hour: str):
        def has_hour(turno: Turnos) -> bool:
            return hour in turno["horarios"]

        filtered_turns = list(filter(has_hour, self.turnos))
        return filtered_turns


if __name__ == "__main__":
    start_time = time.time()
    browser = None

    try:
        browser = Browser()
        browser.open_page(url_login)

        WebDriverWait(browser.browser, 10).until(
            EC.presence_of_element_located((By.ID, "zocial-mail"))
        )

        browser.click_button(by=By.ID, "zocial-mail")

        WebDriverWait(browser.browser, 10).until(
            EC.presence_of_element_located((By.ID, "password-text-field"))
        )

        browser.login_linkedin(username=my_username, password=my_password)

        browser.open_page(url_reserva)

        WebDriverWait(browser.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-start="primeros"]'))
        )

        browser.click_button(by=By.CSS_SELECTOR, '[data-start="primeros"]')

        WebDriverWait(browser.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "box-header-h"))
        )

        browser.get_info_test(by=By.CLASS_NAME, "box-header-h")

        selected_hour = "12:00 hs"

        filtrados = browser.filter_turns(hour=selected_hour)

        if filtrados:
            token = os.getenv("TOKEN")
            chat_id = os.getenv("CHAT_ID")

            mensaje = f"¡Se ha encontrado un turno disponible para las {selected_hour}! Para reservar el turno accede al siguiente link {url_reserva}"

            enviar_mensaje_telegram(mensaje, chat_id, token)
        else:
