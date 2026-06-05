from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from koguchi.envelope import ActionEnvelope


class ProxyResult(StrEnum):
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
    envelope: ActionEnvelope | None = None
    result_digest: str | None = None
    error_digest: str | None = None
    # Phase 1 の filesystem.write は none|confirmed のみ
    side_effect_observed: Literal["none", "partial", "unknown", "confirmed"] | None = None
    confidence: float | None = None         # reconciliation 診断用（最尤推定）
    previous_hash: str | None = None
    hash: str

    # 縮退を防ぐ空フック（Phase 2 以降で埋まる）
    intent: str | None = None               # なぜ
    decision_ref: str | None = None         # Decision Logger が接続
    context_ref: str | None = None          # Context Resolver が接続
