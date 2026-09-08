from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from easy_language_learning_tool.sync.models import DeckPayload, SyncOperation

SUPABASE_PROJECT_URL = "https://jmnsrikmqopdhmnkjmah.supabase.co"
SUPABASE_PUBLIC_CLIENT_CONFIG = "sb_publishable_CtsilxSEQHVULSCmAgdGSg_6BZVtqmE"


class SyncClientError(RuntimeError):
    """Normalized cloud authentication or synchronization failure."""


@dataclass(frozen=True)
class CloudSession:
    access_token: str
    refresh_token: str
    user_id: str


class SupabaseSyncClient:
    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.project_url = project_url.rstrip("/")
        self.publishable_key = publishable_key
        self._http = http_client or httpx.Client(timeout=30)

    def sign_in(self, email: str, password: str) -> CloudSession:
        response = self._http.post(
            f"{self.project_url}/auth/v1/token",
            params={"grant_type": "password"},
            headers=self._public_headers(),
            json={"email": email.strip(), "password": password},
        )
        data = self._json_or_error(response, "Sign-in failed")
        try:
            return CloudSession(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                user_id=str(data["user"]["id"]),
            )
        except (KeyError, TypeError) as error:
            raise SyncClientError("The authentication response was incomplete.") from error

    def refresh_session(self, refresh_token: str) -> CloudSession:
        response = self._http.post(
            f"{self.project_url}/auth/v1/token",
            params={"grant_type": "refresh_token"},
            headers=self._public_headers(),
            json={"refresh_token": refresh_token},
        )
        data = self._json_or_error(response, "Session refresh failed")
        try:
            return CloudSession(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                user_id=str(data["user"]["id"]),
            )
        except (KeyError, TypeError) as error:
            raise SyncClientError("The refreshed session was incomplete.") from error

    def upload(self, operation: SyncOperation, session: CloudSession) -> None:
        if operation.operation.value != "upsert" or operation.entity_type != "deck":
            raise SyncClientError("This client currently accepts deck upserts only.")
        deck = DeckPayload.model_validate(operation.payload)
        deck_row: dict[str, Any] = {
            "id": str(deck.id),
            "user_id": session.user_id,
            "title": deck.title,
            "source_language": deck.source_language,
            "translation_language": deck.translation_language,
            "cefr_level": deck.cefr_level,
            "settings": deck.settings,
            "revision": deck.revision,
            "updated_at": deck.updated_at.isoformat(),
            "deleted_at": None,
            "purge_after": None,
        }
        self._upsert("decks", [deck_row], session)
        card_rows = [
            {
                "id": str(card.id),
                "deck_id": str(deck.id),
                "user_id": session.user_id,
                "rank": card.rank,
                "foreign_word": card.foreign_word,
                "word_translation": card.word_translation,
                "foreign_sentence": card.foreign_sentence,
                "sentence_translation": card.sentence_translation,
                "revision": card.revision,
                "updated_at": deck.updated_at.isoformat(),
            }
            for card in deck.cards
        ]
        for start in range(0, len(card_rows), 250):
            self._upsert("cards", card_rows[start : start + 250], session)
        for audio in deck.audio:
            path = f"{session.user_id}/{deck.id}/{audio.card_id}-{audio.side}.mp3"
            source = Path(audio.local_path)
            if not source.is_file() or source.stat().st_size != audio.byte_size:
                raise SyncClientError(f"Desktop TTS clip is unavailable: {source}")
            response = self._http.post(
                f"{self.project_url}/storage/v1/object/flashcard-audio/{path}",
                headers={
                    "apikey": self.publishable_key,
                    "Authorization": f"Bearer {session.access_token}",
                    "Content-Type": "audio/mpeg",
                    "x-upsert": "true",
                },
                content=source.read_bytes(),
            )
            self._json_or_error(response, "Could not upload desktop TTS audio")
            self._upsert(
                "card_audio",
                [
                    {
                        "id": str(audio.id),
                        "card_id": str(audio.card_id),
                        "user_id": session.user_id,
                        "side": audio.side,
                        "storage_path": path,
                        "sha256": audio.sha256,
                        "byte_size": audio.byte_size,
                        "updated_at": deck.updated_at.isoformat(),
                    }
                ],
                session,
            )

    def _upsert(self, table: str, rows: list[dict[str, Any]], session: CloudSession) -> None:
        response = self._http.post(
            f"{self.project_url}/rest/v1/{table}",
            params={"on_conflict": "id"},
            headers={
                **self._public_headers(),
                "Authorization": f"Bearer {session.access_token}",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=rows,
        )
        self._json_or_error(response, f"Could not synchronize {table}")

    def _public_headers(self) -> dict[str, str]:
        return {"apikey": self.publishable_key, "Content-Type": "application/json"}

    @staticmethod
    def _json_or_error(response: httpx.Response, message: str) -> dict[str, Any]:
        if response.is_success:
            if not response.content:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}
        detail = response.text[:500]
        try:
            payload = response.json()
            detail = str(payload.get("msg") or payload.get("message") or detail)
        except ValueError:
            pass
        raise SyncClientError(f"{message}: {detail}")
