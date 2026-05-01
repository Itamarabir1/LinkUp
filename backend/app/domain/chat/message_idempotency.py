"""
Idempotency keys for POST chat messages (duplicate submit / retry).

Separate Redis prefix from passenger request-ride flows.
"""

import hashlib
import json as json_module
from uuid import UUID


def chat_message_redis_key(user_id: str, client_key: str) -> str:
    """Redis key: idempotency:chat_message:{user_id}:{client_key}."""
    return f"idempotency:chat_message:{user_id}:{client_key}"


def message_send_fingerprint(conversation_id: UUID, body: str) -> str:
    """SHA-256 canonical fingerprint: same conversation + same body = same intent."""
    canonical = json_module.dumps(
        {"conversation_id": str(conversation_id), "body": body},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
