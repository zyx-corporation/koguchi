import hashlib
import json
from datetime import datetime

GENESIS_HASH = "0" * 64


def canonical_serialize(payload: dict) -> bytes:
    """キー順序を固定した決定的シリアライズ。datetime は ISO 8601 文字列へ。"""

    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"not serializable: {type(obj)}")

    return json.dumps(payload, sort_keys=True, default=default, ensure_ascii=False).encode("utf-8")


def compute_hash(previous_hash: str, payload: dict) -> str:
    """hash = H(previous_hash || canonical_serialize(payload))"""
    data = previous_hash.encode("utf-8") + canonical_serialize(payload)
    return hashlib.sha256(data).hexdigest()
