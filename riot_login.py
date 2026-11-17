"""Riot Client sign-in using its own login renderer and local session API."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx
import psutil
import websocket


class LoginFailure(RuntimeError):
    pass


class LocalRiotApi:
    def __init__(self, port: int, token: str):
        self.base = f"https://127.0.0.1:{port}"
        self.token = token

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        with httpx.Client(verify=False, trust_env=False, timeout=4) as client:
            return client.request(method, self.base + path, auth=("riot", self.token), **kwargs)

    def ready(self) -> bool:
        try:
            return self.request("GET", "/help").is_success
        except httpx.HTTPError:
            return False

    def session(self) -> dict | None:
        try:
            response = self.request("GET", "/player-session-lifecycle/v1/session")
            return response.json() if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None

    def userinfo(self) -> dict | None:
        try:
            response = self.request("GET", "/rso-auth/v1/authorization/userinfo")
            if response.status_code != 200:
                return None
            info = response.json().get("userInfo", {})
            if isinstance(info, str):
                info = json.loads(info)
            return info if isinstance(info, dict) else None
        except (httpx.HTTPError, ValueError, AttributeError):
            return None

    def username(self) -> str | None:
        info = self.userinfo()
        return str(info.get("username", "")).strip() or None if info else None

    def follow_league_region(self, timeout: float = 10) -> None:
        """Match Riot Client's selected region to the signed-in account."""
        info = self.userinfo()
        try:
            current_response = self.request("GET", "/riotclient/region-locale")
            regions_response = self.request("GET", "/data-store/v1/system-settings/region_data")
            current = current_response.json() if current_response.status_code == 200 else None
            regions = regions_response.json() if regions_response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return
        if not info or not isinstance(current, dict) or not isinstance(regions, dict):
            return
        account_regions = [info.get("lol"), *(info.get("lol_region") or [])]
        platforms = [entry.get("cpid") for entry in account_regions
                     if isinstance(entry, dict) and entry.get("active") is not False and entry.get("cpid")]
        if not platforms:
            return
        current_region = str(current.get("region", ""))
        region_info = regions.get(current_region, {})
        if isinstance(region_info, dict) and region_info.get("rso_platform_id") in platforms:
            return
        platform = platforms[0]
        if platform in regions:
            target_region = platform
        else:
            target_region = next((name for name, data in regions.items()
                                  if isinstance(data, dict) and data.get("rso_platform_id") == platform), "")
        if not target_region or target_region == current_region:
            return
        self.request("PUT", "/riotclient/region-locale",
                     json={"region": target_region, "locale": current.get("locale", "en_GB")})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = self.request("GET", "/riotclient/region-locale")
                if response.status_code == 200 and response.json().get("region") == target_region:
                    return
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(0.5)
        raise LoginFailure("Riot Client no aplicó la región de la cuenta antes de abrir League.")

    def sign_out(self) -> bool:
        try:
            functions = self.request("GET", "/help").json().get("functions", {})
            if "DeletePlayerSessionLifecycleV1Session" not in functions:
                return False
            return self.request("DELETE", "/player-session-lifecycle/v1/session").is_success
        except (httpx.HTTPError, ValueError, AttributeError):
            return False

    def string_value(self, path: str) -> str | None:
        try:
            response = self.request("GET", path)
            value = response.json() if response.is_success else None
            return value if isinstance(value, str) and value else None
        except (httpx.HTTPError, ValueError):
            return None

    def launch_league(self) -> int | None:
        try:
            response = self.request(
                "POST", "/product-launcher/v1/products/league_of_legends/patchlines/live", json={}
            )
            return response.status_code
        except httpx.TimeoutException:
            # Riot can keep processing the launch after its request times out.
            return None
        except httpx.HTTPError:
            return -1

    def game_session(self) -> dict | None:
        try:
            response = self.request("GET", "/lol-login/v1/session")
            return response.json() if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None

    def patch_state(self) -> dict | None:
        try:
            response = self.request(
                "GET", "/patch-proxy/v2/patch-states/products/league_of_legends/patchlines/live"
            )
            return response.json() if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None


