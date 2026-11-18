from __future__ import annotations

import socket
import logging
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import uvicorn
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from app import ASSET_ROOT, app


def server_log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "RiftVault"
    base.mkdir(parents=True, exist_ok=True)
    return base / "startup.log"


def run_server(sock: socket.socket, result: dict, ready: threading.Event) -> None:
    log_handler = logging.FileHandler(server_log_path(), mode="a", encoding="utf-8")
    logger = logging.getLogger("uvicorn.error")
    logger.handlers.clear()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    try:
        config = uvicorn.Config(app, log_config=None, log_level="info", access_log=False, lifespan="on")
        server = uvicorn.Server(config)
        result["server"] = server
        server.run(sockets=[sock])
        if not server.started and "error" not in result:
            result["error"] = "Uvicorn terminó antes de iniciar el servidor."
    except BaseException:
        result["error"] = traceback.format_exc()
        try:
            sock.close()
        except OSError:
            pass
    finally:
        logger.removeHandler(log_handler)
        log_handler.close()
        ready.set()


def wait_for_server(sock: socket.socket, result: dict, ready: threading.Event, timeout: float = 30) -> int:
    port = sock.getsockname()[1]
    deadline = time.monotonic() + timeout
    server = None
    while time.monotonic() < deadline:
        server = result.get("server")
        if server and server.started:
            server_log_path().write_text(
                f"Rift Vault server started on http://127.0.0.1:{port}\n",
                encoding="utf-8",
            )
            return port
        if ready.is_set():
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                pass
        except OSError:
            pass
        time.sleep(0.1)
    log_file = server_log_path()
    logged = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
    detail = result.get("error") or logged or "El servidor no completó el inicio dentro del tiempo esperado."
    raise RuntimeError(f"No se pudo iniciar el servidor local de Rift Vault.\n\n{detail}")


if __name__ == "__main__":
    from PySide6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    application = QApplication(sys.argv)
    icon_path = ASSET_ROOT / "image.png"
    application.setWindowIcon(QIcon(str(icon_path)))
    close_event = threading.Event()
    app.state.close_event = close_event
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))
    server_log_path().write_text("", encoding="utf-8")
    result: dict = {}
    server_ready = threading.Event()
    threading.Thread(
        target=run_server,
        args=(server_socket, result, server_ready),
        name="rift-vault-server",
        daemon=True,
    ).start()
    try:
        port = wait_for_server(server_socket, result, server_ready)
    except RuntimeError as exc:
        detail = f"{exc}\n\nRegistro: {server_log_path()}"
        server_log_path().write_text(detail, encoding="utf-8")
        QMessageBox.critical(None, "No se pudo iniciar Rift Vault", detail)
        raise
    window = QMainWindow()
    window.setWindowTitle("Rift Vault | League Accounts")
    window.setWindowIcon(QIcon(str(icon_path)))
    window.resize(1440, 920)
    window.setMinimumSize(760, 560)
    view = QWebEngineView(window)
    window.setCentralWidget(view)
    view.load(QUrl(f"http://127.0.0.1:{port}"))
    window.show()
    close_timer = QTimer(window)

    def close_on_login() -> None:
        if close_event.is_set():
            close_timer.stop()
            QTimer.singleShot(500, window.close)

    close_timer.timeout.connect(close_on_login)
    close_timer.start(100)
    sys.exit(application.exec())
