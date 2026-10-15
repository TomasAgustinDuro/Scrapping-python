import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    Playwright,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from telegram_sender import enviar_mensaje_telegram

load_dotenv()

url_login = "https://login.buenosaires.gob.ar/"
url_reserva = (
    "https://formulario-sigeci.buenosaires.gob.ar/InicioTramiteComun?idPrestacion=5206"
)

my_username = os.getenv("MY_USERNAME")
my_password = os.getenv("MY_PASSWORD")
telegram_token = os.getenv("TOKEN")
telegram_chat_id = os.getenv("CHAT_ID")

heartbeat_file = Path(__file__).parent / "last_heartbeat.txt"


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
    """Encapsula las interacciones con el navegador vía Playwright.

    Gestiona el ciclo de vida de browser/context/page, la autenticación
    en el portal GCBA, la navegación del formulario de reserva y la
    extracción de turnos disponibles del calendario.
    """

    def __init__(self, playwright: Playwright):
        """Lanza Chromium y crea un context con viewport y user-agent fijos.

        El user-agent y el viewport se configuran a nivel de context (no
        de browser) porque son los parámetros que, en la versión Selenium
        original, ayudaban a evitar que el portal detecte automation
        (ver build_chrome_options en scrapper_date.py). headless se
        decide dinámicamente: en CI corre sin interfaz gráfica, en local
        se puede ver la ventana para debuggear.

        Args:
            playwright: Instancia de Playwright ya iniciada (viene del
                `with sync_playwright() as p:` en run()).
        """
        is_ci = bool(os.getenv("CI") or os.getenv("HEADLESS"))

        self.browser = playwright.chromium.launch(headless=is_ci)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.new_page()

    def open_login_page(self, url: str):
        self.page.goto(url)
        self.page.locator("#email").fill(my_username)
        self.page.locator("#password-text-field").fill(my_password)
        self.page.locator("#login").click()

    def open_reserve_page(self, url: str):
        self.page.goto(url)

        self.page.locator('[data-start="fecha"]').click()

    def change_month(self):
        """Intenta avanzar al mes siguiente en el calendario del portal.

        Distingue dos motivos de fallo distintos en los logs:
        - No se pudo abrir el selector de mes: indicio de que el HTML
          del portal cambió (anómalo, merece atención).
        - El mes siguiente no está en el dropdown: esperado y normal
          mientras el portal no lo habilite todavía.

        Returns:
            True si el cambio de mes fue exitoso, False en cualquier
            otro caso (sin mes siguiente habilitado o fallo técnico).
        """
        try:
            actual_month_str = self.page.locator("#monthSelected").get_attribute(
                "data-month"
            )

            actual_month = int(actual_month_str)

            next_month_str = str((actual_month % 12) + 1).zfill(2)

            dropdown_button = self.page.locator("#months button.dropbtn")

            dropdown_button.click(timeout=3000)
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            print(
                f"No se pudo abrir el selector de mes "
                f"(¿cambió el HTML del portal?): {error!s}"
            )
            return False

        try:
            next_month_selector = (
                f"#months .dropdown-content [data-month='{next_month_str}']"
            )

            next_option = self.page.locator(next_month_selector)

            next_option.click(timeout=3000)
        except (PlaywrightError, PlaywrightTimeoutError):
            print(
                f"Mes {next_month_str} todavía no está habilitado "
                "(normal si falta tiempo)."
            )
            return False

        new_month = self.page.locator("#monthSelected").get_attribute("data-month")

        return new_month == next_month_str

    def extract_calendar_turns(self):
        self.page.locator("#calendar").wait_for(state="visible", timeout=4000)
        day_elements = self.page.locator("#calendar div > div > h4").all()
        save_button = self.page.locator("div.container-button  #save ")

        obtained_turns = []

        for day_element in day_elements:
            try:
                dia = day_element.get_attribute("data-date")
                if not dia:
                    continue
                day_element.click()

                try:
                    save_button.wait_for(state="visible", timeout=3000)
                    save_button.click()

                    hours_element = self.page.locator("#hoursBody")

                    turno: Turnos = {"dia": dia, "horarios": hours_element.inner_text()}

                    obtained_turns.append(turno)

                    self.page.locator("#edit").click()
                except PlaywrightTimeoutError:
                    continue

            except PlaywrightError as error:
                print(error)

        return obtained_turns

    def filter_turns(self, hours: list[str], turns: list[Turnos]) -> list[Turnos]:
        """Filtra los turnos acumulados para conservar solo los que contienen las horas deseadas.

        Args:
            hours: Lista de strings con los horarios de interés (ej: ["19:00 hs"]).

        Returns:
            Lista de Turnos que contienen al menos uno de los horarios solicitados.
        """

        def has_requested_hour(turn: Turnos) -> bool:
            """Verifica si alguna de las horas solicitadas está en el turno."""
            return any(hour in turn["horarios"] for hour in hours)

        return list(filter(has_requested_hour, turns))

    def close_browser(self) -> None:
        """Cierra el context y el navegador, liberando los recursos."""
        self.context.close()
        self.browser.close()


