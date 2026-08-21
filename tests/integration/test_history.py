from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from easy_language_learning_tool.history.service import HistoryService
from easy_language_learning_tool.persistence.database import initialize_database


class HistoryTests(unittest.TestCase):
    def test_retention_rename_export_and_safe_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "app.sqlite3"
            initialize_database(database)
            recycled: list[str] = []

            def recycle(path: str) -> None:
                recycled.append(path)
                Path(path).unlink()

            service = HistoryService(database, root / "history", recycle, retention_per_type=2)
            ids = []
            for number in range(3):
                source = root / f"source-{number}.xlsx"
                source.write_bytes(str(number).encode())
                ids.append(service.add(source, "workbook", settings={"seed": number}).id)
            self.assertEqual(len(service.list("workbook")), 2)
            self.assertEqual(len(recycled), 1)
            item = service.rename(ids[-1], "renamed")
            self.assertEqual(item.path.name, "renamed.xlsx")
            exported = service.export(item.id, root / "external" / "copy.xlsx")
            service.delete(item.id)
            self.assertTrue(exported.exists())
            self.assertFalse(item.path.exists())


if __name__ == "__main__":
    unittest.main()
