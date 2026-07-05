"""
Módulo principal del bot de scraping de turnos de pádel GCBA.

Se autentica en el portal login.buenosaires.gob.ar, navega al formulario
de reserva SIGECI, recorre el calendario disponible, extrae los horarios
libres y envía una alerta por email cuando encuentra los turnos deseados.

Ejecución:
    python scrapper_date.py
"""

import os
import sys
import time
from datetime import datetime
from typing import List, TypedDict

from dotenv import load_dotenv
from email_sender import email_sender
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


load_dotenv()

my_username = os.getenv("MY_USERNAME")
my_password = os.getenv("MY_PASSWORD")

url_login = "https://login.buenosaires.gob.ar/"
url_reserva = (
    "https://formulario-sigeci.buenosaires.gob.ar/InicioTramiteComun?idPrestacion=5206"
)


def build_chrome_options() -> Options:
    """Construye y retorna las opciones de Chrome según el entorno.

    En GitHub Actions (CI) corre headless. En local corre con ventana
    visible para facilitar el debugging.

    Returns:
        Instancia de Options con los argumentos configurados.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # En CI (GitHub Actions) o si se indica explícitamente, correr headless
    if os.getenv("CI") or os.getenv("HEADLESS"):
        chrome_options.add_argument("--headless=new")

    return chrome_options


class Turnos(TypedDict):
    """Estructura de datos que representa un turno disponible en el calendario.

    Attributes:
        dia: Fecha del turno en formato ISO 8601 (YYYY-MM-DD).
        horarios: Texto plano con los horarios disponibles para ese día,
                  tal como los devuelve el elemento #hoursBody del portal.
    """

    dia: str
    horarios: str


class Browser:
    """Encapsula todas las interacciones con el navegador Chrome headless.

    Gestiona el ciclo de vida del WebDriver, la navegación entre páginas,
    la autenticación en el portal GCBA, la extracción de turnos del calendario
    y el filtrado por horarios de interés.

    Attributes:
        driver: Instancia del WebDriver de Chrome.
        turnos: Lista acumulada de turnos extraídos del calendario durante
                la sesión actual.
    """

    driver: webdriver.Chrome
    turnos: List[Turnos]

    def __init__(self) -> None:
        """Inicializa el WebDriver de Chrome.

        Selenium Manager (incluido en selenium>=4.6) detecta y descarga
        automáticamente el ChromeDriver compatible con el Chrome instalado,
        tanto en GitHub Actions como en entorno local.
        """
        self.turnos = []
        self.driver = webdriver.Chrome(options=build_chrome_options())

    def open_page(self, url: str) -> None:
        """Navega a la URL indicada en el navegador.

        Args:
            url: URL completa a la que debe navegar el driver.
        """
        self.driver.get(url)

    def close_browser(self) -> None:
        """Cierra el navegador y libera los recursos del driver."""
        self.driver.quit()

    def add_inputs(self, by: By, value: str, text: str) -> None:
        """Espera a que un campo de texto sea clickeable y escribe en él.

        Args:
            by: Estrategia de localización del elemento (By.ID, By.CSS_SELECTOR, etc.).
            value: Selector correspondiente a la estrategia elegida.
            text: Texto a escribir en el campo.
        """
        field = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((by, value))
        )
        field.send_keys(text)

    def click_button(self, by: By, value: str) -> None:
        """Espera a que un botón sea clickeable y lo presiona.

        Args:
            by: Estrategia de localización del elemento.
            value: Selector correspondiente a la estrategia elegida.
        """
        button = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((by, value))
        )
        button.click()

    def login(self, username: str, password: str) -> None:
        """Completa y envía el formulario de login del portal GCBA.

        Args:
            username: Email registrado en el portal buenosaires.gob.ar.
            password: Contraseña asociada a la cuenta del portal.
        """
        self.add_inputs(by=By.ID, value="email", text=username)
        self.add_inputs(by=By.ID, value="password-text-field", text=password)
        self.click_button(by=By.ID, value="login")

    def change_month(self) -> bool:
        """Intenta avanzar al mes siguiente en el calendario del portal.

        Lee el mes actual del elemento #monthSelected, calcula el siguiente
        y hace click en la opción correspondiente del dropdown.

        Returns:
            True si el cambio de mes fue exitoso, False si no hay mes siguiente.
        """
        try:
            month_element = self.driver.find_element(By.ID, "monthSelected")
            mes_actual_str = month_element.get_attribute("data-month")
            mes_actual = int(mes_actual_str)

            mes_siguiente_str = str(mes_actual + 1).zfill(2)

            dropdown_button = self.driver.find_element(By.CSS_SELECTOR, "#months button.dropbtn")
            self.driver.execute_script("arguments[0].click()", dropdown_button)
            time.sleep(0.5)

            selector_mes_sig = f"#months .dropdown-content [data-month='{mes_siguiente_str}']"

            opcion_siguiente = self.driver.find_element(By.CSS_SELECTOR, selector_mes_sig)
            self.driver.execute_script("arguments[0].click();", opcion_siguiente)
            time.sleep(1)
            return True
        except Exception as month_error:
            print(f"Error al intentar cambiar de mes: {str(month_error)}")
            return False

    def extract_calendar_turns(self, by: By, value: str) -> None:
        """Recorre el calendario del portal y extrae los turnos disponibles por día.

        Para cada día visible en el calendario, hace click, confirma con "save",
        lee los horarios de #hoursBody, los almacena en self.turnos y vuelve
        al estado anterior con el botón "edit".

        Los errores por día se capturan de forma aislada para que un día
        problemático no interrumpa el recorrido completo.

        Args:
            by: Estrategia de localización del contenedor del calendario.
            value: Selector del contenedor del calendario.
        """
        try:
            calendar_div = self.driver.find_element(by=by, value=value)
            button_container = self.driver.find_element(
                By.CSS_SELECTOR, "div.container-button"
            )
            save_button = button_container.find_element(By.ID, "save")
            day_elements = calendar_div.find_elements(By.CSS_SELECTOR, "div > div > h4")

            for day_element in day_elements:
                try:
                    dia = day_element.get_attribute("data-date")
                    if not dia:
                        continue

                    day_element.click()

                    if save_button.is_displayed() and save_button.is_enabled():
                        save_button.click()

                        hours_element = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.ID, "hoursBody"))
                        )

                        turno: Turnos = {"dia": dia, "horarios": hours_element.text}
                        self.turnos.append(turno)

                        edit_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.ID, "edit"))
                        )
                        edit_button.click()

                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable(save_button)
                        )
                    else:
                        continue

                except Exception as day_error:
                    print(f"Error al procesar el día {dia}: {str(day_error)}")
                    continue

                time.sleep(1)

        except Exception as calendar_error:
            print(f"Error al procesar el calendario: {str(calendar_error)}")

    def filter_turns(self, hours: List[str]) -> List[Turnos]:
        """Filtra los turnos acumulados para conservar solo los que contienen las horas deseadas.

        Args:
            hours: Lista de strings con los horarios de interés (ej: ["19:00 hs"]).

        Returns:
            Lista de Turnos que contienen al menos uno de los horarios solicitados.
        """
        def has_requested_hour(turno: Turnos) -> bool:
            """Verifica si alguna de las horas solicitadas está en el turno."""
            return any(hour in turno["horarios"] for hour in hours)

        return list(filter(has_requested_hour, self.turnos))

def run() -> None:
    """Ejecuta el flujo completo del scraper de turnos de pádel GCBA."""
    browser = None
    try:
        print("[1/7] Iniciando navegador...", flush=True)
        browser = Browser()

        print("[2/7] Abriendo portal de login...", flush=True)
        browser.open_page(url_login)

        WebDriverWait(browser.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "email"))
        )
        browser.click_button(by=By.ID, value="email")

        WebDriverWait(browser.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "password-text-field"))
        )

        print("[3/7] Haciendo login...", flush=True)
        browser.login(username=my_username, password=my_password)

        print("[4/7] Navegando al formulario de reserva...", flush=True)
        browser.open_page(url_reserva)

        WebDriverWait(browser.driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-start="fecha"]'))
        )
        browser.click_button(by=By.CSS_SELECTOR, value='[data-start="fecha"]')

        WebDriverWait(browser.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "calendar"))
        )

        print("[5/7] Extrayendo turnos del mes actual...", flush=True)
        browser.extract_calendar_turns(By.ID, "calendar")
        print(f"       Turnos mes actual: {len(browser.turnos)}", flush=True)

        print("[6/7] Intentando cambiar de mes...", flush=True)
        if browser.change_month():
            browser.extract_calendar_turns(By.ID, "calendar")
            print(f"       Turnos acumulados: {len(browser.turnos)}", flush=True)
        else:
            print("       No se pudo cambiar de mes (normal si no hay mes siguiente)", flush=True)

        print(f"\n=== TURNOS ENCONTRADOS: {len(browser.turnos)} ===", flush=True)
        for turno in browser.turnos:
            print(f"  - {turno['dia']}: {turno['horarios'][:80]}", flush=True)

        selected_hours = ["15:00 hs", "19:00 hs"]

        # Agrupa los turnos filtrados por hora
        turnos_por_hora: dict[str, List[str]] = {hour: [] for hour in selected_hours}

        for turno in browser.filter_turns(hours=selected_hours):
            dia_formateado = datetime.strptime(
                turno["dia"], "%Y-%m-%d"
            ).strftime("%d/%m")
            for hour in selected_hours:
                if hour in turno["horarios"]:
                    turnos_por_hora[hour].append(dia_formateado)

        # Construye mensajes
        mensajes = [
            f"Turnos disponibles a las {hour}: {', '.join(dias)}"
            for hour, dias in turnos_por_hora.items()
            if dias
        ]

        print(f"\n[7/7] Resultado del filtrado:", flush=True)
        if mensajes:
            for msg in mensajes:
                print(f"  ✓ {msg}", flush=True)
            mensaje = (
                "¡Se han encontrado turnos disponibles!\n"
                + "\n".join(mensajes)
                + f"\nPara reservar, accedé al siguiente link: {url_reserva}"
            )
            print("\nEnviando email...", flush=True)
            email_sender(mensaje)
            print("Email enviado.", flush=True)
        else:
            print("  ✗ No hay turnos en los horarios buscados. No se envía email.", flush=True)

    except Exception as run_error:
        print(f"\n❌ El script falló: {str(run_error)}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        if browser is not None:
            browser.close_browser()
        print("\nScript finalizado.", flush=True)


if __name__ == "__main__":
    run()
