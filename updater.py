from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath

import httpx

OWNER = "Alan-Arriero"
REPO = "LoLAccounts"
CURRENT_VERSION = "0.2.34"
EXECUTABLE_NAME = "Rift Vault.exe"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
_lock = threading.Lock()
_status: dict = {"state": "idle", "progress": 0, "current_version": CURRENT_VERSION, "latest_version": CURRENT_VERSION}
_worker: threading.Thread | None = None


def status() -> dict:
    with _lock:
        return dict(_status)


def _set(**values) -> None:
    with _lock:
        _status.update(values)


def _version(tag: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+(?:\.\d+){1,3})(?:[-+].*)?", tag.strip(), re.I)
    return tuple(int(part) for part in match.group(1).split(".")) if match else (0,)


def _safe_extract(archive: Path, destination: Path) -> Path:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            name = item.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or any(part in ("..", "") for part in path.parts):
                raise ValueError("El paquete de actualización contiene una ruta no válida.")
            target = (root / Path(*path.parts)).resolve()
            if not target.is_relative_to(root):
                raise ValueError("El paquete intenta salir de su carpeta.")
            bundle.extract(item, root)
    candidates = [p.parent for p in root.rglob(EXECUTABLE_NAME)]
    if not candidates:
        raise ValueError(f"La release descargada no contiene {EXECUTABLE_NAME}.")
    payload = candidates[0]
    if not (payload / "_internal").is_dir() or not (payload / "_internal" / "static").is_dir():
        raise ValueError("La release descargada está incompleta.")
    return payload


def _check_and_download() -> None:
    if not getattr(sys, "frozen", False):
        _set(state="current")
        return
    _set(state="checking", progress=0)
    try:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        with httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=True, headers=headers) as client:
            response = client.get(API)
            response.raise_for_status()
            release = response.json()
            tag = str(release.get("tag_name", ""))
            if _version(tag) <= _version(CURRENT_VERSION):
                _set(state="current", latest_version=tag or CURRENT_VERSION)
                return
            asset = next((item for item in release.get("assets", []) if item.get("name") == "LoLAccounts-windows-x64.zip"), None)
            if not asset:
                _set(state="error", error="La release no contiene el instalador de Windows.")
                return
            _set(state="downloading", progress=0, latest_version=tag)
            staging = ROOT / ".update-staging"
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True, exist_ok=True)
            archive = staging / "release.zip"
            total = int(asset.get("size") or 0)
            downloaded = 0
            with client.stream("GET", asset["browser_download_url"]) as stream:
                stream.raise_for_status()
                total = int(stream.headers.get("content-length") or total)
                with archive.open("wb") as output:
                    for chunk in stream.iter_bytes(16 * 1024):
                        if chunk:
                            output.write(chunk)
                            downloaded += len(chunk)
                            # Keep the true byte-based progress, including fractions, for smooth UI updates.
                            _set(progress=min(99.9, downloaded * 100 / total) if total else 0)
            payload = _safe_extract(archive, staging / "payload")
            archive.unlink(missing_ok=True)
            _set(state="ready", progress=100, latest_version=tag, payload=str(payload))
    except Exception as exc:
        _set(state="error", error=f"No se pudo descargar la actualización: {exc}")


def _update_worker() -> None:
    _check_and_download()


def start() -> None:
    global _worker
    if not getattr(sys, "frozen", False):
        _set(state="current")
        return
    if _worker is not None:
        return
    _worker = threading.Thread(target=_update_worker, name="release-updater", daemon=True)
    _worker.start()


def apply_and_restart() -> dict:
    info = status()
    if info["state"] != "ready":
        raise RuntimeError("La actualización todavía no está preparada.")
    payload = Path(info["payload"]).resolve()
    root = ROOT.resolve()
    if not payload.is_relative_to(root) or not (payload / EXECUTABLE_NAME).is_file():
        raise RuntimeError("La carpeta de actualización no es válida.")
    if not getattr(sys, "frozen", False):
        raise RuntimeError("El actualizador solo está disponible en la aplicación instalada.")
    script = Path(tempfile.gettempdir()) / f"lolaccounts-update-{os.getpid()}.ps1"
    ps = r"""
$ErrorActionPreference = 'Stop'
$pidToWait = __PID__
$root = '__ROOT__'
$payload = '__PAYLOAD__'
$exe = Join-Path $root '__APP_EXE__'
$legacyExe = Join-Path $root 'LoLAccounts.exe'
$stage = Join-Path $root '.update-staging'
while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 400 }
$preserve = @()
foreach ($name in @('.env', 'league_accounts.db')) {
  $src = Join-Path $root $name
  if (Test-Path -LiteralPath $src) {
    $dst = Join-Path $stage ('preserve-' + $name)
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $preserve += @{ Name = $name; Path = $dst }
  }
}
Copy-Item -Path (Join-Path $payload '*') -Destination $root -Recurse -Force
foreach ($item in $preserve) { Copy-Item -LiteralPath $item.Path -Destination (Join-Path $root $item.Name) -Force }
if (Test-Path -LiteralPath $legacyExe) { Remove-Item -LiteralPath $legacyExe -Force }
Remove-Item -LiteralPath $stage -Recurse -Force
Start-Process -FilePath $exe -WorkingDirectory $root
Remove-Item -LiteralPath $PSCommandPath -Force
"""
    ps = (ps.replace("__PID__", str(os.getpid()))
          .replace("__ROOT__", str(root).replace("'", "''"))
          .replace("__PAYLOAD__", str(payload).replace("'", "''"))
          .replace("__APP_EXE__", EXECUTABLE_NAME.replace("'", "''")))
    script.write_text(ps, encoding="utf-8")
    subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    threading.Thread(target=lambda: (time.sleep(1.0), os._exit(0)), daemon=True).start()
    _set(state="applying")
    return {"status": "restarting", "version": info["latest_version"]}
