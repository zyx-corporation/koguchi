"""Policy Gate — redaction_policy に基づく墨消し範囲の証拠。"""
from datetime import UTC, datetime

from koguchi.decision import make_decision
from koguchi.envelope import ActionEnvelope
from koguchi.events import ExecutionEvent
from koguchi.policy import REDACTED, PolicyGate, RedactionPolicy


def _make_event() -> ExecutionEvent:
    return ExecutionEvent(
        event_id="ev-1",
        record_id="rec-1",
        timestamp=datetime.now(UTC),
        event_type="execution_committed",
        envelope=ActionEnvelope(
            action_id="rec-1",
            tool="filesystem.write",
            target="/tmp/test.txt",
            parameters_digest="abc",
            permission_scope="workspace",
            risk_class=["file_write"],
        ),
        side_effect_observed="confirmed",
        result_digest="digest123",
        intent="重要な設定変更",
        decision_ref="dec-1",
        context_ref="ctx-1",
        confidence=0.95,
        previous_hash="0" * 64,
        hash="a" * 64,
    )


def test_full_policy_shows_all_fields():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.FULL)
    assert redacted["intent"] == "重要な設定変更"
    assert redacted["decision_ref"] == "dec-1"
    assert redacted["context_ref"] == "ctx-1"
    assert redacted["result_digest"] == "digest123"
    assert redacted["envelope"] is not None


def test_without_intent_masks_intent():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.WITHOUT_INTENT)
    assert redacted["intent"] == REDACTED
    assert redacted["decision_ref"] == "dec-1"  # 参照は残す
    assert redacted["context_ref"] == "ctx-1"


def test_minimal_shows_only_basics():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.MINIMAL)
    assert "intent" not in redacted
    assert "decision_ref" not in redacted
    assert "context_ref" not in redacted
    assert "result_digest" not in redacted
    assert "envelope" not in redacted
    # 基本情報は残る
    assert redacted["event_id"] == "ev-1"
    assert redacted["event_type"] == "execution_committed"


def test_decision_full():
    decision = make_decision(action_id="rec-1", intent="テスト")
    redacted = PolicyGate.redact_decision(decision, RedactionPolicy.FULL)
    assert redacted["intent"] == "テスト"
    assert redacted["context_snapshot"] is None  # None もそのまま


def test_decision_without_intent():
    decision = make_decision(action_id="rec-1", intent="テスト")
    redacted = PolicyGate.redact_decision(decision, RedactionPolicy.WITHOUT_INTENT)
    assert redacted["intent"] == REDACTED


def test_decision_without_context():
    decision = make_decision(
        action_id="rec-1", intent="テスト",
        context_snapshot={"key": "value"},
    )
    redacted = PolicyGate.redact_decision(decision, RedactionPolicy.WITHOUT_CONTEXT)
    assert "context_snapshot" not in redacted
    assert redacted["intent"] == "テスト"  # intent は残る


def test_decision_minimal():
    decision = make_decision(action_id="rec-1", intent="テスト")
    redacted = PolicyGate.redact_decision(decision, RedactionPolicy.MINIMAL)
    assert "intent" not in redacted
    assert "context_snapshot" not in redacted
    assert "previous_hash" not in redacted
    assert redacted["decision_id"] is not None
