from __future__ import annotations

import sys
from dataclasses import dataclass, field

SERVICE_NAME = "Easy Language Learning Tool"


def secure_store_name() -> str:
    return "macOS Keychain" if sys.platform == "darwin" else "Windows Credential Manager"


@dataclass
class CredentialStore:
    """Native credential storage through keyring, with session-only fallback."""

    session_values: dict[str, str] = field(default_factory=dict)

    def set(self, provider: str, api_key: str, *, remember: bool) -> None:
        if not api_key:
            self.delete(provider)
            return
        self.session_values[provider] = api_key
        if remember:
            try:
                import keyring

                keyring.set_password(SERVICE_NAME, provider, api_key)
            except Exception as error:
                raise RuntimeError(
                    f"The API key could not be saved to {secure_store_name()}."
                ) from error

    def get(self, provider: str) -> str | None:
        if provider in self.session_values:
            return self.session_values[provider]
        try:
            import keyring

            return keyring.get_password(SERVICE_NAME, provider)
        except Exception:
            return None

    def delete(self, provider: str) -> None:
        self.session_values.pop(provider, None)
        try:
            import keyring

            if keyring.get_password(SERVICE_NAME, provider) is not None:
                keyring.delete_password(SERVICE_NAME, provider)
        except Exception:
            return
