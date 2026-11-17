"""Guarded Riot Client UI login. Credentials never leave the local machine."""
from __future__ import annotations

import os
import subprocess
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Callable

import httpx
import psutil
from pywinauto import Desktop


class LoginFailure(RuntimeError):
    pass


class LocalRiotApi:
    def __init__(self, port: int, password: str):
        self.base = f"https://127.0.0.1:{port}"
        self.password = password

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        with httpx.Client(verify=False, trust_env=False, timeout=3) as client:
            return client.request(
                method, self.base + path, auth=("riot", self.password), **kwargs
            )

    def ready(self) -> bool:
        try:
            return self.request("GET", "/help").is_success
        except httpx.HTTPError:
            return False

    def username(self) -> str | None:
        try:
            response = self.request("GET", "/rso-auth/v1/authorization/userinfo")
            if response.status_code != 200:
                return None
            info = response.json().get("userInfo", {})
            if isinstance(info, str):
                import json

                info = json.loads(info)
            return str(info.get("username", "")).strip() or None
        except (httpx.HTTPError, ValueError, AttributeError):
            return None

    def sign_out(self) -> bool:
        try:
            help_response = self.request("GET", "/help")
            functions = help_response.json().get("functions", {})
            if "DeletePlayerSessionLifecycleV1Session" not in functions:
                return False
            result = self.request("DELETE", "/player-session-lifecycle/v1/session")
            return result.is_success
        except (httpx.HTTPError, ValueError, AttributeError):
            return False

    def launch_league(self) -> bool:
        try:
            response = self.request(
                "POST",
                "/product-launcher/v1/products/league_of_legends/patchlines/live",
                json={},
            )
            return response.is_success or response.status_code == 423
        except httpx.HTTPError:
            return False


def _local_api() -> LocalRiotApi | None:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    lockfile = Path(local) / "Riot Games" / "Riot Client" / "Config" / "lockfile"
    try:
        parts = lockfile.read_text(encoding="utf-8").strip().split(":")
        port, password = int(parts[2]), parts[3]
        if 1 <= port <= 65535 and password:
            return LocalRiotApi(port, password)
    except (OSError, ValueError, IndexError):
        pass
    return None


def _client_process_running(client_path: Path) -> bool:
    expected = str(client_path.resolve()).casefold()
    for process in psutil.process_iter(("exe",)):
        try:
            executable = process.info.get("exe")
            if executable and str(Path(executable).resolve()).casefold() == expected:
                return True
        except (psutil.Error, OSError):
            continue
    return False


def _league_is_running() -> bool:
    names = {"leagueclient.exe", "leagueclientux.exe", "league of legends.exe"}
    for process in psutil.process_iter(("name",)):
        try:
            if (process.info.get("name") or "").casefold() in names:
                return True
        except psutil.Error:
            continue
    return False


def _riot_install_executable(executable: str | None, services_path: Path) -> bool:
    if not executable:
        return False
    image = Path(executable).resolve()
    services = services_path.resolve()
    root = services.parent
    name = image.name.casefold()
    if name == "riotclientux.exe":
        return image.parent == root
    if name == "riot client.exe":
        return image.parent in (root, root / "RiotClientElectron")
    return False


def _find_login_form(services_path: Path):
    for window in Desktop(backend="uia").windows(visible_only=True):
        try:
            pid = window.element_info.process_id
            executable = psutil.Process(pid).exe()
            if not _riot_install_executable(executable, services_path):
                continue
            edits = window.descendants(control_type="Edit")
            password = next((item for item in edits if item.element_info.is_password), None)
            username = next((item for item in edits if not item.element_info.is_password), None)
            if username is not None and password is not None:
                return window, username, password
        except (psutil.Error, OSError, RuntimeError, AttributeError):
            continue
    return None


def _focus_is_target(window, services_path: Path) -> bool:
    try:
        import ctypes

        if int(ctypes.windll.user32.GetForegroundWindow()) != int(window.handle):
            return False
        process = psutil.Process(window.element_info.process_id)
        return _riot_install_executable(process.exe(), services_path)
    except (AttributeError, OSError, TypeError, ValueError):
        return False


class _KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("virtual_key", wintypes.WORD),
        ("scan_code", wintypes.WORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("extra", ctypes.c_void_p),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
        ("data", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("extra", ctypes.c_void_p),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("mouse", _MouseInput), ("keyboard", _KeyboardInput)]


class _Input(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("type", wintypes.DWORD), ("value", _InputUnion)]


def _send_key(window, services_path: Path, key: int, flags: int) -> None:
    if not _focus_is_target(window, services_path):
        raise LoginFailure("Riot Client perdió el foco; se detuvo el relleno por seguridad.")
    event = _Input(type=1, keyboard=_KeyboardInput(key, 0, flags, 0, None))
    if ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(_Input)) != 1:
        raise LoginFailure("Windows rechazó la entrada de teclado dirigida a Riot Client.")


def _send_virtual_key(window, services_path: Path, key: int) -> None:
    _send_key(window, services_path, key, 0)
    _send_key(window, services_path, key, 0x0002)


