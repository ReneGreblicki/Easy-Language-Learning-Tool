from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from easy_language_learning_tool.persistence.database import initialize_database
from easy_language_learning_tool.sync.models import SyncOperation, SyncOperationType
from easy_language_learning_tool.sync.outbox import SyncOutbox


def operation(operation_type: SyncOperationType, delete_everywhere: bool = False) -> SyncOperation:
    entity_id = uuid4()
    return SyncOperation(
        id=uuid4(),
        entity_type="deck",
        entity_id=entity_id,
        operation=operation_type,
        payload={"deck_id": str(entity_id), "delete_everywhere": delete_everywhere},
    )


def test_phone_only_removal_cannot_enter_sync_deletion_outbox() -> None:
    with pytest.raises(ValidationError, match="Phone-only removal"):
        operation(SyncOperationType.SOFT_DELETE)


def test_delete_everywhere_can_be_queued_and_acknowledged(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    initialize_database(database)
    outbox = SyncOutbox(database)
    item = operation(SyncOperationType.SOFT_DELETE, delete_everywhere=True)

    outbox.enqueue(item)
    outbox.enqueue(item)

    assert outbox.pending() == [item]
    outbox.acknowledge(str(item.id))
    assert outbox.pending() == []


def test_failed_item_is_retained_for_retry(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    initialize_database(database)
    outbox = SyncOutbox(database)
    item = operation(SyncOperationType.UPSERT)
    outbox.enqueue(item)

    outbox.record_failure(str(item.id), "network unavailable")

    assert outbox.pending() == []
