from __future__ import annotations

import json
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HistoryItem:
    id: int
    file_type: str
    path: Path
    display_name: str
    created_at: str
    settings: dict[str, object] | None
    status: str


class HistoryService:
    def __init__(
        self,
        database_path: Path,
        history_root: Path,
        recycler: Callable[[str], None] | None = None,
        retention_per_type: int = 20,
    ) -> None:
        self.database_path = database_path
        self.history_root = history_root.resolve()
        self.history_root.mkdir(parents=True, exist_ok=True)
        self.retention_per_type = retention_per_type
        if recycler is None:
            from send2trash import send2trash

            recycler = send2trash
        self.recycler = recycler

    def add(
        self,
        source: Path,
        file_type: str,
        *,
        settings: dict[str, object] | None = None,
        status: str = "complete",
    ) -> HistoryItem:
        if file_type not in {"workbook", "audio"}:
            raise ValueError("History type must be workbook or audio.")
        destination_directory = self.history_root / (
            "Spreadsheets" if file_type == "workbook" else "Audio"
        )
        destination_directory.mkdir(parents=True, exist_ok=True)
        destination = self._deduplicated_path(destination_directory / source.name)
        shutil.copy2(source, destination)
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO history_items(file_type, owned_path, display_name, settings_json, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    file_type,
                    str(destination),
                    destination.name,
                    json.dumps(settings) if settings else None,
                    status,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("History database did not return a new item ID.")
            item_id = cursor.lastrowid
        self._enforce_retention(file_type)
        return self.get(item_id)

    def list(self, file_type: str | None = None) -> list[HistoryItem]:
        sql = "SELECT id, file_type, owned_path, display_name, created_at, settings_json, status FROM history_items"
        params: tuple[str, ...] = ()
        if file_type:
            sql += " WHERE file_type = ?"
            params = (file_type,)
        sql += " ORDER BY created_at DESC, id DESC"
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, item_id: int) -> HistoryItem:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT id, file_type, owned_path, display_name, created_at, settings_json, status FROM history_items WHERE id = ?",
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"History item {item_id} does not exist.")
        return self._from_row(row)

    def rename(self, item_id: int, new_name: str) -> HistoryItem:
        item = self.get(item_id)
        clean = Path(new_name).name.strip()
        if not clean or clean in {".", ".."}:
            raise ValueError("A valid file name is required.")
        suffix = item.path.suffix
        if Path(clean).suffix.casefold() != suffix.casefold():
            clean += suffix
        destination = item.path.with_name(clean)
        self._assert_owned(destination)
        if destination.exists():
            raise FileExistsError("A history item with that name already exists.")
        item.path.rename(destination)
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute(
                    "UPDATE history_items SET owned_path = ?, display_name = ? WHERE id = ?",
                    (str(destination), destination.name, item_id),
                )
        except Exception:
            destination.rename(item.path)
            raise
        return self.get(item_id)

    def delete(self, item_id: int) -> None:
        item = self.get(item_id)
        self._assert_owned(item.path)
        if item.path.exists():
            self.recycler(str(item.path))
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DELETE FROM history_items WHERE id = ?", (item_id,))

    def export(self, item_id: int, destination: Path) -> Path:
        item = self.get(item_id)
        self._assert_owned(item.path)
        if destination.resolve() == item.path.resolve():
            raise ValueError("Choose a location outside the existing history item.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError("The export destination already exists.")
        shutil.copy2(item.path, destination)
        return destination

    def regeneration_settings(self, item_id: int) -> dict[str, object]:
        item = self.get(item_id)
        if item.file_type != "workbook" or item.settings is None:
            raise ValueError("This history item does not contain regeneration settings.")
        return dict(item.settings)

    def _enforce_retention(self, file_type: str) -> None:
        items = self.list(file_type)
        for item in items[self.retention_per_type :]:
            self.delete(item.id)

    def _assert_owned(self, path: Path) -> None:
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self.history_root)
        except ValueError as error:
            raise ValueError("The requested operation is outside app-owned History.") from error

    @staticmethod
    def _deduplicated_path(path: Path) -> Path:
        if not path.exists():
            return path
        for number in range(2, 10_000):
            candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
            if not candidate.exists():
                return candidate
        raise RuntimeError("Could not create a unique history filename.")

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> HistoryItem:
        settings = json.loads(str(row[5])) if row[5] else None
        return HistoryItem(
            id=int(str(row[0])),
            file_type=str(row[1]),
            path=Path(str(row[2])),
            display_name=str(row[3]),
            created_at=str(row[4]),
            settings=settings,
            status=str(row[6]),
        )
