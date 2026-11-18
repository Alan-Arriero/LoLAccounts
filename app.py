from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
import subprocess
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
import keyring
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
import updater
import riot_login

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    ASSET_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).parent
    ASSET_ROOT = ROOT

load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "league_accounts.db")))
KEYRING_SERVICE = "RiftVault.LoLAccounts"
_ddragon_version: str | None = None
_login_status_lock = threading.Lock()
_login_statuses: dict[int, dict[str, str]] = {}
_spain_timezone = ZoneInfo("Europe/Madrid")


def _next_rank_refresh_deadline(now: float | None = None) -> float:
    current = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return next_hour.astimezone(_spain_timezone).timestamp()


_rank_refresh_lock = threading.Lock()
_rank_refresh_stop = threading.Event()
_rank_refresh_thread: threading.Thread | None = None
_rank_refresh_deadline = _next_rank_refresh_deadline()
_rank_refreshing = False
_rank_refresh_last_run: float | None = None


def load_riot_api_key() -> str:
    configured = os.getenv("RIOT_API_KEY", "").strip()
    if configured:
        return configured
    try:
        return (keyring.get_password(KEYRING_SERVICE, "riot_api_key") or "").strip()
    except Exception:
        return ""


RIOT_KEY = load_riot_api_key()


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            tag_line TEXT NOT NULL,
            puuid TEXT UNIQUE,
            tier TEXT, rank TEXT, league_points INTEGER,
            wins INTEGER, losses INTEGER,
            label TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 0,
            profile_icon_id INTEGER,
            summoner_level INTEGER,
            icon_version TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
        for column, sql_type in (("profile_icon_id", "INTEGER"), ("summoner_level", "INTEGER"),
                                 ("icon_version", "TEXT")):
            if column not in columns:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {column} {sql_type}")
        puuid_column = next(row for row in db.execute("PRAGMA table_info(accounts)") if row["name"] == "puuid")
        if puuid_column["notnull"]:
            db.execute("ALTER TABLE accounts RENAME TO accounts_legacy")
            db.execute("""CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL,
                tag_line TEXT NOT NULL,
                puuid TEXT UNIQUE,
                tier TEXT, rank TEXT, league_points INTEGER,
                wins INTEGER, losses INTEGER,
                label TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 0,
                profile_icon_id INTEGER,
                summoner_level INTEGER,
                icon_version TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("""INSERT INTO accounts
                (id, game_name, tag_line, puuid, tier, rank, league_points, wins, losses,
                 label, is_active, profile_icon_id, summoner_level, icon_version, created_at)
                SELECT id, game_name, tag_line, puuid, tier, rank, league_points, wins, losses,
                       label, is_active, profile_icon_id, summoner_level, icon_version, created_at
                FROM accounts_legacy""")
            db.execute("DROP TABLE accounts_legacy")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    updater.start()
    _start_rank_refresh_worker()
    yield
    _rank_refresh_stop.set()


app = FastAPI(title="Rift Vault", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ASSET_ROOT / "static"), name="static")


def _setting(key: str, default: str = "false") -> str:
    with connect() as db:
        row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return str(row["value"]) if row else default


def _preferences() -> dict[str, bool | str]:
    return {
        "close_after_login": _setting("close_after_login") == "true",
        "launch_on_windows": _setting("launch_on_windows") == "true",
        "language": _setting("language", "es"),
    }


def _set_windows_autostart(enabled: bool) -> None:
    if os.name != "nt":
        raise HTTPException(501, "El inicio automático con Windows solo está disponible en Windows")
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "RiftVault"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            command = [str(Path(sys.executable).resolve())]
            if not getattr(sys, "frozen", False):
                command.append(str(Path(__file__).with_name("main.py").resolve()))
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass


class AppSettings(BaseModel):
    close_after_login: bool
    launch_on_windows: bool
    language: Literal["es", "en"] = "es"


@app.get("/api/settings")
async def get_settings():
    return _preferences()


@app.put("/api/settings")
async def put_settings(payload: AppSettings):
    current = _preferences()
    if payload.launch_on_windows != current["launch_on_windows"]:
        _set_windows_autostart(payload.launch_on_windows)
    with connect() as db:
        db.executemany(
            "INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (("close_after_login", str(payload.close_after_login).lower()),
             ("launch_on_windows", str(payload.launch_on_windows).lower()),
             ("language", payload.language)),
        )
    return _preferences()


@app.get("/api/refresh/status")
async def refresh_status():
    with _rank_refresh_lock:
        return {
            "refreshing": _rank_refreshing,
            "next_refresh_seconds": 0 if _rank_refreshing else max(0, int(_rank_refresh_deadline - time.time())),
            "last_refresh": _rank_refresh_last_run,
        }


async def _refresh_rank(account_id: int, puuid: str) -> None:
    ranked = await riot_get(
        f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{quote(puuid, safe='')}"
    )
    selected = next((entry for entry in ranked if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
    selected = selected or next((entry for entry in ranked if entry.get("queueType") == "RANKED_FLEX_SR"), None) or {}
    with connect() as db:
        db.execute("UPDATE accounts SET tier=?,rank=?,league_points=?,wins=?,losses=? WHERE id=?", (
            selected.get("tier", "UNRANKED"), selected.get("rank", ""), selected.get("leaguePoints", 0),
            selected.get("wins", 0), selected.get("losses", 0), account_id))


async def _refresh_all_linked_accounts() -> None:
    with connect() as db:
        rows = db.execute("SELECT id,puuid FROM accounts WHERE puuid IS NOT NULL AND puuid!=''").fetchall()
    for row in rows:
        try:
            await _refresh_rank(int(row["id"]), str(row["puuid"]))
        except HTTPException:
            continue


def _rank_refresh_worker() -> None:
    global _rank_refresh_deadline, _rank_refreshing, _rank_refresh_last_run
    while not _rank_refresh_stop.is_set():
        remaining = max(0, _rank_refresh_deadline - time.time())
        if _rank_refresh_stop.wait(remaining):
            return
        with _rank_refresh_lock:
            if time.time() < _rank_refresh_deadline:
                continue
            _rank_refreshing = True
        try:
            asyncio.run(_refresh_all_linked_accounts())
        except Exception:
            pass
        finally:
            with _rank_refresh_lock:
                _rank_refreshing = False
                _rank_refresh_last_run = time.time()
                _rank_refresh_deadline = _next_rank_refresh_deadline()


def _start_rank_refresh_worker() -> None:
    global _rank_refresh_deadline, _rank_refresh_thread
    if _rank_refresh_thread and _rank_refresh_thread.is_alive():
        return
    _rank_refresh_stop.clear()
    with _rank_refresh_lock:
        _rank_refresh_deadline = _next_rank_refresh_deadline()
    _rank_refresh_thread = threading.Thread(
        target=_rank_refresh_worker, name="hourly-rank-refresh", daemon=True
    )
    _rank_refresh_thread.start()


@app.get("/api/update/status")
async def update_status():
    return updater.status()


@app.post("/api/update/apply")
async def apply_update():
    try:
        return updater.apply_and_restart()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/app/close")
async def request_app_close():
    close_event = getattr(app.state, "close_event", None)
    if close_event is None:
        raise HTTPException(503, "La ventana de escritorio no está conectada")
    close_event.set()
    return {"status": "closing"}


class AccountCreate(BaseModel):
    game_name: str | None = Field(default=None, max_length=80)
    tag_line: str | None = Field(default=None, max_length=16)
    riot_username: str = Field(min_length=1, max_length=160)
    riot_password: str = Field(min_length=1, max_length=256)
    label: str = Field(default="", max_length=40)


class AccountUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=40)
    game_name: str | None = Field(default=None, max_length=80)
    tag_line: str | None = Field(default=None, max_length=16)


async def riot_get(url: str, *, not_found_detail: str = "No se encontró el recurso solicitado en Riot Games") -> dict | list:
    if not RIOT_KEY:
        raise HTTPException(503, "Configura RIOT_API_KEY en el archivo .env")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(url, headers={"X-Riot-Token": RIOT_KEY})
    except httpx.HTTPError as exc:
        raise HTTPException(502, "No se pudo conectar con Riot Games") from exc
    if response.status_code == 404:
        raise HTTPException(404, not_found_detail)
    if response.status_code in (401, 403):
        raise HTTPException(502, "La API key de Riot no es válida o ha caducado")
    if response.status_code == 429:
        raise HTTPException(429, "Límite de peticiones de Riot alcanzado; inténtalo más tarde")
    if response.is_error:
        raise HTTPException(502, f"Riot Games respondió con el error {response.status_code}")
    return response.json()


async def riot_get_or_default(url: str, default: dict | list) -> dict | list:
    try:
        return await riot_get(url)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return default


async def get_ddragon_version() -> str:
    global _ddragon_version
    if _ddragon_version:
        return _ddragon_version
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            response = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
            response.raise_for_status()
            _ddragon_version = response.json()[0]
    except (httpx.HTTPError, IndexError, ValueError):
        _ddragon_version = "16.1.1"
    return _ddragon_version


def public(row: sqlite3.Row) -> dict:
    account = {key: row[key] for key in row.keys() if key not in {"puuid", "is_active"}}
    account["has_credentials"] = bool(keyring.get_password(KEYRING_SERVICE, str(row["id"])))
    account["has_riot_id"] = bool(row["puuid"] and row["game_name"] and row["tag_line"])
    return account


def riot_client_path() -> Path | None:
    candidates: list[Path] = []
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.getenv(variable)
        if base:
            candidates.append(Path(base) / "Riot Games" / "Riot Client" / "RiotClientServices.exe")
    candidates.extend((
        Path("C:/Riot Games/Riot Client/RiotClientServices.exe"),
        Path("D:/Riot Games/Riot Client/RiotClientServices.exe"),
    ))
    for path in candidates:
        if path.is_file():
            return path
    return None



@app.get("/")
async def index():
    return FileResponse(ASSET_ROOT / "static" / "index.html")


@app.get("/image.png")
async def application_logo():
    return FileResponse(ASSET_ROOT / "image.png", media_type="image/png")


@app.get("/api/accounts")
async def list_accounts():
    with connect() as db:
        rows = db.execute("SELECT * FROM accounts ORDER BY created_at DESC, id DESC").fetchall()
    return [public(row) for row in rows]


@app.post("/api/accounts", status_code=201)
async def add_account(payload: AccountCreate):
    game_name = (payload.game_name or "").strip()
    tag_line = (payload.tag_line or "").strip()
    if bool(game_name) != bool(tag_line) or "#" in game_name:
        raise HTTPException(422, "Completa ambos campos del Riot ID o deja ambos vacíos")
    account: dict = {}
    puuid = None
    ranked: list = []
    profile_icon_id = None
    summoner_level = None
    icon_version = None
    selected: dict = {}
    display_name = "Cuenta sin Riot ID"
    if game_name and tag_line:
        encoded_name, encoded_tag = quote(game_name, safe=""), quote(tag_line, safe="")
        account = await riot_get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}",
            not_found_detail="No se encontró ese Riot ID en las cuentas regionales de Riot",
        )
        puuid = account["puuid"]
        ranked_data = await riot_get_or_default(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{quote(puuid, safe='')}",
            [],
        )
        ranked = ranked_data if isinstance(ranked_data, list) else []
        summoner_data = await riot_get_or_default(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{quote(puuid, safe='')}",
            {},
        )
        summoner = summoner_data if isinstance(summoner_data, dict) else {}
        profile_icon_id = summoner.get("profileIconId")
        level = summoner.get("summonerLevel")
        summoner_level = level if isinstance(level, int) and not isinstance(level, bool) else None
        icon_version = await get_ddragon_version()
        display_name = account.get("gameName", game_name)
        tag_line = account.get("tagLine", tag_line)
        solo = next((entry for entry in ranked if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
        flex = next((entry for entry in ranked if entry.get("queueType") == "RANKED_FLEX_SR"), None)
        selected = solo or flex or {}
    with connect() as db:
        try:
            cursor = db.execute("""INSERT INTO accounts
                (game_name, tag_line, puuid, tier, rank, league_points, wins, losses, label,
                 profile_icon_id, summoner_level, icon_version)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
                display_name, tag_line, puuid,
                selected.get("tier", "UNRANKED"), selected.get("rank", ""),
                selected.get("leaguePoints", 0), selected.get("wins", 0), selected.get("losses", 0),
                payload.label.strip(), profile_icon_id, summoner_level, icon_version))
            account_id = cursor.lastrowid
            row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "Esta cuenta ya está en tu colección") from exc
    secret = json.dumps(
        {"username": payload.riot_username.strip(), "password": payload.riot_password},
        ensure_ascii=False,
    )
    try:
        keyring.set_password(KEYRING_SERVICE, str(account_id), secret)
    except Exception as exc:
        with connect() as db:
            db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        raise HTTPException(500, "Windows no pudo guardar la contraseña en su almacén seguro") from exc
    return public(row)


