"""RDE / T-RDE — 意味変化監査のための schema と test helper。

RDE は自動裁定器ではない。意味変化を記録・テスト・レビューしやすくする構造である。
ΔM は価値そのものではない。分類のための監査構造である。
"""

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class RdeCategory(StrEnum):
    PRESERVED = "preserved"
    TRANSFORMED = "transformed"
    SUPPLEMENTED = "supplemented"
    UNRESOLVED = "unresolved"
    RISK = "risk"
    NEXT_POLICY = "next_policy"


class RdeHint(BaseModel):
    """意味変化の候補を記録する hint。自動判定ではなく人間の監査を補助する。"""

    preserved: list[str] = Field(default_factory=list)
    transformed: list[str] = Field(default_factory=list)
    supplemented: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_policy: str | None = None


class RdeReview(BaseModel):
    """RDE review record。RdeReviewStore 実装までは in-memory。"""

    review_id: str
    action_id: str
    hint: RdeHint
    reviewer: str | None = None
    automated: bool = False


def make_review(action_id: str, hint: RdeHint) -> RdeReview:
    """RdeReview のファクトリ関数。"""
    return RdeReview(
        review_id=str(uuid.uuid4()),
        action_id=action_id,
        hint=hint,
    )


# --- T-RDE test helpers ---


def assert_preserved(hint: RdeHint, expected: str) -> None:
    """expected が preserved に含まれていることを検証する。"""
    assert expected in hint.preserved, (
        f"Expected '{expected}' in preserved, got {hint.preserved}"
    )


def assert_risk_declared(hint: RdeHint, keyword: str) -> None:
    """keyword を含むリスクが risks に宣言されていることを検証する。"""
    found = any(keyword in r for r in hint.risks)
    assert found, (
        f"Expected risk containing '{keyword}' in risks, got {hint.risks}"
    )


def assert_no_unresolved_hidden(hint: RdeHint) -> None:
    """unresolved が空でない場合、それが意図的に残されていることを確認する。
    空の unresolved は許容するが、存在する場合は risks にも言及があるべき。
    """
    if hint.unresolved:
        assert hint.risks, (
            "Unresolved items exist but no risks declared. "
            "Unresolved items should have corresponding risk notes."
        )
