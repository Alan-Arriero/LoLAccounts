from __future__ import annotations

import socket
import threading
import time

import uvicorn
import webview

from app import ROOT, app

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def run_server() -> None:
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
    uvicorn.Server(config).run()


def wait_for_server(timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.25):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError("No se pudo iniciar el servidor local de Rift Vault.")


if __name__ == "__main__":
    threading.Thread(target=run_server, name="rift-vault-server", daemon=True).start()
    wait_for_server()
    webview.create_window(
        "Rift Vault | League Accounts",
        URL,
        width=1440,
        height=920,
        min_size=(1024, 680),
        background_color="#080b15",
    )
    webview.start(gui="edgechromium", debug=False, storage_path=str(ROOT / ".webview-data"))
