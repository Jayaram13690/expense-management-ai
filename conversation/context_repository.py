from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import boto3

from config.settings import settings


class ConversationContextRepository:
    """Persists ConversationContext snapshots in DynamoDB."""

    def __init__(self):
        self._table = boto3.resource(
            "dynamodb",
            region_name=settings.aws.aws_region,
        ).Table("ConversationContext")

    def load(self, session_id: str) -> dict | None:
        response = self._table.get_item(Key={"session_id": session_id})

        item = response.get("Item")

        if item is None:
            return None

        return json.loads(item["snapshot"])

    def save(
        self,
        session_id: str,
        snapshot: dict,
    ) -> None:

        ttl = int(time.time()) + 86400

        self._table.put_item(
            Item={
                "session_id": session_id,
                "snapshot": json.dumps(snapshot, default=str),
                "updated_at": datetime.now(UTC).isoformat(),
                "ttl": ttl,
            }
        )

    def delete(self, session_id: str) -> None:
        self._table.delete_item(Key={"session_id": session_id})
