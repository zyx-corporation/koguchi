from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional

from koguchi.envelope import ActionEnvelope


class ProxyResult(str, Enum):
    SUCCESS     = "success"      # 副作用成功 + commit 記録成功
    FAILURE     = "failure"      # Proxy が成功完了を確認できなかった
    REJECTED    = "rejected"     # validate / pending 書込み前に弾かれた。副作用なし
    UNCONFIRMED = "unconfirmed"  # 副作用成功を観測したが commit 記録に失敗。Store には無い


class ExecutionEvent(BaseModel):               # append-only。状態は上書きしない
    event_id: str
    record_id: str                             # 同一副作用に属する event を束ねる
    timestamp: datetime
    event_type: Literal[
        "intent_pending",
        "execution_committed",
        "execution_failed",
        "reconciliation_observed",
    ]
    envelope: Optional[ActionEnvelope] = None
    result_digest: Optional[str] = None
    error_digest: Optional[str] = None
    side_effect_observed: Optional[
        Literal["none", "partial", "unknown", "confirmed"]
    ] = None                                   # Phase 1 の filesystem.write は none|confirmed のみ
    confidence: Optional[float] = None         # reconciliation 診断用（最尤推定）
    previous_hash: Optional[str] = None
    hash: str

    # 縮退を防ぐ空フック（Phase 2 以降で埋まる）
    intent: Optional[str] = None               # なぜ
    decision_ref: Optional[str] = None         # Decision Logger が接続
    context_ref: Optional[str] = None          # Context Resolver が接続