def _local_api() -> LocalRiotApi | None:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    lockfile = Path(local) / "Riot Games" / "Riot Client" / "Config" / "lockfile"
    try:
        parts = lockfile.read_text(encoding="utf-8").strip().split(":")
        port, token = int(parts[2]), parts[3]
        if 1 <= port <= 65535 and token:
            return LocalRiotApi(port, token)
    except (OSError, ValueError, IndexError):
        pass
    return None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _client_processes(root: Path) -> list[psutil.Process]:
    matches = []
    for process in psutil.process_iter(("name", "exe")):
        try:
            name = (process.info.get("name") or "").casefold()
            exe = process.info.get("exe")
            if name in {"riotclientservices.exe", "riot client.exe"} and exe and _inside(Path(exe), root):
                matches.append(process)
        except (psutil.Error, OSError):
            continue
    return matches


def _service_args(root: Path) -> list[str]:
    kept: list[str] = []
    for process in _client_processes(root):
        try:
            if (process.info.get("name") or "").casefold() != "riotclientservices.exe":
                continue
            for arg in process.cmdline()[1:]:
                if arg.startswith("--client-config-url=") and arg not in kept:
                    kept.append(arg)
        except (psutil.Error, OSError):
            continue
    return kept


def _quiet_popen(args: list[str], cwd: Path) -> subprocess.Popen:
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
               "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, cwd=str(cwd), **options)