@app.patch("/api/accounts/{account_id}")
async def update_account(account_id: int, payload: AccountUpdate):
    with connect() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise HTTPException(404, "Cuenta no encontrada")
    if payload.game_name is not None or payload.tag_line is not None:
        game_name = (payload.game_name or "").strip()
        tag_line = (payload.tag_line or "").strip()
        if not game_name or not tag_line or "#" in game_name:
            raise HTTPException(422, "Completa el Riot ID y el tag por separado")
        account = await riot_get(
            "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
            f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}",
            not_found_detail="No se encontró ese Riot ID en las cuentas regionales de Riot",
        )
        puuid = account["puuid"]
        ranked_data = await riot_get_or_default(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{quote(puuid, safe='')}",
            [],
        )
        ranked = ranked_data if isinstance(ranked_data, list) else []
        summoner_data = await riot_get_or_default(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{quote(puuid, safe='')}",
            {},
        )
        summoner = summoner_data if isinstance(summoner_data, dict) else {}
        profile_icon_id = summoner.get("profileIconId")
        level = summoner.get("summonerLevel")
        summoner_level = level if isinstance(level, int) and not isinstance(level, bool) else None
        icon_version = await get_ddragon_version()
        selected = next((entry for entry in ranked if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
        selected = selected or next((entry for entry in ranked if entry.get("queueType") == "RANKED_FLEX_SR"), None) or {}
        with connect() as db:
            try:
                db.execute("""UPDATE accounts SET game_name=?, tag_line=?, puuid=?, tier=?, rank=?,
                    league_points=?, wins=?, losses=?, profile_icon_id=?, summoner_level=?, icon_version=?,
                    label=COALESCE(?, label) WHERE id=?""", (
                    account.get("gameName", game_name), account.get("tagLine", tag_line), puuid,
                    selected.get("tier", "UNRANKED"), selected.get("rank", ""),
                    selected.get("leaguePoints", 0), selected.get("wins", 0), selected.get("losses", 0),
                    profile_icon_id, summoner_level, icon_version,
                    payload.label.strip() if payload.label is not None else None, account_id))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, "Esta cuenta de Riot ya está en tu colección") from exc
            row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Cuenta no encontrada")
            return public(row)
    with connect() as db:
        if payload.label is not None:
            cursor = db.execute("UPDATE accounts SET label=? WHERE id=?", (payload.label.strip(), account_id))
            if not cursor.rowcount:
                raise HTTPException(404, "Cuenta no encontrada")
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Cuenta no encontrada")
        return public(row)


@app.post("/api/accounts/{account_id}/refresh")
async def refresh_account(account_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Cuenta no encontrada")
    if not row["puuid"]:
        raise HTTPException(409, "Añade el Riot ID y tag antes de actualizar el rango")
    await _refresh_rank(account_id, str(row["puuid"]))
    with connect() as db:
        return public(db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone())



@app.post("/api/accounts/{account_id}/login")
async def login_account(account_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Cuenta no encontrada")
    stored = keyring.get_password(KEYRING_SERVICE, str(account_id))
    if not stored:
        raise HTTPException(409, "Esta cuenta no tiene credenciales guardadas")
    try:
        credentials = json.loads(stored)
        username = str(credentials["username"]).strip()
        password = str(credentials["password"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(500, "No se pudieron leer las credenciales guardadas de esta cuenta") from exc
    if not username or not password:
        raise HTTPException(409, "La cuenta no tiene usuario y contraseña guardados")
    with _login_status_lock:
        if any(item["state"] in {"starting", "running", "verification"} for item in _login_statuses.values()):
            raise HTTPException(409, "Ya hay otro inicio de sesión en curso")
        _login_statuses[account_id] = {
            "state": "starting", "step": "client", "message": "Preparando Riot Client…", "progress": None
        }

    def worker() -> None:
        last_step = "client"

        def report(step: str, message: str, progress: float | None = None) -> None:
            nonlocal last_step
            last_step = step
            with _login_status_lock:
                _login_statuses[account_id] = {
                    "state": "verification" if step == "verification" else "running",
                    "step": step,
                    "message": message,
                    "progress": progress,
                }
        try:
            client = riot_client_path()
            if client is None:
                raise riot_login.LoginFailure("No se encontró Riot Client en una ruta de instalación conocida.")
            riot_login.run_login(client, username, password, report)
            report("success", "League of Legends se está abriendo con la cuenta seleccionada.")
            with _login_status_lock:
                _login_statuses[account_id]["state"] = "success"
        except Exception as exc:
            with _login_status_lock:
                _login_statuses[account_id] = {
                    "state": "error", "step": last_step, "message": str(exc), "progress": None
                }

    threading.Thread(target=worker, name=f"riot-login-{account_id}", daemon=True).start()
    return {"account_id": account_id, "status": "started"}


@app.get("/api/accounts/{account_id}/login-status")
async def account_login_status(account_id: int):
    with _login_status_lock:
        return dict(_login_statuses.get(
            account_id, {"state": "idle", "step": "", "message": "", "progress": None}
        ))
@app.delete("/api/accounts/{account_id}", status_code=204)
async def delete_account(account_id: int):
    with connect() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise HTTPException(404, "Cuenta no encontrada")
        db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    try:
        keyring.delete_password(KEYRING_SERVICE, str(account_id))
    except keyring.errors.PasswordDeleteError:
        pass





