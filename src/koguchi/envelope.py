from pydantic import BaseModel
from typing import Optional


class ActionEnvelope(BaseModel):
    action_id: str
    tool: str                                   # PoC は "filesystem.write" のみ
    target: str
    parameters_digest: str                      # 入力の指紋（平文ではなくハッシュ）
    expected_result_digest: Optional[str] = None  # 期待される出力状態の指紋（決定論的ツールのみ）
    permission_scope: str
    risk_class: list[str]
    redaction_policy: Optional[str] = None      # 器だけ（Phase 2 以降）