def _replace_field_text(window, field, value: str, services_path: Path) -> None:
    field.click_input()
    if not _focus_is_target(window, services_path):
        raise LoginFailure("Riot Client perdió el foco; se detuvo el relleno por seguridad.")
    # Select and clear the field, then send Unicode input directly to the
    # verified Riot window. Credentials are never copied to the clipboard.
    _send_key(window, services_path, 0x11, 0)  # Ctrl down
    _send_key(window, services_path, 0x41, 0)  # A down
    _send_key(window, services_path, 0x41, 0x0002)
    _send_key(window, services_path, 0x11, 0x0002)
    _send_virtual_key(window, services_path, 0x08)  # Backspace
    encoded = value.encode("utf-16-le")
    for index in range(0, len(encoded), 2):
        code_unit = int.from_bytes(encoded[index:index + 2], "little")
        # Set the scan code after constructing the event; VK_PACKET is used
        # for Unicode text and preserves punctuation in passwords.
        event = _Input(type=1, keyboard=_KeyboardInput(0, code_unit, 0x0004, 0, None))
        if not _focus_is_target(window, services_path):
            raise LoginFailure("Riot Client perdió el foco; se detuvo el relleno por seguridad.")
        if ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(_Input)) != 1:
            raise LoginFailure("Windows rechazó la entrada de teclado dirigida a Riot Client.")
        release = _Input(type=1, keyboard=_KeyboardInput(0, code_unit, 0x0004 | 0x0002, 0, None))
        if ctypes.windll.user32.SendInput(1, ctypes.byref(release), ctypes.sizeof(_Input)) != 1:
            raise LoginFailure("Windows rechazó la entrada de teclado dirigida a Riot Client.")


def _fill_login_form(
    window, username_field, password_field, username: str, password: str, services_path: Path
) -> None:
    try:
        window.set_focus()
        if not _focus_is_target(window, services_path):
            raise LoginFailure("Windows no permitió enfocar Riot Client; no se escribieron las credenciales.")
        _replace_field_text(window, username_field, username, services_path)
        _replace_field_text(window, password_field, password, services_path)
        buttons = window.descendants(control_type="Button")
        submit = next((
            button for button in buttons
            if any(term in (button.element_info.name or "").casefold()
                   for term in ("sign in", "log in", "iniciar sesión", "acceder"))
        ), None)
        if submit is not None:
            submit.click_input()
        else:
            password_field.set_focus()
            if not _focus_is_target(window, services_path):
                raise LoginFailure("Riot Client perdió el foco; no se envió el formulario.")
            _send_virtual_key(window, services_path, 0x0D)
    except LoginFailure:
        raise
    except Exception as exc:
        raise LoginFailure(
            "No se pudo rellenar el formulario de Riot Client. Comprueba que esté mostrando el inicio de sesión."
        ) from exc


def run_login(
    client_path: Path,
    username: str,
    password: str,
    report: Callable[[str, str], None],
) -> None:
    """Sign in through Riot's visible login form and ask the client to start LoL."""
    report("client", "Comprobando Riot Client…")
    if not _client_process_running(client_path):
        try:
            subprocess.Popen([str(client_path)], cwd=str(client_path.parent), close_fds=True)
        except OSError as exc:
            raise LoginFailure("No se pudo abrir Riot Client.") from exc

    api = None
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        api = _local_api()
        if api and api.ready():
            break
        report("client", "Esperando a que Riot Client termine de iniciar…")
        time.sleep(1)
    if api is None or not api.ready():
        raise LoginFailure("Riot Client no inició su servicio local dentro del tiempo esperado.")

    current = api.username()
    if current and current.casefold() == username.casefold():
        report("launch", "La cuenta ya está iniciada. Abriendo League of Legends…")
        if not api.launch_league():
            raise LoginFailure("Riot Client no aceptó la orden de abrir League of Legends.")
        return

    if current:
        if _league_is_running():
            raise LoginFailure("Cierra League of Legends antes de cambiar a otra cuenta.")
        report("signout", "Cambiando la sesión actual de Riot…")
        if not api.sign_out():
            raise LoginFailure("Riot Client no permitió cerrar la sesión actual. Ciérrala desde el cliente e inténtalo otra vez.")
        signout_deadline = time.monotonic() + 30
        while time.monotonic() < signout_deadline and api.username() is not None:
            time.sleep(0.5)
        if api.username() is not None:
            raise LoginFailure("Riot Client no terminó de cerrar la sesión anterior.")

    report("credentials", "Esperando el formulario de acceso de Riot Client…")
    form = None
    form_deadline = time.monotonic() + 90
    while time.monotonic() < form_deadline:
        form = _find_login_form(client_path)
        if form:
            break
        time.sleep(0.7)
    if not form:
        raise LoginFailure(
            "No se detectó el formulario de Riot Client. Si aparece una verificación, complétala en el cliente y vuelve a intentar."
        )

    report("typing", "Escribiendo las credenciales guardadas en Riot Client…")
    window, username_field, password_field = form
    expected_username = username.casefold()
    _fill_login_form(window, username_field, password_field, username, password, client_path)
    username = password = ""

    report("verification", "Esperando la respuesta de Riot. Si solicita MFA o CAPTCHA, complétalo en Riot Client…")
    auth_deadline = time.monotonic() + 300
    while time.monotonic() < auth_deadline:
        current = api.username()
        if current:
            if current.casefold() != expected_username:
                raise LoginFailure("Riot inició una sesión distinta de la cuenta seleccionada.")
            report("launch", "Riot confirmó la sesión. Abriendo League of Legends…")
            if not api.launch_league():
                raise LoginFailure("Riot inició sesión, pero no aceptó la orden de abrir League of Legends.")
            return
        time.sleep(1)
    raise LoginFailure("Riot no confirmó el inicio de sesión dentro del tiempo esperado.")
