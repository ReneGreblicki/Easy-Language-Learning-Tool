from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from platformdirs import PlatformDirs
except ImportError:  # Allows core-rule tests before optional desktop dependencies are installed.
    PlatformDirs = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class AppPaths:
    data: Path
    cache: Path
    logs: Path
    history: Path

    def create(self) -> None:
        for path in (self.data, self.cache, self.logs, self.history):
            path.mkdir(parents=True, exist_ok=True)


def resolve_app_paths() -> AppPaths:
    if PlatformDirs is None:
        base = Path.home() / "AppData" / "Local" / "Easy Language Learning Tool"
        documents = Path.home() / "Documents"
        return AppPaths(
            base,
            base / "Cache",
            base / "Logs",
            documents / "Easy Language Learning Tool" / "History",
        )
    dirs = PlatformDirs("Easy Language Learning Tool", appauthor=False, roaming=False)
    return AppPaths(
        data=Path(dirs.user_data_dir),
        cache=Path(dirs.user_cache_dir),
        logs=Path(dirs.user_log_dir),
        history=Path.home() / "Documents" / "Easy Language Learning Tool" / "History",
    )
