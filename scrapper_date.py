"""
Módulo principal del bot de scraping de turnos de pádel GCBA.

Se autentica en el portal login.buenosaires.gob.ar, navega al formulario
de reserva SIGECI, recorre el calendario disponible, extrae los horarios
libres y envía una alerta por email cuando encuentra los turnos deseados.

Ejecución:
    python scrapper_date.py
"""

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import TypedDict, List
from email_sender import email_sender
from dotenv import load_dotenv
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options


load_dotenv()

my_username = os.getenv("MY_USERNAME")
my_password = os.getenv("MY_PASSWORD")

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")


url_login = "https://login.buenosaires.gob.ar/"
url_reserva = (
    "https://formulario-sigeci.buenosaires.gob.ar/InicioTramiteComun?idPrestacion=5206"
)


class Turnos(TypedDict):
    """Estructura de datos que representa un turno disponible en el calendario.

    Attributes:
        dia: Fecha del turno en formato ISO 8601 (YYYY-MM-DD).
        horarios: Texto plano con los horarios disponibles para ese día,
                  tal como los devuelve el elemento #hoursBody del portal.
    """

    dia: str
    horarios: List[str]


class Browser:
    """Encapsula todas las interacciones con el navegador Chrome headless.

    Gestiona el ciclo de vida del WebDriver, la navegación entre páginas,
    la autenticación en el portal GCBA, la extracción de turnos del calendario
    y el filtrado por horarios de interés.

    Attributes:
        browser: Instancia del WebDriver de Chrome.
        turnos: Lista acumulada de turnos extraídos del calendario durante
                la sesión actual.
    """

    browser: webdriver.Chrome
    turnos: List[Turnos] = []

    def __init__(self) -> None:
        """Inicializa el WebDriver de Chrome con opciones headless.

        Utiliza webdriver-manager para descargar y gestionar automáticamente
        la versión correcta de ChromeDriver según el Chrome instalado.
        """
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

    def open_page(self, url: str) -> None:
        """Navega a la URL indicada en el navegador.

        Args:
            url: URL completa a la que debe navegar el browser.
        """
        self.browser.get(url)

    def close_browser(self) -> None:
        """Cierra la ventana activa del navegador y libera los recursos del driver."""
        self.browser.close()

    def add_inputs(self, by: By, value: str, text: str) -> None:
        """Espera a que un campo de texto esté presente en el DOM y escribe en él.

        Usa WebDriverWait con un timeout de 10 segundos para evitar condiciones
        de carrera con páginas de carga lenta.

        Args:
            by: Estrategia de localización del elemento (By.ID, By.CSS_SELECTOR, etc.).
            value: Selector correspondiente a la estrategia elegida.
            text: Texto a escribir en el campo.
        """
        field = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((by, value))
        )
        field.send_keys(text)

    def click_button(self, by: By, value: str) -> None:
        """Espera a que un botón sea clickeable y lo presiona.

        Args:
            by: Estrategia de localización del elemento.
            value: Selector correspondiente a la estrategia elegida.
        """
        button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((by, value))
        )
        button.click()

    def login_linkedin(self, username: str, password: str) -> None:
        """Completa y envía el formulario de login del portal GCBA.

        Rellena los campos de email y contraseña, y presiona el botón de login.
        Asume que la página de login ya está cargada y el formulario visible.

        Args:
            username: Email registrado en el portal buenosaires.gob.ar.
            password: Contraseña asociada a la cuenta del portal.
        """
        self.add_inputs(by=By.ID, value="email", text=username)
        self.add_inputs(by=By.ID, value="password-text-field", text=password)
        self.click_button(by=By.ID, value="login")

    def get_info_selector(self, by: By, value: str) -> List[str]:
        """Extrae el texto de todos los elementos <span> dentro de un contenedor.

        Método auxiliar para leer listas de horarios renderizadas como spans
        dentro de un div padre.

        Args:
            by: Estrategia de localización del contenedor padre.
            value: Selector del contenedor padre.

        Returns:
            Lista de strings con el texto de cada <span> encontrado.
        """
        horarios: List[str] = []
        element = self.browser.find_element(by=by, value=value)
        spans = element.find_elements(By.TAG_NAME, "span")

        for span in spans:
            horarios.append(span.text)

        return horarios

    def get_info_test(self, by: By, value: str) -> None:
        """Recorre el calendario del portal y extrae los turnos disponibles por día.

        Para cada día visible en el calendario (#calendar), hace click en él,
        confirma la selección mediante el botón "save", lee los horarios
        disponibles del elemento #hoursBody, los almacena en self.turnos
        y vuelve al estado anterior presionando el botón "edit".

        Los errores por día individual se capturan de forma aislada para que
        un día problemático no interrumpa el recorrido completo.

        Args:
            by: Estrategia de localización del contenedor del calendario.
            value: Selector del contenedor del calendario (normalmente By.ID, "calendar").
        """
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
                                EC.presence_of_element_located((By.ID, "edit"))
                            )
                            edit_button.click()
                            time.sleep(1)
                        else:
                            continue
                except Exception as e:
                    print(f"Error al procesar input con data-date {dia}: {str(e)}")
                    continue

                time.sleep(1)

        except Exception as e:
            print(f"Error al procesar la información: {str(e)}")

    def filter_turns(self, hours: List[str]) -> List[Turnos]:
        """Filtra los turnos acumulados para conservar solo los que contienen las horas deseadas.

        Itera sobre self.turnos y retorna únicamente aquellos donde al menos
        una de las horas solicitadas aparece en el texto de horarios del turno.

        Args:
            hours: Lista de strings con los horarios de interés,
                   en el mismo formato que devuelve el portal (ej: "19:00 hs").

        Returns:
            Lista de Turnos que contienen al menos uno de los horarios solicitados.
        """
        def has_hour(turno: Turnos) -> bool:
            """Verifica si alguna de las horas seleccionadas está presente en el turno."""
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

    WebDriverWait(browser.browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-start="fecha"]'))
    )

    browser.click_button(by=By.CSS_SELECTOR, value='[data-start="fecha"]')

    WebDriverWait(browser.browser, 10).until(
        EC.presence_of_element_located((By.ID, "calendar"))
    )

    browser.get_info_test(By.ID, "calendar")

    selected_hours = ["15:00 hs", "19:00 hs"]  # Lista de horas a filtrar
    dias_formateados = []

    # Inicializa diccionarios para almacenar días filtrados por hora
    turnos_por_hora = {hour: [] for hour in selected_hours}

    # Filtra los turnos utilizando la lista de horas de interés
    filtrados = browser.filter_turns(hours=selected_hours)

    # Formatea las fechas (YYYY-MM-DD → DD/MM) y agrupa por hora
    for filtrado in filtrados:
        dia_formateado = datetime.strptime(filtrado["dia"], "%Y-%m-%d").strftime("%d/%m")
        for hour in selected_hours:
            if hour in filtrado["horarios"]:
                turnos_por_hora[hour].append(dia_formateado)

    # Construye los mensajes solo para las horas que tienen turnos disponibles
    mensajes = []
    for hour, dias in turnos_por_hora.items():
        if dias:
            dias_texto = ", ".join(dias)
            mensajes.append(f"Turnos disponibles a las {hour}: {dias_texto}")

    # Envía el email solo si hay al menos un turno disponible
    if mensajes:
        mensaje = (
            "¡Se han encontrado turnos disponibles!\n"
            + "\n".join(mensajes)
            + f"\nPara reservar, accede al siguiente link {url_reserva}"
        )
        email_sender(mensaje)

    end_time = time.time()
    duration = end_time - start_time
    print(f"Duración del script: {duration:.2f} segundos")
