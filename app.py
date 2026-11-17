from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
import keyring
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import updater

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    ASSET_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).parent
    ASSET_ROOT = ROOT

load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "league_accounts.db")))
RIOT_KEY = os.getenv("RIOT_API_KEY", "").strip()
KEYRING_SERVICE = "RiftVault.LoLAccounts"
_ddragon_version: str | None = None


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            tag_line TEXT NOT NULL,
            puuid TEXT NOT NULL UNIQUE,
            tier TEXT, rank TEXT, league_points INTEGER,
            wins INTEGER, losses INTEGER,
            label TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 0,
            profile_icon_id INTEGER,
            icon_version TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
        for column, sql_type in (("profile_icon_id", "INTEGER"), ("icon_version", "TEXT")):
            if column not in columns:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {column} {sql_type}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    updater.start()
    yield


app = FastAPI(title="Rift Vault", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ASSET_ROOT / "static"), name="static")


@app.get("/api/update/status")
async def update_status():
    return updater.status()


@app.post("/api/update/apply")
async def apply_update():
    try:
        return updater.apply_and_restart()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


class AccountCreate(BaseModel):
    game_name: str = Field(min_length=1, max_length=80)
    tag_line: str = Field(min_length=1, max_length=16)
    riot_username: str = Field(min_length=1, max_length=160)
    riot_password: str = Field(min_length=1, max_length=256)
    label: str = Field(default="", max_length=40)


class AccountUpdate(BaseModel):
    label: str = Field(default="", max_length=40)


async def riot_get(url: str) -> dict | list:
    if not RIOT_KEY:
        raise HTTPException(503, "Configura RIOT_API_KEY en el archivo .env")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(url, headers={"X-Riot-Token": RIOT_KEY})
    except httpx.HTTPError as exc:
        raise HTTPException(502, "No se pudo conectar con Riot Games") from exc
    if response.status_code == 404:
        raise HTTPException(404, "No se encontró ese Riot ID en EUW")
    if response.status_code in (401, 403):
        raise HTTPException(502, "La API key de Riot no es válida o ha caducado")
    if response.status_code == 429:
        raise HTTPException(429, "Límite de peticiones de Riot alcanzado; inténtalo más tarde")
    if response.is_error:
        raise HTTPException(502, f"Riot Games respondió con el error {response.status_code}")
    return response.json()


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
    account = {key: row[key] for key in row.keys() if key != "puuid"}
    account["has_credentials"] = bool(keyring.get_password(KEYRING_SERVICE, str(row["id"])))
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


@app.get("/api/accounts")
async def list_accounts():
    with connect() as db:
        rows = db.execute("SELECT * FROM accounts ORDER BY is_active DESC, game_name COLLATE NOCASE").fetchall()
    return [public(row) for row in rows]


@app.post("/api/accounts", status_code=201)
async def add_account(payload: AccountCreate):
    game_name, tag_line = payload.game_name.strip(), payload.tag_line.strip()
    if not game_name or not tag_line or "#" in game_name:
        raise HTTPException(422, "Escribe el Riot ID como Nombre y Tag por separado")
    encoded_name, encoded_tag = quote(game_name, safe=""), quote(tag_line, safe="")
    account = await riot_get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    )
    puuid = account["puuid"]
    ranked = await riot_get(
        f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{quote(puuid, safe='')}"
    )
    profile_icon_id = None
    try:
        summoner = await riot_get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{quote(puuid, safe='')}"
        )
        profile_icon_id = summoner.get("profileIconId")
    except HTTPException:
        pass
    icon_version = await get_ddragon_version()
    solo = next((entry for entry in ranked if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
    flex = next((entry for entry in ranked if entry.get("queueType") == "RANKED_FLEX_SR"), None)
    selected = solo or flex or {}
    with connect() as db:
        try:
            cursor = db.execute("""INSERT INTO accounts
                (game_name, tag_line, puuid, tier, rank, league_points, wins, losses, label, profile_icon_id, icon_version)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
                account.get("gameName", game_name), account.get("tagLine", tag_line), puuid,
                selected.get("tier", "UNRANKED"), selected.get("rank", ""),
                selected.get("leaguePoints", 0), selected.get("wins", 0), selected.get("losses", 0),
                payload.label.strip(), profile_icon_id, icon_version))
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
        cursor = db.execute("UPDATE accounts SET label=? WHERE id=?", (payload.label.strip(), account_id))
        if not cursor.rowcount:
            raise HTTPException(404, "Cuenta no encontrada")
        return public(db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone())


@app.post("/api/accounts/{account_id}/refresh")
async def refresh_account(account_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Cuenta no encontrada")
    ranked = await riot_get(
        f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{quote(row['puuid'], safe='')}"
    )
    selected = next((entry for entry in ranked if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
    selected = selected or next((entry for entry in ranked if entry.get("queueType") == "RANKED_FLEX_SR"), None) or {}
    with connect() as db:
        db.execute("UPDATE accounts SET tier=?,rank=?,league_points=?,wins=?,losses=? WHERE id=?", (
            selected.get("tier", "UNRANKED"), selected.get("rank", ""), selected.get("leaguePoints", 0),
            selected.get("wins", 0), selected.get("losses", 0), account_id))
        return public(db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone())



@app.post("/api/accounts/{account_id}/activate")
async def activate_account(account_id: int):
    with connect() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise HTTPException(404, "Cuenta no encontrada")
        db.execute("UPDATE accounts SET is_active=0")
        db.execute("UPDATE accounts SET is_active=1 WHERE id=?", (account_id,))
        return public(db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone())


@app.post("/api/accounts/{account_id}/login")
async def login_account(account_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Cuenta no encontrada")
    if not keyring.get_password(KEYRING_SERVICE, str(account_id)):
        raise HTTPException(409, "Esta cuenta no tiene credenciales guardadas")
    client = riot_client_path()
    if client is None:
        raise HTTPException(404, "No se encontró Riot Client. Instálalo en la ruta predeterminada.")
    try:
        subprocess.Popen(
            [str(client), "--launch-product=league_of_legends", "--launch-patchline=live"],
            cwd=str(client.parent),
            close_fds=True,
        )
    except OSError as exc:
        raise HTTPException(500, "No se pudo abrir Riot Client") from exc
    with connect() as db:
        db.execute("UPDATE accounts SET is_active=0")
        db.execute("UPDATE accounts SET is_active=1 WHERE id=?", (account_id,))
    return {"account_id": account_id, "message": "Riot Client está abierto. Completa el inicio de sesión en la ventana del cliente."}
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





