from __future__ import annotations

import json
from pathlib import Path

import httpx

from easy_language_learning_tool.persistence.database import (
    database_connection,
    initialize_database,
)
from easy_language_learning_tool.sync.client import CloudSession, SupabaseSyncClient
from easy_language_learning_tool.sync.service import DesktopSyncService


def test_sign_in_normalizes_supabase_session() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/token"
        assert request.url.params["grant_type"] == "password"
        return httpx.Response(
            200,
            json={
                "access_token": "access",
                "refresh_token": "refresh",
                "user": {"id": "user-id"},
            },
        )

    client = SupabaseSyncClient(
        "https://project.supabase.co",
        "publishable",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.sign_in("user@example.com", "password") == CloudSession(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
    )


def test_refresh_session_normalizes_supabase_session() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["grant_type"] == "refresh_token"
        assert json.loads(request.content) == {"refresh_token": "refresh-old"}
        return httpx.Response(
            200,
            json={
                "access_token": "access-new",
                "refresh_token": "refresh-new",
                "user": {"id": "user-id"},
            },
        )

    client = SupabaseSyncClient(
        "https://project.supabase.co",
        "publishable",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.refresh_session("refresh-old") == CloudSession(
        access_token="access-new",
        refresh_token="refresh-new",
        user_id="user-id",
    )


def test_desktop_service_queues_and_uploads_complete_deck(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    initialize_database(database)
    with database_connection(database) as connection:
        cursor = connection.execute(
            """
            INSERT INTO flashcard_sources(
                file_checksum, source_path, display_name, row_count
            ) VALUES ('checksum', '/deck.xlsx', 'German A1', 1)
            """
        )
        source_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO flashcard_rows(
                source_id, rank, foreign_word, word_translation,
                foreign_sentence, sentence_translation
            ) VALUES (?, 1, 'lernen', 'to learn',
                      'Ich lerne jeden Tag.', 'I learn every day.')
            """,
            (source_id,),
        )

    uploaded: list[tuple[str, list[dict[str, object]]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert isinstance(payload, list)
        uploaded.append((request.url.path, payload))
        return httpx.Response(201)

    client = SupabaseSyncClient(
        "https://project.supabase.co",
        "publishable",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    service = DesktopSyncService(database, client)
    deck_id = service.queue_source(
        source_id,
        source_language="German",
        translation_language="US English",
        cefr_level="A1",
    )

    assert service.flush(
        CloudSession(access_token="access", refresh_token="refresh", user_id="user-id")
    ) == (1, 0)
    assert [path for path, _ in uploaded] == ["/rest/v1/decks", "/rest/v1/cards"]
    assert uploaded[0][1][0]["id"] == str(deck_id)
    assert uploaded[1][1][0]["foreign_word"] == "lernen"
    assert service.outbox.pending() == []


def test_failed_upload_remains_in_outbox(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    initialize_database(database)
    with database_connection(database) as connection:
        cursor = connection.execute(
            """
            INSERT INTO flashcard_sources(
                file_checksum, source_path, display_name, row_count
            ) VALUES ('checksum', '/deck.xlsx', 'German A1', 1)
            """
        )
        source_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO flashcard_rows(
                source_id, rank, foreign_word, word_translation,
                foreign_sentence, sentence_translation
            ) VALUES (?, 1, 'lernen', 'to learn',
                      'Ich lerne.', 'I learn.')
            """,
            (source_id,),
        )

    client = SupabaseSyncClient(
        "https://project.supabase.co",
        "publishable",
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(503, text="offline"))
        ),
    )
    service = DesktopSyncService(database, client)
    service.queue_source(
        source_id,
        source_language="German",
        translation_language="US English",
    )

    assert service.flush(
        CloudSession(access_token="access", refresh_token="refresh", user_id="user-id")
    ) == (0, 1)
    with database_connection(database) as connection:
        state = connection.execute(
            "SELECT sync_state FROM sync_decks WHERE source_id = ?", (source_id,)
        ).fetchone()
        queued = connection.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()
    assert state == ("pending",)
    assert queued == (1,)


def test_desktop_can_optionally_upload_existing_tts_clips(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    cache = tmp_path / "cache"
    initialize_database(database)
    checksum = "abcdef1234567890"
    with database_connection(database) as connection:
        cursor = connection.execute(
            """
            INSERT INTO flashcard_sources(file_checksum, source_path, display_name, row_count)
            VALUES (?, '/deck.xlsx', 'German A1', 1)
            """,
            (checksum,),
        )
        source_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO flashcard_rows(
                source_id, rank, foreign_word, word_translation,
                foreign_sentence, sentence_translation
            ) VALUES (?, 1, 'lernen', 'to learn', 'Ich lerne.', 'I learn.')
            """,
            (source_id,),
        )
    cells = cache / "tts" / "jobs" / f"{checksum[:12]}-settings" / "cells"
    cells.mkdir(parents=True)
    (cells / "00001_1.mp3").write_bytes(b"word-audio")
    (cells / "00001_3.mp3").write_bytes(b"sentence-audio")
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(201)

    client = SupabaseSyncClient(
        "https://project.supabase.co",
        "publishable",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    service = DesktopSyncService(database, client, cache)
    service.queue_source(
        source_id,
        source_language="German",
        translation_language="US English",
        include_audio=True,
    )
    result = service.flush(
        CloudSession(access_token="access", refresh_token="refresh", user_id="user-id")
    )

    assert result == (1, 0)
    assert sum(path.startswith("/storage/v1/object/flashcard-audio/") for path in paths) == 2
    assert paths.count("/rest/v1/card_audio") == 2