def _stop_client(root: Path) -> None:
    deadline = time.monotonic() + 30
    for _ in range(4):
        processes = _client_processes(root)
        if not processes:
            return
        for process in processes:
            try:
                subprocess.run(
                    ["taskkill.exe", "/F", "/T", "/PID", str(process.pid)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=10, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        time.sleep(0.5)
        if time.monotonic() >= deadline:
            break
    if _client_processes(root):
        raise LoginFailure("No se pudo reiniciar Riot Client. Ciérralo y vuelve a intentarlo.")


def _wait_api(timeout: float, progress: Callable[[str], None]) -> LocalRiotApi:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        api = _local_api()
        if api and api.ready():
            return api
        progress("Esperando a que Riot Client prepare la sesión…")
        time.sleep(0.5)
    raise LoginFailure("Riot Client no inició su servicio de sesión dentro del tiempo esperado.")


def _renderer_args(service: Path, api: LocalRiotApi) -> tuple[Path, list[str]]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    data = local / "Riot Games" / "Riot Client"
    lock = (data / "Config" / "lockfile").read_text(encoding="utf-8").strip().split(":")
    if len(lock) != 5 or not lock[1].isdigit() or not lock[2].isdigit():
        raise LoginFailure("Riot Client no publicó un lockfile válido para iniciar sesión.")
    machine = api.string_value("/riotclient/machine-id")
    host_session = api.string_value("/product-session/v1/host-session/id")
    if not machine or not host_session:
        raise LoginFailure("Riot Client todavía está preparando sus datos de sesión.")
    root = service.parent
    renderer = root / "RiotClientElectron" / "Riot Client.exe"
    if not renderer.is_file():
        raise LoginFailure("No se encontró el renderizador de Riot Client.")
    args = [
        f"--app-port={lock[2]}", f"--remoting-auth-token={lock[3]}", f"--app-pid={lock[1]}",
        f"--app-root={root}", f"--user-data-root={data}",
        f"--log-dir={data / 'Logs' / 'Riot Client UX Logs'}",
        f"--machine-id={machine}", f"--session-id={host_session}",
        "--crashpad-environment=prod", "--enable-hardware-acceleration",
    ]
    return renderer, args


class Renderer:
    def __init__(self, script_path: Path):
        self.script = script_path.read_text(encoding="utf-8")
        self.process: subprocess.Popen | None = None
        self.socket = None
        self.port = 0
        self.sequence = 0

    def start(self, renderer_path: Path, args: list[str]) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        debug_args = [*args, "--allow-chrome-dev-tools", "--remote-debugging-address=127.0.0.1",
                      f"--remote-debugging-port={self.port}"]
        self.process = _quiet_popen([str(renderer_path), *debug_args], renderer_path.parent)
        deadline = time.monotonic() + 30
        endpoint = None
        with httpx.Client(trust_env=False, timeout=2) as client:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise LoginFailure("El renderizador de Riot Client se cerró inesperadamente.")
                try:
                    response = client.get(f"http://127.0.0.1:{self.port}/json/list")
                    if response.is_success:
                        pages = response.json()
                        target = next((p for p in pages if p.get("type") == "page"
                                       and p.get("title") == "Riot Client"), None)
                        if target:
                            candidate = target.get("webSocketDebuggerUrl", "")
                            parsed = urlparse(candidate)
                            if (parsed.scheme == "ws" and parsed.hostname == "127.0.0.1"
                                    and parsed.port == self.port and parsed.path.startswith("/devtools/page/")
                                    and not parsed.username and not parsed.password):
                                endpoint = candidate
                                break
                except (httpx.HTTPError, ValueError):
                    pass
                time.sleep(0.25)
        if not endpoint:
            raise LoginFailure("No se pudo conectar con el formulario interno de Riot Client.")
        try:
            self.socket = websocket.create_connection(
                endpoint, timeout=2, suppress_origin=True,
                http_no_proxy=["127.0.0.1", "localhost"], enable_multithread=True,
            )
            self.socket.settimeout(0.2)
        except Exception as exc:
            raise LoginFailure("No se pudo conectar con la ventana de acceso de Riot Client.") from exc
        if self.evaluate(self.script) is not True:
            raise LoginFailure("Riot Client no permitió preparar su formulario de acceso.")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.evaluate("globalThis.__leagueAccountsLogin.ready()") is True:
                time.sleep(1.5)
                return
            time.sleep(0.2)
        raise LoginFailure("El formulario de acceso de Riot Client no terminó de cargar.")

    def evaluate(self, expression: str):
        if self.socket is None:
            raise LoginFailure("La conexión al formulario de Riot Client se cerró.")
        self.sequence += 1
        request_id = self.sequence
        self.socket.send(json.dumps({"id": request_id, "method": "Runtime.evaluate",
                                     "params": {"expression": expression, "returnByValue": True,
                                                "awaitPromise": True}}))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                payload = self.socket.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as exc:
                raise LoginFailure("Se perdió la conexión con Riot Client.") from exc
            try:
                response = json.loads(payload)
            except (TypeError, ValueError):
                continue
            if response.get("id") != request_id:
                continue
            if response.get("error") or response.get("result", {}).get("exceptionDetails"):
                raise LoginFailure("Riot Client rechazó la operación del formulario.")
            return response.get("result", {}).get("result", {}).get("value")
        raise LoginFailure("Riot Client tardó demasiado en responder al formulario.")

    def close(self) -> None:
        if self.socket:
            try:
                self.socket.send(json.dumps({"id": 0, "method": "Browser.close"}))
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        if self.process:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None


def _launch_and_wait(api: LocalRiotApi, username: str,
                     report: Callable[[str, str], None]) -> None:
    """Retry launch while Riot patches, then confirm the game client opened."""
    deadline = time.monotonic() + 1800
    verified_user = api.username()
    if verified_user and verified_user.casefold() != username.casefold():
        raise LoginFailure("La sesión de Riot no coincide con la cuenta seleccionada.")
    api.follow_league_region()
    next_request = 0.0
    request_count = 0
    game_process_seen: float | None = None
    last_message = "Riot aceptó la sesión; esperando a que League of Legends se abra…"
    while time.monotonic() < deadline:
        current_api = _local_api()
        if current_api and current_api.ready():
            api = current_api
        current_user = api.username()
        if current_user and current_user.casefold() != username.casefold():
            raise LoginFailure("La sesión de Riot cambió a otra cuenta antes de abrir League of Legends.")

        game = api.game_session() or {}
        game_user = str(game.get("username", "")).strip()
        if game_user and game_user.casefold() != username.casefold():
            raise LoginFailure("League of Legends abrió con una cuenta distinta de la seleccionada.")
        running = _league_is_running()
        if running:
            if game_user and str(game.get("state", "")).upper() == "SUCCEEDED":
                report("launch", "League of Legends está abierto con la cuenta seleccionada.")
                return
            if game_process_seen is None:
                game_process_seen = time.monotonic()
            # Riot's game-session API can appear a few seconds after the process.
            if current_user and current_user.casefold() == username.casefold() and time.monotonic() - game_process_seen >= 30:
                report("launch", "El cliente de League of Legends está abierto con la cuenta seleccionada.")
                return
        else:
            game_process_seen = None

        patch = api.patch_state() or {}
        state = str(patch.get("state", ""))
        progress = patch.get("progress") if isinstance(patch.get("progress"), dict) else {}
        percent = progress.get("overallProgress")
        active_update = state in {"Updating", "Repairing", "OutOfDate", "NeedsRepair"}
        if active_update:
            if isinstance(percent, (int, float)):
                last_message = f"Riot está actualizando League of Legends ({max(0, min(100, percent)):.0f}%)."
            else:
                last_message = "Riot está descargando o reparando League of Legends…"
        else:
            last_message = "Riot aceptó la sesión; esperando a que League of Legends se abra…"

        now = time.monotonic()
        if now >= next_request:
            api.follow_league_region()
            status = api.launch_league()
            request_count += 1
            if status is None:
                last_message = "Riot está iniciando League of Legends; esperando respuesta del cliente…"
                next_request = now + 3
            elif status in range(200, 300) or status == 423:
                next_request = now + 6
            elif status == 424:
                # Riot uses 424 when it must patch the game before launch.
                next_request = now + 3
                active_update = True
                last_message = "Riot está preparando una actualización de League of Legends…"
            elif status in {408, 429, 500, 502, 503, 504} or status == -1:
                next_request = now + 3
                last_message = "Riot Client está ocupado; volveré a solicitar el inicio de League…"
            else:
                raise LoginFailure(f"Riot rechazó abrir League of Legends (respuesta HTTP {status}).")

        report("launch", last_message)
        time.sleep(1)
    raise LoginFailure("Riot no llegó a abrir League of Legends. Comprueba el estado del cliente o su actualización.")


def _restore_client(service: Path, args: list[str], renderer_path: Path | None,
                    renderer_args: list[str] | None) -> None:
    try:
        if renderer_path and renderer_args:
            _quiet_popen([str(renderer_path), *renderer_args], renderer_path.parent)
        else:
            _quiet_popen([str(service), *args], service.parent)
    except OSError:
        try:
            _quiet_popen([str(service), *args], service.parent)
        except OSError:
            pass


def run_login(client_path: Path, username: str, password: str,
              report: Callable[[str, str], None]) -> None:
    """Use Riot's own login renderer, verify the session and launch League."""
    root = client_path.parent
    report("client", "Comprobando Riot Client…")
    was_running = bool(_client_processes(root))
    service_args = _service_args(root)
    api = _local_api()
    started_headless = False
    if not api or not api.ready():
        report("client", "Iniciando el servicio de Riot Client…")
        try:
            _quiet_popen([str(client_path), "--headless", *service_args], root)
            started_headless = True
        except OSError as exc:
            raise LoginFailure("No se pudo iniciar Riot Client.") from exc
        try:
            api = _wait_api(90, lambda message: report("client", message))
        except LoginFailure:
            _restore_client(client_path, service_args, None, None)
            raise

    current = api.username()
    if current and current.casefold() == username.casefold():
        report("launch", "La cuenta ya está iniciada. Abriendo League of Legends…")
        _launch_and_wait(api, username, report)
        return
    if _league_is_running():
        raise LoginFailure("Cierra League of Legends antes de cambiar a otra cuenta.")
    if current:
        report("signout", "Cerrando la sesión anterior de Riot…")
        if not api.sign_out():
            raise LoginFailure("Riot Client no permitió cerrar la sesión anterior.")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and api.username() is not None:
            time.sleep(0.5)
        if api.username() is not None:
            raise LoginFailure("Riot Client no terminó de cerrar la sesión anterior.")

    renderer = Renderer(Path(__file__).with_name("riot_renderer.js"))
    renderer_path: Path | None = None
    renderer_args: list[str] | None = None
    stopped = started_headless
    launched = False
    try:
        report("credentials", "Preparando el formulario seguro de Riot Client…")
        if was_running or (not started_headless and _client_processes(root)):
            stopped = True
            _stop_client(root)
        if not started_headless:
            report("client", "Iniciando Riot Client en modo de acceso…")
            try:
                _quiet_popen([str(client_path), "--headless", *service_args], root)
            except OSError as exc:
                raise LoginFailure("No se pudo iniciar Riot Client en modo de acceso.") from exc
        api = _wait_api(60, lambda message: report("client", message))
        if api.username():
            raise LoginFailure("Riot Client conservó otra sesión; inténtalo de nuevo.")
        renderer_path, renderer_args = _renderer_args(client_path, api)
        report("credentials", "Cargando el formulario nativo de Riot…")
        renderer.start(renderer_path, renderer_args)
        report("typing", "Introduciendo las credenciales guardadas…")
        values = json.dumps([username, password], ensure_ascii=False)
        filled = renderer.evaluate(f"globalThis.__leagueAccountsLogin.fill(...{values})")
        values = ""
        password = ""
        if filled is not True:
            raise LoginFailure("Riot Client no pudo validar el formulario para esta cuenta.")
        if renderer.evaluate("globalThis.__leagueAccountsLogin.submit()") is not True:
            raise LoginFailure("Riot Client no pudo enviar el formulario de acceso.")

        report("verification", "Esperando la confirmación de Riot…")
        deadline = time.monotonic() + 300
        verification_shown = False
        expected = username.casefold()
        while time.monotonic() < deadline:
            current_api = _local_api()
            if not current_api or current_api.base != api.base:
                raise LoginFailure("La sesión local de Riot cambió durante el acceso.")
            current = current_api.username()
            if current:
                if current.casefold() != expected:
                    raise LoginFailure("Riot inició una sesión distinta de la cuenta seleccionada.")
                report("launch", "Riot confirmó la cuenta. Abriendo League of Legends…")
                _launch_and_wait(current_api, username, report)
                launched = True
                return
            auth_state = renderer.evaluate("globalThis.__leagueAccountsLogin.status()")
            if auth_state in {"rejected", "changed"}:
                raise LoginFailure("Riot rechazó las credenciales. Revísalas en la cuenta guardada.")
            if auth_state == "rate_limited":
                raise LoginFailure("Riot limitó temporalmente los intentos. Espera antes de volver a probar.")
            if auth_state == "captcha_rejected":
                raise LoginFailure("Riot pidió un CAPTCHA. Complétalo en Riot Client y vuelve a iniciar sesión.")
            if auth_state == "verification" and not verification_shown:
                renderer.evaluate("globalThis.__leagueAccountsLogin.showVerification()")
                report("verification", "Riot requiere MFA o CAPTCHA. Complétalo en la ventana de Riot Client.")
                verification_shown = True
            time.sleep(0.3)
        raise LoginFailure("Riot no confirmó el acceso a tiempo. Revisa la verificación en Riot Client.")
    finally:
        renderer.close()
        if stopped and not launched:
            _restore_client(client_path, service_args, renderer_path, renderer_args)


def _league_is_running() -> bool:
    names = {"leagueclient.exe", "leagueclientux.exe", "league of legends.exe"}
    for process in psutil.process_iter(("name",)):
        try:
            if (process.info.get("name") or "").casefold() in names:
                return True
        except psutil.Error:
            continue
    return False
