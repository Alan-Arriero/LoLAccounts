from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi import HTTPException

import app
import updater


@contextmanager
def closing_connection(path: Path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class AccountRegressionTests(unittest.IsolatedAsyncioTestCase):
    def test_hourly_refresh_deadline_uses_spain_clock(self) -> None:
        spain = ZoneInfo("Europe/Madrid")
        for month in (1, 8):
            now = datetime(2026, month, 18, 12, 17, tzinfo=spain)
            deadline = app._next_rank_refresh_deadline(now.timestamp())
            next_refresh = datetime.fromtimestamp(deadline, spain)

            self.assertEqual(
                (next_refresh.year, next_refresh.month, next_refresh.day, next_refresh.hour,
                 next_refresh.minute, next_refresh.second),
                (2026, month, 18, 13, 0, 0),
            )

    async def test_logo_endpoint_serves_the_root_logo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            logo = Path(temporary) / "image.png"
            logo.write_bytes(b"logo")
            with patch.object(app, "ASSET_ROOT", Path(temporary)):
                response = await app.application_logo()

            self.assertEqual(Path(response.path), logo)
            self.assertEqual(response.media_type, "image/png")

    async def test_adds_a_second_account_without_an_euw_rank_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "accounts.db"

            async def riot_get(url: str, **kwargs):
                if "accounts/by-riot-id" in url:
                    if "/Two/" in url:
                        return {"puuid": "second-puuid", "gameName": "Two", "tagLine": "EUW"}
                    return {"puuid": "first-puuid", "gameName": "One", "tagLine": "EUW"}
                if "/league/v4/" in url:
                    if "second-puuid" in url:
                        raise HTTPException(404, "No EUW league entry")
                    return [{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "II"}]
                if "/summoner/v4/" in url:
                    if "second-puuid" in url:
                        raise HTTPException(404, "No EUW summoner")
                    return {"profileIconId": 123, "summonerLevel": 520}
                raise AssertionError(f"Unexpected Riot API URL: {url}")

            with (
                patch.object(app, "DB_PATH", database),
                patch.object(app, "connect", side_effect=lambda: closing_connection(database)),
                patch.object(app, "riot_get", side_effect=riot_get),
                patch.object(app, "get_ddragon_version", new=AsyncMock(return_value="16.1.1")),
                patch.object(app.keyring, "set_password"),
                patch.object(app.keyring, "get_password", return_value="{}"),
            ):
                app.init_db()
                first = await app.add_account(app.AccountCreate(
                    game_name="One", tag_line="EUW", riot_username="one",
                    riot_password="secret",
                ))
                second = await app.add_account(app.AccountCreate(
                    game_name="Two", tag_line="EUW", riot_username="two",
                    riot_password="secret",
                ))
                accounts = await app.list_accounts()

            self.assertEqual(first["summoner_level"], 520)
            self.assertEqual(first["profile_icon_id"], 123)
            self.assertEqual(second["tier"], "UNRANKED")
            self.assertIsNone(second["summoner_level"])
            self.assertEqual(len(accounts), 2)

    def test_existing_database_migrates_summoner_level_column(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "accounts.db"
            db = sqlite3.connect(database)
            try:
                db.execute("""CREATE TABLE accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_name TEXT NOT NULL, tag_line TEXT NOT NULL, puuid TEXT NOT NULL UNIQUE,
                    tier TEXT, rank TEXT, league_points INTEGER, wins INTEGER, losses INTEGER,
                    label TEXT NOT NULL DEFAULT '', is_active INTEGER NOT NULL DEFAULT 0,
                    profile_icon_id INTEGER, icon_version TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )""")
                db.execute("INSERT INTO accounts(game_name, tag_line, puuid) VALUES('One', 'EUW', 'p1')")
                db.commit()
            finally:
                db.close()

            with patch.object(app, "DB_PATH", database):
                with patch.object(app, "connect", side_effect=lambda: closing_connection(database)):
                    app.init_db()
                    with app.connect() as db:
                        columns = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
                        account = db.execute("SELECT game_name, summoner_level FROM accounts").fetchone()

            self.assertIn("summoner_level", columns)
            self.assertEqual(account["game_name"], "One")
            self.assertIsNone(account["summoner_level"])


class UpdaterRegressionTests(unittest.TestCase):
    def test_update_worker_rechecks_after_current_until_update_is_ready(self) -> None:
        checked_states = iter(("current", "ready"))

        def check_for_updates():
            updater._set(state=next(checked_states))

        with (
            patch.object(updater, "_check_and_download", side_effect=check_for_updates) as check,
            patch.object(updater.time, "sleep") as sleep,
        ):
            updater._update_worker()

        self.assertEqual(check.call_count, 2)
        sleep.assert_called_once_with(updater.UPDATE_CHECK_INTERVAL_SECONDS)

    def test_downloads_latest_release_after_skipping_intermediate_versions(self) -> None:
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w") as archive:
            archive.writestr("Rift Vault/Rift Vault.exe", b"exe")
            archive.writestr("Rift Vault/_internal/static/index.html", b"app")
        archive_bytes = archive_buffer.getvalue()
        requested_urls: list[str] = []

        class Response:
            def __init__(self, value):
                self.value = value

            def raise_for_status(self):
                return None

            def json(self):
                return self.value

        class Stream:
            headers = {"content-length": str(len(archive_bytes))}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def raise_for_status(self):
                return None

            def iter_bytes(self, _chunk_size):
                yield archive_bytes

        class Client:
            def __init__(self, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def get(self, url):
                requested_urls.append(url)
                return Response({
                    "tag_name": "v0.2.28",
                    "assets": [{
                        "name": "LoLAccounts-windows-x64.zip",
                        "size": len(archive_bytes),
                        "browser_download_url": "https://example.test/latest.zip",
                    }],
                })

            def stream(self, _method, url):
                requested_urls.append(url)
                return Stream()

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(updater, "ROOT", Path(temporary)),
                patch.object(updater, "httpx") as httpx_mock,
                patch.object(updater.sys, "frozen", True, create=True),
            ):
                httpx_mock.Client = Client
                updater._set(
                    state="idle", progress=0, latest_version=updater.CURRENT_VERSION,
                    error=None, payload=None,
                )
                updater._check_and_download()
                result = updater.status()

        self.assertEqual(requested_urls[0], updater.API)
        self.assertEqual(requested_urls[1], "https://example.test/latest.zip")
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["latest_version"], "v0.2.28")
        self.assertEqual(Path(result["payload"]).name, "Rift Vault")


if __name__ == "__main__":
    unittest.main()
