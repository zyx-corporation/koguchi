"""Phase 7: RDE / T-RDE — 意味変化監査の証拠。"""
import pytest

from koguchi.rde import (
    RdeHint,
    RdeReview,
    assert_no_unresolved_hidden,
    assert_preserved,
    assert_risk_declared,
    make_review,
)


def test_rde_hint_defaults_are_empty():
    hint = RdeHint()
    assert hint.preserved == []
    assert hint.transformed == []
    assert hint.supplemented == []
    assert hint.unresolved == []
    assert hint.risks == []
    assert hint.next_policy is None


def test_rde_review_marks_automated_false_by_default():
    hint = RdeHint()
    review = make_review(action_id="act-1", hint=hint)
    assert review.automated is False
    assert review.reviewer is None
    assert review.action_id == "act-1"


def test_assert_preserved_passes_when_expected_present():
    hint = RdeHint(preserved=["GitHub Issue として作成する"])
    assert_preserved(hint, "GitHub Issue として作成する")


def test_assert_preserved_fails_when_expected_missing():
    hint = RdeHint(preserved=["別の項目"])
    with pytest.raises(AssertionError):
        assert_preserved(hint, "存在しない項目")


def test_assert_risk_declared_detects_keyword():
    hint = RdeHint(risks=["監査可能性を hash の存在だけで満たしたと誤解する"])
    assert_risk_declared(hint, "監査可能性")


def test_assert_risk_declared_fails_when_keyword_missing():
    hint = RdeHint(risks=["別のリスク"])
    with pytest.raises(AssertionError):
        assert_risk_declared(hint, "存在しないキーワード")


def test_assert_no_unresolved_hidden_detects_missing_risks():
    hint = RdeHint(unresolved=["verify_chain の抽象境界"], risks=[])
    with pytest.raises(AssertionError):
        assert_no_unresolved_hidden(hint)


def test_assert_no_unresolved_hidden_passes_when_risks_present():
    hint = RdeHint(
        unresolved=["verify_chain の抽象境界"],
        risks=["未解決のまま実装を進めると後方互換性が失われる"],
    )
    assert_no_unresolved_hidden(hint)


def test_rde_hint_can_represent_joujou_todo_meaning_change():
    hint = RdeHint(
        preserved=[
            "GitHub Issue として作成する",
            "Koguchi の hash chain 検証 API を追加する",
        ],
        transformed=[
            "会話中の作業意図を Issue title/body に圧縮した",
        ],
        unresolved=[
            "verify_chain() を Protocol に含めるか SQLite 実装に限定するか",
        ],
        risks=[
            "監査可能性を hash の存在だけで満たしたと誤解する",
        ],
        next_policy="ADR で verify_chain の抽象境界を決める",
    )
    review = make_review(action_id="joujou-001", hint=hint)
    assert isinstance(review, RdeReview)
    assert_preserved(hint, "GitHub Issue として作成する")
    assert_risk_declared(hint, "監査可能性")
    assert_no_unresolved_hidden(hint)