def return_filter_turns(filtered_turns, selected_hours: list[str]):
    turnos_per_hour: dict[str, list[str]] = {hour: [] for hour in selected_hours}

    for turn in filtered_turns:
        formatted_day = datetime.strptime(turn["dia"], "%Y-%m-%d").strftime("%d/%m")

        for hour in selected_hours:
            if hour in turn["horarios"]:
                turnos_per_hour[hour].append(formatted_day)

    return turnos_per_hour


def create_message(turnos_per_hour: dict[str, list[str]]):
    return [
        f"Turnos disponibles a las {hour}: {', '.join(dias)}"
        for hour, dias in turnos_per_hour.items()
        if dias
    ]


def send_message(messages: str):
    if messages:
        for message in messages:
            print(f"  ✓ {message}", flush=True)
        message = (
            "¡Se han encontrado turnos disponibles!\n"
            + "\n".join(messages)
            + f"\nPara reservar, accedé al siguiente link: {url_reserva}"
        )

        enviar_mensaje_telegram(
            mensaje=message,
            chat_id=telegram_chat_id,
            token=telegram_token,
        )


def read_last_heartbeat_date() -> str | None:
    """Lee la fecha (ISO 8601) del último heartbeat enviado, si existe.

    Returns:
        El string de fecha guardado en heartbeat_file, o None si el
        archivo no existe todavía (nunca se envió un heartbeat).
    """
    if not heartbeat_file.exists():
        return None
    return heartbeat_file.read_text(encoding="utf-8").strip() or None


def save_heartbeat_date(today: date) -> None:
    """Persiste la fecha de hoy como último heartbeat enviado.

    Args:
        today: Fecha a guardar como referencia del último heartbeat.
    """
    heartbeat_file.write_text(today.isoformat(), encoding="utf-8")


def send_heartbeat_if_needed() -> None:
    """Envía un heartbeat diario por Telegram si todavía no se envió hoy.

    Se usa para confirmar que el bot sigue corriendo (y, de paso, para
    generar actividad real en el repo al commitear heartbeat_file,
    evitando que GitHub Actions pause el workflow programado por
    inactividad luego de 60 días).
    """
    today = date.today()

    if read_last_heartbeat_date() == today.isoformat():
        print("Heartbeat de hoy ya enviado, se omite.", flush=True)
        return

    enviar_mensaje_telegram(
        mensaje="✅ El bot de turnos sigue funcionando. No se encontraron turnos hoy.",
        chat_id=telegram_chat_id,
        token=telegram_token,
    )
    save_heartbeat_date(today)


def send_failure_alert(error: Exception) -> None:
    """Notifica por Telegram que el script falló con una excepción.

    A diferencia del heartbeat, esta alerta se envía SIEMPRE que ocurre
    un fallo, sin límite de frecuencia por día, porque cada fallo es
    información nueva y relevante para el usuario.

    Args:
        error: Excepción capturada que interrumpió la ejecución.
    """
    enviar_mensaje_telegram(
        mensaje=f"❌ El bot de turnos falló: {error!s}",
        chat_id=telegram_chat_id,
        token=telegram_token,
    )


def run():
    selected_hours = ["19:00"]
    browser = None

    with sync_playwright() as p:
        try:
            print("Comenzamos..")

            browser = Browser(playwright=p)

            browser.open_login_page(url_login)

            browser.open_reserve_page(url_reserva)

            turnos = browser.extract_calendar_turns()

            if browser.change_month():
                otro_mes_turnos = browser.extract_calendar_turns()

                turnos.extend(otro_mes_turnos)

            turnos_filtrados = browser.filter_turns(selected_hours, turnos)

            turnos_agrupados = return_filter_turns(turnos_filtrados, selected_hours)

            mensaje = create_message(turnos_agrupados)

            if mensaje:
                send_message(mensaje)
                print(mensaje)
            else:
                print("No hubo turnos encontrados")
                send_heartbeat_if_needed()

            print("Finalizado")
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            print(f"❌ El script falló: {error!s}", file=sys.stderr)
            send_failure_alert(error)
            sys.exit(1)
        finally:
            if browser is not None:
                browser.close_browser()


if __name__ == "__main__":
    run()
