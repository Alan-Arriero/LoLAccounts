from __future__ import annotations

import socket
import sys
import threading
import time

import uvicorn
from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from app import ASSET_ROOT, app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_server(port: int) -> None:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    uvicorn.Server(config).run()


def wait_for_server(port: int, timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError("No se pudo iniciar el servidor local de Rift Vault.")


if __name__ == "__main__":
    from PySide6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    application = QApplication(sys.argv)
    icon_path = ASSET_ROOT / "assets" / "yuumi.png"
    application.setWindowIcon(QIcon(str(icon_path)))
    port = free_port()
    threading.Thread(target=run_server, args=(port,), name="rift-vault-server", daemon=True).start()
    wait_for_server(port)
    window = QMainWindow()
    window.setWindowTitle("Rift Vault | League Accounts")
    window.setWindowIcon(QIcon(str(icon_path)))
    window.resize(1440, 920)
    window.setMinimumSize(1024, 680)
    view = QWebEngineView(window)
    window.setCentralWidget(view)
    view.load(QUrl(f"http://127.0.0.1:{port}"))
    window.show()
    sys.exit(application.exec())
